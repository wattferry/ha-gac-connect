import asyncio
import inspect
import json
from unittest.mock import Mock, patch

import pytest
from gac_connect.errors import GacError
from gac_connect.session import Session
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.gac_connect.session_store import ConfigEntryStore, session_path


def make_entry(hass, data=None):
    hass.config_entries = ConfigEntries(hass, {})
    params = dict(version=1, minor_version=1, domain="gac_connect", title="Test", data=data or {}, options={},
                  source="user", unique_id="VIN", discovery_keys={}, subentries_data=[])
    entry = ConfigEntry(**{k: v for k, v in params.items() if k in inspect.signature(ConfigEntry).parameters})
    hass.config_entries._entries[entry.entry_id] = entry
    return entry


def test_legacy_migration_rotation_and_removal_are_durable(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"vin": "VIN", "session": Session(token="old").to_dict()})
        hass.config_entries._store = Mock()  # no production config-entry disk writes
        store = ConfigEntryStore(hass, entry)
        assert (await store.load()).token == "old"
        path = session_path(hass, entry.entry_id)
        assert json.loads(path.read_text())["data"]["token"] == "old"
        assert "session" not in entry.data
        assert path.stat().st_mode & 0o777 == 0o600
        await store.save(Session(token="rotated", refresh_token="next"))
        assert json.loads(path.read_text())["data"]["refresh_token"] == "next"
        assert (await ConfigEntryStore(hass, entry).load()).token == "rotated"
        await store.remove()
        assert not path.exists()
    asyncio.run(run())


def test_failed_migration_keeps_legacy_credentials(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"session": Session(token="old").to_dict()})
        with patch("custom_components.gac_connect.session_store.write_utf8_file_atomic", side_effect=OSError("full")):
            with pytest.raises(GacError, match="persist"):
                await ConfigEntryStore(hass, entry).load()
        assert entry.data["session"]["token"] == "old"
    asyncio.run(run())


def test_corrupt_private_store_does_not_fall_back_to_spent_legacy_token(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"session": Session(token="spent").to_dict()})
        path = session_path(hass, entry.entry_id)
        path.parent.mkdir(parents=True)
        path.write_text("{partial")
        with pytest.raises(GacError, match="read"):
            await ConfigEntryStore(hass, entry).load()
        assert entry.data["session"]["token"] == "spent"
    asyncio.run(run())


def test_a_refresh_saves_only_over_the_credentials_it_started_from(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = make_entry(hass, {"vin": "VIN"})
        hass.config_entries._store = Mock()
        store, sign_in = ConfigEntryStore(hass, entry), ConfigEntryStore(hass, entry)
        await store.save(Session(token="old", refresh_token="refresh"))
        await sign_in.save(Session(token="fresh", refresh_token="fresh-refresh"))   # a Reconfigure
        current = await store.replace(("old", "refresh"), Session(token="rotated", refresh_token="next"))
        assert (current.token, (await store.load()).token) == ("fresh", "fresh")    # kept, and handed back
        assert await store.replace(("fresh", "fresh-refresh"), Session(token="t2", refresh_token="r2")) is None
        assert (await store.load()).token == "t2"
        session_path(hass, entry.entry_id).write_text("{corrupt")
        assert await store.replace(("t2", "r2"), Session(token="t3", refresh_token="r3")) is None
        assert (await store.load()).token == "t3"      # unreadable: the rotated pair is the usable one
        assert store._lock is sign_in._lock          # one lock per credentials file
    asyncio.run(run())
