"""Persist passive evidence and correlate outcomes of user-requested commands."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import logging

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from gac_connect import GacError
from gac_connect.commands import CYCLING_FRESH_AIR, CYCLING_RECIRCULATE
from .api import Capabilities, Support, doors_locked, equipment_from_capabilities, ranges_from_capabilities
from .entity_filter import LOCATION_ENTITIES
from .location import location_enabled
from .const import (
    CONF_ENABLE_ENTITIES, CONF_MODEL,
    CONF_ALLOW_CHARGER_UNLOCK,
    CONF_ALLOW_VEHICLE_SHUTDOWN,
    CONF_OMIT_ENTITIES, CONF_REGION, CONF_VIN, DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# HA entity names map to library evidence. Hardware readings may reveal a
# control, but its individual commands remain unconfirmed until a real result.
ENTITY_FEATURES = {
    "sensor:charge_schedule": "charge_control",
    "sensor:soc": "soc", "sensor:range": "range_km", "sensor:odometer": "odometer_km",
    "sensor:cabin_temp": "cabin_temp_c", "sensor:aux_voltage": "aux_voltage", "sensor:battery_temp": "battery_temp_c",
    "sensor:trip_consumption": "trip_consumption_kwh_100km", "sensor:pm25": "pm25",
    "sensor:outside_temp": "outside_temp_c", "sensor:ac_fan_strength": "ac_fan_strength",
    "sensor:gps_coordinates": "location",
    "sensor:charge_time": "estimated_charge_minutes", "sensor:charge_current": "charge_current_a",
    "sensor:charge_voltage": "charge_voltage_v", "sensor:charge_power": "charge_power_kw",
    "sensor:last_report": "updated_ms", "sensor:charge_window_start": "charge_window_start",
    "sensor:charge_window_stop": "charge_window_stop",
    **{f"sensor:tyre_{i}_{kind}": f"tyre_{i}_{field}" for i in range(1, 5)
       for kind, field in (("pressure", "pressure"), ("temp", "temperature"))},
    "sensor:fridge_keep_mode": "fridge_keep_mode", "sensor:fridge_time_left": "fridge_keep_minutes",
    "binary_sensor:plugged": "plugged_in", "binary_sensor:charging": "charging",
    "binary_sensor:locked": "locked", "binary_sensor:door_open": "door_open",
    "binary_sensor:window_open": "window_open", "binary_sensor:hatch_open": "hatch_open",
    "binary_sensor:hood_open": "hood_open", "binary_sensor:headlights": "headlights_on", "binary_sensor:brake_fluid": "brake_fluid_low",
    **{f"binary_sensor:{position}_{kind}": f"{position}_{kind}_open"
       for position in ("front_left", "front_right", "rear_left", "rear_right") for kind in ("door", "window")},
    "binary_sensor:high_beam": "high_beam_on", "binary_sensor:rear_fog_light": "rear_fog_on",
    "binary_sensor:brake_lights": "brake_lights_on",
    "binary_sensor:turn_signal": "turn_signal_on",
    "binary_sensor:online": "online", "binary_sensor:charger_locked": "charger_locked",
    "binary_sensor:vehicle_power": "power_on",
    "binary_sensor:ac_auto": "ac_auto_on", "binary_sensor:ac_compressor": "ac_compressor_on",
    "binary_sensor:anti_theft": "anti_theft_on",
    **{f"binary_sensor:seat_{i}_ventilation": f"seat_{i}_ventilation_on" for i in range(1, 5)},
    "switch:steering_heat": "steering_heat", "switch:lights": "lights", "switch:ventilation": "ventilation",
    "switch:recirculation": "climate", "switch:precondition_battery": "battery_precondition",
    "switch:sterilisation": "sterilisation",
    **{f"select:seat_{i}_ventilation": f"seat_{i}_ventilation" for i in (1, 2)},
    "switch:charge_switch": "charge_control", "switch:climate_power": "climate", "switch:fridge": "fridge",
    "cover:windows": "windows", "cover:sunroof": "sunroof", "cover:tailgate": "tailgate",
    "climate:climate": "climate", "lock:doors": "doors",
    "button:horn": "horn",
    "button:vehicle_power_off": "vehicle_power_control", "button:charger_unlock": "charger_unlock",
    "button:charge_now": "charge_control", "select:fridge_mode": "fridge", "number:fridge_temperature": "fridge",
    "number:ac_minutes": "climate",
    "device_tracker:location": "location",
}
FRIDGE_ENTITIES = frozenset(key for key in ENTITY_FEATURES if "fridge" in key)
# Entities that send these codes; hidden when the car's capability list leaves one out.
CODES_SENT = {
    "switch:recirculation": ("cycling_modes", (CYCLING_RECIRCULATE, CYCLING_FRESH_AIR)),
    "switch:precondition_battery": ("battery_precondition_modes", (0, 1)),   # cancel, start
}


# Raised when what is read from the capability list changes, so a list saved before is read once more.
RANGES_VERSION = 3


def store_key(entry_id: str) -> str:
    return f"{DOMAIN}.capabilities.{entry_id}"


def _restore_ranges(data) -> dict[str, tuple[int, ...]]:
    if not isinstance(data, dict):
        return {}
    return {key: tuple(values) for key, values in data.items() if isinstance(key, str) and isinstance(values, list)
            and all(type(value) is int for value in values)}


def remote_choices(coordinator, name: str, default: tuple[int, ...]) -> tuple[int, ...]:
    """What the car's capability list offers for a remote setting, or ``default`` until it is read."""
    manager = getattr(coordinator, "capabilities", None)
    return manager.ranges.get(name, default) if manager is not None else default


