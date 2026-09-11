"""Fridge target temperature; its range follows the running mode, or the next one to start.

While the fridge runs, a new temperature is sent straight away. While it is off,
the value is remembered for the next time that mode starts, and nothing is sent.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from gac_connect.commands import FRIDGE_TEMP_RANGE

from . import GacConfigEntry, fridge
from .coordinator import GacCoordinator
from .entity import GacEntity

# the widest span across modes, shown only while the fridge's state is unknown
_ALL_LO = min(lo for lo, _ in FRIDGE_TEMP_RANGE.values())
_ALL_HI = max(hi for _, hi in FRIDGE_TEMP_RANGE.values())


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    fridge.async_add_when_fitted(entry, coordinator, add_entities, lambda: [GacFridgeTemperature(coordinator)])


class GacFridgeTemperature(GacEntity, NumberEntity):
    _attr_translation_key = "fridge_temperature"
    _attr_icon = "mdi:thermometer"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "fridge_temperature")

    @property
    def _fridge(self) -> fridge.FridgeController:
        return fridge.controller(self.coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._fridge.add_listener(self.async_write_ha_state))

    @property
    def native_min_value(self) -> float:
        mode = self._fridge.temp_mode
        return FRIDGE_TEMP_RANGE[mode][0] if mode else _ALL_LO

    @property
    def native_max_value(self) -> float:
        mode = self._fridge.temp_mode
        return FRIDGE_TEMP_RANGE[mode][1] if mode else _ALL_HI

    @property
    def native_value(self) -> float | None:
        return self._fridge.temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"applies_to": self._fridge.temp_mode}

    def _handle_coordinator_update(self) -> None:
        self._fridge.sync()
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        await self._fridge.async_set_temperature(value)
