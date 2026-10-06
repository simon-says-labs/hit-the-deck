"""The configurator's web API with aiohttp's test client.

Run: python3 -m unittest discover -s tests
"""
import json
import tempfile
from pathlib import Path

import yaml
from aiohttp.test_utils import AioHTTPTestCase

import support  # noqa: F401
import webapp  # noqa: E402
from settings import Options, Paths  # noqa: E402


class FakeBackend:
    def __init__(self):
        self.track_time_calls = 0

    async def states(self):
        return {"light.desk": {"entity_id": "light.desk", "state": "on", "attributes": {"friendly_name": "Desk"}},
                "fan.ceiling": {"entity_id": "fan.ceiling", "state": "off",
                                "attributes": {"friendly_name": "Ceiling", "percentage_step": 25}}}

    async def language(self):
        return "de"

    async def track_time_state(self):
        self.track_time_calls += 1
        return {"state": "running", "text": "1:05"}


class Base(AioHTTPTestCase):
    allowed = ("127.0.0.1",)  # the test client connects from loopback

    async def get_application(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.paths = Paths(layout=root / "hit_the_deck.yaml", profiles=root / "profiles", data=root)
        self.backend = FakeBackend()
        return webapp.build_app(self.paths, self.backend, allowed=self.allowed)

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self._tmp.cleanup()

    async def post(self, path, body):
        response = await self.client.post(path, data=json.dumps(body), headers={"Content-Type": "application/json"})
        return response.status, await response.json()


class OnlyIngressTest(Base):
    allowed = (webapp.INGRESS_PROXY,)

    async def test_everyone_else_is_refused(self):
        for path in ("/", "/api/layout", "/api/states"):
            response = await self.client.get(path)
            self.assertEqual(response.status, 403, path)
        status, _ = await self.post("/api/layout", {"pages": []})
        self.assertEqual(status, 403)
        self.assertFalse(self.paths.layout.exists())


class LayoutTest(Base):
    async def test_default_layout_until_something_is_saved(self):
        layout = await (await self.client.get("/api/layout")).json()
        kinds = [b["kind"] for b in layout["pages"][0]["buttons"]]
        self.assertIn("track_time_toggle", kinds)

    async def test_saved_layout_lands_in_the_file(self):
        layout = {"brightness": 60, "pages": [{"name": "1", "buttons": [
            {"kind": "entity", "entity_id": "light.desk", "tap_action": "light.toggle"}]}]}
        self.assertEqual(await self.post("/api/layout", layout), (200, {"ok": True}))
        self.assertEqual(yaml.safe_load(self.paths.layout.read_text()), layout)
        self.assertFalse(list(self.paths.layout.parent.glob("*.tmp")))

    async def test_broken_layouts_are_refused(self):
        for body in ([], {"pages": "x"}, {"pages": [{"buttons": [{"kind": "rocket"}]}]}):
            status, answer = await self.post("/api/layout", body)
            self.assertEqual((status, answer["ok"]), (400, False), body)
        self.assertFalse(self.paths.layout.exists())

    async def test_states_are_listed_for_the_entity_picker(self):
        states = await (await self.client.get("/api/states")).json()
        self.assertEqual([s["entity_id"] for s in states], ["fan.ceiling", "light.desk"])
        self.assertEqual(states[0]["percentage_step"], 25)


class PreviewTest(Base):
    async def test_key_preview_is_a_png(self):
        await self.post("/api/layout", {"pages": [{"buttons": [{"kind": "track_time_toggle"}]}]})
        response = await self.client.get("/api/preview?index=0&page=0")
        body = await response.read()
        self.assertEqual((response.status, response.content_type, body[:4]), (200, "image/png", b"\x89PNG"))
        self.assertEqual(self.backend.track_time_calls, 1)

    async def test_entity_preview_does_not_ask_track_time(self):
        await self.post("/api/layout", {"pages": [{"buttons": [{"kind": "entity", "entity_id": "light.desk"}]}]})
        await self.client.get("/api/preview?index=0&page=0")
        self.assertEqual(self.backend.track_time_calls, 0)

    async def test_out_of_range_and_garbage(self):
        self.assertEqual((await self.client.get("/api/preview?index=99&page=7")).status, 200)
        self.assertEqual((await self.client.get("/api/preview?index=x")).status, 400)

    async def test_screen_and_icon_previews(self):
        for path in ("/api/screen-preview", "/api/icon?name=fan", "/api/icon?name=fan&color=nonsense"):
            response = await self.client.get(path)
            self.assertEqual((response.status, response.content_type), (200, "image/png"), path)

    async def test_track_time_state(self):
        self.assertEqual(await (await self.client.get("/api/track-time")).json(), {"state": "running", "text": "1:05"})


class IconSearchTest(Base):
    async def test_words_in_other_languages_find_icons(self):
        for word, icon in (("schalter", "toggle-switch"), ("ventilateur", "fan"), ("luce", "lightbulb")):
            found = (await (await self.client.get("/api/icons?q=" + word)).json())["icons"]
            self.assertIn(icon, found, word)

    async def test_exact_name_comes_first_and_limit_holds(self):
        found = (await (await self.client.get("/api/icons?q=fan&limit=5")).json())["icons"]
        self.assertEqual((found[0], len(found)), ("fan", 5))


class ProfileTest(Base):
    async def test_save_load_and_remove_without_deleting(self):
        await self.post("/api/layout", {"brightness": 30, "pages": []})
        self.assertEqual((await self.post("/api/profile/save", {"name": "Office/../x"}))[1]["name"], "Officex")
        await self.post("/api/layout", {"brightness": 90, "pages": []})
        self.assertEqual(await (await self.client.get("/api/profiles")).json(), ["Officex"])
        self.assertEqual(await self.post("/api/profile/load", {"name": "Officex"}), (200, {"ok": True}))
        self.assertEqual(yaml.safe_load(self.paths.layout.read_text())["brightness"], 30)
        await self.post("/api/profile/remove", {"name": "Officex"})
        self.assertEqual(await (await self.client.get("/api/profiles")).json(), [])
        self.assertEqual(len(list((self.paths.profiles / "removed").glob("Officex-*.yaml"))), 1)

    async def test_missing_profile(self):
        status, _ = await self.post("/api/profile/load", {"name": "nope"})
        self.assertEqual(status, 404)


class DeviceTest(Base):
    async def test_without_a_deck_a_neo_is_shown(self):
        info = await (await self.client.get("/api/device")).json()
        self.assertEqual((info["keys"], info["connected"]), (8, False))

    async def test_written_device_info_is_used(self):
        self.paths.device_info.write_text(json.dumps({"type": "Stream Deck MK.2", "keys": 15, "rows": 3, "cols": 5}))
        info = await (await self.client.get("/api/device")).json()
        self.assertEqual((info["cols"], info["connected"]), (5, True))


class BackendTest(Base):
    async def test_language_option_wins(self):
        backend = webapp.Backend(Options(language="it"), connection=None)
        self.assertEqual(await backend.language(), "it")
        self.assertEqual(await webapp.Backend(Options(), connection=None).language(), "en")


if __name__ == "__main__":
    import unittest
    unittest.main()
