"""GAC Connect (unofficial) — Home Assistant integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gac_connect.client import GacClient


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_REGION, PLATFORMS
from .coordinator import ConfigEntryStore, GacCoordinator
from .helpers import async_build_client

type GacConfigEntry = ConfigEntry[GacRuntime]


@dataclass
class GacRuntime:
    client: GacClient
    coordinator: GacCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: GacConfigEntry) -> bool:
    # Isolated session: this login's cookies must not mix with other integrations.
    http = async_create_clientsession(hass)
    client = await async_build_client(hass, entry.data[CONF_REGION], http, ConfigEntryStore(hass, entry))
    await client.load()

    coordinator = GacCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = GacRuntime(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_on_update))

    _register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GacConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _reload_on_update(hass: HomeAssistant, entry: GacConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(hass: HomeAssistant) -> None:
    # Registered lazily on first entry; imported here to keep module load light.
    from .services import async_register_services

    async_register_services(hass)
