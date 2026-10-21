"""Options as dashboard entities, and the charge window draft.

Every option on the options page can also be changed by an entity (Configuration
section of the device), so an admin dashboard can manage them. Options Home Assistant
reads at the moment it needs them apply at once; the others add or remove entities or
start a connection, so changing one reloads the integration, as the options page does.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .charging import DAYS
from .const import (
    CONF_DASHBOARD_CARDS,
    CONF_ENABLE_ENTITIES,
    CONF_ENABLE_TRACKER,
    CONF_EXPERIMENTAL_PINLESS_UNLOCK,
    CONF_LOAD_CARDS,
    CONF_OMIT_ENTITIES,
    CONF_PICTURE,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_MOVING,
    CONF_TRACK_PARKED,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .location import location_enabled, tracking_choices

# Read when needed (polling, quiet hours, unlock requests, the shown position): no reload.
LIVE_OPTIONS = frozenset({CONF_SCAN_INTERVAL, CONF_QUIET_START, CONF_QUIET_END, CONF_EXPERIMENTAL_PINLESS_UNLOCK,
                          CONF_TRACK_PARKED, CONF_TRACK_MOVING, CONF_ENABLE_TRACKER, CONF_PICTURE, CONF_LOAD_CARDS,
                          CONF_DASHBOARD_CARDS})
MAX_SCAN_INTERVAL = 3600
DEFAULT_QUIET = ("22:00", "07:00")
SIGNAL_OPTIONS = "gac_connect_options_{entry_id}"
_CLOCK = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")


def needs_reload(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    """Whether a change of options adds or removes entities or connections."""
    def shape(options: Mapping[str, Any]) -> tuple:
        rest = {key: value for key, value in options.items() if key not in LIVE_OPTIONS}
        return tuple(sorted((key, repr(value)) for key, value in rest.items())), location_enabled(options)
    return shape(before) != shape(after)


def scan_interval(options: Mapping[str, Any]) -> timedelta:
    try:
        seconds = max(MIN_SCAN_INTERVAL, int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)))
    except (TypeError, ValueError):
        seconds = DEFAULT_SCAN_INTERVAL
    return timedelta(seconds=seconds)


@callback
def async_set_options(hass: HomeAssistant, entry, updates: Mapping[str, Any]) -> None:
    """Change options the way the options page does (validated, location flag kept in step)."""
    options = {**entry.options, **updates}
    start, end = options.get(CONF_QUIET_START) or "", options.get(CONF_QUIET_END) or ""
    if bool(start) != bool(end):
        raise ServiceValidationError("Quiet hours need both a start and an end")
    if start and start == end:
        raise ServiceValidationError("Quiet hours must start and end at different times")
    if set(options.get(CONF_ENABLE_ENTITIES, ())) & set(options.get(CONF_OMIT_ENTITIES, ())):
        raise ServiceValidationError("An entity cannot be both always shown and omitted")
    options[CONF_ENABLE_TRACKER] = location_enabled(options)
    options.pop(CONF_PICTURE, None)
    hass.config_entries.async_update_entry(entry, options=options)


@callback
def async_options_applied(hass: HomeAssistant, entry) -> None:
    """Tell option entities and the poller about options changed without a reload."""
    coordinator = entry.runtime_data.coordinator
    coordinator.async_set_interval(scan_interval(entry.options))
    async_dispatcher_send(hass, SIGNAL_OPTIONS.format(entry_id=entry.entry_id))
    # Entities that read options (the shown position) publish again at once, so a location
    # tracking choice takes effect now rather than at the next report or freshness tick.
    coordinator.async_update_listeners()


def quiet_hours(options: Mapping[str, Any]) -> tuple[str, str] | None:
    start, end = options.get(CONF_QUIET_START) or "", options.get(CONF_QUIET_END) or ""
    return (start, end) if _CLOCK.fullmatch(start) and _CLOCK.fullmatch(end) else None


def track(options: Mapping[str, Any]) -> dict[str, bool]:
    parked, moving = tracking_choices(options)
    return {CONF_TRACK_PARKED: parked, CONF_TRACK_MOVING: moving}


class ChargeDraft:
    """The charge window being prepared on a dashboard, filled from the car's reported window.

    Each time the car reports a different window, the draft takes it over; edits stay until
    then or until they are sent. Nothing reaches the car before Send charge window. The
    car's report of the window just sent leaves the draft as entered, even where the start
    was moved to the next minute (a one-time window already open).
    """

    def __init__(self) -> None:
        self.start: str | None = None
        self.stop: str | None = None
        self.days: set[str] = set()
        self.until_soc = False
        self._reported: tuple | None = None
        self._sent: tuple | None = None        # (start, stop, weekly, end type); None for any start or stop
        self._listeners: list[Callable[[], None]] = []

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _changed(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def observe(self, status) -> None:
        if status is None:
            return
        start, stop = getattr(status, "charge_window_start", None), getattr(status, "charge_window_stop", None)
        weekly = getattr(status, "charge_weekly", None)
        end_type = getattr(status, "charge_end_type", None)
        reported = (start, stop, weekly, end_type)
        if reported == self._reported or (start is None and stop is None):
            return      # unchanged, or no window to copy (Not set)
        self._reported = reported
        if self._sent is not None:
            sent_start, sent_stop, sent_weekly, sent_end = self._sent
            if sent_start in (None, start) and (weekly or 0, end_type) == (sent_weekly, sent_end) \
                    and sent_stop in (None, stop):
                self._sent = None
                return      # the car took what was sent: keep the draft as entered
        if start is not None and _CLOCK.fullmatch(start):
            self.start = start
        if stop is not None and _CLOCK.fullmatch(stop):
            self.stop = stop
        if type(weekly) is int and 0 <= weekly <= 127:
            self.days = {day for index, day in enumerate(DAYS) if weekly & (1 << index)}
        if end_type in (0, 1):
            self.until_soc = end_type == 1
        self._changed()

    def mark_sent(self, start: str | None, stop: str | None, weekly: int, until_soc: bool) -> None:
        """Remember the window as the car will report it, so that report does not overwrite edits
        (any start for None)."""
        self._sent = (start, None if until_soc else stop, weekly, int(until_soc))

    def set(self, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(self, key, value)
        self._changed()

    @property
    def weekly(self) -> int:
        return sum(1 << index for index, day in enumerate(DAYS) if day in self.days)
