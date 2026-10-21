"""Switches: A/C, recirculation, the charge gate, Smart battery temp, sterilisation,
steering-wheel heat, ventilation, flash lights.

Scheduled charging: on returns to the schedule the car last reported (once or
repeating), resent unchanged; off charges whenever plugged in. Neither is a
continuous pause. The car takes a few minutes to act on a change.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from gac_connect.commands import CYCLING_FRESH_AIR, CYCLING_RECIRCULATE
from gac_connect.models import ChargingMode, VehicleStatus

from . import GacConfigEntry, cabin, fridge
from .coordinator import GacCoordinator
from .entity import GacEntity
from .requested import REQUEST_SECONDS, GacRequestedEntity
from .transition import GacTransitionEntity
from .entity_filter import add_configured_entities
from .charge_now import charge_now_request
from .charging import DAYS
from .const import (CONF_ALLOW_ACCOUNT_ALERTS, CONF_ALLOW_CHARGER_UNLOCK, CONF_ALLOW_PLAINTEXT_PUSH,
                    CONF_ALLOW_VEHICLE_SHUTDOWN, CONF_EXPERIMENTAL_PINLESS_UNLOCK, CONF_QUIET_END, CONF_QUIET_START,
                    CONF_TRACK_MOVING, CONF_TRACK_PARKED)
from .option_entity import GacDraftEntity, GacOptionEntity
from .settings import DEFAULT_QUIET, quiet_hours, track


@dataclass(frozen=True, kw_only=True)
class GacSwitch(SwitchEntityDescription):
    on_cmd: str
    off_cmd: str
    # None = the car does not report this; the switch keeps the last requested state.
    state: Callable[[VehicleStatus], bool | None] | None = None
    # result events that answer this switch's commands; with none listed, results
    # can only be matched by session id, so a refusal may not clear the state
    events: tuple[str, ...] = ()
    attributes: Callable[[VehicleStatus], dict[str, Any]] | None = None
    # Without a reported state, how long a request shows before the switch shows idle_state.
    hold_seconds: float = REQUEST_SECONDS
    # Without a reported state, what the switch shows with no request (None = unknown).
    idle_state: bool | None = None


PRECONDITION_MODES = {0: "Off", 1: "Immediately", 2: "Once", 3: "Repeating"}


def _all_windows_open(status: VehicleStatus) -> bool | None:
    windows = [getattr(status, f"{position}_window_open", None)
               for position in ("front_left", "front_right", "rear_left", "rear_right")]
    return None if None in windows else all(windows)


SWITCHES: tuple[GacSwitch, ...] = (
    GacSwitch(
        key="steering_heat",
        translation_key="steering_heat",
        icon="mdi:steering",
        on_cmd="steering-on",
        off_cmd="steering-off",
        state=lambda s: s.steering_heat_on,
        events=("control_steering",),
    ),
    GacSwitch(
        key="lights",
        translation_key="lights",
        icon="mdi:car-light-high",
        on_cmd="flash-on",
        off_cmd="flash-off",
        state=lambda s: s.lights_on,
        events=("control_light",),
    ),
    GacSwitch(
        key="ventilation",
        translation_key="ventilation",
        icon="mdi:fan",
        on_cmd="ventilate-on",
        off_cmd="ventilate-off",
        events=("control_ventilate_mode",),
        # The app: windows drop 2–3 cm and fresh-air circulation runs. The mode is not reported, and a
        # window reports open alike whether it is 2 cm or all the way down (Aion UT, 2026-10-17), so
        # opened windows are not Ventilation: see GacVentilationSwitch.
        state=lambda s: _all_windows_open(s),
    ),
    GacSwitch(
        key="precondition_battery",
        translation_key="precondition_battery",
        icon="mdi:battery-heart-variant",
        on_cmd="battery-precondition",
        off_cmd="battery-precondition-off",
        # On while the car reports any requested or scheduled preconditioning; Off cancels it.
        state=lambda s: getattr(s, "battery_precondition_on", None),
        events=("control_battery_pretreatment",),
        attributes=lambda s: {
            "reported_mode": PRECONDITION_MODES.get(getattr(s, "battery_precondition_mode", None)),
            "reported_status": getattr(s, "battery_precondition_status", None),
        },
    ),
    GacSwitch(
        key="sterilisation",
        translation_key="sterilisation",
        icon="mdi:virus-off-outline",
        on_cmd="antivirus-on",
        off_cmd="antivirus-off",
        # Hot-air sterilisation runs 30 minutes, then the car reports it off.
        state=lambda s: getattr(s, "sterilisation_on", None),
        events=("control_air_cleaning_system",),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[SwitchEntity] = [GacChargeSwitch(coordinator), GacClimateSwitch(coordinator),
                                    GacRecirculationSwitch(coordinator)]
    entities.extend((GacVentilationSwitch if d.key == "ventilation" else GacCommandSwitch)(coordinator, d)
                    for d in SWITCHES)
    add_configured_entities(entry, add_entities, "switch", entities)
    fridge.async_add_when_fitted(entry, coordinator, add_entities, lambda: [GacFridgeSwitch(coordinator)], platform="switch")
    # Settings and the charge window draft, for an admin dashboard (always present).
    settings: list[SwitchEntity] = [GacOptionSwitch(coordinator, key, option) for key, option in OPTION_SWITCHES.items()]
    settings.append(GacQuietHoursSwitch(coordinator))
    settings.extend(GacDraftDaySwitch(coordinator, day) for day in DAYS)
    settings.append(GacDraftUntilSocSwitch(coordinator))
    add_entities(settings)


class GacChargeSwitch(GacTransitionEntity, SwitchEntity):
    _attr_translation_key = "charging"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "charge_switch")

    @property
    def is_on(self) -> bool | None:
        return self._requested_state if self._requested_state is not None else self._reported_state()

    def _reported_state(self) -> bool | None:
        mode = self.status.charging_mode if self.status is not None else None
        if mode not in (ChargingMode.FREE, ChargingMode.SCHEDULED, ChargingMode.LOOP):
            return None
        # On means the car follows a schedule (once or repeating), not that it is charging.
        return mode is not ChargingMode.FREE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "note": "On follows the car's last reported schedule; off charges whenever plugged in. "
                    "Neither pauses charging.",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._run_transition(True, "charge-resume",
                                   lambda: self.coordinator.client.resume_schedule(self.coordinator.vin))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._run_transition(False, "charge-now", lambda: charge_now_request(self.coordinator))


class GacCommandSwitch(GacRequestedEntity, SwitchEntity):
    entity_description: GacSwitch

    def __init__(self, coordinator: GacCoordinator, description: GacSwitch) -> None:
        super().__init__(coordinator, description.key, description.events)
        self.entity_description = description
        # A switch with an idle state shows a toggle; otherwise HA offers separate on and off buttons.
        self._attr_assumed_state = description.state is None and description.idle_state is None

    @property
    def _reports_value(self) -> bool:
        return self.entity_description.state is not None

    def _reported(self) -> bool | None:
        state = self.entity_description.state
        return state(self.status) if state is not None else self.entity_description.idle_state

    def _hold_seconds(self) -> float:
        return self.entity_description.hold_seconds

    @property
    def is_on(self) -> bool | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attributes = self.entity_description.attributes
        return attributes(self.status) if attributes is not None and self.status is not None else None

    async def _set(self, on: bool) -> None:
        cmd = self.entity_description.on_cmd if on else self.entity_description.off_cmd
        await self._run(on, lambda: self.coordinator.client.command(self.coordinator.vin, cmd), command=cmd)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)


class GacVentilationSwitch(GacCommandSwitch, RestoreEntity):
    """On once Home Assistant has started Ventilation, until it is turned off or a window closes.

    The car reports neither the mode nor how far a window is down, so windows opened another way
    are not Ventilation, and Ventilation started in the GAC app shows off here.
    """

    def __init__(self, coordinator: GacCoordinator, description: GacSwitch) -> None:
        super().__init__(coordinator, description)
        self._started = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        self._started = last is not None and last.state == "on"

    def _reported(self) -> bool | None:
        windows = _all_windows_open(self.status)
        if not self._started:
            return False
        return windows

    def _handle_coordinator_update(self) -> None:
        # Any window closing ends it, even if windows are opened again later.
        if self._started and self._requested is None and _all_windows_open(self.status) is False:
            self._started = False
        super()._handle_coordinator_update()

    def _on_command_result(self, result) -> None:
        if result.ok is False and self._requested is True:
            self._started = False
        super()._on_command_result(result)

    async def _set(self, on: bool) -> None:
        await super()._set(on)
        self._started = on


class GacClimateSwitch(GacEntity, SwitchEntity):
    """The cabin A/C, on whenever it runs (the car does not report who started it).

    Turning it on starts a remote run; the climate entity sets the temperature."""

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "climate_power")
        self._cabin = cabin.controller(coordinator)

    _attr_translation_key = "climate_power"
    _attr_icon = "mdi:air-conditioner"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._cabin.add_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool | None:
        return self._cabin.on

    def _handle_coordinator_update(self) -> None:
        self._cabin.sync()
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._cabin.async_set_power(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._cabin.async_set_power(False)


class GacRecirculationSwitch(GacEntity, SwitchEntity):
    """Air source as reported: on recirculates, off draws fresh air (or the console's Auto, reported alike).

    Changes are sent only while A/C runs (renewing the timed run); an Aion UT
    ignores a remote air-source change otherwise.
    """

    _attr_translation_key = "recirculation"
    _attr_icon = "mdi:autorenew"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "recirculation")
        self._cabin = cabin.controller(coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._cabin.add_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool | None:
        mode = self._cabin.cycling_mode
        return None if mode not in (CYCLING_RECIRCULATE, CYCLING_FRESH_AIR) else mode == CYCLING_RECIRCULATE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"reported_cycling_mode": getattr(self.status, "ac_cycling_mode", None)}

    def _handle_coordinator_update(self) -> None:
        self._cabin.sync()
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._cabin.async_set_cycling_mode(CYCLING_RECIRCULATE)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._cabin.async_set_cycling_mode(CYCLING_FRESH_AIR)


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


# entity key -> option, as on the options page
OPTION_SWITCHES = {
    "allow_plaintext_push": CONF_ALLOW_PLAINTEXT_PUSH,
    "track_parked": CONF_TRACK_PARKED,
    "track_moving": CONF_TRACK_MOVING,
    "allow_remote_unlock": CONF_EXPERIMENTAL_PINLESS_UNLOCK,
    "allow_charger_unlock": CONF_ALLOW_CHARGER_UNLOCK,
    "allow_account_alerts": CONF_ALLOW_ACCOUNT_ALERTS,
    "allow_vehicle_shutdown": CONF_ALLOW_VEHICLE_SHUTDOWN,
}


class GacOptionSwitch(GacOptionEntity, SwitchEntity):
    """One on/off option of the options page."""

    def __init__(self, coordinator: GacCoordinator, key: str, option: str) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._option = option

    @property
    def is_on(self) -> bool:
        if self._option in (CONF_TRACK_PARKED, CONF_TRACK_MOVING):
            return track(self.options)[self._option]
        return self.options.get(self._option) is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.set_options(**{self._option: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.set_options(**{self._option: False})


class GacQuietHoursSwitch(GacOptionEntity, SwitchEntity):
    """No polling between the quiet hours start and end; off clears both times."""

    _attr_translation_key = "quiet_hours"
    _attr_icon = "mdi:sleep"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "quiet_hours")
        self._last = DEFAULT_QUIET

    @property
    def is_on(self) -> bool:
        return quiet_hours(self.options) is not None

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            start, end = self._last
            self.set_options(**{CONF_QUIET_START: start, CONF_QUIET_END: end})

    async def async_turn_off(self, **kwargs: Any) -> None:
        if (current := quiet_hours(self.options)) is not None:
            self._last = current      # turning it back on restores these times
        self.set_options(**{CONF_QUIET_START: "", CONF_QUIET_END: ""})


class GacDraftDaySwitch(GacDraftEntity, SwitchEntity):
    """A day of the charge window being prepared; no days is a one-time window."""

    _attr_icon = "mdi:calendar-week"

    def __init__(self, coordinator: GacCoordinator, day: str) -> None:
        super().__init__(coordinator, f"charge_window_{day}")
        self._attr_translation_key = f"charge_window_{day}"
        self._day = day

    @property
    def is_on(self) -> bool:
        return self._day in self.draft.days

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.draft.set(days=self.draft.days | {self._day})

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.draft.set(days=self.draft.days - {self._day})


class GacDraftUntilSocSwitch(GacDraftEntity, SwitchEntity):
    """The charge window being prepared stops at the car's charge limit, not at its stop time."""

    _attr_translation_key = "charge_window_until_soc"
    _attr_icon = "mdi:battery-charging-high"

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "charge_window_until_soc")

    @property
    def is_on(self) -> bool:
        return self.draft.until_soc

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.draft.set(until_soc=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.draft.set(until_soc=False)
