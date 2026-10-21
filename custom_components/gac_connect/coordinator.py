"""Polling coordinator and the config-entry token store."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import socket
from datetime import time, timedelta
from time import monotonic

import aiohttp

from gac_connect import GacError
from gac_connect.client import GacClient
from gac_connect.const import REQUEST_BUDGETS
from gac_connect.errors import AuthExpiredError, RateLimitedError, ResponseError
from gac_connect.models import VehicleStatus
from gac_connect.push import PushResult

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALLOW_PLAINTEXT_PUSH,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_SCAN_INTERVAL,
    CONF_VIN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    EVENT_COMMAND_RESULT,
    SIGNAL_COMMAND_RESULT,
)
from .api import PushClient
from .capabilities import CapabilityManager
from .command_tracking import ChargingRequests, CommandTracker

_LOGGER = logging.getLogger(__name__)

# Acknowledgement often precedes fresh telemetry. Read again after the backend
# has had time to update, sharing one bounded sequence across all controls.
COMMAND_REFRESH_DELAYS = (5.0, 15.0, 30.0)
RESULT_REFRESH_GAP = 10.0
RECOVERY_DELAYS = (60.0, 120.0, 300.0)
QUIET_RECOVERY_ATTEMPTS = 2
# A network blip (DNS, timeout, lost connection) keeps the last real report for this long
# after the first failed read, logged at debug only; then the entities become unavailable.
NETWORK_GRACE_SECONDS = 300.0
TRANSIENT_FAILURES = frozenset({"dns", "timeout", "connection"})


def _failure_reason(error: Exception) -> str:
    """Classify the retained cause without exposing URLs, tokens or error text."""
    reason = "response" if isinstance(error, ResponseError) else "service"
    cause = error
    for _ in range(8):
        if isinstance(cause, (socket.gaierror, getattr(aiohttp, "ClientConnectorDNSError", socket.gaierror))):
            return "dns"
        if isinstance(cause, (aiohttp.ClientSSLError, aiohttp.ClientConnectorCertificateError)):
            return "tls"
        if isinstance(cause, TimeoutError):
            return "timeout"
        if isinstance(cause, aiohttp.ClientConnectionError):
            reason = "connection"
        cause = cause.__cause__ or cause.__context__
        if cause is None:
            break
    return reason


def _payload_shape(payload: bytes) -> str:
    """Field names (never values) of a push message, to help identify new message types."""
    try:
        obj = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return f"{len(payload)} bytes, not JSON"
    if not isinstance(obj, dict):
        return type(obj).__name__
    data = obj.get("data")
    data_keys = sorted(str(key) for key in data)[:40] if isinstance(data, dict) else type(data).__name__
    return f"keys={sorted(str(key) for key in obj)[:20]} data_keys={data_keys}"


def _parse_hhmm(value: str | None) -> time | None:
    if not value:
        return None
    try:
        h, m = (int(x) for x in value.split(":"))
        return time(hour=h, minute=m)
    except (ValueError, AttributeError):
        return None


# Every vehicle's requests come out of one shared budget. Polls may use at most this
# share of it, leaving the rest for commands, their follow-up reads and sign-ins.
POLL_BUDGET_SHARE = 0.8
# The shortest poll interval one vehicle can have while staying within every budget.
SECONDS_PER_VEHICLE_POLL = max(window / (limit * POLL_BUDGET_SHARE) for window, limit in REQUEST_BUDGETS)


class GacCoordinator(DataUpdateCoordinator[VehicleStatus]):
    """Polls one vehicle's status."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GacClient) -> None:
        try:   # the options form clamps this too; stored values are checked again here
            interval = max(MIN_SCAN_INTERVAL, int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)))
        except (TypeError, ValueError):
            interval = DEFAULT_SCAN_INTERVAL
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data[CONF_VIN][-4:]}",
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )
        self.client = client
        self.vin = entry.data[CONF_VIN]
        self._chosen_interval = interval
        self._stretch_logged: int | None = None
        self.capabilities = CapabilityManager(hass, entry)
        self.commands = CommandTracker(self)
        self.charging_requests = ChargingRequests()
        # Command results arrive on the service's push feed; each one triggers
        # an immediate status refresh so entities show what the car actually did.
        self.push = PushClient(client.mqtt_info, self._on_command_result, decrypt=client.decrypt_push,
                               allow_plaintext=entry.options.get(CONF_ALLOW_PLAINTEXT_PUSH, False) is True)
        self.last_result: PushResult | None = None
        self._force_refresh = False       # explicit refreshes may run inside quiet hours
        self._result_refresh_task: asyncio.Task | None = None
        self._refresh_deadlines: list[float] = []
        self._last_status_refresh = float("-inf")
        self._followup_blocked = False
        self._followup_closed = False
        self._fetch_lock = asyncio.Lock()   # one status request in flight, whatever triggered it
        self._fetch_generation = 0
        self._fetched_status = None
        self._rate_limit_until = float("-inf")
        self.retry_not_before = None
        self.last_refresh_success = None
        self.last_refresh_attempt = None
        self.last_refresh_error = None
        self.last_refresh_error_at = None
        self._refresh_failures = 0
        self._failing_since: float | None = None
        self._recovery_retry_at = None
        self._quiet_recovery_remaining = 0
        self._refresh_outcome = "waiting"
        self._freshness_timer = async_track_time_interval(hass, self._freshness_tick, timedelta(minutes=1))
        entry.async_on_unload(self._cancel_result_refresh)

    @callback
    def _freshness_tick(self, _now) -> None:
        """Age the displayed report without making a request to the car."""
        self.async_update_listeners()

    @property
    def report_age(self) -> float | None:
        if self.data is None or self.data.updated_ms is None:
            return None
        return (dt_util.utcnow().timestamp() - self.data.updated_ms / 1000)

    @property
    def stale_after(self) -> int:
        return max(600, int(self.update_interval.total_seconds()) * 2)

    @property
    def freshness(self) -> str:
        age = self.report_age
        if age is None:
            return "not_reported"
        if age < -60:
            return "clock_mismatch"
        return "stale" if age > self.stale_after else "recent"

    @property
    def polling_state(self) -> str:
        if self._refresh_outcome in ("error", "auth_required", "rate_limited"):
            return self._refresh_outcome
        return "quiet_hours" if self._in_quiet_hours() else self._refresh_outcome

    @callback
    def async_set_interval(self, interval: timedelta) -> None:
        """Poll at a newly chosen interval from the next read on, without a reload."""
        self._chosen_interval = int(interval.total_seconds())
        if self.update_interval is not None:
            self.update_interval = self._shared_interval()
            self._schedule_refresh()

    def _shared_interval(self) -> timedelta:
        """The chosen poll interval, stretched so all vehicles' polls fit the shared budget."""
        vehicles = sum(1 for entry in self.hass.config_entries.async_entries(DOMAIN) if entry.disabled_by is None)
        seconds = max(self._chosen_interval, math.ceil(SECONDS_PER_VEHICLE_POLL * max(1, vehicles)))
        if seconds != self._chosen_interval and seconds != self._stretch_logged:
            _LOGGER.info("polling every %d s instead of %d s so %d vehicles stay within the shared request budget",
                         seconds, self._chosen_interval, vehicles)
        self._stretch_logged = seconds
        return timedelta(seconds=seconds)

    @callback
    def _schedule_refresh(self) -> None:
        """Use HA's polling timer for recovery without changing the user's interval."""
        if self.update_interval is not None:   # None: polling is turned off
            self.update_interval = self._shared_interval()
        interval = self.update_interval
        if (self._refresh_outcome == "error" and self._recovery_retry_at is not None
                and (not self._in_quiet_hours() or self._quiet_recovery_remaining > 0)):
            self.update_interval = timedelta(seconds=max(1.0, self._recovery_retry_at - monotonic()))
        try:
            # Keeping scheduling in HA also honors disabled polling and unload,
            # and works on versions predating UpdateFailed.retry_after.
            super()._schedule_refresh()
        finally:
            self.update_interval = interval

    def start_push(self) -> None:
        self.config_entry.async_create_background_task(
            self.hass, self.push.run(), f"{DOMAIN} push {self.config_entry.entry_id}"
        )
        self.config_entry.async_on_unload(self.push.stop)

    async def _on_command_result(self, topic: str, payload: bytes, result: PushResult) -> None:
        if result.ok is None:
            _LOGGER.debug("ignoring unrecognised push message (code=%s event=%s, %s)",
                          result.code, result.event, _payload_shape(payload))
            return
        await self.async_handle_command_result(result)

    async def async_handle_command_result(self, result: PushResult) -> None:
        """Act on the car's answer to a command, from the push feed or a poll."""
        if result.ok is None:
            _LOGGER.debug("ignoring unrecognised command result (code=%s event=%s)", result.code, result.event)
            return
        if result.vin != self.vin:
            return   # another vehicle on the account, or no vehicle named: not ours to act on
        details = tuple(getattr(result, "details", ()) or ())
        _LOGGER.debug("command result: event=%s ok=%s code=%s reason=%s%s",
                      result.event, result.ok, result.code, result.reason,
                      f" car reported={'; '.join(details)}" if details else "")
        self.last_result = result
        self.commands.result(result)
        registry = dr.async_get(self.hass)
        if lookup := getattr(registry, "async_get_device_by_identifier", None):
            device = lookup((DOMAIN, self.vin), self.config_entry.entry_id)
        else:  # HA versions before device identifiers became entry-scoped
            device = registry.async_get_device(identifiers={(DOMAIN, self.vin)})
        self.hass.bus.async_fire(EVENT_COMMAND_RESULT, {
            "device_id": device.id if device else None,
            "ok": result.ok, "code": result.code, "reason": result.reason, "details": list(details),
            "event": result.event, "session_id": result.session_id,
        })
        async_dispatcher_send(self.hass, SIGNAL_COMMAND_RESULT.format(vin=self.vin), result)
        self._schedule_result_refresh()

    @callback
    def async_schedule_command_refresh(self) -> None:
        """Debounce accepted commands into at most three follow-up reads per burst."""
        if self._followup_closed or monotonic() < self._rate_limit_until:
            return
        now = monotonic()
        self._refresh_deadlines = [now + delay for delay in COMMAND_REFRESH_DELAYS]
        self._start_result_refresh()

    @callback
    def _schedule_result_refresh(self) -> None:
        """A push result shares pending reads, or requests one delayed read."""
        if self._followup_closed or monotonic() < self._rate_limit_until:
            return
        if not self._refresh_deadlines:
            self._refresh_deadlines = [monotonic() + COMMAND_REFRESH_DELAYS[0]]
        self._start_result_refresh()

    @callback
    def _start_result_refresh(self) -> None:
        if self._result_refresh_task and not self._result_refresh_task.done():
            return
        self._result_refresh_task = self.config_entry.async_create_background_task(
            self.hass, self._result_refresh(), f"{DOMAIN} result refresh {self.config_entry.entry_id}"
        )

    async def _result_refresh(self) -> None:
        while self._refresh_deadlines:
            wait = max(self._refresh_deadlines[0], self._last_status_refresh + RESULT_REFRESH_GAP) - monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
                continue  # commands or another status read may have moved the deadline
            self._refresh_deadlines.pop(0)
            self._force_refresh = True  # explicit commands also refresh during quiet hours
            await self.async_refresh()
            if self._followup_blocked:
                self._refresh_deadlines.clear()  # do not retry through a rate limit or expired login
            elif self.commands.records and not self.commands.pending:
                # One read after a result is useful; further reads cannot confirm
                # an already settled command. Unrelated pending actions still wait.
                self._refresh_deadlines.clear()

    @callback
    def async_rate_limited(self, error: RateLimitedError) -> None:
        """Share a command/status backoff without spending further request budget."""
        delay = error.retry_after
        if not isinstance(delay, (int, float)) or not math.isfinite(delay) or delay <= 0:
            delay = 60
        self._rate_limit_until = max(self._rate_limit_until, monotonic() + min(delay, 86400))
        self.retry_not_before = dt_util.utcnow() + timedelta(seconds=self._rate_limit_until - monotonic())
        self._refresh_outcome = "rate_limited"
        self._recovery_retry_at = None
        self._quiet_recovery_remaining = 0
        self._followup_blocked = True
        self._refresh_deadlines.clear()
        self.async_update_listeners()

    @callback
    def _cancel_result_refresh(self) -> None:
        self._followup_closed = True
        self.commands.close()
        if self._freshness_timer is not None:
            self._freshness_timer()
            self._freshness_timer = None
        self._refresh_deadlines.clear()
        if self._result_refresh_task is not None:
            self._result_refresh_task.cancel()

    async def async_shutdown(self) -> None:
        self._cancel_result_refresh()
        if self._result_refresh_task is not None:
            await asyncio.gather(self._result_refresh_task, return_exceptions=True)
        await super().async_shutdown()

    def _in_quiet_hours(self) -> bool:
        start = _parse_hhmm(self.config_entry.options.get(CONF_QUIET_START))
        end = _parse_hhmm(self.config_entry.options.get(CONF_QUIET_END))
        if not start or not end:
            return False
        now = dt_util.now().time()   # Home Assistant's time zone, not the host's
        if start <= end:
            return start <= now < end
        return now >= start or now < end  # window crosses midnight

    async def async_manual_refresh(self) -> None:
        """Honor an explicit refresh even when scheduled polling is suppressed."""
        self._force_refresh = True
        await self.async_request_refresh()

    async def async_refresh_now(self) -> None:
        """One read straight away, without the refresh debounce, for a page that shows its result.

        Skipped while the service has asked for a pause; a read in flight is shared.
        """
        if monotonic() < self._rate_limit_until:
            return
        self._force_refresh = True
        await self.async_refresh()

    def _network_grace(self) -> bool:
        """Whether a network blip may still be shown with the last real report."""
        return (self.last_refresh_error in TRANSIENT_FAILURES and self._fetched_status is not None
                and self.data is not None and self._failing_since is not None
                and monotonic() - self._failing_since < NETWORK_GRACE_SECONDS)

    async def _async_update_data(self) -> VehicleStatus:
        generation = self._fetch_generation
        async with self._fetch_lock:
            if generation != self._fetch_generation and self._refresh_outcome == "ok":
                # A caller that waited for this same in-flight read shares its
                # result, even before DataUpdateCoordinator publishes it.
                self._force_refresh = False
                return self._fetched_status
            forced = self._force_refresh
            self._force_refresh = False
            quiet = self._in_quiet_hours()
            recovery = (self._quiet_recovery_remaining > 0 and self._recovery_retry_at is not None
                        and monotonic() >= self._recovery_retry_at)
            # Explicit actions get a bounded recovery sequence during quiet
            # hours. Otherwise cached data must not undo a failed real fetch.
            if quiet and self.data is not None and not forced and not recovery:
                if self._refresh_outcome == "auth_required":
                    raise ConfigEntryAuthFailed("GAC sign-in required")
                if self._refresh_outcome == "error":
                    if self._network_grace():
                        return self.data
                    if self._quiet_recovery_remaining == 0:
                        self.retry_not_before = None
                    raise UpdateFailed("GAC refresh failed; waiting for an explicit refresh or quiet hours to end")
                return self.data
            if monotonic() < self._rate_limit_until:
                self._followup_blocked = True
                if self.data is not None:
                    return self.data
                raise UpdateFailed("Waiting for GAC's request limit before refreshing")
            if recovery and not forced:
                self._quiet_recovery_remaining -= 1
            self._followup_blocked = False
            self.last_refresh_attempt = dt_util.utcnow()
            try:
                status = await self.client.get_status(self.vin)
                self.last_refresh_success = dt_util.utcnow()
                self._refresh_outcome = "ok"
                self.retry_not_before = None
                self._refresh_failures = 0
                self._failing_since = None
                self._recovery_retry_at = None
                self._quiet_recovery_remaining = 0
                self._fetched_status = status
                if manager := getattr(self, "capabilities", None):
                    manager.observe(status)
                self.commands.observe(status)
                return status
            except AuthExpiredError as err:
                self._refresh_outcome = "auth_required"
                self._followup_blocked = True
                self._recovery_retry_at = None
                self._quiet_recovery_remaining = 0
                self.retry_not_before = None
                self.last_refresh_error = "auth"
                self.last_refresh_error_at = dt_util.utcnow()
                raise ConfigEntryAuthFailed(str(err)) from err
            except RateLimitedError as err:
                self.async_rate_limited(err)
                # Held back by the request limits (or the service asked us to slow
                # down): keep showing the last reading rather than going unavailable.
                if self.data is not None:
                    _LOGGER.debug("status refresh skipped: %s", err)
                    return self.data
                raise UpdateFailed(str(err)) from err
            except ResponseError as err:
                self._refresh_outcome = "error"
                self._followup_blocked = True
                self.last_refresh_error = _failure_reason(err)
                self.last_refresh_error_at = dt_util.utcnow()
                self._refresh_failures += 1
                delay = min(self.update_interval.total_seconds(),
                            RECOVERY_DELAYS[min(self._refresh_failures - 1, len(RECOVERY_DELAYS) - 1)])
                self._recovery_retry_at = monotonic() + delay
                if forced:
                    self._quiet_recovery_remaining = QUIET_RECOVERY_ATTEMPTS
                self.retry_not_before = (self.last_refresh_error_at + timedelta(seconds=delay)
                                         if not quiet or self._quiet_recovery_remaining > 0 else None)
                if self._failing_since is None:
                    self._failing_since = monotonic()
                if self._network_grace():
                    _LOGGER.debug("status refresh failed (%s); keeping the last report and retrying in %ds",
                                  self.last_refresh_error, delay)
                    return self.data
                raise UpdateFailed(f"{err} ({self.last_refresh_error})") from err
            except GacError as err:
                self._refresh_outcome = "error"
                self._recovery_retry_at = None
                self._quiet_recovery_remaining = 0
                self.retry_not_before = None
                self.last_refresh_error = _failure_reason(err)
                self.last_refresh_error_at = dt_util.utcnow()
                raise UpdateFailed(str(err)) from err
            except Exception:
                self._refresh_outcome = "error"
                self._recovery_retry_at = None
                self._quiet_recovery_remaining = 0
                self.retry_not_before = None
                self.last_refresh_error = "unexpected"
                self.last_refresh_error_at = dt_util.utcnow()
                raise
            finally:
                self._last_status_refresh = monotonic()
                self._fetch_generation += 1
