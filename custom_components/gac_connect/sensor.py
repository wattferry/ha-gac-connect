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
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .entity import GacEntity


@dataclass(frozen=True, kw_only=True)
class GacSensor(SensorEntityDescription):
    value: Callable[[VehicleStatus], float | int | None]


SENSORS: tuple[GacSensor, ...] = (
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
    GacSensor(key="aux_voltage", translation_key="aux_voltage", device_class=SensorDeviceClass.VOLTAGE,
              native_unit_of_measurement=UnitOfElectricPotential.VOLT,
              state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC,
              value=lambda s: s.aux_voltage),
    GacSensor(key="charge_time", translation_key="charge_time",
              native_unit_of_measurement=UnitOfTime.MINUTES,
              value=lambda s: s.estimated_charge_minutes),
    GacSensor(key="charge_current", translation_key="charge_current",
              device_class=SensorDeviceClass.CURRENT,
              native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
              state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC,
              value=lambda s: s.charge_current_a),
    GacSensor(key="pm25", translation_key="pm25", device_class=SensorDeviceClass.PM25,
              native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
              state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC,
              value=lambda s: s.pm25),
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
            state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC,
            value=lambda s, i=i: s.tyres[i].temperature_c if i < len(s.tyres) else None,
        ))
    return tuple(out)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    add_entities(GacSensorEntity(coordinator, d) for d in (*SENSORS, *_tyre_sensors()))


class GacSensorEntity(GacEntity, SensorEntity):
    entity_description: GacSensor

    def __init__(self, coordinator, description: GacSensor) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        if self.status is None:
            return None
        return self.entity_description.value(self.status)
