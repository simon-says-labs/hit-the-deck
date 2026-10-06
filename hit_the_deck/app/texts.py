"""Texts drawn on the deck itself, and the words the icon search understands.

The configurator in the browser has its own texts in static/i18n.js.
Every language must have every key; tests/test_i18n.py checks that.

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

LANGUAGES = ("en", "de", "fr", "it", "es")

DECK_TEXTS = {
    "en": {"start": "Start", "pause": "Pause", "stop": "Stop", "offline": "offline", "page": "Page"},
    "de": {"start": "Start", "pause": "Pause", "stop": "Stopp", "offline": "offline", "page": "Seite"},
    "fr": {"start": "Démarrer", "pause": "Pause", "stop": "Arrêter", "offline": "hors ligne", "page": "Page"},
    "it": {"start": "Avvia", "pause": "Pausa", "stop": "Ferma", "offline": "offline", "page": "Pagina"},
    "es": {"start": "Iniciar", "pause": "Pausa", "stop": "Detener", "offline": "sin conexión", "page": "Página"},
}

WEEKDAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
    "it": ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"],
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
}

WEEKDAYS_SHORT = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    "fr": ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"],
    "it": ["lun", "mar", "mer", "gio", "ven", "sab", "dom"],
    "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
}

DATE_FORMAT = {"en": "%Y-%m-%d", "de": "%d.%m.%Y", "fr": "%d/%m/%Y", "it": "%d/%m/%Y", "es": "%d/%m/%Y"}

# Material Design Icon names are English; these words lead the icon search to them.
ICON_WORDS = {
    "de": {
        "schalter": ["switch", "toggle"], "lichtschalter": ["light-switch", "switch"],
        "steckdose": ["socket", "outlet", "power-plug"], "licht": ["light", "lamp", "bulb"],
        "lampe": ["lamp", "light", "bulb"], "ventilator": ["fan"], "lüfter": ["fan"],
        "heizung": ["radiator", "thermostat", "heat"], "temperatur": ["thermometer"],
        "rollladen": ["blinds", "roller-shade", "window-shutter"], "vorhang": ["curtains"],
        "fernseher": ["television", "tv"], "musik": ["music", "speaker"], "lautsprecher": ["speaker"],
        "kamera": ["camera", "cctv"], "tür": ["door"], "fenster": ["window"], "schloss": ["lock"],
        "haus": ["home", "house"], "szene": ["palette", "movie-open"], "batterie": ["battery"],
        "wetter": ["weather"], "sonne": ["weather-sunny", "solar"], "wasser": ["water"],
        "auto": ["car"], "staubsauger": ["robot-vacuum", "vacuum"], "uhr": ["clock"],
        "bewegung": ["motion", "run"], "strom": ["flash", "power", "current"], "arbeit": ["briefcase", "laptop"],
    },
    "fr": {
        "interrupteur": ["switch", "toggle"], "prise": ["socket", "power-plug"], "lumière": ["light", "lamp", "bulb"],
        "lampe": ["lamp", "light"], "ventilateur": ["fan"], "chauffage": ["radiator", "thermostat"],
        "température": ["thermometer"], "volet": ["blinds", "window-shutter"], "rideau": ["curtains"],
        "télévision": ["television", "tv"], "musique": ["music", "speaker"], "caméra": ["camera", "cctv"],
        "porte": ["door"], "fenêtre": ["window"], "serrure": ["lock"], "maison": ["home", "house"],
        "scène": ["palette", "movie-open"], "batterie": ["battery"], "météo": ["weather"],
        "eau": ["water"], "voiture": ["car"], "aspirateur": ["robot-vacuum"], "horloge": ["clock"],
        "travail": ["briefcase", "laptop"],
    },
    "it": {
        "interruttore": ["switch", "toggle"], "presa": ["socket", "power-plug"], "luce": ["light", "lamp", "bulb"],
        "lampada": ["lamp", "light"], "ventilatore": ["fan"], "riscaldamento": ["radiator", "thermostat"],
        "temperatura": ["thermometer"], "tapparella": ["blinds", "window-shutter"], "tenda": ["curtains"],
        "televisore": ["television", "tv"], "musica": ["music", "speaker"], "telecamera": ["camera", "cctv"],
        "porta": ["door"], "finestra": ["window"], "serratura": ["lock"], "casa": ["home", "house"],
        "scena": ["palette", "movie-open"], "batteria": ["battery"], "meteo": ["weather"],
        "acqua": ["water"], "auto": ["car"], "aspirapolvere": ["robot-vacuum"], "orologio": ["clock"],
        "lavoro": ["briefcase", "laptop"],
    },
    "es": {
        "interruptor": ["switch", "toggle"], "enchufe": ["socket", "power-plug"], "luz": ["light", "lamp", "bulb"],
        "lámpara": ["lamp", "light"], "ventilador": ["fan"], "calefacción": ["radiator", "thermostat"],
        "temperatura": ["thermometer"], "persiana": ["blinds", "window-shutter"], "cortina": ["curtains"],
        "televisor": ["television", "tv"], "música": ["music", "speaker"], "cámara": ["camera", "cctv"],
        "puerta": ["door"], "ventana": ["window"], "cerradura": ["lock"], "casa": ["home", "house"],
        "escena": ["palette", "movie-open"], "batería": ["battery"], "tiempo": ["weather"],
        "agua": ["water"], "coche": ["car"], "aspiradora": ["robot-vacuum"], "reloj": ["clock"],
        "trabajo": ["briefcase", "laptop"],
    },
}


def pick_language(wanted: str, home_assistant_language: str = "") -> str:
    """The option wins unless it is "auto"; then Home Assistant's language; else English."""
    for candidate in (wanted, home_assistant_language):
        code = (candidate or "").lower().replace("_", "-").split("-")[0]
        if code in LANGUAGES:
            return code
    return "en"


def deck_text(language: str, key: str) -> str:
    return DECK_TEXTS.get(language, DECK_TEXTS["en"])[key]


def icon_search_terms(query: str) -> list:
    """The query itself plus the icon names its word stands for in any language."""
    terms = [query]
    for words in ICON_WORDS.values():
        for term in words.get(query, []):
            if term not in terms:
                terms.append(term)
    return terms
