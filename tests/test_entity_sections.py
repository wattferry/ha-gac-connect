"""Each entity sits in the device page section that suits it."""
from homeassistant.const import EntityCategory

from custom_components.gac_connect.binary_sensor import BINARY_SENSORS
from custom_components.gac_connect.button import BUTTONS, GacRefreshButton
from custom_components.gac_connect.sensor import ACTIVITY_SENSORS, FRIDGE_SENSORS, SENSORS, GacActivitySensor, _tyre_sensors
from test_regressions import coord

DIAGNOSTIC = {
    # how fresh and healthy the cloud connection is
    "sensor:last_report", "binary_sensor:online",
    # secondary readings already shown by a control
    "sensor:ac_fan_strength", "binary_sensor:ac_auto", "binary_sensor:ac_compressor",
    *(f"binary_sensor:seat_{i}_ventilation" for i in range(1, 5)),
    "sensor:charge_window_start", "sensor:charge_window_stop", "binary_sensor:charger_locked",
    # a setting made in the car
    "sensor:fridge_keep_mode",
}


def test_readings_are_sensors_and_connection_details_are_diagnostic():
    entities = {f"sensor:{d.key}": d for d in (*SENSORS, *_tyre_sensors(), *FRIDGE_SENSORS)}
    entities |= {f"binary_sensor:{d.key}": d for d in BINARY_SENSORS}
    for key, description in entities.items():
        expected = EntityCategory.DIAGNOSTIC if key in DIAGNOSTIC else None
        assert description.entity_category is expected, key
    c = coord(None)
    assert {d.key for d in ACTIVITY_SENSORS} == {"last_command", "data_freshness", "last_refresh", "polling_status"}
    assert all(GacActivitySensor(c, d).entity_category is EntityCategory.DIAGNOSTIC for d in ACTIVITY_SENSORS)
    assert GacRefreshButton(c).entity_category is EntityCategory.DIAGNOSTIC
    assert all(d.entity_category is None for d in BUTTONS)                       # car controls stay in Controls
