# Hit the Deck

Plug a Stream Deck into your Home Assistant machine and use its keys for lights, switches,
scenes, fans and sensors. Assign the keys in the configurator in the sidebar; changes reach the
deck at once. Made for the Stream Deck Neo (8 keys, info bar and two touch points); other
Stream Deck models with keys work too.

## Works best with Track Time

With [Track Time](https://github.com/simon-says-labs/track-time) installed, two key types track
your working day:

| Key | Does |
|---|---|
| Track Time: start / pause / resume | stopped → start, running → pause, paused → resume. Green with the time worked today while running, blue with pause bars while paused. |
| Track Time: stop | ends the working day, also from a pause. |

Hit the Deck finds Track Time on its own when both run in the same Home Assistant. If Track Time
is not installed or not running, the key shows "offline".

## First start

1. Plug the Stream Deck into a USB port of the Home Assistant machine.
2. Install Hit the Deck, turn on **Watchdog** and **Show in sidebar**, then start it.
3. Open **Hit the Deck** in the sidebar, click a key and assign it.

Turn on **Watchdog**: after a USB reset the deck gets a new device node that a running
container cannot see. Hit the Deck then stops itself, and the watchdog starts a fresh container.
Without a deck it waits 10 minutes and does the same.

## Options

| Option | Default | Meaning |
|---|---|---|
| `language` | `auto` | Weekdays, dates and the default texts of the Track Time keys. `auto` uses Home Assistant's language. The configurator follows your browser. |
| `auto_brightness` | `false` | Dim the deck while `brightness_light_entity` is off, e.g. at night. |
| `brightness_light_entity` | – | An entity that is off when the room is dark, e.g. a light group. |
| `brightness_min` | `10` | Brightness in % while that entity is off. The slider in the configurator is the day value. |
| `track_time_url` | – | Only if Track Time runs elsewhere, e.g. `http://192.0.2.10:7979`. |
| `track_time_api_key` | – | Track Time's API key, needed with `track_time_url` when Track Time has one. |

## Keys

| Type | What it shows and does |
|---|---|
| Entity | Icon and colour from the entity's state; on press an action such as `light.toggle`. Layouts: full icon, icon + value, gauge, meter. Fans can get a preset (speed, oscillation) that snaps to the fan's own steps. |
| Track Time: start / pause / resume, stop | see above |
| Switch page | Next or previous page. Each page has its own keys. |
| Empty | Nothing. |

The **info bar** of the Stream Deck Neo shows sections side by side: clock, date with weekday,
an entity's state or a text, on one colour or a gradient. The two **touch points** next to it
switch pages or run an action.

**Profiles** save a complete layout under a name; export and import move it to another
installation. Removed profiles are moved to `profiles/removed/`, not deleted.

## Files

The key layout is `hit_the_deck.yaml` in the app's configuration folder
(`/addon_configs/<id>_hit_the_deck/`), with profiles in `profiles/`. Both are part of Home
Assistant backups. You can edit the YAML by hand; the deck picks up changes without a restart.

## Permissions

The Stream Deck is a USB HID device. On Home Assistant OS it could only be opened with
`full_access`, `udev` and the `SYS_RAWIO` capability, so the app asks for them. The configurator
only answers Home Assistant's ingress, and only administrators see it in the sidebar.
