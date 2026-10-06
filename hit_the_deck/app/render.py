"""Draws the key images and the Stream Deck Neo info bar.

Keys are drawn at 144 x 144 pixels and scaled to the device size (96 x 96 on the Neo), the
info bar at its native 248 x 58. Icons come from the bundled Material Design Icons font.
No Stream Deck library is needed here, so the configurator can show the same images.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

import display_rules as rules
import texts

ASSETS = Path(__file__).resolve().parent / "assets" / "mdi"
MDI_FONT = ASSETS / "mdi.ttf"
MDI_CODEPOINTS = ASSETS / "mdi-codepoints.json"

TEXT_FONTS = [
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",            # Alpine (the app image)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # Debian, Ubuntu, Raspberry Pi OS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",      # macOS
    "C:\\Windows\\Fonts\\arialbd.ttf",                        # Windows
]

R = 144  # internal key resolution

KIND_ALIASES = {"timetracker_start": "track_time_toggle", "timetracker_stop": "track_time_stop"}

PAUSE_BLUE = "#6e8ca0"
PAUSE_BLUE_DARK = "#243642"
RUNNING_GREEN = "#2f9e44"
STOP_RED = "#e03131"

_codepoints = None
_fonts: dict = {}


def kind_of(button: dict) -> str:
    kind = button.get("kind", "entity")
    return KIND_ALIASES.get(kind, kind)


def codepoints() -> dict:
    global _codepoints
    if _codepoints is None:
        _codepoints = json.loads(MDI_CODEPOINTS.read_text())
    return _codepoints


def _text_font_path() -> str:
    return next((path for path in TEXT_FONTS if os.path.exists(path)), "")


def text_font(size: int):
    key = ("text", size)
    if key not in _fonts:
        path = _text_font_path()
        _fonts[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
    return _fonts[key]


def icon_font(size: int):
    key = ("icon", size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(str(MDI_FONT), size)
    return _fonts[key]


def icon_char(name: str) -> str:
    table = codepoints()
    code = table.get((name or "").replace("mdi:", "").strip())
    return chr(code if code is not None else table["help-circle"])


def outlined(draw, xy, text, font, fill, anchor, stroke=3):
    draw.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill="#000000")


def fit_font(draw, text, max_width, start_size, min_size=14):
    """Shrinks the font until the text fits, like the Stream Deck app does."""
    size = start_size
    while size > min_size:
        font = text_font(size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return text_font(min_size)


def draw_icon(img, name, color, size, center):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(center, icon_char(name), font=icon_font(size), fill=color, anchor="mm")
    img.alpha_composite(layer)


def canvas(background="#000000"):
    return Image.new("RGBA", (R, R), background)


def finish(img, out_size):
    rgb = Image.new("RGB", img.size, "#000000")
    rgb.paste(img, mask=img.split()[3])
    return rgb if out_size == R else rgb.resize((out_size, out_size), Image.LANCZOS)


def draw_title(draw, button, default_pos="top"):
    """Draws the button title; returns where it went (None without a title)."""
    title = (button.get("title") or "").strip()
    if not title:
        return None
    pos = (button.get("title_pos") or default_pos).lower()
    color = button.get("title_color") or "#ffffff"
    font = fit_font(draw, title, max_width=136, start_size=int(button.get("title_size") or 22))
    if pos == "middle":
        outlined(draw, (72, 72), title, font, color, anchor="mm")
    elif pos == "bottom":
        outlined(draw, (72, 138), title, font, color, anchor="ms")
    else:
        outlined(draw, (72, 4), title, font, color, anchor="ma")
    return pos


# --- entity keys -----------------------------------------------------------------------

def render_entity_key(button: dict, entity_state, out_size=96):
    img = canvas(button.get("bg") or "#000000")
    draw = ImageDraw.Draw(img)
    entity_id = button.get("entity_id", "")
    state = (entity_state or {}).get("state", "unavailable")
    attributes = (entity_state or {}).get("attributes") or {}

    visual = rules.resolve_visual(entity_id, state, attributes)
    icon = button.get("icon") or visual["icon"]
    if state in rules.ON_STATES:
        color = button.get("color_on") or button.get("color") or visual["color"]
    else:
        color = button.get("color_off") or button.get("color") or visual["color"]

    if (button.get("layout") or "standard").lower() == "full":
        draw_icon(img, icon, color, size=118, center=(72, 74))
    else:
        draw_icon(img, icon, color, size=78, center=(72, 58))

    title_pos = draw_title(draw, button)
    label = ""
    if rules.domain_of(entity_id) == "sensor" and entity_state:
        label = rules.format_sensor_label(state, attributes)
    elif button.get("label"):
        label = str(button["label"])
    if label:
        if title_pos == "bottom":
            outlined(draw, (72, 4), label, text_font(26), "#ffffff", anchor="ma")
        else:
            outlined(draw, (72, 138), label, text_font(26), "#ffffff", anchor="ms")

    if button.get("service_indicator"):
        draw.ellipse([R - 15, -15, R + 15, 15], fill=rules.INDICATOR_COLOR)
    return finish(img, out_size)


def gauge_value(button, entity_state):
    """(fraction 0..1, value text, unit, valid) for gauge and meter keys."""
    low = float(button.get("gauge_min", 0))
    high = float(button.get("gauge_max", 40))
    if high <= low:
        high = low + 1
    raw = (entity_state or {}).get("state", "?")
    unit = ((entity_state or {}).get("attributes") or {}).get("unit_of_measurement", "")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0, str(raw), unit, False
    return max(0.0, min(1.0, (value - low) / (high - low))), "%g" % round(value, 1), unit, True


def gauge_font_px(button) -> int:
    value = button.get("gauge_font", 34)
    try:
        return max(12, min(48, int(value)))
    except (TypeError, ValueError):
        return {"s": 24, "m": 34, "l": 42}.get(str(value), 34)


def gauge_color(fraction, entity_state):
    attributes = (entity_state or {}).get("attributes") or {}
    if attributes.get("device_class") == "temperature":
        try:
            return rules.temperature_color(float(entity_state.get("state")), attributes.get("unit_of_measurement", ""))
        except (TypeError, ValueError):
            pass
    return "#43a047" if fraction < 0.6 else "#ffa600" if fraction < 0.85 else "#db4437"


def render_gauge_key(button, entity_state, out_size=96):
    """A 240° arc like Home Assistant's gauge card."""
    img = canvas(button.get("bg") or "#000000")
    draw = ImageDraw.Draw(img)
    fraction, value_text, unit, valid = gauge_value(button, entity_state)
    color = button.get("color") or (gauge_color(fraction, entity_state) if valid else rules.PROBLEM_COLOR)
    box, start, sweep = [26, 36, 118, 128], 150, 240
    draw.arc(box, start, start + sweep, fill="#33363c", width=13)
    if valid and fraction > 0:
        draw.arc(box, start, start + sweep * fraction, fill=color, width=13)
    font = fit_font(draw, value_text, max_width=100, start_size=gauge_font_px(button), min_size=12)
    draw.text((72, 78), value_text, font=font, fill=button.get("title_color") or "#ffffff", anchor="mm")
    if unit:
        draw.text((72, 102), unit, font=text_font(16), fill="#9aa0a8", anchor="mm")
    draw_title(draw, button)
    return finish(img, out_size)


