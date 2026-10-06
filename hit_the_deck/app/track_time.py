"""The Track Time keys talk to the Track Time app (https://github.com/simon-says-labs/track-time).

Inside Home Assistant Hit the Deck finds Track Time on its own. The Supervisor names an app
"<repository id>_<slug>", where the repository id is the first 8 hex digits of the SHA-1 of
the repository URL ("local" for apps in the local folder), and gives it the host name with
dashes instead of underscores. Hit the Deck asks the Supervisor for the info of those two
candidates (allowed for every app) and uses Track Time's internal port, which accepts other
apps on the Supervisor network. The track_time_url option overrides all of this, e.g.
http://<host>:7979 together with track_time_api_key.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request

REPOSITORY = "https://github.com/simon-says-labs/track-time"
SLUG = "track_time"
INTERNAL_PORT = 8099
TIMEOUT = 3
OFFLINE = {"state": "offline", "text": ""}


def repository_id(url: str) -> str:
    """The Supervisor's id for a repository URL (supervisor/store/utils.py)."""
    return hashlib.sha1(url.lower().encode()).hexdigest()[:8]


def candidate_slugs() -> list:
    return ["%s_%s" % (repository_id(REPOSITORY), SLUG), "local_" + SLUG]


def http_json(url: str, method: str = "GET", headers=None, timeout: float = TIMEOUT):
    """JSON from url, or None when there is no answer or no JSON."""
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:  # e.g. 401 with a wrong API key
        error.close()
        return None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def discover(supervisor_token: str, fetch=http_json):
    """Base URL of a running Track Time app, or None."""
    if not supervisor_token:
        return None
    for slug in candidate_slugs():
        info = fetch("http://supervisor/addons/%s/info" % slug,
                     headers={"Authorization": "Bearer " + supervisor_token}) or {}
        data = info.get("data") or {}
        if data.get("state") == "started" and data.get("hostname"):
            return "http://%s:%d" % (data["hostname"], INTERNAL_PORT)
    return None


class TrackTime:
    def __init__(self, base_url: str, api_key: str = "", fetch=http_json):
        self.base_url = base_url.rstrip("/")
        self._headers = {"X-Api-Key": api_key} if api_key else {}
        self._fetch = fetch

    def __repr__(self) -> str:
        return "TrackTime(%r)" % self.base_url

    def _call(self, path: str, method: str = "GET"):
        return self._fetch(self.base_url + path, method=method, headers=self._headers)

    def state(self) -> dict:
        """{"state": running|paused|stopped|offline, "text": time worked today (H:MM)}."""
        data = self._call("/api/state")
        if not data or data.get("state") not in ("running", "paused", "stopped"):
            return dict(OFFLINE)
        return {"state": data["state"], "text": data.get("today_text") or data.get("elapsed_text") or ""}

    def toggle(self) -> dict:
        """stopped -> start, running -> pause, paused -> resume."""
        return self.state() if self._call("/api/toggle", "POST") else dict(OFFLINE)

    def stop(self) -> dict:
        return self.state() if self._call("/api/stop", "POST") else dict(OFFLINE)


def connect(options, supervisor_token: str, api_key: str = "", fetch=http_json):
    """TrackTime from the option, else from discovery; None if neither is there.

    api_key is the key from the keychain in standalone mode; the option wins if both are set.
    """
    if options.track_time_url:
        return TrackTime(options.track_time_url, options.track_time_api_key or api_key, fetch)
    base_url = discover(supervisor_token, fetch)
    return TrackTime(base_url, "", fetch) if base_url else None
