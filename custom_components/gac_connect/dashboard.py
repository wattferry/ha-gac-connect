"""The dashboard cards: serve the bundle, load it on every dashboard, and keep one dashboard per car.

The cards are always available for the owner's own dashboards while the integration runs. Each
entry also chooses which cards its generated dashboard holds; none means no generated dashboard.
That dashboard is the integration's only while it is exactly as generated: an edited one is never
changed or removed, and one the owner deletes is an opt-out (the choice is cleared rather than
the dashboard recreated).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from inspect import unwrap
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify

from .const import CONF_DASHBOARD_CARDS, CONF_LOAD_CARDS, DASHBOARD_CARDS, DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = f"/{DOMAIN}/frontend"
BUNDLE = "gac-connect-cards.js"            # the loader every page loads; it loads CARDS once HA has booted
CARDS = "gac-connect-cards-main.js"
FRONTEND_DIR = Path(__file__).parent / "frontend"
_DATA = f"{DOMAIN}_cards"
CAR_CARDS = ("vehicle", "charging", "climate", "location", "activity")


class DashboardError(Exception):
    """Home Assistant's dashboards cannot be reached."""


class DashboardEdited(DashboardError):
    """The generated dashboard was edited, so it is left for the owner to change."""


def cards_loaded(options: dict[str, Any]) -> bool:
    """Whether the owner chose to load the cards; until then nothing is added to Home Assistant's pages."""
    return options.get(CONF_LOAD_CARDS) is True


def dashboard_cards(options: dict[str, Any]) -> tuple[str, ...]:
    """The chosen cards in dashboard order; none while the cards are not loaded, or from before the cards."""
    if not cards_loaded(options):
        return ()
    chosen = set(options.get(CONF_DASHBOARD_CARDS) or ())
    return tuple(card for card in DASHBOARD_CARDS if card in chosen)


def dashboard_config(device_id: str, title: str, cards: tuple[str, ...] = DASHBOARD_CARDS) -> dict[str, Any]:
    """What the generated dashboard holds; only this exact configuration is ever replaced or removed."""
    def card(kind: str) -> dict[str, str]:
        return {"type": f"custom:gac-{kind}-card", "device": device_id}

    views = []
    if car := [card(kind) for kind in CAR_CARDS if kind in cards]:
        views.append({"title": title, "path": "car", "cards": car})
    if "settings" in cards:
        views.append({"title": "Settings", "path": "settings", "cards": [card("settings")]})
    return {"title": title, "views": views}


def _available(hass: HomeAssistant) -> bool:
    return {"frontend", "http", "lovelace"} <= hass.config.components and getattr(hass, "http", None) is not None


# ---- the card bundle -------------------------------------------------------

class _Cards:
    def __init__(self) -> None:
        self.url: str | None = None
        self.wanted: set[str] = set()
        self.lock = asyncio.Lock()


def _cards(hass: HomeAssistant) -> _Cards:
    return hass.data.setdefault(_DATA, _Cards())


async def async_want_cards(hass: HomeAssistant, entry_id: str, want: bool) -> None:
    """Load the bundle on every page while any entry that loads the cards is set up; drop it when none is."""
    if not _available(hass) or not (FRONTEND_DIR / BUNDLE).exists() or not (FRONTEND_DIR / CARDS).exists():
        return
    from homeassistant.components import frontend

    cards = _cards(hass)
    async with cards.lock:
        if want:
            cards.wanted.add(entry_id)
        else:
            cards.wanted.discard(entry_id)
        if cards.wanted and cards.url is None:
            # One version for the loader and the cards, which the loader passes on to the cards' address.
            digest = await hass.async_add_executor_job(lambda: hashlib.sha256(
                (FRONTEND_DIR / BUNDLE).read_bytes() + (FRONTEND_DIR / CARDS).read_bytes()).hexdigest()[:12])
            if not hass.data.get(f"{_DATA}_route"):
                from homeassistant.components.http import StaticPathConfig

                await hass.http.async_register_static_paths(
                    [StaticPathConfig(URL_BASE, str(FRONTEND_DIR), cache_headers=True)])
                hass.data[f"{_DATA}_route"] = True
            cards.url = f"{URL_BASE}/{BUNDLE}?v={digest}"
            frontend.add_extra_js_url(hass, cards.url)
        elif not cards.wanted and cards.url is not None:
            frontend.remove_extra_js_url(hass, cards.url)
            cards.url = None


# ---- the generated dashboard -------------------------------------------------

def _dashboards(hass: HomeAssistant) -> dict[str, Any]:
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    data: Any = hass.data.get(LOVELACE_DATA)
    if data is None:
        return {}
    return data["dashboards"] if isinstance(data, dict) else data.dashboards


