"""Services: charge_now, set_charge_window, send_command, get_control_capabilities, get_position,
get_alerts, get_departure_plans."""

from __future__ import annotations

import json
import re
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from gac_connect.errors import GacError

from .api import validate_clock, validate_weekly
from .charge_now import charge_now_request
from .command_tracking import async_send
from .charging import window_target
from .capability_report import cabin_capability_report, full_capability_report
from .const import DOMAIN

ATTR_VIN = "vin"
ATTR_START = "start"
ATTR_STOP = "stop"
ATTR_WEEKLY = "weekly"
ATTR_UNTIL_SOC = "until_soc"
ATTR_COMMAND = "command"
ATTR_PARAMS = "params"
ATTR_PAGE = "page"

# Words in a field name that can place or identify the car or a person; their values are masked in the
# reads below. GAC's alert replies carry the full VIN as "din".
_LOCATING = frozenset({"lat", "latitude", "lon", "lng", "long", "longitude", "gps", "coordinate", "coordinates",
                       "address", "addr", "street", "city", "district", "province", "location", "place", "poi",
                       "vin", "din"})


def _locating(key: object) -> bool:
    return any(word.lower() in _LOCATING for word in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", str(key)))


def _decoded_alerts(page: Any) -> Any:
    """The alert page with each item's ``alarmContent`` JSON string decoded, for reading."""
    items = page.get("list") if isinstance(page, dict) else None
    if not isinstance(items, list):
        return page
    decoded = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("alarmContent"), str):
            try:
                item = {**item, "alarmContent": json.loads(item["alarmContent"])}
            except ValueError:
                pass
        decoded.append(item)
    return {**page, "list": decoded}


