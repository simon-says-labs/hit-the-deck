#!/usr/bin/env python3
"""Connects Hit the Deck on a computer to Home Assistant, step by step.

    python3 standalone/connect.py            set up or change the connection
    python3 standalone/connect.py --forget   remove the saved token

1. Asks for the Home Assistant address and checks that Home Assistant answers there.
2. Opens your profile's security page in the browser, where you create a long-lived token.
3. You paste the token here; the input stays hidden.
4. The token is checked against Home Assistant and stored in the system keychain
   (Keychain on macOS, Credential Manager on Windows, Secret Service on Linux).
   It is never written to a project file, a log or the screen.
5. Optionally: the address and API key of Track Time.

Not needed inside Home Assistant: there the app gets its access from the Supervisor.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import argparse
import getpass
import json
import locale
import os
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hit_the_deck" / "app"))
import credentials  # noqa: E402

DEFAULT_URL = "http://homeassistant.local:8123"
ATTEMPTS = 3

TEXTS = {
    "en": {
        "intro": "Connect Hit the Deck to Home Assistant. Your token stays on this computer.",
        "ask_url": "Home Assistant address [{0}]: ",
        "unreachable": "No answer from {0}. Check the address and that this computer is in the same network.",
        "not_ha": "{0} answers, but it does not look like Home Assistant (status {1}).",
        "reachable": "Home Assistant found at {0}.",
        "browser": "Your browser now opens {0}\n"
                   "  1. Scroll down to “Long-lived access tokens” and click “Create token”.\n"
                   "  2. Name it “Hit the Deck” and confirm.\n"
                   "  3. Copy the token (it is shown only once) and come back here.",
        "browser_failed": "Could not open a browser. Open this address yourself: {0}",
        "ask_token": "Paste the token (the input stays hidden): ",
        "empty": "Nothing was pasted.",
        "rejected": "Home Assistant did not accept this token. Please copy it again.",
        "accepted": "Token accepted by Home Assistant.",
        "no_keychain": "No system keychain found ({0}).",
        "ask_file": "Store the token in a file only you can read instead ({0})? [y/N] ",
        "not_saved": "Nothing was saved.",
        "saved": "Token stored in the {0}.",
        "verify_failed": "The token could not be read back from the {0}. Nothing else was changed.",
        "ask_tt": "Track Time address, e.g. http://homeassistant.local:7979 (empty = skip): ",
        "tt_unreachable": "Track Time does not answer at {0}. In Track Time, turn on port 7979 under Network.",
        "ask_tt_key": "Track Time API key (hidden, empty if Track Time has none): ",
        "tt_ok": "Track Time reached at {0}.",
        "tt_rejected": "Track Time refused the key (status {0}).",
        "done": "Done. Start Hit the Deck with:  python3 standalone/run.py",
        "forgotten": "Saved token and Track Time key removed from the {0}.",
        "nothing": "Nothing saved.",
        "yes": ("y", "yes"),
    },
    "de": {
        "intro": "Hit the Deck mit Home Assistant verbinden. Dein Token bleibt auf diesem Computer.",
        "ask_url": "Adresse von Home Assistant [{0}]: ",
        "unreachable": "Keine Antwort von {0}. Prüfe die Adresse und ob dieser Computer im selben Netz ist.",
        "not_ha": "{0} antwortet, sieht aber nicht nach Home Assistant aus (Status {1}).",
        "reachable": "Home Assistant unter {0} gefunden.",
        "browser": "Dein Browser öffnet jetzt {0}\n"
                   "  1. Nach unten zu „Langlebige Zugriffstoken“ scrollen und „Token erstellen“ klicken.\n"
                   "  2. Als Namen „Hit the Deck“ eingeben und bestätigen.\n"
                   "  3. Den Token kopieren (er wird nur einmal angezeigt) und hierher zurückkommen.",
        "browser_failed": "Konnte keinen Browser öffnen. Öffne diese Adresse selbst: {0}",
        "ask_token": "Token einfügen (die Eingabe bleibt unsichtbar): ",
        "empty": "Es wurde nichts eingefügt.",
        "rejected": "Home Assistant hat diesen Token nicht angenommen. Bitte noch einmal kopieren.",
        "accepted": "Token von Home Assistant angenommen.",
        "no_keychain": "Kein Schlüsselbund des Systems gefunden ({0}).",
        "ask_file": "Token stattdessen in einer Datei speichern, die nur du lesen kannst ({0})? [j/N] ",
        "not_saved": "Es wurde nichts gespeichert.",
        "saved": "Token im {0} gespeichert.",
        "verify_failed": "Der Token ließ sich aus dem {0} nicht zurücklesen. Sonst wurde nichts geändert.",
        "ask_tt": "Adresse von Track Time, z. B. http://homeassistant.local:7979 (leer = überspringen): ",
        "tt_unreachable": "Track Time antwortet nicht unter {0}. Schalte in Track Time unter Netzwerk den Port 7979 ein.",
        "ask_tt_key": "API-Schlüssel von Track Time (unsichtbar, leer, falls Track Time keinen hat): ",
        "tt_ok": "Track Time unter {0} erreicht.",
        "tt_rejected": "Track Time hat den Schlüssel abgelehnt (Status {0}).",
        "done": "Fertig. Hit the Deck starten mit:  python3 standalone/run.py",
        "forgotten": "Gespeicherter Token und Track-Time-Schlüssel aus dem {0} entfernt.",
        "nothing": "Nichts gespeichert.",
        "yes": ("j", "ja", "y", "yes"),
    },
    "fr": {
        "intro": "Connecter Hit the Deck à Home Assistant. Votre jeton reste sur cet ordinateur.",
        "ask_url": "Adresse de Home Assistant [{0}] : ",
        "unreachable": "Pas de réponse de {0}. Vérifiez l'adresse et que cet ordinateur est sur le même réseau.",
        "not_ha": "{0} répond, mais ne ressemble pas à Home Assistant (statut {1}).",
        "reachable": "Home Assistant trouvé à {0}.",
        "browser": "Votre navigateur ouvre maintenant {0}\n"
                   "  1. Descendez jusqu'à « Jetons d'accès longue durée » et cliquez sur « Créer un jeton ».\n"
                   "  2. Nommez-le « Hit the Deck » et confirmez.\n"
                   "  3. Copiez le jeton (il n'est affiché qu'une fois) et revenez ici.",
        "browser_failed": "Impossible d'ouvrir un navigateur. Ouvrez vous-même cette adresse : {0}",
        "ask_token": "Collez le jeton (la saisie reste masquée) : ",
        "empty": "Rien n'a été collé.",
        "rejected": "Home Assistant n'a pas accepté ce jeton. Copiez-le à nouveau.",
        "accepted": "Jeton accepté par Home Assistant.",
        "no_keychain": "Aucun trousseau système trouvé ({0}).",
        "ask_file": "Enregistrer le jeton dans un fichier lisible par vous seul à la place ({0}) ? [o/N] ",
        "not_saved": "Rien n'a été enregistré.",
        "saved": "Jeton enregistré dans le {0}.",
        "verify_failed": "Impossible de relire le jeton depuis le {0}. Rien d'autre n'a été modifié.",
        "ask_tt": "Adresse de Track Time, p. ex. http://homeassistant.local:7979 (vide = ignorer) : ",
        "tt_unreachable": "Track Time ne répond pas à {0}. Dans Track Time, activez le port 7979 sous Réseau.",
        "ask_tt_key": "Clé API de Track Time (masquée, vide si Track Time n'en a pas) : ",
        "tt_ok": "Track Time joint à {0}.",
        "tt_rejected": "Track Time a refusé la clé (statut {0}).",
        "done": "Terminé. Démarrez Hit the Deck avec :  python3 standalone/run.py",
        "forgotten": "Jeton et clé Track Time enregistrés retirés du {0}.",
        "nothing": "Rien d'enregistré.",
        "yes": ("o", "oui", "y", "yes"),
    },
    "it": {
        "intro": "Collega Hit the Deck a Home Assistant. Il tuo token resta su questo computer.",
        "ask_url": "Indirizzo di Home Assistant [{0}]: ",
        "unreachable": "Nessuna risposta da {0}. Controlla l'indirizzo e che questo computer sia nella stessa rete.",
        "not_ha": "{0} risponde, ma non sembra Home Assistant (stato {1}).",
        "reachable": "Home Assistant trovato su {0}.",
        "browser": "Il browser apre ora {0}\n"
                   "  1. Scorri fino a «Token di accesso a lungo termine» e fai clic su «Crea token».\n"
                   "  2. Chiamalo «Hit the Deck» e conferma.\n"
                   "  3. Copia il token (viene mostrato una sola volta) e torna qui.",
        "browser_failed": "Impossibile aprire un browser. Apri tu questo indirizzo: {0}",
        "ask_token": "Incolla il token (l'inserimento resta nascosto): ",
        "empty": "Non è stato incollato nulla.",
        "rejected": "Home Assistant non ha accettato questo token. Copialo di nuovo.",
        "accepted": "Token accettato da Home Assistant.",
        "no_keychain": "Nessun portachiavi di sistema trovato ({0}).",
        "ask_file": "Salvare invece il token in un file leggibile solo da te ({0})? [s/N] ",
        "not_saved": "Non è stato salvato nulla.",
        "saved": "Token salvato nel {0}.",
        "verify_failed": "Impossibile rileggere il token dal {0}. Nient'altro è stato modificato.",
        "ask_tt": "Indirizzo di Track Time, ad es. http://homeassistant.local:7979 (vuoto = salta): ",
        "tt_unreachable": "Track Time non risponde su {0}. In Track Time attiva la porta 7979 in Rete.",
        "ask_tt_key": "Chiave API di Track Time (nascosta, vuota se Track Time non ne ha): ",
        "tt_ok": "Track Time raggiunto su {0}.",
        "tt_rejected": "Track Time ha rifiutato la chiave (stato {0}).",
        "done": "Fatto. Avvia Hit the Deck con:  python3 standalone/run.py",
        "forgotten": "Token e chiave di Track Time salvati rimossi dal {0}.",
        "nothing": "Niente di salvato.",
        "yes": ("s", "sì", "si", "y", "yes"),
    },
    "es": {
        "intro": "Conectar Hit the Deck con Home Assistant. Tu token se queda en este ordenador.",
        "ask_url": "Dirección de Home Assistant [{0}]: ",
        "unreachable": "No hay respuesta de {0}. Comprueba la dirección y que este ordenador esté en la misma red.",
        "not_ha": "{0} responde, pero no parece Home Assistant (estado {1}).",
        "reachable": "Home Assistant encontrado en {0}.",
        "browser": "Tu navegador abre ahora {0}\n"
                   "  1. Baja hasta «Tokens de acceso de larga duración» y haz clic en «Crear token».\n"
                   "  2. Llámalo «Hit the Deck» y confirma.\n"
                   "  3. Copia el token (solo se muestra una vez) y vuelve aquí.",
        "browser_failed": "No se pudo abrir un navegador. Abre tú esta dirección: {0}",
        "ask_token": "Pega el token (la entrada queda oculta): ",
        "empty": "No se pegó nada.",
        "rejected": "Home Assistant no aceptó este token. Cópialo de nuevo.",
        "accepted": "Token aceptado por Home Assistant.",
        "no_keychain": "No se encontró un llavero del sistema ({0}).",
        "ask_file": "¿Guardar el token en un archivo que solo tú puedes leer ({0})? [s/N] ",
        "not_saved": "No se guardó nada.",
        "saved": "Token guardado en el {0}.",
        "verify_failed": "No se pudo volver a leer el token del {0}. No se cambió nada más.",
        "ask_tt": "Dirección de Track Time, p. ej. http://homeassistant.local:7979 (vacío = omitir): ",
        "tt_unreachable": "Track Time no responde en {0}. En Track Time, activa el puerto 7979 en Red.",
        "ask_tt_key": "Clave API de Track Time (oculta, vacía si Track Time no tiene): ",
        "tt_ok": "Track Time alcanzado en {0}.",
        "tt_rejected": "Track Time rechazó la clave (estado {0}).",
        "done": "Listo. Inicia Hit the Deck con:  python3 standalone/run.py",
        "forgotten": "Token y clave de Track Time guardados eliminados del {0}.",
        "nothing": "Nada guardado.",
        "yes": ("s", "sí", "si", "y", "yes"),
    },
}

STORE_NAMES = {
    "en": {"system keychain": "system keychain", "private file": "private file"},
    "de": {"system keychain": "Schlüsselbund des Systems", "private file": "privaten Datei"},
    "fr": {"system keychain": "trousseau du système", "private file": "fichier privé"},
    "it": {"system keychain": "portachiavi di sistema", "private file": "file privato"},
    "es": {"system keychain": "llavero del sistema", "private file": "archivo privado"},
}


def system_language(env=None) -> str:
    env = os.environ if env is None else env
    for value in (env.get("LC_ALL"), env.get("LC_MESSAGES"), env.get("LANG"), (locale.getlocale()[0] or "")):
        code = (value or "").lower()[:2]
        if code in TEXTS:
            return code
    return "en"


def normalise_url(text: str) -> str:
    url = text.strip().rstrip("/")
    if url and "://" not in url:
        url = "http://" + url
    return url


def http_status(url: str, token: str = "", key: str = "", timeout: float = 8):
    """HTTP status of a GET, or None when nothing answers. Never puts secrets into errors."""
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if key:
        headers["X-Api-Key"] = key
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code
    except (urllib.error.URLError, OSError, ValueError):
        return None


class Console:
    """Input and output; replaced in the tests."""

    def say(self, text: str) -> None:
        print(text, flush=True)

    def ask(self, prompt: str) -> str:
        return input(prompt)

    def ask_hidden(self, prompt: str) -> str:
        return getpass.getpass(prompt)

    def open_browser(self, url: str) -> bool:
        return webbrowser.open(url)


class Assistant:
    def __init__(self, console=None, config_dir=None, status=http_status, keyring_module=None, language=None):
        self.console = console or Console()
        self.config_dir = Path(config_dir or credentials.user_config_dir())
        self.status = status
        self.keyring_module = keyring_module
        self.lang = language or system_language()
        self.t = TEXTS[self.lang]

    def say(self, key, *args):
        self.console.say(self.t[key].format(*args))

    # --- files that hold no secrets ------------------------------------------------------
    @property
    def connection_file(self) -> Path:
        return self.config_dir / "connection.json"

    @property
    def options_file(self) -> Path:
        return self.config_dir / "options.json"

    def read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return {}

    def write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    # --- steps ---------------------------------------------------------------------------
    def ask_url(self):
        default = self.read_json(self.connection_file).get("url") or DEFAULT_URL
        for _ in range(ATTEMPTS):
            url = normalise_url(self.console.ask(self.t["ask_url"].format(default))) or default
            status = self.status(url + "/api/")
            if status == 401:          # Home Assistant answers 401 without a token
                self.say("reachable", url)
                return url
            if status is None:
                self.say("unreachable", url)
            else:
                self.say("not_ha", url, status)
        return None

    def ask_token(self, url: str):
        page = url + "/profile/security"
        self.say("browser", page)
        if not self.console.open_browser(page):
            self.say("browser_failed", page)
        for _ in range(ATTEMPTS):
            token = "".join(self.console.ask_hidden(self.t["ask_token"]).split())
            if not token:
                self.say("empty")
                continue
            if self.status(url + "/api/", token=token) == 200:
                self.say("accepted")
                return token
            self.say("rejected")
        return None

    def open_store(self):
        try:
            return credentials.KeychainStore(self.keyring_module)
        except credentials.NoKeychain as reason:
            self.say("no_keychain", reason)
            path = credentials.secrets_file(self.config_dir)
            answer = self.console.ask(self.t["ask_file"].format(path)).strip().lower()
            return credentials.FileStore(path) if answer in self.t["yes"] else None

    def store_name(self, store) -> str:
        return STORE_NAMES[self.lang][store.name]

    def save(self, store, key: str, value: str) -> bool:
        store.set(key, value)
        if store.get(key) != value:
            self.say("verify_failed", self.store_name(store))
            return False
        return True

    def ask_track_time(self, store) -> None:
        address = normalise_url(self.console.ask(self.t["ask_tt"]))
        if not address:
            return
        if self.status(address + "/healthz") is None:
            self.say("tt_unreachable", address)
            return
        key = self.console.ask_hidden(self.t["ask_tt_key"]).strip()
        status = self.status(address + "/api/state", key=key)
        if status != 200:
            self.say("tt_rejected", status)
            return
        options = self.read_json(self.options_file)
        options["track_time_url"] = address
        self.write_json(self.options_file, options)
        if key:
            self.save(store, credentials.TRACK_TIME_API_KEY, key)
        else:
            store.remove(credentials.TRACK_TIME_API_KEY)
        self.say("tt_ok", address)

    def run(self) -> int:
        self.say("intro")
        url = self.ask_url()
        if not url:
            return 1
        token = self.ask_token(url)
        if not token:
            self.say("not_saved")
            return 1
        store = self.open_store()
        if store is None:
            self.say("not_saved")
            return 1
        if not self.save(store, credentials.HOME_ASSISTANT_TOKEN, token):
            return 1
        self.say("saved", self.store_name(store))
        self.write_json(self.connection_file, {"url": url})
        self.ask_track_time(store)
        self.say("done")
        return 0

    def forget(self) -> int:
        store = credentials.open_store(self.config_dir, self.keyring_module)
        if store is None:
            self.say("nothing")
            return 0
        store.remove(credentials.HOME_ASSISTANT_TOKEN)
        store.remove(credentials.TRACK_TIME_API_KEY)
        self.say("forgotten", self.store_name(store))
        return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Connect Hit the Deck on this computer to Home Assistant.")
    parser.add_argument("--forget", action="store_true", help="remove the saved token and Track Time key")
    args = parser.parse_args(argv)
    assistant = Assistant()
    try:
        return assistant.forget() if args.forget else assistant.run()
    except (KeyboardInterrupt, EOFError):
        assistant.console.say("")
        assistant.say("not_saved")
        return 130


if __name__ == "__main__":
    sys.exit(main())
