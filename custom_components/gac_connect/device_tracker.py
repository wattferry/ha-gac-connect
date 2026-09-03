"""Device tracker: the vehicle's GPS location. Off by default for privacy."""
from __future__ import annotations

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .const import CONF_ENABLE_TRACKER, DEFAULT_ENABLE_TRACKER
from .coordinator import GacCoordinator
from .entity import GacEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    if not entry.options.get(CONF_ENABLE_TRACKER, DEFAULT_ENABLE_TRACKER):
        return
    add_entities([GacDeviceTracker(entry.runtime_data.coordinator)])


class GacDeviceTracker(GacEntity, TrackerEntity):
    _attr_translation_key = "location"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "location")

    @property
    def latitude(self) -> float | None:
        return self.status.latitude if self.status else None

    @property
    def longitude(self) -> float | None:
        return self.status.longitude if self.status else None
