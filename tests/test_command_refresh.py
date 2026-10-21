"""Bounded post-command reads shared by every control and its reported sensors."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.binary_sensor import BINARY_SENSORS, GacBinaryEntity
from custom_components.gac_connect.command_tracking import async_send
from gac_connect.errors import GacError, RateLimitedError
from test_autodetect import vehicle
from test_regressions import ACCEPTED


class Clock:
    now = 0.0

    def monotonic(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


def clock_patch(clock):
    # Replace only this module's asyncio reference; HA keeps its real event loop.
    return patch("custom_components.gac_connect.coordinator.asyncio",
                 SimpleNamespace(Lock=asyncio.Lock, gather=asyncio.gather, sleep=clock.sleep))


def test_accepted_commands_and_results_share_three_delayed_reads(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            clock = Clock()
            times = []

            async def fetch(_vin):
                times.append(clock.now)
                return decode_status({})

            coordinator.client.get_status.side_effect = fetch
            with patch.object(coordinator, "_start_result_refresh") as start, clock_patch(clock), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                for command in ("lock", "sunroof-close", "aircon-on", "fridge-on"):
                    await async_send(coordinator, command, AsyncMock(return_value=ACCEPTED)())
                    coordinator._schedule_result_refresh()
                coordinator.client.get_status.assert_not_awaited()  # Never immediately after acceptance.
                assert start.called
                await coordinator._result_refresh()
                assert times == [5, 15, 30]
                assert coordinator._refresh_deadlines == []
    asyncio.run(run())


def test_a_new_command_during_a_read_retains_its_followups(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            clock = Clock()
            times = []

            async def fetch(_vin):
                times.append(clock.now)
                if len(times) == 1:
                    coordinator.async_schedule_command_refresh()
                return decode_status({})

            coordinator.client.get_status.side_effect = fetch
            with patch.object(coordinator, "_start_result_refresh"), clock_patch(clock), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                coordinator.async_schedule_command_refresh()
                await coordinator._result_refresh()
            assert times == [5, 15, 25, 35]
            assert all(later - earlier >= 10 for earlier, later in zip(times, times[1:]))
    asyncio.run(run())


def test_scheduled_and_manual_reads_also_space_followup_requests(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            clock = Clock()
            times = []

            async def fetch(_vin):
                times.append(clock.now)
                return decode_status({})

            coordinator.client.get_status.side_effect = fetch
            with patch.object(coordinator, "_start_result_refresh"), clock_patch(clock), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                coordinator.async_schedule_command_refresh()
                clock.now = 4
                await coordinator.async_refresh()
                await coordinator._result_refresh()
            assert times == [4, 14, 24, 34]
    asyncio.run(run())


def test_fresh_reports_update_related_sensors_even_during_quiet_hours(tmp_path):
    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (_, _, coordinator):
            clock = Clock()
            locked = decode_status({"doorAccessors": [
                {"door": i, "lock": 0 if i < 3 else -1} for i in range(1, 5)
            ]})
            unlocked = decode_status({"doorAccessors": [{"door": 1, "lock": 1}]})
            coordinator.data = locked
            sensor = GacBinaryEntity(coordinator, next(d for d in BINARY_SENSORS if d.key == "locked"))
            coordinator.client.get_status.side_effect = [locked, locked, unlocked]
            with patch.object(coordinator, "_start_result_refresh"), \
                    patch.object(coordinator, "_in_quiet_hours", return_value=True), clock_patch(clock), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                coordinator.async_schedule_command_refresh()
                assert sensor.is_on is False  # Acceptance never fabricates a sensor reading.
                await coordinator._result_refresh()
                assert sensor.is_on is True
                assert coordinator.client.get_status.await_count == 3
    asyncio.run(run())


def test_a_rate_limit_stops_followups_and_preserves_the_last_report(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            clock = Clock()
            previous = coordinator.data = decode_status({})
            coordinator.client.get_status.side_effect = RateLimitedError("wait")
            with patch.object(coordinator, "_start_result_refresh"), clock_patch(clock), \
                    patch("custom_components.gac_connect.coordinator.monotonic", clock.monotonic):
                coordinator.async_schedule_command_refresh()
                await coordinator._result_refresh()
                assert coordinator.data is previous
                assert coordinator.client.get_status.await_count == 1
                assert coordinator._refresh_deadlines == []
    asyncio.run(run())


@pytest.mark.parametrize("failure", [GacError("offline"), asyncio.CancelledError()])
def test_failed_or_cancelled_commands_do_not_schedule_reads(failure):
    coordinator = SimpleNamespace(capabilities=None, async_schedule_command_refresh=Mock())
    with pytest.raises(type(failure)):
        asyncio.run(async_send(coordinator, "lock", AsyncMock(side_effect=failure)()))
    coordinator.async_schedule_command_refresh.assert_not_called()


def test_unload_cancels_followups_and_prevents_late_scheduling(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, coordinator):
            coordinator.async_schedule_command_refresh()
            first = coordinator._result_refresh_task
            coordinator.async_schedule_command_refresh()
            coordinator._schedule_result_refresh()
            assert coordinator._result_refresh_task is first
            await entry._async_process_on_unload(hass)
            await asyncio.sleep(0)
            assert first.done()
            assert coordinator._refresh_deadlines == []
            coordinator.async_schedule_command_refresh()
            assert coordinator._refresh_deadlines == []
            coordinator.client.get_status.assert_not_awaited()
    asyncio.run(run())


def test_confirmation_stops_followups_but_an_unrelated_pending_command_keeps_them(tmp_path):
    from dataclasses import replace

    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            clock = Clock()
            baseline = coordinator.data = replace(decode_status({}), steering_heat_on=False)
            coordinator.client.get_status.return_value = replace(baseline, steering_heat_on=True)
            with patch.object(coordinator, '_start_result_refresh'), clock_patch(clock), \
                    patch('custom_components.gac_connect.coordinator.monotonic', clock.monotonic):
                await async_send(coordinator, 'steering-on', AsyncMock(return_value=ACCEPTED)())
                await coordinator._result_refresh()
                assert coordinator.commands.state == 'confirmed'
                assert coordinator.client.get_status.await_count == 1
                await async_send(coordinator, 'horn-on', AsyncMock(return_value={'data': {'sessionId': 'horn'}})())
                await coordinator._result_refresh()
                assert coordinator.commands.state == 'pending'
                assert coordinator.client.get_status.await_count == 4
    asyncio.run(run())


def test_overlapping_status_requests_share_one_network_read(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            started, release = asyncio.Event(), asyncio.Event()
            report = decode_status({})
            async def fetch(_vin):
                started.set()
                await release.wait()
                return report
            c.client.get_status.side_effect = fetch
            first = asyncio.create_task(c._async_update_data())
            await started.wait()
            second = asyncio.create_task(c._async_update_data())
            await asyncio.sleep(0)
            release.set()
            assert await first is report and await second is report
            c.client.get_status.assert_awaited_once()
    asyncio.run(run())


@pytest.mark.parametrize('from_command', [False, True])
def test_cooldown_blocks_manual_and_background_reads_until_retry_time(tmp_path, from_command):
    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            clock = Clock()
            c.data = decode_status({})
            with patch('custom_components.gac_connect.coordinator.monotonic', clock.monotonic):
                error = RateLimitedError('wait', retry_after=120)
                if from_command:
                    with pytest.raises(RateLimitedError):
                        await async_send(c, 'lock', AsyncMock(side_effect=error)())
                else:
                    c.client.get_status.side_effect = error
                    await c.async_refresh()
                attempts = c.client.get_status.await_count
                last_success = c.last_refresh_success
                for now in (1, 30, 119):
                    clock.now = now
                    c._force_refresh = True
                    await c.async_refresh()
                    c.async_schedule_command_refresh()
                    c._schedule_result_refresh()
                    assert c._refresh_deadlines == []
                assert c.last_refresh_success == last_success
                assert c.client.get_status.await_count == attempts
                assert c.polling_state == 'rate_limited' and c.retry_not_before is not None
                clock.now = 120
                c.client.get_status.side_effect = None
                await c.async_refresh()
                assert c.client.get_status.await_count == attempts + 1
                assert c.polling_state == 'ok' and c.retry_not_before is None
    asyncio.run(run())
