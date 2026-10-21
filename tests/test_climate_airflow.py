"""Calibrated outlet labels and confirmation of optional manual-start writes."""
import asyncio
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from gac_connect.commands import CATALOG, build_body
from gac_connect.errors import GacError
from gac_connect.models import VehicleStatus
from gac_connect.push import PushResult
from custom_components.gac_connect.cabin import controller
from custom_components.gac_connect.climate import AIRFLOW_NAMES
from test_autodetect import vehicle
from test_regressions import ACCEPTED, climate, scheduled  # noqa: F401


@pytest.mark.parametrize("mode,code", [("cabin", 1), ("cabin_feet", 2), ("feet", 3), ("feet_windscreen", 4)])
@pytest.mark.parametrize("running", [False, True])
def test_verified_codes_are_visible_and_outlet_requests_omit_fan(mode, code, running):
    coordinator, entity = climate(VehicleStatus(ac_on=running, ac_target_temp_c=23, ac_fan_strength=3,
                                              ac_blowing_mode=code, power_on=True))
    assert entity.swing_mode == mode
    assert entity.swing_modes == ["cabin", "cabin_feet", "feet", "feet_windscreen"]
    assert entity.supported_features & ClimateEntityFeature.SWING_MODE
    coordinator.config_entry.options["ac_minutes"] = 5
    asyncio.run(entity.async_set_swing_mode(mode))
    coordinator.client.command.assert_awaited_once_with(
        "TESTVIN", "aircon-manual-on", temperature=23, currentDuration=5, blowingMode=code
    )
    call = coordinator.client.command.await_args
    assert build_body(CATALOG[call.args[1]], call.args[0], call.kwargs) == {
        "identifier": {"vin": "TESTVIN", "grade": 2, "duration": 5},
        "operations": [{"enableAutoMode": 0, "enableAirCompressor": 1,
                        "temperature": 23, "temperatureUnit": 0, "blowingMode": code}],
    }


@pytest.mark.parametrize("code", [None, -1, 0, 6, 8, True, "3", 3.5])
def test_unknown_outlet_codes_are_not_guessed(code):
    _, entity = climate(VehicleStatus(ac_on=True, ac_blowing_mode=code, power_on=True))
    assert entity.swing_mode is None
    assert entity.extra_state_attributes["reported_blowing_mode"] == code


@pytest.mark.parametrize("mode", ["off", "auto", "windscreen", "all", "3", 3, None, []])
def test_unmapped_selections_send_nothing(mode):
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_blowing_mode=1))
    with pytest.raises(ServiceValidationError):
        asyncio.run(entity.async_set_swing_mode(mode))
    coordinator.client.command.assert_not_awaited()


def test_pending_airflow_requires_fresh_outlet_report_and_follows_console_after_confirmation():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_blowing_mode=1, updated_ms=100, power_on=True))
    asyncio.run(entity.async_set_swing_mode("feet"))
    assert entity.swing_mode == "feet" and coordinator.data.ac_blowing_mode == 1
    assert entity.extra_state_attributes["reported_airflow"] == "cabin"
    for changes in ({"updated_ms": 101}, {"ac_blowing_mode": 3, "updated_ms": 99}):
        coordinator.data = replace(coordinator.data, **changes)
        entity._handle_coordinator_update()
        assert entity._cabin._req is not None
    coordinator.data = replace(coordinator.data, ac_blowing_mode=3, updated_ms=102)
    entity._handle_coordinator_update()
    assert entity._cabin._req is None
    coordinator.data = replace(coordinator.data, ac_blowing_mode=5)
    entity._handle_coordinator_update()
    assert entity.swing_mode is None
    assert entity.extra_state_attributes["reported_airflow"] == "windscreen"


@pytest.mark.parametrize("failure", ["result", "transport", "expiry"])
def test_failed_outlet_selection_restores_vehicle_reading_without_auto_fallback(failure):
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_blowing_mode=1, power_on=True))
    if failure == "transport":
        coordinator.client.command.side_effect = GacError("failed")
        with pytest.raises(HomeAssistantError):
            asyncio.run(entity.async_set_swing_mode("feet"))
    else:
        with patch("custom_components.gac_connect.cabin.monotonic", return_value=100):
            asyncio.run(entity.async_set_swing_mode("feet"))
        if failure == "result":
            entity._cabin._handle_result(PushResult(False, "13101", None, {}, session_id="s1"))
        else:
            with patch("custom_components.gac_connect.cabin.monotonic", return_value=281):
                entity._cabin._expired(None)
    assert entity.swing_mode == "cabin" and entity._cabin._req is None
    assert coordinator.client.command.await_count == 1


