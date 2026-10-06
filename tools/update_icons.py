#!/usr/bin/env python3
"""Refreshes the bundled Material Design Icons from the official @mdi/font package.

Downloads the npm tarball of the given version, checks its integrity hash, copies the TTF and
the license, and writes the name -> codepoint table the renderer uses.

    python3 tools/update_icons.py 7.4.47

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "hit_the_deck" / "app" / "assets" / "mdi"
REGISTRY = "https://registry.npmjs.org/@mdi/font"
RULE = re.compile(r'\.mdi-([a-z0-9-]+)::before\s*\{\s*content:\s*"\\([0-9A-Fa-f]+)"')


def codepoints_from_css(css: str) -> dict:
    """{"ab-testing": 0xF01C9, ...} from materialdesignicons.css."""
    return {name: int(code, 16) for name, code in RULE.findall(css)}


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main(version: str) -> int:
    meta = json.loads(fetch(REGISTRY))["versions"][version]["dist"]
    tarball = fetch(meta["tarball"])
    algorithm, expected = meta["integrity"].split("-", 1)
    if base64.b64encode(hashlib.new(algorithm, tarball).digest()).decode() != expected:
        print("integrity check failed", file=sys.stderr)
        return 1
    with tarfile.open(fileobj=io.BytesIO(tarball)) as archive:
        read = lambda name: archive.extractfile("package/" + name).read()  # noqa: E731
        css = read("css/materialdesignicons.css").decode()
        TARGET.mkdir(parents=True, exist_ok=True)
        (TARGET / "mdi.ttf").write_bytes(read("fonts/materialdesignicons-webfont.ttf"))
        (TARGET / "LICENSE").write_bytes(read("LICENSE"))
    table = codepoints_from_css(css)
    (TARGET / "mdi-codepoints.json").write_text(json.dumps(table, sort_keys=True, separators=(",", ":")))
    (TARGET / "VERSION").write_text(version + "\n")
    print("%d icons from @mdi/font %s" % (len(table), version))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "7.4.47"))
