"""Which icon and colour an entity gets on a key.

The rules follow the default display configuration of the Stream Deck plugin
"Home Assistant" by Christoph Giesche (https://github.com/cgiesche/streamdeck-homeassistant,
MIT License, see THIRD_PARTY_NOTICES.md), so keys look the same as on a computer with
that plugin. Domains and sensor classes that are not listed fall back to neutral defaults.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

ON_STATES = {"on", "playing", "open", "opening", "home", "locked", "heat", "active"}
ON_COLOR = "#ffd484"
BASE_COLOR = "#aaaaaa"
PROBLEM_COLOR = "#ff6f91"
PROBLEM_STATES = {"unavailable", "unknown", "error"}
INDICATOR_COLOR = "#62ff65"


def temperature_color(value: float, unit: str = "") -> str:
    """Colour scale for temperatures (°C, or °F converted)."""
    celsius = (value - 32) * 5 / 9 if unit == "°F" else value
    steps = [
        (-20, "#0000FF"), (-15, "#0040FF"), (-10, "#0080FF"), (-5, "#00BFFF"),
        (0, "#87CEFA"), (5, "#B0E0E6"), (10, "#90EE90"), (15, "#ADFF2F"),
        (20, "#FFFF00"), (25, "#FFA500"),
    ]
    for threshold, color in steps:
        if celsius <= threshold:
            return color
    return "#FF0000"


# icon = off/default, on_icon = while on, off_color = colour while off
DOMAIN_RULES: dict = {
    "switch": {"icon": "toggle-switch-off", "on_icon": "toggle-switch"},
    "input_boolean": {"icon": "toggle-switch-off", "on_icon": "toggle-switch"},
    "light": {"icon": "lightbulb", "off_color": "#888888", "on_icon": "lightbulb"},
    "fan": {"icon": "fan", "off_icon": "fan-off"},
    "lock": {"icon": "lock-open", "on_icon": "lock"},
    "person": {"icon": "account"},
    "media_player": {"icon": "play-circle"},
    "cover": {"icon": "garage", "on_icon": "garage-open"},
    "scene": {"icon": "palette", "off_color": "#ffd484"},
    "script": {"icon": "script-text-play"},
    "automation": {"icon": "robot"},
    "binary_sensor": {"icon": "radiobox-blank", "on_icon": "radiobox-marked"},
    "button": {"icon": "gesture-tap-button"},
    "input_button": {"icon": "gesture-tap-button"},
}

SENSOR_CLASSES: dict = {
    "temperature": {"icon": "thermometer", "color_fn": temperature_color},
    "humidity": {"icon": "water-percent", "color": "#2C73D2"},
    "power": {"icon": "flash", "color": "#F9F871"},
    "energy": {"icon": "lightning-bolt", "color": "#F9F871"},
    "voltage": {"icon": "flash", "color": "#F9F871"},
    "current": {"icon": "current-ac", "color": "#2C73D2"},
    "pressure": {"icon": "gauge", "color": "#2C73D2"},
    "atmospheric_pressure": {"icon": "thermometer-lines", "color": "#2C73D2"},
    "carbon_dioxide": {"icon": "molecule-co2"},
    "illuminance": {"icon": "brightness-5"},
}


def domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if entity_id and "." in entity_id else ""


def resolve_visual(entity_id: str, state: str, attributes: dict) -> dict:
    """{"icon": <mdi name>, "color": <hex>, "is_on": bool} for an entity state."""
    domain = domain_of(entity_id)
    attributes = attributes or {}
    is_on = state in ON_STATES

    if state in PROBLEM_STATES:
        return {"icon": DOMAIN_RULES.get(domain, {}).get("icon", "help-circle"),
                "color": PROBLEM_COLOR, "is_on": is_on}

    if domain == "sensor":
        rule = SENSOR_CLASSES.get(attributes.get("device_class", ""))
        if not rule:
            return {"icon": "gauge", "color": BASE_COLOR, "is_on": False}
        color = rule.get("color", BASE_COLOR)
        if "color_fn" in rule:
            try:
                color = rule["color_fn"](float(state), attributes.get("unit_of_measurement", ""))
            except (TypeError, ValueError):
                color = BASE_COLOR
        return {"icon": rule["icon"], "color": color, "is_on": False}

    rule = DOMAIN_RULES.get(domain)
    if not rule:
        return {"icon": "circle-outline", "color": ON_COLOR if is_on else BASE_COLOR, "is_on": is_on}
    if is_on:
        return {"icon": rule.get("on_icon", rule.get("icon", "circle")),
                "color": rule.get("on_color", ON_COLOR), "is_on": True}
    return {"icon": rule.get("off_icon", rule.get("icon", "circle")),
            "color": rule.get("off_color", BASE_COLOR), "is_on": False}


def format_sensor_label(state: str, attributes: dict) -> str:
    """Rounded value plus unit, e.g. "21.5°C"; non-numeric states as they are."""
    unit = (attributes or {}).get("unit_of_measurement", "")
    try:
        rounded = round(float(state), 1)
    except (TypeError, ValueError):
        return str(state)
    if rounded == int(rounded):
        rounded = int(rounded)
    return "%s%s" % (rounded, unit)
