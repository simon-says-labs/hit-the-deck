"""The key layout file (hit_the_deck.yaml): reading it and its pages.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import yaml


def load(path, fallback=None) -> dict:
    """The layout from path, else from fallback, else empty."""
    for candidate in (path, fallback):
        if candidate is None:
            continue
        try:
            return yaml.safe_load(candidate.read_text()) or {}
        except FileNotFoundError:
            continue
        except (OSError, yaml.YAMLError) as exc:
            print("[WARN] key layout %s not readable: %s" % (candidate, exc), flush=True)
    return {}


def pages_of(layout: dict) -> list:
    """`pages: [{name, buttons}]`; a plain `buttons:` list counts as one page."""
    pages = layout.get("pages")
    if isinstance(pages, list) and pages:
        return pages
    return [{"name": "1", "buttons": layout.get("buttons", [])}]
