"""Additional readings must remain read-only and respect location privacy."""
import asyncio
import importlib
import json
from unittest.mock import AsyncMock, Mock
from types import SimpleNamespace

import pytest
from homeassistant.components.device_tracker import SourceType

from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.binary_sensor import BINARY_SENSORS, GacBinaryEntity
from custom_components.gac_connect.device_tracker import GacDeviceTracker
from custom_components.gac_connect.climate import GacClimate
from custom_components.gac_connect.sensor import SENSORS, GacSensorEntity
from custom_components.gac_connect.switch import SWITCHES, GacCommandSwitch
from gac_connect.errors import CommandError, RateLimitedError
from custom_components.gac_connect.command_tracking import async_send
from custom_components.gac_connect.diagnostics import async_get_config_entry_diagnostics
from custom_components.gac_connect.charging import schedule_attributes
from custom_components.gac_connect.config_flow import GacOptionsFlow
from test_autodetect import vehicle
from test_regressions import coord


def test_gps_sensor_keeps_the_tracker_and_exposes_coordinate_attributes():
    status = decode_status({'positionAccessors': [{'latitude': 12.3456789, 'longitude': 98.7654321}]})
    c = coord(status)
    c.config_entry.options['enable_tracker'] = True   # an entry saved before the parked/moving split
    tracker = GacDeviceTracker(c)
    gps = GacSensorEntity(c, next(d for d in SENSORS if d.key == 'gps_coordinates'))
    assert tracker.source_type is SourceType.GPS
    assert tracker.entity_category is gps.entity_category is None  # both appear in Sensors
    assert tracker.unique_id == 'TESTVIN_location' and gps.unique_id == 'TESTVIN_gps_coordinates'
    assert tracker.latitude == 12.3456789 and tracker.longitude == 98.7654321
    assert gps.native_value == '12.345679, 98.765432'
    assert gps.extra_state_attributes == {'latitude': 12.3456789, 'longitude': 98.7654321}
    c.data = decode_status({'positionAccessors': [{'latitude': 12.3456789}]})
    assert gps.native_value is None


@pytest.mark.parametrize('enabled', [False, True])
def test_coordinate_and_tracker_entities_share_privacy_setting(tmp_path, enabled):
    async def run():
        async with vehicle(tmp_path, options={'enable_tracker': enabled}) as (hass, entry, c):
            added = []
            c.data = decode_status({'positionAccessors': [{'latitude': 12.3, 'longitude': 98.7}]})
            if c.capabilities:
                c.capabilities.observe(c.data)
            for platform in ('sensor', 'device_tracker'):
                await importlib.import_module(f'custom_components.gac_connect.{platform}').async_setup_entry(
                    hass, entry, lambda entities: added.extend(e.unique_id for e in entities))
            assert ('VIN_gps_coordinates' in added) is enabled
            assert ('VIN_location' in added) is enabled
            c.client.command.assert_not_awaited()
            diagnostics = await async_get_config_entry_diagnostics(hass, entry)
            assert '12.3' not in json.dumps(diagnostics)
            assert diagnostics['status_raw']['positionAccessors'][0]['latitude'] == '**REDACTED**'
    asyncio.run(run())


def test_seat_ventilation_and_anti_theft_expose_status_without_writable_entities():
    c = coord(decode_status({'seatTemperatureAccessors': [
        {'seat': 2, 'enableWind': 1, 'windStrength': 3, 'temperatureStrength': 0, 'temperatureMode': 0},
        {'seat': 1, 'enableWind': 0, 'windStrength': 0},
    ], 'antiTheftAccessors': [{'enable': 1}]}))
    seat = GacBinaryEntity(c, next(d for d in BINARY_SENSORS if d.key == 'seat_2_ventilation'))
    theft = GacBinaryEntity(c, next(d for d in BINARY_SENSORS if d.key == 'anti_theft'))
    assert seat.is_on is True and seat.extra_state_attributes['seat_id'] == '2'
    assert seat.extra_state_attributes['reported_wind_strength'] == 3
    assert seat.extra_state_attributes['reported_enable_wind'] == 1
    assert theft.is_on is True
    c.client.command.assert_not_awaited()


