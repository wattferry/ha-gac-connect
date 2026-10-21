"""Cloud failures recover on real reads, including bounded quiet-hour retries."""
import asyncio
import json
import socket
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.gac_connect.api import decode_status
from gac_connect.errors import (
    AuthExpiredError, RateLimitedError, ResponseError,
)
from custom_components.gac_connect.coordinator import NETWORK_GRACE_SECONDS, _failure_reason
from custom_components.gac_connect.button import GacRefreshButton
from custom_components.gac_connect.diagnostics import async_get_config_entry_diagnostics
from custom_components.gac_connect.sensor import ACTIVITY_SENSORS, GacActivitySensor, GacSensorEntity, SENSORS
from test_autodetect import vehicle
from test_command_refresh import Clock, clock_patch
from test_regressions import ACCEPTED


def network_error(cause):
    error = ResponseError("Could not reach GAC")
    error.__cause__ = cause
    return error


@pytest.mark.parametrize("cause,reason", [
    (TimeoutError("PRIVATE-TOKEN"), "timeout"),
    (socket.gaierror(-3, "PRIVATE-HOST"), "dns"),
    (aiohttp.ClientSSLError(SimpleNamespace(host="PRIVATE-HOST", port=443, ssl=True),
                            OSError("PRIVATE-URL")), "tls"),
    (aiohttp.ClientConnectionError("PRIVATE-URL"), "connection"),
])
def test_transport_failure_exposes_only_a_safe_reason(cause, reason):
    assert _failure_reason(network_error(cause)) == reason


def test_dns_cause_is_recognized_inside_a_connector_error():
    key = SimpleNamespace(host="PRIVATE-HOST", port=443, ssl=True)
    cause = aiohttp.ClientConnectorError(key, socket.gaierror(-3, "PRIVATE-TOKEN"))
    cause.__cause__ = cause.os_error
    assert _failure_reason(network_error(cause)) == "dns"


def test_long_poll_interval_uses_backoff_and_returns_to_normal_on_success(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={"scan_interval": 3600}) as (hass, _, c):
            cancel = c.async_add_listener(lambda: None)
            try:
                c.client.get_status.side_effect = [network_error(TimeoutError())] * 4 + [decode_status({})]
                with patch.object(c, "_in_quiet_hours", return_value=False):
                    for expected in (60, 120, 300, 300, 3600):
                        await c.async_refresh()
                        handle = c._unsub_refresh.__self__
                        assert expected - 2 <= handle.when() - hass.loop.time() <= expected + 1
                        assert c.update_interval == timedelta(hours=1)
                    assert c.last_update_success
                    assert c.polling_state == "ok"
                    assert c.retry_not_before is None
                    assert c.last_refresh_error == "timeout"  # Retained for diagnosis after recovery.
            finally:
                cancel()
    asyncio.run(run())


def test_recovery_does_not_lengthen_a_short_poll_interval(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={"scan_interval": 60}) as (hass, _, c):
            cancel = c.async_add_listener(lambda: None)
            try:
                c.client.get_status.side_effect = network_error(TimeoutError())
                with patch.object(c, "_in_quiet_hours", return_value=False):
                    for _ in range(3):
                        await c.async_refresh()
                        assert 58 <= c._unsub_refresh.__self__.when() - hass.loop.time() <= 61
            finally:
                cancel()
    asyncio.run(run())


