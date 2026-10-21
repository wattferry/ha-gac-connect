"""Verified manual startup, blower choices and shared command confirmation."""
import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from gac_connect.commands import CATALOG, build_body
from gac_connect.errors import GacError
from gac_connect.models import VehicleStatus
from gac_connect.push import PushResult
from custom_components.gac_connect.cabin import controller
from custom_components.gac_connect.sensor import SENSORS
from custom_components.gac_connect.switch import GacClimateSwitch
from test_autodetect import vehicle
from test_regressions import ACCEPTED, climate, scheduled  # noqa: F401


@pytest.mark.parametrize("speed", range(1, 11))
@pytest.mark.parametrize("automatic", [False, True])
def test_climate_displays_numeric_speed_even_with_unreliable_auto_flag(speed, automatic):
    _, entity = climate(VehicleStatus(ac_on=True, ac_fan_strength=speed, ac_auto_on=automatic))
    assert entity.fan_modes == ["off", *(str(value) for value in range(1, 8))]
    assert entity.supported_features & ClimateEntityFeature.FAN_MODE
    assert entity.fan_mode == (str(speed) if speed <= 7 else None)
    assert entity.extra_state_attributes["reported_fan_strength"] == speed


@pytest.mark.parametrize("speed", [None, -1, 11, 1.5, True, "6", float("nan"), float("inf")])
def test_unknown_fan_readings_are_not_presented_as_a_valid_choice(speed):
    _, entity = climate(VehicleStatus(ac_on=True, ac_fan_strength=speed))
    assert entity.fan_mode is None


@pytest.mark.parametrize("speed", [1, 6, 7])
@pytest.mark.parametrize("running", [False, True])
def test_selected_speed_uses_verified_manual_start_and_leaves_outlets_absent(speed, running):
    coordinator, entity = climate(VehicleStatus(ac_on=running, ac_target_temp_c=23,
                                              ac_fan_strength=3, ac_blowing_mode=2))
    coordinator.config_entry.options["ac_minutes"] = 5
    asyncio.run(entity.async_set_fan_mode(str(speed)))
    coordinator.client.command.assert_awaited_once_with(
        "TESTVIN", "aircon-manual-on", temperature=23, currentDuration=5, windStrength=speed
    )
    call = coordinator.client.command.await_args
    assert build_body(CATALOG[call.args[1]], call.args[0], call.kwargs) == {
        "identifier": {"vin": "TESTVIN", "grade": 2, "duration": 5},
        "operations": [{"enableAutoMode": 0, "enableAirCompressor": 1,
                        "temperature": 23, "temperatureUnit": 0, "windStrength": speed}],
    }
    assert entity.fan_mode == str(speed)
    assert coordinator.data.ac_fan_strength == 3
    assert entity.hvac_mode == HVACMode.HEAT_COOL


@pytest.mark.parametrize("use_switch", [False, True])
@pytest.mark.parametrize("reported_speed", [None, 10])
def test_ordinary_on_omits_fan_even_with_missing_or_console_only_telemetry(use_switch, reported_speed):
    coordinator, entity = climate(VehicleStatus(ac_on=False, ac_target_temp_c=23,
                                              ac_fan_strength=reported_speed))
    control = GacClimateSwitch(coordinator) if use_switch else entity
    asyncio.run(control.async_turn_on())
    call = coordinator.client.command.await_args
    assert build_body(CATALOG[call.args[1]], call.args[0], call.kwargs)["operations"] == [
        {"enableAutoMode": 0, "enableAirCompressor": 1, "temperature": 23, "temperatureUnit": 0}
    ]


def test_fan_off_uses_dedicated_stop_and_existing_sensor_remains():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_fan_strength=6))
    asyncio.run(entity.async_set_fan_mode("off"))
    coordinator.client.command.assert_awaited_once_with("TESTVIN", "aircon-off")
    assert entity.fan_mode == "off"
    sensor = next(description for description in SENSORS if description.key == "ac_fan_strength")
    assert sensor.value(coordinator.data) == 6  # telemetry never becomes optimistic


@pytest.mark.parametrize("mode", ["0", "8", "9", "10", "11", "auto", "6.0", "bad", 6, None])
def test_invalid_choices_send_nothing(mode):
    coordinator, entity = climate(VehicleStatus(ac_on=True))
    with pytest.raises(ServiceValidationError):
        asyncio.run(entity.async_set_fan_mode(mode))
    coordinator.client.command.assert_not_awaited()


@pytest.mark.parametrize("speed", [0, 8, 9, 10, 11, True, "6", 6.5, None])
def test_shared_controller_rejects_invalid_remote_speeds_before_queueing_a_command(speed):
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_fan_strength=3))
    with pytest.raises(ServiceValidationError, match="Remote fan speed must be an integer from 1 to 7"):
        asyncio.run(entity._cabin.async_set_fan_speed(speed))
    coordinator.client.command.assert_not_awaited()
    assert entity._cabin._req is None and entity.fan_mode == "3"