def test_unknown_seat_enable_code_is_exposed_without_inventing_smart_state():
    c = coord(decode_status({'seatTemperatureAccessors': [
        {'seat': 1, 'enableWind': 2, 'windStrength': 1, 'temperatureMode': 0},
    ]}))
    seat = GacBinaryEntity(c, next(d for d in BINARY_SENSORS if d.key == 'seat_1_ventilation'))
    assert seat.is_on is None
    assert seat.extra_state_attributes['reported_enable_wind'] == 2
    assert seat.extra_state_attributes['reported_wind_strength'] == 1
    assert seat.extra_state_attributes['reported_temperature_mode'] == 0
    c.client.command.assert_not_awaited()


@pytest.mark.parametrize('seat_id', [1, 2])
def test_seat_level_selects_send_levels_and_correlate_only_their_session(tmp_path, seat_id):
    from gac_connect.push import PushResult
    from custom_components.gac_connect.select import GacSeatVentilationSelect
    from homeassistant.exceptions import HomeAssistantError

    async def run():
        async with vehicle(tmp_path) as (hass, _, c):
            c.data = decode_status({'seatTemperatureAccessors': [{'seat': seat_id, 'enableWind': 1, 'windStrength': 0}]})
            c.client.set_seat_ventilation_level = AsyncMock(return_value={'code': 13001, 'data': {'sessionId': 's1'}})
            sel = GacSeatVentilationSelect(c, seat_id)
            sel.hass, sel.async_write_ha_state = hass, Mock()
            try:
                assert sel.current_option == 'off' and sel.options == ['off', 'low', 'medium', 'high']
                await sel.async_select_option('medium')
                c.client.set_seat_ventilation_level.assert_awaited_once_with('VIN', seat_id, 2)
                assert sel.current_option == 'medium'
                assert c.commands.records[-1].command == f'seat-{seat_id}-ventilation-on'
                sel._handle_result(PushResult(False, '13101', None, {}, event='control_seat_temperature'))
                sel._handle_result(PushResult(False, '13101', None, {}, session_id='other-seat'))
                assert sel.current_option == 'medium'
                sel._handle_result(PushResult(False, '13101', None, {}, session_id='s1'))
                assert sel.current_option == 'off'
                c.client.set_seat_ventilation_level.side_effect = CommandError('rejected')
                with pytest.raises(HomeAssistantError):
                    await sel.async_select_option('high')
                assert sel.current_option == 'off'
                c.client.set_seat_ventilation_level.side_effect = None
                await sel.async_select_option('high')
                c.data = decode_status({'seatTemperatureAccessors': [{'seat': seat_id, 'enableWind': 1, 'windStrength': 3}]})
                sel._handle_coordinator_update()
                assert sel._requested is None and sel.current_option == 'high'   # confirmed by the report
                await sel.async_select_option('off')
                assert c.client.set_seat_ventilation_level.await_args.args == ('VIN', seat_id, 0)
                assert c.commands.records[-1].command == f'seat-{seat_id}-ventilation-off'
            finally:
                sel._cancel_expiry()
    asyncio.run(run())


def test_seat_controls_require_manual_or_successful_command_evidence(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={'enable_entities': ['select:seat_1_ventilation']}) as (_, _, c):
            c.data = decode_status({'seatTemperatureAccessors': [
                {'seat': 1, 'enableWind': 0}, {'seat': 2, 'enableWind': 0},
            ]})
            c.capabilities.observe(c.data)
            assert c.capabilities.includes('select:seat_1_ventilation')
            assert not c.capabilities.includes('select:seat_2_ventilation')
            c.capabilities.confirm_command('seat-2-ventilation-on')
            assert c.capabilities.includes('select:seat_2_ventilation')
            assert all(not d.key.startswith('seat_') for d in SWITCHES)
            c.client.command.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('error,reason,code', [
    (CommandError('PRIVATE response', code=13101), 'gateway_rejected', '13101'),
    (CommandError('PRIVATE response', code='PRIVATE-TOKEN'), 'command_error', None),
    (RateLimitedError('PRIVATE response'), 'rate_limited', None),
])
def test_command_failures_keep_safe_reason_and_service_code(tmp_path, error, reason, code):
    async def run():
        async with vehicle(tmp_path) as (_, _, c):
            with pytest.raises(type(error)):
                await async_send(c, 'charge-window', AsyncMock(side_effect=error)())
            attrs = c.commands.attributes()
            assert attrs['failure_reason'] == reason and attrs['response_code'] == code
            assert attrs['recent_commands'][-1]['failure_reason'] == reason
            assert 'PRIVATE' not in json.dumps(attrs)
    asyncio.run(run())


