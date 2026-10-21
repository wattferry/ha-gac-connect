"""Exercise the schedule view and editor against the bundled command builder."""
import asyncio
import re
from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from custom_components.gac_connect.api import GacClient, decode_status
from custom_components.gac_connect.config_flow import GacOptionsFlow
from custom_components.gac_connect.charging import schedule_attributes, schedule_mode
from gac_connect.errors import CommandError
from test_autodetect import result, vehicle
from test_regressions import ACCEPTED


def setup_flow(hass, entry, coordinator):
    flow = GacOptionsFlow()
    flow.hass, flow.handler = hass, entry.entry_id
    client = coordinator.client = object.__new__(GacClient)
    client.timezone = 'Asia/Bangkok'
    client._tz = ZoneInfo(client.timezone)
    client._charge_time_formats = {}
    client._charge_windows = {}
    client._reservation = AsyncMock(return_value=ACCEPTED)
    return flow, client


def test_view_prefills_the_reported_window_without_sending_a_command(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            c.data = decode_status({'chargingAccessors': [{'chargingMode': 0, 'dailyReservationStartTime': 82800000,
                'dailyReservationStopTime': 18000000, 'weeklyReservation': 3}]})
            page = await flow.async_step_charging()
            summary = page['description_placeholders']['schedule']
            for value in ('Whenever plugged in', '23:00', '05:00', 'Monday, Tuesday', 'Asia/Bangkok'):
                assert value in summary
            assert schedule_mode(c.data) == 'unrestricted'  # a stored window is not proof scheduled mode is active
            assert schedule_attributes(c.data)['reported_clock_verified'] is False
            form = await flow.async_step_charge_window()
            suggestions = {key.schema: key.description.get('suggested_value')
                           for key in form['data_schema'].schema if key.schema in ('start', 'stop')}
            assert suggestions == {'start': '23:00', 'stop': '05:00'}
            assert form['data_schema'](suggestions)['days'] == ['mon', 'tue']
            await flow.async_step_charge_now()
            client._reservation.assert_not_awaited()
            assert c.commands.state == 'idle'
    asyncio.run(run())


@pytest.mark.parametrize('until_soc', [False, True])
def test_editor_sends_validated_overnight_window_with_selected_days(tmp_path, until_soc):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            before = dict(entry.options)
            form = await flow.async_step_charge_window()
            submitted = form['data_schema']({'start': '23:00', 'stop': '05:00', 'days': ['mon', 'fri'], 'until_soc': until_soc})
            response = await flow.async_step_charge_window(submitted)
            assert response['type'] == 'menu' and response['step_id'] == 'charging'
            vin, operation = client._reservation.await_args.args
            assert vin == 'VIN'
            assert operation['weeklyReservation'] == 17
            assert operation['dailyReservationStartTime'] == 82800000
            # Stopping at the charge limit sends no stop time (the gateway refuses one with 13101).
            # 05:00 after a 23:00 start is sent as 29:00, as the app does.
            assert operation.get('dailyReservationStopTime') == (None if until_soc else 18000000 + 86400000)
            assert ('stopTime' in operation) is not until_soc
            assert operation['chargingMode'] == 2 and operation['chargingEndType'] == int(until_soc)
            start = datetime(*(operation['startTime'][k] for k in ('year', 'month', 'day', 'hour', 'minute')))
            assert start.weekday() in (0, 4) and (start.hour, start.minute) == (23, 0)  # dated, never undated
            assert c.commands.state == 'pending'  # acceptance did not fabricate a schedule
            assert c.data is None
            assert dict(entry.options) == before
            await flow.async_step_charging()
            await flow.async_step_charge_window()
            client._reservation.assert_awaited_once()  # navigating back must not replay the command
    asyncio.run(run())


@pytest.mark.parametrize('start,stop', [('23:00', '23:00'), ('25:00', '05:00'), ('12:30:00', '05:00')])
def test_invalid_window_never_sends(tmp_path, start, stop):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            response = await flow.async_step_charge_window({'start': start, 'stop': stop})
            assert response['errors']['base'] == 'invalid_charge_window'
            client._reservation.assert_not_awaited()
    asyncio.run(run())


def test_rejected_window_keeps_input_and_charge_now_requires_submit(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            c.data = decode_status({'chargingAccessors': [{'weeklyReservation': 3, 'chargingEndType': 1,
                'dailyReservationStartTime': 82800000, 'dailyReservationStopTime': 18000000}]})
            client._reservation.side_effect = CommandError('rejected')
            response = await flow.async_step_charge_window({'start': '22:00', 'stop': '06:00', 'days': [], 'until_soc': False})
            assert response['errors']['base'] == 'command_refused'      # the gateway's reason is shown
            assert response['description_placeholders']['reason'] == 'rejected'
            values = response['data_schema']({'start': '22:00', 'stop': '06:00'})
            assert values['days'] == [] and values['until_soc'] is False
            assert {key.schema: key.description.get('suggested_value') for key in response['data_schema'].schema
                    if key.schema in ('start', 'stop')} == {'start': '22:00', 'stop': '06:00'}
            assert c.commands.state == 'failed'
            client._reservation.reset_mock(side_effect=True)
            await flow.async_step_charge_now()
            client._reservation.assert_not_awaited()
            response = await flow.async_step_charge_now({})
            assert response['type'] == 'menu' and response['step_id'] == 'charging'
            assert client._reservation.await_args.args[1]['chargingMode'] == 0
            client._reservation.assert_awaited_once()
    asyncio.run(run())


@pytest.mark.parametrize('weekly,days', [(0, []), (127, ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']), (64, ['sun'])])
def test_prefill_includes_reported_days_and_stopping_rule(tmp_path, weekly, days):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            c.data = decode_status({'chargingAccessors': [{'weeklyReservation': weekly, 'chargingEndType': 1,
                'startTime': {'year': 2026, 'month': 10, 'day': 11, 'hour': 22, 'minute': 8},
                'stopTime': {'year': 2026, 'month': 10, 'day': 12, 'hour': 6, 'minute': 10}}]})
            form = await flow.async_step_charge_window()
            suggestions = {key.schema: key.description.get('suggested_value') for key in form['data_schema'].schema
                           if key.schema in ('start', 'stop')}
            assert suggestions == {'start': '22:08', 'stop': '06:10'}
            values = form['data_schema'](suggestions)
            assert values['days'] == days and values['until_soc'] is True
            client._reservation.assert_not_awaited()
    asyncio.run(run())


def test_missing_schedule_stays_unknown_and_refresh_is_explicit(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            c.client.timezone = 'Asia/Bangkok'
            assert 'Not reported' in (await flow.async_step_charging())['description_placeholders']['schedule']
            c.client.get_status.assert_not_awaited()
            await flow.async_step_refresh_charging()
            c.client.get_status.assert_awaited_once()
            assert schedule_attributes(c.data)['reported_start'] is None
            del entry.runtime_data
            for step in (flow.async_step_charging, flow.async_step_charge_window, flow.async_step_charge_now):
                assert (await step())['reason'] == 'vehicle_not_loaded'
    asyncio.run(run())


def test_real_ut_schedule_reads_calendar_fields_and_confirms_after_new_report(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            raw = {'timezoneAccessor': {'timezone': 'Asia/Bangkok'}, 'chargingAccessors': [{
                'chargingMode': 1, 'weeklyReservation': 0, 'chargingEndType': 0,
                'dailyReservationStartTime': 1791727200000, 'dailyReservationStopTime': 1791756000000,
                'startTime': {'year': 2026, 'month': 10, 'day': 11, 'hour': 22, 'minute': 0},
                'stopTime': {'year': 2026, 'month': 10, 'day': 12, 'hour': 6, 'minute': 0},
            }]}
            c.data = decode_status(raw, updated_ms=1000)
            summary = (await flow.async_step_charging())['description_placeholders']['schedule']
            for value in ('22:00', '06:00', 'Stop time', 'One time', '(once)'):
                assert value in summary
            assert 'disagree' not in summary   # once timestamps read on the service clock (UTC+8) agree
            response = await flow.async_step_charge_window({'start': '23:00', 'stop': '07:00'})
            assert response['type'] == 'menu'
            operation = client._reservation.await_args.args[1]   # one time: the app's once, dated start and stop
            assert operation['chargingMode'] == 1 and 'weeklyReservation' not in operation
            assert (operation['stopTime']['hour'], operation['stopTime']['minute']) == (7, 0)
            assert c.commands.state == 'pending'
            # The car reports the once window with weeklyReservation 0 (Aion UT, 2026-10-17).
            c.commands.observe(decode_status({'chargingAccessors': [{**operation, 'weeklyReservation': 0}]},
                                             updated_ms=2000))
            assert c.commands.state == 'confirmed'
    asyncio.run(run())


@pytest.mark.parametrize('days,weekly', [([], 0), (['tue', 'fri'], 18),
                                         (['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'], 127)])
def test_editor_days_follow_the_app_once_repeat_and_every_day(tmp_path, days, weekly):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            await flow.async_step_charge_window({'start': '22:06', 'stop': '22:12', 'days': days, 'until_soc': False})
            operation = client._reservation.await_args.args[1]
            if weekly:      # repeating: loop mode with times of day
                assert (operation['chargingMode'], operation['weeklyReservation']) == (2, weekly)
                assert operation['dailyReservationStartTime'] == 79560000
                report = operation
            else:           # one time: the app's once; the car reports it with weekly 0
                assert operation['chargingMode'] == 1 and 'weeklyReservation' not in operation
                report = {**operation, 'weeklyReservation': 0}
            c.data = decode_status({'chargingAccessors': [report]}, updated_ms=2000)
            assert schedule_attributes(c.data)['reported_days'] == {
                0: 'One time', 18: 'Tuesday, Friday', 127: 'Every day'}[weekly]
            c.commands.observe(c.data)
            assert c.commands.state == 'confirmed'
    asyncio.run(run())


@pytest.mark.parametrize('step,user_input', [('charge_now', {}),
                                             ('charge_window', {'start': '22:00', 'stop': '06:00', 'days': []})])
def test_car_refusal_is_shown_on_the_form(tmp_path, step, user_input):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)

            async def refused(*_args, **_kwargs):
                c.commands.result(result(ok=False))
                return ACCEPTED
            client._reservation.side_effect = refused
            response = await getattr(flow, f'async_step_{step}')(user_input)
            assert response['errors']['base'] == 'command_refused'
            assert response['description_placeholders']['reason'] == 'The car refused the request: result code 13101.'
            assert c.commands.state == 'rejected'
    asyncio.run(run())


@pytest.mark.parametrize('until_soc,sent', [(True, True), (False, False)])
def test_the_stop_time_is_needed_only_without_the_charge_limit(tmp_path, until_soc, sent):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            form = await flow.async_step_charge_window()
            submitted = form['data_schema']({'start': '23:00', 'days': [], 'until_soc': until_soc})
            response = await flow.async_step_charge_window(submitted)
            if sent:
                assert response['step_id'] == 'charging'
                assert 'dailyReservationStopTime' not in client._reservation.await_args.args[1]
            else:
                assert response['errors'] == {'base': 'invalid_charge_window'}
                client._reservation.assert_not_awaited()
    asyncio.run(run())


def test_a_window_that_could_not_be_sent_says_the_request_failed(tmp_path):
    from gac_connect.errors import ResponseError

    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            client._reservation.side_effect = ResponseError('Could not reach GAC')
            response = await flow.async_step_charge_window({'start': '21:00', 'stop': '23:00', 'days': []})
            assert response['errors']['base'] == 'command_failed'
    asyncio.run(run())


def test_after_sending_the_page_shows_the_request_and_says_the_report_predates_it(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            c.data = decode_status({'chargingAccessors': [{'chargingMode': 2, 'weeklyReservation': 127,
                'dailyReservationStartTime': 79860000, 'dailyReservationStopTime': 79920000}]})
            page = await flow.async_step_charge_window({'start': '23:09', 'stop': '00:10', 'days': ['fri', 'sat']})
            text = page['description_placeholders']['schedule']
            assert '23:09 → 00:10, Friday, Saturday — sent; waiting for the car\'s report' in text
            assert 'values below are from before it' in text
            assert '**Reported window:** 22:11 → 22:12' in text          # the old report, still shown
            client._reservation.side_effect = CommandError('rejected', code=13002)
            page = await flow.async_step_charge_window({'start': '23:09', 'until_soc': True, 'days': []})
            text = (await flow.async_step_charging())['description_placeholders']['schedule']
            assert re.search(r'23:09 → the target charge level, One time on \w{3} \d{1,2} \w{3} — refused: '
                             r'not supported by this vehicle \(code 13002\)', text)
            assert 'values below are from before it' not in text
    asyncio.run(run())


def test_after_an_accepted_window_the_page_reads_the_car_again(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow, client = setup_flow(hass, entry, c)
            c.data = decode_status({'chargingAccessors': [{'chargingMode': 2, 'weeklyReservation': 127,
                'dailyReservationStartTime': 79860000, 'dailyReservationStopTime': 79920000}]})
            # The car's next report: the new window across midnight, as an Aion UT reports it.
            client.get_status = AsyncMock(return_value=decode_status({'chargingAccessors': [{
                'chargingMode': 2, 'weeklyReservation': 48, 'chargingEndType': 0,
                'dailyReservationStartTime': 83340000, 'dailyReservationStopTime': 87000000}]}))
            page = await flow.async_step_charge_window({'start': '23:09', 'stop': '00:10', 'days': ['fri', 'sat']})
            client.get_status.assert_awaited()
            text = page['description_placeholders']['schedule']
            assert "23:09 → 00:10, Friday, Saturday — confirmed by the car's report" in text
            assert '**Reported window:** 23:09 → 00:10' in text and 'from before it' not in text
    asyncio.run(run())


UT_ONCE = {'chargingMode': 1, 'chargingEndType': 1, 'weeklyReservation': 0,
           'dailyReservationStartTime': 1791963060000, 'dailyReservationStopTime': 1792006260000,
           'startTime': {'year': 2026, 'month': 10, 'day': 14, 'hour': 15, 'minute': 31, 'second': 0, 'millisecond': 0},
           'stopTime': {'year': 2026, 'month': 10, 'day': 15, 'hour': 3, 'minute': 31, 'second': 0, 'millisecond': 0}}
NOT_SET = {'chargingMode': 1, 'chargingEndType': 0, 'weeklyReservation': 0,
           'dailyReservationStartTime': 0, 'dailyReservationStopTime': 0,
           'startTime': {'year': 2000, 'month': 0, 'day': 0, 'hour': 0, 'minute': 0, 'second': 0},
           'stopTime': {'year': 2000, 'month': 0, 'day': 0, 'hour': 0, 'minute': 1, 'second': 0}}


@pytest.mark.parametrize('charging,text', [
    (UT_ONCE, '15:31 (Wed 14 Oct) → 03:31 (Thu 15 Oct)'),          # set from the console on an Aion UT
    (NOT_SET, 'Not set'),                                            # the app: "Charging time is not set"
    ({'chargingMode': 2, 'weeklyReservation': 48, 'dailyReservationStartTime': 83340000,
      'dailyReservationStopTime': 87000000}, '23:09 → 00:10'),
])
def test_the_reported_window_names_one_time_dates_and_the_not_set_placeholder(charging, text):
    from custom_components.gac_connect.charging import reported_window_text
    assert reported_window_text(decode_status({'chargingAccessors': [charging]})) == text


@pytest.mark.parametrize('start,stop,until_soc,day', [
    ('15:00', '03:00', False, 'Wed 14 Oct'),      # open at 15:24: charges at once
    ('15:00', None, True, 'Thu 15 Oct'),          # no stop time sent: the next 15:00
    ('22:00', '06:00', False, 'Wed 14 Oct'),
])
def test_a_one_time_request_says_which_day_it_was_sent_for(start, stop, until_soc, day):
    from custom_components.gac_connect.charging import _requested, window_target
    from custom_components.gac_connect.command_tracking import CommandRecord

    zone = ZoneInfo('Asia/Bangkok')
    record = CommandRecord('charge-window', 0, None, window_target(start, stop, 0, until_soc),
                           requested_at=datetime(2026, 10, 14, 15, 24, tzinfo=zone))
    assert _requested(record, zone).endswith(f', One time on {day}')
    assert _requested(record).endswith(', One time')


def test_a_used_one_time_window_reads_not_set_and_explains_it_will_not_charge(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            # Aion UT 2026-10-16 after a one-time window ended: once mode, both times 0, waiting (27).
            c.data = decode_status({'chargingAccessors': [{'chargingMode': 1, 'chargingEndType': 0, 'weeklyReservation': 0,
                'dailyReservationStartTime': 0, 'dailyReservationStopTime': 0, 'chargingStatus': 27,
                'startTime': {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 0},
                'stopTime': {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 0}}],
                'chargerAccessors': [{'plug': 1, 'lock': 0}]})
            assert schedule_mode(c.data) == 'not_set' and c.data.charging is False
            flow, _ = setup_flow(hass, entry, c)
            page = await flow.async_step_charging()
            assert "will not charge until you set a window or choose Charge now" in page['description_placeholders']['schedule']
    asyncio.run(run())
