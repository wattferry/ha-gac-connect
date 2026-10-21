"""Verified power states and explicit shutdown permission across all HA entry points."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.binary_sensor import BINARY_SENSORS, GacBinaryEntity
from custom_components.gac_connect.button import BUTTONS, GacButtonEntity
from custom_components.gac_connect.config_flow import GacConfigFlow, GacOptionsFlow
from custom_components.gac_connect.const import CONF_ALLOW_VEHICLE_SHUTDOWN
from custom_components.gac_connect.entity_filter import apply_registry_choices
from test_autodetect import result, vehicle
from test_regressions import coord, service_registry


POWER = next(d for d in BINARY_SENSORS if d.key == 'vehicle_power')
SHUTDOWN = next(d for d in BUTTONS if d.key == 'vehicle_power_off')


@pytest.mark.parametrize('mode,expected', [(2, True), (0, False), (1, True), (-1, None), (None, None)])
def test_power_sensor_shows_only_the_reported_power_mode_in_sensors(mode, expected):
    c = coord(decode_status({'powerAccessors': [{'powerMode': mode}]}, online=True))
    sensor = GacBinaryEntity(c, POWER)
    assert sensor.is_on is expected
    assert sensor.entity_category is None and sensor.device_class is None
    assert sensor.unique_id == 'TESTVIN_vehicle_power'
    assert sensor.extra_state_attributes == {'power_mode': mode}
    assert c.data.online is True
    c.client.command.assert_not_awaited()
    c.data = None
    assert sensor.is_on is None and sensor.extra_state_attributes is None
    c.data = SimpleNamespace(online=True)  # a partial deployment with an older library
    assert sensor.is_on is None and sensor.extra_state_attributes == {'power_mode': None}


@pytest.mark.parametrize('allowed', [False, True])
@pytest.mark.parametrize('omitted', [False, True])
def test_shutdown_choice_controls_button_visibility_without_suppressing_power_sensor(tmp_path, allowed, omitted):
    async def run():
        from custom_components.gac_connect import binary_sensor, button
        options = {CONF_ALLOW_VEHICLE_SHUTDOWN: allowed,
                   'enable_entities': ['button:vehicle_power_off'],
                   'omit_entities': ['button:vehicle_power_off'] if omitted else []}
        async with vehicle(tmp_path, options=options) as (hass, entry, c):
            c.data = decode_status({'powerAccessors': [{'powerMode': 0}]})
            c.capabilities.observe(c.data)
            c.capabilities.confirm_command('vehicle-power-off')
            added = []
            for module in (binary_sensor, button):
                await module.async_setup_entry(hass, entry, lambda entities: added.extend(e.unique_id for e in entities))
            assert 'VIN_vehicle_power' in added
            assert ('VIN_vehicle_power_off' in added) is (allowed and not omitted)
            c.client.command.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('allowed', [None, False, 'true', 1])
@pytest.mark.parametrize('command', ['vehicle-power-off', 'power-off', 'powerkeep-stop'])
def test_service_shutdown_requires_the_separate_permission_even_when_always_shown(allowed, command):
    c = coord(decode_status({'powerAccessors': [{'powerMode': 2}]}))
    c.config_entry.options = {'enable_entities': ['button:vehicle_power_off']}
    if allowed is not None:
        c.config_entry.options[CONF_ALLOW_VEHICLE_SHUTDOWN] = allowed
    action = service_registry(c)['send_command'][0]
    with pytest.raises(ServiceValidationError, match='Allow remote vehicle shutdown'):
        asyncio.run(action(SimpleNamespace(data={'command': command})))
    c.client.command.assert_not_awaited()
    c.async_schedule_command_refresh.assert_not_called()
    assert c.data.power_on is True


def test_shutdown_tracks_fresh_power_off_without_optimistic_sensor_changes_and_can_be_revoked(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_VEHICLE_SHUTDOWN: True}) as (hass, entry, c):
            c.data = decode_status({'powerAccessors': [{'powerMode': 2}]}, updated_ms=100, online=True)
            sensor, button = GacBinaryEntity(c, POWER), GacButtonEntity(c, SHUTDOWN)
            await button.async_press()
            c.client.command.assert_awaited_once_with('VIN', 'vehicle-power-off')
            assert sensor.is_on is True and c.commands.state == 'pending'
            c.commands.result(result())
            assert c.commands.state == 'awaiting_report'
            for report in (
                decode_status({'powerAccessors': [{'powerMode': 0}]}, updated_ms=99),
                decode_status({'powerAccessors': [{'powerMode': 1}]}, updated_ms=200),
                decode_status({'airConditionAccessors': [{'windStrength': 0, 'enableAirCompressor': 0}]}, updated_ms=200),
            ):
                c.commands.observe(report)
                assert c.commands.state == 'awaiting_report'
            c.data = decode_status({'powerAccessors': [{'powerMode': 0}]}, updated_ms=200, online=True)
            c.commands.observe(c.data)
            assert c.commands.state == 'confirmed' and sensor.is_on is False
            assert c.data.online is True
            hass.config_entries.async_update_entry(entry, options={CONF_ALLOW_VEHICLE_SHUTDOWN: False})
            with pytest.raises(ServiceValidationError):
                await button.async_press()  # an already-created entity cannot bypass a revoked setting
            assert c.client.command.await_count == 1
            assert len(c.commands.records) == 1
    asyncio.run(run())


def test_disabling_shutdown_preserves_its_registry_id_for_reenable(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            registry = er.async_get(hass)
            record = registry.async_get_or_create('button', 'gac_connect', 'VIN_vehicle_power_off')
            for allowed in (False, True, False, True):
                hass.config_entries.async_update_entry(entry, options={CONF_ALLOW_VEHICLE_SHUTDOWN: allowed})
                apply_registry_choices(hass, entry)
                current = registry.async_get(record.entity_id)
                assert current is not None and current.id == record.id
                assert current.disabled_by is (None if allowed else er.RegistryEntryDisabler.INTEGRATION)
            c.client.command.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('allowed', [False, True])
def test_setup_and_options_save_the_shutdown_permission(tmp_path, allowed):
    async def run():
        flow = GacConfigFlow()
        async with vehicle(tmp_path) as (hass, entry, c):
            flow.hass = hass
            flow._vehicle = SimpleNamespace(vin='VIN', model='Aion UT')
            flow._client = SimpleNamespace(session=SimpleNamespace(to_dict=Mock(return_value={})))
            form = await flow.async_step_remote_controls()
            defaults = form['data_schema']({})
            assert defaults[CONF_ALLOW_VEHICLE_SHUTDOWN] is False
            await flow.async_step_remote_controls({**defaults, CONF_ALLOW_VEHICLE_SHUTDOWN: allowed})
            created = await flow.async_step_cards({'dashboard_cards': []})
            assert created['options'][CONF_ALLOW_VEHICLE_SHUTDOWN] is allowed
            options_flow = GacOptionsFlow()
            options_flow.hass, options_flow.handler = hass, entry.entry_id
            form = await options_flow.async_step_settings()
            assert form['data_schema']({})[CONF_ALLOW_VEHICLE_SHUTDOWN] is False
            await options_flow.async_step_settings({CONF_ALLOW_VEHICLE_SHUTDOWN: allowed})
            assert entry.options[CONF_ALLOW_VEHICLE_SHUTDOWN] is allowed
            await options_flow.async_step_settings({'scan_interval': 120})
            assert entry.options[CONF_ALLOW_VEHICLE_SHUTDOWN] is allowed
            c.client.command.assert_not_awaited()
    asyncio.run(run())
