"""Constants for the GAC Connect integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "gac_connect"

# config entry data
CONF_REGION: Final = "region"
CONF_MOBILE: Final = "mobile"
CONF_VIN: Final = "vin"
CONF_SESSION: Final = "session"
CONF_MODEL: Final = "model"

# options
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_QUIET_START: Final = "quiet_start"
CONF_QUIET_END: Final = "quiet_end"
CONF_ENABLE_TRACKER: Final = "enable_tracker"   # any location tracking; kept for older entries
CONF_TRACK_PARKED: Final = "track_parked"
CONF_TRACK_MOVING: Final = "track_moving"
CONF_ENABLE_FRIDGE: Final = "enable_fridge"   # retired in 1.4; read only by the entry migration
CONF_AC_MINUTES: Final = "ac_minutes"   # retired setting; seeds the Pre-conditioning run time
CONF_PICTURE: Final = "picture"        # retired option; removed from stored options on save
CONF_OMIT_ENTITIES: Final = "omit_entities"
CONF_PROFILE: Final = "profile"   # removed setting; read only to migrate older entries
CONF_ENABLE_ENTITIES: Final = "enable_entities"
# Retain the stored key so existing unlock preferences survive the API migration.
CONF_EXPERIMENTAL_PINLESS_UNLOCK: Final = "experimental_pinless_unlock"
CONF_ALLOW_PLAINTEXT_PUSH: Final = "allow_plaintext_push"
CONF_ALLOW_VEHICLE_SHUTDOWN: Final = "allow_vehicle_shutdown"
CONF_ALLOW_CHARGER_UNLOCK: Final = "allow_charger_unlock"
CONF_ALLOW_ACCOUNT_ALERTS: Final = "allow_account_alerts"
CONF_LOAD_CARDS: Final = "load_cards"   # load the dashboard cards into Home Assistant's pages; off: nothing is added
CONF_DASHBOARD_CARDS: Final = "dashboard_cards"   # the cards on the car's generated dashboard; none: no dashboard
DASHBOARD_CARDS: Final = ("vehicle", "charging", "climate", "location", "activity", "settings")
VEHICLE_SHUTDOWN_COMMANDS: Final = frozenset({"vehicle-power-off", "power-off", "powerkeep-stop"})

DEFAULT_SCAN_INTERVAL: Final = 300     # seconds
MIN_SCAN_INTERVAL: Final = 60
DEFAULT_ENABLE_TRACKER: Final = False
DEFAULT_AC_MINUTES: Final = 30       # minutes an A/C run lasts

SIGNAL_COMMAND_RESULT: Final = "gac_connect_command_result_{vin}"
EVENT_COMMAND_RESULT: Final = "gac_connect_command_result"

PLATFORMS: Final = [
    "sensor", "binary_sensor", "button", "switch", "device_tracker",
    "climate", "lock", "cover", "select", "number", "event", "time",
]
