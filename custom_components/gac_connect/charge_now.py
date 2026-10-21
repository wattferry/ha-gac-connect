"""Charge now, which also starts a new charge once one has ended.

GAC has no start command. Charge now switches the schedule off and the car charges
whenever a charge begins (plugging in, the supply coming on), but once a charge has ended
(a one-time window finished, the connector was unlocked) that alone does not start another.
Then a one-time window to the charge limit is sent, starting at the next minute, and the
schedule is switched off once charging has begun, which keeps it going past that window
(Aion UT, 2026-10-17). A repeating schedule is never replaced this way.
"""
from __future__ import annotations

import asyncio
import logging
from time import monotonic

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from gac_connect.errors import GacError
from gac_connect.models import restart_needed
from .command_tracking import async_send, charging_generation, charging_requests

_LOGGER = logging.getLogger(__name__)
# Reads after the restart window is sent, in seconds. It starts 30-90 s later and the car
# reported charging about two and a half minutes after it was sent.
RESTART_READS = (60, 90, 120, 150, 180, 240, 300)


def charge_now_request(coordinator, *, until_soc: bool = False):
    """The Charge now request to send through the command ledger."""
    helper = getattr(getattr(coordinator.config_entry, "runtime_data", None), "charge_now", None)
    if helper is None:
        return coordinator.client.charge_now(coordinator.vin, until_soc=until_soc)
    return helper.request(until_soc=until_soc)


class ChargeNow:
    def __init__(self, coordinator) -> None:
        self._coordinator = coordinator
        self._charging = asyncio.Event()
        self._claimed = False             # set before the restart is sent, so presses cannot both send it
        self._generation: int | None = None     # the charging choice the follow-up belongs to
        self._until_soc = False
        self._task: asyncio.Task | None = None

    @property
    def restarting(self) -> bool:
        return self._claimed

    @callback
    def observe(self, status) -> None:
        if self.restarting and getattr(status, "charging", None) is True:
            self._charging.set()

    def _still_wanted(self) -> bool:
        return charging_requests(self._coordinator).generation == self._generation

    def _given_up(self) -> bool:
        """A different charging choice was made; another Charge now joins this one when its turn comes."""
        requests = charging_requests(self._coordinator)
        return requests.generation != self._generation and requests.latest != "charge-now"

    def _own_generation(self) -> int:
        mine = charging_generation()     # set while this request is being sent through async_send
        return charging_requests(self._coordinator).generation if mine is None else mine

    async def request(self, *, until_soc: bool = False):
        coordinator = self._coordinator
        client, vin = coordinator.client, coordinator.vin
        if self._claimed:
            # Charge now again: the follow-up now belongs to this, the latest choice, and
            # switches the schedule off with its stopping rule. Nothing more is sent now.
            self._generation, self._until_soc = self._own_generation(), until_soc
            _LOGGER.info("Charge now: already starting a new charge; nothing more sent")
            return None
        if not restart_needed(coordinator.data):
            return await client.charge_now(vin, until_soc=until_soc)
        self._claimed = True
        self._generation, self._until_soc = self._own_generation(), until_soc     # before anything is awaited
        self._charging.clear()
        try:
            started = monotonic()
            response = await client.restart_charging(vin)
        except BaseException:
            self._claimed = False
            raise
        _LOGGER.info("Charge now: the car's charge had ended, so a one-time window to the charge limit "
                     "starts a new one; the schedule switches off once charging begins")
        runtime = coordinator.config_entry.runtime_data
        if (draft := getattr(runtime, "charge_draft", None)) is not None:
            draft.mark_sent(None, None, 0, True)     # the dashboard's draft is not this window
        self._task = coordinator.config_entry.async_create_background_task(
            coordinator.hass, self._follow(started), "gac_connect charge now")
        return response

    async def _follow(self, started: float) -> None:
        coordinator = self._coordinator
        try:
            for at in RESTART_READS:
                if self._given_up():
                    break
                try:
                    async with asyncio.timeout(max(0.0, started + at - monotonic())):
                        await self._charging.wait()
                except TimeoutError:
                    await coordinator.async_refresh_now()
                if self._charging.is_set():
                    break
            if self._given_up():
                _LOGGER.info("Charge now: another charging request followed, so the schedule is left as it is")
                return
            if not self._charging.is_set():
                _LOGGER.info("Charge now: the car did not report charging; switching the schedule off anyway")
            try:
                sent = await async_send(coordinator, "charge-now",
                                        lambda: coordinator.client.charge_now(coordinator.vin,
                                                                              until_soc=self._until_soc),
                                        still_wanted=self._still_wanted)
            except (GacError, HomeAssistantError) as err:
                _LOGGER.warning("Charge now could not switch the schedule off after starting the charge: %s", err)
                return
            if sent is None:
                _LOGGER.info("Charge now: another charging request followed, so the schedule is left as it is")
        finally:
            self._claimed = False
