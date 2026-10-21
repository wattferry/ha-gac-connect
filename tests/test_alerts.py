"""Alerts from the car's report, and from GAC's alert list while the owner allows it."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from gac_connect.alerts import ALERT_KEYS
from gac_connect.errors import AccountSessionEnded, ResponseError
from custom_components.gac_connect.account_alerts import SIGNAL_ACCOUNT_ALERT, AccountAlerts
from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.car_alerts import CAR_ALERT_TYPES, HOLD_SECONDS, CarAlertWatcher
from custom_components.gac_connect.config_flow import GacOptionsFlow
from custom_components.gac_connect.const import CONF_ALLOW_ACCOUNT_ALERTS
from custom_components.gac_connect.diagnostics import async_get_config_entry_diagnostics
from custom_components.gac_connect.sensor import LAST_ALERT_STATES, GacLastAlertSensor
from test_autodetect import vehicle

STRINGS = json.loads((Path(__file__).resolve().parents[1] / "custom_components/gac_connect/translations/en.json")
                     .read_text())


def report(*, power=0, lock=0, door=0, window=0, charging=None, plug=None, sterilising=None):
    raw = {"powerAccessors": [{"powerMode": power}],
           "doorAccessors": [{"lock": lock, "openMode": door}, {"lock": lock, "openMode": 0}],
           "windowAccessors": [{"openMode": window}]}
    if charging is not None:
        raw["chargingAccessors"] = [{"chargingStatus": charging}]
    if plug is not None:
        raw["chargerAccessors"] = [{"plug": plug}]
    if sterilising is not None:
        raw["airConditionAccessors"] = [{"airConditionAntivirusMode": sterilising}]
    return decode_status(raw)


def test_stopped_charging_fires_once_when_the_report_changes():
    watcher = CarAlertWatcher(None)
    assert watcher.observe(report(charging=2, plug=1), 0) == []        # the first report is the baseline
    fired = watcher.observe(report(charging=0, plug=1), 10)
    assert [name for name, _ in fired] == ["charging_stopped"]
    assert watcher.observe(report(charging=0, plug=1), 20) == []
    # Unplugging mid-charge is not reported: the cable is out.
    watcher.observe(report(charging=2, plug=1), 30)
    assert watcher.observe(report(charging=0, plug=0), 40) == []


def test_left_unlocked_waits_for_the_hold_and_fires_once_per_episode():
    watcher = CarAlertWatcher(None)
    watcher.observe(report(power=1, lock=1), 0)
    assert watcher.observe(report(power=0, lock=1), 100) == []
    assert watcher.observe(report(power=0, lock=1), 100 + HOLD_SECONDS - 1) == []
    assert [name for name, _ in watcher.observe(report(power=0, lock=1), 100 + HOLD_SECONDS)] == ["left_unlocked"]
    assert watcher.observe(report(power=0, lock=1), 1000) == []
    watcher.observe(report(power=0, lock=0), 1100)                      # locked: the episode ends
    watcher.observe(report(power=0, lock=1), 1200)
    assert [name for name, _ in watcher.observe(report(power=0, lock=1), 1200 + HOLD_SECONDS)] == ["left_unlocked"]


def test_locking_up_within_the_hold_and_driving_raise_nothing():
    watcher = CarAlertWatcher(None)
    watcher.observe(report(power=0, lock=1, door=1, window=1), 0)
    assert watcher.observe(report(power=0, lock=0), HOLD_SECONDS - 10) == []
    assert watcher.observe(report(power=0, lock=0), 2 * HOLD_SECONDS) == []
    watcher.observe(report(power=1, lock=1, window=1), 3000)
    assert watcher.observe(report(power=1, lock=1, window=1), 3000 + 2 * HOLD_SECONDS) == []


def test_open_door_and_window_name_what_is_open():
    watcher = CarAlertWatcher(None)
    watcher.observe(report(power=0, door=1, window=1), 0)
    fired = dict(watcher.observe(report(power=0, door=1, window=1), HOLD_SECONDS))
    assert fired == {"left_open": {"open": ["door"]}, "window_left_open": {"open": []}}


def test_numbered_doors_and_windows_are_named():
    def numbered(**open_):
        return decode_status({
            "powerAccessors": [{"powerMode": 0}],
            "doorAccessors": [{"door": n, "lock": 0, "openMode": int(open_.get(f"door{n}", 0))} for n in (1, 2, 3, 4)],
            "windowAccessors": [{"window": n, "openMode": int(open_.get(f"window{n}", 0))} for n in (1, 2, 3, 4)],
        })
    watcher = CarAlertWatcher(None)
    watcher.observe(numbered(door2=1, window4=1), 0)
    fired = dict(watcher.observe(numbered(door2=1, window4=1), HOLD_SECONDS))
    assert fired == {"left_open": {"open": ["front_right_door"]}, "window_left_open": {"open": ["rear_right"]}}


def test_sterilisation_finishing_fires():
    watcher = CarAlertWatcher(None)
    watcher.observe(report(power=0, sterilising=1), 0)
    assert [name for name, _ in watcher.observe(report(power=0, sterilising=0), 5)] == ["sterilisation_finished"]


def item(alert_id, created, source, obj, reason):
    content = {"alarmStatus": [{"alarmSource": source, "alarms": [{"alarmObject": obj, "alarmReason": reason,
                                                                    "signals": []}]}]}
    return {"alarmId": alert_id, "createTime": created, "alarmContent": json.dumps(content)}


OLD = item("a1", "2026-10-14T08:37:20Z", 210, 0, 3)
NEW = item("a2", "2026-10-16T09:00:00Z", 210, 0, 6)
NEWER = item("a3", "2026-10-16T09:05:00Z", 1, 0, 2)


def alerts_for(hass, entry, c, *pages):
    c.client.get_alarms = AsyncMock(side_effect=[{"list": page} if isinstance(page, list) else page
                                                 for page in pages])
    alerts = AccountAlerts(hass, entry, c)
    fired = []

    @callback
    def collect(alert):
        fired.append(alert)

    async_dispatcher_connect(hass, SIGNAL_ACCOUNT_ALERT.format(vin="VIN"), collect)
    return alerts, fired


def test_listed_alerts_are_history_and_only_new_ones_fire_oldest_first(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_ACCOUNT_ALERTS: True}) as (hass, entry, c):
            alerts, fired = alerts_for(hass, entry, c, [OLD], [NEWER, NEW, OLD], [NEWER, NEW, OLD])
            sensor = GacLastAlertSensor(c, alerts)
            assert sensor.native_value == "not_read_yet" and sensor.available
            await alerts.async_setup()
            await alerts.async_read()
            assert fired == [] and alerts.state == "ok"
            assert sensor.native_value == "connector_not_plugged_in"
            await alerts.async_read()
            assert [a.alert_id for a in fired] == ["a2", "a3"]
            assert sensor.native_value == "door_unlocked"
            assert sensor.extra_state_attributes["title"] == "Doors not locked"
            await alerts.async_read()
            assert len(fired) == 2
            # A restart remembers what was seen.
            again, fired_again = alerts_for(hass, entry, c, [NEWER, NEW, OLD])
            await again.async_setup()
            await again.async_read()
            assert fired_again == []
            alerts.async_close()
            again.async_close()
    asyncio.run(run())


def test_an_ended_account_session_shows_signed_out_and_stops_reading(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_ACCOUNT_ALERTS: True}) as (hass, entry, c):
            alerts, _ = alerts_for(hass, entry, c, [OLD])
            await alerts.async_read()
            c.client.get_alarms = AsyncMock(side_effect=AccountSessionEnded("signed in on another phone"))
            await alerts.async_read()
            sensor = GacLastAlertSensor(c, alerts)
            assert alerts.state == "signed_out" and sensor.native_value == "signed_out"
            assert sensor.extra_state_attributes["account_state"] == "signed_out"
            assert sensor.extra_state_attributes["last_read"] is not None
            assert sensor.extra_state_attributes["last_error"] == "signed in on another phone"
            c.client.last_account_refresh = (1792148400.0, False)
            assert alerts.diagnostics()["last_account_token_refresh"] == {"at": "2026-10-16T11:00:00+00:00",
                                                                          "accepted": False}
            await alerts.async_read()
            c.client.get_alarms.assert_awaited_once()                  # no more reads until signed in again
    asyncio.run(run())


def test_a_failed_read_keeps_the_last_alert(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_ACCOUNT_ALERTS: True}) as (hass, entry, c):
            alerts, _ = alerts_for(hass, entry, c)
            sensor = GacLastAlertSensor(c, alerts)
            c.client.get_alarms = AsyncMock(side_effect=ResponseError("down"))
            await alerts.async_read()
            assert sensor.native_value == "read_failed"
            assert sensor.extra_state_attributes["last_error"] == "down" == alerts.diagnostics()["last_error"]
            c.client.get_alarms = AsyncMock(side_effect=[{"list": [OLD]}, ResponseError("down")])
            await alerts.async_read()
            await alerts.async_read()
            assert alerts.state == "error" and sensor.native_value == "connector_not_plugged_in"
            c.client.get_alarms = AsyncMock(return_value={"list": [OLD]})
            await alerts.async_read()
            assert alerts.last_error is None and alerts.state == "ok"
    asyncio.run(run())


def test_alerts_are_off_unless_allowed(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            alerts, _ = alerts_for(hass, entry, c, [OLD])
            await alerts.async_setup()
            await alerts.async_read()
            assert alerts.state == "off" and not alerts.enabled
            c.client.get_alarms.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize("allowed", [False, True])
def test_options_save_the_permission_and_diagnostics_show_the_state(tmp_path, allowed):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            assert (await flow.async_step_settings())["data_schema"]({})[CONF_ALLOW_ACCOUNT_ALERTS] is False
            await flow.async_step_settings({CONF_ALLOW_ACCOUNT_ALERTS: allowed})
            assert entry.options[CONF_ALLOW_ACCOUNT_ALERTS] is allowed
            entry.runtime_data.alerts = AccountAlerts(hass, entry, c)
            diagnostics = await async_get_config_entry_diagnostics(hass, entry)
            assert diagnostics["options"][CONF_ALLOW_ACCOUNT_ALERTS] is allowed
            assert diagnostics["account_alerts"]["state"] == ("waiting" if allowed else "off")
    asyncio.run(run())


def test_every_alert_state_and_event_type_has_a_name():
    entity = STRINGS["entity"]
    assert set(entity["sensor"]["last_gac_alert"]["state"]) == {*ALERT_KEYS, *LAST_ALERT_STATES}
    assert set(entity["event"]["gac_alert"]["state_attributes"]["event_type"]["state"]) == set(ALERT_KEYS)
    assert set(entity["event"]["car_alert"]["state_attributes"]["event_type"]["state"]) == set(CAR_ALERT_TYPES)
    settings = STRINGS["options"]["step"]["settings"]
    assert CONF_ALLOW_ACCOUNT_ALERTS in settings["data"] and CONF_ALLOW_ACCOUNT_ALERTS in settings["data_description"]


def test_alerts_from_one_report_are_each_recorded(tmp_path):
    from unittest.mock import patch
    from custom_components.gac_connect.event import GacCarAlertEvent

    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            entity = GacCarAlertEvent(c)
            entity.hass = hass
            c.data = report(power=0, lock=1, window=1)
            entity._watcher.observe(c.data, 0)
            written = []
            with patch.object(GacCarAlertEvent, "async_write_ha_state",
                              lambda self: written.append(self.state_attributes["event_type"])), \
                    patch("custom_components.gac_connect.event.monotonic", return_value=HOLD_SECONDS):
                c.data = report(power=0, lock=1, window=1)
                entity._handle_coordinator_update()
            assert written[:2] == ["left_unlocked", "window_left_open"]
    asyncio.run(run())


def test_an_unload_during_a_read_publishes_and_saves_nothing(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_ACCOUNT_ALERTS: True}) as (hass, entry, c):
            alerts, fired = alerts_for(hass, entry, c, [OLD])
            await alerts.async_setup()
            await alerts.async_read()                            # history
            gate, started = asyncio.Event(), asyncio.Event()

            async def slow(vin, **kwargs):
                started.set()
                await gate.wait()
                return {"list": [NEW, OLD]}
            c.client.get_alarms = AsyncMock(side_effect=slow)
            alerts._store.async_save = AsyncMock()
            alerts._scheduled()
            await started.wait()
            alerts.async_close()                                 # the entry unloads mid-read
            gate.set()
            await asyncio.sleep(0)
            assert alerts._task.cancelled() or alerts._task.done()
            assert fired == [] and not alerts._store.async_save.called
            alerts._scheduled()                                  # a late timer starts nothing
            assert alerts._task.done()
    asyncio.run(run())


@pytest.mark.parametrize("page", [{"list": 42}, {"list": [dict(NEW, alarmContent=json.dumps(
    {"alarmStatus": [{"alarmSource": 210, "alarms": [{"alarmObject": 0, "alarmReason": 6, "signals": 42}]}]}))]}, 7])
def test_a_malformed_alert_page_is_a_failed_read(tmp_path, page):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_ACCOUNT_ALERTS: True}) as (hass, entry, c):
            alerts, _ = alerts_for(hass, entry, c, [OLD], page)
            await alerts.async_setup()
            await alerts.async_read()
            read_at = alerts.last_read
            await alerts.async_read()
            if isinstance(page, dict) and isinstance(page["list"], list):
                assert alerts.state == "ok"                      # a bad signals field is just left out
            else:
                assert alerts.state == "error" and alerts.last_read == read_at and alerts.last_error
            alerts.async_close()
    asyncio.run(run())


def test_a_history_write_under_way_finishes_before_removal_deletes_it(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_ACCOUNT_ALERTS: True}) as (hass, entry, c):
            alerts, _ = alerts_for(hass, entry, c, [OLD], [NEW, OLD])
            await alerts.async_setup()
            await alerts.async_read()
            writing, release, events = asyncio.Event(), asyncio.Event(), []

            async def slow_save(data):
                writing.set()
                await release.wait()             # the write is under way
                events.append("written")
            alerts._store.async_save = slow_save
            alerts._scheduled()
            await writing.wait()
            alerts.async_close()                 # the entry unloads mid-write
            drained = asyncio.create_task(alerts.async_drain())
            await asyncio.sleep(0.01)
            assert not drained.done()            # unload, and so removal, waits for the write
            release.set()
            await drained
            events.append("removal may delete it now")
            assert events == ["written", "removal may delete it now"]
    asyncio.run(run())



def test_every_way_an_entry_goes_away_waits_for_the_history_write(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_ACCOUNT_ALERTS: True}) as (hass, entry, c):
            alerts, _ = alerts_for(hass, entry, c, [OLD], [NEW, OLD])
            await alerts.async_setup()
            await alerts.async_read()
            writing, release, events = asyncio.Event(), asyncio.Event(), []

            async def slow_save(data):
                writing.set()
                await release.wait()
                events.append("written")
            alerts._store.async_save = slow_save
            alerts._scheduled()
            await writing.wait()
            # The clean-up Home Assistant runs after an unload and after a failed set-up alike.
            cleanup = asyncio.create_task(entry._async_process_on_unload(hass))
            await asyncio.sleep(0.01)
            assert not cleanup.done()
            release.set()
            await cleanup
            events.append("cleaned up")
            assert events == ["written", "cleaned up"]
    asyncio.run(run())
