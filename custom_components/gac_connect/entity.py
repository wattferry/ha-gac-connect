"""Base entity: one device per VIN, coordinator-driven."""
from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

from gac_connect import GacError

from homeassistant.exceptions import HomeAssistantError
from gac_connect.push import PushResult

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, DOMAIN, SIGNAL_COMMAND_RESULT
from .coordinator import GacCoordinator


class GacEntity(CoordinatorEntity[GacCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: GacCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.vin}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.vin)},
            manufacturer="GAC Aion",
            name=coordinator.config_entry.data.get(CONF_MODEL) or "Aion",
            model=coordinator.config_entry.data.get(CONF_MODEL),
            serial_number=coordinator.vin,
        )

    # ---- command-result correlation --------------------------------------
    # A command's result may arrive before the request that sent it has
    # returned the session id; results seen in that window are held back and
    # matched once the id is known.
    _result_events: tuple[str, ...] = ()

    def _init_results(self) -> None:
        self._session_id: str | None = None
        self._awaiting_accept = False
        self._held: list[PushResult] = []

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if not hasattr(self, "_held"):
            self._init_results()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_COMMAND_RESULT.format(vin=self.coordinator.vin), self._handle_result
        ))

    @callback
    def _handle_result(self, result: PushResult) -> None:
        if self._awaiting_accept:
            self._held.append(result)
            return
        if self._matches(result):
            self._on_command_result(result)

    def _matches(self, result: PushResult) -> bool:
        """Does a result answer the command this entity is waiting on?

        Only a matching session id, or a result event mapped to this entity,
        counts; anything that cannot be correlated leaves entity state alone.
        """
        if result.session_id and self._session_id:
            return result.session_id == self._session_id
        if result.session_id and self._awaiting_accept:
            return False
        return bool(self._result_events and result.event and result.event in self._result_events)

    def _begin_command(self) -> None:
        self._session_id = None
        self._awaiting_accept = True
        self._held = []

    @callback
    def _end_command(self, session_id: str | None) -> None:
        """Record the accepted command's id and replay results held meanwhile."""
        self._session_id = session_id
        self._awaiting_accept = False
        held, self._held = self._held, []
        for result in held:
            if self._matches(result):
                self._on_command_result(result)

    def _on_command_result(self, result: PushResult) -> None:
        """React to a result that answers this entity's command; override."""

    @property
    def status(self):
        return self.coordinator.data

    async def _send(self, coro: Awaitable[Any]) -> Any:
        """Run a vehicle command, surfacing library errors as HA errors."""
        try:
            return await coro
        except GacError as err:
            raise HomeAssistantError(str(err)) from err
