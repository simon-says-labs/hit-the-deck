"""Secrets for standalone mode (Hit the Deck on a computer instead of inside Home Assistant).

Secrets go into the system keychain through the keyring library: Keychain on macOS,
Credential Manager on Windows, Secret Service (GNOME Keyring, KWallet) on Linux.
Only when no keychain exists, and only after the user agreed, a file readable by the
user alone (mode 600) is used instead. Secrets never go into options, logs or the environment.

Inside Home Assistant none of this is used: the Supervisor hands the app its own token.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

SERVICE = "hit-the-deck"
HOME_ASSISTANT_TOKEN = "home_assistant_token"
TRACK_TIME_API_KEY = "track_time_api_key"


def user_config_dir(platform: str = sys.platform, env=None, home: Path = None) -> Path:
    env = os.environ if env is None else env
    home = home or Path.home()
    if platform == "darwin":
        return home / "Library" / "Application Support" / SERVICE
    if platform.startswith("win"):
        return Path(env.get("APPDATA") or home / "AppData" / "Roaming") / SERVICE
    return Path(env.get("XDG_CONFIG_HOME") or home / ".config") / SERVICE


class NoKeychain(Exception):
    """No usable system keychain on this computer."""


class KeychainStore:
    """Stores secrets in the system keychain."""

    name = "system keychain"

    def __init__(self, keyring_module=None):
        if keyring_module is None:
            try:
                import keyring as keyring_module
            except ImportError as exc:
                raise NoKeychain("the keyring package is not installed") from exc
        backend = keyring_module.get_keyring()
        if "fail" in type(backend).__module__ or getattr(backend, "priority", 1) <= 0:
            raise NoKeychain("no keychain backend available (%s)" % type(backend).__name__)
        self._keyring = keyring_module

    def get(self, key: str) -> str:
        return self._keyring.get_password(SERVICE, key) or ""

    def set(self, key: str, value: str) -> None:
        self._keyring.set_password(SERVICE, key, value)

    def remove(self, key: str) -> None:
        if self.get(key):
            self._keyring.delete_password(SERVICE, key)


class FileStore:
    """Fallback: a JSON file only the current user can read (mode 600)."""

    name = "private file"

    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle)
        os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)

    def get(self, key: str) -> str:
        return self._read().get(key, "")

    def set(self, key: str, value: str) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def remove(self, key: str) -> None:
        data = self._read()
        if data.pop(key, None) is not None:
            self._write(data)


def secrets_file(config_dir: Path) -> Path:
    return Path(config_dir) / "secrets.json"


def open_store(config_dir: Path, keyring_module=None):
    """The keychain if there is one, else the private file if the user chose it before, else None."""
    try:
        return KeychainStore(keyring_module)
    except NoKeychain:
        path = secrets_file(config_dir)
        return FileStore(path) if path.exists() else None
