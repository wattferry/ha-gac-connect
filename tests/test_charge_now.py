"""Charge now also starts a new charge once one has ended (a one-time window, then the schedule off)."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.charge_now import ChargeNow, charge_now_request
from custom_components.gac_connect.command_tracking import async_send
from custom_components.gac_connect.settings import ChargeDraft
from test_autodetect import vehicle
from test_regressions import ACCEPTED

WINDOW = {"dailyReservationStartTime": 1792207200000, "dailyReservationStopTime": 1792207320000}


def report(status, mode, plug=1, **charging):
    return decode_status({"chargingAccessors": [{"chargingStatus": status, "chargingMode": mode, **WINDOW, **charging}],
                          "chargerAccessors": [{"plug": plug, "lock": 0}]})


def prepared(entry, c, status):
    c.client.charge_now = AsyncMock(return_value=ACCEPTED)
    c.client.restart_charging = AsyncMock(return_value=ACCEPTED)
    c.async_refresh_now = AsyncMock()
    entry.runtime_data.charge_draft = ChargeDraft()
    helper = entry.runtime_data.charge_now = ChargeNow(c)
    c.async_set_updated_data(status)
    return helper


def test_charge_now_only_switches_the_schedule_off_when_the_car_can_charge(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            prepared(entry, c, report(27, 2))       # waiting for a repeating schedule
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()):
                await async_send(c, "charge-now", charge_now_request(c))
            c.client.charge_now.assert_awaited_once_with("VIN", until_soc=False)
            c.client.restart_charging.assert_not_awaited()
    asyncio.run(run())


def test_an_ended_charge_is_started_again_then_the_schedule_switched_off(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                await async_send(c, "charge-now", charge_now_request(c))
                c.client.restart_charging.assert_awaited_once_with("VIN")
                c.client.charge_now.assert_not_awaited()
                assert helper.restarting
                assert await charge_now_request(c) is None      # a second press sends nothing more
                c.async_set_updated_data(report(2, 1))           # charging from the one-time window
                await asyncio.wait_for(helper._task, 1)
            c.client.charge_now.assert_awaited_once_with("VIN", until_soc=False)
            assert c.client.restart_charging.await_count == 1
    asyncio.run(run())


def test_without_a_charging_report_the_schedule_is_switched_off_anyway(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(27, 1, dailyReservationStartTime=0, dailyReservationStopTime=0))
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.01, 0.02)):
                await async_send(c, "charge-now", charge_now_request(c))   # "not set": restarted
                await asyncio.wait_for(helper._task, 1)
            assert c.async_refresh_now.await_count == 2
            c.client.charge_now.assert_awaited_once()
    asyncio.run(run())


def test_a_later_charging_request_cancels_the_switch_off(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 1))
            c.client.resume_schedule = AsyncMock(return_value=ACCEPTED)
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05,)):
                await async_send(c, "charge-now", charge_now_request(c))
                await async_send(c, "charge-resume", c.client.resume_schedule("VIN"))
                await asyncio.wait_for(helper._task, 1)
            c.client.charge_now.assert_not_awaited()
    asyncio.run(run())


def test_the_restart_window_does_not_replace_the_dashboard_draft():
    draft = ChargeDraft()
    draft.set(start="22:00", stop="06:00", days={"sat"})
    draft._reported = ("11:00", "11:11", 0, 0)
    draft.mark_sent(None, None, 0, True)
    draft.observe(decode_status({"chargingAccessors": [{"chargingMode": 1, "chargingEndType": 1, "weeklyReservation": 0,
                                                        "dailyReservationStartTime": 1792209600000,
                                                        "dailyReservationStopTime": 1792209600000}]}))
    assert (draft.start, draft.stop, draft.days) == ("22:00", "06:00", {"sat"})


def test_two_presses_at_once_send_one_restart(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            gate = asyncio.Event()

            async def slow_restart(vin):
                await gate.wait()
                return ACCEPTED
            c.client.restart_charging.side_effect = slow_restart
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (5,)):
                first = asyncio.create_task(async_send(c, "charge-now", charge_now_request(c)))
                second = asyncio.create_task(async_send(c, "charge-now", charge_now_request(c)))
                await asyncio.sleep(0.01)
                gate.set()
                await asyncio.gather(first, second)
                assert c.client.restart_charging.await_count == 1 and helper.restarting
                helper._task.cancel()
    asyncio.run(run())


def test_a_newer_schedule_made_while_the_switch_off_waits_its_turn_is_kept(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            c.client.set_charge_window = AsyncMock(return_value=ACCEPTED)
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                await async_send(c, "charge-now", charge_now_request(c))
                gate = asyncio.Event()

                async def slow_window(*args, **kwargs):
                    await gate.wait()
                    return ACCEPTED
                c.client.set_charge_window.side_effect = slow_window
                newer = asyncio.create_task(async_send(c, "charge-window", c.client.set_charge_window(
                    "VIN", "23:00", "05:00", weekly=127, until_soc=False)))
                await asyncio.sleep(0.01)                        # the newer window is on its way out
                c.async_set_updated_data(report(2, 1))           # charging: the switch-off comes due and waits
                await asyncio.sleep(0.01)
                gate.set()
                await newer
                await asyncio.wait_for(helper._task, 1)
            c.client.set_charge_window.assert_awaited_once()
            c.client.charge_now.assert_not_awaited()             # the newer schedule is not switched off
            assert not helper.restarting
    asyncio.run(run())


def test_a_newer_schedule_cannot_overtake_a_switch_off_already_on_its_way(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            order, gate = [], asyncio.Event()

            async def slow_off(vin, until_soc=False):
                await gate.wait()                                 # waiting for its turn with the service
                order.append("schedule off")
                return ACCEPTED

            async def window(*args, **kwargs):
                order.append("newer window")
                return ACCEPTED
            c.client.set_charge_window = AsyncMock(side_effect=window)
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                await async_send(c, "charge-now", charge_now_request(c))
                c.client.charge_now.side_effect = slow_off
                c.async_set_updated_data(report(2, 1))
                await asyncio.sleep(0.01)                        # the switch-off is being sent
                newer = asyncio.create_task(async_send(c, "charge-window", c.client.set_charge_window(
                    "VIN", "23:00", "05:00", weekly=127, until_soc=False)))
                await asyncio.sleep(0.01)
                gate.set()
                await newer
                await asyncio.wait_for(helper._task, 1)
            assert order == ["schedule off", "newer window"]   # the newer choice is the one left in place
    asyncio.run(run())


def _window(c):
    return async_send(c, "charge-window", c.client.set_charge_window("VIN", "23:00", "05:00", weekly=127,
                                                                      until_soc=False))


def test_a_schedule_made_while_the_restart_is_being_accepted_is_kept(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            order, gate = [], asyncio.Event()

            async def slow_restart(vin):
                order.append("restart")
                await gate.wait()
                return ACCEPTED
            c.client.restart_charging.side_effect = slow_restart
            c.client.set_charge_window = AsyncMock(side_effect=lambda *a, **k: order.append("window") or ACCEPTED)
            c.client.charge_now.side_effect = lambda *a, **k: order.append("schedule off") or ACCEPTED
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                press = asyncio.create_task(async_send(c, "charge-now", charge_now_request(c)))
                await asyncio.sleep(0.01)                        # the restart is out, awaiting acceptance
                newer = asyncio.create_task(_window(c))
                await asyncio.sleep(0.01)
                gate.set()
                await asyncio.gather(press, newer)
                c.async_set_updated_data(report(2, 1))
                await asyncio.wait_for(helper._task, 1)
            assert order == ["restart", "window"]
    asyncio.run(run())


def test_a_schedule_queued_after_charge_now_behind_another_request_is_kept(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            gate, order = asyncio.Event(), []

            async def slow_resume(vin):
                await gate.wait()
                return ACCEPTED
            c.client.resume_schedule = AsyncMock(side_effect=slow_resume)
            c.client.restart_charging.side_effect = lambda vin: order.append("restart") or ACCEPTED
            c.client.set_charge_window = AsyncMock(side_effect=lambda *a, **k: order.append("window") or ACCEPTED)
            c.client.charge_now.side_effect = lambda *a, **k: order.append("schedule off") or ACCEPTED
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                earlier = asyncio.create_task(async_send(c, "charge-resume", c.client.resume_schedule("VIN")))
                await asyncio.sleep(0.01)
                press = asyncio.create_task(async_send(c, "charge-now", charge_now_request(c)))
                newer = asyncio.create_task(_window(c))
                await asyncio.sleep(0.01)
                gate.set()
                await asyncio.gather(earlier, press, newer)
                c.async_set_updated_data(report(2, 1))
                if helper._task is not None:
                    await asyncio.wait_for(helper._task, 1)
            assert "schedule off" not in order and order[-1] == "window"
    asyncio.run(run())


def test_charge_now_again_with_another_stopping_rule_is_the_one_followed(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                await async_send(c, "charge-now", charge_now_request(c, until_soc=False))
                await async_send(c, "charge-now", charge_now_request(c, until_soc=True))
                c.async_set_updated_data(report(2, 1))
                await asyncio.wait_for(helper._task, 1)
            assert c.client.restart_charging.await_count == 1
            c.client.charge_now.assert_awaited_once_with("VIN", until_soc=True)
    asyncio.run(run())


def test_charge_now_again_queued_behind_a_slow_request_still_sets_the_stopping_rule(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            gate = asyncio.Event()

            async def slow_window(*args, **kwargs):
                await gate.wait()
                return ACCEPTED
            c.client.set_charge_window = AsyncMock(side_effect=slow_window)
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                await async_send(c, "charge-now", charge_now_request(c, until_soc=False))
                held = asyncio.create_task(_window(c))                       # in transport
                await asyncio.sleep(0.01)
                again = asyncio.create_task(async_send(c, "charge-now", charge_now_request(c, until_soc=True)))
                c.async_set_updated_data(report(2, 1))                       # the follow-up queues too
                await asyncio.sleep(0.01)
                gate.set()
                await asyncio.gather(held, again)
                await asyncio.wait_for(helper._task, 1)
            c.client.charge_now.assert_awaited_once_with("VIN", until_soc=True)
    asyncio.run(run())


def test_a_repeat_cancelled_before_its_turn_does_not_stop_the_switch_off(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (hass, entry, c):
            helper = prepared(entry, c, report(4, 0))
            entry.async_on_unload(c.async_add_listener(lambda: helper.observe(c.data)))
            gate = asyncio.Event()

            async def slow_restart(vin):
                await gate.wait()
                return ACCEPTED
            c.client.restart_charging.side_effect = slow_restart
            with patch("custom_components.gac_connect.command_tracking.POLL_DELAYS", ()), \
                    patch("custom_components.gac_connect.charge_now.RESTART_READS", (0.05, 5)):
                first = asyncio.create_task(async_send(c, "charge-now", charge_now_request(c)))
                await asyncio.sleep(0.01)
                repeat = asyncio.create_task(async_send(c, "charge-now", charge_now_request(c)))
                await asyncio.sleep(0.01)
                repeat.cancel()                                              # never sent
                gate.set()
                await first
                with pytest.raises(asyncio.CancelledError):
                    await repeat
                c.async_set_updated_data(report(2, 1))
                await asyncio.wait_for(helper._task, 1)
            c.client.charge_now.assert_awaited_once()                        # the switch-off still went out
    asyncio.run(run())


def test_the_latest_standing_choice_wins_when_a_middle_one_is_cancelled():
    from custom_components.gac_connect.command_tracking import ChargingRequests

    queue = ChargingRequests()
    one, two, three = queue.choose("charge-now"), queue.choose("charge-window"), queue.choose("charge-resume")
    queue.withdraw(two)
    assert (queue.generation, queue.latest) == (three, "charge-resume")
    queue.withdraw(three)
    assert (queue.generation, queue.latest) == (one, "charge-now")
    queue.sent(one)
    assert queue.generation == one
