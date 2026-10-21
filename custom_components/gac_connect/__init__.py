"""GAC Connect (unofficial) — Home Assistant integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gac_connect.client import GacClient


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from gac_connect.errors import GacError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import slugify
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .charge_now import ChargeNow
from .account_alerts import AccountAlerts, store_key as account_alerts_store_key
from .cabin import controller as cabin_controller
from .capabilities import FRIDGE_ENTITIES, store_key as capabilities_store_key
from .const import (
    CONF_DASHBOARD_CARDS, CONF_ENABLE_FRIDGE, CONF_LOAD_CARDS, CONF_MODEL, CONF_OMIT_ENTITIES, CONF_PROFILE,
    CONF_REGION, CONF_VIN,
    DOMAIN, PLATFORMS,
)
from .dashboard import async_apply_dashboard, async_remove_dashboard, async_want_cards
from .coordinator import GacCoordinator
from .session_store import ConfigEntryStore
from .settings import ChargeDraft, async_options_applied, needs_reload
from .entity_filter import apply_registry_choices
from .fridge import FridgeController, store_key
from .helpers import async_build_client
from .statistics import async_setup_cleanup

type GacConfigEntry = ConfigEntry[GacRuntime]


@dataclass
class GacRuntime:
    client: GacClient
    coordinator: GacCoordinator
    options: dict = field(default_factory=dict)  # snapshot: reload only when these change
    fridge: FridgeController | None = None
    alerts: AccountAlerts | None = None
    charge_draft: ChargeDraft | None = None
    charge_now: ChargeNow | None = None


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Watch permanent sensor removals even while vehicle entries are unloaded."""
    async_setup_cleanup(hass)
    return True


# What the removed Aion UT profile omitted on its own; the car's capability list decides these now.
_UT_PROFILE_OMISSIONS = frozenset({
    "switch:steering_heat", "cover:sunroof", "binary_sensor:seat_3_ventilation", "binary_sensor:seat_4_ventilation",
    *(f"sensor:tyre_{i}_{kind}" for i in range(1, 5) for kind in ("pressure", "temp")),
})


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """1.2: vehicle profiles were removed; detection decides, and the owner's own choices stay.

    1.3: Unrestricted charging became Scheduled charging, with on and off swapped, so its
    default entity ID follows the new meaning. A custom ID is left alone.

    1.4: the Fridge / warmer box controls option was removed (the capability list decides);
    an owner's Off becomes Omit for each fridge entity.

    1.5: Battery preconditioning took the app's name, Smart battery temp, and its default
    entity ID follows. A custom ID is left alone.

    1.6: Pre-conditioning became A/C, as it shows the A/C however it was started; its
    default entity ID follows. A custom ID is left alone.

    1.7: the dashboard cards arrived; an existing car gets no dashboard it did not ask for.

    1.8: loading the cards became the owner's choice, off by default. A car that already had
    the cards (1.7) keeps them loaded; an older one gets them only when the owner turns them on.
    """
    had_cards = entry.version == 1 and entry.minor_version >= 7
    if entry.version == 1 and entry.minor_version < 2:
        options = dict(entry.options)
        profile = options.pop(CONF_PROFILE, None)
        model = str(entry.data.get(CONF_MODEL) or "").strip().casefold()
        if profile == "aion_ut" or (profile is None and (model == "aion ut" or model.startswith("aion ut "))):
            options[CONF_OMIT_ENTITIES] = sorted(set(options.get(CONF_OMIT_ENTITIES, ())) - _UT_PROFILE_OMISSIONS)
            options[CONF_ENABLE_FRIDGE] = True
        hass.config_entries.async_update_entry(entry, options=options, minor_version=2)
    if entry.version == 1 and entry.minor_version < 3:
        _rename_default_id(hass, entry, "charge_switch", "_unrestricted_charging", "_scheduled_charging")
        hass.config_entries.async_update_entry(entry, minor_version=3)
    if entry.version == 1 and entry.minor_version < 4:
        options = dict(entry.options)
        if options.pop(CONF_ENABLE_FRIDGE, None) is False:
            options[CONF_OMIT_ENTITIES] = sorted(set(options.get(CONF_OMIT_ENTITIES, ())) | FRIDGE_ENTITIES)
        hass.config_entries.async_update_entry(entry, options=options, minor_version=4)
    if entry.version == 1 and entry.minor_version < 5:
        _rename_default_id(hass, entry, "precondition_battery", "_battery_preconditioning", "_smart_battery_temp")
        hass.config_entries.async_update_entry(entry, minor_version=5)
    if entry.version == 1 and entry.minor_version < 6:
        _rename_default_id(hass, entry, "climate_power", "_pre_conditioning", "_a_c")
        hass.config_entries.async_update_entry(entry, minor_version=6)
    if entry.version == 1 and entry.minor_version < 7:
        # Dashboard cards arrived: an existing car gets the cards, but no dashboard it did not ask for.
        hass.config_entries.async_update_entry(
            entry, options={CONF_DASHBOARD_CARDS: [], **entry.options}, minor_version=7)
    if entry.version == 1 and entry.minor_version < 8:
        hass.config_entries.async_update_entry(
            entry, options={CONF_LOAD_CARDS: had_cards, **entry.options}, minor_version=8)
    return True


