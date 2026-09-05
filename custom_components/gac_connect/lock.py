"""Lock: remote door lock. Unlocking needs the car's remote-control PIN, which the
library does not support yet, so unlock reports a clear error instead."""
from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .coordinator import GacCoordinator
from .entity import GacEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    add_entities([GacLock(entry.runtime_data.coordinator)])


class GacLock(GacEntity, LockEntity):
    _attr_translation_key = "doors"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "doors")

    @property
    def is_locked(self) -> bool | None:
        return self.status.locked if self.status else None

    async def async_lock(self, **kwargs: Any) -> None:
        self._attr_is_locking = True
        self.async_write_ha_state()
        try:
            await self._send(self.coordinator.client.lock(self.coordinator.vin))
        finally:
            self._attr_is_locking = False
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_unlock(self, **kwargs: Any) -> None:
        # Raises a PIN-required error from the library until PIN support exists.
        await self._send(self.coordinator.client.command(self.coordinator.vin, "unlock"))
        await self.coordinator.async_request_refresh()
