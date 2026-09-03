"""Diagnostics with personal data redacted."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import GacConfigEntry

TO_REDACT = {
    "vin", "mobile", "session", "token", "refreshToken", "refresh_token",
    "main_token", "main_refresh_token", "latitude", "longitude", "traceId",
    "plateNo", "plate",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GacConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    status = coordinator.data
    raw = dict(status.raw) if status else {}
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "status_raw": async_redact_data(raw, TO_REDACT),
    }
