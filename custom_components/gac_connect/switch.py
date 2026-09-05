"""Switches: the charge gate, steering-wheel heat and cabin ventilation.

Scheduled charging: the car has no plain start/stop; this models the charge
gate. On lets the car charge whenever plugged in; off gates charging via the
schedule. Resuming takes the car a few minutes to act on.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from gac_connect.models import ChargingMode, VehicleStatus

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .coordinator import GacCoordinator
from .entity import GacEntity


@dataclass(frozen=True, kw_only=True)
class GacSwitch(SwitchEntityDescription):
    on_cmd: str
    off_cmd: str
    # None = the car does not report this; the switch keeps the last requested state.
    state: Callable[[VehicleStatus], bool | None] | None = None


REQUEST_SECONDS = 180   # a requested state overrides the car's report at most this long


SWITCHES: tuple[GacSwitch, ...] = (
    GacSwitch(key="steering_heat", translation_key="steering_heat", icon="mdi:steering",
              on_cmd="steering-on", off_cmd="steering-off", state=lambda s: s.steering_heat_on),
    GacSwitch(key="ventilation", translation_key="ventilation", icon="mdi:fan",
              on_cmd="ventilate-on", off_cmd="ventilate-off"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[SwitchEntity] = [GacChargeSwitch(coordinator)]
    entities.extend(GacCommandSwitch(coordinator, d) for d in SWITCHES)
    add_entities(entities)


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

    async def _set(self, on: bool) -> None:
        cmd = self.entity_description.on_cmd if on else self.entity_description.off_cmd
        await self._send(self.coordinator.client.command(self.coordinator.vin, cmd))
        self._requested = on
        self._requested_until = monotonic() + REQUEST_SECONDS
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
