"""Shared helpers: build a client without blocking the event loop.

The library loads its key material from a bundled file when a client is first
constructed. That is synchronous file I/O, so it must run in the executor rather
than on the event loop.
"""
from __future__ import annotations

import aiohttp
from gac_connect.client import GacClient
from gac_connect.keys import Material, load_material
from gac_connect.session import TokenStore

from homeassistant.core import HomeAssistant


async def async_build_client(
    hass: HomeAssistant,
    region: str,
    http: aiohttp.ClientSession,
    store: TokenStore | None = None,
) -> GacClient:
    material: Material = await hass.async_add_executor_job(load_material)
    return GacClient(region, http, store, material=material)
