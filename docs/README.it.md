<p align="center"><img src="social-preview.png" width="100%" alt="Hit the Deck. Simon says: hit the deck!"></p>

# Hit the Deck

<p align="center"><b><a href="../README.md#deutsch">🇩🇪 Deutsch</a> · <a href="../README.md#english">🇬🇧 English</a> · <a href="README.fr.md">🇫🇷 Français</a> · 🇮🇹 Italiano · <a href="README.es.md">🇪🇸 Español</a></b></p>

> **Simon says: hit the deck!** Uno Stream Deck collegato al computer di Home Assistant diventa un telecomando per
> luci, interruttori, scene, ventilatori e sensori. Assegni i tasti in un configuratore nella barra laterale, che li
> disegna esattamente come il deck. Pensato per lo Stream Deck Neo, ancora meglio insieme a Track Time.

[![Aggiungi il repository al tuo Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsimon-says-labs%2Fhit-the-deck)

<p align="center"><img src="configurator.png" width="820" alt="Il configuratore: otto tasti di uno Stream Deck Neo con una lampada, un ventilatore, un indicatore, Track Time in corso a 3:10, una macchina del caffè, un misuratore, una scena e un tasto di stop; sotto, la barra informazioni con ora e data; a destra, l'editor dei tasti"></p>

## Ancora meglio con Track Time

[Track Time](https://github.com/simon-says-labs/track-time) è un sistema di rilevazione dell'orario di lavoro per
Home Assistant. Hit the Deck lo trova da solo e ti dà due tasti per la tua giornata lavorativa:

<p align="center"><img src="keys.png" width="560" alt="Tasti come li disegna il deck; il tasto Track Time è verde e mostra 3:10, il tasto di stop è rosso"></p>

| Tasto | Funzione |
|---|---|
| Track Time: avvia / pausa / riprendi | fermo → avvia, in corso → pausa, in pausa → riprendi; mostra il tempo lavorato oggi |
| Track Time: stop | termina la giornata lavorativa, anche da una pausa |

## Funzioni

- **Tasti entità** con icona e colore in base allo stato dell'entità, in quattro visualizzazioni: icona piena,
  icona + valore, Gauge e Meter. Una pressione esegue qualsiasi azione, una sequenza di azioni o una preimpostazione
  del ventilatore.
- **Pagine**, cambiate tramite tasti o con i due punti touch del Neo.
- **Barra informazioni** (info bar) dello Stream Deck Neo: ora, data, stati delle entità e testo, con sfumature e
  modelli pronti all'uso.
- **Configuratore nella barra laterale** con anteprime dal vivo, galleria di icone (Material Design Icons, ricercabile
  in cinque lingue), profili, esportazione e importazione. Le modifiche arrivano subito sul deck.
- **Si attenua di notte** finché un'entità luce a tua scelta è spenta.
- **Si riprende dopo un reset USB** insieme al sistema di controllo e sorveglianza dell'app.
- **Cinque lingue**: inglese, tedesco, francese, italiano, spagnolo.

## Installazione in Home Assistant

1. Clicca sul pulsante qui sopra, oppure aggiungi `https://github.com/simon-says-labs/hit-the-deck` come repository
   nello store delle app, in **Impostazioni → Applicazioni**.
2. Collega lo Stream Deck al computer di Home Assistant.
3. Installa **Hit the Deck**, attiva **Sistema di controllo e sorveglianza** e **Mostra nella barra laterale**, poi
   avvialo.
4. Facoltativo: installa [Track Time](https://github.com/simon-says-labs/track-time) per i tasti del tempo.

Requisiti: Home Assistant OS o Supervised su un computer a 64 bit (`aarch64` o `amd64`), per esempio un
Raspberry Pi 4 o 5. Ogni opzione è descritta in [DOCS.md](../hit_the_deck/DOCS.md) (in inglese).

## Standalone: su un computer

Hit the Deck funziona anche su un computer Mac, Windows o Linux a cui è collegato lo Stream Deck. In questo caso
serve un token di accesso a lunga durata, e un piccolo assistente crea la connessione insieme a te:

```bash
pip install -r standalone/requirements.txt   # più hidapi, vedi la documentazione di python-elgato-streamdeck
python3 standalone/connect.py                # una sola volta
python3 standalone/run.py                    # configuratore su http://127.0.0.1:8099
```

`connect.py` controlla l'indirizzo di Home Assistant, apre nel browser la pagina di sicurezza del tuo profilo, dove
crei il token, legge il token incollato senza mostrarlo, lo verifica con Home Assistant e lo salva nel portachiavi
del sistema. Il token non finisce mai in un file di questo progetto, in un log o sullo schermo.
`connect.py --forget` lo rimuove. La libreria USB nativa si installa seguendo la
[guida di installazione di python-elgato-streamdeck](https://python-elgato-streamdeck.readthedocs.io/en/stable/pages/backend_libusb_hidapi.html).

## Sicurezza

- In Home Assistant non serve creare alcun token: il Supervisor fornisce all'app il suo accesso.
- Il configuratore risponde solo all'ingress di Home Assistant (in modalità standalone: solo 127.0.0.1).
- L'app richiede i permessi per l'hardware USB per aprire lo Stream Deck; [SECURITY.md](../SECURITY.md) spiega perché
  e come segnalare le vulnerabilità.

## Sviluppo

```bash
python3 -m venv .venv && .venv/bin/pip install pillow pyyaml aiohttp websockets keyring
.venv/bin/python -m unittest discover -s tests   # nessuno Stream Deck necessario
.venv/bin/python tools/demo.py                   # il configuratore con entità inventate
```

Vedi [CONTRIBUTING.md](../CONTRIBUTING.md). Modifiche: [hit_the_deck/CHANGELOG.md](../hit_the_deck/CHANGELOG.md).

## Licenza

[MIT](../LICENSE) © 2026 Simon Eckmiller · pubblicato da [Simon Says](https://github.com/simon-says-labs).
Componenti di terze parti: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

Questo è un progetto indipendente. Non è affiliato a Elgato o Home Assistant né approvato da loro. Stream Deck e
Home Assistant sono marchi dei rispettivi proprietari.

<p align="right"><a href="#hit-the-deck">↑</a></p>
