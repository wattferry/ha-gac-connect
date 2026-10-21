"""Read seats by their app IDs, including during partial library updates."""
from __future__ import annotations


def reported_seat(status, seat_id: int):
    return next((seat for seat in getattr(status, "seats", ()) if seat.position == str(seat_id)), None)


def ventilation_state(status, seat_id: int) -> bool | None:
    return getattr(reported_seat(status, seat_id), "ventilation_on", None)


def ventilation_level(status, seat_id: int) -> int | None:
    """0 when off, else the reported level; None while unknown."""
    seat = reported_seat(status, seat_id)
    on = getattr(seat, "ventilation_on", None)
    if on is None:
        return None
    if not on:
        return 0
    strength = getattr(seat, "ventilation_strength", None)
    return int(strength) if strength is not None and strength == int(strength) else None