METER_SEGMENTS = ["#3b82f6", "#4ade80", "#facc15", "#ef4444"]


def render_meter_key(button, entity_state, out_size=96):
    """A half circle with coloured segments and a needle."""
    img = canvas(button.get("bg") or "#000000")
    draw = ImageDraw.Draw(img)
    fraction, value_text, unit, valid = gauge_value(button, entity_state)
    box, (cx, cy, radius), start, sweep = [22, 46, 122, 146], (72, 96, 50), 180, 180
    step = sweep / len(METER_SEGMENTS)
    for i, color in enumerate(METER_SEGMENTS):
        draw.arc(box, start + i * step, start + (i + 1) * step + 0.5, fill=color, width=14)
    if valid:
        angle = math.radians(start + sweep * fraction)
        tip = (cx + (radius - 2) * math.cos(angle), cy + (radius - 2) * math.sin(angle))
        base = (cx + 10 * math.cos(angle + math.pi), cy + 10 * math.sin(angle + math.pi))
        draw.line([base, tip], fill="#ffffff", width=5)
        draw.line([base, tip], fill="#222222", width=1)
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill="#ffffff", outline="#222222")
    text = value_text + unit
    font = fit_font(draw, text, max_width=104, start_size=gauge_font_px(button), min_size=13)
    outlined(draw, (72, 140), text, font, button.get("title_color") or "#ffffff", anchor="ms", stroke=2)
    draw_title(draw, button)
    return finish(img, out_size)


