"""Config flow: region → mobile → slide puzzle → SMS code → vehicle.

The puzzle is an external step (see captcha_view). Reauth re-runs sign-in;
reconfigure changes region/vehicle; options tune polling and privacy.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from gac_connect.client import GacClient

import voluptuous as vol
from gac_connect.errors import GacError, LoginError

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_REGION
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.network import get_url

from .captcha_view import CAPTCHA_URL, GacCaptchaView, flow_state
from .helpers import async_build_client
from .const import (
    CONF_AC_MINUTES,
    CONF_ENABLE_TRACKER,
    CONF_MOBILE,
    CONF_MODEL,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_SCAN_INTERVAL,
    CONF_SESSION,
    CONF_VIN,
    DEFAULT_ENABLE_TRACKER,
    DEFAULT_AC_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

REGIONS = ["AU", "NZ", "GB", "SG", "AE"]


class GacConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._client: GacClient | None = None
        self._mobile: str | None = None
        self._region: str = "AU"
        self._view_registered = False

    # ---- step 1: region + mobile ----------------------------------------
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._region = user_input[CONF_REGION]
            self._mobile = user_input[CONF_MOBILE]
            try:
                http = async_create_clientsession(self.hass)
                self._client = await async_build_client(self.hass, self._region, http)
                await self._client.start_captcha()
            except GacError:
                errors["base"] = "cannot_connect"
            else:
                return await self.async_step_captcha()
        schema = vol.Schema({
            vol.Required(CONF_REGION, default=self._region): vol.In(REGIONS),
            vol.Required(CONF_MOBILE): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    # ---- step 2: slide puzzle (external) --------------------------------
    async def async_step_captcha(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # Resumed by the captcha view once the puzzle is solved and SMS is sent.
        if user_input is not None:
            # An external step may only transition to an external-step-done, which
            # then hands off to the SMS step.
            flow_state(self.hass).pop(self.flow_id, None)
            return self.async_external_step_done(next_step_id="sms")

        if not self._view_registered:
            self.hass.http.register_view(GacCaptchaView())
            self._view_registered = True
        flow_state(self.hass)[self.flow_id] = {
            "client": self._client,
            "mobile": self._mobile,
            "captcha": self._client._captcha,  # already fetched in step 1
            "attempt": 1,
            "status": "pending",
        }
        base = get_url(self.hass, prefer_external=False, allow_ip=True)
        return self.async_external_step(step_id="captcha", url=f"{base}{CAPTCHA_URL}?flow_id={self.flow_id}")

    # ---- step 3: SMS code ------------------------------------------------
    async def async_step_sms(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._client.login_sms(self._mobile, user_input["code"])
            except LoginError:
                errors["base"] = "invalid_code"
            except GacError:
                errors["base"] = "cannot_connect"
            if not errors:
                return await self.async_step_vehicle()
        return self.async_show_form(
            step_id="sms", data_schema=vol.Schema({vol.Required("code"): str}), errors=errors,
        )

    # ---- step 4: pick the vehicle ---------------------------------------
    async def async_step_vehicle(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        vehicles = await self._client.list_vehicles()
        if not vehicles:
            return self.async_abort(reason="no_vehicles")
        by_vin = {v.vin: v for v in vehicles}

        if len(vehicles) == 1:
            user_input = {CONF_VIN: vehicles[0].vin}
        if user_input is not None:
            vin = user_input[CONF_VIN]
            await self.async_set_unique_id(vin)
            self._abort_if_unique_id_configured()
            veh = by_vin[vin]
            return self.async_create_entry(
                title=veh.model or f"Aion {vin[-4:]}",
                data={
                    CONF_REGION: self._region,
                    CONF_MOBILE: self._mobile,
                    CONF_VIN: vin,
                    CONF_MODEL: veh.model,
                    CONF_SESSION: self._client.session.to_dict(),
                },
            )
        options = {v.vin: f"{v.model or 'Aion'} ({v.plate or v.vin[-4:]})" for v in vehicles}
        return self.async_show_form(
            step_id="vehicle", data_schema=vol.Schema({vol.Required(CONF_VIN): vol.In(options)}),
        )

    # ---- reauth ----------------------------------------------------------
    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        self._region = entry_data[CONF_REGION]
        self._mobile = entry_data.get(CONF_MOBILE)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        http = async_create_clientsession(self.hass)
        self._client = await async_build_client(self.hass, self._region, http)
        await self._client.start_captcha()
        return await self.async_step_captcha()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GacOptionsFlow:
        return GacOptionsFlow()


class GacOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL,
                         default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)):
                vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL)),
            vol.Optional(CONF_ENABLE_TRACKER,
                         default=opts.get(CONF_ENABLE_TRACKER, DEFAULT_ENABLE_TRACKER)): bool,
            vol.Optional(CONF_QUIET_START, default=opts.get(CONF_QUIET_START, "")): str,
            vol.Optional(CONF_QUIET_END, default=opts.get(CONF_QUIET_END, "")): str,
            vol.Optional(CONF_AC_MINUTES, default=opts.get(CONF_AC_MINUTES, DEFAULT_AC_MINUTES)):
                vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
