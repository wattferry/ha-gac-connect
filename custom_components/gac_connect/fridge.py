"""Fridge / warmer box: one controller per car behind the switch, mode selector and temperature.

The car reports a working mode and, while running, a target temperature; each
running mode has its own range. The controller is the single place that sends
fridge commands. It serialises them, shows a requested state until the car's
report confirms it (or a timer expires, or the car refuses), and remembers the
last running mode and the last temperature per mode across restarts, so
switching on or picking a mode restores what was used before.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
import math
from time import monotonic
from typing import Any

from gac_connect import GacError, command_session_id
from gac_connect.commands import FRIDGE_DEFAULT_TEMP, FRIDGE_MODES, FRIDGE_TEMP_RANGE, validate_fridge
from gac_connect.push import PushResult

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SIGNAL_COMMAND_RESULT

_LOGGER = logging.getLogger(__name__)

RUNNING_MODES: tuple[str, ...] = tuple(FRIDGE_MODES)          # refrigerate, heat, freeze
OPTIONS: tuple[str, ...] = ("off", *RUNNING_MODES)
RESULT_EVENTS: tuple[str, ...] = ("control_refrigerator",)
REQUEST_SECONDS = 180      # a requested state overrides the car's report at most this long
STORE_VERSION = 1


def store_key(entry_id: str) -> str:
    return f"{DOMAIN}.fridge.{entry_id}"


def fitted(coordinator) -> bool:
    return bool(coordinator.data is not None and getattr(coordinator.data, "fridge_fitted", False))


def _in_range(mode: Any, t: Any) -> bool:
    if mode not in FRIDGE_TEMP_RANGE or isinstance(t, bool) or not isinstance(t, (int, float)):
        return False
    lo, hi = FRIDGE_TEMP_RANGE[mode]
    return math.isfinite(t) and lo <= t <= hi


@dataclass
class _Request:
    """One pending request: what it asked for, how to match its result, how to undo it."""

    option: str                          # "off" or a running mode
    temp: float | None
    deadline: float                      # monotonic time after which the car's report wins
    session_id: str | None = None
    # preferences to restore if the car refuses: (previous mode, previous temperature of `option`)
    undo: tuple[str, float | None] | None = None


class FridgeController:
    """Shared state and the only command path for one car's fridge."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, store_key(entry.entry_id))
        self.mode: str = "refrigerate"                       # next mode the switch starts
        self.temps: dict[str, float] = dict(FRIDGE_DEFAULT_TEMP)
        self.lock = asyncio.Lock()
        self._req: _Request | None = None
        self._expire: CALLBACK_TYPE | None = None
        self._listeners: set[Callable[[], None]] = set()
        self._seen: Any = None                               # last report learnt from
        self._awaiting_accept = False                        # a send is in flight; hold results
        self._held: list[PushResult] = []

    # ---- lifecycle --------------------------------------------------------
    async def async_setup(self, entry: ConfigEntry) -> None:
        data = await self._store.async_load() or {}
        if data.get("mode") in FRIDGE_MODES:
            self.mode = data["mode"]
        for m, t in (data.get("temps") or {}).items():
            if _in_range(m, t):
                self.temps[m] = float(t)
        self.sync()
        entry.async_on_unload(async_dispatcher_connect(
            self.hass, SIGNAL_COMMAND_RESULT.format(vin=self.coordinator.vin), self._handle_result))
        entry.async_on_unload(self.coordinator.async_add_listener(self.sync))
        entry.async_on_unload(self._cancel_expiry)

    def _prefs(self) -> dict[str, Any]:
        return {"mode": self.mode, "temps": dict(self.temps)}

    def _save(self) -> None:
        self._store.async_delay_save(self._prefs, 2)

    @callback
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(cb)
        return lambda: self._listeners.discard(cb)

    @callback
    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    # ---- what the entities show -------------------------------------------
    @property
    def pending_option(self) -> str | None:
        return self._req.option if self._req is not None else None

    @property
    def pending_temp(self) -> float | None:
        return self._req.temp if self._req is not None else None

    @property
    def reported_option(self) -> str | None:
        data = self.coordinator.data
        return getattr(data, "fridge_mode", None) if data is not None else None

    @property
    def option(self) -> str | None:
        """Requested state while one is pending, else the car's report (None = unknown)."""
        return self.pending_option if self.pending_option is not None else self.reported_option

    @property
    def running(self) -> bool | None:
        opt = self.option
        return None if opt is None else opt in RUNNING_MODES

    @property
    def temp_mode(self) -> str | None:
        """The mode a temperature edit applies to: the running one, or the next start."""
        opt = self.option
        if opt is None:
            return None
        return opt if opt in RUNNING_MODES else self.mode

    @property
    def temperature(self) -> float | None:
        mode = self.temp_mode
        if mode is None:
            return None
        if self.option not in RUNNING_MODES:      # off: the value kept for the next start
            return self.temps.get(mode, FRIDGE_DEFAULT_TEMP[mode])
        if self.pending_option == mode and self.pending_temp is not None:
            return self.pending_temp
        data = self.coordinator.data
        t = getattr(data, "fridge_temp_c", None) if data is not None else None
        if self.reported_option == mode and _in_range(mode, t):
            return float(t)
        return self.temps.get(mode, FRIDGE_DEFAULT_TEMP[mode])

    # ---- learning from reports ---------------------------------------------
    @callback
    def sync(self) -> None:
        """Learn from a new report (once per report) and settle a confirmed request."""
        data = self.coordinator.data
        if data is None or data is self._seen or self._awaiting_accept:
            return      # while a send is in flight, the report is settled once it finishes
        self._seen = data
        mode, t = getattr(data, "fridge_mode", None), getattr(data, "fridge_temp_c", None)
        req = self._req
        if req is not None and mode == req.option and (
            mode == "off" or req.temp is None or t == req.temp
        ):
            self._clear_pending()
        # a report older than a pending request must not overwrite what was just asked for
        if mode in FRIDGE_MODES and self.pending_option is None:
            changed = mode != self.mode
            self.mode = mode
            if _in_range(mode, t) and self.temps.get(mode) != float(t):
                self.temps[mode], changed = float(t), True
            if changed:
                self._save()
        self._notify()

    @callback
    def _clear_pending(self) -> None:
        self._req = None
        self._cancel_expiry()

    @callback
    def _arm_expiry(self) -> None:
        """(Re)schedule expiry for the current request at its own deadline."""
        self._cancel_expiry()
        if self._req is not None:
            self._expire = async_call_later(
                self.hass, max(0.0, self._req.deadline - monotonic()), self._expired)

    @callback
    def _cancel_expiry(self) -> None:
        if self._expire is not None:
            self._expire()
            self._expire = None

    @callback
    def _expired(self, _now) -> None:
        self._expire = None
        if self._req is not None and monotonic() >= self._req.deadline - 1:
            _LOGGER.debug("fridge request not confirmed within %ss; showing the car's report", REQUEST_SECONDS)
            self._req = None
            self._notify()
        elif self._req is not None:
            self._arm_expiry()

    # ---- command results -----------------------------------------------------
    @callback
    def _handle_result(self, result: PushResult) -> None:
        if self._awaiting_accept:
            self._held.append(result)
        elif self._matches(result):
            self._on_result(result)

    def _matches(self, result: PushResult) -> bool:
        """Does a result answer the pending request? Session id first, else the event name."""
        req = self._req
        if req is None:
            return False
        if result.session_id and req.session_id:
            return result.session_id == req.session_id
        return bool(result.event and result.event in RESULT_EVENTS)

    @callback
    def _on_result(self, result: PushResult) -> None:
        req = self._req
        if result.ok is False and req is not None:
            _LOGGER.warning("car did not apply the fridge request (result code %s)", result.code)
            if req.undo is not None and req.option in FRIDGE_MODES:
                prev_mode, prev_temp = req.undo
                if self.mode == req.option:
                    self.mode = prev_mode
                # keep a temperature edited since; only undo the one this request set
                if prev_temp is not None and self.temps.get(req.option) == req.temp:
                    self.temps[req.option] = prev_temp
                self._save()
            self._clear_pending()
            self._notify()

    @callback
    def _replay(self, held: list[PushResult]) -> None:
        for result in held:
            if self._matches(result):
                self._on_result(result)

    # ---- requests --------------------------------------------------------------
    async def async_set_option(self, option: str) -> None:
        if option not in OPTIONS:
            raise ServiceValidationError(f"Unknown fridge mode {option!r}")
        async with self.lock:
            if option == "off":
                await self._request("off", None)
            else:
                _, t = self._checked(option, self.temps.get(option))
                await self._request(option, t)

    async def async_turn_on(self) -> None:
        async with self.lock:
            mode = self.mode
            _, t = self._checked(mode, self.temps.get(mode))
            await self._request(mode, t)

    async def async_turn_off(self) -> None:
        async with self.lock:
            await self._request("off", None)

    async def async_set_temperature(self, value: float) -> None:
        async with self.lock:
            opt = self.option
            if opt is None:
                raise ServiceValidationError(
                    "The fridge's state is unknown; refresh the car's status and try again")
            mode = opt if opt in RUNNING_MODES else self.mode
            _, t = self._checked(mode, value)
            if opt in RUNNING_MODES:
                await self._request(mode, t)
            else:      # off: nothing to send; remember it for the next start in this mode
                self.temps[mode] = t
                self._save()
                self._notify()

    @staticmethod
    def _checked(mode: str, temperature: float | None) -> tuple[int, float]:
        try:
            return validate_fridge(mode, temperature)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def _request(self, option: str, temp: float | None) -> None:
        """Show ``option`` at once and send it; restore the previous request if sending fails. Lock held."""
        client, vin = self.coordinator.client, self.coordinator.vin
        prev = self._req
        req = _Request(option, temp, deadline=monotonic() + REQUEST_SECONDS)
        self._req = req
        self._arm_expiry()
        self._awaiting_accept, self._held = True, []
        self._notify()
        resp, sent = None, False
        try:
            if option == "off":
                resp = await client.fridge_off(vin)
            else:
                resp = await client.fridge_on(vin, mode=option, temperature=temp)
            sent = True
        except GacError as err:
            raise HomeAssistantError(str(err)) from err
        finally:
            self._awaiting_accept = False
            held, self._held = self._held, []
            if not sent:
                # nothing was accepted: the previous request (if still in time) stands again,
                # with its own session id, deadline and rollback, and sees results held meanwhile
                if self._req is req:
                    self._req = prev if prev is not None and monotonic() < prev.deadline else None
                    self._arm_expiry()
                    self._replay(held)
                self.sync()            # a report that arrived meanwhile, against the restored request
                self._notify()
        req.session_id = command_session_id(resp)
        if option != "off":
            req.undo = (self.mode, self.temps.get(option))
            self.mode, self.temps[option] = option, float(temp)
            self._save()
        if self._req is req:                 # not expired or superseded while sending
            self._replay(held)
        self.sync()                          # a report that arrived meanwhile
        self._notify()
        self.hass.async_create_task(self.coordinator.async_request_refresh())


def controller(coordinator) -> FridgeController:
    return coordinator.config_entry.runtime_data.fridge


def async_add_when_fitted(entry: ConfigEntry, coordinator, add_entities, make: Callable[[], list]) -> None:
    """Add the fridge entities now if the car has one, or when a report first shows one."""
    if fitted(coordinator):
        add_entities(make())
        return
    unsub: Callable[[], None] | None = None

    @callback
    def _check() -> None:
        nonlocal unsub
        if unsub is not None and fitted(coordinator):
            remove, unsub = unsub, None
            remove()
            add_entities(make())

    unsub = coordinator.async_add_listener(_check)

    @callback
    def _stop() -> None:
        nonlocal unsub
        if unsub is not None:
            remove, unsub = unsub, None
            remove()

    entry.async_on_unload(_stop)
