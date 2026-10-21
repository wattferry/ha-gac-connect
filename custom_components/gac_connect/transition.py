"""Keep a requested transition pending until telemetry confirms it or it expires."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
from time import monotonic
from typing import Any

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.event import async_call_later

from gac_connect import command_session_id
from gac_connect.push import PushResult
from .entity import GacEntity

_LOGGER = logging.getLogger(__name__)
REQUEST_SECONDS = 180


class GacTransitionEntity(GacEntity):
    """Serialize commands without mistaking acceptance or cached state for completion."""

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._requested_state: bool | None = None
        self._requested_until = 0.0
        self._baseline = None
        self._op_lock = asyncio.Lock()
        self._expire: CALLBACK_TYPE | None = None
        self._init_results()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._clear_pending)

    def _reported_state(self) -> bool | None:
        """Return the reported boolean represented by this control."""
        raise NotImplementedError

    @callback
    def _cancel_expiry(self) -> None:
        if self._expire is not None:
            self._expire()
            self._expire = None

    @callback
    def _clear_pending(self) -> None:
        self._requested_state = None
        self._session_id = None
        self._cancel_expiry()

    @callback
    def _arm_expiry(self) -> None:
        self._cancel_expiry()
        if self._requested_state is not None:
            self._expire = async_call_later(
                self.coordinator.hass, max(0, self._requested_until - monotonic()), self._expired
            )

    @callback
    def _expired(self, _now) -> None:
        self._expire = None
        if self._requested_state is None:
            return
        if monotonic() < self._requested_until:
            self._arm_expiry()
            return
        _LOGGER.warning("%s command was not confirmed within %ss; showing the last report",
                        self.entity_id, REQUEST_SECONDS)
        self._clear_pending()
        self.async_write_ha_state()

    @callback
    def _sync_pending(self) -> None:
        if self._requested_state is None or self._awaiting_accept:
            return
        data = self.status
        if data is None or data == self._baseline:
            return
        before = self._baseline.updated_ms if self._baseline is not None else None
        if before is not None and data.updated_ms is not None and data.updated_ms < before:
            return  # An older backend report is not confirmation.
        # Some backends reuse updateTime even when readings change. Compare the
        # actual state too instead of waiting forever for that timestamp to advance.
        if self._reported_state() is self._requested_state:
            self._clear_pending()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync_pending()
        super()._handle_coordinator_update()

    def _matches(self, result: PushResult) -> bool:
        # For security-sensitive controls, an event name without the exact
        # accepted session ID must never settle a different pending command.
        return bool(self._requested_state is not None and self._session_id
                    and result.session_id == self._session_id
                    and result.vin in (None, self.coordinator.vin))

    def _on_command_result(self, result: PushResult) -> None:
        if result.ok is False and self._requested_state is not None:
            _LOGGER.warning("car did not apply %s (result code %s: %s)", self.entity_id, result.code,
                            result.reason or "unknown reason")
            self._clear_pending()
            self.async_write_ha_state()
        # Success triggers shared follow-up polls. Only telemetry settles the state.

    async def _run_transition(
        self, target: bool, command: str, make_request: Callable[[], Awaitable[Any]],
    ) -> None:
        async with self._op_lock:
            previous = (self._requested_state, self._requested_until, self._session_id, self._baseline)
            self._requested_state, self._requested_until = target, monotonic() + REQUEST_SECONDS
            self._baseline = self.status
            self._begin_command()
            self._arm_expiry()
            self.async_write_ha_state()
            accepted = False
            try:
                response = await self._send(make_request(), command=command)
                accepted = True
            finally:
                if accepted:
                    self._end_command(command_session_id(response))
                else:
                    state, deadline, session_id, baseline = previous
                    self._requested_state = state if deadline > monotonic() else None
                    self._requested_until, self._baseline = deadline, baseline
                    self._end_command(session_id)
                self._sync_pending()  # A new report may have arrived while sending.
                self._arm_expiry()
                self.async_write_ha_state()
