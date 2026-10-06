"""The connection assistant (standalone/connect.py) and the secret store, without network or keychain.

The most important check: the token ends up in the keychain and nowhere else - not on screen,
not in a file next to the configuration.

Run: python3 -m unittest discover -s tests
"""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
import connect  # noqa: E402
import credentials  # noqa: E402

TOKEN = "eyFAKE.token-for-tests.only"
URL = "http://homeassistant.local:8123"


class FakeConsole:
    def __init__(self, answers=(), hidden=()):
        self.answers, self.hidden = list(answers), list(hidden)
        self.output, self.opened = [], []

    def say(self, text):
        self.output.append(text)

    def ask(self, prompt):
        self.output.append(prompt)
        return self.answers.pop(0)

    def ask_hidden(self, prompt):
        self.output.append(prompt)
        return self.hidden.pop(0)

    def open_browser(self, url):
        self.opened.append(url)
        return True


class FakeKeyring:
    """Behaves like the keyring package with a working backend."""

    class Backend:
        priority = 5

    def __init__(self):
        self.saved = {}

    def get_keyring(self):
        return self.Backend()

    def get_password(self, service, key):
        return self.saved.get((service, key))

    def set_password(self, service, key, value):
        self.saved[(service, key)] = value

    def delete_password(self, service, key):
        del self.saved[(service, key)]


class NoKeyring(FakeKeyring):
    class Backend:
        priority = 0


def fake_home_assistant(valid_tokens=(TOKEN,), track_time=None):
    """status(url, token, key) like Home Assistant (and optionally Track Time) would answer."""
    def status(url, token="", key="", timeout=8):
        if url.startswith(URL):
            if url.endswith("/api/"):
                return 200 if token in valid_tokens else 401
        if track_time and url.startswith(track_time["url"]):
            if url.endswith("/healthz"):
                return 200
            return 200 if key == track_time["key"] else 401
        return None
    return status


class AssistantTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.keyring = FakeKeyring()

    def tearDown(self):
        self._tmp.cleanup()

    def assistant(self, console, status=None, keyring=None):
        return connect.Assistant(console, self.dir, status or fake_home_assistant(), keyring or self.keyring, "en")

    def files_text(self):
        return "".join(p.read_text(errors="ignore") for p in self.dir.rglob("*") if p.is_file())

    def test_token_goes_to_the_keychain_only(self):
        console = FakeConsole(answers=["", ""], hidden=["  " + TOKEN + "\n"])
        self.assertEqual(self.assistant(console).run(), 0)
        self.assertEqual(self.keyring.saved[(credentials.SERVICE, credentials.HOME_ASSISTANT_TOKEN)], TOKEN)
        self.assertEqual(console.opened, [URL + "/profile/security"])
        self.assertEqual(json.loads((self.dir / "connection.json").read_text()), {"url": URL})
        self.assertNotIn(TOKEN, "\n".join(console.output))
        self.assertNotIn(TOKEN, self.files_text())

    def test_wrong_token_is_rejected_and_asked_again(self):
        console = FakeConsole(answers=["homeassistant.local:8123/", ""], hidden=["wrong", TOKEN])
        self.assertEqual(self.assistant(console).run(), 0)
        self.assertIn(connect.TEXTS["en"]["rejected"], console.output)

    def test_three_wrong_tokens_save_nothing(self):
        console = FakeConsole(answers=[""], hidden=["a", "b", "c"])
        self.assertEqual(self.assistant(console).run(), 1)
        self.assertEqual(self.keyring.saved, {})
        self.assertFalse((self.dir / "connection.json").exists())

    def test_unreachable_address_is_asked_again(self):
        console = FakeConsole(answers=["http://192.0.2.1:8123", "", ""], hidden=[TOKEN])
        self.assertEqual(self.assistant(console).run(), 0)
        self.assertIn(connect.TEXTS["en"]["unreachable"].format("http://192.0.2.1:8123"), console.output)

    def test_without_keychain_the_private_file_needs_a_yes(self):
        console = FakeConsole(answers=["", "n"], hidden=[TOKEN])
        self.assertEqual(self.assistant(console, keyring=NoKeyring()).run(), 1)
        self.assertFalse(credentials.secrets_file(self.dir).exists())

        console = FakeConsole(answers=["", "y", ""], hidden=[TOKEN])
        self.assertEqual(self.assistant(console, keyring=NoKeyring()).run(), 0)
        path = credentials.secrets_file(self.dir)
        self.assertEqual(json.loads(path.read_text())[credentials.HOME_ASSISTANT_TOKEN], TOKEN)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_track_time_address_and_key(self):
        tt = {"url": "http://homeassistant.local:7979", "key": "tt-key"}
        console = FakeConsole(answers=["", tt["url"]], hidden=[TOKEN, "tt-key"])
        self.assertEqual(self.assistant(console, fake_home_assistant(track_time=tt)).run(), 0)
        self.assertEqual(self.keyring.saved[(credentials.SERVICE, credentials.TRACK_TIME_API_KEY)], "tt-key")
        self.assertEqual(json.loads((self.dir / "options.json").read_text())["track_time_url"], tt["url"])
        self.assertNotIn("tt-key", self.files_text())

    def test_forget_removes_both_secrets(self):
        self.keyring.set_password(credentials.SERVICE, credentials.HOME_ASSISTANT_TOKEN, TOKEN)
        self.keyring.set_password(credentials.SERVICE, credentials.TRACK_TIME_API_KEY, "k")
        self.assertEqual(self.assistant(FakeConsole()).forget(), 0)
        self.assertEqual(self.keyring.saved, {})

    def test_language_from_the_environment(self):
        self.assertEqual(connect.system_language({"LANG": "de_DE.UTF-8"}), "de")
        self.assertEqual(connect.system_language({"LC_ALL": "it_IT.UTF-8", "LANG": "de_DE"}), "it")

    def test_url_is_normalised(self):
        self.assertEqual(connect.normalise_url(" homeassistant.local:8123/ "), URL)
        self.assertEqual(connect.normalise_url("https://ha.example/"), "https://ha.example")


class StoreTest(unittest.TestCase):
    def test_config_folder_per_system(self):
        home = Path("/home/alex")
        self.assertEqual(credentials.user_config_dir("darwin", {}, home),
                         home / "Library" / "Application Support" / "hit-the-deck")
        self.assertEqual(credentials.user_config_dir("win32", {"APPDATA": "C:\\Users\\alex\\AppData\\Roaming"}, home),
                         Path("C:\\Users\\alex\\AppData\\Roaming") / "hit-the-deck")
        self.assertEqual(credentials.user_config_dir("linux", {}, home), home / ".config" / "hit-the-deck")

    def test_keychain_without_backend_is_refused(self):
        with self.assertRaises(credentials.NoKeychain):
            credentials.KeychainStore(NoKeyring())

    def test_open_store_prefers_the_keychain(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsInstance(credentials.open_store(Path(tmp), FakeKeyring()), credentials.KeychainStore)
            self.assertIsNone(credentials.open_store(Path(tmp), NoKeyring()))

    def test_connection_never_prints_the_token(self):
        import home_assistant
        store = credentials.KeychainStore(FakeKeyring())
        store.set(credentials.HOME_ASSISTANT_TOKEN, TOKEN)
        connection = home_assistant.connection_from_environment({"HTD_HA_URL": "https://ha.example/"}, store)
        self.assertEqual((connection.rest, connection.websocket), ("https://ha.example/api", "wss://ha.example/api/websocket"))
        self.assertNotIn(TOKEN, repr(connection))
        with self.assertRaises(RuntimeError):
            home_assistant.connection_from_environment({}, None)


if __name__ == "__main__":
    unittest.main()