def _masked(value: Any, hide: bool = False) -> Any:
    """The position report with every locating value masked and the field names kept."""
    if isinstance(value, dict):
        return {key: _masked(item, hide or _locating(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [_masked(item, hide) for item in value]
    return "**masked**" if hide and value is not None else value


def _coordinators(hass: HomeAssistant) -> dict[str, object]:
    """Map VIN -> coordinator across all loaded entries."""
    out: dict[str, object] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        runtime = getattr(entry, "runtime_data", None)
        if runtime is not None:
            out[runtime.coordinator.vin] = runtime.coordinator
    return out


def _resolve(hass: HomeAssistant, call: ServiceCall):
    coordinators = _coordinators(hass)
    vin = call.data.get(ATTR_VIN) or (next(iter(coordinators)) if len(coordinators) == 1 else None)
    if vin not in coordinators:
        raise HomeAssistantError(f"unknown or unspecified vin; known: {', '.join(coordinators) or 'none'}")
    return coordinators[vin], vin


def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "charge_now"):
        return

    async def charge_now(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        try:
            await async_send(coordinator, "charge-now",
                             charge_now_request(coordinator, until_soc=call.data.get(ATTR_UNTIL_SOC, False)))
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def set_charge_window(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        start, stop = call.data[ATTR_START], call.data.get(ATTR_STOP)
        weekly, until_soc = call.data.get(ATTR_WEEKLY, 0), call.data.get(ATTR_UNTIL_SOC, False)
        if stop is None and not until_soc:
            raise ServiceValidationError("stop is required unless until_soc is set")
        try:
            await async_send(coordinator, "charge-window", coordinator.client.set_charge_window(
                vin, start, stop, weekly=weekly, until_soc=until_soc,
            ), expected=window_target(start, stop, weekly, until_soc, getattr(coordinator.client, "timezone", None)))
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def send_command(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        try:
            command = call.data[ATTR_COMMAND]
            params = call.data.get(ATTR_PARAMS) or {}
            await async_send(coordinator, command, coordinator.client.command(vin, command, **params),
                             expected={} if params else None)
        except (ValueError, TypeError) as err:
            # The library validates raw parameters (e.g. A/C duration or fan speed) before sending.
            raise ServiceValidationError(f"Invalid parameters for {call.data[ATTR_COMMAND]}: {err}") from err
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def get_control_capabilities(call: ServiceCall) -> dict:
        coordinator, vin = _resolve(hass, call)
        try:
            data = await coordinator.client.get_control_capabilities(vin)
            return {**cabin_capability_report(data), "all": full_capability_report(data)}
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def get_position(call: ServiceCall) -> dict:
        coordinator, vin = _resolve(hass, call)
        try:
            return {"position": _masked(await coordinator.client.get_position(vin))}
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def get_alerts(call: ServiceCall) -> dict:
        coordinator, vin = _resolve(hass, call)
        try:
            page = await coordinator.client.get_alarms(vin, page=call.data.get(ATTR_PAGE, 1))
        except GacError as err:
            raise HomeAssistantError(str(err)) from err
        return {"alerts": _masked(_decoded_alerts(page))}

    async def get_departure_plans(call: ServiceCall) -> dict:
        """Both generations the app uses: the plan list, and the older single standby setting."""
        coordinator, vin = _resolve(hass, call)
        reads = {"plans": coordinator.client.get_departure_plans(vin),
                 "standby": coordinator.client.get_standby_config(vin),
                 "default_plan": coordinator.client.get_standby_config(vin, default=True)}
        result: dict[str, Any] = {}
        for key, read in reads.items():
            try:
                result[key] = _masked(await read)
            except GacError as err:
                result[key] = {"error": str(err)}
        return result

    base = vol.Schema({vol.Optional(ATTR_VIN): cv.string})
    hass.services.async_register(
        DOMAIN, "charge_now", charge_now, base.extend({vol.Optional(ATTR_UNTIL_SOC): cv.boolean})
    )
    hass.services.async_register(
        DOMAIN,
        "set_charge_window",
        set_charge_window,
        base.extend(
            {
                vol.Required(ATTR_START): validate_clock,
                vol.Optional(ATTR_STOP): validate_clock,
                vol.Optional(ATTR_WEEKLY): validate_weekly,
                vol.Optional(ATTR_UNTIL_SOC): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "send_command",
        send_command,
        base.extend({vol.Required(ATTR_COMMAND): cv.string, vol.Optional(ATTR_PARAMS): dict}),
    )
    hass.services.async_register(
        DOMAIN, "get_control_capabilities", get_control_capabilities, base,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, "get_position", get_position, base, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(
        DOMAIN, "get_alerts", get_alerts,
        base.extend({vol.Optional(ATTR_PAGE): vol.All(vol.Coerce(int), vol.Range(min=1, max=100))}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, "get_departure_plans", get_departure_plans, base,
                                 supports_response=SupportsResponse.ONLY)

    async def set_entity_visibility(call: ServiceCall) -> None:
        """Automatic (follow the car), always show, or omit one entity, as on the options page."""
        from .const import CONF_ENABLE_ENTITIES, CONF_OMIT_ENTITIES
        from .entity_filter import OMIT_OPTIONS
        from .settings import async_set_options

        coordinator, _ = _resolve(hass, call)
        key, visibility = call.data["entity"], call.data["visibility"]
        if key not in OMIT_OPTIONS:
            raise ServiceValidationError(f"Unknown entity {key!r}; the Entity choices sensor lists them")
        entry = coordinator.config_entry
        always = [item for item in entry.options.get(CONF_ENABLE_ENTITIES, ()) if item != key]
        omit = [item for item in entry.options.get(CONF_OMIT_ENTITIES, ()) if item != key]
        if visibility == "always":
            always.append(key)
        elif visibility == "omit":
            omit.append(key)
        async_set_options(hass, entry, {CONF_ENABLE_ENTITIES: sorted(always), CONF_OMIT_ENTITIES: sorted(omit)})

    hass.services.async_register(DOMAIN, "set_entity_visibility", set_entity_visibility, base.extend({
        vol.Required("entity"): cv.string,
        vol.Required("visibility"): vol.In(("automatic", "always", "omit")),
    }))
