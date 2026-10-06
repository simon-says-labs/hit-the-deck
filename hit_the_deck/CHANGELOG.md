# Changelog

All notable changes to the Hit the Deck app. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning: [Semantic Versioning](https://semver.org/).

## 1.0.0 - 2026-10-06

First public release.

- Stream Deck keys for Home Assistant entities: full icon, icon + value, gauge and meter layouts,
  actions on press, sequences, fan presets that snap to the fan's own steps.
- Track Time keys (start / pause / resume and stop) that find the Track Time app on their own and
  show the time worked today.
- Info bar of the Stream Deck Neo with clock, date, entity and text sections, gradients and
  templates; the two touch points switch pages or run actions.
- Configurator in the sidebar (ingress) that draws the keys exactly as the deck does; pages,
  profiles, export and import; icon gallery with search in five languages.
- Automatic dimming while a chosen entity is off.
- Recovery after USB resets: the app stops its container so the watchdog starts a fresh one.
- Standalone mode for a computer: `standalone/connect.py` creates the connection with a token that
  is checked and stored in the system keychain.
- User interface in English, German, French, Italian and Spanish.
