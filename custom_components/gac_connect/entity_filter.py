"""Apply detected equipment and explicit entity choices."""
from __future__ import annotations

from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_VIN, DOMAIN

# Option IDs use the platform and existing unique-id suffix so an option can be
# applied to an entity that was already registered before this setting existed.
ENTITY_CHOICES: dict[str, dict[str, str]] = {
    "sensor": {
        "charge_schedule": "Charging schedule",
        "soc": "Battery", "range": "Range", "odometer": "Odometer",
        "cabin_temp": "Cabin temperature", "aux_voltage": "12V battery", "battery_temp": "Battery temperature",
        "trip_consumption": "Trip consumption",
        "outside_temp": "Outside temperature", "ac_fan_strength": "Cabin fan strength",
        "gps_coordinates": "GPS coordinates",
        "charge_time": "Estimated charge time", "charge_current": "Charge current",
        "charge_power": "Charge power", "charge_voltage": "Charge voltage",
        "pm25": "Cabin PM2.5", "last_report": "Last report",
        "charge_window_start": "Reported charge window start", "charge_window_stop": "Reported charge window stop",
        "fridge_keep_mode": "Fridge after leaving", "fridge_time_left": "Fridge time left",
        **{f"tyre_{i}_{kind}": f"Tyre {i} {label}"
           for i in range(1, 5)
           for kind, label in (("pressure", "pressure"), ("temp", "temperature"))},
    },
    "binary_sensor": {
        "vehicle_power": "Vehicle power",
        "plugged": "Plugged in", "charging": "Charging", "locked": "Lock state",
        "door_open": "Door state", "window_open": "Window state",
        **{f"{position}_{kind}": f"{label} {kind}" for position, label in (
            ("front_left", "Front left"), ("front_right", "Front right"), ("rear_left", "Rear left"),
            ("rear_right", "Rear right")) for kind in ("door", "window")},
        "high_beam": "High beams", "rear_fog_light": "Rear fog light", "turn_signal": "Turn indicators",
        "brake_lights": "Brake lights",
        "hatch_open": "Boot state", "hood_open": "Hood state", "headlights": "Headlights", "brake_fluid": "Brake fluid", "online": "Online", "charger_locked": "Charger lock",
        "ac_auto": "A/C auto mode", "ac_compressor": "A/C compressor", "anti_theft": "Anti-theft enabled",
        **{f"seat_{i}_ventilation": f"{name} seat ventilation state" for i, name in
           enumerate(("Driver", "Front passenger", "Rear left", "Rear right"), start=1)},
    },
    "button": {
        "vehicle_power_off": "Turn vehicle off",
        "charge_now": "Charge now",
        "charger_unlock": "Unlock charging connector",
        "horn": "Sound horn",
    },
    "switch": {
        "charge_switch": "Scheduled charging", "climate_power": "A/C",
        "steering_heat": "Steering wheel heat", "lights": "Flash lights",
        "ventilation": "Ventilation", "recirculation": "Recirculation",
        "precondition_battery": "Smart battery temp", "sterilisation": "Sterilisation",
        "fridge": "Fridge",
    },
    "cover": {"windows": "Windows", "sunroof": "Sunroof", "tailgate": "Boot"},
    "climate": {"climate": "Climate"},
    "lock": {"doors": "Doors"},
    "select": {
        "seat_1_ventilation": "Driver seat ventilation",
        "seat_2_ventilation": "Front passenger seat ventilation",
        "fridge_mode": "Fridge mode",
    },
    "number": {"ac_minutes": "Pre-conditioning run time", "fridge_temperature": "Fridge temperature"},
    "device_tracker": {"location": "Location"},
}

OMIT_OPTIONS: dict[str, str] = {
    f"{domain}:{key}": f"{domain.replace('_', ' ').title()} · {label}"
    for domain in ENTITY_CHOICES
    for key, label in ENTITY_CHOICES[domain].items()
}
LOCATION_ENTITIES = frozenset({"device_tracker:location", "sensor:gps_coordinates"})

def add_configured_entities(
    entry: ConfigEntry, add_entities: AddEntitiesCallback, domain: str, entities: Iterable
) -> None:
    """Add each entity once detection and the entity choices include it."""
    coordinator = entry.runtime_data.coordinator
    manager = coordinator.capabilities
    candidates = list(entities)
    added: set[str] = set()
    prefix = f"{entry.data[CONF_VIN]}_"

    def add_detected() -> None:
        ready = []
        for entity in candidates:
            key = f"{domain}:{entity.unique_id.removeprefix(prefix)}"
            if key not in added and manager.includes(key):
                added.add(key)
                ready.append(entity)
        if ready:
            apply_registry_choices(coordinator.hass, entry)
            add_entities(ready)

    entry.async_on_unload(coordinator.async_add_listener(add_detected))
    add_detected()


def apply_registry_choices(hass, entry: ConfigEntry) -> None:
    """Disable registered entities that detection or the entity choices exclude, and re-enable the rest."""
    registry = er.async_get(hass)
    runtime = getattr(entry, "runtime_data", None)
    manager = getattr(getattr(runtime, "coordinator", None), "capabilities", None)
    if manager is None:
        return
    for option in OMIT_OPTIONS:
        domain, key = option.split(":", 1)
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{entry.data[CONF_VIN]}_{key}")
        if entity_id is None:
            continue
        current = registry.async_get(entity_id)
        excluded = not manager.includes(option)
        if excluded and current.disabled_by is None:
            registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
        elif not excluded and current.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(entity_id, disabled_by=None)
