"""Door lock, with opt-in unlocking that does not require a PIN."""
from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from . import GacConfigEntry
from .const import CONF_EXPERIMENTAL_PINLESS_UNLOCK, CONF_MODEL
from .coordinator import GacCoordinator
from .entity_filter import add_configured_entities
from .lock_state import car_locked, doors_locked
from .transition import GacTransitionEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    add_configured_entities(entry, add_entities, "lock", [GacLock(entry.runtime_data.coordinator)])


class GacLock(GacTransitionEntity, LockEntity):
    _attr_translation_key = "doors"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "doors")

    @property
    def is_locked(self) -> bool | None:
        # The car is locked only with all four doors locked and the boot shut.
        return car_locked(self.status, self.coordinator.config_entry.data.get(CONF_MODEL))

    @property
    def is_open(self) -> bool | None:
        """Open while the boot is open, whatever the doors: the car is not secure."""
        return None if self.status is None else self.status.hatch_open

    def _reported_state(self) -> bool | None:
        # A lock or unlock command acts on the doors, so the doors alone confirm it.
        return doors_locked(self.status, self.coordinator.config_entry.data.get(CONF_MODEL))

    @property
    def is_locking(self) -> bool:
        return self._requested_state is True

    @property
    def is_unlocking(self) -> bool:
        return self._requested_state is False

    async def async_lock(self, **kwargs: Any) -> None:
        await self._run_transition(True, "lock", lambda: self.coordinator.client.lock(self.coordinator.vin))

    async def async_unlock(self, **kwargs: Any) -> None:
        if self.coordinator.config_entry.options.get(CONF_EXPERIMENTAL_PINLESS_UNLOCK) is not True:
            raise HomeAssistantError(
                "Remote unlocking is disabled. Turn on 'Allow remote unlocking' in GAC Connect options to use it."
            )
        await self._run_transition(False, "unlock", lambda: self.coordinator.client.unlock(self.coordinator.vin))
