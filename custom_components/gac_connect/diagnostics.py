"""Diagnostics with personal data redacted."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import GacConfigEntry
from gac_connect import __version__ as LIBRARY_VERSION
from gac_connect.const import REGIONS
from .const import (
    CONF_ALLOW_ACCOUNT_ALERTS, CONF_ALLOW_CHARGER_UNLOCK, CONF_ALLOW_PLAINTEXT_PUSH, CONF_ENABLE_TRACKER,
    CONF_EXPERIMENTAL_PINLESS_UNLOCK, CONF_OMIT_ENTITIES, CONF_ENABLE_ENTITIES,
    CONF_QUIET_END, CONF_QUIET_START, CONF_SCAN_INTERVAL,
    CONF_REGION, CONF_TRACK_MOVING, CONF_TRACK_PARKED,
)

# URLs can contain passwords, signed query strings or private locations. New
# options must be reviewed before being included in a shareable diagnostic.
SAFE_OPTIONS = {
    CONF_ALLOW_ACCOUNT_ALERTS, CONF_ALLOW_CHARGER_UNLOCK, CONF_ALLOW_PLAINTEXT_PUSH, CONF_ENABLE_TRACKER,
    CONF_TRACK_PARKED, CONF_TRACK_MOVING,
    CONF_EXPERIMENTAL_PINLESS_UNLOCK, CONF_OMIT_ENTITIES, CONF_ENABLE_ENTITIES,
    CONF_QUIET_END, CONF_QUIET_START, CONF_SCAN_INTERVAL,
}

TO_REDACT = {
    "vin", "mobile", "session", "token", "refreshToken", "refresh_token",
    "main_token", "main_refresh_token", "latitude", "longitude", "traceId",
    "plateNo", "plate",
}
# Report groups whose every value may locate the car or identify people (position
# details, emergency phone numbers, location-authorisation dates). Field names are
# kept so unmodelled fields can still be discovered; values are masked.
MASKED_GROUPS = {"positionAccessors", "dialNumberAccessors", "gpsAuthorAccessors"}


def _mask(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _mask(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask(item) for item in value]
    return None if value is None else "**REDACTED**"


def _shape(value: str, known: dict[str, str]) -> str:
    """A push identifier with the VIN and mobile named and any other ID reduced to its length."""
    for label, secret in known.items():
        if len(secret) >= 6:
            value = re.sub(re.escape(secret), f"<{label}>", value, flags=re.IGNORECASE)

    def token(match: re.Match) -> str:
        text = match.group()
        if text in known or not (len(text) >= 20 or (len(text) >= 6 and any(c.isdigit() for c in text))):
            return text
        return f"<{len(text)} digits>" if text.isdigit() else f"<{len(text)} chars>"
    return re.sub(r"[A-Za-z0-9]+", token, value)


def _push(coordinator, entry) -> dict[str, Any] | None:
    """What the push channel sends in the clear on a plaintext broker, without the values."""
    push = getattr(coordinator, "push", None)
    broker = getattr(push, "broker", None)
    if broker is None:
        if getattr(push, "refused_plaintext", False) is True:
            return {"connected": False, "not_used": "the broker is unencrypted and Allow unencrypted push "
                                                    "connections is off; command results are polled"}
        return None
    mobile = re.sub(r"\D", "", str(entry.data.get("mobile") or "")).lstrip("0")
    known = {"VIN": str(entry.data.get("vin") or getattr(coordinator, "vin", None) or ""), "mobile": mobile}
    return {"connected": push.connected is True, "tls": broker.tls, "host": broker.host, "port": broker.port,
            "topics": [_shape(topic, known) for topic in broker.topics],
            "client_id": _shape(broker.client_id, known), "username": _shape(broker.username, known)}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GacConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    status = coordinator.data
    raw = {key: _mask(value) if key in MASKED_GROUPS else value
           for key, value in (status.raw if status else {}).items()}
    region = REGIONS.get(entry.data.get(CONF_REGION), {})
    polling = {"state": getattr(coordinator, "polling_state", None),
               "last_error_reason": getattr(coordinator, "last_refresh_error", None)}
    for name, attr in (("last_attempt", "last_refresh_attempt"), ("last_success", "last_refresh_success"),
                       ("last_error_time", "last_refresh_error_at"), ("retry_not_before", "retry_not_before")):
        value = getattr(coordinator, attr, None)
        polling[name] = value.isoformat() if value is not None else None
    return {
        "library": {"version": LIBRARY_VERSION, "bundled": False},
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": {key: value for key, value in entry.options.items() if key in SAFE_OPTIONS},
        "endpoints": {"account_host": region.get("main"), "vehicle_host": region.get("iov")},
        "polling": polling,
        "status_updated_ms": status.updated_ms if status else None,
        "status_online": status.online if status else None,
        "commands": _commands(coordinator),
        "push": _push(coordinator, entry),
        "account_alerts": alerts.diagnostics() if (alerts := getattr(getattr(entry, "runtime_data", None), "alerts",
                                                                      None)) is not None else None,
        "status_raw": async_redact_data(raw, TO_REDACT),
        "capabilities": coordinator.capabilities.diagnostics() if getattr(coordinator, "capabilities", None) else None,
    }


def _commands(coordinator) -> dict | None:
    """The command ledger, without the car's free-form refusal labels: they are text from the
    service that this export cannot vouch for, so only how many there were is shared."""
    tracker = getattr(coordinator, "commands", None)
    if tracker is None:
        return None
    ledger = dict(tracker.attributes())
    ledger["reported_causes"] = len(ledger.get("reported_causes") or ())
    return ledger
