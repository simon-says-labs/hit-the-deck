"""Finding and talking to Track Time, also against a real local HTTP server that behaves like it.

Run: python3 -m unittest discover -s tests
"""
import hashlib
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import ImageChops

import support  # noqa: F401
import render  # noqa: E402
import track_time  # noqa: E402
from settings import Options  # noqa: E402


class DiscoveryTest(unittest.TestCase):
    def test_repository_id_is_the_supervisors(self):
        expected = hashlib.sha1(b"https://github.com/simon-says-labs/track-time").hexdigest()[:8]
        self.assertEqual(track_time.repository_id("https://github.com/Simon-Says-Labs/track-time"), expected)
        self.assertEqual(track_time.candidate_slugs(), [expected + "_track_time", "local_track_time"])

    def test_finds_the_started_app_and_uses_its_hostname(self):
        asked = []

        def fetch(url, method="GET", headers=None):
            asked.append((url, headers))
            if url.endswith("local_track_time/info"):
                return {"result": "ok", "data": {"state": "started", "hostname": "local-track-time"}}
            return {"result": "error", "message": "App is not installed"}

        self.assertEqual(track_time.discover("token", fetch), "http://local-track-time:8099")
        self.assertEqual(asked[0][1], {"Authorization": "Bearer token"})
        self.assertTrue(asked[0][0].startswith("http://supervisor/addons/"))

    def test_stopped_app_is_not_used(self):
        fetch = lambda url, **_: {"data": {"state": "stopped", "hostname": "x"}}  # noqa: E731
        self.assertIsNone(track_time.discover("token", fetch))

    def test_without_supervisor_there_is_nothing_to_discover(self):
        self.assertIsNone(track_time.discover("", lambda *a, **k: self.fail("must not ask")))

    def test_option_wins_over_discovery(self):
        options = Options(track_time_url="http://192.0.2.10:7979", track_time_api_key="k")
        client = track_time.connect(options, "token", fetch=lambda *a, **k: self.fail("must not discover"))
        self.assertEqual((client.base_url, client._headers), ("http://192.0.2.10:7979", {"X-Api-Key": "k"}))

    def test_keychain_key_is_used_when_the_option_is_empty(self):
        client = track_time.connect(Options(track_time_url="http://h:7979"), "", api_key="from-keychain")
        self.assertEqual(client._headers, {"X-Api-Key": "from-keychain"})


class FakeTrackTimeServer(BaseHTTPRequestHandler):
    """Answers like Track Time's REST API; requires the API key when one is set."""
    state = "stopped"
    api_key = "secret"

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _allowed(self):
        if self.headers.get("X-Api-Key") != type(self).api_key:
            self._send(401, {"ok": False, "error": "api key required"})
            return False
        return True

    def do_GET(self):
        if self._allowed() and self.path == "/api/state":
            self._send(200, {"state": type(self).state, "since": None, "paused_since": None,
                             "elapsed_text": "0:00", "today_text": "3:10" if type(self).state != "stopped" else "0:00"})

    def do_POST(self):
        if not self._allowed():
            return
        cls = type(self)
        action = None
        if self.path == "/api/toggle":
            action = {"stopped": "start", "running": "pause", "paused": "resume"}[cls.state]
            cls.state = {"stopped": "running", "running": "paused", "paused": "running"}[cls.state]
        elif self.path == "/api/stop" and cls.state != "stopped":
            action, cls.state = "stop", "stopped"
        self._send(200, {"ok": True, "action": action, "state": {"state": cls.state}})

    def log_message(self, *args):
        pass


class AgainstAServerTest(unittest.TestCase):
    def setUp(self):
        FakeTrackTimeServer.state = "stopped"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeTrackTimeServer)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.running = True

    def tearDown(self):
        self.stop_server()

    def stop_server(self):
        if self.running:
            self.server.shutdown()
            self.server.server_close()
            self.running = False

    def test_toggle_shows_running_on_the_key(self):
        client = track_time.connect(Options(track_time_url=self.url, track_time_api_key="secret"), "")
        self.assertEqual(client.state(), {"state": "stopped", "text": "0:00"})
        after = client.toggle()
        self.assertEqual(after, {"state": "running", "text": "3:10"})
        key = render.render_track_time_toggle(after)
        expected = render.render_track_time_toggle({"state": "running", "text": "3:10"})
        self.assertIsNone(ImageChops.difference(key, expected).getbbox())
        self.assertEqual(client.toggle()["state"], "paused")
        self.assertEqual(client.stop()["state"], "stopped")

    def test_wrong_key_shows_offline(self):
        client = track_time.TrackTime(self.url, "wrong")
        self.assertEqual(client.state(), track_time.OFFLINE)
        self.assertEqual(client.toggle(), track_time.OFFLINE)
        self.assertEqual(FakeTrackTimeServer.state, "stopped")

    def test_nobody_listening_shows_offline(self):
        self.stop_server()
        self.assertEqual(track_time.TrackTime(self.url, "secret").state(), track_time.OFFLINE)


if __name__ == "__main__":
    unittest.main()
