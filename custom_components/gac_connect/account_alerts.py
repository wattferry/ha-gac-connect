"""GAC's alert list, read every few minutes while the owner allows it.

The list lives on GAC's account service, which allows one sign-in per account: when the GAC
app signs in elsewhere, the session here ends ("signed_out") until Home Assistant signs in
again (Reconfigure). Alerts already listed when reading starts are remembered, not fired.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store

from gac_connect.alerts import Alert, parse_alerts
from gac_connect.errors import AccountSessionEnded, GacError, ResponseError
from .const import CONF_ALLOW_ACCOUNT_ALERTS, DOMAIN

_LOGGER = logging.getLogger(__name__)

READ_INTERVAL = timedelta(minutes=10)
FIRST_READ_SECONDS = 30
SEEN_LIMIT = 200
SIGNAL_ACCOUNT_ALERT = "gac_connect_account_alert_{vin}"
SIGNAL_ACCOUNT_ALERTS_UPDATED = "gac_connect_account_alerts_updated_{vin}"


def alert_attributes(alert: Alert) -> dict:
    return {
        "title": alert.title, "created": alert.created.isoformat() if alert.created else None,
        "code": f"{alert.source}/{alert.object}/{alert.reason}", "message": alert.message,
        "signals": [{"code": s.code, "description": s.description, "value": s.value} for s in alert.signals],
        "alert_id": alert.alert_id,
    }


def store_key(entry_id: str) -> str:
    return f"{DOMAIN}.{entry_id}.account_alerts"


class AccountAlerts:
    """States: off (not allowed), waiting, ok, signed_out, error."""

    def __init__(self, hass: HomeAssistant, entry, coordinator) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.enabled = entry.options.get(CONF_ALLOW_ACCOUNT_ALERTS) is True
        self.state = "waiting" if self.enabled else "off"
        self.latest: Alert | None = None
        self.last_read: datetime | None = None      # the last read that GAC answered (or ended the session on)
        self.last_error: str | None = None          # why the last read failed (the library's bounded wording)
        self._seen: list[str] | None = None        # None until the first read or the stored list
        self._store = Store(hass, 1, store_key(entry.entry_id))
        self._unsub: list[Callable[[], None]] = []
        self._task: asyncio.Task | None = None      # the read in progress, cancelled on unload
        self._saving: asyncio.Future | None = None  # the history write in progress, finished before removal
        self._closed = False

    async def async_setup(self) -> None:
        if not self.enabled:
            return
        stored = await self._store.async_load()
        if isinstance(stored, dict) and isinstance(stored.get("seen"), list):
            self._seen = [str(item) for item in stored["seen"]][-SEEN_LIMIT:]
        self._unsub.append(async_call_later(self.hass, FIRST_READ_SECONDS, self._scheduled))
        self._unsub.append(async_track_time_interval(self.hass, self._scheduled, READ_INTERVAL))
        # A coroutine: Home Assistant runs it and waits for it on every way an entry goes away
        # (unload, reload, and clean-up after a failed set-up), so a removal that follows
        # always deletes the final file.
        self.entry.async_on_unload(self._async_unloaded)

    async def _async_unloaded(self) -> None:
        self.async_close()
        await self.async_drain()

    async def async_drain(self) -> None:
        """Wait for a history write already under way, so an entry removal deletes the final file."""
        if self._saving is not None and not self._saving.done():
            await asyncio.wait({self._saving})

    @callback
    def async_close(self) -> None:
        """Stop reading: no timers, and a read in progress publishes and starts no save. A save
        already under way finishes (``async_drain``)."""
        self._closed = True
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()
        if self._task is not None and not self._task.done() and self._task is not asyncio.current_task():
            self._task.cancel()

    @callback
    def _scheduled(self, _now=None) -> None:
        if self._closed or (self._task is not None and not self._task.done()):
            return
        self._task = self.entry.async_create_background_task(
            self.hass, self.async_read(), f"{DOMAIN} alert read {self.entry.entry_id}")

    async def async_read(self) -> None:
        if not self.enabled or self.state == "signed_out" or self._closed:
            return
        vin = self.coordinator.vin
        try:
            page = await self.coordinator.client.get_alarms(vin)
            try:
                alerts = parse_alerts(page)   # a malformed page is a failed read, not an empty one
            except (TypeError, ValueError, AttributeError, KeyError) as err:
                raise ResponseError(f"the alert list could not be read ({type(err).__name__})") from err
        except AccountSessionEnded as err:
            self.last_read = datetime.now(UTC)
            self.last_error = str(err)[:200]
            _LOGGER.info("GAC alerts stop until Home Assistant signs in again (Reconfigure): %s", err)
            self.state = "signed_out"
            self.async_close()
            self._changed()
            return
        except GacError as err:
            if self.state != "error":
                _LOGGER.info("GAC's alert list could not be read: %s", err)
            self.last_error = str(err)[:200]
            self.state = "error"
            self._changed()
            return
        if self._closed:
            return          # unloaded while the read was out
        self.last_read = datetime.now(UTC)
        self.last_error = None
        _LOGGER.debug("GAC alert list read: %d alerts", len(alerts))
        if self._seen is None:
            self._seen = []          # first read: what is already listed is history, not news
        else:
            seen = set(self._seen)
            for alert in reversed(alerts):            # oldest first
                if alert.alert_id not in seen:
                    async_dispatcher_send(self.hass, SIGNAL_ACCOUNT_ALERT.format(vin=vin), alert)
        known = set(self._seen)
        self._seen.extend(alert.alert_id for alert in reversed(alerts) if alert.alert_id not in known)
        self._seen = self._seen[-SEEN_LIMIT:]
        if self._closed:
            return
        self._saving = asyncio.ensure_future(self._store.async_save({"seen": list(self._seen)}))
        await asyncio.shield(self._saving)
        if self._closed:
            return
        self.latest = alerts[0] if alerts else self.latest
        self.state = "ok"
        self._changed()

    @callback
    def _changed(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_ACCOUNT_ALERTS_UPDATED.format(vin=self.coordinator.vin))

    def diagnostics(self) -> dict:
        latest = self.latest
        refresh = getattr(self.coordinator.client, "last_account_refresh", None)
        return {"state": self.state, "remembered": len(self._seen or ()),
                "last_read": self.last_read.isoformat() if self.last_read else None,
                "last_error": self.last_error,
                "last_account_token_refresh": None if not refresh else {
                    "at": datetime.fromtimestamp(refresh[0], UTC).isoformat(), "accepted": refresh[1]},
                "latest": None if latest is None else {"key": latest.key, "created": latest.created.isoformat()
                                                       if latest.created else None}}
