"""The whole entry lifecycle through Home Assistant's own loader: set-up, option change, reload,
failed set-up, unload and removal. Only the GAC client is replaced."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from homeassistant import loader
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from gac_connect.errors import GacError
from custom_components.gac_connect.api import decode_status

REPO = Path(__file__).resolve().parents[1]
CAPABILITIES = json.loads((REPO / "tests/fixtures/ut_capabilities.json").read_text())
REPORT = {"drivingOverviewAccessors": [{"remainElectricityPercentage": 0.62, "remainVoyageCourse": 280}],
          "chargerAccessors": [{"plug": 0, "lock": 1}],
          "doorAccessors": [{"door": n, "lock": 0, "openMode": 0} for n in (1, 2, 3, 4)]}


def fake_client(load_error=None):
    client = Mock()
    client.timezone = "Asia/Bangkok"
    client.load = AsyncMock(side_effect=load_error)
    client.get_status = AsyncMock(return_value=decode_status(REPORT, online=True, updated_ms=1792200000000))
    client.get_control_capabilities = AsyncMock(return_value=CAPABILITIES)
    client.mqtt_info = AsyncMock(side_effect=GacError("no push in tests"))
    client.get_alarms = AsyncMock(return_value={"list": []})
    return client


async def home_assistant(tmp_path):
    (tmp_path / "custom_components").symlink_to(REPO / "custom_components")
    hass = HomeAssistant(str(tmp_path))
    hass.config.time_zone = "Asia/Bangkok"
    loader.async_setup(hass)
    if hasattr(dr, "async_setup"):
        dr.async_setup(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    return hass


def entry():
    import inspect

    params = dict(version=1, minor_version=6, domain="gac_connect", title="AION UT",
                  data={"region": "TH", "vin": "VIN", "model": "Aion UT", "mobile": "0812345678"},
                  options={"scan_interval": 300}, source="user", unique_id="VIN", discovery_keys={},
                  subentries_data=[])
    return ConfigEntry(**{k: v for k, v in params.items() if k in inspect.signature(ConfigEntry).parameters})


async def stop(hass):
    """Shut the instance down for real. It was never started, and a plain stop returns at
    once then, so force it; final writes run and the state must reach STOPPED."""
    from homeassistant.core import CoreState

    await hass.async_stop(force=True)
    assert hass.state is CoreState.stopped


def offline(client):
    """Only the network side is replaced: the client and its HTTP session."""
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch("custom_components.gac_connect.async_build_client", AsyncMock(return_value=client)))
    stack.enter_context(patch("custom_components.gac_connect.async_create_clientsession", Mock()))
    return stack


def test_the_whole_entry_lifecycle(tmp_path):
    async def run():
        hass = await home_assistant(tmp_path)
        car = entry()
        client = fake_client()
        with offline(client):
            await hass.config_entries.async_add(car)
            await hass.async_block_till_done()
            assert car.state is ConfigEntryState.LOADED
            states = {s.entity_id: s.state for s in hass.states.async_all() if "aion_ut" in s.entity_id}
            assert states["sensor.aion_ut_battery"] == "62.0" and states["lock.aion_ut_doors"] == "locked"
            assert len(states) > 40
            assert hass.services.has_service("gac_connect", "set_entity_visibility")

            # A live option applies without a reload; one that changes the entities reloads.
            hass.config_entries.async_update_entry(car, options={**car.options, "scan_interval": 120})
            await hass.async_block_till_done()
            assert car.runtime_data.coordinator.update_interval.total_seconds() == 120
            first_runtime = car.runtime_data
            hass.config_entries.async_update_entry(car, options={**car.options, "omit_entities": ["sensor:pm25"]})
            await hass.async_block_till_done()
            assert car.state is ConfigEntryState.LOADED and car.runtime_data is not first_runtime

            assert await hass.config_entries.async_unload(car.entry_id)
            assert car.state is ConfigEntryState.NOT_LOADED
            assert all(s.state == "unavailable" for s in hass.states.async_all() if "aion_ut" in s.entity_id)

        # A set-up that fails is retried later.
        with offline(fake_client(load_error=GacError("credentials unreadable"))):
            await hass.config_entries.async_reload(car.entry_id)
            await hass.async_block_till_done()
            assert car.state is ConfigEntryState.SETUP_RETRY

        # Every file the entry owns exists before removal and is gone after it.
        from homeassistant.helpers.storage import Store

        from custom_components.gac_connect.account_alerts import store_key as alerts_key
        from custom_components.gac_connect.capabilities import store_key as capabilities_key
        from custom_components.gac_connect.fridge import store_key as fridge_key
        from custom_components.gac_connect.session_store import session_path

        owned = [tmp_path / ".storage" / key(car.entry_id) for key in (alerts_key, capabilities_key, fridge_key)]
        for path in owned:
            await Store(hass, 1, path.name).async_save({"seeded": True})
        credentials = session_path(hass, car.entry_id)
        credentials.write_text('{"version": 1, "data": {}}')
        owned.append(credentials)
        assert all(path.exists() for path in owned)
        with offline(client):
            await hass.config_entries.async_remove(car.entry_id)
            await hass.async_block_till_done()
        assert [path.name for path in owned if path.exists()] == []
        await stop(hass)
    asyncio.run(run())


def test_saved_request_limits_are_restored_once_and_a_corrupt_record_pauses(tmp_path):
    import time

    from homeassistant.helpers.storage import Store

    from custom_components.gac_connect import helpers
    from gac_connect.limits import DEFAULT_LIMITER

    async def run():
        for saved, paused in (({"sent": [], "commands": [], "blocked_until": time.time() + 120, "last_done": 0}, True),
                              ({"sent": "corrupt"}, True), (None, False)):
            hass = HomeAssistant(str(tmp_path / str(len(str(saved)))))
            if saved is not None:
                await Store(hass, 1, helpers.LIMITS_KEY).async_save(saved)
            DEFAULT_LIMITER._blocked_until = 0.0
            await asyncio.gather(helpers.async_setup_limits(hass), helpers.async_setup_limits(hass))
            assert (DEFAULT_LIMITER._blocked_until > time.monotonic()) is paused
            assert DEFAULT_LIMITER.state_path is None and DEFAULT_LIMITER.on_change is not None
            DEFAULT_LIMITER._blocked_until = 0.0
            await stop(hass)
    asyncio.run(run())


def test_turning_moving_tracking_off_hides_the_position_at_once(tmp_path):
    async def run():
        hass = await home_assistant(tmp_path)
        car = entry()
        car = ConfigEntry(**{**{k: getattr(car, k) for k in ("version", "minor_version", "domain", "title", "data",
                                                               "source", "unique_id")},
                             "options": {"scan_interval": 300, "track_parked": True, "track_moving": True,
                                         "enable_tracker": True},
                             **{k: v for k, v in {"discovery_keys": {}, "subentries_data": []}.items()
                                if k in __import__("inspect").signature(ConfigEntry).parameters}})
        client = fake_client()
        moving = dict(REPORT, powerAccessors=[{"powerMode": 2}],
                      positionAccessors=[{"latitude": 13.7, "longitude": 100.5}])
        client.get_status = AsyncMock(return_value=decode_status(moving, online=True, updated_ms=1792200000000))
        with offline(client):
            await hass.config_entries.async_add(car)
            await hass.async_block_till_done()
            tracker = next(s for s in hass.states.async_all("device_tracker") if "aion_ut" in s.entity_id)
            assert tracker.attributes.get("latitude") == 13.7
            hass.config_entries.async_update_entry(car, options={**car.options, "track_moving": False})
            await hass.async_block_till_done()
            tracker = hass.states.get(tracker.entity_id)
            assert tracker.attributes.get("latitude") is None
            assert await hass.config_entries.async_unload(car.entry_id)
        await stop(hass)
    asyncio.run(run())
