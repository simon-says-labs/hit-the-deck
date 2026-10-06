"""Shared test setup: the app folder on sys.path and stand-ins for the Stream Deck library,
so every test runs without a device and without hidapi.
"""
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(ROOT, "hit_the_deck", "app")
STANDALONE = os.path.join(ROOT, "standalone")
for path in (APP, STANDALONE):
    if path not in sys.path:
        sys.path.insert(0, path)


class TransportError(Exception):
    """Stand-in for StreamDeck.Transport.Transport.TransportError."""


class PILHelper:
    @staticmethod
    def to_native_key_format(deck, image):
        return image

    @staticmethod
    def to_native_screen_format(deck, image):
        return image


def install_streamdeck_stubs():
    if "StreamDeck" in sys.modules and getattr(sys.modules["StreamDeck"], "_stub", False):
        return
    for name in ("StreamDeck", "StreamDeck.DeviceManager", "StreamDeck.ImageHelpers",
                 "StreamDeck.Transport", "StreamDeck.Transport.Transport"):
        module = types.ModuleType(name)
        module._stub = True
        sys.modules[name] = module
    sys.modules["StreamDeck.DeviceManager"].DeviceManager = object
    sys.modules["StreamDeck.ImageHelpers"].PILHelper = PILHelper
    sys.modules["StreamDeck.Transport.Transport"].TransportError = TransportError


install_streamdeck_stubs()
