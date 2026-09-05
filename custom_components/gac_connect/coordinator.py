"""Polling coordinator and the config-entry token store."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta

from gac_connect import GacError
from gac_connect.client import GacClient
from gac_connect.errors import AuthExpiredError, RateLimitedError
from gac_connect.models import VehicleStatus
from gac_connect.push import PushClient, PushResult
from gac_connect.session import Session

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_SCAN_INTERVAL,
    CONF_SESSION,
    CONF_VIN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_COMMAND_RESULT,
    SIGNAL_COMMAND_RESULT,
)

_LOGGER = logging.getLogger(__name__)


class ConfigEntryStore:
    """Persist the session in the config entry so tokens survive restarts."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry

    async def load(self) -> Session:
        return Session.from_dict(self._entry.data.get(CONF_SESSION))

    async def save(self, session: Session) -> None:
        self._hass.config_entries.async_update_entry(
            self._entry, data={**self._entry.data, CONF_SESSION: session.to_dict()}
        )


def _parse_hhmm(value: str | None) -> time | None:
    if not value:
        return None
    try:
        h, m = (int(x) for x in value.split(":"))
        return time(hour=h, minute=m)
    except (ValueError, AttributeError):
        return None


class GacCoordinator(DataUpdateCoordinator[VehicleStatus]):
    """Polls one vehicle's status."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GacClient) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data[CONF_VIN][-4:]}",
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )
        self.client = client
        self.vin = entry.data[CONF_VIN]
        # Command results arrive on the service's push feed; each one triggers
        # an immediate status refresh so entities show what the car actually did.
        # The service's broker is plain TCP with short-lived credentials; opted in knowingly.
        self.push = PushClient(client.mqtt_info, self._on_command_result, decrypt=client.decrypt_push,
                               allow_plaintext=True)
        self.last_result: PushResult | None = None
        self._force_refresh = False       # a command result may refresh inside quiet hours
        self._result_refresh_task: asyncio.Task | None = None
        self._result_refresh_again = False
        self._fetch_lock = asyncio.Lock()   # one status request in flight, whatever triggered it

    def start_push(self) -> None:
        self.config_entry.async_create_background_task(
            self.hass, self.push.run(), f"{DOMAIN} push {self.config_entry.entry_id}"
        )
        self.config_entry.async_on_unload(self.push.stop)

    async def _on_command_result(self, topic: str, payload: bytes, result: PushResult) -> None:
        if result.ok is None:
            _LOGGER.debug("ignoring unrecognised push message (%d bytes)", len(payload))
            return
        if result.vin != self.vin:
            return   # another vehicle on the account, or no vehicle named: not ours to act on
        _LOGGER.debug("command result: event=%s ok=%s code=%s", result.event, result.ok, result.code)
        self.last_result = result
        device = dr.async_get(self.hass).async_get_device(identifiers={(DOMAIN, self.vin)})
        self.hass.bus.async_fire(EVENT_COMMAND_RESULT, {
            "device_id": device.id if device else None,
            "ok": result.ok, "code": result.code,
            "event": result.event, "session_id": result.session_id,
        })
        async_dispatcher_send(self.hass, SIGNAL_COMMAND_RESULT.format(vin=self.vin), result)
        self._schedule_result_refresh()

    def _schedule_result_refresh(self) -> None:
        """One status refresh per burst of results, without blocking the feed."""
        self._force_refresh = True
        if self._result_refresh_task and not self._result_refresh_task.done():
            self._result_refresh_again = True
            return
        self._result_refresh_task = self.config_entry.async_create_background_task(
            self.hass, self._result_refresh(), f"{DOMAIN} result refresh {self.config_entry.entry_id}"
        )

    async def _result_refresh(self) -> None:
        while True:
            self._result_refresh_again = False
            await self.async_refresh()
            if not self._result_refresh_again:
                return
            await asyncio.sleep(2)   # results that landed mid-refresh share one more

    def _in_quiet_hours(self) -> bool:
        start = _parse_hhmm(self.config_entry.options.get(CONF_QUIET_START))
        end = _parse_hhmm(self.config_entry.options.get(CONF_QUIET_END))
        if not start or not end:
            return False
        now = datetime.now().time()
        if start <= end:
            return start <= now < end
        return now >= start or now < end  # window crosses midnight

    async def _async_update_data(self) -> VehicleStatus:
        async with self._fetch_lock:
            # During quiet hours, keep the last reading instead of waking the car —
            # unless a command result asked for one confirmation refresh.
            if self._in_quiet_hours() and self.data is not None and not self._force_refresh:
                return self.data
            self._force_refresh = False
            try:
                return await self.client.get_status(self.vin)
            except AuthExpiredError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except RateLimitedError as err:
                raise UpdateFailed(str(err)) from err  # retry_after handled by HA if set
            except GacError as err:
                raise UpdateFailed(str(err)) from err
