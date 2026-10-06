#!/usr/bin/env python3
"""The configurator: shows the keys as the deck draws them and lets you assign each one.

Inside Home Assistant it opens in the sidebar (ingress) and only answers the ingress proxy;
Home Assistant handles the login. On a computer it listens on 127.0.0.1 only.
Saving writes the key layout; the deck picks it up without a restart.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import time
from pathlib import Path

import yaml
from aiohttp import web
from PIL import Image

import credentials
import home_assistant
import layout as layout_file
import render
import texts
import track_time
from settings import DEFAULT_LAYOUT, Options, Paths

STATIC = Path(__file__).resolve().parent / "static"
INGRESS_PROXY = "172.30.32.2"
LOOPBACK = ("127.0.0.1", "::1")
DEFAULT_DEVICE = {"type": "Stream Deck Neo", "keys": 8, "rows": 2, "cols": 4, "screen": [248, 58], "connected": False}
KINDS = {"entity", "track_time_toggle", "track_time_stop", "page", "empty", "timetracker_start", "timetracker_stop"}


def safe_name(name: str) -> str:
    return re.sub(r"[^\w\- ]", "", name or "", flags=re.UNICODE).strip()[:60] or "profile"


def check_layout(layout) -> str:
    """Empty string if the layout can be saved, else what is wrong."""
    if not isinstance(layout, dict):
        return "layout must be an object"
    pages = layout.get("pages", [])
    if not isinstance(pages, list):
        return "pages must be a list"
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("buttons", []), list):
            return "every page needs a list of buttons"
        for button in page.get("buttons", []):
            if not isinstance(button, dict) or button.get("kind", "entity") not in KINDS:
                return "unknown key kind: %r" % (button.get("kind") if isinstance(button, dict) else button)
    return ""


def write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    os.replace(temporary, path)


def icon_search(query: str, names: list, limit: int) -> list:
    """Exact names first, then names starting with a term, then names containing it."""
    terms = texts.icon_search_terms(query)
    exact, prefix, contains = [], [], []
    for name in names:
        for term in terms:
            if name == term:
                exact.append(name)
            elif name.startswith(term):
                prefix.append(name)
            elif term in name:
                contains.append(name)
            else:
                continue
            break
    return (exact + prefix + contains)[:limit]


class Backend:
    """Everything the configurator reads from Home Assistant and Track Time, briefly cached."""

    def __init__(self, options: Options, connection, supervisor_token="", track_time_key=""):
        self.options = options
        self.connection = connection
        self.supervisor_token = supervisor_token
        self.track_time_key = track_time_key
        self._states, self._states_at = {}, 0.0
        self._language, self._language_at = None, 0.0
        self._track_time, self._track_time_at = None, -1e9

    async def states(self) -> dict:
        if self.connection and time.time() - self._states_at > 3:
            result = await home_assistant.fetch_json(self.connection, "/states")
            if result is not None:
                self._states = {item["entity_id"]: item for item in result}
                self._states_at = time.time()
        return self._states

    async def language(self) -> str:
        if self._language is None or time.time() - self._language_at > 300:
            config = await home_assistant.fetch_json(self.connection, "/config") if self.connection else None
            self._language = texts.pick_language(self.options.language, (config or {}).get("language", ""))
            self._language_at = time.time()
        return self._language

    async def track_time_state(self) -> dict:
        if self._track_time is None and time.time() - self._track_time_at > 60:
            self._track_time_at = time.time()
            self._track_time = await asyncio.to_thread(
                track_time.connect, self.options, self.supervisor_token, self.track_time_key)
        if self._track_time is None:
            return dict(track_time.OFFLINE)
        return await asyncio.to_thread(self._track_time.state)


def build_app(paths: Paths, backend: Backend, allowed=(INGRESS_PROXY,)) -> web.Application:

    @web.middleware
    async def only_allowed(request, handler):
        if request.remote not in allowed:
            return web.json_response({"ok": False, "error": "forbidden"}, status=403)
        return await handler(request)

    app = web.Application(middlewares=[only_allowed], client_max_size=2 * 1024 * 1024)

    def load_layout() -> dict:
        return layout_file.load(paths.layout, DEFAULT_LAYOUT)

    def save_layout(layout: dict) -> None:
        write_atomically(paths.layout, yaml.safe_dump(layout, allow_unicode=True, sort_keys=False))

    def png(image, cache="no-store"):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return web.Response(body=buffer.getvalue(), content_type="image/png", headers={"Cache-Control": cache})

    async def index(request):
        return web.FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})

    async def get_layout(request):
        return web.json_response(load_layout())

    async def post_layout(request):
        try:
            layout = await request.json()
        except ValueError:
            return web.json_response({"ok": False, "error": "not JSON"}, status=400)
        problem = check_layout(layout)
        if problem:
            return web.json_response({"ok": False, "error": problem}, status=400)
        save_layout(layout)
        return web.json_response({"ok": True})

    async def get_states(request):
        result = []
        for entity_id, entity in (await backend.states()).items():
            attributes = entity.get("attributes") or {}
            result.append({"entity_id": entity_id, "state": entity.get("state"),
                           "name": attributes.get("friendly_name", entity_id), "domain": entity_id.split(".", 1)[0],
                           "unit": attributes.get("unit_of_measurement", ""),
                           "percentage_step": attributes.get("percentage_step")})
        result.sort(key=lambda item: (item["domain"], str(item["name"]).lower()))
        return web.json_response(result)

    async def preview(request):
        try:
            index_, page = int(request.query.get("index", "0")), int(request.query.get("page", "0"))
        except ValueError:
            return web.json_response({"ok": False, "error": "index and page must be numbers"}, status=400)
        pages = layout_file.pages_of(load_layout())
        buttons = pages[page].get("buttons", []) if 0 <= page < len(pages) else []
        button = buttons[index_] if 0 <= index_ < len(buttons) else {"kind": "empty"}
        tt_state = await backend.track_time_state() if render.kind_of(button).startswith("track_time") else None
        image = render.render_button(button, await backend.states(), tt_state, await backend.language(), out_size=96)
        return png(image)

    async def screen_preview(request):
        image = render.render_screen(load_layout().get("screen") or {}, await backend.states(),
                                     language=await backend.language())
        return png(image)

    async def get_track_time(request):
        return web.json_response(await backend.track_time_state())

    async def icon(request):
        name = request.query.get("name", "").strip() or "help-circle"
        color = request.query.get("color", "#e9eaec")
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        try:
            render.draw_icon(image, name, color, size=56, center=(32, 33))
        except ValueError:
            render.draw_icon(image, name, "#e9eaec", size=56, center=(32, 33))
        return png(image, cache="public, max-age=86400")

    async def icons(request):
        query = request.query.get("q", "").strip().lower().replace("mdi:", "")
        try:
            limit = max(1, min(int(request.query.get("limit", "96")), 200))
        except ValueError:
            limit = 96
        names = sorted(render.codepoints())
        found = icon_search(query, names, limit) if query else names[:limit]
        return web.json_response({"icons": found, "total": len(found) if query else len(names)})

    async def device(request):
        try:
            info = json.loads(paths.device_info.read_text())
        except (OSError, ValueError):
            return web.json_response(DEFAULT_DEVICE)
        info.setdefault("rows", 2)
        if not info.get("cols"):
            info["cols"] = (info.get("keys", 8) + info["rows"] - 1) // info["rows"]
        info["connected"] = True
        return web.json_response(info)

    async def profiles(request):
        paths.profiles.mkdir(parents=True, exist_ok=True)
        return web.json_response(sorted(p.stem for p in paths.profiles.glob("*.yaml")))

    async def profile_body(request) -> str:
        try:
            return safe_name((await request.json()).get("name", ""))
        except (ValueError, AttributeError):
            return ""

    async def profile_save(request):
        name = await profile_body(request)
        write_atomically(paths.profiles / (name + ".yaml"), yaml.safe_dump(load_layout(), allow_unicode=True, sort_keys=False))
        return web.json_response({"ok": True, "name": name})

    async def profile_load(request):
        source = paths.profiles / ((await profile_body(request)) + ".yaml")
        if not source.exists():
            return web.json_response({"ok": False, "error": "profile not found"}, status=404)
        layout = yaml.safe_load(source.read_text()) or {}
        problem = check_layout(layout)
        if problem:
            return web.json_response({"ok": False, "error": problem}, status=400)
        save_layout(layout)
        return web.json_response({"ok": True})

    async def profile_remove(request):
        """Moves the profile into profiles/removed/ instead of deleting it."""
        name = await profile_body(request)
        source = paths.profiles / (name + ".yaml")
        if source.exists():
            target = paths.profiles / "removed" / ("%s-%s.yaml" % (name, time.strftime("%Y%m%d-%H%M%S")))
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
        return web.json_response({"ok": True})

    app.router.add_get("/", index)
    app.router.add_get("/api/layout", get_layout)
    app.router.add_post("/api/layout", post_layout)
    app.router.add_get("/api/states", get_states)
    app.router.add_get("/api/preview", preview)
    app.router.add_get("/api/screen-preview", screen_preview)
    app.router.add_get("/api/track-time", get_track_time)
    app.router.add_get("/api/device", device)
    app.router.add_get("/api/icon", icon)
    app.router.add_get("/api/icons", icons)
    app.router.add_get("/api/profiles", profiles)
    app.router.add_post("/api/profile/save", profile_save)
    app.router.add_post("/api/profile/load", profile_load)
    app.router.add_post("/api/profile/remove", profile_remove)
    app.router.add_static("/static/", STATIC)
    return app


def main():
    paths = Paths.from_env()
    options = Options.load()
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
    store = None if supervisor_token else credentials.open_store(paths.layout.parent)
    try:
        connection = home_assistant.connection_from_environment(store=store)
    except RuntimeError as exc:
        print("[SETUP] %s" % exc, flush=True)
        connection = None
    key = store.get(credentials.TRACK_TIME_API_KEY) if store else ""
    host = os.environ.get("HTD_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("HTD_WEB_PORT", "8099"))
    allowed = LOOPBACK if host in LOOPBACK else (INGRESS_PROXY,)
    print("[WEB] configurator on %s:%d" % (host, port), flush=True)
    web.run_app(build_app(paths, Backend(options, connection, supervisor_token, key), allowed),
                host=host, port=port, print=None)


if __name__ == "__main__":
    main()
