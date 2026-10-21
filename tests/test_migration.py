"""Older entries drop retired settings and keep the owner's own choices."""
import asyncio

import pytest

from custom_components.gac_connect import _UT_PROFILE_OMISSIONS, async_migrate_entry
from custom_components.gac_connect.capabilities import FRIDGE_ENTITIES
from test_autodetect import vehicle


@pytest.mark.parametrize("stored_profile", [None, "aion_ut"])
def test_aion_ut_entries_lose_only_the_preset_omissions(tmp_path, stored_profile):
    async def run():
        options = {"omit_entities": sorted(_UT_PROFILE_OMISSIONS | {"sensor:pm25"}), "enable_fridge": False,
                   "enable_tracker": False, "experimental_pinless_unlock": True}
        if stored_profile:
            options["profile"] = stored_profile
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, options=options, minor_version=1)
            assert await async_migrate_entry(hass, entry)
            assert entry.minor_version == 8 and "profile" not in entry.options
            assert entry.options["omit_entities"] == ["sensor:pm25"]      # the preset's fridge Off is not the owner's
            assert "enable_fridge" not in entry.options
            assert entry.options["enable_tracker"] is False and entry.options["experimental_pinless_unlock"] is True
            assert len([key for key in _UT_PROFILE_OMISSIONS if key.startswith("sensor:tyre_")]) == 8
    asyncio.run(run())


@pytest.mark.parametrize("profile", ["custom", "aion_v", "auto_detect"])
def test_other_profiles_keep_every_choice(tmp_path, profile):
    async def run():
        options = {"profile": profile, "omit_entities": ["cover:sunroof", "sensor:tyre_1_temp"], "enable_fridge": False}
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, options=options, minor_version=1)
            assert await async_migrate_entry(hass, entry)
            assert entry.options == {"omit_entities": sorted({"cover:sunroof", "sensor:tyre_1_temp", *FRIDGE_ENTITIES}),
                                     "dashboard_cards": [], "load_cards": False}
    asyncio.run(run())


def test_migration_runs_once(tmp_path):
    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, options={"omit_entities": ["cover:sunroof"]}, minor_version=2)
            assert await async_migrate_entry(hass, entry)
            assert entry.options["omit_entities"] == ["cover:sunroof"]   # a later Omit choice stays
    asyncio.run(run())


@pytest.mark.parametrize("object_id,expected", [
    ("aion_ut_unrestricted_charging", "switch.aion_ut_scheduled_charging"),
    ("my_charge_gate", "switch.my_charge_gate"),                     # a custom ID stays
    ("garage_unrestricted_charging", "switch.garage_unrestricted_charging"),   # even one ending the same way
])
def test_the_charge_switch_entity_id_follows_its_new_meaning(tmp_path, object_id, expected):
    from homeassistant.helpers import entity_registry as er

    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            registry = er.async_get(hass)
            registry.async_get_or_create("switch", "gac_connect", "VIN_charge_switch", suggested_object_id=object_id,
                                         config_entry=entry, device_id=_car(hass, entry))
            hass.config_entries.async_update_entry(entry, minor_version=2)
            assert await async_migrate_entry(hass, entry)
            assert registry.async_get_entity_id("switch", "gac_connect", "VIN_charge_switch") == expected
            assert entry.minor_version == 8
    asyncio.run(run())



@pytest.mark.parametrize("object_id,expected", [
    ("aion_ut_battery_preconditioning", "switch.aion_ut_smart_battery_temp"),
    ("warm_the_pack", "switch.warm_the_pack"),                       # a custom ID stays
])
def test_the_smart_battery_temp_entity_id_follows_its_new_name(tmp_path, object_id, expected):
    from homeassistant.helpers import entity_registry as er

    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            registry = er.async_get(hass)
            registry.async_get_or_create("switch", "gac_connect", "VIN_precondition_battery", suggested_object_id=object_id,
                                         config_entry=entry, device_id=_car(hass, entry))
            hass.config_entries.async_update_entry(entry, minor_version=4)
            assert await async_migrate_entry(hass, entry)
            assert registry.async_get_entity_id("switch", "gac_connect", "VIN_precondition_battery") == expected
            assert entry.minor_version == 8
    asyncio.run(run())


@pytest.mark.parametrize("object_id,expected", [
    ("aion_ut_pre_conditioning", "switch.aion_ut_a_c"),
    ("cabin_cooling", "switch.cabin_cooling"),                       # a custom ID stays
    ("my_custom_garage_pre_conditioning", "switch.my_custom_garage_pre_conditioning"),
])
def test_the_a_c_entity_id_follows_its_new_name(tmp_path, object_id, expected):
    from homeassistant.helpers import entity_registry as er

    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            registry = er.async_get(hass)
            registry.async_get_or_create("switch", "gac_connect", "VIN_climate_power", suggested_object_id=object_id,
                                         config_entry=entry, device_id=_car(hass, entry))
            hass.config_entries.async_update_entry(entry, minor_version=5)
            assert await async_migrate_entry(hass, entry)
            assert registry.async_get_entity_id("switch", "gac_connect", "VIN_climate_power") == expected
            assert entry.minor_version == 8
    asyncio.run(run())

def test_the_charge_switch_rename_never_takes_an_existing_id(tmp_path):
    from homeassistant.helpers import entity_registry as er

    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            registry = er.async_get(hass)
            registry.async_get_or_create("switch", "other", "x", suggested_object_id="aion_ut_scheduled_charging")
            registry.async_get_or_create("switch", "gac_connect", "VIN_charge_switch",
                                         suggested_object_id="aion_ut_unrestricted_charging", config_entry=entry)
            hass.config_entries.async_update_entry(entry, minor_version=2)
            assert await async_migrate_entry(hass, entry)
            assert registry.async_get_entity_id("switch", "gac_connect", "VIN_charge_switch") == \
                "switch.aion_ut_unrestricted_charging"
    asyncio.run(run())


def _car(hass, entry):
    from homeassistant.helpers import device_registry as dr

    return dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={("gac_connect", "VIN")},
                                                  name="AION UT").id


def test_existing_cars_get_the_cards_but_no_dashboard_they_did_not_ask_for(tmp_path):
    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, options={"scan_interval": 120}, minor_version=6)
            assert await async_migrate_entry(hass, entry)
            assert entry.minor_version == 8
            assert entry.options == {"scan_interval": 120, "dashboard_cards": [], "load_cards": False}
            hass.config_entries.async_update_entry(entry, options={"dashboard_cards": ["vehicle"]}, minor_version=6)
            assert await async_migrate_entry(hass, entry)
            assert entry.options == {"dashboard_cards": ["vehicle"], "load_cards": False}
    asyncio.run(run())


def test_cars_that_had_the_cards_keep_them_and_older_ones_get_none_until_chosen(tmp_path):
    async def run():
        async with vehicle(tmp_path, model="Aion UT") as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, options={"dashboard_cards": ["vehicle"]}, minor_version=7)
            assert await async_migrate_entry(hass, entry)
            assert entry.minor_version == 8 and entry.options == {"dashboard_cards": ["vehicle"], "load_cards": True}
            hass.config_entries.async_update_entry(entry, options={"dashboard_cards": [], "load_cards": False},
                                                   minor_version=7)
            assert await async_migrate_entry(hass, entry)
            assert entry.options["load_cards"] is False       # the owner's own choice stays
    asyncio.run(run())
