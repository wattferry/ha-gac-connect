"""Fridge mode: off, refrigerate, heat or freeze."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry, fridge
from .coordinator import GacCoordinator
from .entity import GacEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    fridge.async_add_when_fitted(entry, coordinator, add_entities, lambda: [GacFridgeModeSelect(coordinator)])


class GacFridgeModeSelect(GacEntity, SelectEntity):
    _attr_translation_key = "fridge_mode"
    _attr_icon = "mdi:fridge-variant-outline"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "fridge_mode")
        self._attr_options = list(fridge.OPTIONS)

    @property
    def _fridge(self) -> fridge.FridgeController:
        return fridge.controller(self.coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._fridge.add_listener(self.async_write_ha_state))

    @property
    def current_option(self) -> str | None:
        return self._fridge.option

    def _handle_coordinator_update(self) -> None:
        self._fridge.sync()
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        await self._fridge.async_set_option(option)