# --- Track Time keys -------------------------------------------------------------------

def render_track_time_toggle(track_time: dict, button=None, language="en", out_size=96):
    """stopped: play symbol · running: green with today's time · paused: blue with pause bars."""
    button = button or {}
    state = track_time.get("state", "offline")
    text = track_time.get("text", "")
    title_color = button.get("title_color") or "#ffffff"
    if state == "paused":
        img = Image.new("RGBA", (R, R), button.get("bg_paused") or PAUSE_BLUE_DARK)
        draw = ImageDraw.Draw(img)
        draw.ellipse([10, 10, 134, 134], fill=PAUSE_BLUE)
        draw.rounded_rectangle([54, 38, 66, 82], radius=3, fill="#ffffff")
        draw.rounded_rectangle([78, 38, 90, 82], radius=3, fill="#ffffff")
        outlined(draw, (72, 116), text or texts.deck_text(language, "pause"), text_font(26), title_color, anchor="mm")
    elif state == "running":
        img = Image.new("RGBA", (R, R), button.get("bg_running") or "#14532d")
        draw = ImageDraw.Draw(img)
        draw.ellipse([10, 10, 134, 134], fill=RUNNING_GREEN)
        outlined(draw, (72, 72), text or "0:00", text_font(38), title_color, anchor="mm")
    elif state == "stopped":
        img = canvas(button.get("bg") or "#000000")
        draw = ImageDraw.Draw(img)
        draw.ellipse([34, 22, 110, 98], fill=RUNNING_GREEN)
        draw.polygon([(60, 40), (60, 80), (96, 60)], fill="#ffffff")
        outlined(draw, (72, 138), button.get("title") or texts.deck_text(language, "start"),
                 text_font(24), title_color, anchor="ms", stroke=2)
    else:
        img = canvas(button.get("bg") or "#000000")
        draw = ImageDraw.Draw(img)
        draw_icon(img, "timer-off-outline", rules.PROBLEM_COLOR, size=78, center=(72, 58))
        outlined(draw, (72, 138), texts.deck_text(language, "offline"), fit_font(draw, texts.deck_text(language, "offline"), 136, 22),
                 title_color, anchor="ms", stroke=2)
    return finish(img, out_size)


def render_track_time_stop(button=None, language="en", out_size=96):
    button = button or {}
    img = canvas(button.get("bg") or "#000000")
    draw = ImageDraw.Draw(img)
    draw.ellipse([34, 22, 110, 98], fill=STOP_RED)
    draw.rounded_rectangle([58, 46, 86, 74], radius=3, fill="#ffffff")
    outlined(draw, (72, 138), button.get("title") or texts.deck_text(language, "stop"), text_font(24),
             button.get("title_color") or "#ffffff", anchor="ms", stroke=2)
    return finish(img, out_size)


def render_page_key(button, out_size=96):
    img = canvas(button.get("bg") or "#000000")
    draw = ImageDraw.Draw(img)
    icon = button.get("icon") or ("chevron-left-circle" if button.get("page_target") == "prev" else "chevron-right-circle")
    draw_icon(img, icon, button.get("color") or "#9aa0a8", size=84, center=(72, 62))
    draw_title(draw, button, default_pos="bottom")
    return finish(img, out_size)


def render_button(button: dict, states: dict, track_time=None, language="en", out_size=96):
    kind = kind_of(button)
    if kind == "track_time_toggle":
        return render_track_time_toggle(track_time or {"state": "offline"}, button, language, out_size)
    if kind == "track_time_stop":
        return render_track_time_stop(button, language, out_size)
    if kind == "page":
        return render_page_key(button, out_size)
    if kind == "empty" or not button.get("entity_id"):
        return finish(canvas(), out_size)
    entity_state = states.get(button["entity_id"])
    layout = (button.get("layout") or "").lower()
    if layout == "gauge":
        return render_gauge_key(button, entity_state, out_size)
    if layout == "meter":
        return render_meter_key(button, entity_state, out_size)
    return render_entity_key(button, entity_state, out_size)


