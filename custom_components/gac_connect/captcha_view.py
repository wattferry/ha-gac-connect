"""Serves the library's slide-puzzle page during the config flow and resumes it.

The config flow enters an external step pointing the browser at this view, which
serves the page and its state and hands each Verify to the flow's PuzzleSession
(library ``puzzle``): a correct slide sends the SMS and resumes the config flow; a
wrong slide swaps in a fresh puzzle without leaving the page.

Only the user solves the puzzle — nothing here measures the gap.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from aiohttp import web

from gac_connect import puzzle
from gac_connect.puzzle import PuzzleSession

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import UnknownFlow

from .const import DOMAIN

CAPTCHA_URL = "/api/gac_connect/captcha"
CAPTCHA_SECONDS = 600


def flow_state(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    return hass.data.setdefault(DOMAIN, {}).setdefault("flows", {})


def discard_flow_state(hass: HomeAssistant, flow_id: str) -> None:
    state = flow_state(hass).pop(flow_id, None)
    task = state.get("verification_task") if state else None
    if task is not None and task is not asyncio.current_task() and not task.done():
        task.cancel()


def active_flow_state(hass: HomeAssistant, flow_id: str | None) -> dict | None:
    state = flow_state(hass).get(flow_id)
    if state is None:
        return None
    try:
        active = hass.config_entries.flow.async_get(flow_id)
    except UnknownFlow:
        active = None
    if not active or time.monotonic() >= state["expires"]:
        discard_flow_state(hass, flow_id)
        return None
    return state


class GacCaptchaView(HomeAssistantView):
    url = CAPTCHA_URL
    name = "api:gac_connect:captcha"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        flow_id = request.query.get("flow_id")
        state = active_flow_state(hass, flow_id)
        if not state:
            return web.Response(status=404, text="expired")
        if request.query.get("state"):
            return web.json_response(state["session"].state())
        return web.Response(text=puzzle.page("Home Assistant"), content_type="text/html")

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        flow_id = request.query.get("flow_id")
        state = active_flow_state(hass, flow_id)
        if not state:
            return web.json_response({"ok": False}, status=404)
        try:
            data = await request.json()
            x = puzzle.offset(data.get("x") if isinstance(data, dict) else None)
        except (ValueError, TypeError):
            return web.json_response({"ok": False}, status=400)

        # Reading the body yielded control: the flow may have been canceled.
        if active_flow_state(hass, flow_id) is not state:
            return web.json_response({"ok": False}, status=404)

        session: PuzzleSession = state["session"]
        if session.busy:     # another Verify is being checked; it alone owns the cancellable task
            return web.json_response({"ok": False, "busy": True}, status=409)
        task = state["verification_task"] = asyncio.current_task()
        try:
            result = await session.submit(x)
        finally:
            if state.get("verification_task") is task:
                state.pop("verification_task", None)
        if result.get("verified") and active_flow_state(hass, flow_id) is state:
            # the SMS has just been sent, and the sign-in is still open: on to the code
            hass.async_create_task(hass.config_entries.flow.async_configure(flow_id=flow_id, user_input={}))
        return web.json_response(result)
