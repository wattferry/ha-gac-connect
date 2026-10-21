"""Location tracking can be limited to a parked or to a moving car."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import CONF_ENABLE_TRACKER, CONF_TRACK_MOVING, CONF_TRACK_PARKED, DEFAULT_ENABLE_TRACKER


def tracking_choices(options: Mapping[str, Any]) -> tuple[bool, bool]:
    """Whether a parked and a moving car are tracked; older entries follow their single setting."""
    enabled = options.get(CONF_ENABLE_TRACKER, DEFAULT_ENABLE_TRACKER) is True
    return options.get(CONF_TRACK_PARKED, enabled) is True, options.get(CONF_TRACK_MOVING, enabled) is True


def location_enabled(options: Mapping[str, Any]) -> bool:
    """Whether the location entities exist at all."""
    return any(tracking_choices(options))


def shown_position(status, options: Mapping[str, Any]) -> tuple[float | None, float | None]:
    """The reported position, or (None, None) while the car is in a state that is not tracked.

    The car reports no speed or gear, so a car that is switched on counts as moving
    and one that is off as parked. While its power state is unknown, the position is
    shown only when both are tracked.
    """
    if status is None:
        return None, None
    parked, moving = tracking_choices(options)
    power_on = getattr(status, "power_on", None)
    shown = parked and moving if power_on is None else moving if power_on else parked
    return (status.latitude, status.longitude) if shown else (None, None)
