import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from gac_connect.push import interpret
from custom_components.gac_connect.api import PushClient


@pytest.mark.parametrize("payload", [b'{"success":true}', b'[]', b'garbage', b'{{', b'null'])
def test_plaintext_cannot_bypass_configured_decryptor(payload):
    decrypt = Mock()
    client = PushClient(AsyncMock(), Mock(), decrypt=decrypt)
    assert interpret(client._unwrap(payload)).ok is None
    decrypt.assert_not_called()


@pytest.mark.parametrize("outcome", [None, ValueError("invalid envelope")])
def test_failed_decryption_does_not_accept_outer_success(outcome):
    decrypt = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
    client = PushClient(AsyncMock(), Mock(), decrypt=decrypt)
    payload = b'{"encryptData":"bad","success":true}'
    assert interpret(client._unwrap(payload)).ok is None


def test_valid_envelope_and_explicit_no_decryption_mode():
    decoded = {"success": True, "data": {"identifier": {"vin": "VIN"}}}
    client = PushClient(AsyncMock(), Mock(), decrypt=Mock(return_value=decoded))
    result = interpret(client._unwrap(b'{"encryptData":"encrypted"}'))
    assert result.ok is True and result.vin == "VIN"
    plain = PushClient(AsyncMock(), Mock())
    assert interpret(plain._unwrap(json.dumps(decoded).encode())).ok is True


@pytest.mark.parametrize("host,allow,connect", [
    ("tcp://broker.invalid", False, False), ("tcp://broker.invalid", True, True),
    ("ssl://broker.invalid", False, True),
])
def test_transport_requires_tls_or_explicit_consent(host, allow, connect):
    async def run():
        client = PushClient(AsyncMock(), Mock(), allow_plaintext=allow)
        async def fetch():
            client.stop()  # one attempt, no broker or reconnect sleeps
            return {"host": host, "topics": ["result"], "password": "synthetic"}
        client._fetch_info = fetch
        client._tls = AsyncMock(return_value=object())
        client._pump = AsyncMock()
        connection = Mock()
        connection.__aenter__ = AsyncMock(return_value=Mock(subscribe=AsyncMock()))
        connection.__aexit__ = AsyncMock(return_value=False)
        with patch("gac_connect.push.aiomqtt.Client", return_value=connection) as factory:
            await client.run()
        assert factory.called is connect
        if connect:
            assert (factory.call_args.kwargs["tls_context"] is not None) is host.startswith("ssl:")
            client._pump.assert_awaited_once()
        assert client.connected is False
    asyncio.run(run())


@pytest.mark.parametrize("option,allowed", [(None, False), (False, False), (True, True), ("true", False)])
def test_coordinator_push_consent_defaults_to_off(tmp_path, option, allowed):
    from homeassistant.core import HomeAssistant
    from custom_components.gac_connect.coordinator import GacCoordinator
    from test_session_store import make_entry

    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"vin": "VIN"})
        if option is not None:
            hass.config_entries.async_update_entry(entry, options={"allow_plaintext_push": option})
        coordinator = GacCoordinator(hass, entry, Mock())
        assert coordinator.push._allow_plaintext is allowed
    asyncio.run(run())


def test_unrecognised_push_messages_log_field_names_only():
    from custom_components.gac_connect.coordinator import _payload_shape

    shape = _payload_shape(b'{"msgType": 7, "data": {"alarmContent": "PRIVATE-TEXT", "vin": "PRIVATE-VIN"}}')
    assert shape == "keys=['data', 'msgType'] data_keys=['alarmContent', 'vin']"
    assert "PRIVATE" not in shape
    assert _payload_shape(b"\xff") == "1 bytes, not JSON"
    assert _payload_shape(b"[1]") == "list"
