"""Every visible text exists in English, German, French, Italian and Spanish.

Covers the configurator (static/i18n.js), the deck (texts.py), the app options
(translations/*.yaml) and the connection assistant (standalone/connect.py).

Run: python3 -m unittest discover -s tests
"""
import os
import re
import unittest

import yaml

import support  # noqa: F401
import connect  # noqa: E402
import texts  # noqa: E402

APP = os.path.join(support.ROOT, "hit_the_deck")
LANGUAGES = ["en", "de", "fr", "it", "es"]
PLACEHOLDER = re.compile(r"\{\d\}")


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def configurator_texts():
    """Parses i18n.js into {lang: {key: text}} without a JavaScript engine."""
    source = read(APP, "app", "static", "i18n.js")
    result = {}
    for lang, body in re.findall(r"^  (\w\w): \{(.*?)^  \},", source, re.S | re.M):
        result[lang] = dict(re.findall(r'(\w+): "((?:[^"\\]|\\.)*)"', body))
    return result


class ConfiguratorTextsTest(unittest.TestCase):
    def test_same_keys_and_placeholders_in_every_language(self):
        all_texts = configurator_texts()
        self.assertEqual(sorted(all_texts), sorted(LANGUAGES))
        english = all_texts["en"]
        self.assertGreater(len(english), 150)
        for lang in LANGUAGES:
            self.assertEqual(sorted(all_texts[lang]), sorted(english), lang)
            for key, text in all_texts[lang].items():
                self.assertTrue(text.strip(), "%s.%s is empty" % (lang, key))
                self.assertEqual(sorted(PLACEHOLDER.findall(text)), sorted(PLACEHOLDER.findall(english[key])),
                                 "%s.%s placeholders" % (lang, key))

    def test_every_key_the_page_uses_exists(self):
        page = read(APP, "app", "static", "index.html")
        used = set(re.findall(r'data-t(?:-placeholder|-title|-alt)?="(\w+)"', page))
        used |= set(re.findall(r'\bt\("(\w+)"', page))
        used |= set(re.findall(r'\["(chip\w+)"', page))
        used |= set(re.findall(r'(?:secField|secColor)\("(\w+)"', page))
        used |= set(re.findall(r':\s*"(sec[A-Z]\w+)"', page))
        self.assertGreater(len(used), 150)
        self.assertEqual(used - set(configurator_texts()["en"]), set())


class DeckTextsTest(unittest.TestCase):
    def test_deck_texts_weekdays_and_date_formats(self):
        for table in (texts.DECK_TEXTS, texts.WEEKDAYS, texts.WEEKDAYS_SHORT, texts.DATE_FORMAT):
            self.assertEqual(sorted(table), sorted(LANGUAGES))
        for lang in LANGUAGES:
            self.assertEqual(sorted(texts.DECK_TEXTS[lang]), sorted(texts.DECK_TEXTS["en"]), lang)
            self.assertEqual(len(texts.WEEKDAYS[lang]), 7)
            self.assertEqual(len(texts.WEEKDAYS_SHORT[lang]), 7)

    def test_icon_words_for_every_language_but_english(self):
        self.assertEqual(sorted(texts.ICON_WORDS), sorted(set(LANGUAGES) - {"en"}))

    def test_language_choice(self):
        self.assertEqual(texts.pick_language("auto", "de"), "de")
        self.assertEqual(texts.pick_language("auto", "en-GB"), "en")
        self.assertEqual(texts.pick_language("fr", "de"), "fr")
        self.assertEqual(texts.pick_language("auto", "nl"), "en")


class OptionTextsTest(unittest.TestCase):
    def test_every_option_is_named_and_described(self):
        schema = yaml.safe_load(read(APP, "config.yaml"))["schema"]
        for lang in LANGUAGES:
            configuration = yaml.safe_load(read(APP, "translations", lang + ".yaml"))["configuration"]
            self.assertEqual(sorted(configuration), sorted(schema), lang)
            for option, entry in configuration.items():
                self.assertTrue(entry.get("name") and entry.get("description"), "%s: %s" % (lang, option))


class AssistantTextsTest(unittest.TestCase):
    def test_same_keys_and_placeholders(self):
        english = connect.TEXTS["en"]
        self.assertEqual(sorted(connect.TEXTS), sorted(LANGUAGES))
        for lang in LANGUAGES:
            self.assertEqual(sorted(connect.TEXTS[lang]), sorted(english), lang)
            for key, text in connect.TEXTS[lang].items():
                if isinstance(text, str):
                    self.assertEqual(sorted(PLACEHOLDER.findall(text)), sorted(PLACEHOLDER.findall(english[key])),
                                     "%s.%s" % (lang, key))
            self.assertEqual(sorted(connect.STORE_NAMES[lang]), sorted(connect.STORE_NAMES["en"]))


if __name__ == "__main__":
    unittest.main()
