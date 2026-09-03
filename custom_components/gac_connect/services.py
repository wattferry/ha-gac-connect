"""Services: charge_now, charge_pause, set_charge_window, send_command."""
from __future__ import annotations

import voluptuous as vol
from gac_connect.errors import GacError

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

ATTR_VIN = "vin"
ATTR_START = "start"
ATTR_STOP = "stop"
ATTR_WEEKLY = "weekly"
ATTR_UNTIL_SOC = "until_soc"
ATTR_COMMAND = "command"
ATTR_PARAMS = "params"


def _clients(hass: HomeAssistant) -> dict[str, object]:
    """Map VIN -> client across all loaded entries."""
    out: dict[str, object] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        runtime = getattr(entry, "runtime_data", None)
        if runtime is not None:
            out[runtime.coordinator.vin] = runtime.client
    return out


def _resolve(hass: HomeAssistant, call: ServiceCall):
    clients = _clients(hass)
    vin = call.data.get(ATTR_VIN) or (next(iter(clients)) if len(clients) == 1 else None)
    if vin not in clients:
        raise HomeAssistantError(f"unknown or unspecified vin; known: {', '.join(clients) or 'none'}")
    return clients[vin], vin


def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "charge_now"):
        return

    async def charge_now(call: ServiceCall) -> None:
        client, vin = _resolve(hass, call)
        try:
            await client.charge_now(vin, until_soc=call.data.get(ATTR_UNTIL_SOC, False))
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def charge_pause(call: ServiceCall) -> None:
        client, vin = _resolve(hass, call)
        try:
            await client.charge_pause(vin)
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def set_charge_window(call: ServiceCall) -> None:
        client, vin = _resolve(hass, call)
        try:
            await client.set_charge_window(
                vin, call.data[ATTR_START], call.data[ATTR_STOP],
                weekly=call.data.get(ATTR_WEEKLY, 0),
                until_soc=call.data.get(ATTR_UNTIL_SOC, False),
            )
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    async def send_command(call: ServiceCall) -> None:
        client, vin = _resolve(hass, call)
        try:
            await client.command(vin, call.data[ATTR_COMMAND], **(call.data.get(ATTR_PARAMS) or {}))
        except GacError as err:
            raise HomeAssistantError(str(err)) from err

    base = vol.Schema({vol.Optional(ATTR_VIN): cv.string})
    hass.services.async_register(DOMAIN, "charge_now", charge_now,
                                 base.extend({vol.Optional(ATTR_UNTIL_SOC): cv.boolean}))
    hass.services.async_register(DOMAIN, "charge_pause", charge_pause, base)
    hass.services.async_register(DOMAIN, "set_charge_window", set_charge_window, base.extend({
        vol.Required(ATTR_START): cv.string, vol.Required(ATTR_STOP): cv.string,
        vol.Optional(ATTR_WEEKLY): cv.positive_int, vol.Optional(ATTR_UNTIL_SOC): cv.boolean,
    }))
    hass.services.async_register(DOMAIN, "send_command", send_command,
                                 base.extend({vol.Required(ATTR_COMMAND): cv.string,
                                              vol.Optional(ATTR_PARAMS): dict}))
