import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.gac_connect.config_flow import GacOptionsFlow
from custom_components.gac_connect.const import CONF_EXPERIMENTAL_PINLESS_UNLOCK
from custom_components.gac_connect.coordinator import GacCoordinator
from test_session_store import make_entry


def test_repeated_submits_persist_and_notify_without_finishing_the_flow(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"vin": "VIN", "model": "Aion V"})
        hass.config_entries._store = Mock()
        listener = AsyncMock()
        remove_listener = entry.add_update_listener(listener)
        flow = GacOptionsFlow()
        flow.hass, flow.handler = hass, entry.entry_id
        try:
            for interval in (600, 900):
                result = await flow.async_step_settings({"scan_interval": interval})
                assert result["type"] == "menu" and result["step_id"] == "init"
                await hass.async_block_till_done()
                assert entry.options["scan_interval"] == interval
                reopened = await flow.async_step_settings()
                assert reopened["data_schema"]({})["scan_interval"] == interval
            assert listener.await_count == 2
            saved = dict(entry.options)
            invalid = await flow.async_step_settings({"quiet_start": "invalid", "quiet_end": "06:00"})
            assert invalid["type"] == "form"
            assert dict(entry.options) == saved
        finally:
            remove_listener()
    asyncio.run(run())


@pytest.mark.parametrize("allow_unlock", [None, False, True])
def test_options_preserve_existing_unlock_preference(tmp_path, allow_unlock):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"vin": "VIN", "model": "Aion V"})
        hass.config_entries._store = Mock()
        if allow_unlock is not None:
            hass.config_entries.async_update_entry(entry, options={CONF_EXPERIMENTAL_PINLESS_UNLOCK: allow_unlock})
        flow = GacOptionsFlow()
        flow.hass, flow.handler = hass, entry.entry_id

        form = await flow.async_step_settings()
        # Saving an unrelated setting through the displayed form must keep the
        # existing choice; an older entry without the option stays disabled.
        validated = form["data_schema"]({"scan_interval": 600})
        assert validated[CONF_EXPERIMENTAL_PINLESS_UNLOCK] is (allow_unlock is True)
        result = await flow.async_step_settings(validated)
        assert result["type"] == "menu" and result["step_id"] == "init"
        assert entry.options[CONF_EXPERIMENTAL_PINLESS_UNLOCK] is (allow_unlock is True)
        assert entry.options["scan_interval"] == 600

    asyncio.run(run())


@pytest.mark.parametrize("start,end,error", [
    ("25:70", "06:00", "invalid_quiet_time"), ("1:00", "06:00", "invalid_quiet_time"),
    ("22:00", "", "quiet_pair_required"), ("", "06:00", "quiet_pair_required"),
    ("22:00", "22:00", "quiet_times_equal"), ("words", "06:00", "invalid_quiet_time"),
    ("", "", None), ("22:00", "06:00", None), ("08:00", "18:00", None),
])
def test_quiet_hours_validation(tmp_path, start, end, error):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"vin": "VIN"})
        flow = GacOptionsFlow()
        flow.hass = hass
        flow.handler = entry.entry_id
        result = await flow.async_step_settings({"quiet_start": start, "quiet_end": end})
        if error:
            assert result["type"] == "form"
            assert error in result["errors"].values()
        else:
            assert result["type"] == "menu" and result["step_id"] == "init"
            assert entry.options["quiet_start"] == start
            assert entry.options["quiet_end"] == end
    asyncio.run(run())


@pytest.mark.parametrize("start,end,clock,quiet", [
    ("22:00", "06:00", "23:00", True), ("22:00", "06:00", "05:59", True),
    ("22:00", "06:00", "06:00", False), ("08:00", "18:00", "08:00", True),
    ("08:00", "18:00", "18:00", False), ("", "", "23:00", False),
])
def test_quiet_hours_boundaries_use_home_assistant_clock(start, end, clock, quiet):
    from types import SimpleNamespace
    coordinator = object.__new__(GacCoordinator)
    coordinator.config_entry = SimpleNamespace(options={"quiet_start": start, "quiet_end": end})
    now = datetime.fromisoformat(f"2026-10-11T{clock}:00+07:00")
    with patch("custom_components.gac_connect.coordinator.dt_util.now", return_value=now):
        assert coordinator._in_quiet_hours() is quiet
