# Contributing

Thanks for your interest in Hit the Deck. Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/simon-says-labs/hit-the-deck/issues) with your Home Assistant
version, the app version, your Stream Deck model, what you expected and what happened, and the
relevant lines of the app log (**Settings → Apps → Hit the Deck → Log**). Never paste a token.

## Development

No Stream Deck is needed for the tests.

```bash
python3 -m venv .venv && .venv/bin/pip install pillow pyyaml aiohttp websockets keyring
.venv/bin/python -m unittest discover -s tests     # runtime, drawing, Track Time, configurator, texts
.venv/bin/python tools/demo.py                     # configurator with made-up entities on 127.0.0.1:8099
docker build -t hit-the-deck:dev hit_the_deck      # the app image
```

| File | Does |
|---|---|
| `hit_the_deck/app/runtime.py` | talks to the deck and to Home Assistant |
| `hit_the_deck/app/render.py` | draws keys and the info bar (also used by the configurator) |
| `hit_the_deck/app/webapp.py`, `static/` | the configurator |
| `hit_the_deck/app/track_time.py` | finds and calls Track Time |
| `standalone/` | running on a computer instead of inside Home Assistant |

## Pull requests

- One topic per pull request, with a test that fails without your change.
- Every configurator text goes through `t("key")` and needs all five languages in `static/i18n.js`;
  deck texts live in `texts.py`, option texts in `translations/*.yaml`. The tests check all of them.
- Add a line to `hit_the_deck/CHANGELOG.md` under an `Unreleased` heading.