class CapabilityManager:
    def __init__(self, hass, entry) -> None:
        self.entry = entry
        self.detector = Capabilities(entry.data.get(CONF_MODEL))
        self._store = Store(hass, 1, store_key(entry.entry_id))
        identity = f"{entry.data.get(CONF_REGION)}:{entry.data[CONF_VIN]}"
        self._vehicle_key = hashlib.sha256(identity.encode()).hexdigest()
        self._dirty = False
        self.capability_list_read = False   # the car's own capability list has been read
        self.ranges: dict[str, tuple[int, ...]] = {}   # its remote fan, outlet and seat choices

    async def async_load(self) -> None:
        try:
            data = await self._store.async_load()
        except Exception:
            _LOGGER.warning("Could not read detected equipment; learning again from vehicle reports")
            return
        if isinstance(data, dict) and data.get("vehicle_key") == self._vehicle_key:
            self.detector.restore(data.get("evidence"))
            self.capability_list_read = (data.get("capability_list_read") is True
                                         and data.get("ranges_version") == RANGES_VERSION)
            self.ranges = _restore_ranges(data.get("ranges"))

    def _snapshot(self) -> dict:
        return {"vehicle_key": self._vehicle_key, "evidence": self.detector.export_state(),
                "capability_list_read": self.capability_list_read,
                "ranges": {key: list(values) for key, values in self.ranges.items()},
                "ranges_version": RANGES_VERSION}

    async def async_read_capability_list_once(self, client, vin: str) -> None:
        """Read the list at the first start; reports decide meanwhile if it cannot be read."""
        if self.capability_list_read:
            return
        try:
            await self.async_read_capability_list(client, vin)
        except (GacError, HomeAssistantError) as err:
            _LOGGER.info("Could not read the car's capability list; detecting equipment from its reports: %s", err)

    async def async_read_capability_list(self, client, vin: str) -> int:
        """Read what the car offers remotely and let it decide what is shown; saved at once.

        Replaces any earlier list. Raises HomeAssistantError for an unusable answer;
        the service's own errors propagate. Returns how many features it settled.
        """
        data = await client.get_control_capabilities(vin)
        flags = equipment_from_capabilities(data)
        if not flags:
            raise HomeAssistantError("The car's capability list was empty or incomplete")
        self.detector.observe_equipment(flags, replace=True)
        self.ranges = ranges_from_capabilities(data)
        self.capability_list_read = True
        self._dirty = False
        await self._store.async_save(self._snapshot())
        return len(flags)

    def _changed(self) -> None:
        self._dirty = True
        self._store.async_delay_save(self._snapshot, 10)

    def observe(self, status) -> None:
        # Use the same model-aware interpretation as the lock entities (UT
        # rear-door sentinels), without changing the coordinator's report.
        if status.locked is None and (locked := doors_locked(status, self.entry.data.get(CONF_MODEL))) is not None:
            status = replace(status, locked=locked)
        if self.detector.observe(status):
            self._changed()

    def includes(self, entity_key: str, *, user_choices: bool = True) -> bool:
        """Whether an entity is shown; without ``user_choices``, as if Omit and Always show were empty."""
        if entity_key == "button:vehicle_power_off" and self.entry.options.get(CONF_ALLOW_VEHICLE_SHUTDOWN) is not True:
            return False
        if entity_key == "button:charger_unlock" and self.entry.options.get(CONF_ALLOW_CHARGER_UNLOCK) is not True:
            return False
        if entity_key in LOCATION_ENTITIES and not location_enabled(self.entry.options):
            return False
        if user_choices and entity_key in self.entry.options.get(CONF_OMIT_ENTITIES, ()):
            return False
        if entity_key == "button:refresh":
            return True
        if entity_key == "button:vehicle_power_off":
            return True  # the separate shutdown setting is an explicit opt-in
        if user_choices and entity_key in self.entry.options.get(CONF_ENABLE_ENTITIES, ()):
            return True
        feature = ENTITY_FEATURES.get(entity_key)
        return (feature is not None and self.detector.feature(feature).state is Support.SUPPORTED
                and self._codes_offered(entity_key))

    def _codes_offered(self, entity_key: str) -> bool:
        """False when the car's capability list leaves out a code the entity sends."""
        name, codes = CODES_SENT.get(entity_key, (None, ()))
        return name not in self.ranges or set(codes) <= set(self.ranges[name])

    def confirm_command(self, command: str) -> bool:
        """Called only after the shared tracker correlates a successful result."""
        if self.detector.confirm_command(command):
            self._changed()
            return True
        return False

    async def async_close(self) -> None:
        if self._dirty:
            try:
                await self._store.async_save(self._snapshot())
                self._dirty = False
            except Exception:
                _LOGGER.warning("Could not save detected equipment; it will be learned again next time")

    def diagnostics(self) -> dict:
        data = self.detector.diagnostics()
        data["entities"] = {key: {"shown": self.includes(key), "override": (
            "disable" if key in self.entry.options.get(CONF_OMIT_ENTITIES, ()) else
            "enable" if key in self.entry.options.get(CONF_ENABLE_ENTITIES, ()) else "automatic")}
            for key in ENTITY_FEATURES}
        data["ranges"] = {key: list(values) for key, values in self.ranges.items()}
        return data

    def decision(self, entity_key: str, *, user_choices: bool = True) -> tuple[bool, str]:
        """Whether an entity is shown, and the short reason, overrides first."""
        options = self.entry.options
        if entity_key == "button:vehicle_power_off" and options.get(CONF_ALLOW_VEHICLE_SHUTDOWN) is not True:
            return False, "remote shutdown is not allowed in Vehicle settings"
        if entity_key == "button:charger_unlock" and options.get(CONF_ALLOW_CHARGER_UNLOCK) is not True:
            return False, "remote connector unlock is not allowed in Vehicle settings"
        if user_choices and entity_key in options.get(CONF_OMIT_ENTITIES, ()):
            return False, "your Omit choice"
        if entity_key in LOCATION_ENTITIES and not location_enabled(options):
            return False, "location tracking is off"
        if entity_key == "button:vehicle_power_off":
            return True, "remote shutdown is allowed in Vehicle settings"
        if user_choices and entity_key in options.get(CONF_ENABLE_ENTITIES, ()):
            return True, "your Always show choice"
        evidence = self.detector.feature(ENTITY_FEATURES.get(entity_key, ""))
        if evidence.state is Support.SUPPORTED and not self._codes_offered(entity_key):
            return False, "the car's capability list does not offer it remotely"
        shown = self.includes(entity_key, user_choices=user_choices)
        if evidence.source == "vehicle_equipment":
            return shown, ("the car's capability list offers it" if shown
                           else "the car's capability list does not offer it remotely")
        if evidence.source == "observed_telemetry":
            return shown, "seen in the car's reports"
        if evidence.source == "confirmed_command":
            return shown, "a command to it succeeded"
        if evidence.source == "model_default":
            return shown, "not fitted to this model"
        return shown, "not seen in the car's reports yet"

    def explanation(self, entity_key: str) -> str:
        shown, reason = self.decision(entity_key)
        return f"{'Shown' if shown else 'Hidden'}: {reason}."
