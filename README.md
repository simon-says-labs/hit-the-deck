<p align="center"><img src="hit_the_deck/logo.png" width="250" alt="Hit the Deck logo"></p>

# Hit the Deck

**Simon says: hit the deck!** A Stream Deck plugged into your Home Assistant machine becomes a
remote for lights, switches, scenes, fans and sensors. Assign the keys in a configurator in the
Home Assistant sidebar; it draws them exactly as the deck does. Made for the Stream Deck Neo.

[![Add the repository to your Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsimon-says-labs%2Fhit-the-deck)

> **Kurz auf Deutsch:** Hit the Deck macht ein Stream Deck am Home-Assistant-Rechner zur
> Fernbedienung für Licht, Schalter, Szenen, Ventilatoren und Sensoren. Die Tasten belegst du in
> einem Konfigurator in der Seitenleiste. Zusammen mit [Track Time](https://github.com/simon-says-labs/track-time)
> startet, pausiert und beendet eine Taste deinen Arbeitstag. Oberfläche auf Deutsch, Englisch,
> Französisch, Italienisch und Spanisch.

<p align="center"><img src="docs/configurator.png" width="820" alt="The configurator: eight keys of a Stream Deck Neo with a lamp, a fan, a gauge, Track Time running at 3:10, a coffee machine, a meter, a scene and a stop key; the info bar with clock and date below; the key editor on the right"></p>

## Works best with Track Time

[Track Time](https://github.com/simon-says-labs/track-time) is a time tracker for Home Assistant.
Hit the Deck finds it on its own and gives you two keys for your working day:

<p align="center"><img src="docs/keys.png" width="560" alt="Keys as drawn on the deck; the Track Time key is green and shows 3:10, the stop key is red"></p>

| Key | Does |
|---|---|
| Track Time: start / pause / resume | stopped → start, running → pause, paused → resume; shows the time worked today |
| Track Time: stop | ends the working day, also from a pause |

## Features

- **Entity keys** with icons and colours from the entity's state, in four layouts: full icon,
  icon + value, gauge and meter. A press runs any action, a sequence of actions or a fan preset.
- **Pages**, switched by keys or by the Neo's two touch points.
- **Info bar** of the Stream Deck Neo: clock, date, entity states and text, with gradients and
  ready-made templates.
- **Configurator in the sidebar** with live previews, an icon gallery (Material Design Icons,
  searchable in five languages), profiles, export and import. Changes reach the deck at once.
- **Dims at night** while a light entity you choose is off.
- **Recovers from USB resets** together with the app's watchdog.
- **Five languages**: English, German, French, Italian, Spanish.

## Installation in Home Assistant

1. Click the button above, or add `https://github.com/simon-says-labs/hit-the-deck` as a repository in
   the app store under **Settings → Apps**.
2. Plug the Stream Deck into the Home Assistant machine.
3. Install **Hit the Deck**, turn on **Watchdog** and **Show in sidebar**, and start it.
4. Optional: install [Track Time](https://github.com/simon-says-labs/track-time) for the time keys.

Requires Home Assistant OS or Supervised on a 64-bit machine (`aarch64` or `amd64`), for example
a Raspberry Pi 4 or 5. Every option is described in [DOCS.md](hit_the_deck/DOCS.md).

## Standalone: on a computer

Hit the Deck also runs on a Mac, Windows or Linux computer with the Stream Deck plugged into it.
It then needs a long-lived access token, and a small assistant creates the connection with you:

```bash
pip install -r standalone/requirements.txt   # plus hidapi, see python-elgato-streamdeck's docs
python3 standalone/connect.py                # once
python3 standalone/run.py                    # configurator on http://127.0.0.1:8099
```

`connect.py` checks the Home Assistant address, opens your profile's security page in the browser
where you create the token, reads the pasted token without showing it, checks it against Home
Assistant and stores it in the system keychain. The token never lands in a file of this project,
a log or the screen. `connect.py --forget` removes it. The native USB library comes from
[python-elgato-streamdeck](https://python-elgato-streamdeck.readthedocs.io/en/stable/pages/backend_libusb_hidapi.html)'s installation guide.

## Security

- Inside Home Assistant there is no token to create: the Supervisor gives the app its access.
- The configurator answers Home Assistant's ingress only (standalone: 127.0.0.1 only).
- The app asks for USB hardware rights to open the Stream Deck; [SECURITY.md](SECURITY.md) explains
  why and how to report vulnerabilities.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install pillow pyyaml aiohttp websockets keyring
.venv/bin/python -m unittest discover -s tests   # no Stream Deck needed
.venv/bin/python tools/demo.py                   # the configurator with made-up entities
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [hit_the_deck/CHANGELOG.md](hit_the_deck/CHANGELOG.md).

## License

[MIT](LICENSE) © 2026 Simon Eckmiller · published by [Simon Says](https://github.com/simon-says-labs).
Third-party parts: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This is an independent project. It is not affiliated with or endorsed by Elgato or Home
Assistant. Stream Deck and Home Assistant are trademarks of their respective owners.
