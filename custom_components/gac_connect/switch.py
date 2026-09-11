"""Switches: pre-conditioning, the charge gate, steering-wheel heat, ventilation, flash lights.

Scheduled charging: the car has no plain start/stop; this models the charge
gate. On lets the car charge whenever plugged in; off gates charging via the
schedule. Resuming takes the car a few minutes to act on.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import asyncio
from time import monotonic
from typing import Any

from gac_connect.commands import validate_climate
import logging

from gac_connect.models import ChargingMode, VehicleStatus
from gac_connect import command_session_id
from gac_connect.push import PushResult

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .const import CONF_AC_MINUTES, DEFAULT_AC_MINUTES
from .coordinator import GacCoordinator
from .entity import GacEntity
from . import fridge


@dataclass(frozen=True, kw_only=True)
class GacSwitch(SwitchEntityDescription):
    on_cmd: str
    off_cmd: str
    # None = the car does not report this; the switch keeps the last requested state.
    state: Callable[[VehicleStatus], bool | None] | None = None
    # result events that answer this switch's commands; with none listed, results
    # can only be matched by session id, so a refusal may not clear the state
    events: tuple[str, ...] = ()


_LOGGER = logging.getLogger(__name__)

REQUEST_SECONDS = 180   # a requested state overrides the car's report at most this long


SWITCHES: tuple[GacSwitch, ...] = (
    GacSwitch(key="steering_heat", translation_key="steering_heat", icon="mdi:steering",
              on_cmd="steering-on", off_cmd="steering-off", state=lambda s: s.steering_heat_on,
              events=("control_steering",)),
    GacSwitch(key="lights", translation_key="lights", icon="mdi:car-light-high",
              on_cmd="flash-on", off_cmd="flash-off", state=lambda s: s.lights_on,
              events=("control_light",)),
    GacSwitch(key="ventilation", translation_key="ventilation", icon="mdi:fan",
              on_cmd="ventilate-on", off_cmd="ventilate-off", events=("control_ventilate_mode",)),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[SwitchEntity] = [GacChargeSwitch(coordinator), GacClimateSwitch(coordinator)]
    entities.extend(GacCommandSwitch(coordinator, d) for d in SWITCHES)
    add_entities(entities)
    fridge.async_add_when_fitted(entry, coordinator, add_entities, lambda: [GacFridgeSwitch(coordinator)])


class GacChargeSwitch(GacEntity, SwitchEntity):
    _attr_translation_key = "charging"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "charge_switch")

    @property
    def is_on(self) -> bool | None:
        if self.status is None or self.status.charging_mode is None:
            return None
        # FREE = charge on plug-in ("on"); SCHEDULED gate = paused ("off").
        return self.status.charging_mode is ChargingMode.FREE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"note": "resuming charge can take a few minutes to take effect"}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send(self.coordinator.client.charge_now(self.coordinator.vin))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(self.coordinator.client.charge_pause(self.coordinator.vin))
        await self.coordinator.async_request_refresh()


class GacCommandSwitch(GacEntity, SwitchEntity):
    entity_description: GacSwitch

    def __init__(self, coordinator: GacCoordinator, description: GacSwitch) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._requested: bool | None = None
        self._requested_until: float = 0.0
        self._op_lock = asyncio.Lock()      # one command at a time per entity
        self._result_events = description.events
        self._init_results()
        self._attr_assumed_state = description.state is None

    @property
    def is_on(self) -> bool | None:
        if self._requested is not None:
            return self._requested
        if self.entity_description.state is None or self.status is None:
            return None
        return self.entity_description.state(self.status)

    def _handle_coordinator_update(self) -> None:
        st = self.entity_description.state
        if self._requested is not None and st is not None:
            confirmed = self.status is not None and st(self.status) == self._requested
            if confirmed or monotonic() > self._requested_until:
                self._requested = None   # the car's report is authoritative again
        super()._handle_coordinator_update()

    def _on_command_result(self, result: PushResult) -> None:
        if self._requested is None:
            return
        if result.ok is False:
            _LOGGER.warning("car did not apply %s (result code %s)", self.entity_id, result.code)
            self._requested = None
            self.async_write_ha_state()

    async def _run(self, on: bool, make_request) -> None:
        """Show the requested state at once; undo it if the request itself fails.

        Commands on one entity run one at a time (the request is only created
        once the lock is held), and cancellation restores the previous state.
        """
        async with self._op_lock:
            prev = (self._requested, self._requested_until)
            self._requested, self._requested_until = on, monotonic() + REQUEST_SECONDS
            self._begin_command()
            self.async_write_ha_state()
            resp = None
            try:
                resp = await self._send(make_request())
            finally:
                if resp is None:
                    self._requested, self._requested_until = prev
                    self._end_command(None)
                    self.async_write_ha_state()
                else:
                    self._end_command(command_session_id(resp))
        await self.coordinator.async_request_refresh()

    async def _set(self, on: bool) -> None:
        cmd = self.entity_description.on_cmd if on else self.entity_description.off_cmd
        await self._run(on, lambda: self.coordinator.client.command(self.coordinator.vin, cmd))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)


class GacClimateSwitch(GacCommandSwitch):
    """Plain on/off for cabin pre-conditioning; the climate entity sets the temperature."""

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, GacSwitch(
            key="climate_power", translation_key="climate_power", icon="mdi:air-conditioner",
            on_cmd="aircon-on", off_cmd="aircon-off", state=lambda s: s.ac_on,
            events=("control_air_condition",)))

    async def _set(self, on: bool) -> None:
        client, vin = self.coordinator.client, self.coordinator.vin
        if on:
            minutes = self.coordinator.config_entry.options.get(CONF_AC_MINUTES, DEFAULT_AC_MINUTES)
            target = self.status.ac_target_temp_c if self.status else None
            try:
                target, _ = validate_climate(target, minutes)
            except ValueError:
                target = 24.0   # no usable reported setpoint
            await self._run(on, lambda: client.climate_on(vin, temperature=target, minutes=minutes))
        else:
            await self._run(on, lambda: client.climate_off(vin))


class GacFridgeSwitch(GacEntity, SwitchEntity):
    """Fridge on/off. On resumes the last running mode at its last temperature."""

    _attr_translation_key = "fridge"
    _attr_icon = "mdi:fridge-outline"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "fridge")

    @property
    def _fridge(self) -> fridge.FridgeController:
        return fridge.controller(self.coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._fridge.add_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool | None:
        return self._fridge.running

    def _handle_coordinator_update(self) -> None:
        self._fridge.sync()
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._fridge.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._fridge.async_turn_off()
