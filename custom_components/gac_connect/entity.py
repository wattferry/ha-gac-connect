"""Base entity: one device per VIN, coordinator-driven."""
from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

from gac_connect import GacError

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, DOMAIN
from .coordinator import GacCoordinator


class GacEntity(CoordinatorEntity[GacCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: GacCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.vin}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.vin)},
            manufacturer="GAC Aion",
            name=coordinator.config_entry.data.get(CONF_MODEL) or "Aion",
            model=coordinator.config_entry.data.get(CONF_MODEL),
            serial_number=coordinator.vin,
        )

    @property
    def status(self):
        return self.coordinator.data

    async def _send(self, coro: Awaitable[Any]) -> Any:
        """Run a vehicle command, surfacing library errors as HA errors."""
        try:
            return await coro
        except GacError as err:
            raise HomeAssistantError(str(err)) from err
