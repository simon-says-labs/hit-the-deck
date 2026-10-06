"""Key and info bar images, drawn without a deck.

Run: python3 -m unittest discover -s tests
"""
import unittest
from datetime import datetime

from PIL import ImageChops

import support  # noqa: F401
import display_rules  # noqa: E402
import render  # noqa: E402


def same(a, b):
    return ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None


class KeyTest(unittest.TestCase):
    def test_every_kind_gives_a_key_image(self):
        states = {"light.desk": {"state": "on", "attributes": {}},
                  "sensor.t": {"state": "21.5", "attributes": {"device_class": "temperature", "unit_of_measurement": "°C"}}}
        buttons = [{"kind": "empty"}, {"kind": "page"}, {"kind": "track_time_toggle"}, {"kind": "track_time_stop"},
                   {"kind": "entity", "entity_id": "light.desk", "layout": "full", "title": "Desk", "service_indicator": True},
                   {"kind": "entity", "entity_id": "sensor.t"},
                   {"kind": "entity", "entity_id": "sensor.t", "layout": "gauge", "gauge_min": 0, "gauge_max": 40},
                   {"kind": "entity", "entity_id": "sensor.t", "layout": "meter"},
                   {"kind": "entity", "entity_id": "sensor.missing", "layout": "gauge"}]
        for button in buttons:
            with self.subTest(button=button):
                image = render.render_button(button, states, {"state": "running", "text": "1:05"}, "en", out_size=96)
                self.assertEqual((image.size, image.mode), ((96, 96), "RGB"))

    def test_track_time_states_look_different(self):
        images = {state: render.render_track_time_toggle({"state": state, "text": "2:15"}, {}, "en")
                  for state in ("running", "paused", "stopped", "offline")}
        for a in images:
            for b in images:
                if a < b:
                    self.assertFalse(same(images[a], images[b]), "%s looks like %s" % (a, b))

    def test_running_key_shows_the_time(self):
        a = render.render_track_time_toggle({"state": "running", "text": "1:05"})
        b = render.render_track_time_toggle({"state": "running", "text": "2:15"})
        self.assertFalse(same(a, b))

    def test_default_titles_follow_the_language(self):
        english = render.render_track_time_stop({}, "en")
        german = render.render_track_time_stop({}, "de")
        self.assertFalse(same(english, german))  # "Stop" vs. "Stopp"
        titled = render.render_track_time_stop({"title": "Stop"}, "de")
        self.assertTrue(same(english, titled))

    def test_unknown_icon_falls_back_to_help_circle(self):
        self.assertEqual(render.icon_char("no-such-icon"), chr(render.codepoints()["help-circle"]))
        self.assertEqual(render.icon_char("mdi:fan"), chr(render.codepoints()["fan"]))

    def test_old_kind_names_are_understood(self):
        self.assertEqual(render.kind_of({"kind": "timetracker_start"}), "track_time_toggle")
        self.assertEqual(render.kind_of({}), "entity")


class InfoBarTest(unittest.TestCase):
    friday = datetime(2026, 10, 9, 14, 30)

    def test_size_and_default_sections(self):
        image = render.render_screen({}, {}, language="en", now=self.friday)
        self.assertEqual(image.size, (248, 58))

    def test_weekday_follows_the_language(self):
        english = render.render_screen({}, {}, language="en", now=self.friday)
        german = render.render_screen({}, {}, language="de", now=self.friday)
        self.assertFalse(same(english, german))

    def test_entity_section_and_gradient(self):
        screen = {"background_color": "#000000", "background_color_2": "#0b3d5c", "dividers": True,
                  "sections": [{"type": "entity", "entity_id": "sensor.t", "label": "Out", "format": "{state}{unit}"},
                               {"type": "text", "text": "Hi"}, {"type": "clock"}]}
        image = render.render_screen(screen, {"sensor.t": {"state": "7", "attributes": {"unit_of_measurement": "°C"}}},
                                     now=self.friday)
        self.assertNotEqual(image.getpixel((5, 0)), image.getpixel((5, 57)))


class DisplayRulesTest(unittest.TestCase):
    def test_on_and_off_light(self):
        self.assertEqual(display_rules.resolve_visual("light.a", "on", {})["color"], display_rules.ON_COLOR)
        self.assertEqual(display_rules.resolve_visual("light.a", "off", {})["color"], "#888888")

    def test_unavailable_is_marked(self):
        self.assertEqual(display_rules.resolve_visual("switch.a", "unavailable", {})["color"], display_rules.PROBLEM_COLOR)

    def test_temperature_colour_and_label(self):
        visual = display_rules.resolve_visual("sensor.t", "30", {"device_class": "temperature"})
        self.assertEqual((visual["icon"], visual["color"]), ("thermometer", "#FF0000"))
        self.assertEqual(display_rules.format_sensor_label("21.0", {"unit_of_measurement": "°C"}), "21°C")
        self.assertEqual(display_rules.format_sensor_label("on", {}), "on")


if __name__ == "__main__":
    unittest.main()
