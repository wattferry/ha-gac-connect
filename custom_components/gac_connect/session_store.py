"""Durable per-entry credentials, separate from HA's delayed config-entry writes."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from gac_connect.errors import GacError
from gac_connect.session import Session, credential_pair
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util.file import WriteError, write_utf8_file_atomic

from .const import CONF_SESSION, DOMAIN


def session_path(hass: HomeAssistant, entry_id: str) -> Path:
    return Path(hass.config.path(".storage", f"{DOMAIN}.session.{entry_id}"))


class ConfigEntryStore:
    """Migrate legacy entry credentials only after an awaited atomic disk write.

    Saves to one entry's credentials take turns (one lock per file, shared by every store
    object for it), and ``replace`` compares and saves within one turn, so a refresh still
    in flight can never write over a sign-in saved meanwhile.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass, self._entry = hass, entry
        self._path = session_path(hass, entry.entry_id)
        locks = hass.data.setdefault(f"{DOMAIN}_session_locks", {})
        self._lock: asyncio.Lock = locks.setdefault(str(self._path), asyncio.Lock())

    def _read(self) -> dict | None:
        try:
            saved = json.loads(self._path.read_text())
        except FileNotFoundError:
            return None
        if not isinstance(saved, dict) or saved.get("version") != 1 or not isinstance(saved.get("data"), dict):
            raise ValueError("unsupported session file")
        return saved["data"]

    async def load(self) -> Session:
        try:
            saved = await self._hass.async_add_executor_job(self._read)
        except (OSError, ValueError) as err:
            raise GacError("Could not read saved GAC credentials") from err
        if saved is not None:
            self._remove_legacy()
            return Session.from_dict(saved)
        legacy = self._entry.data.get(CONF_SESSION)
        session = Session.from_dict(legacy)
        if legacy is not None:
            await self.save(session)
        return session

    def _write(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_utf8_file_atomic(str(self._path), json.dumps({"version": 1, "data": data}), private=True)

    async def save(self, session: Session) -> None:
        async with self._lock:
            await self._finish(self._hass.async_add_executor_job(self._write, session.to_dict()))
        self._remove_legacy()

    async def replace(self, expected: tuple[str | None, str | None], session: Session) -> Session | None:
        """Save ``session`` only if the saved credentials are still ``expected``; else return them."""
        async with self._lock:
            current = await self._finish(self._hass.async_add_executor_job(self._replace, expected,
                                                                             session.to_dict()))
        if current is None:
            self._remove_legacy()
            return None
        return Session.from_dict(current)

    def _replace(self, expected: tuple[str | None, str | None], data: dict) -> dict | None:
        try:
            current = self._read()
        except (OSError, ValueError):
            current = None          # unreadable: the session being saved is the usable one
        if current is None:
            current = self._entry.data.get(CONF_SESSION)     # not migrated from the entry yet
        if current is not None and credential_pair(Session.from_dict(current)) != expected:
            return current
        self._write(data)
        return None

    @staticmethod
    async def _finish(pending):
        """Await a disk operation to its end, even when the caller is cancelled meanwhile."""
        try:
            try:
                return await asyncio.shield(pending)
            except asyncio.CancelledError:
                await pending
                raise
        except (OSError, WriteError) as err:
            raise GacError("Could not persist GAC credentials") from err

    def _remove_legacy(self) -> None:
        if CONF_SESSION in self._entry.data:
            self._hass.config_entries.async_update_entry(
                self._entry, data={k: v for k, v in self._entry.data.items() if k != CONF_SESSION}
            )

    async def remove(self) -> None:
        await self._hass.async_add_executor_job(lambda: self._path.unlink(missing_ok=True))
