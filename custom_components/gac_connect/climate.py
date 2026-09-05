"""Climate: remote cabin pre-conditioning (A/C, auto mode) with a target temperature.

The car reports whether the A/C is running and its setpoint, so the entity shows
real state; right after a command it shows the requested state until the next
poll confirms it. A run lasts the "A/C run time" option (default 30 minutes).
"""
from __future__ import annotations

from time import monotonic
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .const import CONF_AC_MINUTES, DEFAULT_AC_MINUTES
from .coordinator import GacCoordinator
from .entity import GacEntity

DEFAULT_TARGET_C = 24.0
MIN_TEMP_C, MAX_TEMP_C = 16.0, 30.0
PENDING_SECONDS = 180   # how long a requested state may override the car's report


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    add_entities([GacClimate(entry.runtime_data.coordinator)])


class GacClimate(GacEntity, ClimateEntity):
    _attr_translation_key = "climate"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_min_temp = MIN_TEMP_C
    _attr_max_temp = MAX_TEMP_C
    _attr_target_temperature_step = 0.5
    _attr_precision = PRECISION_HALVES
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "climate")
        self._target: float | None = None    # setpoint asked for from HA
        self._pending: bool | None = None    # requested on/off until the car confirms
        self._pending_until: float = 0.0     # ...or until this deadline passes

    @property
    def _run_minutes(self) -> int:
        return int(self.coordinator.config_entry.options.get(CONF_AC_MINUTES, DEFAULT_AC_MINUTES))

    @property
    def current_temperature(self) -> float | None:
        return self.status.cabin_temp_c if self.status else None

    @property
    def target_temperature(self) -> float | None:
        if self._target is not None:
            return self._target
        reported = self.status.ac_target_temp_c if self.status else None
        return reported if reported else DEFAULT_TARGET_C

    @property
    def hvac_mode(self) -> HVACMode | None:
        on = self._pending
        if on is None:
            on = self.status.ac_on if self.status else None
        if on is None:
            return None
        return HVACMode.HEAT_COOL if on else HVACMode.OFF

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"run_minutes": self._run_minutes}

    def _handle_coordinator_update(self) -> None:
        # The car's report becomes authoritative once it matches what we asked
        # for, or once the request has had a fair chance to be reflected.
        expired = monotonic() > self._pending_until
        if self._pending is not None:
            if (self.status is not None and self.status.ac_on == self._pending) or expired:
                self._pending = None
        if self._target is not None and self._pending is None:
            reported = self.status.ac_target_temp_c if self.status else None
            if reported == self._target or expired:
                self._target = None
        super()._handle_coordinator_update()

    def _mark_pending(self, on: bool) -> None:
        self._pending = on
        self._pending_until = monotonic() + PENDING_SECONDS
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_turn_on(self) -> None:
        await self._send(self.coordinator.client.climate_on(
            self.coordinator.vin, temperature=self.target_temperature or DEFAULT_TARGET_C,
            minutes=self._run_minutes,
        ))
        self._mark_pending(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self._send(self.coordinator.client.climate_off(self.coordinator.vin))
        self._mark_pending(False)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        try:
            value = float(temp)
        except (TypeError, ValueError):
            raise ServiceValidationError(f"temperature must be a number, got {temp!r}") from None
        if value != value or not MIN_TEMP_C <= value <= MAX_TEMP_C:
            raise ServiceValidationError(
                f"temperature must be between {MIN_TEMP_C:g} and {MAX_TEMP_C:g} °C, got {temp}"
            )
        self._target = round(value * 2) / 2
        self._pending_until = monotonic() + PENDING_SECONDS
        if self.hvac_mode == HVACMode.HEAT_COOL:
            await self.async_turn_on()   # re-send so the car adopts the new setpoint
        else:
            self.async_write_ha_state()
