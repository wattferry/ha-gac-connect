"""Vehicle report time and cloud request success are different facts."""
import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from custom_components.gac_connect.api import decode_status
from gac_connect.errors import GacError, RateLimitedError
from custom_components.gac_connect.sensor import ACTIVITY_SENSORS, GacActivitySensor
from test_autodetect import vehicle


def test_cloud_success_does_not_make_an_old_vehicle_report_fresh(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            now = datetime(2026, 10, 11, tzinfo=UTC)
            old = replace(decode_status({}), updated_ms=int((now - timedelta(hours=1)).timestamp() * 1000))
            coordinator.client.get_status.return_value = old
            with patch('custom_components.gac_connect.coordinator.dt_util.utcnow', return_value=now) as utc_clock:
                await coordinator.async_refresh()
                assert coordinator.last_refresh_success == now
                assert coordinator.freshness == 'stale'
                assert coordinator.report_age == 3600
                utc_clock.return_value = now + timedelta(seconds=30)
                for error, state in [(RateLimitedError('wait'), 'rate_limited'), (GacError('offline'), 'error')]:
                    coordinator._rate_limit_until = float('-inf')  # simulate the previous cooldown having elapsed
                    coordinator.client.get_status.side_effect = error
                    await coordinator.async_refresh()
                    assert coordinator.last_refresh_success == now
                    assert coordinator.polling_state == state
                    sensor = GacActivitySensor(coordinator, next(d for d in ACTIVITY_SENSORS if d.key == 'polling_status'))
                    assert sensor.available and sensor.native_value == state
    asyncio.run(run())


def test_display_ages_without_network_and_stops_on_unload(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, coordinator):
            now = datetime(2026, 10, 11, tzinfo=UTC)
            with patch('custom_components.gac_connect.coordinator.dt_util.utcnow', return_value=now):
                coordinator.data = decode_status({})
                assert coordinator.freshness == 'not_reported'
                coordinator.data = replace(coordinator.data, updated_ms=int(now.timestamp() * 1000))
                assert coordinator.freshness == 'recent'
                coordinator.data = replace(coordinator.data, updated_ms=int((now + timedelta(minutes=2)).timestamp() * 1000))
                assert coordinator.freshness == 'clock_mismatch'
                coordinator.data = replace(coordinator.data, updated_ms=int((now - timedelta(seconds=601)).timestamp() * 1000))
                assert coordinator.freshness == 'stale'
                coordinator.update_interval = timedelta(minutes=10)
                assert coordinator.freshness == 'recent'
                with patch.object(coordinator, '_in_quiet_hours', return_value=True):
                    await coordinator.async_refresh()
                    assert coordinator.polling_state == 'quiet_hours'
                    assert coordinator.last_refresh_success is None
                with patch.object(coordinator, 'async_update_listeners') as notify:
                    coordinator._freshness_tick(now)
                    notify.assert_called_once()
                coordinator.client.get_status.assert_not_awaited()
                cancel = coordinator._freshness_timer
                coordinator._freshness_timer = Mock(wraps=cancel)
                await entry._async_process_on_unload(hass)
                assert coordinator._freshness_timer is None
    asyncio.run(run())
