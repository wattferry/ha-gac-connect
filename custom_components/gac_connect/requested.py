"""Show a requested value until a report confirms it, the car refuses it or it expires."""
from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.event import async_call_later

from gac_connect import command_session_id
from gac_connect.push import PushResult

from .entity import GacEntity

_LOGGER = logging.getLogger(__name__)

REQUEST_SECONDS = 180  # a requested value overrides the car's report at most this long


class GacRequestedEntity(GacEntity):
    """Commands run one at a time; the requested value shows at once and yields to a matching report."""

    def __init__(self, coordinator, key: str, events: tuple[str, ...] = ()) -> None:
        super().__init__(coordinator, key)
        self._requested: Any = None
        self._requested_until: float = 0.0
        self._baseline = None       # the report the request was made against
        self._op_lock = asyncio.Lock()  # one command at a time per entity
        # result events that answer this entity's commands; with none listed, results
        # can only be matched by session id, so a refusal may not clear the state
        self._result_events = events
        self._init_results()
        self._expire: CALLBACK_TYPE | None = None

    def _reported(self) -> Any:
        """The value in the latest report, or None when unknown."""
        return None

    @property
    def _reports_value(self) -> bool:
        """Whether the car reports this value; if not, a request is assumed until it expires."""
        return True

    def _hold_seconds(self) -> float:
        """How long a requested value is shown before the report (or unknown) takes over."""
        return REQUEST_SECONDS

    @property
    def _value(self) -> Any:
        if self._requested is not None:
            return self._requested
        return None if self.status is None else self._reported()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._cancel_expiry)

    @callback
    def _cancel_expiry(self) -> None:
        if self._expire is not None:
            self._expire()
            self._expire = None

    @callback
    def _arm_expiry(self) -> None:
        self._cancel_expiry()
        if self._requested is not None:
            self._expire = async_call_later(self.hass, max(0, self._requested_until - monotonic()), self._expired)

    @callback
    def _expired(self, _now) -> None:
        self._expire = None
        if monotonic() >= self._requested_until:
            self._requested = None
            self.async_write_ha_state()
        else:
            self._arm_expiry()

    def _newer_report(self) -> bool:
        """A report taken after the request's baseline (an out-of-order older one confirms nothing)."""
        data, base = self.status, self._baseline
        if data is None or data is base:
            return False
        before = getattr(base, "updated_ms", None)
        after = getattr(data, "updated_ms", None)
        return before is None or after is None or after >= before

    def _handle_coordinator_update(self) -> None:
        if self._requested is not None and self._reports_value:
            confirmed = self._newer_report() and self._reported() == self._requested
            if confirmed or monotonic() > self._requested_until:
                self._requested = None  # the car's report is authoritative again
                self._cancel_expiry()
        super()._handle_coordinator_update()

    def _on_command_result(self, result: PushResult) -> None:
        if self._requested is None:
            return
        if result.ok is False:
            _LOGGER.warning("car did not apply %s (result code %s: %s)", self.entity_id, result.code,
                            result.reason or "unknown reason")
            self._requested = None
            self._cancel_expiry()
            self.async_write_ha_state()

    async def _run(self, value: Any, make_request, *, command: str, expected=None) -> None:
        """Show the requested value at once; undo it if the request itself fails.

        Commands on one entity run one at a time (the request is only created
        once the lock is held), and cancellation restores the previous state.
        """
        async with self._op_lock:
            prev = (self._requested, self._requested_until)
            previous_session = self._session_id
            self._requested, self._requested_until = value, monotonic() + self._hold_seconds()
            self._baseline = self.status
            self._begin_command()
            self._arm_expiry()
            self.async_write_ha_state()
            resp = None
            try:
                resp = await self._send(make_request(), command=command, expected=expected)
            finally:
                if resp is None:
                    self._requested, self._requested_until = prev
                    self._end_command(previous_session)
                    self._arm_expiry()
                    self.async_write_ha_state()
                else:
                    self._end_command(command_session_id(resp))
                    self._arm_expiry()