def test_older_status_does_not_remove_climate_or_crash_the_charging_panel(tmp_path):
    """Reproduce the live partial-install failure with the older status schema."""
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            current = decode_status({'chargingAccessors': [{'chargingMode': 1,
                'dailyReservationStartTime': 79200000, 'dailyReservationStopTime': 21600000}],
                'airConditionAccessors': [{'temperature': 24, 'windStrength': 0, 'enableAirCompressor': 0}]})
            added_fields = {'outside_temp_c', 'ac_fan_strength', 'ac_auto_on', 'ac_compressor_on',
                            'ac_blowing_mode', 'ac_cycling_mode', 'seats', 'anti_theft_on',
                            'charge_end_type', 'charge_clock_consistent', 'charge_time_format'}
            c.data = SimpleNamespace(**{k: v for k, v in vars(current).items() if k not in added_fields})
            c.client.timezone = 'Asia/Bangkok'
            climate = GacClimate(c)
            assert climate.hvac_mode == 'off' and climate.target_temperature == 24
            assert climate.extra_state_attributes['reported_fan_strength'] is None
            for description in BINARY_SENSORS:
                entity = GacBinaryEntity(c, description)
                entity.is_on
                entity.extra_state_attributes
            for description in SENSORS:
                entity = GacSensorEntity(c, description)
                entity.native_value
                entity.extra_state_attributes
            assert schedule_attributes(c.data)['stopping_rule'] == 'Not reported'
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            result = await flow.async_step_charging()
            assert result['type'] == 'menu'
            assert '22:00' in result['description_placeholders']['schedule']
    asyncio.run(run())


def _windows(*open_positions, updated=1):
    return decode_status({"windowAccessors": [{"window": n, "openMode": int(n in open_positions)} for n in (1, 2, 3, 4)]},
                         updated_ms=updated)


def test_ventilation_is_on_only_once_started_until_a_window_closes(monkeypatch):
    # Aion UT, 2026-10-17: ventilation left all four windows reporting open, past the app's 5 minutes.
    from unittest.mock import AsyncMock, Mock

    monkeypatch.setattr("custom_components.gac_connect.requested.async_call_later", lambda *args: Mock())

    from custom_components.gac_connect.switch import SWITCHES, GacVentilationSwitch
    from test_regressions import ACCEPTED, coord

    c = coord(_windows())
    c.client.command = AsyncMock(return_value=ACCEPTED)
    sw = GacVentilationSwitch(c, next(d for d in SWITCHES if d.key == "ventilation"))
    sw.hass, sw.async_write_ha_state = Mock(), Mock()
    assert sw.assumed_state is False and sw.is_on is False
    c.data = _windows(1, 2, 3, 4, updated=1)                 # windows opened another way are not ventilation
    sw._handle_coordinator_update()
    assert sw.is_on is False
    asyncio.run(sw.async_turn_on())
    assert sw.is_on is True                                  # requested, until the report shows it
    c.data = _windows(1, 2, 3, 4, updated=2)
    sw._handle_coordinator_update()
    assert sw._requested is None and sw.is_on is True        # confirmed by the windows
    c.data = _windows(3, updated=3)                          # a window closed: ventilation has ended
    sw._handle_coordinator_update()
    assert sw.is_on is False
    c.data = _windows(1, 2, 3, 4, updated=4)                 # and opening them again does not restart it
    sw._handle_coordinator_update()
    assert sw.is_on is False
    asyncio.run(sw.async_turn_on())
    c.data = _windows(1, 2, 3, 4, updated=5)
    sw._handle_coordinator_update()
    assert sw.is_on is True
    asyncio.run(sw.async_turn_off())
    c.data = _windows(1, 2, 3, 4, updated=6)                 # turned off here: off, even before they close
    sw._handle_coordinator_update()
    assert sw.is_on is False


