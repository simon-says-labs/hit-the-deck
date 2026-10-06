"""Options and file locations.

Inside Home Assistant: options in /data/options.json, the key layout and profiles in the
app's configuration folder (/config), runtime state in /data. On a computer,
standalone/run.py points the HTD_* variables at the user's config folder.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass
class Options:
    language: str = "auto"
    auto_brightness: bool = False
    brightness_light_entity: str = ""
    brightness_min: int = 10
    track_time_url: str = ""
    track_time_api_key: str = ""

    @classmethod
    def load(cls, path=None) -> "Options":
        path = path or os.environ.get("HTD_OPTIONS", "/data/options.json")
        try:
            raw = json.loads(Path(path).read_text()) or {}
        except (OSError, ValueError):
            raw = {}
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in names and v is not None})


@dataclass
class Paths:
    layout: Path
    profiles: Path
    data: Path

    @classmethod
    def from_env(cls, env=None) -> "Paths":
        env = os.environ if env is None else env
        config = Path(env.get("HTD_CONFIG_DIR", "/config"))
        return cls(layout=config / "hit_the_deck.yaml", profiles=config / "profiles",
                   data=Path(env.get("HTD_DATA_DIR", "/data")))

    @property
    def device_info(self) -> Path:
        return self.data / "device.json"

    @property
    def page(self) -> Path:
        return self.data / "page.json"


DEFAULT_LAYOUT = Path(__file__).resolve().parent / "default-layout.yaml"
