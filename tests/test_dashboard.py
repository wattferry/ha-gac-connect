"""The dashboard cards: nothing loads until the owner installs them, the bundle loads while any car
wants it, and the generated dashboard is created, kept, updated or removed only while it is exactly
as generated."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.components.lovelace.const import ConfigNotFound
from homeassistant.core import HomeAssistant

from custom_components.gac_connect import dashboard
from custom_components.gac_connect.dashboard import (
    DashboardEdited, VehicleDashboard, async_apply_dashboard, async_remove_dashboard, async_want_cards,
    dashboard_cards, dashboard_config,
)


class Board:
    def __init__(self, item_id: str, url_path: str) -> None:
        self.config = {"id": item_id, "url_path": url_path}
        self.saved = None

    async def async_load(self, force: bool):
        if self.saved is None:
            raise ConfigNotFound
        return self.saved

    async def async_save(self, config):
        self.saved = config


class Collection:
    def __init__(self, boards: dict) -> None:
        self.boards = boards
        self.created: list[dict] = []
        self.deleted: list[str] = []

    async def async_create_item(self, data):
        item_id = f"id-{len(self.created) + 1}"
        self.created.append(data)
        self.boards[data["url_path"]] = Board(item_id, data["url_path"])
        return {"id": item_id, **data}

    async def async_delete_item(self, item_id):
        self.deleted.append(item_id)
        for key, board in list(self.boards.items()):
            if board.config["id"] == item_id:
                del self.boards[key]


def lovelace(boards: dict | None = None):
    boards = {} if boards is None else boards
    collection = Collection(boards)
    stack = [patch.object(dashboard, "_dashboards", lambda hass: boards),
             patch.object(dashboard, "_collection", lambda hass: collection),
             patch.object(dashboard, "_available", lambda hass: True)]
    for item in stack:
        item.start()
    return boards, collection, lambda: [item.stop() for item in stack]


EVERY = ("vehicle", "charging", "climate", "location", "activity", "settings")


def test_a_dashboard_holds_the_chosen_cards_and_goes_when_none_are_chosen(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        boards, collection, stop = lovelace()
        try:
            car = VehicleDashboard(hass, "entry")
            assert await car.async_apply(EVERY, "device", "AION V")
            assert collection.created == [{"url_path": "gac-aion-v", "title": "AION V", "icon": "mdi:car-electric",
                                           "require_admin": False, "show_in_sidebar": True}]
            board = boards["gac-aion-v"]
            assert board.saved == dashboard_config("device", "AION V", EVERY)
            assert [[card["type"] for card in view["cards"]] for view in board.saved["views"]] == [
                [f"custom:gac-{kind}-card" for kind in EVERY[:5]], ["custom:gac-settings-card"]]

            assert await car.async_apply(EVERY, "device", "AION V")        # kept, not created again
            assert len(collection.created) == 1
            await car.async_apply(("vehicle", "charging"), "device", "AION V")     # fewer cards, same dashboard
            assert [view["path"] for view in board.saved["views"]] == ["car"]
            assert (await car.async_status())["cards"] == ("vehicle", "charging")

            assert await car.async_apply((), "device", "AION V")
            assert collection.deleted == ["id-1"] and boards == {}
            assert await car.store.async_load() is None and await car.async_status() is None
        finally:
            stop()
            await hass.async_stop(force=True)
    asyncio.run(run())


def test_an_edited_dashboard_is_never_changed_or_removed(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        boards, collection, stop = lovelace()
        try:
            car = VehicleDashboard(hass, "entry")
            await car.async_apply(EVERY, "device", "AION V")
            boards["gac-aion-v"].saved = {"views": [{"title": "Mine", "cards": []}]}
            assert (await car.async_status())["edited"] is True
            assert await car.async_apply(EVERY, "device", "AION V")         # the same choice: kept as edited
            for change in ((), ("vehicle",)):
                with pytest.raises(DashboardEdited):
                    await car.async_apply(change, "device", "AION V")
            assert collection.deleted == [] and boards["gac-aion-v"].saved["views"][0]["title"] == "Mine"
            # Removing the entry keeps an edited dashboard and forgets it.
            await async_remove_dashboard(hass, "entry")
            assert "gac-aion-v" in boards and await car.store.async_load() is None
        finally:
            stop()
            await hass.async_stop(force=True)
    asyncio.run(run())


def test_a_dashboard_the_owner_deleted_is_not_recreated(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        boards, collection, stop = lovelace()
        try:
            car = VehicleDashboard(hass, "entry")
            await car.async_apply(EVERY, "device", "AION V")
            boards.clear()
            assert await car.async_apply(EVERY, "device", "AION V") is False
            assert len(collection.created) == 1 and await car.store.async_load() is None

            entry = SimpleNamespace(entry_id="entry", title="AION V",
                                    options={"load_cards": True, "dashboard_cards": list(EVERY)})
            await car.async_apply(EVERY, "device", "AION V")
            boards.clear()
            hass.config_entries = Mock()
            with patch.object(dashboard, "async_want_cards", AsyncMock()):
                await async_apply_dashboard(hass, entry, "device")
            hass.config_entries.async_update_entry.assert_called_once_with(
                entry, options={"load_cards": True, "dashboard_cards": []})
        finally:
            stop()
            await hass.async_stop(force=True)
    asyncio.run(run())


def test_a_taken_path_gets_a_number_and_an_unedited_layout_follows_new_versions(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        theirs = Board("theirs", "gac-aion-v")
        boards, _, stop = lovelace({"gac-aion-v": theirs})
        try:
            car = VehicleDashboard(hass, "entry")
            await car.async_apply(EVERY, "device", "AION V")
            assert set(boards) == {"gac-aion-v", "gac-aion-v-2"} and theirs.saved is None
            old_layout = {"views": [{"cards": [{"type": "custom:gac-vehicle-card", "device": "device"}]}]}
            boards["gac-aion-v-2"].saved = old_layout
            owned = await car.store.async_load()
            await car.store.async_save({**owned, "config": old_layout})
            await car.async_apply(EVERY, "device", "AION V")
            assert boards["gac-aion-v-2"].saved == dashboard_config("device", "AION V", EVERY)
        finally:
            stop()
            await hass.async_stop(force=True)
    asyncio.run(run())


def test_removing_the_entry_removes_an_unedited_dashboard_and_its_record(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        boards, _, stop = lovelace()
        try:
            await VehicleDashboard(hass, "entry").async_apply(EVERY, "device", "AION V")
            await async_remove_dashboard(hass, "entry")
            assert boards == {} and not (tmp_path / ".storage" / dashboard.store_key("entry")).exists()
        finally:
            stop()
            await hass.async_stop(force=True)
    asyncio.run(run())


def test_the_chosen_cards_come_back_in_dashboard_order_only_once_installed():
    assert dashboard_cards({"load_cards": True, "dashboard_cards": ["settings", "vehicle"]}) == ("vehicle", "settings")
    assert dashboard_cards({}) == () and dashboard_cards({"load_cards": True, "dashboard_cards": None}) == ()
    assert dashboard_cards({"dashboard_cards": ["vehicle"]}) == ()
    assert dashboard_cards({"load_cards": False, "dashboard_cards": ["vehicle"]}) == ()


@pytest.mark.parametrize("options, loads", [
    ({}, False),
    ({"load_cards": False, "dashboard_cards": list(EVERY)}, False),
    ({"load_cards": True, "dashboard_cards": []}, True),
])
def test_nothing_is_added_to_the_pages_until_the_cards_are_installed(tmp_path, options, loads):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        hass.http = Mock(async_register_static_paths=AsyncMock())
        entry = SimpleNamespace(entry_id="entry", title="AION V", options=options)
        apply = AsyncMock(return_value=True)
        with patch.object(dashboard, "_available", lambda hass: True), \
             patch("homeassistant.components.frontend.add_extra_js_url") as added, \
             patch.object(VehicleDashboard, "async_apply", apply):
            await async_apply_dashboard(hass, entry, "device")
        assert added.called is loads and hass.http.async_register_static_paths.called is loads
        assert apply.await_args.args[0] == ()        # no generated dashboard without its cards
        await hass.async_stop(force=True)
    asyncio.run(run())


def test_the_bundle_loads_while_any_car_wants_the_cards(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        hass.http = Mock(async_register_static_paths=AsyncMock())
        added, removed = Mock(), Mock()
        with patch.object(dashboard, "_available", lambda hass: True), \
             patch("homeassistant.components.frontend.add_extra_js_url", added), \
             patch("homeassistant.components.frontend.remove_extra_js_url", removed):
            await async_want_cards(hass, "one", True)
            await async_want_cards(hass, "two", True)
            assert added.call_count == 1 and hass.http.async_register_static_paths.await_count == 1
            url = added.call_args.args[1]
            assert url.startswith("/gac_connect/frontend/gac-connect-cards.js?v=") and len(url.rsplit("=", 1)[1]) == 12
            await async_want_cards(hass, "one", False)
            removed.assert_not_called()
            await async_want_cards(hass, "two", False)
            removed.assert_called_once_with(hass, url)
            await async_want_cards(hass, "one", True)
            assert added.call_count == 2 and hass.http.async_register_static_paths.await_count == 1
        await hass.async_stop(force=True)
    asyncio.run(run())


def test_without_the_frontend_nothing_is_registered(tmp_path):
    async def run():
        hass = HomeAssistant(str(tmp_path))
        entry = SimpleNamespace(entry_id="entry", title="AION V",
                                options={"load_cards": True, "dashboard_cards": ["vehicle"]})
        with patch("homeassistant.components.frontend.add_extra_js_url") as added:
            await async_apply_dashboard(hass, entry, "device")
        added.assert_not_called()
        await hass.async_stop(force=True)
    asyncio.run(run())


def test_the_committed_bundle_and_its_fonts_ship_with_the_integration():
    folder = dashboard.FRONTEND_DIR
    assert len(list((folder / "fonts").glob("*.woff2"))) == 10 and (folder / "fonts" / "OFL.txt").exists()
    cards = (folder / dashboard.CARDS).read_text()
    for card in ("vehicle", "climate", "charging", "location", "activity", "settings"):
        assert f"gac-{card}-card" in cards
    # The loader every page loads is small, waits for Home Assistant, and loads the cards itself.
    loader = (folder / dashboard.BUNDLE).read_text()
    assert len(loader) < 1_000 and 'querySelector("home-assistant")' in loader and dashboard.CARDS in loader
    assert "customElements" not in loader


def test_the_configure_page_confirms_removal_and_leaves_an_edited_dashboard_alone(tmp_path):
    from custom_components.gac_connect.config_flow import GacOptionsFlow
    from test_autodetect import vehicle

    async def run():
        async with vehicle(tmp_path) as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, options={**entry.options, "dashboard": "cards",
                                                                   "load_cards": True,
                                                                   "dashboard_cards": list(EVERY)})
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            status = {"url_path": "gac-aion-ut", "cards": EVERY, "edited": False}
            with patch.object(dashboard, "_available", lambda hass: True), \
                 patch.object(VehicleDashboard, "async_status", AsyncMock(side_effect=lambda: status)):
                form = await flow.async_step_cards()
                assert form["description_placeholders"]["status"] == "This car's dashboard is at /gac-aion-ut."
                assert form["data_schema"]({}) == {"load_cards": True, "dashboard_cards": list(EVERY)}

                confirm = await flow.async_step_cards({"load_cards": True, "dashboard_cards": []})
                assert confirm["step_id"] == "confirm_remove_dashboard"
                assert confirm["description_placeholders"]["after"].startswith("The cards stay installed")
                again = await flow.async_step_confirm_remove_dashboard({"confirm": False})
                assert again["errors"] == {"base": "confirmation_required"}
                assert entry.options["dashboard_cards"] == list(EVERY)
                assert (await flow.async_step_confirm_remove_dashboard({"confirm": True}))["step_id"] == "init"
                assert entry.options["dashboard_cards"] == [] and "dashboard" not in entry.options
                assert entry.options["load_cards"] is True

                status["edited"] = True
                form = await flow.async_step_cards({"load_cards": True, "dashboard_cards": ["vehicle"]})
                assert form["errors"] == {"base": "dashboard_edited"} and entry.options["dashboard_cards"] == []
                assert "has been edited" in form["description_placeholders"]["status"]
    asyncio.run(run())


def test_uninstalling_the_cards_removes_the_dashboard_after_a_confirmation(tmp_path):
    from custom_components.gac_connect.config_flow import GacOptionsFlow
    from test_autodetect import vehicle

    async def run():
        async with vehicle(tmp_path) as (hass, entry, _):
            hass.config_entries.async_update_entry(entry, options={**entry.options, "load_cards": True,
                                                                   "dashboard_cards": list(EVERY)})
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            status = {"url_path": "gac-aion-ut", "cards": EVERY, "edited": False}
            with patch.object(dashboard, "_available", lambda hass: True), \
                 patch.object(VehicleDashboard, "async_status", AsyncMock(side_effect=lambda: status)):
                # The card list does not count once the cards are off.
                confirm = await flow.async_step_cards({"load_cards": False, "dashboard_cards": list(EVERY)})
                assert confirm["step_id"] == "confirm_remove_dashboard"
                assert "stop working on your own dashboards" in confirm["description_placeholders"]["after"]
                assert (await flow.async_step_confirm_remove_dashboard({"confirm": True}))["step_id"] == "init"
                assert entry.options["load_cards"] is False and entry.options["dashboard_cards"] == []

                status = None       # with no dashboard, the cards go back on without a question
                assert (await flow.async_step_cards({"load_cards": True}))["step_id"] == "init"
                assert entry.options["load_cards"] is True and entry.options["dashboard_cards"] == []
    asyncio.run(run())