def _air(cycling, running, updated):
    return decode_status({'airConditionAccessors': [{'cyclingMode': cycling, 'windStrength': 3 if running else 0,
                                                     'enableAirCompressor': int(running), 'temperature': 23}]},
                         updated_ms=updated)


def test_recirculation_while_ac_runs_is_sent_at_once_through_the_shared_cabin_queue(tmp_path):
    from custom_components.gac_connect import cabin
    from custom_components.gac_connect.switch import GacRecirculationSwitch

    async def run():
        async with vehicle(tmp_path) as (_, entry, c):
            c.client.climate_manual_on = AsyncMock(return_value={'code': 13001, 'data': {'sessionId': 'r1'}})
            c.data = _air(1, True, 1)
            cabin.controller(c).async_setup(entry)
            sw = GacRecirculationSwitch(c)
            sw.async_write_ha_state = Mock()
            assert sw.is_on is True and sw.extra_state_attributes == {'reported_cycling_mode': 1}
            await sw.async_turn_off()
            kwargs = c.client.climate_manual_on.await_args.kwargs
            assert kwargs['cycling_mode'] == 2 and kwargs['temperature'] == 23 and kwargs['fan_speed'] is None
            assert sw.is_on is False                       # the pending selection shows at once
            c.data = _air(2, True, 2)
            cabin.controller(c).sync()
            assert sw.is_on is False and cabin.controller(c)._req is None   # confirmed by the report
    asyncio.run(run())


def test_recirculation_shows_the_report_and_is_refused_while_ac_is_off(tmp_path):
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.gac_connect import cabin
    from custom_components.gac_connect.switch import GacClimateSwitch, GacRecirculationSwitch

    async def run():
        async with vehicle(tmp_path) as (_, entry, c):
            c.client.climate_manual_on = AsyncMock(return_value={'code': 13001, 'data': {'sessionId': 'r1'}})
            c.data = _air(1, False, 1)
            cabin.controller(c).async_setup(entry)
            recirculation, climate = GacRecirculationSwitch(c), GacClimateSwitch(c)
            assert recirculation.is_on is True and climate.is_on is False   # the car's report, A/C off
            for action in (recirculation.async_turn_off, recirculation.async_turn_on):
                with pytest.raises(ServiceValidationError, match='only while the cabin A/C is running'):
                    await action()
            c.client.climate_manual_on.assert_not_awaited()
            assert climate.is_on is False
            c.data = _air(2, False, 2)                       # a console change shows while A/C is off
            cabin.controller(c).sync()
            assert recirculation.is_on is False
    asyncio.run(run())


@pytest.mark.parametrize('mode,on,name', [(0, False, 'Off'), (1, True, 'Immediately'), (3, True, 'Repeating')])
def test_battery_preconditioning_switch_follows_the_reported_mode(mode, on, name):
    sw = GacCommandSwitch(coord(decode_status({'batteryPretreatmentAccessors': [
        {'batteryPretreatmentMode': mode, 'batteryPretreatmentStatus': -1}]})),
        next(d for d in SWITCHES if d.key == 'precondition_battery'))
    assert sw.is_on is on and sw.assumed_state is False
    assert sw.extra_state_attributes == {'reported_mode': name, 'reported_status': None}
    assert (sw.entity_description.on_cmd, sw.entity_description.off_cmd) == (
        'battery-precondition', 'battery-precondition-off')


def test_replaced_entities_are_retired_from_the_registry():
    from custom_components.gac_connect import _RETIRED
    from custom_components.gac_connect.button import BUTTONS

    assert {('button', 'precondition_battery'), ('switch', 'seat_1_ventilation'),
            ('switch', 'seat_2_ventilation')} <= set(_RETIRED)
    assert not any(d.key == 'precondition_battery' for d in BUTTONS)