def test_temperature_and_fan_changes_preserve_pending_outlet_expectation_without_replaying_it():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_fan_strength=3, ac_blowing_mode=1, power_on=True))

    async def run():
        await entity.async_set_swing_mode("feet")
        await entity.async_set_fan_mode("6")
        await entity.async_set_temperature(temperature=22)

    asyncio.run(run())
    calls = coordinator.client.command.await_args_list
    assert calls[1].kwargs == {"temperature": 23, "currentDuration": 30, "windStrength": 6}
    assert calls[2].kwargs == {"temperature": 22}
    assert entity.swing_mode == "feet" and entity.fan_mode == "6"
    for changes in ({"ac_target_temp_c": 22}, {"ac_fan_strength": 6}):
        coordinator.data = replace(coordinator.data, **changes)
        entity._handle_coordinator_update()
        assert entity._cabin._req is not None
    coordinator.data = replace(coordinator.data, ac_blowing_mode=3)
    entity._handle_coordinator_update()
    assert entity._cabin._req is None


def test_auto_preset_discards_pending_manual_outlet_selection():
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_blowing_mode=1, power_on=True))

    async def run():
        await entity.async_set_swing_mode("feet")
        await entity.async_set_preset_mode("cooling")

    asyncio.run(run())
    assert coordinator.client.command.await_args.args[1] == "aircon-on"
    assert "ac_blowing_mode" not in entity._cabin._req.expected
    assert entity.swing_mode == "cabin"


def test_command_ledger_keeps_outlet_expectation_when_replaced_by_fan_change(tmp_path):
    async def run():
        async with vehicle(tmp_path) as (_, _, coordinator):
            coordinator.client.climate_manual_on = AsyncMock(return_value=ACCEPTED)
            coordinator.data = VehicleStatus(ac_on=True, ac_target_temp_c=23, ac_fan_strength=3, ac_blowing_mode=1, power_on=True)
            cabin = controller(coordinator)
            try:
                await cabin.async_set_blowing_mode(3)
                await cabin.async_set_fan_speed(6)
                assert coordinator.commands.records[0].state == "superseded"
                coordinator.commands.observe(replace(coordinator.data, ac_fan_strength=6))
                assert coordinator.commands.state == "pending"
                coordinator.commands.observe(replace(coordinator.data, ac_fan_strength=6, ac_blowing_mode=3))
                assert coordinator.commands.state == "confirmed"
            finally:
                cabin._cancel_expiry()

    asyncio.run(run())


def test_climate_translates_every_calibrated_outlet_and_enables_only_implemented_features():
    _, entity = climate(VehicleStatus())
    root = Path(__file__).resolve().parents[1]
    strings = json.loads((root / "custom_components/gac_connect/translations/en.json").read_text())
    labels = strings["entity"]["climate"]["climate"]["state_attributes"]["swing_mode"]["state"]
    assert set(labels) == set(AIRFLOW_NAMES.values())
    assert labels["feet_windscreen"] == "Feet + Windscreen"
    assert int(entity.supported_features) == 441


@pytest.mark.parametrize("power", [False, None])
def test_outlet_changes_require_reported_vehicle_power_but_other_climate_controls_still_work(power):
    coordinator, entity = climate(VehicleStatus(ac_on=True, ac_target_temp_c=23, power_on=power))

    async def run():
        with pytest.raises(ServiceValidationError, match="fully on"):
            await entity.async_set_swing_mode("feet")
        coordinator.client.command.assert_not_awaited()
        assert entity._cabin._req is None
        await entity.async_set_temperature(temperature=22)
        await entity.async_set_fan_mode("6")
        await entity.async_turn_off()

    asyncio.run(run())
    assert [call.args[1] for call in coordinator.client.command.await_args_list] == [
        "aircon-temperature", "aircon-manual-on", "aircon-off",
    ]


@pytest.mark.parametrize("code,name", [(5, "windscreen"), (7, "all")])
def test_console_only_outlets_remain_readable_without_offering_unverified_writes(code, name):
    _, entity = climate(VehicleStatus(ac_on=True, ac_blowing_mode=code))
    assert entity.swing_mode is None
    assert name not in entity.swing_modes
    assert entity.extra_state_attributes["reported_airflow"] == name
    assert entity.extra_state_attributes["reported_blowing_mode"] == code
