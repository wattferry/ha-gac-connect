"""Binary sensors: vehicle power, charging, openings, locks and connectivity."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from gac_connect.models import VehicleStatus

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GacConfigEntry
from .const import CONF_MODEL
from .entity import GacEntity
from .entity_filter import add_configured_entities
from .lock_state import doors_unlocked
from .seats import reported_seat, ventilation_state


POSITIONS = ("front_left", "front_right", "rear_left", "rear_right")
# Turn indicators covers the hazard lights too: the car reports them the same way.
LIGHT_SENSORS = {"high_beam": "high_beam_on", "rear_fog_light": "rear_fog_on", "turn_signal": "turn_signal_on",
                 "brake_lights": "brake_lights_on"}


@dataclass(frozen=True, kw_only=True)
class GacBinary(BinarySensorEntityDescription):
    value: Callable[[VehicleStatus], bool | None]


BINARY_SENSORS: tuple[GacBinary, ...] = (
    GacBinary(key="vehicle_power", translation_key="vehicle_power", icon="mdi:car-electric",
              value=lambda s: getattr(s, "power_on", None)),
    GacBinary(key="plugged", translation_key="plugged", device_class=BinarySensorDeviceClass.PLUG,
              value=lambda s: s.plugged_in),
    GacBinary(key="charging", translation_key="charging", device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
              value=lambda s: s.charging),
    # HA lock/opening semantics: on = unlocked / open.
    GacBinary(key="locked", translation_key="locked", device_class=BinarySensorDeviceClass.LOCK,
              value=doors_unlocked),
    GacBinary(key="door_open", translation_key="door_open", device_class=BinarySensorDeviceClass.DOOR,
              value=lambda s: s.door_open),
    GacBinary(key="window_open", translation_key="window_open", device_class=BinarySensorDeviceClass.WINDOW,
              value=lambda s: s.window_open),
    # Each door and window by position, shown once the car reports it.
    *(GacBinary(key=f"{position}_{kind}", translation_key=f"{position}_{kind}", device_class=device_class,
                value=lambda s, field=f"{position}_{kind}_open": getattr(s, field, None))
      for kind, device_class in (("door", BinarySensorDeviceClass.DOOR), ("window", BinarySensorDeviceClass.WINDOW))
      for position in POSITIONS),
    GacBinary(key="hatch_open", translation_key="hatch_open", device_class=BinarySensorDeviceClass.OPENING,
              value=lambda s: s.hatch_open),
    GacBinary(key="hood_open", translation_key="hood_open", device_class=BinarySensorDeviceClass.OPENING,
              value=lambda s: getattr(s, "hood_open", None)),
    GacBinary(key="headlights", translation_key="headlights", device_class=BinarySensorDeviceClass.LIGHT,
              value=lambda s: getattr(s, "headlights_on", None)),
    # Shown once the car has reported each on: an off light reads the same as a missing one.
    *(GacBinary(key=key, translation_key=key, device_class=BinarySensorDeviceClass.LIGHT,
                value=lambda s, field=field: getattr(s, field, None))
      for key, field in LIGHT_SENSORS.items()),
    # The app's Brake fluid check: on (a problem) while the car reports a brake alarm.
    GacBinary(key="brake_fluid", translation_key="brake_fluid", device_class=BinarySensorDeviceClass.PROBLEM,
              value=lambda s: getattr(s, "brake_fluid_low", None)),
    GacBinary(key="online", translation_key="online", device_class=BinarySensorDeviceClass.CONNECTIVITY,
              entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: s.online),
    GacBinary(key="charger_locked", translation_key="charger_locked", device_class=BinarySensorDeviceClass.LOCK,
              entity_category=EntityCategory.DIAGNOSTIC,
              value=lambda s: (not s.charger_locked) if s.charger_locked is not None else None),
    GacBinary(key="ac_auto", translation_key="ac_auto", icon="mdi:fan-auto",
              entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: getattr(s, "ac_auto_on", None)),
    GacBinary(key="ac_compressor", translation_key="ac_compressor", icon="mdi:air-conditioner",
              entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: getattr(s, "ac_compressor_on", None)),
    GacBinary(key="anti_theft", translation_key="anti_theft", icon="mdi:shield-car",
              value=lambda s: getattr(s, "anti_theft_on", None)),
    *(GacBinary(key=f"seat_{i}_ventilation", translation_key=f"seat_{i}_ventilation",
               icon="mdi:car-seat-cooler", entity_category=EntityCategory.DIAGNOSTIC,
               value=lambda s, i=i: ventilation_state(s, i))
      for i in range(1, 5)),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: GacConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    add_configured_entities(entry, add_entities, "binary_sensor",
                            (GacBinaryEntity(coordinator, d) for d in BINARY_SENSORS))


class GacBinaryEntity(GacEntity, BinarySensorEntity):
    entity_description: GacBinary

    def __init__(self, coordinator, description: GacBinary) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if self.status is None:
            return None
        if self.entity_description.key == "locked":
            return doors_unlocked(self.status, self.coordinator.config_entry.data.get(CONF_MODEL))
        return self.entity_description.value(self.status)

    @property
    def extra_state_attributes(self):
        key = self.entity_description.key
        if key == "vehicle_power" and self.status is not None:
            return {"power_mode": getattr(self.status, "power_mode", None)}
        if key.startswith("seat_") and self.status:
            seat_id = int(key.split("_")[1])
            if (seat := reported_seat(self.status, seat_id)) is not None:
                return {"seat_id": seat.position, "reported_wind_strength": seat.ventilation_strength,
                        "reported_enable_wind": getattr(seat, "ventilation_enable_code", None),
                        "reported_heating_strength": seat.heating_strength,
                        "reported_temperature_mode": seat.temperature_mode}
        return None