def _rename_default_id(hass: HomeAssistant, entry: ConfigEntry, key: str, old: str, new: str) -> None:
    """Give a switch that still has its default entity ID (the vehicle device's name and the old
    ending ``old``) the ending ``new``, unless that ID is taken. Any other ID is the owner's
    choice and is left alone, even one that ends the same way."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, f"{entry.data[CONF_VIN]}_{key}")
    if not entity_id:
        return
    device = dr.async_get(hass).async_get(registry.async_get(entity_id).device_id or "")
    names = (device.name, device.name_by_user) if device is not None else ()
    defaults = {f"switch.{slugify(name)}{old}" for name in names if name}
    if entity_id in defaults:
        renamed = entity_id.removesuffix(old) + new
        if registry.async_get(renamed) is None:
            registry.async_update_entity(entity_id, new_entity_id=renamed)


async def async_setup_entry(hass: HomeAssistant, entry: GacConfigEntry) -> bool:
    # Isolated session: this login's cookies must not mix with other integrations.
    http = async_create_clientsession(hass)
    client = await async_build_client(hass, entry.data[CONF_REGION], http, ConfigEntryStore(hass, entry))
    try:
        await client.load()
    except GacError as err:
        raise ConfigEntryNotReady(str(err)) from err

    _remove_retired_entities(hass, entry)
    coordinator = GacCoordinator(hass, entry, client)
    await coordinator.capabilities.async_load()
    await coordinator.async_config_entry_first_refresh()
    await coordinator.capabilities.async_read_capability_list_once(client, coordinator.vin)

    entry.runtime_data = GacRuntime(client=client, coordinator=coordinator, options=dict(entry.options))
    apply_registry_choices(hass, entry)
    cabin_controller(coordinator).async_setup(entry)
    entry.runtime_data.fridge = FridgeController(hass, entry, coordinator)
    await entry.runtime_data.fridge.async_setup(entry)
    entry.runtime_data.alerts = AccountAlerts(hass, entry, coordinator)
    await entry.runtime_data.alerts.async_setup()
    draft = entry.runtime_data.charge_draft = ChargeDraft()
    draft.observe(coordinator.data)
    entry.async_on_unload(coordinator.async_add_listener(lambda: draft.observe(coordinator.data)))
    charge_now = entry.runtime_data.charge_now = ChargeNow(coordinator)
    entry.async_on_unload(coordinator.async_add_listener(lambda: charge_now.observe(coordinator.data)))
    coordinator.start_push()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_on_update))
    await async_apply_dashboard(hass, entry, _device_id(hass, entry))

    _register_services(hass)
    return True


# unique-id suffixes of entities earlier versions created and later versions replaced
_RETIRED: tuple[tuple[str, str], ...] = (
    ("button", "flash_lights"),
    ("button", "precondition_battery"),        # now a switch
    ("button", "charge_pause"),                # the car has no pause; Scheduled charging on is one
    ("switch", "seat_1_ventilation"), ("switch", "seat_2_ventilation"),   # now level selects
)


def _remove_retired_entities(hass: HomeAssistant, entry: GacConfigEntry) -> None:
    registry = er.async_get(hass)
    for domain, suffix in _RETIRED:
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{entry.data[CONF_VIN]}_{suffix}")
        if entity_id:
            registry.async_remove(entity_id)


def _device_id(hass: HomeAssistant, entry: GacConfigEntry) -> str | None:
    wanted = (DOMAIN, entry.data[CONF_VIN])
    return next((device.id for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
                 if wanted in device.identifiers), None)


async def async_unload_entry(hass: HomeAssistant, entry: GacConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.coordinator.capabilities.async_close()
        await async_want_cards(hass, entry.entry_id, False)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: GacConfigEntry) -> None:
    """Remove this entry's statistics, credentials, preferences and equipment."""
    from homeassistant.helpers.storage import Store

    async_setup_cleanup(hass).async_remove_entry(entry)
    await Store(hass, 1, store_key(entry.entry_id)).async_remove()
    await Store(hass, 1, capabilities_store_key(entry.entry_id)).async_remove()
    await Store(hass, 1, account_alerts_store_key(entry.entry_id)).async_remove()
    await ConfigEntryStore(hass, entry).remove()
    await async_remove_dashboard(hass, entry.entry_id)


async def _reload_on_update(hass: HomeAssistant, entry: GacConfigEntry) -> None:
    # The token store writes refreshed tokens into entry.data; that must not
    # bounce the integration (it would close the session under a running poll).
    runtime = getattr(entry, "runtime_data", None)
    if runtime is not None and dict(entry.options) == runtime.options:
        return
    if runtime is not None and not needs_reload(runtime.options, entry.options):
        dashboard_changed = any(runtime.options.get(key) != entry.options.get(key)
                                for key in (CONF_LOAD_CARDS, CONF_DASHBOARD_CARDS))
        runtime.options = dict(entry.options)      # read when needed: applies without a reload
        async_options_applied(hass, entry)
        if dashboard_changed:
            await async_apply_dashboard(hass, entry, _device_id(hass, entry))
        return
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(hass: HomeAssistant) -> None:
    # Registered lazily on first entry; imported here to keep module load light.
    from .services import async_register_services

    async_register_services(hass)
