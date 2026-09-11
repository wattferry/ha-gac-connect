"""Shared helpers: build a client without blocking the event loop.

The library loads its key material from a bundled file when a client is first
constructed. That is synchronous file I/O, so it must run in the executor rather
than on the event loop.

Every client (config entries and sign-in flows alike) passes the library's
process-wide request limiter. Its state is kept in Home Assistant's storage and
restored before the first client is built, so a restart does not reset the
budgets or cut short a pause the service asked for.
"""
from __future__ import annotations

import asyncio

import aiohttp
from gac_connect.client import GacClient
from gac_connect.keys import Material, load_material
from gac_connect.const import RECOVERY_PAUSE
from gac_connect.limits import DEFAULT_LIMITER
from gac_connect.session import TokenStore

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

LIMITS_KEY = f"{DOMAIN}.request_limits"
_LIMITS_READY = f"{DOMAIN}_limits_ready"


async def async_setup_limits(hass: HomeAssistant) -> None:
    """Restore the request limiter's state (once per run) before any client exists."""
    task: asyncio.Task | None = hass.data.get(_LIMITS_READY)
    if task is None or (task.done() and (task.cancelled() or task.exception() is not None)):
        task = hass.data[_LIMITS_READY] = hass.async_create_task(_restore_limits(hass))
    await asyncio.shield(task)   # a caller that gives up does not cancel the restore


async def _restore_limits(hass: HomeAssistant) -> None:
    # Home Assistant keeps the limiter's state in its own storage (below) rather than
    # the library's default state file, which would mean file I/O on the event loop.
    DEFAULT_LIMITER.state_path = None
    store: Store[dict] = Store(hass, 1, LIMITS_KEY)
    try:
        data = await store.async_load()
    except Exception:  # noqa: BLE001 — unreadable storage
        data = False
    if data is not None and not DEFAULT_LIMITER.import_state(data):
        # Saved limits exist but cannot be read, so any pause in them is unknown: pause
        # conservatively instead of starting afresh.
        DEFAULT_LIMITER.hold(RECOVERY_PAUSE, "the saved request limits could not be read")

    @callback
    def _changed(urgent: bool) -> None:
        if urgent:      # a pause the service asked for is written straight away
            hass.async_create_task(store.async_save(DEFAULT_LIMITER.export_state()))
        else:
            store.async_delay_save(DEFAULT_LIMITER.export_state, 10)

    DEFAULT_LIMITER.on_change = _changed


async def async_build_client(
    hass: HomeAssistant,
    region: str,
    http: aiohttp.ClientSession,
    store: TokenStore | None = None,
) -> GacClient:
    await async_setup_limits(hass)
    material: Material = await hass.async_add_executor_job(load_material)
    return GacClient(region, http, store, material=material)
