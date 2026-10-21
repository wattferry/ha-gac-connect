"""The integration must exercise only the library's public API."""
import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import gac_connect
import pytest
from gac_connect.client import GacClient as LibraryClient
from gac_connect.const import PROFILE_MATERIAL, REGIONS
from gac_connect.session import MemoryStore

from custom_components.gac_connect import api, helpers


def test_the_library_is_actually_exercised():
    assert api.GacClient is LibraryClient
    for name in api.__all__:
        assert getattr(api, name) is getattr(gac_connect, name), name
    assert api.GacClient.__module__ == "gac_connect.client"
    assert not any(name.startswith("custom_components.gac_connect._compat_b1") for name in sys.modules)


@pytest.mark.parametrize("region", list(REGIONS))
def test_factory_uses_selected_client_and_loads_correct_profile_off_loop(region):
    material = Mock()
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(return_value=material),
                           config=SimpleNamespace(time_zone="UTC"))
    http, store = Mock(), MemoryStore()
    with patch.object(helpers, "async_setup_limits", new=AsyncMock()) as limits:
        client = asyncio.run(helpers.async_build_client(hass, region, http, store))
    assert type(client) is api.GacClient
    assert client._http is http and client._store is store and client._m is material
    limits.assert_awaited_once_with(hass)
    hass.async_add_executor_job.assert_awaited_once_with(helpers.load_material, PROFILE_MATERIAL[REGIONS[region]["profile"]])



@pytest.mark.parametrize("ha_zone,region,expected", [
    ("Australia/Perth", "AU", "Australia/Perth"),      # a multi-zone country follows HA
    ("Asia/Bangkok", "TH", "Asia/Bangkok"),
    ("Europe/London", "TH", "Europe/London"),          # HA's choice wins even if it differs
    ("UTC", "AU", "Australia/Brisbane"),               # looks unset: the region's zone
    ("Etc/GMT", "TH", "Asia/Bangkok"),
    ("Not/AZone", "TH", "Asia/Bangkok"),
    (None, "NZ", "Pacific/Auckland"),
])
def test_schedules_use_home_assistants_time_zone_unless_it_looks_unset(ha_zone, region, expected):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(return_value=Mock()),
                           config=SimpleNamespace(time_zone=ha_zone))
    with patch.object(helpers, "async_setup_limits", new=AsyncMock()):
        client = asyncio.run(helpers.async_build_client(hass, region, Mock(), MemoryStore()))
    assert client.timezone == expected and client._zone().key == expected
