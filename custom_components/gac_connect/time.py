"""Times: quiet hours, and the start and stop of the charge window being prepared."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .const import CONF_QUIET_END, CONF_QUIET_START
from .coordinator import GacCoordinator
from .option_entity import GacDraftEntity, GacOptionEntity
from .settings import DEFAULT_QUIET, quiet_hours


async def async_setup_entry(hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    add_entities([GacQuietTime(coordinator, CONF_QUIET_START), GacQuietTime(coordinator, CONF_QUIET_END),
                  GacDraftTime(coordinator, "start"), GacDraftTime(coordinator, "stop")])


def _clock(value: str | None) -> time | None:
    if not value:
        return None
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


class GacQuietTime(GacOptionEntity, TimeEntity):
    """Quiet hours start or end; setting one while quiet hours are off turns them on."""

    _attr_icon = "mdi:sleep"

    def __init__(self, coordinator: GacCoordinator, option: str) -> None:
        key = "quiet_hours_start" if option == CONF_QUIET_START else "quiet_hours_end"
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._option = option

    @property
    def native_value(self) -> time | None:
        current = quiet_hours(self.options)
        return _clock(current[0 if self._option == CONF_QUIET_START else 1]) if current else None

    async def async_set_value(self, value: time) -> None:
        start, end = quiet_hours(self.options) or DEFAULT_QUIET
        clock = f"{value.hour:02d}:{value.minute:02d}"
        start, end = (clock, end) if self._option == CONF_QUIET_START else (start, clock)
        self.set_options(**{CONF_QUIET_START: start, CONF_QUIET_END: end})


class GacDraftTime(GacDraftEntity, TimeEntity):
    """Start or stop of the charge window being prepared (car-local time)."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: GacCoordinator, part: str) -> None:
        super().__init__(coordinator, f"charge_window_{part}")
        self._attr_translation_key = f"charge_window_{part}"
        self._part = part

    @property
    def native_value(self) -> time | None:
        return _clock(getattr(self.draft, self._part))

    async def async_set_value(self, value: time) -> None:
        self.draft.set(**{self._part: f"{value.hour:02d}:{value.minute:02d}"})
