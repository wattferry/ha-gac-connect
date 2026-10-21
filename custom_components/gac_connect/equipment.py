"""Which entities are shown and why, without telemetry or identifiers."""
from collections import Counter
from functools import partial

from . import fridge
from .cabin import DEFAULT_BLOWING_MODES, DEFAULT_FAN_SPEEDS, DEFAULT_MINUTES_RANGE, DEFAULT_TEMPERATURE_RANGE
from .capabilities import remote_choices
from .climate import AIRFLOW_NAMES
from .const import CONF_ENABLE_ENTITIES, CONF_OMIT_ENTITIES
from .entity_filter import ENTITY_CHOICES
from .select import DEFAULT_SEAT_LEVELS, SEAT_LEVEL_NAMES

# What each entity reports or does, in a few words.
DETAILS: dict[str, str] = {
    "sensor:charge_schedule": "scheduled or whenever plugged in",
    "sensor:soc": "%", "sensor:range": "km", "sensor:odometer": "km",
    "sensor:cabin_temp": "°C", "sensor:outside_temp": "°C", "sensor:aux_voltage": "V", "sensor:battery_temp": "°C",
    "sensor:trip_consumption": "kWh/100 km",
    "sensor:ac_fan_strength": "0–10", "sensor:gps_coordinates": "latitude, longitude",
    "sensor:charge_time": "minutes", "sensor:charge_current": "A", "sensor:charge_power": "kW",
    "sensor:charge_voltage": "V", "sensor:pm25": "µg/m³", "sensor:last_report": "time",
    "sensor:charge_window_start": "HH:MM", "sensor:charge_window_stop": "HH:MM",
    "sensor:fridge_keep_mode": "timed or unlimited", "sensor:fridge_time_left": "minutes",
    **{f"sensor:tyre_{i}_pressure": "kPa" for i in range(1, 5)},
    **{f"sensor:tyre_{i}_temp": "°C" for i in range(1, 5)},
    "binary_sensor:vehicle_power": "on/off", "binary_sensor:plugged": "plugged in/unplugged",
    "binary_sensor:charging": "charging/not charging", "binary_sensor:locked": "locked/unlocked",
    "binary_sensor:door_open": "open/closed", "binary_sensor:window_open": "open/closed",
    "binary_sensor:hatch_open": "open/closed", "binary_sensor:hood_open": "open/closed", "binary_sensor:headlights": "on/off",
    **{f"binary_sensor:{position}_{kind}": "open/closed"
       for position in ("front_left", "front_right", "rear_left", "rear_right") for kind in ("door", "window")},
    **{f"binary_sensor:{key}": "on/off" for key in ("high_beam", "rear_fog_light", "turn_signal", "brake_lights")},
    "binary_sensor:brake_fluid": "normal/low", "binary_sensor:online": "connected/disconnected",
    "binary_sensor:charger_locked": "locked/unlocked", "binary_sensor:ac_auto": "on/off",
    "binary_sensor:ac_compressor": "on/off", "binary_sensor:anti_theft": "armed/disarmed",
    **{f"binary_sensor:seat_{i}_ventilation": "running/off" for i in range(1, 5)},
    "button:vehicle_power_off": "switches the car off", "button:charge_now": "charge when plugged in",
    "button:horn": "sounds the horn", "button:charger_unlock": "releases the charging connector",
    "switch:charge_switch": "on follows the schedule, off charges whenever plugged in", "switch:climate_power": "A/C on/off",
    "switch:steering_heat": "on/off", "switch:lights": "flash on/off", "switch:ventilation": "on/off",
    "switch:recirculation": "on recirculates, off fresh air; while the A/C runs",
    "switch:precondition_battery": "on/off", "switch:sterilisation": "on/off", "switch:fridge": "on/off",
    "cover:windows": "open/close", "cover:sunroof": "open/close", "cover:tailgate": "open/close",
    "lock:doors": "lock; unlock if allowed",
    "device_tracker:location": "home/away and map",
}
# Controls first, then readings.
ORDER = ("climate", "switch", "select", "number", "cover", "lock", "button", "device_tracker", "sensor", "binary_sensor")
ENTITIES = {f"{domain}:{key}": label for domain in ORDER for key, label in ENTITY_CHOICES[domain].items()}