# --- info bar (Stream Deck Neo screen) -------------------------------------------------

SCREEN_SIZES = {"s": 14, "m": 18, "l": 24, "xl": 34}

DEFAULT_SECTIONS = [
    {"type": "clock", "format": "%H:%M", "size": "xl", "weight": 3},
    {"type": "date", "weekday": True, "weekday_style": "long", "size": "l", "weight": 2},
]


def screen_background(screen: dict, width: int, height: int):
    """One colour, or a vertical gradient to background_color_2."""
    top = screen.get("background_color", "#000000")
    bottom = screen.get("background_color_2")
    if not bottom:
        return Image.new("RGB", (width, height), top)
    (r1, g1, b1), (r2, g2, b2) = ImageColor.getrgb(top)[:3], ImageColor.getrgb(bottom)[:3]
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line([(0, y), (width, y)], fill=(round(r1 + (r2 - r1) * t), round(g1 + (g2 - g1) * t), round(b1 + (b2 - b1) * t)))
    return img


def render_screen(screen: dict, states: dict, width=248, height=58, language="en", now=None):
    img = screen_background(screen, width, height)
    draw = ImageDraw.Draw(img)
    sections = screen.get("sections") or DEFAULT_SECTIONS
    now = now or datetime.now()
    weights = [max(1, int(section.get("weight", 1) or 1)) for section in sections]
    x = 0
    for i, section in enumerate(sections):
        w = int(width * weights[i] / sum(weights)) if i < len(sections) - 1 else width - x
        cx = x + w // 2
        kind = section.get("type", "entity")
        size = SCREEN_SIZES.get(str(section.get("size", "m")), 18)
        color = section.get("color", "#FFFFFF")

        if kind == "clock":
            text = now.strftime(section.get("format") or "%H:%M")
            draw.text((cx, height // 2), text, font=fit_font(draw, text, w - 8, size, 10), fill=color, anchor="mm")
        elif kind == "date":
            names = texts.WEEKDAYS if section.get("weekday_style", "long") == "long" else texts.WEEKDAYS_SHORT
            weekday = names.get(language, names["en"])[now.weekday()]
            date_text = now.strftime(section.get("format") or texts.DATE_FORMAT.get(language, "%Y-%m-%d"))
            if section.get("weekday", True):
                draw.text((cx, 17), weekday, font=fit_font(draw, weekday, w - 8, max(12, size - 6), 10),
                          fill=section.get("weekday_color", "#9aa0a8"), anchor="mm")
                draw.text((cx, 41), date_text, font=fit_font(draw, date_text, w - 8, size, 10), fill=color, anchor="mm")
            else:
                draw.text((cx, height // 2), date_text, font=fit_font(draw, date_text, w - 8, size, 10),
                          fill=color, anchor="mm")
        elif kind == "text":
            text = str(section.get("text", ""))
            draw.text((cx, height // 2), text, font=fit_font(draw, text, w - 8, size, 10), fill=color, anchor="mm")
        else:
            entity = states.get(section.get("entity_id", ""), {})
            state = entity.get("state", "?")
            unit = (entity.get("attributes") or {}).get("unit_of_measurement", "")
            text = section.get("format", "{state}{unit}").replace("{state}", str(state)).replace("{unit}", unit)
            fill = section.get("color_on", "#ffd484") if state in rules.ON_STATES else section.get("color_off", color)
            font = fit_font(draw, text, w - 8, size if section.get("size") else 20, 10)
            if section.get("label"):
                draw.text((cx, 12), section["label"], font=text_font(11), fill="#AAAAAA", anchor="mm")
                draw.text((cx, 37), text, font=font, fill=fill, anchor="mm")
            else:
                draw.text((cx, height // 2), text, font=font, fill=fill, anchor="mm")

        if screen.get("dividers") and i < len(sections) - 1:
            draw.line([(x + w, 8), (x + w, height - 8)], fill="#2a2d33", width=1)
        x += w
    return img
