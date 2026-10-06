#!/usr/bin/env python3
"""Runs Hit the Deck on a computer with a Stream Deck plugged into it.

    python3 standalone/run.py [--port 8099]

Run standalone/connect.py once before. The configurator opens on http://127.0.0.1:<port>
and is reachable from this computer only. Key layout, profiles and options live in the
user's config folder (macOS: ~/Library/Application Support/hit-the-deck, Windows:
%APPDATA%\\hit-the-deck, Linux: ~/.config/hit-the-deck); the token stays in the keychain.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "hit_the_deck" / "app"
sys.path.insert(0, str(APP))
import credentials  # noqa: E402

DEFAULT_OPTIONS = {"language": "auto", "auto_brightness": False, "brightness_min": 10}
EXIT_DEVICE_GONE = 3


def environment(config_dir: Path, url: str, port: int, base=None) -> dict:
    env = dict(os.environ if base is None else base)
    env.pop("SUPERVISOR_TOKEN", None)
    env.update({"HTD_CONFIG_DIR": str(config_dir), "HTD_DATA_DIR": str(config_dir / "data"),
                "HTD_OPTIONS": str(config_dir / "options.json"), "HTD_HA_URL": url,
                "HTD_WEB_HOST": "127.0.0.1", "HTD_WEB_PORT": str(port)})
    return env


def prepare(config_dir: Path) -> str:
    """The saved Home Assistant URL; creates the data folder and default options."""
    try:
        url = json.loads((config_dir / "connection.json").read_text())["url"]
    except (OSError, ValueError, KeyError):
        return ""
    (config_dir / "data").mkdir(parents=True, exist_ok=True)
    options = config_dir / "options.json"
    if not options.exists():
        options.write_text(json.dumps(DEFAULT_OPTIONS, indent=2))
    return url


def stop_like_ctrl_c(*_):
    raise KeyboardInterrupt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run Hit the Deck on this computer.")
    parser.add_argument("--port", type=int, default=8099, help="port of the configurator (default 8099)")
    args = parser.parse_args(argv)

    config_dir = credentials.user_config_dir()
    url = prepare(config_dir)
    if not url or credentials.open_store(config_dir) is None:
        print("Not connected yet. Run:  python3 standalone/connect.py", flush=True)
        return 2
    env = environment(config_dir, url, args.port)
    # SIGTERM (e.g. from a service manager) ends like Ctrl+C, so both child processes stop too.
    signal.signal(signal.SIGTERM, stop_like_ctrl_c)
    print("Configurator: http://127.0.0.1:%d   (stop with Ctrl+C)" % args.port, flush=True)
    web = subprocess.Popen([sys.executable, "-u", str(APP / "webapp.py")], cwd=str(APP), env=env)
    try:
        while True:
            # On a computer a re-plugged deck is visible to a new process, so restart instead of exiting.
            code = subprocess.call([sys.executable, "-u", str(APP / "runtime.py")], cwd=str(APP), env=env)
            if code != EXIT_DEVICE_GONE:
                return code
            print("Stream Deck gone, looking for it again in 5 s", flush=True)
            time.sleep(5)
    except KeyboardInterrupt:
        return 0
    finally:
        web.terminate()
        web.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
