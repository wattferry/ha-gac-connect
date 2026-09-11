"""Device tracker: the vehicle's GPS location. Off by default for privacy.

The tracker carries the car's picture so the map shows the car, not the entity's
initials: the one set in the options, or else a bundled render for the model.
"""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .const import CONF_ENABLE_TRACKER, CONF_MODEL, CONF_PICTURE, DEFAULT_ENABLE_TRACKER, DOMAIN
from .coordinator import GacCoordinator
from .entity import GacEntity

PICTURES_URL = f"/{DOMAIN}/pictures"
_PICTURES_DIR = Path(__file__).parent / "pictures"
# model name as the service reports it (lower case) -> bundled picture
_BUNDLED: dict[str, str] = {"aion v": "aion-v.png"}
_REGISTERED = f"{DOMAIN}_pictures_registered"


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    if not entry.options.get(CONF_ENABLE_TRACKER, DEFAULT_ENABLE_TRACKER):
        return
    picture = await _async_picture(hass, entry)
    add_entities([GacDeviceTracker(entry.runtime_data.coordinator, picture)])


async def _async_picture(hass: HomeAssistant, entry: GacConfigEntry) -> str | None:
    """The picture set in the options, else a bundled one for the model, else none (initials)."""
    if custom := (entry.options.get(CONF_PICTURE) or "").strip():
        return custom
    name = _BUNDLED.get(str(entry.data.get(CONF_MODEL) or "").strip().lower())
    http = getattr(hass, "http", None)
    if name is None or http is None:
        return None
    if not hass.data.get(_REGISTERED):
        hass.data[_REGISTERED] = True
        await http.async_register_static_paths(
            [StaticPathConfig(PICTURES_URL, str(_PICTURES_DIR), cache_headers=False)])
    return f"{PICTURES_URL}/{name}"


class GacDeviceTracker(GacEntity, TrackerEntity):
    _attr_translation_key = "location"

    def __init__(self, coordinator: GacCoordinator, picture: str | None = None) -> None:
        super().__init__(coordinator, "location")
        self._attr_entity_picture = picture

    @property
    def latitude(self) -> float | None:
        return self.status.latitude if self.status else None

    @property
    def longitude(self) -> float | None:
        return self.status.longitude if self.status else None
