"""The deck runtime without a deck: recovery after USB resets, brightness, keys, Track Time.

Run: python3 -m unittest discover -s tests
"""
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401  (stubs the Stream Deck library)
from support import TransportError

import runtime  # noqa: E402
import track_time  # noqa: E402
from settings import Options, Paths  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class FailingRuntime:
    """Raises the given errors one after another, then ends the test with KeyboardInterrupt."""

    def __init__(self, errors, clock=None, run_time=0):
        self.errors = list(errors)
        self.runs = 0
        self.clock = clock
        self.run_time = run_time

    async def run(self):
        self.runs += 1
        if self.clock:
            self.clock.t += self.run_time
        if not self.errors:
            raise KeyboardInterrupt
        raise self.errors.pop(0)


def exit_code(function):
    try:
        function()
    except SystemExit as stop:
        return stop.code
    except KeyboardInterrupt:
        return None


class RecoveryTest(unittest.TestCase):
    def test_lasting_device_loss_exits_with_3_after_three_errors(self):
        clock, rt = Clock(), FailingRuntime([TransportError("No HID device.")] * 5)
        self.assertEqual(exit_code(lambda: runtime.keep_running(rt, clock.sleep, clock.now)), 3)
        self.assertEqual((rt.runs, clock.t), (3, 10))

    def test_rare_transport_errors_do_not_exit(self):
        clock = Clock()
        rt = FailingRuntime([TransportError("x")] * 4, clock, run_time=3600)
        self.assertIsNone(exit_code(lambda: runtime.keep_running(rt, clock.sleep, clock.now)))

    def test_other_errors_never_exit(self):
        clock, rt = Clock(), FailingRuntime([RuntimeError("websocket gone")] * 10)
        self.assertIsNone(exit_code(lambda: runtime.keep_running(rt, clock.sleep, clock.now)))
        self.assertEqual(rt.runs, 11)

    def test_no_deck_at_start_exits_after_the_wait(self):
        clock = Clock()
        self.assertEqual(exit_code(lambda: runtime.wait_for_deck(lambda: None, clock.sleep, clock.now)), 3)
        self.assertEqual(clock.t, runtime.STARTUP_WAIT_S)

    def test_deck_plugged_in_later_is_used(self):
        clock = Clock()
        deck = runtime.wait_for_deck(lambda: "DECK" if clock.t >= 20 else None, clock.sleep, clock.now)
        self.assertEqual((deck, clock.t), ("DECK", 20))

    def test_restarts_stay_below_the_supervisor_limit(self):
        self.assertLessEqual(1800 // runtime.STARTUP_WAIT_S, 10)


class GoneDeck:
    def screen_image_format(self):
        return {"size": (248, 58)}

    def set_screen_image(self, _):
        raise TransportError("No HID device.")

    def key_count(self):
        return 2

    def key_image_format(self):
        return {"size": (96, 96)}

    def set_key_image(self, *_):
        raise TransportError("No HID device.")


class RecordingDeck:
    def __init__(self, keys=8):
        self.brightness = []
        self.images = {}
        self.keys = keys

    def set_brightness(self, value):
        self.brightness.append(value)

    def key_count(self):
        return self.keys

    def key_image_format(self):
        return {"size": (96, 96)}

    def set_key_image(self, index, image):
        self.images[index] = image

    def screen_image_format(self):
        return {"size": (248, 58)}

    def set_screen_image(self, image):
        self.images["screen"] = image

    def set_key_callback(self, _):
        raise StopTest


class StopTest(Exception):
    pass


def make_runtime(deck, layout=None, options=None, tmp=None):
    tmp = Path(tmp or tempfile.mkdtemp())
    paths = Paths(layout=tmp / "hit_the_deck.yaml", profiles=tmp / "profiles", data=tmp)
    paths.layout.write_text(json.dumps(layout or {"brightness": 79, "pages": [{"buttons": []}]}))
    return runtime.Runtime(deck, paths, options or Options(), connection=None)


class DrawingTest(unittest.TestCase):
    def test_lost_device_in_the_info_bar_reaches_keep_running(self):
        with self.assertRaises(TransportError):
            make_runtime(GoneDeck()).render_screen()

    def test_lost_device_on_the_keys_reaches_keep_running(self):
        with self.assertRaises(TransportError):
            make_runtime(GoneDeck()).render_all_keys()

    def test_every_key_and_the_info_bar_are_drawn(self):
        deck = RecordingDeck()
        rt = make_runtime(deck, {"pages": [{"buttons": [{"kind": "track_time_toggle"}, {"kind": "track_time_stop"}]}]})
        rt.render_all_keys()
        rt.render_screen()
        self.assertEqual(sorted(k for k in deck.images if k != "screen"), list(range(8)))
        self.assertEqual(deck.images["screen"].size, (248, 58))


class FakeSocket:
    def __init__(self, states):
        self._states = states
        self.actions = []

    async def states(self):
        return self._states

    async def language(self):
        return "de"

    async def subscribe_state_changes(self):
        return None

    async def call_action(self, action, data):
        self.actions.append((action, data))


class BrightnessTest(unittest.TestCase):
    """A short transport error at night restarts run(); the deck must end dimmed, not at the day value."""

    def night_runtime(self, deck):
        options = Options(auto_brightness=True, brightness_light_entity="light.living_room", brightness_min=10)
        rt = make_runtime(deck, options=options)
        rt._brightness = 10  # dimmed before the error

        async def connect():
            rt.socket = FakeSocket({"light.living_room": {"state": "off"}})
            rt.states = await rt.socket.states()
            rt.language = "de"
        rt.connect_home_assistant = connect
        return rt

    def test_restart_with_lights_off_ends_at_night_brightness(self):
        deck = RecordingDeck()
        with self.assertRaises(StopTest):
            asyncio.run(self.night_runtime(deck).run())
        self.assertEqual(deck.brightness[-1], 10)

    def test_layout_reload_with_lights_off_ends_at_night_brightness(self):
        deck = RecordingDeck()
        rt = self.night_runtime(deck)
        rt.states = {"light.living_room": {"state": "off"}}
        rt.layout_mtime = -1
        rt.reload_layout_if_changed()
        self.assertEqual(deck.brightness[-1], 10)

    def test_without_a_light_entity_nothing_is_dimmed(self):
        rt = make_runtime(RecordingDeck(), options=Options(auto_brightness=True))
        self.assertIsNone(rt.auto_brightness())


class FakeTrackTime:
    def __init__(self, state="stopped"):
        self.current = {"state": state, "text": "0:00"}
        self.calls = []

    def state(self):
        return dict(self.current)

    def toggle(self):
        self.calls.append("toggle")
        nxt = {"stopped": "running", "running": "paused", "paused": "running"}[self.current["state"]]
        self.current = {"state": nxt, "text": "0:00"}
        return self.state()

    def stop(self):
        self.calls.append("stop")
        self.current = {"state": "stopped", "text": "0:00"}
        return self.state()


class ImmediateLoop:
    def call_soon_threadsafe(self, function, *args):
        function(*args)


class TrackTimeKeysTest(unittest.TestCase):
    layout = {"pages": [{"buttons": [{"kind": "track_time_toggle"}, {"kind": "entity"}, {"kind": "track_time_stop"}]}]}

    def runtime_with(self, fake):
        rt = make_runtime(RecordingDeck(), self.layout)
        rt.track_time, rt.loop = fake, ImmediateLoop()
        rt.drawn = []
        rt.render_key = rt.drawn.append
        return rt

    def test_stopped_from_outside_redraws_once(self):
        fake = FakeTrackTime("running")
        rt = self.runtime_with(fake)
        rt.track_time_state = fake.state()
        fake.current = {"state": "stopped", "text": ""}
        asyncio.run(rt.refresh_track_time())
        self.assertEqual(rt.drawn, [0, 2])
        rt.drawn.clear()
        asyncio.run(rt.refresh_track_time())
        self.assertEqual(rt.drawn, [])

    def test_new_minute_redraws(self):
        fake = FakeTrackTime("running")
        rt = self.runtime_with(fake)
        rt.track_time_state = fake.state()
        fake.current = {"state": "running", "text": "0:01"}
        asyncio.run(rt.refresh_track_time())
        self.assertEqual(rt.drawn, [0, 2])

    def test_toggle_key_starts_and_pauses(self):
        fake = FakeTrackTime("stopped")
        rt = self.runtime_with(fake)
        rt.on_key(rt.deck, 0, False)
        self.assertEqual(rt.track_time_state["state"], "running")
        rt.on_key(rt.deck, 0, False)
        self.assertEqual(rt.track_time_state["state"], "paused")
        rt.on_key(rt.deck, 2, False)
        self.assertEqual((fake.calls, rt.track_time_state["state"]), (["toggle", "toggle", "stop"], "stopped"))

    def test_key_down_does_nothing(self):
        fake = FakeTrackTime()
        rt = self.runtime_with(fake)
        rt.on_key(rt.deck, 0, True)
        self.assertEqual(fake.calls, [])

    def test_press_without_track_time_does_not_crash(self):
        rt = self.runtime_with(None)
        rt.on_key(rt.deck, 0, False)
        self.assertEqual(rt.track_time_state, track_time.OFFLINE)

    def test_old_key_kinds_still_work(self):
        fake = FakeTrackTime()
        rt = self.runtime_with(fake)
        rt.layout = {"buttons": [{"kind": "timetracker_start"}]}
        rt.on_key(rt.deck, 0, False)
        self.assertEqual(fake.calls, ["toggle"])


class ActionsTest(unittest.TestCase):
    def test_action_and_entity_are_combined(self):
        self.assertEqual(runtime.action_data({"entity_id": "light.desk", "action_data": {"brightness": 10}}),
                         {"brightness": 10, "entity_id": "light.desk"})
        self.assertEqual(runtime.action_of({"tap_service": "light.toggle"}), "light.toggle")

    def test_fan_speed_snaps_to_the_fans_steps(self):
        states = {"fan.desk": {"state": "off", "attributes": {"percentage_step": 100 / 9}}}
        steps = runtime.fan_sequence({"entity_id": "fan.desk", "fan_speed": 40}, states)
        self.assertEqual(steps[0]["data"]["percentage"], 44)  # step 4 of 9

    def test_running_fan_turns_off(self):
        steps = runtime.fan_sequence({"entity_id": "fan.desk", "fan_speed": 50}, {"fan.desk": {"state": "on"}})
        self.assertEqual([s["action"] for s in steps], ["fan.turn_off"])

    def test_sequential_fan_sets_the_speed_again_after_oscillation(self):
        steps = runtime.fan_sequence({"entity_id": "fan.bed", "fan_speed": 30, "fan_oscillate": True,
                                      "fan_sequential": True}, {"fan.bed": {"state": "off"}})
        self.assertEqual([s["action"] for s in steps],
                         ["fan.turn_on", "fan.set_percentage", "fan.oscillate", "fan.set_percentage"])

    def test_touch_point_switches_page(self):
        rt = make_runtime(RecordingDeck(), {"pages": [{"buttons": []}, {"buttons": []}], "touch_right": {"page": "next"}})
        rt.render_all_keys = lambda: None
        rt.on_key(rt.deck, 9, False)  # Neo: key_count() + 1 is the right touch point
        self.assertEqual(rt.page, 1)
        self.assertEqual(json.loads(rt.paths.page.read_text()), {"page": 1})

    def test_entity_key_runs_its_action(self):
        rt = make_runtime(RecordingDeck(), {"pages": [{"buttons": [
            {"kind": "entity", "entity_id": "light.desk", "tap_action": "light.toggle"}]}]})

        async def press():
            rt.loop = asyncio.get_running_loop()
            rt.socket = FakeSocket({})
            rt.on_key(rt.deck, 0, False)
            await asyncio.sleep(0.05)
            return rt.socket.actions

        self.assertEqual(asyncio.run(press()), [("light.toggle", {"entity_id": "light.desk"})])


if __name__ == "__main__":
    unittest.main()
