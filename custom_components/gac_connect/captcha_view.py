"""Serves the slide-puzzle page during the config flow and resumes it.

The config flow enters an external step pointing the browser at this view. The
page renders the puzzle images, the user drags the piece and presses Verify, and
the offset is POSTed back. On a correct slide the SMS is sent and the config flow
is resumed; a wrong slide swaps in a fresh puzzle without leaving the page.

Only the user solves the puzzle — nothing here measures the gap.
"""
from __future__ import annotations

from typing import Any

from aiohttp import web
from gac_connect.errors import CaptchaError, LoginError

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

CAPTCHA_URL = "/api/gac_connect/captcha"


def flow_state(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    return hass.data.setdefault(DOMAIN, {}).setdefault("flows", {})


_PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>GAC verification</title>
<style>body{font-family:system-ui,-apple-system,sans-serif;background:#111;color:#eee;display:flex;
flex-direction:column;align-items:center;gap:16px;padding:28px}.st{position:relative;width:310px;height:155px;
background:#000;border-radius:8px;overflow:hidden}.st img{position:absolute;top:0;left:0}input{width:310px}
button{font-size:16px;font-weight:700;padding:10px 24px;border:0;border-radius:9px;background:#2e7d32;color:#fff}
button:disabled{background:#444}.m{min-height:1.3em}.ok{color:#4ade80;font-weight:700}.bad{color:#f87171}
.x{font-size:30px;font-weight:800}</style>
<h3>Slide the piece into the gap</h3>
<div class=st><img id=b width=310 height=155><img id=p></div>
<input id=s type=range min=0 max=263 value=0><div class=x id=xv>0</div>
<button id=g>Verify</button><div class=m id=m>Drag into the gap, then Verify. Arrow keys nudge a pixel.</div>
<script>
const F=new URLSearchParams(location.search).get('flow_id');
const s=document.getElementById('s'),p=document.getElementById('p'),xv=document.getElementById('xv'),
b=document.getElementById('b'),g=document.getElementById('g'),m=document.getElementById('m');
let at=0,done=false;const u=()=>{p.style.left=s.value+'px';xv.textContent=s.value};s.oninput=u;
document.onkeydown=e=>{if(e.key=='ArrowRight'){s.value=+s.value+1;u()}if(e.key=='ArrowLeft'){s.value=+s.value-1;u()}};
async function poll(){if(done)return;const t=await(await fetch('?flow_id='+F+'&state=1',{headers:{accept:'application/json'}})).json();
if(t.attempt!=at){at=t.attempt;b.src='data:image/png;base64,'+t.bg;p.src='data:image/png;base64,'+t.piece;s.value=0;u();g.disabled=false;if(at>1)m.innerHTML='<span class=bad>Not quite — new puzzle (try '+at+').</span>'}
if(t.status=='ok'){done=true;g.disabled=true;m.innerHTML='<span class=ok>Verified ✓</span> return to Home Assistant.';return}
if(t.status=='failed'){done=true;g.disabled=true;m.innerHTML='<span class=bad>'+t.msg+'</span>';return}
setTimeout(poll,500)}
g.onclick=async()=>{g.disabled=true;m.textContent='Checking…';
await fetch('?flow_id='+F,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({x:+s.value})})};
poll();</script>"""


class GacCaptchaView(HomeAssistantView):
    url = CAPTCHA_URL
    name = "api:gac_connect:captcha"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        flow_id = request.query.get("flow_id")
        state = flow_state(hass).get(flow_id)
        if not state:
            return web.Response(status=404, text="expired")
        if request.query.get("state"):
            return web.json_response(_public(state))
        return web.Response(text=_PAGE, content_type="text/html")

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        flow_id = request.query.get("flow_id")
        state = flow_state(hass).get(flow_id)
        if not state:
            return web.json_response({"ok": False}, status=404)
        try:
            x = int((await request.json()).get("x"))
        except (ValueError, TypeError):
            return web.json_response({"ok": False}, status=400)

        client = state["client"]
        try:
            await client.request_sms(state["mobile"], x)
        except (CaptchaError, LoginError):
            # wrong slide (or a bad ticket) — hand back a fresh puzzle
            state["captcha"] = await client.start_captcha()
            state["attempt"] += 1
            return web.json_response({"ok": False, "retry": True})
        state["status"] = "ok"
        hass.async_create_task(
            hass.config_entries.flow.async_configure(flow_id=flow_id, user_input={})
        )
        return web.json_response({"ok": True})


def _public(state: dict[str, Any]) -> dict[str, Any]:
    c = state["captcha"]
    return {
        "attempt": state["attempt"],
        "status": state.get("status", "pending"),
        "msg": state.get("msg", ""),
        "bg": c.background,
        "piece": c.piece,
    }
