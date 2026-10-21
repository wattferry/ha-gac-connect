"""Every vehicle polls from one shared request budget, so more vehicles poll less often."""
import asyncio
import inspect
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry, ConfigEntryDisabler

from custom_components.gac_connect.coordinator import SECONDS_PER_VEHICLE_POLL
from test_autodetect import vehicle


def add_vehicle(hass, vin, *, disabled=False):
    params = dict(version=1, minor_version=1, domain="gac_connect", title=vin, data={"vin": vin}, options={},
                  source="user", unique_id=vin, discovery_keys={}, subentries_data=[],
                  disabled_by=ConfigEntryDisabler.USER if disabled else None)
    entry = ConfigEntry(**{k: v for k, v in params.items() if k in inspect.signature(ConfigEntry).parameters})
    hass.config_entries._entries[entry.entry_id] = entry


def test_polling_stretches_so_all_vehicles_fit_the_shared_budget(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={"scan_interval": 60}) as (hass, _, c):
            assert SECONDS_PER_VEHICLE_POLL == 36   # 3000 a day, 80% of it for polls
            assert c._shared_interval() == timedelta(seconds=60)
            add_vehicle(hass, "VIN2")
            assert c._shared_interval() == timedelta(seconds=72)
            add_vehicle(hass, "VIN3")
            add_vehicle(hass, "VIN4", disabled=True)    # a disabled vehicle does not poll
            assert c._shared_interval() == timedelta(seconds=108)
            cancel = c.async_add_listener(lambda: None)
            try:
                c._schedule_refresh()
                assert c.update_interval == timedelta(seconds=108)
            finally:
                cancel()
    asyncio.run(run())


def test_a_longer_chosen_interval_is_kept(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={"scan_interval": 600}) as (hass, _, c):
            for vin in ("VIN2", "VIN3"):
                add_vehicle(hass, vin)
            assert c._shared_interval() == timedelta(seconds=600)
    asyncio.run(run())
