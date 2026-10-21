"""Unlock charging connector: shown and sent only with its own permission."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.gac_connect.button import BUTTONS, GacButtonEntity
from custom_components.gac_connect.config_flow import GacConfigFlow, GacOptionsFlow
from custom_components.gac_connect.const import CONF_ALLOW_CHARGER_UNLOCK
from test_autodetect import vehicle
from test_regressions import coord, service_registry

UT_LIST = json.loads((Path(__file__).parent / "fixtures" / "ut_capabilities.json").read_text())
UNLOCK = next(d for d in BUTTONS if d.key == "charger_unlock")


@pytest.mark.parametrize("allowed", [False, True])
def test_the_button_follows_the_permission_and_the_capability_list(tmp_path, allowed):
    async def run():
        async with vehicle(tmp_path, model="Aion UT", options={CONF_ALLOW_CHARGER_UNLOCK: allowed}) as (_, _, c):
            c.client.get_control_capabilities = AsyncMock(return_value=UT_LIST)
            assert not c.capabilities.includes("button:charger_unlock")
            await c.capabilities.async_read_capability_list(c.client, "VIN")
            assert c.capabilities.includes("button:charger_unlock") is allowed
            shown, reason = c.capabilities.decision("button:charger_unlock")
            assert shown is allowed and (allowed or "not allowed" in reason)
    asyncio.run(run())


@pytest.mark.parametrize("allowed", [None, False, "true", 1])
def test_the_action_needs_the_permission_too(allowed):
    c = coord(None)
    c.config_entry.options = {"enable_entities": ["button:charger_unlock"]}
    if allowed is not None:
        c.config_entry.options[CONF_ALLOW_CHARGER_UNLOCK] = allowed
    action = service_registry(c)["send_command"][0]
    with pytest.raises(ServiceValidationError, match="Allow remote charging connector unlock"):
        asyncio.run(action(SimpleNamespace(data={"command": "charger-unlock"})))
    c.client.command.assert_not_awaited()


def test_pressing_sends_the_unlock_and_a_revoked_permission_stops_it(tmp_path):
    async def run():
        async with vehicle(tmp_path, options={CONF_ALLOW_CHARGER_UNLOCK: True}) as (hass, entry, c):
            button = GacButtonEntity(c, UNLOCK)
            await button.async_press()
            c.client.command.assert_awaited_once_with("VIN", "charger-unlock")
            hass.config_entries.async_update_entry(entry, options={CONF_ALLOW_CHARGER_UNLOCK: False})
            with pytest.raises(ServiceValidationError):
                await button.async_press()
            assert c.client.command.await_count == 1
    asyncio.run(run())


@pytest.mark.parametrize("allowed", [False, True])
def test_setup_and_options_save_the_permission(tmp_path, allowed):
    async def run():
        flow = GacConfigFlow()
        async with vehicle(tmp_path) as (hass, entry, _):
            flow.hass = hass
            flow._vehicle = SimpleNamespace(vin="VIN", model="Aion UT")
            flow._client = SimpleNamespace(session=SimpleNamespace(to_dict=Mock(return_value={})))
            defaults = (await flow.async_step_remote_controls())["data_schema"]({})
            assert defaults[CONF_ALLOW_CHARGER_UNLOCK] is False
            await flow.async_step_remote_controls({**defaults, CONF_ALLOW_CHARGER_UNLOCK: allowed})
            created = await flow.async_step_cards({"dashboard_cards": []})
            assert created["options"][CONF_ALLOW_CHARGER_UNLOCK] is allowed
            options_flow = GacOptionsFlow()
            options_flow.hass, options_flow.handler = hass, entry.entry_id
            assert (await options_flow.async_step_settings())["data_schema"]({})[CONF_ALLOW_CHARGER_UNLOCK] is False
            await options_flow.async_step_settings({CONF_ALLOW_CHARGER_UNLOCK: allowed})
            assert entry.options[CONF_ALLOW_CHARGER_UNLOCK] is allowed
    asyncio.run(run())
