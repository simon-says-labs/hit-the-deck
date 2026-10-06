# Security policy

Only the latest release receives fixes. Please report vulnerabilities through
[GitHub's private vulnerability reporting](https://github.com/simon-says-labs/hit-the-deck/security/advisories/new),
not in public issues.

## How Hit the Deck handles access

**Inside Home Assistant**
- The app reaches Home Assistant through the Supervisor with the token the Supervisor gives it.
  You never create or paste a token.
- It uses the Supervisor API only to read the info of the Track Time app (default role).
- The configurator answers Home Assistant's ingress proxy only, and only administrators see it.
- To open the Stream Deck (a USB HID device) the app requests `full_access`, `udev` and the
  `SYS_RAWIO` capability. Without them the device could not be opened on Home Assistant OS.
  Narrowing this down to fewer rights is an open task; contributions with a tested smaller set
  are welcome.

**On a computer (standalone mode)**
- `standalone/connect.py` opens Home Assistant's token page in your browser, reads the pasted token
  without showing it, checks it against Home Assistant and stores it in the system keychain
  (Keychain, Credential Manager, Secret Service). Only if there is no keychain, and only after you
  agree, it uses a file that only your user can read (mode 600).
- The token is never written to the configuration, a log, the screen or the environment of the
  processes. `python3 standalone/connect.py --forget` removes it again.
- The configurator listens on 127.0.0.1 only.
- A long-lived token has the rights of your user. Create it with a user that has only the rights
  the deck needs, and delete it in your Home Assistant profile when you stop using Hit the Deck.
