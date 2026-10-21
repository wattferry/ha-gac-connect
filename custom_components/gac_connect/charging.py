"""Present reported charging information without inventing clock conversions."""
from datetime import datetime

from homeassistant.util import dt as dt_util

from gac_connect.errors import result_reason
from gac_connect.models import ChargingMode
from .api import window_operation

DAYS = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
        "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}


def reported_days(mask: int | None, mode=None) -> str:
    """The app's view: no days is a one-time window (Once); 127 is every day."""
    if mask is None:
        return "Not reported"
    if mask == 127:
        return "Every day"
    if mask == 0:
        return "One time" if mode in (ChargingMode.SCHEDULED, None) else "None"
    return ", ".join(day for index, day in enumerate(DAYS.values()) if mask & (1 << index))


SCHEDULE_TYPES = {ChargingMode.FREE: "Immediately", ChargingMode.SCHEDULED: "Once", ChargingMode.LOOP: "Repeating"}


def _day(struct) -> str | None:
    """A calendar field as "Thu 15 Oct", or None unless it is a real date."""
    try:
        date = datetime(struct["year"], struct["month"], struct["day"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return f"{date:%a} {date.day} {date:%b}"


def reported_window_text(status) -> str:
    """The reported window, with its dates for a one-time window; "Not set" for the car's placeholder."""
    start, stop = (getattr(status, key, None) for key in ("charge_window_start", "charge_window_stop"))
    if start is None and stop is None and getattr(status, "charging_mode", None) is not None:
        return "Not set"
    days = (None, None)
    raw = getattr(status, "raw", None)
    charging = raw.get("chargingAccessors") if isinstance(raw, dict) else None
    if status.charging_mode is ChargingMode.SCHEDULED and isinstance(charging, list) and charging \
            and isinstance(charging[0], dict):
        days = tuple(_day(charging[0].get(key)) for key in ("startTime", "stopTime"))
    return " → ".join(f"{clock or 'Not reported'}" + (f" ({day})" if day and clock else "")
                      for clock, day in zip((start, stop), days, strict=True))


def schedule_mode(status) -> str:
    """Once a one-time window has passed, the car stays in once mode with no times (the app's
    "Charging time is not set") and waits (chargingStatus 27): it will not charge until a
    window is set or Charge now is pressed (Aion UT, 2026-10-16). That is "not_set"."""
    if status is None:
        return "not_reported"
    if (status.charging_mode is ChargingMode.SCHEDULED and status.charge_window_start is None
            and status.charge_window_stop is None):
        return "not_set"
    return {ChargingMode.FREE: "unrestricted", ChargingMode.SCHEDULED: "scheduled",
            ChargingMode.LOOP: "scheduled"}.get(status.charging_mode, "not_reported")


def schedule_attributes(status) -> dict:
    return {
        "reported_start": status.charge_window_start if status else None,
        "reported_stop": status.charge_window_stop if status else None,
        "reported_days": reported_days(status.charge_weekly if status else None,
                                       getattr(status, "charging_mode", None)),
        "reported_schedule_type": SCHEDULE_TYPES.get(getattr(status, "charging_mode", None), "Not reported"),
        "reported_clock_verified": False,
        "reported_clock_consistent": getattr(status, "charge_clock_consistent", None),
        "reported_time_format": getattr(status, "charge_time_format", None),
        "stopping_rule": {0: "Stop time", 1: "Vehicle target charge level"}.get(
            getattr(status, "charge_end_type", None), "Not reported"),
    }


CHARGE_COMMANDS = ("charge-window", "charge-now", "charge-resume", "charge-schedule")
_REQUEST_STATES = {
    "sending": "sending", "pending": "sent; waiting for the car's report",
    "awaiting_report": "sent; waiting for the car's report", "confirmed": "confirmed by the car's report",
    "reported_success": "the car reported success", "timed_out": "not confirmed by the car's report within 3 minutes",
    "cancelled": "cancelled", "superseded": "replaced by a newer request",
}


def _request_day(record, zone) -> str | None:
    """The day a one-time request was dated for, rebuilt as it was sent."""
    expected = record.expected
    try:
        operation = window_operation(expected["charge_window_start"], expected.get("charge_window_stop"), zone,
                                     until_soc=bool(expected.get("charge_end_type")), now=record.requested_at)
    except (KeyError, TypeError, ValueError):
        return None
    return _day(operation.get("startTime"))


def _requested(record, zone=None) -> str:
    """What a charging request asked for, from the fields it waits to see reported."""
    expected = record.expected
    if record.command == "charge-now":
        return "charge whenever plugged in"
    if record.command == "charge-resume":
        return "back to the saved schedule"
    if "charge_window_start" not in expected:
        return "a charging schedule"
    stop = expected.get("charge_window_stop") or "the target charge level"
    days = reported_days(expected.get("charge_weekly"), ChargingMode.SCHEDULED)
    if expected.get("charge_weekly") == 0 and zone is not None and (day := _request_day(record, zone)):
        days += f" on {day}"
    return f"{expected['charge_window_start']} → {stop}, {days}"


def _request_summary(coordinator) -> tuple[str, bool]:
    """The latest charging request and its progress, and whether it still awaits the car."""
    tracker = getattr(coordinator, "commands", None)
    record = next((r for r in reversed(tracker.records) if r.command in CHARGE_COMMANDS), None) if tracker else None
    if record is None:
        return "", False
    if record.state in ("rejected", "failed"):
        reason = record.refusal_reason or result_reason(record.response_code)
        code = f" (code {record.response_code})" if record.response_code else ""
        progress = f"refused: {reason}{code}" if reason else f"failed{code}"
        if record.refusal_details:
            progress += f"; the car reported: {'; '.join(record.refusal_details)}"
    else:
        progress = _REQUEST_STATES.get(record.state, record.state)
    sent = dt_util.as_local(record.requested_at).strftime("%H:%M")
    waiting = record.state in ("sending", "pending", "awaiting_report")
    zone = dt_util.get_time_zone(str(getattr(coordinator.client, "timezone", "") or ""))
    return f"**Last request ({sent}):** {_requested(record, zone)} — {progress}\n\n", waiting


def schedule_summary(coordinator) -> str:
    request, waiting = _request_summary(coordinator)
    data = coordinator.data
    mode = {"unrestricted": "Whenever plugged in", "scheduled": "Scheduled charging",
            "not_set": "Not set: the car will not charge until you set a window or choose Charge now",
            "not_reported": "Not reported"}[schedule_mode(data)]
    if schedule_mode(data) == "scheduled":
        mode += f" ({schedule_attributes(data)['reported_schedule_type'].lower()})"
    fields = schedule_attributes(data)
    age = coordinator.report_age
    age_text = "Not reported" if age is None else "Clock ahead" if age < -60 else f"{max(0, int(age // 60))} minutes"
    refresh = {"waiting": "No refresh yet", "ok": "Last request succeeded", "quiet_hours": "Quiet hours",
               "rate_limited": "Waiting for request limit", "error": "Last refresh failed",
               "auth_required": "Sign in again"}[coordinator.polling_state]
    clock_note = ("The calendar fields and timestamps disagree in the vehicle's reported time zone. "
                  "Calendar start/stop fields are shown; verify them in the official app. "
                  if fields["reported_clock_consistent"] is False else
                  "The reported clock has not been independently verified against the scheduling time zone. ")
    stale = ("The car has not reported the request yet, so the values below are from before it. "
             "Choose Refresh vehicle report in a minute or two.\n\n" if waiting else "")
    return (f"{request}{stale}**Reported mode:** {mode}\n\n"
            f"**Reported window:** {reported_window_text(data) if data else 'Not reported → Not reported'}\n\n"
            f"**Reported days:** {fields['reported_days']}\n\n"
            f"**Stopping rule:** {fields['stopping_rule']}\n\n"
            f"**Report age:** {age_text} · {refresh}\n\n"
            f"**Scheduling time zone:** {coordinator.client.timezone}\n\n"
            "These are cached vehicle readings. Use the Last report and Data freshness sensors to judge their age. "
            "A saved window may still be reported while the car charges whenever plugged in; "
            "that does not mean it is active. "
            f"{clock_note}The target charge level is not available here.")


def window_target(start: str, stop: str | None, weekly: int, until_soc: bool, timezone: str | None = None) -> dict:
    """The reported fields required to confirm a requested window (no days is a one-time window).

    Stopping at the charge limit sends no stop time, and the car keeps its saved one. A
    one-time window already open is sent starting at the next minute, which the car then
    reports; ``timezone`` (the car's) lets that start be expected.
    """
    if not weekly and timezone:
        try:
            zone = dt_util.get_time_zone(timezone)
            struct = window_operation(start, stop, zone, weekly=0, until_soc=until_soc).get("startTime") if zone else None
        except ValueError:
            struct = None
        if struct:
            start = f"{struct['hour']:02d}:{struct['minute']:02d}"
    target = {"charge_scheduled": True, "charge_window_start": start,
              "charge_weekly": weekly, "charge_end_type": int(until_soc)}
    if not until_soc:
        target["charge_window_stop"] = stop
    return target
