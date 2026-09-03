"""Switch: scheduled charging (on = charge now / free, off = paused).

The car has no plain start/stop; this models the charge gate. Turning it on lets
the car charge whenever plugged in; off gates charging via the schedule. Resuming
takes the car a few minutes to act on, reflected in a short delay before status
catches up.
"""
from __future__ import annotations

from typing import Any

from gac_connect.models import ChargingMode

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .coordinator import GacCoordinator
from .entity import GacEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    add_entities([GacChargeSwitch(entry.runtime_data.coordinator)])


class GacChargeSwitch(GacEntity, SwitchEntity):
    _attr_translation_key = "charging"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "charge_switch")

    @property
    def is_on(self) -> bool | None:
        if self.status is None or self.status.charging_mode is None:
            return None
        # FREE = charge on plug-in ("on"); SCHEDULED gate = paused ("off").
        return self.status.charging_mode is ChargingMode.FREE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"note": "resuming charge can take a few minutes to take effect"}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.charge_now(self.coordinator.vin)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.charge_pause(self.coordinator.vin)
        await self.coordinator.async_request_refresh()
