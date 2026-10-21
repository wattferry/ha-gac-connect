"""Sensors: battery, range, odometer, temperatures, charging, tyres."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from gac_connect.models import VehicleStatus

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergyDistance,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

try:
    from homeassistant.const import UnitOfDensity
except ImportError:  # older releases (2025.3 among them) predate UnitOfDensity
    from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER as PM25_UNIT
else:
    PM25_UNIT = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER

from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import GacConfigEntry, fridge
from gac_connect.alerts import ALERT_KEYS
from .account_alerts import SIGNAL_ACCOUNT_ALERTS_UPDATED, alert_attributes
from .entity import GacEntity
from .entity_filter import OMIT_OPTIONS, add_configured_entities
from .const import CONF_ENABLE_ENTITIES, CONF_OMIT_ENTITIES
from .command_tracking import STATES as COMMAND_STATES
from .charging import schedule_attributes, schedule_mode
from .location import shown_position


@dataclass(frozen=True, kw_only=True)
class GacActivityDescription(SensorEntityDescription):
    value: Callable


ACTIVITY_SENSORS = (
    GacActivityDescription(key="last_command", translation_key="last_command", device_class=SensorDeviceClass.ENUM,
                           options=COMMAND_STATES, value=lambda c: c.commands.state),
    GacActivityDescription(key="data_freshness", translation_key="data_freshness",
                           device_class=SensorDeviceClass.ENUM,
                           options=["recent", "stale", "not_reported", "clock_mismatch"],
                           value=lambda c: c.freshness),
    GacActivityDescription(key="last_refresh", translation_key="last_refresh",
                           device_class=SensorDeviceClass.TIMESTAMP, value=lambda c: c.last_refresh_success),
    GacActivityDescription(key="polling_status", translation_key="polling_status",
                           device_class=SensorDeviceClass.ENUM,
                           options=["waiting", "ok", "quiet_hours", "rate_limited", "error", "auth_required"],
                           value=lambda c: c.polling_state),
)


@dataclass(frozen=True, kw_only=True)
class GacSensor(SensorEntityDescription):
    value: Callable[[VehicleStatus], str | float | int | datetime | None]


def gps_coordinates(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return f"{latitude:.6f}, {longitude:.6f}"


SENSORS: tuple[GacSensor, ...] = (
    GacSensor(key="charge_schedule", translation_key="charge_schedule", device_class=SensorDeviceClass.ENUM,
              options=["unrestricted", "scheduled", "not_set", "not_reported"], icon="mdi:calendar-clock",
              value=schedule_mode),
    GacSensor(key="soc", translation_key="soc", device_class=SensorDeviceClass.BATTERY,
              native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
              value=lambda s: s.soc),
    GacSensor(key="range", translation_key="range", device_class=SensorDeviceClass.DISTANCE,
              native_unit_of_measurement=UnitOfLength.KILOMETERS,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: s.range_km),
    GacSensor(key="odometer", translation_key="odometer", device_class=SensorDeviceClass.DISTANCE,
              native_unit_of_measurement=UnitOfLength.KILOMETERS,
              state_class=SensorStateClass.TOTAL_INCREASING, value=lambda s: s.odometer_km),
    GacSensor(key="cabin_temp", translation_key="cabin_temp", device_class=SensorDeviceClass.TEMPERATURE,
              native_unit_of_measurement=UnitOfTemperature.CELSIUS,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: s.cabin_temp_c),
    GacSensor(key="outside_temp", translation_key="outside_temp", device_class=SensorDeviceClass.TEMPERATURE,
              native_unit_of_measurement=UnitOfTemperature.CELSIUS,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: getattr(s, "outside_temp_c", None)),
    # The entity applies the parked/moving tracking choices to the position.
    GacSensor(key="gps_coordinates", translation_key="gps_coordinates", icon="mdi:map-marker",
              entity_category=None, value=lambda s: gps_coordinates(s.latitude, s.longitude)),
    GacSensor(key="ac_fan_strength", translation_key="ac_fan_strength", icon="mdi:fan",
              entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: getattr(s, "ac_fan_strength", None)),
    GacSensor(key="aux_voltage", translation_key="aux_voltage", device_class=SensorDeviceClass.VOLTAGE,
              native_unit_of_measurement=UnitOfElectricPotential.VOLT,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: s.aux_voltage),
    GacSensor(key="battery_temp", translation_key="battery_temp", device_class=SensorDeviceClass.TEMPERATURE,
              native_unit_of_measurement=UnitOfTemperature.CELSIUS,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: getattr(s, "battery_temp_c", None)),
    # The average of the drive under way, else the last one (the screen's Trip, within a few tenths).
    GacSensor(key="trip_consumption", translation_key="trip_consumption", device_class=SensorDeviceClass.ENERGY_DISTANCE,
              native_unit_of_measurement=UnitOfEnergyDistance.KILO_WATT_HOUR_PER_100_KM, suggested_display_precision=1,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: getattr(s, "trip_consumption_kwh_100km", None)),
    GacSensor(key="charge_time", translation_key="charge_time", device_class=SensorDeviceClass.DURATION,
              native_unit_of_measurement=UnitOfTime.MINUTES,
              value=lambda s: s.estimated_charge_minutes),
    GacSensor(key="charge_current", translation_key="charge_current",
              device_class=SensorDeviceClass.CURRENT,
              native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: s.charge_current_a),
    GacSensor(key="charge_power", translation_key="charge_power", device_class=SensorDeviceClass.POWER,
              native_unit_of_measurement=UnitOfPower.KILO_WATT, state_class=SensorStateClass.MEASUREMENT,
              value=lambda s: s.charge_power_kw),
    GacSensor(key="charge_voltage", translation_key="charge_voltage", device_class=SensorDeviceClass.VOLTAGE,
              native_unit_of_measurement=UnitOfElectricPotential.VOLT, state_class=SensorStateClass.MEASUREMENT,
              value=lambda s: s.charge_voltage_v),
    GacSensor(key="pm25", translation_key="pm25", device_class=SensorDeviceClass.PM25,
              native_unit_of_measurement=PM25_UNIT,
              state_class=SensorStateClass.MEASUREMENT, value=lambda s: s.pm25),
    GacSensor(key="last_report", translation_key="last_report", device_class=SensorDeviceClass.TIMESTAMP,
              entity_category=EntityCategory.DIAGNOSTIC,
              value=lambda s: datetime.fromtimestamp(s.updated_ms / 1000, tz=UTC) if s.updated_ms else None),
    # The reservation window as the car's service reports it. Its clock does not
    # necessarily match local time, so these are off by default.
    GacSensor(key="charge_window_start", translation_key="charge_window_start", icon="mdi:clock-start",
              entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
              value=lambda s: s.charge_window_start),
    GacSensor(key="charge_window_stop", translation_key="charge_window_stop", icon="mdi:clock-end",
              entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
              value=lambda s: s.charge_window_stop),
)


# Only on cars that report a fridge / warmer box.
FRIDGE_SENSORS: tuple[GacSensor, ...] = (
    # A setting made in the car, not a reading.
    GacSensor(key="fridge_keep_mode", translation_key="fridge_keep_mode", icon="mdi:fridge-alert-outline",
              device_class=SensorDeviceClass.ENUM, options=["timed", "unlimited"],
              entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: s.fridge_keep_mode),
    GacSensor(key="fridge_time_left", translation_key="fridge_time_left", icon="mdi:timer-sand",
              device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.MINUTES,
              value=lambda s: s.fridge_keep_minutes),
)


def _tyre_sensors() -> tuple[GacSensor, ...]:
    out: list[GacSensor] = []
    for i in range(4):
        out.append(GacSensor(
            key=f"tyre_{i + 1}_pressure", translation_key=f"tyre_{i + 1}_pressure",
            device_class=SensorDeviceClass.PRESSURE, native_unit_of_measurement=UnitOfPressure.KPA,
            state_class=SensorStateClass.MEASUREMENT,
            value=lambda s, i=i: s.tyres[i].pressure_kpa if i < len(s.tyres) else None,
        ))
        out.append(GacSensor(
            key=f"tyre_{i + 1}_temp", translation_key=f"tyre_{i + 1}_temp",
            device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            value=lambda s, i=i: s.tyres[i].temperature_c if i < len(s.tyres) else None,
        ))
    return tuple(out)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    # Integration health is available for every vehicle, including before any
    # optional equipment has been detected or when cloud updates fail.
    add_entities(GacActivitySensor(coordinator, description) for description in ACTIVITY_SENSORS)
    add_configured_entities(
        entry, add_entities, "sensor",
        (GacSensorEntity(coordinator, d) for d in (*SENSORS, *_tyre_sensors())),
    )
    fridge.async_add_when_fitted(
        entry, coordinator, add_entities, lambda: [GacSensorEntity(coordinator, d) for d in FRIDGE_SENSORS], platform="sensor")
    alerts = getattr(entry.runtime_data, "alerts", None)
    if alerts is not None and alerts.enabled:
        add_entities([GacLastAlertSensor(coordinator, alerts)])
    add_entities([GacEntityChoicesSensor(coordinator)])


class GacSensorEntity(GacEntity, SensorEntity):
    entity_description: GacSensor

    def __init__(self, coordinator, description: GacSensor) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        if self.status is None:
            return None
        if self.entity_description.key == "gps_coordinates":
            return gps_coordinates(*self._position)
        return self.entity_description.value(self.status)

    @property
    def _position(self) -> tuple[float | None, float | None]:
        return shown_position(self.status, self.coordinator.config_entry.options)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "charge_schedule":
            return schedule_attributes(self.status)
        if self.entity_description.key == "gps_coordinates":
            latitude, longitude = self._position
            return {"latitude": latitude, "longitude": longitude}
        return None


LAST_ALERT_STATES = ("no_alerts", "not_read_yet", "read_failed", "signed_out")


class GacLastAlertSensor(GacEntity, SensorEntity):
    """The newest alert in GAC's alert list; Signed out once the account session has ended."""

    _attr_translation_key = "last_gac_alert"
    _attr_icon = "mdi:car-info"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [*ALERT_KEYS, *LAST_ALERT_STATES]

    def __init__(self, coordinator, alerts) -> None:
        super().__init__(coordinator, "last_gac_alert")
        self._alerts = alerts

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_ACCOUNT_ALERTS_UPDATED.format(vin=self.coordinator.vin), self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return True       # its states say why there is no alert

    @property
    def native_value(self) -> str | None:
        state, latest = self._alerts.state, self._alerts.latest
        if state == "signed_out":
            return "signed_out"          # alerts have stopped, whatever the last one was
        if latest is not None:
            return latest.key
        return {"ok": "no_alerts", "error": "read_failed"}.get(state, "not_read_yet")

    @property
    def extra_state_attributes(self) -> dict:
        latest = self._alerts.latest
        last_read = self._alerts.last_read
        return {"account_state": self._alerts.state, "last_read": last_read.isoformat() if last_read else None,
                "last_error": self._alerts.last_error,
                **(alert_attributes(latest) if latest is not None else {})}


