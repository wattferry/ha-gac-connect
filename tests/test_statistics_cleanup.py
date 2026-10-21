"""Removal behavior against real HA registries and temporary recorder databases."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import func, select

from homeassistant import loader
from homeassistant.components.recorder import models
from homeassistant.components.recorder.db_schema import Statistics, StatisticsMeta, StatisticsShortTerm
from homeassistant.components.recorder.tasks import SynchronizeTask
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er, recorder as recorder_helper
from homeassistant.helpers.recorder import DATA_INSTANCE, get_instance
from homeassistant.setup import async_setup_component

from custom_components.gac_connect import async_setup, async_unload_entry
from custom_components.gac_connect.const import DOMAIN
from custom_components.gac_connect.entity_filter import apply_registry_choices
from custom_components.gac_connect.statistics import async_setup_cleanup
from test_session_store import make_entry


@asynccontextmanager
async def recorded_vehicle(tmp_path, *, cleanup=True, recorder=True):
    hass = HomeAssistant(str(tmp_path))
    entry = make_entry(hass, {"vin": "VIN", "model": "Aion V", "region": "AU"})
    hass.config_entries._store = Mock()
    loader.async_setup(hass)
    hass.config.skip_pip = True  # Tests never install dependencies or use a live HA database.
    if hasattr(dr, "async_setup"):
        dr.async_setup(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    try:
        if recorder:
            recorder_helper.async_initialize_recorder(hass)
            assert await async_setup_component(hass, "recorder", {"recorder": {
                "db_url": f"sqlite:///{tmp_path / 'recorder-test.db'}",
                "auto_purge": False, "auto_repack": False,
            }})
        await hass.async_start()
        if recorder:
            await get_instance(hass).async_recorder_ready.wait()
        if cleanup:
            assert await async_setup(hass, {})
        yield hass, entry, er.async_get(hass)
    finally:
        await hass.async_stop()
        # HA's process-wide helpers otherwise retain the stopped test instance.
        get_instance.cache_clear()
        er.async_get.cache_clear()


def sensor(registry, entry, key, **kwargs):
    return registry.async_get_or_create("sensor", DOMAIN, f"{entry.data['vin']}_{key}",
                                        config_entry=entry, suggested_object_id=key, **kwargs)


async def seed_statistics(hass, entity_ids):
    instance = get_instance(hass)
    for entity_id in entity_ids:
        metadata = {"statistic_id": entity_id, "source": "recorder", "name": None,
                    "unit_of_measurement": "%", "has_sum": True}
        if "mean_type" in models.StatisticMetaData.__annotations__:
            metadata.update(mean_type=models.StatisticMeanType.NONE, unit_class=None)
        else:
            metadata["has_mean"] = False
        for table in (Statistics, StatisticsShortTerm):
            instance.async_import_statistics(metadata.copy(), [{
                "start": datetime(2026, 10, 1, tzinfo=UTC), "sum": 40.0, "state": 40.0,
            }], table)
    await assert_statistics(hass, entity_ids)


async def assert_statistics(hass, entity_ids):
    instance = get_instance(hass)
    await hass.async_block_till_done()
    # Always queue a barrier: async_block_till_done can return early when the
    # queue is empty but a statistics task is still executing in Recorder.
    if "future" in SynchronizeTask.__dataclass_fields__:
        done = hass.loop.create_future()
        instance.queue_task(SynchronizeTask(done))
        await done
    else:
        done = asyncio.Event()
        instance.queue_task(SynchronizeTask(done))
        await done.wait()

    def read():
        with instance.get_session() as session:
            return (
                set(session.scalars(select(StatisticsMeta.statistic_id))),
                session.scalar(select(func.count()).select_from(Statistics)),
                session.scalar(select(func.count()).select_from(StatisticsShortTerm)),
            )

    # Check both tables too: deleting metadata alone must not leave orphan rows.
    assert await instance.async_add_executor_job(read) == (set(entity_ids), len(entity_ids), len(entity_ids))


@pytest.mark.parametrize("state", ["active", "disabled", "renamed", "registered_before_setup"])
def test_deleting_one_sensor_clears_only_its_statistics(tmp_path, state):
    async def run():
        async with recorded_vehicle(tmp_path, cleanup=state != "registered_before_setup") as (hass, entry, registry):
            removed = sensor(registry, entry, "soc")
            retained = sensor(registry, entry, "range")
            foreign = registry.async_get_or_create("sensor", "other_integration", "VIN_soc",
                                                   suggested_object_id="gac_connect_battery")
            await seed_statistics(hass, {removed.entity_id, retained.entity_id, foreign.entity_id})
            if state == "disabled":
                registry.async_update_entity(removed.entity_id, disabled_by=er.RegistryEntryDisabler.USER)
            elif state == "renamed":
                removed = registry.async_update_entity(removed.entity_id, new_entity_id="sensor.my_car_battery")
            elif state == "registered_before_setup":
                assert await async_setup(hass, {})
            await assert_statistics(hass, {removed.entity_id, retained.entity_id, foreign.entity_id})
            registry.async_remove(removed.entity_id)
            await assert_statistics(hass, {retained.entity_id, foreign.entity_id})

    asyncio.run(run())


@pytest.mark.parametrize("cleanup_loaded", [False, True])
def test_removing_whole_entry_clears_disabled_and_renamed_sensors(tmp_path, cleanup_loaded):
    async def run():
        async with recorded_vehicle(tmp_path, cleanup=cleanup_loaded) as (hass, entry, registry):
            removed = sensor(registry, entry, "soc", disabled_by=er.RegistryEntryDisabler.USER)
            renamed = sensor(registry, entry, "odometer")
            renamed = registry.async_update_entity(renamed.entity_id, new_entity_id="sensor.renamed_car_distance")
            other_entry = make_entry(hass, {"vin": "OTHER", "model": "Aion V"})
            hass.config_entries._entries[entry.entry_id] = entry
            hass.config_entries._store = Mock()
            retained = sensor(registry, other_entry, "soc")
            await seed_statistics(hass, {removed.entity_id, renamed.entity_id, retained.entity_id})

            # Exercise HA's actual removal order, including an entry that never
            # loaded successfully and therefore has no runtime_data.
            result = await hass.config_entries.async_remove(entry.entry_id)
            assert result == {"require_restart": False}
            assert registry.async_get(removed.entity_id) is None
            assert registry.async_get(renamed.entity_id) is None
            assert registry.async_get(retained.entity_id) is not None
            await assert_statistics(hass, {retained.entity_id})

    asyncio.run(run())


@pytest.mark.parametrize("registered", [False, True])
def test_entry_cleanup_includes_older_deletions_but_protects_reused_ids(tmp_path, registered):
    async def run():
        async with recorded_vehicle(tmp_path, cleanup=False) as (hass, entry, registry):
            orphan = sensor(registry, entry, "range")
            reused = sensor(registry, entry, "soc")
            registry.async_remove(orphan.entity_id)
            registry.async_remove(reused.entity_id)
            await hass.async_block_till_done()
            if registered:
                foreign = registry.async_get_or_create("sensor", "other_integration", "NEW",
                                                       suggested_object_id="soc")
                assert foreign.entity_id == reused.entity_id
            else:
                # YAML sensors can exist without a unique ID or registry entry.
                hass.states.async_set(reused.entity_id, "42")
            await seed_statistics(hass, {orphan.entity_id, reused.entity_id})

            await hass.config_entries.async_remove(entry.entry_id)
            await assert_statistics(hass, {reused.entity_id})

    asyncio.run(run())


def test_removing_a_device_clears_its_sensors_statistics(tmp_path):
    async def run():
        async with recorded_vehicle(tmp_path) as (hass, entry, registry):
            devices = dr.async_get(hass)
            device = devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "VIN")})
            removed = sensor(registry, entry, "soc", device_id=device.id)
            retained = sensor(registry, entry, "range")
            await seed_statistics(hass, {removed.entity_id, retained.entity_id})
            devices.async_remove_device(device.id)
            await hass.async_block_till_done()
            assert registry.async_get(removed.entity_id) is None
            await assert_statistics(hass, {retained.entity_id})

    asyncio.run(run())


def test_normal_shutdown_preserves_statistics(tmp_path):
    async def run():
        async with recorded_vehicle(tmp_path) as (hass, entry, registry):
            retained = sensor(registry, entry, "soc")
            await seed_statistics(hass, {retained.entity_id})
        # Read the closed test database: stopping HA must not erase statistics.
        with sqlite3.connect(tmp_path / "recorder-test.db") as connection:
            assert connection.execute("SELECT statistic_id FROM statistics_meta").fetchall() == [(retained.entity_id,)]
            for table in ("statistics", "statistics_short_term"):
                assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (1,)

    asyncio.run(run())


def test_a_registry_removal_also_cleans_up_sensor_statistics(tmp_path):
    async def run():
        async with recorded_vehicle(tmp_path) as (hass, entry, registry):
            removed = sensor(registry, entry, "fridge_time_left")
            retained = sensor(registry, entry, "soc")
            await seed_statistics(hass, {removed.entity_id, retained.entity_id})
            registry.async_remove(removed.entity_id)       # as a retired entity is removed at setup
            await assert_statistics(hass, {retained.entity_id})

    asyncio.run(run())


def test_omitting_hiding_unloading_and_reloading_preserve_statistics(tmp_path):
    async def run():
        async with recorded_vehicle(tmp_path) as (hass, entry, registry):
            retained = sensor(registry, entry, "soc")
            await seed_statistics(hass, {retained.entity_id})
            cleanup = async_setup_cleanup(hass)
            listeners = hass.bus.async_listeners()[er.EVENT_ENTITY_REGISTRY_UPDATED]
            hass.config_entries.async_update_entry(entry, options={"omit_entities": ["sensor:soc"]})
            apply_registry_choices(hass, entry)
            registry.async_update_entity(retained.entity_id, hidden_by=er.RegistryEntryHider.USER)
            entry.runtime_data = SimpleNamespace(coordinator=SimpleNamespace(
                capabilities=SimpleNamespace(async_close=AsyncMock())))
            with patch.object(hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)):
                assert await async_unload_entry(hass, entry)
            await entry._async_process_on_unload(hass)
            for _ in range(2):
                assert await async_setup(hass, {})
                assert async_setup_cleanup(hass) is cleanup
            assert hass.bus.async_listeners()[er.EVENT_ENTITY_REGISTRY_UPDATED] == listeners
            await assert_statistics(hass, {retained.entity_id})
            # Unloading must not leave a subsequently deleted, disabled sensor
            # without cleanup. Nor may a reload have installed duplicate listeners.
            with patch.object(get_instance(hass), "async_clear_statistics", wraps=get_instance(hass).async_clear_statistics) as clear:
                registry.async_remove(retained.entity_id)
                clear.assert_called_once_with([retained.entity_id])
            await assert_statistics(hass, set())

    asyncio.run(run())


def test_removal_without_recorder_still_succeeds_and_explains_cleanup_limit(tmp_path, caplog):
    async def run():
        async with recorded_vehicle(tmp_path, recorder=False) as (hass, entry, registry):
            removed = sensor(registry, entry, "soc")
            registry.async_remove(removed.entity_id)
            sensor(registry, entry, "range")
            await hass.config_entries.async_remove(entry.entry_id)
            assert DATA_INSTANCE not in hass.data
            assert "statistics" in caplog.text and "must be cleared manually" in caplog.text

    asyncio.run(run())
