"""Remote cabin A/C with a shared temperature selection and command queue."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import ATTR_HVAC_MODE
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry, cabin
from .coordinator import GacCoordinator
from .entity import GacEntity
from .entity_filter import add_configured_entities

PRESET_HEATING, PRESET_COOLING = "heating", "cooling"
# Outlet codes calibrated on an Aion UT's console; 1–4 also worked remotely there. Each is
# offered where the car's capability list includes it, and console reports can show the rest.
AIRFLOW_NAMES = {1: "cabin", 2: "cabin_feet", 3: "feet", 4: "feet_windscreen", 5: "windscreen", 7: "all"}


async def async_setup_entry(hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback) -> None:
    add_configured_entities(entry, add_entities, "climate", [GacClimate(entry.runtime_data.coordinator)])


class GacClimate(GacEntity, ClimateEntity):
    _attr_translation_key = "climate"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_preset_modes = [PRESET_HEATING, PRESET_COOLING]
    _attr_target_temperature_step = 1.0
    # The console can report half degrees; the app's remote control uses whole degrees.
    _attr_precision = PRECISION_HALVES
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "climate")
        # Fan only is the console's Fan: the blower runs without the compressor.
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.FAN_ONLY]
        self._cabin = cabin.controller(coordinator)
        # The car's remote choices; a refreshed capability list reloads the entry.
        low, high = self._cabin.temperature_range or cabin.DEFAULT_TEMPERATURE_RANGE
        self._attr_min_temp, self._attr_max_temp = float(low), float(high)
        # GAC 2.0.32 uses automatic A/C at the maximum/minimum setpoint for these buttons.
        self._presets = {PRESET_HEATING: float(high), PRESET_COOLING: float(low)}
        self._attr_fan_modes = ["off", *(str(speed) for speed in self._cabin.fan_speeds)]
        self._airflow = {AIRFLOW_NAMES[code]: code for code in self._cabin.blowing_modes if code in AIRFLOW_NAMES}
        self._attr_swing_modes = list(self._airflow)
        features = (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON
                    | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.PRESET_MODE)
        if self._cabin.fan_speeds:
            features |= ClimateEntityFeature.FAN_MODE
        if self._airflow:
            features |= ClimateEntityFeature.SWING_MODE
        self._attr_supported_features = features

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._cabin.add_listener(self.async_write_ha_state))

    @property
    def current_temperature(self) -> float | None:
        return self.status.cabin_temp_c if self.status else None

    @property
    def target_temperature(self) -> float:
        return self._cabin.target

    @property
    def hvac_mode(self) -> HVACMode | None:
        on = self._cabin.on
        if on is None:
            return None
        if not on:
            return HVACMode.OFF
        return HVACMode.FAN_ONLY if self._cabin.compressor is False else HVACMode.HEAT_COOL

    @property
    def preset_mode(self) -> str | None:
        if self._cabin.on is True and self._cabin.compressor is not False:
            return next((preset for preset, target in self._presets.items() if self._cabin.target == target), None)
        return None

    @property
    def fan_mode(self) -> str | None:
        # Console-only speeds remain in reported_fan_strength and the sensor.
        mode = self._cabin.fan_mode
        return mode if mode in self._attr_fan_modes else None

    @property
    def swing_mode(self) -> str | None:
        name = AIRFLOW_NAMES.get(self._cabin.blowing_mode)
        return name if name in self._airflow else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self.status
        blowing_mode = getattr(status, "ac_blowing_mode", None)
        return {"run_minutes": self._cabin.run_minutes,
                "reported_fan_strength": getattr(status, "ac_fan_strength", None),
                "reported_auto_mode": getattr(status, "ac_auto_on", None),
                "reported_compressor": getattr(status, "ac_compressor_on", None),
                "reported_blowing_mode": blowing_mode,
                "reported_airflow": AIRFLOW_NAMES.get(blowing_mode) if type(blowing_mode) is int else None,
                "reported_cycling_mode": getattr(status, "ac_cycling_mode", None)}

    def _handle_coordinator_update(self) -> None:
        self._cabin.sync()
        super()._handle_coordinator_update()

    @staticmethod
    def _power_for_mode(mode: HVACMode) -> bool:
        if mode not in (HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.FAN_ONLY):
            raise ServiceValidationError(f"Unsupported mode {mode}; choose Off, Heat/Cool or Fan only")
        return mode != HVACMode.OFF

    def _compressor_for_mode(self, mode: HVACMode | None) -> bool | None:
        """The compressor choice a mode asks for, or None when it would not change it."""
        if mode == HVACMode.FAN_ONLY:
            return False
        if mode == HVACMode.HEAT_COOL and self._cabin.compressor is False:
            return True
        return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if not self._power_for_mode(hvac_mode):
            await self._cabin.async_set_power(False)
        else:
            await self._cabin.async_set_fan_only(hvac_mode == HVACMode.FAN_ONLY)

    async def async_turn_on(self) -> None:
        await self._cabin.async_set_power(True)

    async def async_turn_off(self) -> None:
        await self._cabin.async_set_power(False)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode not in self._attr_fan_modes:
            speeds = self._cabin.fan_speeds
            raise ServiceValidationError(
                f"Unsupported remote fan mode; choose Off or a speed from {speeds[0]} to {speeds[-1]}" if speeds
                else "The car's capability list offers no remote fan speeds"
            )
        if fan_mode == "off":
            await self._cabin.async_set_power(False)
        else:
            await self._cabin.async_set_fan_speed(int(fan_mode))

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        if not isinstance(swing_mode, str) or swing_mode not in self._airflow:
            raise ServiceValidationError(
                f"Unsupported airflow; choose {', '.join(self._airflow)}" if self._airflow
                else "The car's capability list offers no remote airflow choice"
            )
        await self._cabin.async_set_blowing_mode(self._airflow[swing_mode])

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self._presets:
            raise ServiceValidationError(f"Unsupported preset {preset_mode}; choose heating or cooling")
        await self._cabin.async_set_temperature(self._presets[preset_mode], on=True, automatic=True)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        mode = kwargs.get(ATTR_HVAC_MODE)
        on = self._power_for_mode(mode) if mode is not None else None
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            if on is not None:
                await self._cabin.async_set_power(on)
            return
        try:
            value = float(temp)
        except (TypeError, ValueError, OverflowError):
            raise ServiceValidationError(f"temperature must be a number, got {temp!r}") from None
        low, high = self._attr_min_temp, self._attr_max_temp
        if isinstance(temp, bool) or not math.isfinite(value) or not low <= value <= high:
            raise ServiceValidationError(f"temperature must be between {low:g} and {high:g} °C")
        await self._cabin.async_set_temperature(value, on=on, compressor=self._compressor_for_mode(mode))
