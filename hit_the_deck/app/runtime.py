#!/usr/bin/env python3
"""Hit the Deck: drives a Stream Deck from Home Assistant.

- Draws every key and the Neo info bar, redraws a key when its entity changes.
- Runs a Home Assistant action, a sequence or a fan preset when a key is pressed.
- Track Time keys start, pause, resume and stop the Track Time app.
- Reloads the key layout when the configurator saves it (no restart).
- Recovers from USB resets: after repeated transport errors it exits, the Supervisor's
  watchdog starts a fresh container, and only a fresh container sees the new device node.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import sys
import time

from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from StreamDeck.Transport.Transport import TransportError
from websockets.exceptions import ConnectionClosed

import credentials
import home_assistant
import layout as layout_file
import render
import texts
import track_time
from settings import DEFAULT_LAYOUT, Options, Paths

FAILURE_LIMIT = int(os.environ.get("HTD_FAILURE_LIMIT", "3"))
FAILURE_WINDOW_S = 60          # transport errors further apart start counting again
STARTUP_WAIT_S = int(os.environ.get("HTD_STARTUP_WAIT_S", "600"))
EXIT_DEVICE_GONE = 3
EXIT_NOT_CONFIGURED = 2
TRACK_TIME_REFRESH_S = 15
TRACK_TIME_DISCOVERY_S = 60


def log(message: str) -> None:
    print(message, flush=True)


def action_of(item: dict) -> str:
    return item.get("tap_action") or item.get("tap_service") or item.get("action") or item.get("service") or ""


def action_data(item: dict) -> dict:
    data = dict(item.get("action_data") or item.get("service_data") or item.get("data") or {})
    if item.get("entity_id") and "entity_id" not in data:
        data["entity_id"] = item["entity_id"]
    return data


def fan_sequence(button: dict, states: dict) -> list:
    """Fan preset key: a running fan turns off, otherwise it turns on at the preset.

    The speed snaps to the fan's own steps (percentage_step); many fans ignore other values.
    fan_sequential sends on, speed and oscillation one after another with 4 s pauses, for
    fans that drop commands sent in quick succession, and sets the speed again after
    oscillation because some fans reset their speed when oscillation is switched on.
    """
    entity_id = button.get("entity_id", "")
    entity = states.get(entity_id) or {}
    if entity.get("state") == "on":
        return [{"action": "fan.turn_off", "data": {"entity_id": entity_id}}]
    speed = button.get("fan_speed")
    if speed is not None:
        try:
            step = float((entity.get("attributes") or {}).get("percentage_step") or 0)
            if step > 0:
                speed = min(100, round(max(1, round(float(speed) / step)) * step))
        except (TypeError, ValueError):
            pass
    oscillate = button.get("fan_oscillate")
    if button.get("fan_sequential"):
        steps = [{"action": "fan.turn_on", "data": {"entity_id": entity_id}, "delay_ms": 4000}]
        if speed is not None:
            steps.append({"action": "fan.set_percentage", "data": {"entity_id": entity_id, "percentage": int(speed)},
                          "delay_ms": 4000})
        if oscillate is not None:
            steps.append({"action": "fan.oscillate", "data": {"entity_id": entity_id, "oscillating": bool(oscillate)},
                          "delay_ms": 4000})
            if speed is not None and oscillate:
                steps.append({"action": "fan.set_percentage",
                              "data": {"entity_id": entity_id, "percentage": int(speed)}})
        return steps
    data = {"entity_id": entity_id}
    if speed is not None:
        data["percentage"] = int(speed)
    steps = [{"action": "fan.turn_on", "data": data}]
    if oscillate is not None:
        steps.append({"action": "fan.oscillate", "data": {"entity_id": entity_id, "oscillating": bool(oscillate)},
                      "delay_ms": 300})
    return steps


class Runtime:
    def __init__(self, deck, paths: Paths, options: Options, connection, supervisor_token: str = "",
                 track_time_key: str = "", clock=time.time):
        self.deck = deck
        self.paths = paths
        self.options = options
        self.connection = connection
        self.supervisor_token = supervisor_token
        self.track_time_key = track_time_key
        self.clock = clock
        self.layout = layout_file.load(paths.layout)
        self.layout_mtime = self._mtime()
        self.states: dict = {}
        self.language = "en"
        self.socket = None
        self.loop = None
        self.page = self._load_page()
        self.track_time = None
        self.track_time_state = dict(track_time.OFFLINE)
        self._last = {"screen": 0.0, "dim": 0.0, "track_time": 0.0, "discovery": -1e9}
        self._brightness = None

    # --- brightness --------------------------------------------------------------------
    def auto_brightness(self):
        """Day value (the configurator's slider) while the light entity is not off, else brightness_min."""
        if not (self.options.auto_brightness and self.options.brightness_light_entity):
            return None
        state = (self.states.get(self.options.brightness_light_entity) or {}).get("state")
        return int(self.options.brightness_min) if state == "off" else int(self.layout.get("brightness", 80))

    def apply_auto_brightness(self):
        value = self.auto_brightness()
        if value is not None and value != self._brightness:
            self.deck.set_brightness(value)
            self._brightness = value
            log("[DIM] brightness %d%%" % value)

    def reset_brightness(self):
        """Sets the day value and then enforces the automatic value again.

        After set_brightness(day) the remembered value no longer matches the device; without
        forgetting it, a night value equal to the previous one would never be written again.
        """
        self.deck.set_brightness(int(self.layout.get("brightness", 80)))
        self._brightness = None
        self.apply_auto_brightness()

    # --- pages -------------------------------------------------------------------------
    def _mtime(self) -> float:
        try:
            return self.paths.layout.stat().st_mtime
        except OSError:
            return 0.0

    def _load_page(self) -> int:
        try:
            return int(json.loads(self.paths.page.read_text())["page"])
        except (OSError, ValueError, KeyError, TypeError):
            return 0

    def pages(self) -> list:
        return layout_file.pages_of(self.layout)

    def buttons(self) -> list:
        pages = self.pages()
        if self.page >= len(pages):
            self.page = 0
        return pages[self.page].get("buttons", [])

    def switch_page(self, target):
        count = len(self.pages())
        if target == "next":
            self.page = (self.page + 1) % count
        elif target == "prev":
            self.page = (self.page - 1) % count
        else:
            try:
                self.page = max(0, min(count - 1, int(target)))
            except (TypeError, ValueError):
                return
        try:
            self.paths.page.write_text(json.dumps({"page": self.page}))
        except OSError:
            pass
        self.render_all_keys()

    # --- drawing -----------------------------------------------------------------------
    def render_key(self, index: int):
        buttons = self.buttons()
        button = buttons[index] if index < len(buttons) else {"kind": "empty"}
        image = render.render_button(button, self.states, self.track_time_state, self.language,
                                     out_size=self.deck.key_image_format()["size"][0])
        self.deck.set_key_image(index, PILHelper.to_native_key_format(self.deck, image))

    def render_all_keys(self):
        for index in range(self.deck.key_count()):
            try:
                self.render_key(index)
            except TransportError:
                raise  # device gone: keep_running() decides
            except Exception as exc:
                log("[WARN] key %d: %s" % (index, exc))

    def render_track_time_keys(self):
        for index, button in enumerate(self.buttons()):
            if render.kind_of(button).startswith("track_time"):
                self.render_key(index)

    def render_screen(self):
        try:
            width, height = self.deck.screen_image_format()["size"]
        except Exception:
            return  # this model has no screen
        try:
            image = render.render_screen(self.layout.get("screen") or {}, self.states, width, height, self.language)
            self.deck.set_screen_image(PILHelper.to_native_screen_format(self.deck, image))
        except (AttributeError, NotImplementedError):
            pass
        except TransportError:
            raise  # without this, a lost device was swallowed here every second
        except Exception as exc:
            log("[WARN] info bar: %s" % exc)

    # --- Track Time --------------------------------------------------------------------
    def connect_track_time(self):
        self.track_time = track_time.connect(self.options, self.supervisor_token, self.track_time_key)
        log("[TRACK TIME] %s" % (self.track_time or "not found, the keys show offline"))

    async def refresh_track_time(self):
        now = self.clock()
        if self.track_time is None and now - self._last["discovery"] >= TRACK_TIME_DISCOVERY_S:
            self._last["discovery"] = now
            await asyncio.to_thread(self.connect_track_time)
        new = await asyncio.to_thread(self.track_time.state) if self.track_time else dict(track_time.OFFLINE)
        if new != self.track_time_state:
            self.track_time_state = new
            self.render_track_time_keys()

    def press_track_time(self, action: str):
        """Runs in the deck's reader thread; drawing happens on the event loop."""
        if self.track_time is None:
            log("[TRACK TIME] key pressed, but Track Time was not found")
            return
        self.track_time_state = getattr(self.track_time, action)()
        log("[TRACK TIME] %s -> %s" % (action, self.track_time_state["state"]))
        self.loop.call_soon_threadsafe(self.render_track_time_keys)

    # --- keys --------------------------------------------------------------------------
    def schedule(self, coroutine):
        asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def on_key(self, deck, key, pressed):
        if pressed:
            return
        count = deck.key_count()
        if key >= count:  # the Neo's two touch points next to the info bar
            zone = self.layout.get("touch_left" if key == count else "touch_right") or {}
            if zone.get("page"):
                self.switch_page(zone["page"])
            elif action_of(zone):
                self.schedule(self.run_action(action_of(zone), action_data(zone)))
            return
        buttons = self.buttons()
        if key >= len(buttons):
            return
        button = buttons[key]
        kind = render.kind_of(button)
        if kind == "track_time_toggle":
            self.press_track_time("toggle")
        elif kind == "track_time_stop":
            self.press_track_time("stop")
        elif kind == "page":
            self.switch_page(button.get("page_target", "next"))
        elif kind == "entity":
            if button.get("sequence"):
                self.schedule(self.run_sequence(button["sequence"]))
            elif button.get("entity_id", "").startswith("fan.") and (
                    button.get("fan_speed") is not None or button.get("fan_oscillate") is not None):
                self.schedule(self.run_sequence(fan_sequence(button, self.states)))
            elif action_of(button):
                self.schedule(self.run_action(action_of(button), action_data(button)))

    async def run_action(self, action: str, data: dict):
        try:
            await self.socket.call_action(action, data)
            log("[HA] %s %s" % (action, data))
        except Exception as exc:
            log("[WARN] %s: %s" % (action, exc))

    async def run_sequence(self, steps: list):
        for step in steps:
            if action_of(step):
                await self.run_action(action_of(step), action_data(step))
            if step.get("delay_ms"):
                await asyncio.sleep(step["delay_ms"] / 1000)

    # --- main loop ---------------------------------------------------------------------
    def reload_layout_if_changed(self):
        mtime = self._mtime()
        if mtime != self.layout_mtime:
            log("[LAYOUT] changed, reloading")
            self.layout = layout_file.load(self.paths.layout)
            self.layout_mtime = mtime
            self.reset_brightness()
            self.render_all_keys()
            self.render_screen()

    def handle(self, message: dict):
        if message.get("type") != "event" or message["event"].get("event_type") != "state_changed":
            return
        entity_id = message["event"]["data"]["entity_id"]
        new_state = message["event"]["data"].get("new_state")
        if new_state:
            self.states[entity_id] = new_state
        if entity_id == self.options.brightness_light_entity:
            self.apply_auto_brightness()
        for index, button in enumerate(self.buttons()):
            if button.get("entity_id") == entity_id:
                self.render_key(index)

    async def connect_home_assistant(self):
        self.socket = await home_assistant.Socket.connect(self.connection)
        self.states = await self.socket.states()
        self.language = texts.pick_language(self.options.language, await self.socket.language())
        await self.socket.subscribe_state_changes()

    async def run(self):
        self.loop = asyncio.get_running_loop()
        await self.connect_home_assistant()
        await self.refresh_track_time()
        self.reset_brightness()
        self.deck.set_key_callback(self.on_key)
        self.render_all_keys()
        self.render_screen()
        interval = float((self.layout.get("screen") or {}).get("update_interval", 1) or 1)
        while True:
            try:
                self.handle(await asyncio.wait_for(self.socket.receive(), timeout=1.0))
            except asyncio.TimeoutError:
                pass
            except (ConnectionClosed, ConnectionError) as exc:
                log("[HA] connection lost (%s), reconnecting" % exc)
                await asyncio.sleep(3)
                await self.connect_home_assistant()
                self.render_all_keys()
            now = self.clock()
            if now - self._last["screen"] >= interval:
                self.render_screen()
                self._last["screen"] = now
            if now - self._last["dim"] >= 5:
                self.apply_auto_brightness()
                self._last["dim"] = now
            if now - self._last["track_time"] >= TRACK_TIME_REFRESH_S:
                await self.refresh_track_time()
                self._last["track_time"] = now
            self.reload_layout_if_changed()


def write_device_info(deck, paths: Paths):
    """Model, key grid and screen size for the configurator."""
    info = {"type": str(deck.deck_type()), "keys": deck.key_count(), "rows": None, "cols": None, "screen": None}
    try:
        info["rows"], info["cols"] = deck.key_layout()
    except Exception:
        pass
    try:
        if deck.is_visual():
            info["screen"] = list(deck.screen_image_format()["size"])
    except Exception:
        pass
    try:
        paths.device_info.write_text(json.dumps(info))
    except OSError as exc:
        log("[WARN] device.json: %s" % exc)


def open_deck(paths: Paths):
    for deck in DeviceManager().enumerate():
        if deck.is_visual():
            deck.open()
            deck.reset()
            log("[OK] %s (%d keys)" % (deck.deck_type(), deck.key_count()))
            write_device_info(deck, paths)
            return deck
    return None


def wait_for_deck(open_function, sleep=time.sleep, now=time.monotonic):
    """Waits for a deck. A container does not see a deck plugged in after it started, so
    after STARTUP_WAIT_S it exits and the watchdog starts a fresh one. 600 s keep the
    restarts below the Supervisor's limit (10 per 30 min) even with the deck unplugged."""
    began = now()
    while True:
        try:
            deck = open_function()
        except Exception as exc:
            log("[WARN] opening the deck: %s" % exc)
            deck = None
        if deck is not None:
            return deck
        if now() - began >= STARTUP_WAIT_S:
            log("[GONE] no Stream Deck for %d s, exiting so the Supervisor restarts the app" % STARTUP_WAIT_S)
            sys.exit(EXIT_DEVICE_GONE)
        log("[WAIT] no Stream Deck found, trying again in 5 s (plug it in via USB)")
        sleep(5)


def keep_running(runtime, sleep=time.sleep, now=time.monotonic):
    """Restarts the runtime after errors; exits when the deck stays gone."""
    failures, last = 0, None
    while True:
        try:
            asyncio.run(runtime.run())
        except TransportError as exc:
            moment = now()
            failures = failures + 1 if last is not None and moment - last < FAILURE_WINDOW_S else 1
            last = moment
            log("[ERROR] Stream Deck not reachable: %s (%d/%d)" % (exc, failures, FAILURE_LIMIT))
            if failures >= FAILURE_LIMIT:
                log("[GONE] Stream Deck gone (USB reset?), exiting so the Supervisor restarts the app")
                sys.exit(EXIT_DEVICE_GONE)
            sleep(5)
        except Exception as exc:
            log("[ERROR] runtime stopped: %s, restarting in 5 s" % exc)
            sleep(5)


def ensure_layout(paths: Paths):
    if not paths.layout.exists():
        paths.layout.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEFAULT_LAYOUT, paths.layout)
        log("[LAYOUT] created %s" % paths.layout)


def main():
    paths = Paths.from_env()
    options = Options.load()
    ensure_layout(paths)
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
    store = None if supervisor_token else credentials.open_store(paths.layout.parent)
    try:
        connection = home_assistant.connection_from_environment(store=store)
    except RuntimeError as exc:
        log("[SETUP] %s" % exc)
        sys.exit(EXIT_NOT_CONFIGURED)
    key = store.get(credentials.TRACK_TIME_API_KEY) if store else ""
    deck = wait_for_deck(lambda: open_deck(paths))

    def shutdown(*_):
        try:
            deck.reset()
            deck.close()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    keep_running(Runtime(deck, paths, options, connection, supervisor_token, key))


if __name__ == "__main__":
    main()
