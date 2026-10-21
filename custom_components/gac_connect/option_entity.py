"""Base for the entities that show and change an option or the charge window draft."""
from __future__ import annotations

from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .entity import GacEntity
from .settings import SIGNAL_OPTIONS, async_set_options


class GacOptionEntity(GacEntity):
    """A setting, not a reading: always available, in the device's Configuration section."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        return True

    @property
    def options(self) -> dict[str, Any]:
        return dict(self.coordinator.config_entry.options)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_OPTIONS.format(entry_id=self.coordinator.config_entry.entry_id),
            self.async_write_ha_state))

    def set_options(self, **updates: Any) -> None:
        async_set_options(self.hass, self.coordinator.config_entry, updates)
        self.async_write_ha_state()


class GacDraftEntity(GacEntity):
    """Part of the charge window being prepared; nothing is sent before Send charge window."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        return True

    @property
    def draft(self):
        return self.coordinator.config_entry.runtime_data.charge_draft

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.draft.add_listener(self.async_write_ha_state))