class GacActivitySensor(GacEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, description: GacActivityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        return True  # A failed cloud request must not hide the explanation.

    @property
    def native_value(self):
        return self.entity_description.value(self.coordinator)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "last_command":
            return self.coordinator.commands.attributes()
        if self.entity_description.key == "data_freshness":
            age = self.coordinator.report_age
            return {"report_age_seconds": round(age) if age is not None else None,
                    "stale_after_seconds": self.coordinator.stale_after}
        if self.entity_description.key == "polling_status":
            return {"last_attempt": self.coordinator.last_refresh_attempt,
                    "retry_not_before": self.coordinator.retry_not_before,
                    "last_error_reason": self.coordinator.last_refresh_error,
                    "last_error_time": self.coordinator.last_refresh_error_at}
        return None


class GacEntityChoicesSensor(GacEntity, SensorEntity):
    """How many entities are always shown or omitted by choice; the attributes list them all.

    Change one with the gac_connect.set_entity_visibility action (it reloads the integration).
    """

    _attr_translation_key = "entity_choices"
    _attr_icon = "mdi:eye-settings-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _unrecorded_attributes = frozenset({"entities"})

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "entity_choices")

    @property
    def available(self) -> bool:
        return True

    def _choices(self) -> tuple[list[str], list[str]]:
        options = self.coordinator.config_entry.options
        return sorted(options.get(CONF_ENABLE_ENTITIES, ())), sorted(options.get(CONF_OMIT_ENTITIES, ()))

    @property
    def native_value(self) -> int:
        always, omit = self._choices()
        return len(always) + len(omit)

    @property
    def extra_state_attributes(self) -> dict:
        always, omit = self._choices()
        return {"always_show": always, "omit": omit, "entities": dict(OMIT_OPTIONS)}
