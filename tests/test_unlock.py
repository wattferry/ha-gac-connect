import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from gac_connect.errors import CommandError
from homeassistant.exceptions import HomeAssistantError

from custom_components.gac_connect.const import CONF_EXPERIMENTAL_PINLESS_UNLOCK
from custom_components.gac_connect.lock import GacLock
from test_client_failures import Response, make_client
from test_regressions import coord


@pytest.fixture(autouse=True)
def transition_timer(monkeypatch):
    monkeypatch.setattr("custom_components.gac_connect.transition.async_call_later", Mock(return_value=Mock()))


@pytest.mark.parametrize("enabled", [None, False, True])
def test_unlock_calls_public_client_method_only_when_enabled(enabled):
    coordinator = coord(None)
    if enabled is not None:
        coordinator.config_entry.options[CONF_EXPERIMENTAL_PINLESS_UNLOCK] = enabled
    coordinator.client.unlock = AsyncMock(return_value={"code": 13001})
    entity = GacLock(coordinator)
    assert entity.code_format is None  # Enabling the control never changes a PIN requirement.
    entity.async_write_ha_state = Mock()
    if enabled:
        asyncio.run(entity.async_unlock())
        coordinator.client.unlock.assert_awaited_once_with("TESTVIN")
        coordinator.async_schedule_command_refresh.assert_called_once()
        assert entity.is_unlocking
    else:
        with pytest.raises(HomeAssistantError, match="Remote unlocking is disabled.*Allow remote unlocking"):
            asyncio.run(entity.async_unlock())
        coordinator.client.unlock.assert_not_called()


def test_unlock_failure_clears_pending_state_and_surfaces_error():
    coordinator = coord(None)
    coordinator.config_entry.options[CONF_EXPERIMENTAL_PINLESS_UNLOCK] = True
    coordinator.client.unlock = AsyncMock(side_effect=CommandError("rejected"))
    entity = GacLock(coordinator)
    entity.async_write_ha_state = Mock()
    with pytest.raises(HomeAssistantError, match="rejected"):
        asyncio.run(entity.async_unlock())
    assert not entity.is_unlocking
    coordinator.client.unlock.assert_awaited_once()


@pytest.mark.parametrize("body,accepted", [({"code": 13001}, True), ({"success": "false"}, False), ({}, False)])
@pytest.mark.parametrize("generic", [False, True])
def test_unlock_uses_normal_transport_and_command_acceptance(body, accepted, generic):
    from gac_connect.limits import Limiter
    from unittest.mock import patch

    with patch("gac_connect.client.DEFAULT_LIMITER", Limiter(min_gap=0, state_path=None)):
        client, http, _ = make_client(Response(body=body), valid=True)

    async def run():
        await client.load()
        action = client.command("VIN", "unlock") if generic else client.unlock("VIN")
        if accepted:
            assert await action == body
        else:
            with pytest.raises(CommandError):
                await action

    asyncio.run(run())
    assert http.post.call_count == 1
    assert http.post.call_args.args[0].endswith("/door/unlock")


@pytest.mark.parametrize("enabled", [None, False, "true", True])
def test_advanced_action_unlock_honors_the_same_opt_in(enabled):
    from types import SimpleNamespace

    from homeassistant.exceptions import ServiceValidationError

    from test_regressions import service_registry

    coordinator = coord(None)
    if enabled is not None:
        coordinator.config_entry.options[CONF_EXPERIMENTAL_PINLESS_UNLOCK] = enabled
    action = service_registry(coordinator)["send_command"][0]
    call = SimpleNamespace(data={"command": "unlock"})
    if enabled is True:
        asyncio.run(action(call))
        coordinator.client.command.assert_awaited_once_with("TESTVIN", "unlock")
    else:
        with pytest.raises(ServiceValidationError, match="Allow remote unlocking"):
            asyncio.run(action(call))
        coordinator.client.command.assert_not_awaited()


@pytest.mark.parametrize("command,params", [("aircon-on", {"currentDuration": 90}),
                                            ("aircon-manual-on", {"windStrength": 11}),
                                            ("aircon-on", {"temperature": "hot"})])
def test_advanced_action_reports_invalid_raw_parameters_as_validation_errors(command, params):
    from types import SimpleNamespace

    from homeassistant.exceptions import ServiceValidationError

    from test_client_failures import make_client as client_for
    from test_regressions import service_registry

    coordinator = coord(None)
    coordinator.client, http, _ = client_for(Response(body={"code": 13001}), valid=True)
    action = service_registry(coordinator)["send_command"][0]
    with pytest.raises(ServiceValidationError, match=f"Invalid parameters for {command}"):
        asyncio.run(action(SimpleNamespace(data={"command": command, "params": params})))
    http.post.assert_not_called()
