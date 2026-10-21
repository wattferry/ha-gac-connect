"""Map library lock state to Home Assistant's binary sensor polarity."""
from __future__ import annotations

from gac_connect.models import VehicleStatus

from .api import doors_locked as doors_locked


def car_locked(status: VehicleStatus | None, model: str | None = None) -> bool | None:
    """Locked means all four doors locked and the boot shut: with the boot open the car is not locked."""
    if status is not None and status.hatch_open is True:
        return False
    return doors_locked(status, model)


def doors_unlocked(status: VehicleStatus, model: str | None = None) -> bool | None:
    """Home Assistant lock binary sensors use on for unlocked; an open boot counts as unlocked."""
    locked = car_locked(status, model)
    return None if locked is None else not locked
