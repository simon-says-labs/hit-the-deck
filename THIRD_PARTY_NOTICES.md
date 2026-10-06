# Third-party notices

Hit the Deck is MIT licensed (see [LICENSE](LICENSE)). It contains or builds on the following
third-party work.

## Home Assistant plugin for the Stream Deck app, by Christoph Giesche

The icon and colour rules in `hit_the_deck/app/display_rules.py`, and the look of the entity,
gauge and info bar images in `hit_the_deck/app/render.py`, follow the default display
configuration of https://github.com/cgiesche/streamdeck-homeassistant
(`public/config/default-display-config.yml`), so keys look the same as with that plugin on a
computer. Icon names, colours and temperature steps were taken from that file and expressed in
Python.

```
MIT License

Copyright (c) 2023 Christoph Giesche

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Material Design Icons (Pictogrammers)

`hit_the_deck/app/assets/mdi/mdi.ttf` is the unchanged font from the npm package
[`@mdi/font`](https://www.npmjs.com/package/@mdi/font) version 7.4.47 (see `VERSION` there;
`tools/update_icons.py` downloads it and checks the package's integrity hash).
`mdi-codepoints.json` is generated from the package's CSS.

The fonts are distributed under the Apache License 2.0 (`assets/mdi/APACHE-2.0.txt`); the
Pictogrammers Free License that comes with the package is in `assets/mdi/LICENSE`.

## Installed at build time, not part of this repository

| Package | License | Source |
|---|---|---|
| python-elgato-streamdeck (`streamdeck` 0.10.0) | see its repository | https://github.com/abcminiuser/python-elgato-streamdeck |
| Pillow, PyYAML, aiohttp, websockets, hidapi, libusb, DejaVu fonts | see the Alpine packages | Alpine Linux, via the Home Assistant base image |
| keyring (standalone mode only) | MIT | https://github.com/jaraco/keyring |
