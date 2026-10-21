"""Selects: front-seat ventilation level, and fridge mode (off, refrigerate, heat or freeze)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry, fridge
from .capabilities import remote_choices
from .coordinator import GacCoordinator
from .entity import GacEntity
from .entity_filter import add_configured_entities
from .requested import GacRequestedEntity
from .seats import reported_seat

# Ventilation strengths 1–3, verified on an Aion UT's front seats; a seat offers the
# levels its capability list includes, and these until the list is read.
SEAT_LEVEL_NAMES = {1: "low", 2: "medium", 3: "high"}
DEFAULT_SEAT_LEVELS = (1, 2, 3)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    add_configured_entities(entry, add_entities, "select",
                            [GacSeatVentilationSelect(coordinator, seat) for seat in (1, 2)])
    fridge.async_add_when_fitted(entry, coordinator, add_entities, lambda: [GacFridgeModeSelect(coordinator)], platform="select")


class GacSeatVentilationSelect(GacRequestedEntity, SelectEntity):
    """Front-seat ventilation strength. Both seats share a result event, so only a session id settles one.

    The console's Smart mode is not reported (an idle Smart seat reports as off and
    a running one as a level), and choosing a level here replaces it.
    """

    _attr_icon = "mdi:car-seat-cooler"

    def __init__(self, coordinator: GacCoordinator, seat: int) -> None:
        super().__init__(coordinator, f"seat_{seat}_ventilation")
        self._seat = seat
        self._attr_translation_key = f"seat_{seat}_ventilation"
        levels = remote_choices(coordinator, f"seat_{seat}_ventilation_levels", DEFAULT_SEAT_LEVELS)
        self._levels = {"off": 0, **{SEAT_LEVEL_NAMES[level]: level for level in levels if level in SEAT_LEVEL_NAMES}}
        self._attr_options = list(self._levels)

    def _reported(self) -> str | None:
        seat = reported_seat(self.status, self._seat)
        if seat is None or seat.ventilation_on is None:
            return None
        if not seat.ventilation_on:
            return "off"
        strength = seat.ventilation_strength
        name = SEAT_LEVEL_NAMES.get(int(strength)) if strength is not None and strength == int(strength) else None
        return name if name in self._levels else None

    @property
    def current_option(self) -> str | None:
        return self._value

    async def async_select_option(self, option: str) -> None:
        if option not in self._levels:
            raise ServiceValidationError(f"Unknown seat ventilation level {option!r}")
        level = self._levels[option]
        client, vin = self.coordinator.client, self.coordinator.vin
        await self._run(option, lambda: client.set_seat_ventilation_level(vin, self._seat, level),
                        command=f"seat-{self._seat}-ventilation-{'on' if level else 'off'}",
                        expected={f"seat_{self._seat}_ventilation_level": level})


class GacFridgeModeSelect(GacEntity, SelectEntity):
    _attr_translation_key = "fridge_mode"
    _attr_icon = "mdi:fridge-variant-outline"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "fridge_mode")
        self._attr_options = list(fridge.options(coordinator))

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
