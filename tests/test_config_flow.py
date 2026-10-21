import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.gac_connect.config_flow import GacConfigFlow, GacOptionsFlow
from custom_components.gac_connect.const import CONF_EXPERIMENTAL_PINLESS_UNLOCK


@pytest.mark.parametrize("error", [aiohttp.ClientConnectionError(), TimeoutError()])
@pytest.mark.parametrize("step", ["user", "sms", "vehicle", "reauth_confirm"])
def test_network_failure_is_a_flow_error(tmp_path, error, step):
    async def run():
        flow = GacConfigFlow()
        flow.hass = HomeAssistant(str(tmp_path))
        flow._client = SimpleNamespace(start_captcha=AsyncMock(side_effect=error),
                                       login_sms=AsyncMock(side_effect=error), list_vehicles=AsyncMock(side_effect=error))
        data = {"region": "AU", "mobile": "0412345678", "code": "123456"}
        with patch("custom_components.gac_connect.config_flow.async_create_clientsession", return_value=Mock()), \
             patch("custom_components.gac_connect.config_flow.async_build_client", AsyncMock(return_value=flow._client)):
            result = await getattr(flow, f"async_step_{step}")(data)
        if step == "vehicle":
            assert result["type"] == "abort" and result["reason"] == "cannot_connect"
        else:
            assert result["type"] == "form" and result["errors"] == {"base": "cannot_connect"}
    asyncio.run(run())


@pytest.mark.parametrize("allow_unlock", [None, False, True])
def test_setup_saves_the_unlock_choice(tmp_path, allow_unlock):
    async def run():
        flow = GacConfigFlow()
        flow.hass = HomeAssistant(str(tmp_path))
        flow._vehicle = SimpleNamespace(vin="TESTVIN", model="Aion UT")
        flow._client = SimpleNamespace(session=SimpleNamespace(to_dict=Mock(return_value={})))

        form = await flow.async_step_remote_controls()
        assert form["step_id"] == "remote_controls" and "profile" not in form["data_schema"].schema
        submitted = {} if allow_unlock is None else {CONF_EXPERIMENTAL_PINLESS_UNLOCK: allow_unlock}
        validated = form["data_schema"](submitted)
        assert validated[CONF_EXPERIMENTAL_PINLESS_UNLOCK] is (allow_unlock is True)

        cards = await flow.async_step_remote_controls(validated)
        assert cards["step_id"] == "cards"
        result = await flow.async_step_cards(cards["data_schema"]({}))
        assert result["type"] == "create_entry"     # the cards are off unless chosen: no refresh step
        assert result["options"]["load_cards"] is False and result["options"]["dashboard_cards"] == []
        assert result["options"][CONF_EXPERIMENTAL_PINLESS_UNLOCK] is (allow_unlock is True)
        assert "profile" not in result["options"]
        assert "enable_fridge" not in result["options"]
        assert result["options"]["omit_entities"] == [] and result["options"]["enable_entities"] == []

    asyncio.run(run())


def test_vehicle_choice_reuses_the_list_it_showed(tmp_path):
    async def run():
        flow = GacConfigFlow()
        flow.hass = HomeAssistant(str(tmp_path))
        flow.context = {"source": "user"}
        vehicles = [SimpleNamespace(vin="VIN1", model="Aion UT", plate=None),
                    SimpleNamespace(vin="VIN2", model="Aion V", plate="P2")]
        flow._client = SimpleNamespace(list_vehicles=AsyncMock(return_value=vehicles))
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = Mock()
        flow.async_step_remote_controls = AsyncMock(return_value={"type": "form", "step_id": "remote_controls"})
        shown = await flow.async_step_vehicle()
        assert shown["step_id"] == "vehicle"
        chosen = await flow.async_step_vehicle({"vin": "VIN2"})
        assert chosen["step_id"] == "remote_controls" and flow._vehicle is vehicles[1]
        flow._client.list_vehicles.assert_awaited_once()
    asyncio.run(run())


