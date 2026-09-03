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
CONF_ENABLE_TRACKER: Final = "enable_tracker"

DEFAULT_SCAN_INTERVAL: Final = 300     # seconds
MIN_SCAN_INTERVAL: Final = 60
DEFAULT_ENABLE_TRACKER: Final = False

PLATFORMS: Final = ["sensor", "binary_sensor", "button", "switch", "device_tracker"]
