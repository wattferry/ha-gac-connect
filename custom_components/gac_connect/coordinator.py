"""Polling coordinator and the config-entry token store."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from gac_connect import GacError
from gac_connect.client import GacClient
from gac_connect.errors import AuthExpiredError, RateLimitedError
from gac_connect.models import VehicleStatus
from gac_connect.session import Session

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_SCAN_INTERVAL,
    CONF_SESSION,
    CONF_VIN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ConfigEntryStore:
    """Persist the session in the config entry so tokens survive restarts."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry

    async def load(self) -> Session:
        return Session.from_dict(self._entry.data.get(CONF_SESSION))

    async def save(self, session: Session) -> None:
        self._hass.config_entries.async_update_entry(
            self._entry, data={**self._entry.data, CONF_SESSION: session.to_dict()}
        )


def _parse_hhmm(value: str | None) -> time | None:
    if not value:
        return None
    try:
        h, m = (int(x) for x in value.split(":"))
        return time(hour=h, minute=m)
    except (ValueError, AttributeError):
        return None


class GacCoordinator(DataUpdateCoordinator[VehicleStatus]):
    """Polls one vehicle's status."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GacClient) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data[CONF_VIN][-4:]}",
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )
        self.client = client
        self.vin = entry.data[CONF_VIN]

    def _in_quiet_hours(self) -> bool:
        start = _parse_hhmm(self.config_entry.options.get(CONF_QUIET_START))
        end = _parse_hhmm(self.config_entry.options.get(CONF_QUIET_END))
        if not start or not end:
            return False
        now = datetime.now().time()
        if start <= end:
            return start <= now < end
        return now >= start or now < end  # window crosses midnight

    async def _async_update_data(self) -> VehicleStatus:
        # During quiet hours, keep the last reading instead of waking the car.
        if self._in_quiet_hours() and self.data is not None:
            return self.data
        try:
            return await self.client.get_status(self.vin)
        except AuthExpiredError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RateLimitedError as err:
            raise UpdateFailed(str(err)) from err  # retry_after handled by HA if set
        except GacError as err:
            raise UpdateFailed(str(err)) from err
