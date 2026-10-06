"""The default options pass the Supervisor's own option check.

The Supervisor validates every option that is present, also an empty optional one: a "?" only
allows the key to be missing (supervisor/apps/options.py). An empty default for a match() type
therefore stops the app from starting. This test repeats the Supervisor's type rules.

Run: python3 -m unittest discover -s tests   (needs PyYAML)
"""
import os
import re
import unittest

import yaml

CONFIG = os.path.join(os.path.dirname(__file__), "..", "hit_the_deck", "config.yaml")
TYPE = re.compile(r"^(?P<name>str|password|int|float|bool|email|url|port|match|list)(?:\((?P<arg>.*)\))?(?P<optional>\?)?$")


def check(type_, value):
    """Raises ValueError if value would fail the Supervisor's check for type_."""
    found = TYPE.match(type_)
    if not found:
        raise ValueError("unknown type %s" % type_)
    name, arg = found["name"], found["arg"]
    if name in ("str", "password"):
        if not isinstance(value, (str, int, float)):
            raise ValueError("not a string")
    elif name == "int":
        number = int(value)
        if arg:
            low, high = (float(x) if x else None for x in arg.split(","))
            if (low is not None and number < low) or (high is not None and number > high):
                raise ValueError("out of range")
    elif name == "bool":
        if not isinstance(value, bool):
            raise ValueError("not a boolean")
    elif name == "match":
        if not re.match(arg, str(value)):
            raise ValueError("%r does not match %s" % (value, arg))
    elif name == "list":
        if str(value) not in arg.split("|"):
            raise ValueError("%r not in %s" % (value, arg))
    elif name == "url":
        if not re.match(r"^https?://[^\s/]+", str(value)):
            raise ValueError("not a URL")


class OptionDefaultsTest(unittest.TestCase):
    def setUp(self):
        with open(CONFIG, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def test_every_default_passes_its_type(self):
        schema = self.config["schema"]
        for key, value in self.config["options"].items():
            types = schema[key]
            for item in (value if isinstance(types, list) else [value]):
                with self.subTest(option=key, value=item):
                    check(types[0] if isinstance(types, list) else types, item)

    def test_required_options_have_defaults(self):
        for key, type_ in self.config["schema"].items():
            first = type_[0] if isinstance(type_, list) else type_
            if not str(first).endswith("?"):
                self.assertIn(key, self.config["options"], key)

    def test_language_default_is_allowed(self):
        check(self.config["schema"]["language"], self.config["options"]["language"])
        with self.assertRaises(ValueError):
            check(self.config["schema"]["language"], "nl")

    def test_checker_rejects_what_the_supervisor_rejects(self):
        with self.assertRaises(ValueError):
            check(r"match(^person\.[a-z0-9_]+$)?", "")
        with self.assertRaises(ValueError):
            check("int(7,3650)", 3)
        check(r"match(^person\.[a-z0-9_]+$)?", "person.alex")


if __name__ == "__main__":
    unittest.main()
