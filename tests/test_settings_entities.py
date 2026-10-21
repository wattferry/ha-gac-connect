"""Options and the charge window draft as entities, for an admin dashboard."""
import asyncio
from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.gac_connect import _reload_on_update
from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.button import GacSendWindowButton
from custom_components.gac_connect.number import GacPollingInterval
from custom_components.gac_connect.sensor import GacEntityChoicesSensor
from custom_components.gac_connect.settings import ChargeDraft, needs_reload
from custom_components.gac_connect.switch import (
    GacDraftDaySwitch, GacDraftUntilSocSwitch, GacOptionSwitch, GacQuietHoursSwitch)
from custom_components.gac_connect.time import GacDraftTime, GacQuietTime
from test_autodetect import vehicle
from test_regressions import ACCEPTED


def with_draft(entry):
    entry.runtime_data.charge_draft = ChargeDraft()
    return entry.runtime_data.charge_draft


def entity(cls, hass, *args):
    item = cls(*args)
    item.hass = hass
    item.async_write_ha_state = Mock()
    return item


@pytest.mark.parametrize("before,after,reload", [
    ({"experimental_pinless_unlock": False}, {"experimental_pinless_unlock": True}, False),
    ({"scan_interval": 60}, {"scan_interval": 300}, False),
    ({"quiet_start": "", "quiet_end": ""}, {"quiet_start": "22:00", "quiet_end": "07:00"}, False),
    ({"track_parked": True, "track_moving": True}, {"track_parked": False, "track_moving": True}, False),
    ({"track_parked": True, "track_moving": False}, {"track_parked": False, "track_moving": False}, True),
    ({"allow_account_alerts": False}, {"allow_account_alerts": True}, True),
    ({"allow_vehicle_shutdown": False}, {"allow_vehicle_shutdown": True}, True),
    ({"omit_entities": []}, {"omit_entities": ["sensor:pm25"]}, True),
    ({"load_cards": False}, {"load_cards": True}, False),
])
def test_only_options_that_add_or_remove_entities_reload(before, after, reload):
    assert needs_reload(before, after) is reload


def test_a_live_option_applies_without_a_reload(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={"scan_interval": 300}) as (hass, entry, c):
            entry.runtime_data.options = dict(entry.options)
            hass.config_entries.async_reload = AsyncMock()
            published = Mock()
            c.async_add_listener(published)
            hass.config_entries.async_update_entry(entry, options={**entry.options, "scan_interval": 120})
            await _reload_on_update(hass, entry)
            hass.config_entries.async_reload.assert_not_awaited()
            assert c.update_interval == timedelta(seconds=120) and entry.runtime_data.options["scan_interval"] == 120
            assert c._shared_interval() == timedelta(seconds=120)    # kept when the next poll is scheduled
            published.assert_called()                                 # entities publish the change at once
            with patch("custom_components.gac_connect.async_apply_dashboard", AsyncMock()) as applied:
                hass.config_entries.async_update_entry(entry, options={**entry.options, "load_cards": True})
                await _reload_on_update(hass, entry)
            applied.assert_awaited_once()                             # installing the cards needs no reload
            hass.config_entries.async_update_entry(entry, options={**entry.options, "allow_account_alerts": True})
            await _reload_on_update(hass, entry)
            hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)
    asyncio.run(run())


def test_option_switches_change_the_options(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={"track_parked": True, "track_moving": True}) as (hass, entry, c):
            unlock = entity(GacOptionSwitch, hass, c, "allow_remote_unlock", "experimental_pinless_unlock")
            assert unlock.is_on is False and unlock.available is True
            await unlock.async_turn_on()
            assert entry.options["experimental_pinless_unlock"] is True and unlock.is_on is True
            parked = entity(GacOptionSwitch, hass, c, "track_parked", "track_parked")
            await parked.async_turn_off()
            assert entry.options["track_parked"] is False and entry.options["enable_tracker"] is True
    asyncio.run(run())


