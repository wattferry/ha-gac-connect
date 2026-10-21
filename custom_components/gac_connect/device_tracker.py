"""Device tracker: the vehicle's GPS location. Off by default for privacy.

The tracker has no picture of its own; dashboard cards supply the car's image.
"""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .coordinator import GacCoordinator
from .entity import GacEntity
from .entity_filter import add_configured_entities
from .location import location_enabled, shown_position


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    if not location_enabled(entry.options):
        return
    add_configured_entities(entry, add_entities, "device_tracker", [GacDeviceTracker(entry.runtime_data.coordinator)])


class GacDeviceTracker(GacEntity, TrackerEntity):
    _attr_translation_key = "location"
    _attr_icon = "mdi:car"     # the dashboard map shows this car in place of the name's initials
    _attr_source_type = SourceType.GPS
    # TrackerEntity defaults to Diagnostic; keep both location readings in Sensors.
    _attr_entity_category = None

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "location")

    @property
    def latitude(self) -> float | None:
        return shown_position(self.status, self.coordinator.config_entry.options)[0]

    @property
    def longitude(self) -> float | None:
        return shown_position(self.status, self.coordinator.config_entry.options)[1]
