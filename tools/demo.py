#!/usr/bin/env python3
"""Shows the configurator with made-up entities, without Home Assistant, Track Time or a deck.

    python3 tools/demo.py [--port 8099]

Open http://127.0.0.1:8099. The layout is kept in a temporary folder that disappears when
the demo stops; nothing touches a real installation. The README pictures come from here.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import yaml
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hit_the_deck" / "app"))
import webapp  # noqa: E402
from settings import Paths  # noqa: E402


def entity(entity_id, state, name, **attributes):
    return {"entity_id": entity_id, "state": state, "attributes": dict(attributes, friendly_name=name)}


STATES = {e["entity_id"]: e for e in [
    entity("light.desk", "on", "Desk lamp"),
    entity("fan.ceiling", "off", "Ceiling fan", percentage_step=25),
    entity("switch.coffee_machine", "on", "Coffee machine"),
    entity("scene.focus", "scening", "Focus"),
    entity("sensor.outdoor_temperature", "18.4", "Outdoor", device_class="temperature", unit_of_measurement="°C"),
    entity("sensor.office_temperature", "22.6", "Office", device_class="temperature", unit_of_measurement="°C"),
]}

LAYOUT = {
    "brightness": 80,
    "pages": [{"name": "Office", "buttons": [
        {"kind": "entity", "entity_id": "light.desk", "tap_action": "light.toggle", "layout": "full", "title": "Desk"},
        {"kind": "entity", "entity_id": "fan.ceiling", "tap_action": "fan.toggle", "layout": "full", "title": "Fan"},
        {"kind": "entity", "entity_id": "sensor.outdoor_temperature", "layout": "gauge", "gauge_min": -10,
         "gauge_max": 40, "title": "Outside"},
        {"kind": "track_time_toggle"},
        {"kind": "entity", "entity_id": "switch.coffee_machine", "tap_action": "switch.toggle", "layout": "full",
         "title": "Coffee", "icon": "coffee-maker"},
        {"kind": "entity", "entity_id": "sensor.office_temperature", "layout": "meter", "gauge_min": 15,
         "gauge_max": 30, "title": "Office"},
        {"kind": "entity", "entity_id": "scene.focus", "tap_action": "scene.turn_on", "layout": "full",
         "title": "Focus", "icon": "head-lightbulb"},
        {"kind": "track_time_stop"},
    ]}],
    "screen": {"background_color": "#0b3d5c", "background_color_2": "#020c14", "sections": [
        {"type": "clock", "format": "%H:%M", "size": "xl", "weight": 3, "color": "#7fdbff"},
        {"type": "date", "weekday": True, "weekday_style": "long", "size": "l", "weight": 2,
         "color": "#ffffff", "weekday_color": "#9ad1f5"}]},
}


class DemoBackend:
    async def states(self):
        return STATES

    async def language(self):
        return "en"

    async def track_time_state(self):
        return {"state": "running", "text": "3:10"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        paths = Paths(layout=root / "hit_the_deck.yaml", profiles=root / "profiles", data=root)
        paths.layout.write_text(yaml.safe_dump(LAYOUT, allow_unicode=True, sort_keys=False))
        paths.device_info.write_text(json.dumps({"type": "Stream Deck Neo", "keys": 8, "rows": 2, "cols": 4,
                                                 "screen": [248, 58]}))
        print("Demo configurator: http://127.0.0.1:%d" % args.port, flush=True)
        web.run_app(webapp.build_app(paths, DemoBackend(), allowed=webapp.LOOPBACK),
                    host="127.0.0.1", port=args.port, print=None)


if __name__ == "__main__":
    main()
