"""Clear recorder statistics only when GAC sensors are permanently removed."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.recorder import DATA_INSTANCE

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_DATA_KEY = f"{DOMAIN}.statistics_cleanup"


@callback
def _clear_statistics(hass: HomeAssistant, entity_ids: set[str]) -> None:
    """Queue the recorder's own cleanup; never open or modify its database here."""
    if not entity_ids:
        return
    if (recorder := hass.data.get(DATA_INSTANCE)) is None:
        _LOGGER.warning(
            "Recorder is unavailable; statistics for %s removed GAC sensors must "
            "be cleared manually from Home Assistant's Statistics page",
            len(entity_ids),
        )
        return
    recorder.async_clear_statistics(sorted(entity_ids))


class StatisticsCleanup:
    """Watch registry removal, independently of entity availability or unloading.

    One listener lasts for the integration's lifetime in this HA process. An
    entry unload cannot remove it: disabled entities can still be deleted, and
    HA unloads an entry before removing its registry entries.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.registry = er.async_get(hass)
        self._sensors = {
            entity.entity_id for entity in self.registry.entities.values()
            if entity.platform == DOMAIN and entity.domain == "sensor"
        }
        self._unsubscribe = hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._registry_updated)
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._stop)

    @callback
    def _registry_updated(self, event: Event) -> None:
        entity_id = event.data["entity_id"]
        if event.data["action"] == "remove":
            if entity_id in self._sensors:
                self._sensors.remove(entity_id)
                _clear_statistics(self.hass, {entity_id})
            return
        # A rename transfers statistics in the recorder. Follow its new ID;
        # disabling, hiding and other registry edits must not clear anything.
        if old_entity_id := event.data.get("old_entity_id"):
            self._sensors.discard(old_entity_id)
        entity = self.registry.async_get(entity_id)
        if entity is not None and entity.platform == DOMAIN and entity.domain == "sensor":
            self._sensors.add(entity_id)
        else:
            self._sensors.discard(entity_id)

    @callback
    def async_remove_entry(self, entry: ConfigEntry) -> None:
        """Collect exact registry IDs before HA clears an entry's registry rows."""
        entity_ids = {
            entity.entity_id for entity in er.async_entries_for_config_entry(self.registry, entry.entry_id)
            if entity.platform == DOMAIN and entity.domain == "sensor"
        }
        # Include earlier deletions still attributed to this entry. A reused ID
        # belongs to its current owner, so never clear that other entity's data.
        for deleted in self.registry.deleted_entities.values():
            if (deleted.config_entry_id != entry.entry_id or deleted.platform != DOMAIN
                    or not deleted.entity_id.startswith("sensor.")):
                continue
            current = self.registry.async_get(deleted.entity_id)
            if current is None:
                # Sensors without a unique ID may reuse the ID without creating
                # a registry entry. Treat any live state as another owner.
                if self.hass.states.get(deleted.entity_id) is None:
                    entity_ids.add(deleted.entity_id)
            elif current.config_entry_id == entry.entry_id and current.platform == DOMAIN:
                entity_ids.add(deleted.entity_id)
        # The registry's ensuing removal events must not queue duplicate clears.
        self._sensors.difference_update(entity_ids)
        _clear_statistics(self.hass, entity_ids)

    @callback
    def _stop(self, _event: Event) -> None:
        self._unsubscribe()
        self._sensors.clear()
        self.hass.data.pop(_DATA_KEY, None)


@callback
def async_setup_cleanup(hass: HomeAssistant) -> StatisticsCleanup:
    """Install one registry listener, including across entry reloads."""
    if _DATA_KEY not in hass.data:
        hass.data[_DATA_KEY] = StatisticsCleanup(hass)
    return hass.data[_DATA_KEY]