def _collection(hass: HomeAssistant) -> Any:
    """Core keeps the dashboards collection behind its list command, not in hass.data."""
    from homeassistant.components import websocket_api
    from homeassistant.components.lovelace.dashboard import DashboardsCollection

    entry = hass.data.get(websocket_api.DOMAIN, {}).get("lovelace/dashboards/list")
    handler = unwrap(entry[0]) if isinstance(entry, tuple) else None
    collection = getattr(getattr(handler, "__self__", None), "storage_collection", None)
    if not isinstance(collection, DashboardsCollection):
        data = hass.data.get("lovelace")
        collection = data.get("dashboards_collection") if isinstance(data, dict) else None
    if not isinstance(collection, DashboardsCollection):
        raise DashboardError("Home Assistant's dashboard list is unavailable")
    return collection


def store_key(entry_id: str) -> str:
    return f"{DOMAIN}.{entry_id}.dashboard"


async def _load(board: Any) -> Any:
    from homeassistant.components.lovelace.const import ConfigNotFound

    try:
        return await board.async_load(False)
    except ConfigNotFound:
        return None


class VehicleDashboard:
    """The one dashboard an entry generated, recorded by its ID, path, cards and configuration."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.store: Store[dict[str, Any]] = Store(hass, 1, store_key(entry_id))
        self.lock = asyncio.Lock()

    async def async_status(self) -> dict[str, Any] | None:
        """The generated dashboard's path and whether it was edited; None when there is none."""
        owned = await self.store.async_load() or {}
        board = _dashboards(self.hass).get(owned.get("url_path")) if owned else None
        if board is None or (board.config or {}).get("id") != owned.get("id"):
            return None
        return {"url_path": owned["url_path"], "cards": tuple(owned.get("cards", ())),
                "edited": await _load(board) != owned.get("config")}

    async def async_apply(self, cards: tuple[str, ...], device_id: str | None, title: str) -> bool:
        """Create, update or remove the dashboard to hold these cards. False: the owner deleted it."""
        async with self.lock:
            owned = await self.store.async_load() or {}
            if not owned:
                if cards and device_id:
                    await self._create(cards, device_id, title)
                return True
            board = _dashboards(self.hass).get(owned.get("url_path"))
            if board is None or (board.config or {}).get("id") != owned.get("id"):
                await self.store.async_remove()
                return not cards
            current = await _load(board)
            if current != owned.get("config"):
                if not cards or tuple(owned.get("cards", ())) != cards:
                    raise DashboardEdited(f"The {owned['url_path']} dashboard was edited; change it yourself")
                return True
            if not cards:
                await _collection(self.hass).async_delete_item(owned["id"])
                await self.store.async_remove()
                return True
            wanted = dashboard_config(device_id, title, cards) if device_id else current
            if wanted != current:
                await board.async_save(wanted)
                await self.store.async_save({**owned, "cards": list(cards), "config": wanted})
            return True

    async def _create(self, cards: tuple[str, ...], device_id: str, title: str) -> None:
        collection = _collection(self.hass)
        boards = _dashboards(self.hass)
        base = f"gac-{slugify(title, separator='-') or 'car'}"
        url_path = next(path for n in range(1, 100) if (path := base if n == 1 else f"{base}-{n}") not in boards)
        created = await collection.async_create_item({
            "url_path": url_path, "title": title, "icon": "mdi:car-electric",
            "require_admin": False, "show_in_sidebar": True,
        })
        config = dashboard_config(device_id, title, cards)
        try:
            await _dashboards(self.hass)[url_path].async_save(config)
            await self.store.async_save({"id": created["id"], "url_path": url_path, "cards": list(cards),
                                         "config": config})
        except Exception:
            await collection.async_delete_item(created["id"])
            await self.store.async_remove()
            raise


async def async_apply_dashboard(hass: HomeAssistant, entry, device_id: str | None) -> None:
    """Load the cards if the owner chose them, and bring the generated dashboard in line with the entry's choice."""
    try:
        await async_want_cards(hass, entry.entry_id, cards_loaded(entry.options))
    except Exception as err:   # never let a dashboard problem stop the car's entities
        _LOGGER.warning("GAC Connect could not load its dashboard cards: %s", err)
        return
    if not _available(hass):
        return
    try:
        kept = await VehicleDashboard(hass, entry.entry_id).async_apply(dashboard_cards(entry.options), device_id,
                                                                        entry.title)
    except Exception as err:
        _LOGGER.warning("GAC Connect could not update the %s dashboard: %s", entry.title, err)
        return
    if not kept:
        hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_DASHBOARD_CARDS: []})


async def async_remove_dashboard(hass: HomeAssistant, entry_id: str) -> None:
    """On entry removal: remove an unedited dashboard; an edited one stays the owner's."""
    dashboard = VehicleDashboard(hass, entry_id)
    try:
        if _available(hass):
            await dashboard.async_apply((), None, "")
    except DashboardEdited:
        pass
    except Exception as err:
        _LOGGER.warning("GAC Connect could not remove its dashboard: %s", err)
    finally:
        await dashboard.store.async_remove()
