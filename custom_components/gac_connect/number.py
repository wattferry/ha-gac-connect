"""Numbers: the remote A/C run time, and the fridge target temperature.

The run time is how long a remote A/C start runs before the car ends it; it is a
setting kept in Home Assistant, not sent until the next start.

The fridge temperature's range follows the running mode, or the next one to start.
While the fridge runs, a new temperature is sent straight away. While it is off,
the value is remembered for the next time that mode starts, and nothing is sent.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry, cabin, fridge
from .coordinator import GacCoordinator
from .entity import GacEntity
from .entity_filter import add_configured_entities
from .const import CONF_SCAN_INTERVAL, MIN_SCAN_INTERVAL
from .option_entity import GacOptionEntity
from .settings import MAX_SCAN_INTERVAL, scan_interval


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    add_configured_entities(entry, add_entities, "number", [GacRunTime(coordinator)])
    add_entities([GacPollingInterval(coordinator)])
    fridge.async_add_when_fitted(entry, coordinator, add_entities, lambda: [GacFridgeTemperature(coordinator)], platform="number")


class GacRunTime(GacEntity, RestoreNumber):
    """How long a remote A/C start (A/C, Climate) runs before the car ends it.

    The car applies it only to a remote start; once it is switched on, its own climate
    control takes over. Kept in Home Assistant across restarts.
    """

    _attr_translation_key = "ac_minutes"
    _attr_icon = "mdi:timer-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_step = 1.0

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "ac_minutes")
        self._cabin = cabin.controller(coordinator)
        low, high = self._cabin.minutes_range or cabin.DEFAULT_MINUTES_RANGE
        self._attr_native_min_value, self._attr_native_max_value = float(low), float(high)

    @property
    def available(self) -> bool:
        return True     # a setting, not a reading: it can change while the car is unreachable

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            try:
                self._cabin.set_run_minutes(int(last.native_value))
            except (ServiceValidationError, ValueError, OverflowError):
                pass    # outside the car's range now: the current value stands
        self.async_on_remove(self._cabin.add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> float:
        return float(self._cabin.run_minutes)

    async def async_set_native_value(self, value: float) -> None:
        if value != int(value):
            raise ServiceValidationError("The run time must be a whole number of minutes")
        self._cabin.set_run_minutes(int(value))


class GacFridgeTemperature(GacEntity, NumberEntity):
    _attr_translation_key = "fridge_temperature"
    _attr_icon = "mdi:thermometer"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "fridge_temperature")
        # the widest span across the car's modes, shown only while the fridge's state is unknown
        modes = fridge.running_modes(coordinator) or fridge.RUNNING_MODES
        spans = [fridge.temperature_range(coordinator, mode) for mode in modes]
        self._all = (min(lo for lo, _ in spans), max(hi for _, hi in spans))

    @property
    def _fridge(self) -> fridge.FridgeController:
        return fridge.controller(self.coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._fridge.add_listener(self.async_write_ha_state))

    @property
    def native_min_value(self) -> float:
        mode = self._fridge.temp_mode
        return fridge.temperature_range(self.coordinator, mode)[0] if mode else self._all[0]

    @property
    def native_max_value(self) -> float:
        mode = self._fridge.temp_mode
        return fridge.temperature_range(self.coordinator, mode)[1] if mode else self._all[1]

    @property
    def native_value(self) -> float | None:
        return self._fridge.temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"applies_to": self._fridge.temp_mode}

    def _handle_coordinator_update(self) -> None:
        self._fridge.sync()
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        await self._fridge.async_set_temperature(value)


class GacPollingInterval(GacOptionEntity, NumberEntity):
    """How often the car's report is read; applies at once, without a reload."""

    _attr_translation_key = "polling_interval"
    _attr_icon = "mdi:timer-sync-outline"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = float(MIN_SCAN_INTERVAL)
    _attr_native_max_value = float(MAX_SCAN_INTERVAL)
    _attr_native_step = 30.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "polling_interval")

    @property
    def native_value(self) -> float:
        return scan_interval(self.options).total_seconds()

    async def async_set_native_value(self, value: float) -> None:
        if value != int(value):
            raise ServiceValidationError("The polling interval must be a whole number of seconds")
        self.set_options(**{CONF_SCAN_INTERVAL: int(value)})