def _span(low: float, high: float) -> str:
    return f"{low:g}–{high:g}" if low >= 0 else f"{low:g} to {high:g}".replace("-", "−")


def _remote_details(coordinator) -> dict[str, str]:
    """Details that follow the car's remote choices, as the entities offer them."""
    choices = partial(remote_choices, coordinator)
    speeds = choices("fan_speeds", DEFAULT_FAN_SPEEDS)
    outlets = [code for code in choices("blowing_modes", DEFAULT_BLOWING_MODES) if code in AIRFLOW_NAMES]
    temperatures = choices("ac_temperature_range", DEFAULT_TEMPERATURE_RANGE) or DEFAULT_TEMPERATURE_RANGE
    climate = ["Off, On, Fan only", f"{_span(*temperatures)} °C"]
    if speeds:
        climate.append(f"fan {speeds[0]}–{speeds[-1]}" if len(speeds) > 1 else f"fan {speeds[0]}")
    if outlets:
        climate.append(f"{len(outlets)} airflow choice{'s' if len(outlets) > 1 else ''}")
    details = {"climate:climate": "; ".join([*climate, "Heating and Cooling presets"])}
    low, high = choices("ac_minutes_range", DEFAULT_MINUTES_RANGE) or DEFAULT_MINUTES_RANGE
    details["number:ac_minutes"] = f"{low}–{high} minutes per remote start"
    for seat in (1, 2):
        levels = choices(f"seat_{seat}_ventilation_levels", DEFAULT_SEAT_LEVELS)
        names = [SEAT_LEVEL_NAMES[level].title() for level in levels if level in SEAT_LEVEL_NAMES]
        details[f"select:seat_{seat}_ventilation"] = ", ".join(["Off", *names])
    modes = fridge.running_modes(coordinator)
    details["select:fridge_mode"] = ", ".join(["Off", *(mode.title() for mode in modes)])
    spans = [_span(*fridge.temperature_range(coordinator, mode)) for mode in modes]
    if spans:
        joined = spans[0] if len(spans) == 1 else f"{', '.join(spans[:-1])} or {spans[-1]}"
        details["number:fridge_temperature"] = f"{joined} °C" + (" by mode" if len(spans) > 1 else "")
    return details


def equipment_summary(entry) -> str:
    runtime = getattr(entry, "runtime_data", None)
    manager = getattr(getattr(runtime, "coordinator", None), "capabilities", None)
    if manager is None:
        return "The vehicle is not loaded. Reconnect it to see its equipment."
    decide = manager.decision
    details = {**DETAILS, **_remote_details(runtime.coordinator)}
    omitted = set(entry.options.get(CONF_OMIT_ENTITIES, ()))
    always = set(entry.options.get(CONF_ENABLE_ENTITIES, ()))
    choices: list[str] = []
    rows: dict[bool, list[tuple[str, str]]] = {True: [], False: []}
    for key, label in ENTITIES.items():
        detail = details.get(key)
        line = f"- {label} ({detail})" if detail else f"- {label}"
        if key in omitted or key in always:
            # What the car's evidence alone would decide, so an override that changes nothing shows.
            automatic, _ = decide(key, user_choices=False)
            if key in omitted:
                choices.append(f"{line}: omitted; " + ("otherwise shown" if automatic else "would be hidden anyway"))
            else:
                choices.append(f"{line}: always shown; " + ("would be shown anyway" if automatic else "otherwise hidden"))
            continue
        shown, reason = decide(key)
        rows[shown].append((line, reason))
    sections = ["**Your choices (Vehicle settings)**\n\n" + "\n".join(choices)] if choices else []
    for shown, items in rows.items():
        if not items:
            continue
        # The most common reason heads the section; any other is given on its line, after the rest.
        main = Counter(reason for _, reason in items).most_common(1)[0][0]
        lines = [line for line, reason in items if reason == main]
        lines += [f"{line} — {reason}" for line, reason in items if reason != main]
        note = ", unless noted" if len(lines) > sum(reason == main for _, reason in items) else ""
        sections.append(f"**{'Shown' if shown else 'Hidden'} ({main}{note})**\n\n" + "\n".join(lines))
    return "\n\n".join(sections)
