import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import UnknownFlow

from gac_connect.puzzle import PuzzleSession
from custom_components.gac_connect.captcha_view import GacCaptchaView, flow_state
from custom_components.gac_connect.config_flow import GacConfigFlow


def pending(hass):
    hass.config_entries = SimpleNamespace(flow=SimpleNamespace(async_get=Mock(return_value={"step_id": "captcha"}),
                                                              async_abort=Mock(), async_configure=AsyncMock()))
    client = SimpleNamespace(request_sms=AsyncMock(), start_captcha=AsyncMock())
    session = PuzzleSession(client, "synthetic", SimpleNamespace(background="", piece=""))
    flow_state(hass)["flow"] = {"session": session, "expires": time.monotonic()+600}
    request = SimpleNamespace(app={"hass": hass}, query={"flow_id": "flow", "state": "1"},
                              json=AsyncMock(return_value={"x": 10}))
    return request, client


def test_removed_flow_and_expired_flow_cannot_request_sms(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        for expired in (False, True):
            request, client = pending(hass)
            if expired:
                flow_state(hass)["flow"]["expires"] = 0
            else:
                hass.config_entries.flow.async_get.side_effect = UnknownFlow
            assert (await GacCaptchaView().post(request)).status == 404
            assert "flow" not in flow_state(hass)
            client.request_sms.assert_not_called()
    asyncio.run(run())


def test_flow_removal_cancels_inflight_verification_and_detaches_session(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        request, client = pending(hass)
        started = asyncio.Event()
        async def waiting(*args):
            started.set()
            await asyncio.Event().wait()
        client.request_sms.side_effect = waiting
        task = asyncio.create_task(GacCaptchaView().post(request))
        await started.wait()
        flow = GacConfigFlow()
        flow.hass, flow.flow_id = hass, "flow"
        flow._http = SimpleNamespace(detach=Mock())
        http = flow._http
        cancel = flow._captcha_expiry = Mock()
        flow.async_remove()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)
        assert not flow_state(hass)
        http.detach.assert_called_once()
        cancel.assert_called_once()
        hass.config_entries.flow.async_configure.assert_not_awaited()
    asyncio.run(run())


def test_flow_cleanup_preserves_the_shared_home_assistant_connector(tmp_path):
    import aiohttp
    from homeassistant.helpers.aiohttp_client import async_create_clientsession

    async def run():
        hass = HomeAssistant(str(tmp_path))
        connector = aiohttp.TCPConnector()
        flow = GacConfigFlow()
        flow.hass, flow.flow_id = hass, "flow"
        other = None
        try:
            with patch("homeassistant.helpers.aiohttp_client._async_get_connector", return_value=connector):
                other = async_create_clientsession(hass, auto_cleanup=False)
                first = await flow._new_http()
                second = await flow._new_http()
            assert first.closed
            assert not second.closed and not other.closed and not connector.closed
            flow.async_remove()
            assert second.closed
            assert not other.closed and not connector.closed
        finally:
            if other is not None:
                other.detach()
            if flow._http is not None:
                flow._http.detach()
            await connector.close()
    asyncio.run(run())


def test_cancellation_while_reading_request_body_cannot_send_sms(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        request, client = pending(hass)
        async def read_body():
            flow_state(hass).clear()  # removed while the HTTP body was arriving
            return {"x": 10}
        request.json = read_body
        assert (await GacCaptchaView().post(request)).status == 404
        client.request_sms.assert_not_called()
    asyncio.run(run())


@pytest.mark.parametrize("body", [[], {}, {"x": -1}, {"x": 264}, {"x": True}, {"x": "10"}])
def test_invalid_offset_cannot_request_sms(tmp_path, body):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        request, client = pending(hass)
        request.json.return_value = body
        response = await GacCaptchaView().post(request)
        assert response.status == 400
        client.request_sms.assert_not_called()
    asyncio.run(run())


def test_expiry_aborts_the_flow(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        pending(hass)
        flow = GacConfigFlow()
        flow.hass, flow.flow_id = hass, "flow"
        flow._expire_puzzle(None)
        hass.config_entries.flow.async_abort.assert_called_once_with("flow")
        assert not flow_state(hass)
    asyncio.run(run())


def test_a_right_slide_resumes_the_flow_once_and_a_wrong_one_shows_a_new_puzzle(tmp_path):
    from gac_connect.errors import CaptchaError

    async def run():
        hass = HomeAssistant(str(tmp_path))
        request, client = pending(hass)
        client.request_sms.side_effect = [CaptchaError("rejected"), None]
        client.start_captcha.return_value = SimpleNamespace(background="bg2", piece="piece2")
        response = await GacCaptchaView().post(request)
        assert response.status == 200 and flow_state(hass)["flow"]["session"].state()["attempt"] == 2
        hass.config_entries.flow.async_configure.assert_not_called()
        assert (await GacCaptchaView().post(request)).status == 200
        await asyncio.sleep(0)
        hass.config_entries.flow.async_configure.assert_called_once_with(flow_id="flow", user_input={})
        assert (await GacCaptchaView().post(request)).status == 200      # already verified
        await asyncio.sleep(0)
        assert client.request_sms.await_count == 2 and hass.config_entries.flow.async_configure.call_count == 1
        state = await GacCaptchaView().get(request)
        assert state.status == 200
    asyncio.run(run())


def test_a_second_verify_while_the_first_is_checked_leaves_it_cancellable(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        request, client = pending(hass)
        started = asyncio.Event()

        async def waiting(*args):
            started.set()
            await asyncio.Event().wait()
        client.request_sms.side_effect = waiting
        first = asyncio.create_task(GacCaptchaView().post(request))
        await started.wait()
        assert (await GacCaptchaView().post(request)).status == 409       # busy
        assert flow_state(hass)["flow"]["verification_task"] is first      # still tracked
        flow = GacConfigFlow()
        flow.hass, flow.flow_id = hass, "flow"
        flow._http = SimpleNamespace(detach=Mock())
        flow._captcha_expiry = Mock()
        flow.async_remove()
        with pytest.raises(asyncio.CancelledError):
            await first
        hass.config_entries.flow.async_configure.assert_not_called()
    asyncio.run(run())
