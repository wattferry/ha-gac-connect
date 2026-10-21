"""Controls must not revert to cached reports before an accepted action settles."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.binary_sensor import BINARY_SENSORS, GacBinaryEntity
from custom_components.gac_connect.cover import COVERS, GacCoverEntity
from custom_components.gac_connect.lock import GacLock
from custom_components.gac_connect.switch import GacChargeSwitch
from gac_connect.errors import CommandError
from gac_connect.models import ChargingMode, VehicleStatus
from gac_connect.push import PushResult
from homeassistant.exceptions import HomeAssistantError

from test_regressions import ACCEPTED, coord


@pytest.fixture(autouse=True)
def timers(monkeypatch):
    callbacks = []

    def later(hass, seconds, callback):
        timer = SimpleNamespace(delay=seconds, callback=callback, cancel=Mock())
        callbacks.append(timer)
        return timer.cancel

    monkeypatch.setattr("custom_components.gac_connect.transition.async_call_later", later)
    return callbacks


def report(kind, target, updated=10):
    if kind == "lock":
        return decode_status({"doorAccessors": [
            {"door": i, "lock": (0 if target else 1) if i < 3 else -1} for i in range(1, 5)
        ]}, updated_ms=updated)
    if kind == "charge":
        return VehicleStatus(charging_mode=ChargingMode.SCHEDULED if target else ChargingMode.FREE, updated_ms=updated)
    field = {"windows": "window_open", "sunroof": "sunroof_open", "tailgate": "hatch_open"}[kind]
    return VehicleStatus(**{field: not target, "updated_ms": updated})


def control(kind, target):
    coordinator = coord(report(kind, not target))
    coordinator.config_entry.data["model"] = "Aion UT"
    coordinator.config_entry.options["experimental_pinless_unlock"] = True
    if kind == "lock":
        entity = GacLock(coordinator)
        action = entity.async_lock if target else entity.async_unlock
    elif kind == "charge":
        coordinator.client.charge_now = AsyncMock(return_value=ACCEPTED)
        coordinator.client.resume_schedule = AsyncMock(return_value=ACCEPTED)
        entity = GacChargeSwitch(coordinator)
        action = entity.async_turn_on if target else entity.async_turn_off
    else:
        entity = GacCoverEntity(coordinator, next(d for d in COVERS if d.key == kind))
        action = entity.async_close_cover if target else entity.async_open_cover
    entity.async_write_ha_state = Mock()
    return coordinator, entity, action


@pytest.mark.parametrize("kind,target", [
    (kind, target) for kind in ("lock", "windows", "sunroof", "tailgate") for target in (False, True)
] + [("charge", True), ("charge", False)])
def test_control_holds_transition_until_a_new_matching_report(kind, target, timers):
    coordinator, entity, action = control(kind, target)
    asyncio.run(action())
    assert entity._requested_state is target
    timer = timers[-1]
    if kind == "lock":
        assert entity.state == ("locking" if target else "unlocking")
        sensor = GacBinaryEntity(coordinator, next(d for d in BINARY_SENSORS if d.key == "locked"))
        assert sensor.is_on is target  # Last observed state, not a fabricated command result.
    elif kind == "charge":
        assert entity.is_on is target
        if target:
            coordinator.client.resume_schedule.assert_awaited_once_with("TESTVIN")
        else:
            coordinator.client.charge_now.assert_awaited_once_with("TESTVIN", until_soc=False)
    else:
        assert entity.state == ("closing" if target else "opening")
    # An auto-detect notification of the existing report is not confirmation.
    entity._handle_coordinator_update()
    assert entity._requested_state is target
    coordinator.data = report(kind, not target, 20)
    entity._handle_coordinator_update()
    assert entity._requested_state is target
    # An out-of-order report with the requested value must not settle the action.
    coordinator.data = report(kind, target, 9)
    entity._handle_coordinator_update()
    assert entity._requested_state is target
    coordinator.data = report(kind, target, 30)
    entity._handle_coordinator_update()
    assert entity._requested_state is None
    timer.cancel.assert_called_once()
    if kind == "lock":
        assert entity.state == ("locked" if target else "unlocked")
        assert sensor.is_on is not target
    # Later physical changes become authoritative when the next poll arrives.
    coordinator.data = report(kind, not target, 40)
    entity._handle_coordinator_update()
    assert entity._reported_state() is not target
    assert entity._requested_state is None


@pytest.mark.parametrize("timestamp", [None, 10, 11])
def test_changed_telemetry_can_confirm_without_an_advancing_backend_timestamp(timestamp):
    coordinator, entity, action = control("lock", False)
    asyncio.run(action())
    coordinator.data = report("lock", False, timestamp)
    entity._handle_coordinator_update()
    assert entity.state == "unlocked"


def test_transition_expires_with_a_real_home_assistant_timer(monkeypatch, tmp_path):
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.event import async_call_later

    monkeypatch.setattr("custom_components.gac_connect.transition.async_call_later", async_call_later)
    monkeypatch.setattr("custom_components.gac_connect.transition.REQUEST_SECONDS", 0.02)

    async def run():
        coordinator, entity, action = control("lock", False)
        coordinator.hass = HomeAssistant(str(tmp_path))
        await action()
        assert entity.state == "unlocking"
        await asyncio.sleep(0.05)
        assert entity.state == "locked"
        assert entity._expire is None

    asyncio.run(run())


def test_successful_push_does_not_claim_a_lock_report_that_has_not_arrived():
    _, entity, action = control("lock", True)
    asyncio.run(action())
    entity._handle_result(PushResult(True, "0000", None, {}, session_id="s1", vin="TESTVIN"))
    assert entity.state == "locking"
    assert entity.is_locked is False


def test_only_a_matched_rejection_clears_the_transition():
    _, entity, action = control("lock", False)
    asyncio.run(action())
    for session, vin in [(None, "TESTVIN"), ("other", "TESTVIN"), ("s1", "OTHER")]:
        entity._handle_result(PushResult(False, "13101", None, {}, session_id=session, vin=vin))
        assert entity.state == "unlocking"
    entity._handle_result(PushResult(False, "13101", None, {}, session_id="s1", vin="TESTVIN"))
    assert entity.state == "locked"


def test_rejection_before_acceptance_is_replayed_without_leaving_a_timer(timers):
    coordinator, entity, action = control("sunroof", False)

    async def request(*args, **kwargs):
        entity._handle_result(PushResult(False, "13101", None, {}, session_id="s1", vin="TESTVIN"))
        return ACCEPTED

    coordinator.client.command.side_effect = request
    asyncio.run(action())
    assert entity.state == "closed"
    assert entity._expire is None
    assert all(timer.cancel.called for timer in timers)


@pytest.mark.parametrize("cancel", [False, True])
def test_failed_second_action_restores_the_previous_pending_action(cancel):
    coordinator, entity, action = control("lock", False)

    async def run():
        await action()
        deadline = entity._requested_until
        failure = asyncio.CancelledError() if cancel else CommandError("refused")
        coordinator.client.command.side_effect = failure
        with pytest.raises(asyncio.CancelledError if cancel else HomeAssistantError):
            await entity.async_lock()
        assert entity.state == "unlocking"
        assert entity._requested_until == deadline
        assert entity._session_id == "s1"

    asyncio.run(run())


def test_expiry_returns_to_reported_state_without_needing_another_poll(timers):
    _, entity, action = control("lock", False)
    with patch("custom_components.gac_connect.transition.monotonic", return_value=100):
        asyncio.run(action())
    assert entity.state == "unlocking"
    with patch("custom_components.gac_connect.transition.monotonic", return_value=281):
        timers[-1].callback(None)
    assert entity.state == "locked"
    assert entity._expire is None


def test_commands_on_the_same_control_are_serialized():
    coordinator, entity, action = control("lock", False)

    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        async def request(vin, command):
            if command == "unlock":
                started.set()
                await release.wait()
            return ACCEPTED

        coordinator.client.command.side_effect = request
        first = asyncio.create_task(action())
        await started.wait()
        second = asyncio.create_task(entity.async_lock())
        await asyncio.sleep(0)
        assert coordinator.client.command.await_count == 1
        release.set()
        await asyncio.gather(first, second)
        assert entity.state == "locking"

    asyncio.run(run())


def test_entity_removal_cancels_pending_timer(timers):
    from custom_components.gac_connect.entity import GacEntity

    _, entity, action = control("windows", False)
    cleanup = []
    entity.async_on_remove = cleanup.append

    async def run():
        with patch.object(GacEntity, "async_added_to_hass", new=AsyncMock()):
            await entity.async_added_to_hass()
        await action()
        for remove in cleanup:
            remove()
        assert entity._expire is None
        assert entity._requested_state is None
        assert timers[-1].cancel.called

    asyncio.run(run())


@pytest.mark.parametrize("key,field", [("steering_heat", "steering_heat_on"), ("lights", "lights_on")])
def test_reported_switches_keep_requested_state_through_stale_polls(key, field, monkeypatch):
    from custom_components.gac_connect.switch import SWITCHES, GacCommandSwitch

    monkeypatch.setattr("custom_components.gac_connect.requested.async_call_later", Mock(return_value=Mock()))
    coordinator = coord(VehicleStatus(**{field: False}))
    entity = GacCommandSwitch(coordinator, next(d for d in SWITCHES if d.key == key))
    entity.hass = coordinator.hass
    entity.async_write_ha_state = Mock()
    asyncio.run(entity.async_turn_on())
    coordinator.data = VehicleStatus(**{field: False})
    entity._handle_coordinator_update()
    assert entity.is_on is True
    assert getattr(coordinator.data, field) is False
    coordinator.data = VehicleStatus(**{field: True})
    entity._handle_coordinator_update()
    assert entity._requested is None and entity.is_on is True
    coordinator.async_schedule_command_refresh.assert_called_once()


def test_climate_controls_keep_target_while_actual_temperature_remains_reported(monkeypatch):
    from custom_components.gac_connect.climate import GacClimate
    from custom_components.gac_connect.switch import GacClimateSwitch

    monkeypatch.setattr("custom_components.gac_connect.cabin.async_call_later", Mock(return_value=Mock()))
    coordinator = coord(VehicleStatus(ac_on=False, ac_target_temp_c=24, cabin_temp_c=30))
    climate = GacClimate(coordinator)
    switch = GacClimateSwitch(coordinator)
    climate.async_write_ha_state = Mock()
    switch.async_write_ha_state = Mock()
    asyncio.run(climate.async_set_temperature(temperature=22, hvac_mode="heat_cool"))
    coordinator.data = VehicleStatus(ac_on=False, ac_target_temp_c=24, cabin_temp_c=30)
    climate._handle_coordinator_update()
    assert climate.target_temperature == 22 and switch.is_on is True
    assert climate.current_temperature == 30
    coordinator.data = VehicleStatus(ac_on=True, ac_target_temp_c=22, cabin_temp_c=28)
    climate._handle_coordinator_update()
    assert climate.target_temperature == 22 and switch.is_on is True
    assert climate.current_temperature == 28
    assert climate._cabin._req is None
    coordinator.async_schedule_command_refresh.assert_called_once()


@pytest.mark.parametrize("surface", ["switch", "mode", "temperature"])
def test_fridge_controls_share_confirmation_without_fabricating_sensor_readings(surface, monkeypatch):
    from custom_components.gac_connect.fridge import FridgeController
    from custom_components.gac_connect.number import GacFridgeTemperature
    from custom_components.gac_connect.select import GacFridgeModeSelect
    from custom_components.gac_connect.sensor import FRIDGE_SENSORS, GacSensorEntity
    from custom_components.gac_connect.switch import GacFridgeSwitch

    monkeypatch.setattr("custom_components.gac_connect.fridge.async_call_later", Mock(return_value=Mock()))
    initial = VehicleStatus(fridge_mode="refrigerate" if surface == "temperature" else "off",
                            fridge_temp_c=4, fridge_fitted=True, fridge_keep_minutes=0)
    coordinator = coord(initial)
    with patch("custom_components.gac_connect.fridge.Store"):
        controller = FridgeController(coordinator.hass, coordinator.config_entry, coordinator)
    coordinator.config_entry.runtime_data = SimpleNamespace(fridge=controller)
    controller.sync()
    switch = GacFridgeSwitch(coordinator)
    select = GacFridgeModeSelect(coordinator)
    number = GacFridgeTemperature(coordinator)
    sensor = GacSensorEntity(coordinator, next(d for d in FRIDGE_SENSORS if d.key == "fridge_time_left"))
    for entity in (switch, select, number):
        entity.async_write_ha_state = Mock()
    action = {"switch": switch.async_turn_on, "mode": lambda: select.async_select_option("heat"),
              "temperature": lambda: number.async_set_native_value(6)}[surface]
    asyncio.run(action())
    target_mode, target_temp = controller.pending_option, controller.pending_temp
    coordinator.data = VehicleStatus(**initial.__dict__)
    switch._handle_coordinator_update()
    assert switch.is_on is True and select.current_option == target_mode
    assert number.native_value == target_temp
    assert sensor.native_value == 0
    assert controller._req is not None
    coordinator.data = VehicleStatus(fridge_mode=target_mode, fridge_temp_c=target_temp,
                                    fridge_fitted=True, fridge_keep_minutes=12)
    number._handle_coordinator_update()
    assert controller._req is None
    assert select.current_option == target_mode and number.native_value == target_temp
    assert sensor.native_value == 12
    coordinator.async_schedule_command_refresh.assert_called_once()