@pytest.mark.parametrize("speed", [8, 9, 10])
def test_console_only_speed_is_reported_without_becoming_a_remote_choice(speed):
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_fan_strength=speed))
    sensor = next(description for description in SENSORS if description.key == "ac_fan_strength")
    assert sensor.value(coordinator.data) == speed
    assert entity.extra_state_attributes["reported_fan_strength"] == speed
    assert entity._cabin.fan_mode == str(speed)
    assert entity.fan_mode is None and str(speed) not in entity.fan_modes
    coordinator.client.command.assert_not_awaited()


def test_confirmation_requires_fan_and_temperature_in_a_fresh_report():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_fan_strength=3,
                                              updated_ms=100))
    asyncio.run(entity.async_set_fan_mode("6"))
    for fields in ({"ac_target_temp_c": 24}, {"ac_fan_strength": 6, "updated_ms": 99}, {}):
        coordinator.data = replace(coordinator.data, **fields)
        entity._handle_coordinator_update()
        assert entity._cabin._req is not None
    coordinator.data = replace(coordinator.data, ac_target_temp_c=23, ac_fan_strength=6, updated_ms=101)
    entity._handle_coordinator_update()
    assert entity._cabin._req is None
    coordinator.data = replace(coordinator.data, ac_fan_strength=10)
    entity._handle_coordinator_update()
    assert entity.fan_mode is None
    assert entity.extra_state_attributes["reported_fan_strength"] == 10


@pytest.mark.parametrize("failure", ["result", "transport", "expiry"])
def test_failed_fan_selection_restores_reported_speed(failure):
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_fan_strength=3))
    if failure == "transport":
        coordinator.client.command.side_effect = GacError("failed")
        with pytest.raises(HomeAssistantError):
            asyncio.run(entity.async_set_fan_mode("6"))
    else:
        with patch("custom_components.gac_connect.cabin.monotonic", return_value=100):
            asyncio.run(entity.async_set_fan_mode("6"))
        assert entity.fan_mode == "6"
        if failure == "result":
            entity._cabin._handle_result(PushResult(False, "13101", None, {}, session_id="s1"))
        else:
            with patch("custom_components.gac_connect.cabin.monotonic", return_value=281):
                entity._cabin._expired(None)
    assert entity.fan_mode == "3" and entity._cabin._req is None
    assert coordinator.client.command.await_count == 1


@pytest.mark.parametrize("running", [False, True])
def test_temperature_adjustment_retains_unconfirmed_fan_selection(running):
    coordinator, entity = climate(VehicleStatus(ac_on=running, ac_target_temp_c=23, ac_fan_strength=3))

    async def run():
        await entity.async_set_fan_mode("6")
        await entity.async_set_temperature(temperature=22)

    asyncio.run(run())
    assert coordinator.client.command.await_args.args[1] == ("aircon-temperature" if running else "aircon-manual-on")
    assert coordinator.client.command.await_args.kwargs == {"temperature": 22, **({} if running else {"currentDuration": 30})}
    coordinator.data = replace(coordinator.data, ac_on=True, ac_target_temp_c=22)
    entity._handle_coordinator_update()
    assert entity.fan_mode == "6" and entity._cabin._req is not None
    coordinator.data = replace(coordinator.data, ac_fan_strength=6)
    entity._handle_coordinator_update()
    assert entity._cabin._req is None


def test_automatic_preset_replaces_pending_manual_fan_expectation():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_fan_strength=3))

    async def run():
        await entity.async_set_fan_mode("6")
        await entity.async_set_preset_mode("cooling")

    asyncio.run(run())
    assert coordinator.client.command.await_args.args[1] == "aircon-on"
    assert entity._cabin._req.expected == {"ac_on": True, "ac_target_temp_c": 18}
    assert entity.fan_mode == "3"


def test_command_ledger_requires_reported_fan_before_confirming(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            coordinator.client.climate_manual_on = AsyncMock(return_value=ACCEPTED)
            coordinator.client.climate_set_temperature = AsyncMock(return_value=ACCEPTED)
            coordinator.data = VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_fan_strength=3, updated_ms=100)
            cabin = controller(coordinator)
            try:
                await cabin.async_set_fan_speed(6)
                await cabin.async_set_temperature(22)
                assert coordinator.commands.records[0].state == "superseded"
                coordinator.commands.observe(replace(coordinator.data, ac_target_temp_c=22, updated_ms=101))
                assert coordinator.commands.state == "pending"
                coordinator.commands.observe(replace(coordinator.data, ac_target_temp_c=22,
                                                    ac_fan_strength=6, updated_ms=102))
                assert coordinator.commands.state == "confirmed"
            finally:
                cabin._cancel_expiry()

    asyncio.run(run())


