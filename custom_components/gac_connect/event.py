"""Events: alerts from the car's report, and (when allowed) from GAC's alert list."""
from __future__ import annotations

from time import monotonic

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from gac_connect.alerts import ALERT_KEYS, Alert

from . import GacConfigEntry
from .account_alerts import SIGNAL_ACCOUNT_ALERT, alert_attributes
from .car_alerts import CAR_ALERT_TYPES, CarAlertWatcher
from .const import CONF_MODEL
from .entity import GacEntity


async def async_setup_entry(hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[EventEntity] = [GacCarAlertEvent(coordinator)]
    alerts = getattr(entry.runtime_data, "alerts", None)
    if alerts is not None and alerts.enabled:
        entities.append(GacAccountAlertEvent(coordinator))
    add_entities(entities)


class GacCarAlertEvent(GacEntity, EventEntity):
    """Fires when the car's report shows charging finished, the car left unlocked or open, and so on."""

    _attr_translation_key = "car_alert"
    _attr_event_types = list(CAR_ALERT_TYPES)

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "car_alert")
        self._watcher = CarAlertWatcher(coordinator.config_entry.data.get(CONF_MODEL))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._watcher.observe(self.coordinator.data, monotonic())     # the report at start-up is the baseline

    @callback
    def _handle_coordinator_update(self) -> None:
        # Write each event as it fires: alerts raised by the same report (left unlocked and
        # a window left open, say) would otherwise leave only the last one recorded.
        for event_type, attributes in self._watcher.observe(self.coordinator.data, monotonic()):
            self._trigger_event(event_type, attributes)
            self.async_write_ha_state()
        super()._handle_coordinator_update()


class GacAccountAlertEvent(GacEntity, EventEntity):
    """Fires for each new alert in GAC's alert list."""

    _attr_translation_key = "gac_alert"
    _attr_event_types = list(ALERT_KEYS)

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "gac_alert")

    @property
    def available(self) -> bool:
        return True       # the alert list does not depend on the car's report

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_ACCOUNT_ALERT.format(vin=self.coordinator.vin), self._on_alert))

    @callback
    def _on_alert(self, alert: Alert) -> None:
        self._trigger_event(alert.key, alert_attributes(alert))
        self.async_write_ha_state()