def located(power):
    return decode_status({'positionAccessors': [{'latitude': 12.5, 'longitude': 98.5}],
                          **({'powerAccessors': [{'powerMode': power}]} if power is not None else {})})


@pytest.mark.parametrize('parked,moving,power,shown', [
    (True, True, 0, True), (True, True, 2, True), (True, True, None, True),
    (True, False, 0, True), (True, False, 2, False), (True, False, None, False),
    (False, True, 0, False), (False, True, 2, True), (False, True, None, False),
    (False, False, 2, False),
])
def test_position_is_shown_only_in_the_tracked_state(parked, moving, power, shown):
    c = coord(located(power))
    c.config_entry.options.update(track_parked=parked, track_moving=moving)
    tracker = GacDeviceTracker(c)
    gps = GacSensorEntity(c, next(d for d in SENSORS if d.key == 'gps_coordinates'))
    expected = (12.5, 98.5) if shown else (None, None)
    assert (tracker.latitude, tracker.longitude) == expected
    assert gps.native_value == ('12.500000, 98.500000' if shown else None)
    assert gps.extra_state_attributes == {'latitude': expected[0], 'longitude': expected[1]}


@pytest.mark.parametrize('options,choices', [
    ({}, (False, False)), ({'enable_tracker': True}, (True, True)), ({'enable_tracker': False}, (False, False)),
    ({'enable_tracker': True, 'track_parked': True, 'track_moving': False}, (True, False)),
    ({'track_parked': False, 'track_moving': True}, (False, True)),
])
def test_older_entries_follow_their_single_location_setting(options, choices):
    from custom_components.gac_connect.location import location_enabled, tracking_choices
    assert tracking_choices(options) == choices
    assert location_enabled(options) is any(choices)


@pytest.mark.parametrize('parked,moving', [(True, False), (False, True), (False, False)])
def test_entities_exist_when_either_state_is_tracked(tmp_path, parked, moving):
    async def run():
        options = {'track_parked': parked, 'track_moving': moving}
        async with vehicle(tmp_path, options=options) as (hass, entry, c):
            added = []
            c.data = located(0)
            if c.capabilities:
                c.capabilities.observe(c.data)
            for platform in ('sensor', 'device_tracker'):
                await importlib.import_module(f'custom_components.gac_connect.{platform}').async_setup_entry(
                    hass, entry, lambda entities: added.extend(e.unique_id for e in entities))
            assert ('VIN_location' in added) is ('VIN_gps_coordinates' in added) is (parked or moving)
    asyncio.run(run())


@pytest.mark.parametrize('stored', [False, True])
def test_settings_offer_both_choices_and_keep_the_single_setting_in_step(tmp_path, stored):
    async def run():
        async with vehicle(tmp_path, options={'enable_tracker': stored}) as (hass, entry, _):
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            form = await flow.async_step_settings()
            defaults = {key.schema: key.default() for key in form['data_schema'].schema
                        if key.schema in ('enable_tracker', 'track_parked', 'track_moving')}
            assert defaults == {'track_parked': stored, 'track_moving': stored}
            await flow.async_step_settings({'track_parked': False, 'track_moving': True})
            assert [entry.options[key] for key in ('track_parked', 'track_moving', 'enable_tracker')] == [
                False, True, True]
            await flow.async_step_settings({'track_parked': False, 'track_moving': False})
            assert entry.options['enable_tracker'] is False
    asyncio.run(run())


@pytest.mark.parametrize("mode,on", [(1, True), (0, False)])
def test_the_sterilisation_switch_follows_the_reported_mode(mode, on):
    sw = GacCommandSwitch(coord(decode_status({"airConditionAccessors": [{"airConditionAntivirusMode": mode}]})),
                          next(d for d in SWITCHES if d.key == "sterilisation"))
    assert sw.is_on is on
    assert (sw.entity_description.on_cmd, sw.entity_description.off_cmd) == ("antivirus-on", "antivirus-off")