def sent(coordinator):
    call = coordinator.client.command.await_args
    return call.args[1], build_body(CATALOG[call.args[1]], call.args[0], call.kwargs)["operations"][0]


@pytest.mark.parametrize("compressor,mode", [(False, HVACMode.FAN_ONLY), (True, HVACMode.HEAT_COOL),
                                             (None, HVACMode.HEAT_COOL)])
def test_reported_compressor_shows_fan_only_or_heat_cool(compressor, mode):
    _, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=32, ac_compressor_on=compressor))
    assert entity.hvac_modes == [HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.FAN_ONLY]
    assert entity.preset_modes == ["heating", "cooling"]
    assert entity.hvac_mode == mode
    assert entity.preset_mode == (None if mode == HVACMode.FAN_ONLY else "heating")


@pytest.mark.parametrize("running", [False, True])
def test_fan_only_runs_the_blower_alone_until_reported(running):
    coordinator, entity = climate(VehicleStatus(ac_on=running, ac_target_temp_c=23, ac_compressor_on=running,
                                              updated_ms=100))
    asyncio.run(entity.async_set_hvac_mode(HVACMode.FAN_ONLY))
    assert sent(coordinator) == ("aircon-manual-on", {"enableAutoMode": 0, "enableAirCompressor": 0,
                                                      "temperature": 23, "temperatureUnit": 0})
    assert entity.hvac_mode == HVACMode.FAN_ONLY
    coordinator.data = replace(coordinator.data, ac_on=True, ac_compressor_on=True, updated_ms=101)
    entity._handle_coordinator_update()
    assert entity._cabin._req is not None and entity.hvac_mode == HVACMode.FAN_ONLY
    coordinator.data = replace(coordinator.data, ac_compressor_on=False, updated_ms=102)
    entity._handle_coordinator_update()
    assert entity._cabin._req is None and entity.hvac_mode == HVACMode.FAN_ONLY


def test_speed_change_keeps_fan_only_and_heat_cool_restores_the_compressor():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_compressor_on=False))
    asyncio.run(entity.async_set_fan_mode("3"))
    assert sent(coordinator)[1]["enableAirCompressor"] == 0 and entity.hvac_mode == HVACMode.FAN_ONLY
    asyncio.run(entity.async_set_hvac_mode(HVACMode.HEAT_COOL))
    assert sent(coordinator)[1]["enableAirCompressor"] == 1 and entity.hvac_mode == HVACMode.HEAT_COOL
    assert entity._cabin._req.expected == {"ac_on": True, "ac_target_temp_c": 23, "ac_fan_strength": 3,
                                           "ac_compressor_on": True}


@pytest.mark.parametrize("use_switch", [False, True])
def test_ordinary_start_from_off_uses_the_compressor(use_switch):
    coordinator, entity = climate(VehicleStatus(ac_on=False, ac_target_temp_c=23, ac_compressor_on=False))
    control = GacClimateSwitch(coordinator) if use_switch else entity
    asyncio.run(control.async_turn_on())
    assert sent(coordinator)[1]["enableAirCompressor"] == 1
    assert entity.hvac_mode == HVACMode.HEAT_COOL
    assert "ac_compressor_on" not in entity._cabin._req.expected   # models without the reading still confirm


def test_temperature_with_fan_only_starts_the_blower_alone_and_plain_changes_keep_it():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_compressor_on=True))
    asyncio.run(entity.async_set_temperature(temperature=21, hvac_mode=HVACMode.FAN_ONLY))
    assert sent(coordinator) == ("aircon-manual-on", {"enableAutoMode": 0, "enableAirCompressor": 0,
                                                      "temperature": 21, "temperatureUnit": 0})
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_compressor_on=False))
    asyncio.run(entity.async_set_temperature(temperature=21))
    assert sent(coordinator)[0] == "aircon-temperature" and entity.hvac_mode == HVACMode.FAN_ONLY


@pytest.mark.parametrize("mode", [HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO, HVACMode.DRY])
def test_unsupported_modes_send_nothing(mode):
    coordinator, entity = climate(VehicleStatus(ac_on=True))
    with pytest.raises(ServiceValidationError, match="Fan only"):
        asyncio.run(entity.async_set_hvac_mode(mode))
    coordinator.client.command.assert_not_awaited()


@pytest.mark.parametrize("preset", ["fan_only", "ac", "eco"])
def test_presets_are_only_the_app_buttons(preset):
    coordinator, entity = climate(VehicleStatus(ac_on=True))
    with pytest.raises(ServiceValidationError, match="heating or cooling"):
        asyncio.run(entity.async_set_preset_mode(preset))
    coordinator.client.command.assert_not_awaited()