@pytest.mark.parametrize("model, shown, outcome", [
    ("1", "AION V (P1)", "AION V"),            # the UK reports a model code; a confirmed one gets its name
    (1, "AION V (P1)", "AION V"),
    ("Aion UT", "Aion UT (P1)", "Aion UT"),
    ("99", "99 (P1)", None),                   # an unconfirmed code is shown as it is, and stops setup
])
def test_a_model_code_is_named_once_at_setup(tmp_path, model, shown, outcome):
    async def run():
        flow = GacConfigFlow()
        flow.hass = HomeAssistant(str(tmp_path))
        flow.context = {"source": "user"}
        flow._region, flow._mobile = "GB", "07123456789"
        vehicles = [SimpleNamespace(vin="VIN1", model=model, plate="P1"),
                    SimpleNamespace(vin="VIN2", model="Aion V", plate="P2")]
        flow._client = SimpleNamespace(list_vehicles=AsyncMock(return_value=vehicles),
                                       session=SimpleNamespace(to_dict=Mock(return_value={})))
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = Mock()
        form = await flow.async_step_vehicle()
        assert form["data_schema"].schema["vin"].container["VIN1"] == shown
        result = await flow.async_step_vehicle({"vin": "VIN1"})
        if outcome is None:
            assert result["type"] == "abort" and result["reason"] == "unrecognised_model"
            return
        assert result["step_id"] == "remote_controls"
        assert result["description_placeholders"]["model"] == outcome
        await flow.async_step_remote_controls({})
        created = await flow.async_step_cards({})
        assert created["title"] == outcome and created["data"]["model"] == outcome
    asyncio.run(run())


def test_every_launched_market_and_the_uk_can_be_chosen_by_name(tmp_path):
    from gac_connect.const import LISTED_REGIONS, REGIONS as LIBRARY_REGIONS
    from custom_components.gac_connect.config_flow import REGION_NAMES, REGIONS

    async def run():
        flow = GacConfigFlow()
        flow.hass = HomeAssistant(str(tmp_path))
        form = await flow.async_step_user()
        selector = form["data_schema"].schema["region"]
        options = selector.config["options"]
        assert [option["value"] for option in options] == REGIONS
        assert set(REGIONS) == LISTED_REGIONS | {"GB"} and set(REGIONS) <= set(LIBRARY_REGIONS)
        assert [option["label"] for option in options] == sorted(REGION_NAMES.values())
        assert selector("TH") == "TH"
        with pytest.raises(Exception):
            selector("ZZ")
    asyncio.run(run())


def test_reconfigure_signs_in_again_and_keeps_the_entry(tmp_path):
    from homeassistant.config_entries import SOURCE_RECONFIGURE
    from test_autodetect import vehicle

    async def run():
        async with vehicle(tmp_path) as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, data={**entry.data, "mobile": "0812345678"})
            flow = GacConfigFlow()
            flow.hass = hass
            flow.context = {"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
            form = await flow.async_step_reconfigure()
            assert form["type"] == "form" and form["step_id"] == "reauth_confirm"
            assert (flow._region, flow._mobile) == ("AU", "0812345678")
            # After the puzzle and the SMS code: the same entry gets the new session.
            flow._client = SimpleNamespace(list_vehicles=AsyncMock(return_value=[SimpleNamespace(vin="VIN")]),
                                           session=SimpleNamespace())
            flow._mobile = "0899999999"
            hass.config_entries.async_schedule_reload = Mock()
            entry.async_on_unload(entry.add_update_listener(AsyncMock()))    # as async_setup_entry adds
            with patch("custom_components.gac_connect.config_flow.ConfigEntryStore") as store, \
                    patch("homeassistant.config_entries.report_usage") as deprecated:
                store.return_value.save = AsyncMock()
                done = await flow.async_step_vehicle()
            assert (done["type"], done["reason"]) == ("abort", "reauth_successful")
            store.return_value.save.assert_awaited_once_with(flow._client.session)
            assert entry.data["mobile"] == "0899999999"
            hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)
            deprecated.assert_not_called()     # HA 2026.12 drops reload_and_abort with an update listener
    asyncio.run(run())


def test_settings_drop_the_retired_car_picture(tmp_path):
    from test_autodetect import vehicle

    async def run():
        async with vehicle(tmp_path, options={"picture": "/local/old.png", "scan_interval": 120}) as (hass, entry, _):
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            form = await flow.async_step_settings()
            assert "picture" not in form["data_schema"].schema
            await flow.async_step_settings({"scan_interval": 180})
            assert "picture" not in entry.options and entry.options["scan_interval"] == 180
    asyncio.run(run())
