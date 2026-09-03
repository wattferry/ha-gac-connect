"""Buttons: force refresh, charge now, charge pause."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from gac_connect.client import GacClient

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .coordinator import GacCoordinator
from .entity import GacEntity


@dataclass(frozen=True, kw_only=True)
class GacButton(ButtonEntityDescription):
    press: Callable[[GacClient, str], Awaitable[object]]


BUTTONS: tuple[GacButton, ...] = (
    GacButton(key="charge_now", translation_key="charge_now",
              press=lambda c, vin: c.charge_now(vin)),
    GacButton(key="charge_pause", translation_key="charge_pause",
              press=lambda c, vin: c.charge_pause(vin)),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[ButtonEntity] = [GacButtonEntity(coordinator, d) for d in BUTTONS]
    entities.append(GacRefreshButton(coordinator))
    add_entities(entities)


class GacButtonEntity(GacEntity, ButtonEntity):
    entity_description: GacButton

    def __init__(self, coordinator: GacCoordinator, description: GacButton) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.entity_description.press(self.coordinator.client, self.coordinator.vin)
        await self.coordinator.async_request_refresh()


class GacRefreshButton(GacEntity, ButtonEntity):
    _attr_translation_key = "refresh"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
