"""Covers: windows, sunroof and tailgate.

The state is unknown when the car does not report it. Available remote actions
vary by model; a state reading alone does not confirm opening or closing support.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gac_connect.models import VehicleStatus

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .coordinator import GacCoordinator
from .entity_filter import add_configured_entities
from .transition import GacTransitionEntity


@dataclass(frozen=True, kw_only=True)
class GacCover(CoverEntityDescription):
    is_open: Callable[[VehicleStatus], bool | None]
    open_cmd: str
    close_cmd: str


COVERS: tuple[GacCover, ...] = (
    GacCover(key="windows", translation_key="windows", device_class=CoverDeviceClass.WINDOW,
             is_open=lambda s: s.window_open, open_cmd="window-open", close_cmd="window-close"),
    GacCover(key="sunroof", translation_key="sunroof", device_class=CoverDeviceClass.WINDOW,
             is_open=lambda s: s.sunroof_open, open_cmd="sunroof-open", close_cmd="sunroof-close"),
    GacCover(key="tailgate", translation_key="tailgate", device_class=CoverDeviceClass.DOOR,
             is_open=lambda s: s.hatch_open, open_cmd="tailgate-open", close_cmd="tailgate-close"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    add_configured_entities(entry, add_entities, "cover",
                            (GacCoverEntity(coordinator, d) for d in COVERS))


class GacCoverEntity(GacTransitionEntity, CoverEntity):
    entity_description: GacCover
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, coordinator: GacCoordinator, description: GacCover) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_closed(self) -> bool | None:
        if self.status is None:
            return None
        v = self.entity_description.is_open(self.status)
        return None if v is None else not v

    def _reported_state(self) -> bool | None:
        return self.is_closed

    @property
    def is_opening(self) -> bool:
        return self._requested_state is False

    @property
    def is_closing(self) -> bool:
        return self._requested_state is True

    async def async_open_cover(self, **kwargs: Any) -> None:
        command = self.entity_description.open_cmd
        await self._run_transition(False, command, lambda: self.coordinator.client.command(self.coordinator.vin, command))

    async def async_close_cover(self, **kwargs: Any) -> None:
        command = self.entity_description.close_cmd
        await self._run_transition(True, command, lambda: self.coordinator.client.command(self.coordinator.vin, command))
