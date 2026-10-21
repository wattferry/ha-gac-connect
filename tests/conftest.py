import pytest


@pytest.fixture(autouse=True)
def _no_result_poll_waits(monkeypatch):
    """Commands sent without a push channel poll for the car's answer; tests do not wait for it."""
    monkeypatch.setattr("custom_components.gac_connect.command_tracking.POLL_DELAYS", (0, 0, 0))


@pytest.fixture(autouse=True)
def _release_stopped_home_assistant():
    """Drop HA's process-wide caches of a test's instance once the test ends.

    Several helpers cache the instance they were first called with for the whole process.
    Left there, a stopped instance survives to interpreter exit, where Python 3.14 has
    crashed tearing it down (exit 139 after every test had passed).
    """
    yield
    from importlib import import_module

    for module, name in (("homeassistant.helpers.entity_registry", "async_get"),
                         ("homeassistant.helpers.area_registry", "async_get"),
                         ("homeassistant.helpers.floor_registry", "async_get"),
                         ("homeassistant.helpers.label_registry", "async_get"),
                         ("homeassistant.helpers.issue_registry", "async_get"),
                         ("homeassistant.helpers.category_registry", "async_get"),
                         ("homeassistant.helpers.restore_state", "async_get"),
                         ("homeassistant.helpers.recorder", "get_instance"),
                         ("homeassistant.helpers.translation", "_async_get_translations_cache")):
        try:
            cached = getattr(import_module(module), name)
        except (ImportError, AttributeError):
            continue          # not in this Home Assistant release
        clear = getattr(cached, "cache_clear", None)
        if clear is not None:
            clear()
    current = getattr(import_module("homeassistant.core"), "_hass", None)    # the "current instance" slot
    if current is not None and hasattr(current, "hass"):
        current.hass = None


@pytest.fixture(autouse=True)
def _detach_request_limiter():
    """The bundled library's limiter is process-wide; a test's storage callback must not outlive it."""
    yield
    from gac_connect.limits import DEFAULT_LIMITER

    DEFAULT_LIMITER.on_change = None


def pytest_sessionfinish(session, exitstatus):
    """Clear every remaining Home Assistant cache before the interpreter tears its modules down."""
    import sys

    for name, module in list(sys.modules.items()):
        if not name.startswith("homeassistant") or module is None:
            continue
        for value in list(vars(module).values()):
            clear = getattr(value, "cache_clear", None)
            if callable(clear) and hasattr(value, "cache_info"):
                clear()
