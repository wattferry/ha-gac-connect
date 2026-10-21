"""Group entities by whether they are shown and why, without probing the car."""
import asyncio
import re
from types import SimpleNamespace

from custom_components.gac_connect.api import decode_status
from custom_components.gac_connect.config_flow import GacOptionsFlow
from custom_components.gac_connect.entity_filter import OMIT_OPTIONS
from custom_components.gac_connect.equipment import equipment_summary
from test_autodetect import vehicle


def groups(text):
    """Heading -> items, from the summary's markdown."""
    found = {}
    for block in text.split("\n\n**")[0:]:
        heading, _, items = block.strip("*").partition("**\n\n")
        found[heading] = items.split("\n")
    return found


def test_entities_are_grouped_by_reason_with_short_details(tmp_path):
    async def run():
        async with vehicle(tmp_path, model='Aion UT', options={
            'enable_entities': ['button:horn'], 'omit_entities': ['sensor:pm25'],
        }) as (hass, entry, c):
            c.capabilities.observe(decode_status({'steeringAccessors': [{'steering': 0}]}))
            c.capabilities.confirm_command('sunroof-close')
            before = dict(entry.options)
            flow = GacOptionsFlow()
            flow.hass, flow.handler = hass, entry.entry_id
            menu = await flow.async_step_init()
            assert menu['type'] == 'menu' and 'equipment' in menu['menu_options']
            page = await flow.async_step_equipment()
            text = page['description_placeholders']['equipment']
            found = groups(text)
            assert list(found) == ['Your choices (Vehicle settings)', "Shown (seen in the car's reports, unless noted)",
                                   "Hidden (not seen in the car's reports yet, unless noted)"]
            assert found['Your choices (Vehicle settings)'] == [
                '- Sound horn (sounds the horn): always shown; otherwise hidden',
                '- Cabin PM2.5 (µg/m³): omitted; would be hidden anyway',
            ]
            assert found["Shown (seen in the car's reports, unless noted)"] == [
                '- Steering wheel heat (on/off)', '- Sunroof (open/close) — a command to it succeeded']
            hidden = found["Hidden (not seen in the car's reports yet, unless noted)"]
            assert '- Climate (Off, On, Fan only; 18–32 °C; fan 1–7; 4 airflow choices; Heating and Cooling presets)' in hidden
            assert '- Tyre 1 pressure (kPa) — not fitted to this model' in hidden
            assert '- Fridge mode (Off, Refrigerate, Heat, Freeze) — not fitted to this model' in hidden
            assert '- Location (home/away and map) — location tracking is off' in hidden
            assert sum(len(items) for items in found.values()) == len(OMIT_OPTIONS)   # every entity, once
            assert 'VIN' not in text and not re.search(r'[.!?] [A-Z][a-z]+ [a-z]+ [a-z]+', text)   # no prose
            assert (await flow.async_step_equipment({}))['type'] == 'menu'
            assert dict(entry.options) == before
            c.client.command.assert_not_called()
            c.client.get_status.assert_not_called()
    asyncio.run(run())


def test_every_decision_matches_what_is_shown(tmp_path):
    async def run():
        async with vehicle(tmp_path, model='Aion UT') as (_, _, c):
            for key in OMIT_OPTIONS:
                assert c.capabilities.decision(key)[0] is c.capabilities.includes(key), key
    asyncio.run(run())


def test_an_unloaded_vehicle_says_so():
    entry = SimpleNamespace(data={'model': 'Aion UT'}, options={})
    assert equipment_summary(entry) == 'The vehicle is not loaded. Reconnect it to see its equipment.'
