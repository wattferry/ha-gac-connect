"""Buttons: refresh, charging, charging connector unlock, horn and vehicle shutdown; sending the
prepared charge window and reading the capability list again (settings)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from gac_connect.client import GacClient
from gac_connect.errors import GacError

from . import GacConfigEntry
from .charge_now import charge_now_request
from .coordinator import GacCoordinator
from .entity import GacEntity
from .entity_filter import add_configured_entities


@dataclass(frozen=True, kw_only=True)
class GacButton(ButtonEntityDescription):
    press: Callable[[GacClient, str], Awaitable[object]] | None    # None: Charge now
    command: str


BUTTONS: tuple[GacButton, ...] = (
    GacButton(key="vehicle_power_off", command="vehicle-power-off", translation_key="vehicle_power_off",
              icon="mdi:power", press=lambda c, vin: c.command(vin, "vehicle-power-off")),
    GacButton(key="charge_now", command="charge-now", translation_key="charge_now", press=None),
    GacButton(key="charger_unlock", command="charger-unlock", translation_key="charger_unlock",
              icon="mdi:lock-open-variant", press=lambda c, vin: c.command(vin, "charger-unlock")),
    GacButton(key="horn", command="horn-on", translation_key="horn", icon="mdi:bullhorn", press=lambda c, vin: c.command(vin, "horn-on")),
)


async def async_setup_entry(hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[ButtonEntity] = [GacButtonEntity(coordinator, d) for d in BUTTONS]
    entities.append(GacRefreshButton(coordinator))
    add_configured_entities(entry, add_entities, "button", entities)
    add_entities([GacSendWindowButton(coordinator), GacCapabilitiesButton(coordinator)])


class GacButtonEntity(GacEntity, ButtonEntity):
    entity_description: GacButton

    def __init__(self, coordinator: GacCoordinator, description: GacButton) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        press = self.entity_description.press
        request = (charge_now_request(self.coordinator) if press is None
                   else press(self.coordinator.client, self.coordinator.vin))
        await self._send(request, command=self.entity_description.command)


class GacRefreshButton(GacEntity, ButtonEntity):
    _attr_translation_key = "refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC   # reads the cloud status; controls nothing in the car

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    @property
    def available(self) -> bool:
        return True  # Retrying a failed cloud read must remain possible.

    async def async_press(self) -> None:
        await self.coordinator.async_manual_refresh()


class GacSendWindowButton(GacEntity, ButtonEntity):
    """Send the prepared charge window (Charge window start/stop, Charge on…, Stop at charge limit)."""

    _attr_translation_key = "send_charge_window"
    _attr_icon = "mdi:calendar-check"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "send_charge_window")

    async def async_press(self) -> None:
        from .api import validate_clock
        from .charging import window_target
        from .command_tracking import async_send

        draft = self.coordinator.config_entry.runtime_data.charge_draft
        try:
            start = validate_clock(draft.start)
            stop = validate_clock(draft.stop) if draft.stop or not draft.until_soc else None
        except ValueError as err:
            raise ServiceValidationError("Set the charge window start, and its stop unless it stops at the "
                                         "charge limit") from err
        if not draft.until_soc and start == stop:
            raise ServiceValidationError("The charge window must start and stop at different times")
        stop = None if draft.until_soc else stop       # stopping at the charge limit sends no stop time
        weekly = draft.weekly
        coordinator = self.coordinator
        expected = window_target(start, stop, weekly, draft.until_soc, getattr(coordinator.client, "timezone", None))
        draft.mark_sent(expected["charge_window_start"], stop, weekly, draft.until_soc)
        try:
            await async_send(coordinator, "charge-window", coordinator.client.set_charge_window(
                coordinator.vin, start, stop, weekly=weekly, until_soc=draft.until_soc), expected=expected)
        except ValueError as err:
            raise ServiceValidationError(f"{str(err)[:1].upper()}{str(err)[1:]}") from err
        except GacError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_refresh_now()       # show the car's answer, not the old report


class GacCapabilitiesButton(GacEntity, ButtonEntity):
    """Read the car's capability list again (for example after a software update); reloads."""

    _attr_translation_key = "refresh_capabilities"
    _attr_icon = "mdi:car-cog"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GacCoordinator) -> None:
        super().__init__(coordinator, "refresh_capabilities")

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        coordinator = self.coordinator
        try:
            await coordinator.capabilities.async_read_capability_list(coordinator.client, coordinator.vin)
        except GacError as err:
            raise HomeAssistantError(f"The capability list could not be read: {err}") from err
        self.hass.config_entries.async_schedule_reload(coordinator.config_entry.entry_id)