def test_quiet_hours_switch_and_times(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            switch = entity(GacQuietHoursSwitch, hass, c)
            start = entity(GacQuietTime, hass, c, "quiet_start")
            end = entity(GacQuietTime, hass, c, "quiet_end")
            assert switch.is_on is False and start.native_value is None
            await start.async_set_value(time(21, 0))      # the end defaults while quiet hours were off
            assert (entry.options["quiet_start"], entry.options["quiet_end"]) == ("21:00", "07:00")
            await end.async_set_value(time(8, 0))
            assert switch.is_on is True and end.native_value == time(8, 0)
            await switch.async_turn_off()
            assert (entry.options["quiet_start"], entry.options["quiet_end"]) == ("", "")
            await switch.async_turn_on()                  # the last times come back
            assert (entry.options["quiet_start"], entry.options["quiet_end"]) == ("21:00", "08:00")
            with pytest.raises(ServiceValidationError):
                await end.async_set_value(time(21, 0))
    asyncio.run(run())


def test_poll_interval_number(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            number = entity(GacPollingInterval, hass, c)
            await number.async_set_native_value(600)
            assert entry.options["scan_interval"] == 600 and number.native_value == 600
            assert (number.native_min_value, number.native_max_value) == (60, 3600)
    asyncio.run(run())


def test_the_draft_follows_a_new_reported_window_and_keeps_edits_otherwise():
    draft = ChargeDraft()
    report = decode_status({"chargingAccessors": [{"chargingMode": 2, "weeklyReservation": 17, "chargingEndType": 0,
                                                   "dailyReservationStartTime": 82800000,
                                                   "dailyReservationStopTime": 18000000 + 86400000}]})
    draft.observe(report)
    assert (draft.start, draft.stop, draft.days, draft.until_soc) == ("23:00", "05:00", {"mon", "fri"}, False)
    draft.set(start="22:00")
    draft.observe(report)                     # the same window again: the edit stays
    assert draft.start == "22:00"
    placeholder = decode_status({"chargingAccessors": [{"chargingMode": 1, "dailyReservationStartTime": 0,
                                                        "dailyReservationStopTime": 0}]})
    draft.observe(placeholder)                # Not set: nothing to copy
    assert draft.start == "22:00"
    other = decode_status({"chargingAccessors": [{"chargingMode": 2, "weeklyReservation": 0, "chargingEndType": 1,
                                                  "dailyReservationStartTime": 3600000}]})
    draft.observe(other)
    assert (draft.start, draft.days, draft.until_soc) == ("01:00", set(), True)


def test_the_cars_report_of_the_sent_window_keeps_the_draft_as_entered():
    # Sent 10:00-11:11 at 11:05: the car reports 11:07-11:11 (moved to the next minute); keep 10:00.
    draft = ChargeDraft()
    draft.set(start="10:00", stop="11:11")
    draft.mark_sent("11:07", "11:11", 0, False)
    sent = decode_status({"chargingAccessors": [{"chargingMode": 1, "chargingEndType": 0, "weeklyReservation": 0,
                                                 "dailyReservationStartTime": 1792206420000,
                                                 "dailyReservationStopTime": 1792206660000}]})
    draft.observe(sent)
    assert (draft.start, draft.stop) == ("10:00", "11:11")
    other = decode_status({"chargingAccessors": [{"chargingMode": 2, "weeklyReservation": 96, "chargingEndType": 0,
                                                  "dailyReservationStartTime": 79200000,
                                                  "dailyReservationStopTime": 21600000 + 86400000}]})
    draft.observe(other)                      # a window set elsewhere (the app): the draft follows it
    assert (draft.start, draft.stop, draft.days) == ("22:00", "06:00", {"sat", "sun"})


def test_draft_entities_edit_and_send_the_window(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            draft = with_draft(entry)
            start, stop = entity(GacDraftTime, hass, c, "start"), entity(GacDraftTime, hass, c, "stop")
            monday, until = entity(GacDraftDaySwitch, hass, c, "mon"), entity(GacDraftUntilSocSwitch, hass, c)
            button = entity(GacSendWindowButton, hass, c)
            with pytest.raises(ServiceValidationError):
                await button.async_press()            # no start yet
            await start.async_set_value(time(23, 0))
            await stop.async_set_value(time(5, 0))
            await monday.async_turn_on()
            assert (draft.start, draft.stop, draft.weekly) == ("23:00", "05:00", 1)
            c.client.set_charge_window = AsyncMock(return_value=ACCEPTED)
            c.async_refresh_now = AsyncMock()
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()):
                await button.async_press()
            c.client.set_charge_window.assert_awaited_once_with("VIN", "23:00", "05:00", weekly=1, until_soc=False)
            await until.async_turn_on()                # stop at the charge limit: no stop time
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()):
                await button.async_press()
            assert c.client.set_charge_window.await_args.args[2] is None
            assert c.client.set_charge_window.await_args.kwargs["until_soc"] is True
    asyncio.run(run())


def test_entity_visibility_action_and_choices_sensor(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            from custom_components.gac_connect.services import async_register_services
            registered = {}
            fake = SimpleNamespace(
                services=SimpleNamespace(has_service=Mock(return_value=False),
                                         async_register=lambda d, name, handler, schema, **kw: registered.update(
                                             {name: handler})),
                config_entries=SimpleNamespace(
                    async_entries=Mock(return_value=[SimpleNamespace(runtime_data=entry.runtime_data)]),
                    async_update_entry=hass.config_entries.async_update_entry))
            async_register_services(fake)
            action = registered["set_entity_visibility"]
            await action(SimpleNamespace(data={"entity": "binary_sensor:front_left_door", "visibility": "always"}))
            await action(SimpleNamespace(data={"entity": "sensor:pm25", "visibility": "omit"}))
            assert entry.options["enable_entities"] == ["binary_sensor:front_left_door"]
            assert entry.options["omit_entities"] == ["sensor:pm25"]
            await action(SimpleNamespace(data={"entity": "sensor:pm25", "visibility": "automatic"}))
            assert entry.options["omit_entities"] == []
            with pytest.raises(ServiceValidationError):
                await action(SimpleNamespace(data={"entity": "sensor:nope", "visibility": "omit"}))
            sensor = GacEntityChoicesSensor(c)
            assert sensor.native_value == 1
            attributes = sensor.extra_state_attributes
            assert attributes["always_show"] == ["binary_sensor:front_left_door"] and attributes["omit"] == []
            assert "binary_sensor:front_left_door" in attributes["entities"]
    asyncio.run(run())