def test_quiet_hours_cannot_make_a_failed_fetch_look_recovered(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            clock = Clock()
            c.client.get_status.return_value = replace(decode_status({}), soc=50)
            with patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                with patch.object(c, "_in_quiet_hours", return_value=False):
                    await c.async_refresh()
                    success = c.last_refresh_success
                    c.client.get_status.side_effect = network_error(TimeoutError())
                    await c.async_refresh()
                    assert c.last_update_success and c.polling_state == "error"   # a network blip, for now
                clock.now = NETWORK_GRACE_SECONDS + 1
                with patch.object(c, "_in_quiet_hours", return_value=True):
                    for _ in range(3):
                        await c.async_refresh()
                        assert not c.last_update_success
                        assert c.polling_state == "error"
                        assert c.last_refresh_success == success
                    assert c.client.get_status.await_count == 2
                    assert c.data.soc == 50
    asyncio.run(run())


@pytest.mark.parametrize("cause,graced", [(socket.gaierror(-3, "x"), True), (TimeoutError(), True),
                                          (aiohttp.ClientSSLError(None, OSError()), False)])
def test_a_network_blip_keeps_the_last_report_quietly_for_a_few_minutes(tmp_path, caplog, cause, graced):
    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            clock = Clock()
            c.client.get_status.return_value = replace(decode_status({}), soc=50)
            with patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic), \
                    patch.object(c, "_in_quiet_hours", return_value=False):
                await c.async_refresh()
                c.client.get_status.side_effect = network_error(cause)
                caplog.clear()
                for now in (0, 60, 180, NETWORK_GRACE_SECONDS - 1):
                    clock.now = now
                    await c.async_refresh()
                    assert c.last_update_success is graced and c.polling_state == "error"
                    assert (c.data.soc == 50) and c.retry_not_before is not None
                assert not [r for r in caplog.records if r.levelname == "ERROR"] or not graced
                clock.now = NETWORK_GRACE_SECONDS
                await c.async_refresh()
                assert not c.last_update_success          # still failing: unavailable, as before
                assert [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
                c.client.get_status.side_effect = None
                await c.async_refresh()
                assert c.last_update_success and c.polling_state == "ok" and c._failing_since is None
    asyncio.run(run())


@pytest.mark.parametrize("recover", [False, True])
def test_explicit_quiet_hour_read_gets_bounded_recovery_and_preserves_availability_truth(tmp_path, recover):
    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            c.data = decode_status({})
            clock = Clock()
            c.client.get_status.side_effect = network_error(TimeoutError("PRIVATE-TOKEN"))
            health = GacActivitySensor(c, next(d for d in ACTIVITY_SENSORS if d.key == "polling_status"))
            sensor = GacSensorEntity(c, next(d for d in SENSORS if d.key == "soc"))
            with patch.object(c, "_in_quiet_hours", return_value=True), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                c._force_refresh = True
                await c.async_refresh()
                assert not sensor.available and health.available and health.native_value == "error"
                assert c._quiet_recovery_remaining == 2
                clock.now = 59
                await c.async_refresh()
                assert c.client.get_status.await_count == 1 and not c.last_update_success
                if recover:
                    c.client.get_status.side_effect = None
                clock.now = 60
                await c.async_refresh()
                if recover:
                    assert c.client.get_status.await_count == 2
                    assert sensor.available and health.native_value == "quiet_hours"
                    assert c.last_refresh_success is not None and c.retry_not_before is None
                    assert c._quiet_recovery_remaining == 0
                else:
                    clock.now = 180
                    await c.async_refresh()
                    clock.now = 600
                    await c.async_refresh()
                    assert c.client.get_status.await_count == 3
                    assert not sensor.available and c.last_refresh_success is None
                    assert c._quiet_recovery_remaining == 0 and c.retry_not_before is None
                assert health.extra_state_attributes["last_error_reason"] == "timeout"
                assert "PRIVATE" not in json.dumps(health.extra_state_attributes, default=str)
    asyncio.run(run())


def test_failed_post_command_read_uses_recovery_instead_of_rapid_followups_or_command_replay(tmp_path):
    from custom_components.gac_connect.command_tracking import async_send

    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            c.data = decode_status({})
            clock = Clock()
            c.client.get_status.side_effect = network_error(TimeoutError())
            with patch.object(c, "_start_result_refresh"), clock_patch(clock), \
                    patch.object(c, "_in_quiet_hours", return_value=True), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                command = AsyncMock(return_value=ACCEPTED)
                await async_send(c, "lock", command())
                await c._result_refresh()
                assert c.client.get_status.await_count == 1
                assert c._refresh_deadlines == [] and not c.last_update_success
                clock.now = 65
                c.client.get_status.side_effect = None
                await c.async_refresh()
                assert c.client.get_status.await_count == 2 and c.last_update_success
                command.assert_awaited_once()
    asyncio.run(run())


def test_initial_setup_still_requires_a_real_report(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            c.client.get_status.side_effect = network_error(TimeoutError())
            entry._async_set_state(hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
            with pytest.raises(ConfigEntryNotReady):
                await c.async_config_entry_first_refresh()
            assert c.data is None and not c.last_update_success
    asyncio.run(run())


def test_refresh_button_remains_usable_after_a_failed_cloud_read(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            c.data = decode_status({})
            button = GacRefreshButton(c)
            c._debounced_refresh.cooldown = 0.001
            c.client.get_status.side_effect = network_error(TimeoutError())
            with patch.object(c, "_in_quiet_hours", return_value=True):
                await button.async_press()
                assert not c.last_update_success and button.available
                await asyncio.sleep(0.01)  # Let HA's normal button debounce window expire.
                c.client.get_status.side_effect = None
                await button.async_press()
                assert c.client.get_status.await_count == 2 and c.last_update_success
                assert c.last_refresh_success is not None
    asyncio.run(run())


@pytest.mark.parametrize("failure,state", [
    (RateLimitedError("wait", retry_after=600), "rate_limited"),
    (AuthExpiredError("sign in"), "auth_required"),
])
def test_service_backoff_and_reauthentication_cancel_transient_recovery(tmp_path, failure, state):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            c.data = decode_status({})
            clock = Clock()
            reauth_method = ("async_start_reauth_if_available" if hasattr(entry, "async_start_reauth_if_available")
                             else "async_start_reauth")
            with patch.object(c, "_in_quiet_hours", return_value=True), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic), \
                    patch.object(entry, reauth_method) as reauth:
                c._force_refresh = True
                c.client.get_status.side_effect = network_error(TimeoutError())
                await c.async_refresh()
                c.client.get_status.side_effect = failure
                clock.now = 60
                await c.async_refresh()
                assert c._quiet_recovery_remaining == 0 and c._recovery_retry_at is None
                assert c.polling_state == state
                if state == "rate_limited":
                    c._force_refresh = True
                    await c.async_refresh()
                    assert c.client.get_status.await_count == 2
                    assert (c.retry_not_before - c.last_refresh_attempt).total_seconds() >= 599
                    reauth.assert_not_called()
                else:
                    reauth.assert_called_once_with(hass)
                    assert c.retry_not_before is None and not c.last_update_success
    asyncio.run(run())


def test_diagnostics_retain_safe_failure_details_and_the_configured_hosts(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            c.client.get_status.side_effect = network_error(socket.gaierror(-3, "PRIVATE-TOKEN"))
            await c.async_refresh()
            c.client.get_status.side_effect = None
            await c.async_refresh()
            result = await async_get_config_entry_diagnostics(hass, entry)
            assert result["polling"]["last_error_reason"] == "dns"
            assert result["polling"]["last_error_time"] is not None
            assert result["polling"]["last_success"] is not None
            assert result["polling"]["retry_not_before"] is None
            assert result["endpoints"] == {"account_host": "nl-app-api.gac-international.com",
                                           "vehicle_host": "eu-iov-sdk-access.gac-international.com"}
            assert "PRIVATE" not in json.dumps(result)
    asyncio.run(run())
