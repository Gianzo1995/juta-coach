# Juta – Analisi del movimento (prototipo v0.1)

## Installazione (una volta sola, ~10 minuti)

1. **Installa Python 3.12** da https://www.python.org/downloads/
   Nella prima schermata dell'installazione **spunta "Add python.exe to PATH"**, poi "Install Now".
2. **Estrai lo zip** in una cartella, ad esempio `Documenti\juta_movimento`.
3. **Doppio clic su `installa.bat`**. Scarica i componenti (qualche minuto) e alla fine esegue un autotest:
   deve comparire **"TUTTO OK: il motore funziona."**
   Se Windows mostra "PC protetto da Windows", clicca *Ulteriori informazioni → Esegui comunque*.

## Uso

**Doppio clic su `avvia.bat`.** Al primo avvio scarica il modello di riconoscimento (~10 MB).

| Tasto | Azione |
|---|---|
| 1 / 2 / 3 | Squat / Panca piana / Lat machine |
| R | Azzera il conteggio |
| D | Mostra gli angoli misurati (utile per calibrare) |
| Q o Esc | Esci |

**Posizione della camera:**
- Squat e panca: la camera ti vede **di lato**, corpo intero nell'inquadratura.
- Lat machine: la camera è **di fronte**.

Distanza di circa 2–3 m, una sola persona inquadrata, luce buona e non controluce.

**Per provare a casa senza bilanciere:** squat a corpo libero di lato alla webcam. La panca puoi simularla sdraiato sul pavimento con un bastone.

## Analizzare un video registrato

Funziona per i test con gli istruttori. Apri il Prompt dei comandi nella cartella (scrivi `cmd` nella barra dell'indirizzo di Esplora file) e digita:

```
avvia.bat --video nomefile.mp4 --esercizio squat
```

## Dove sono le cose

| Cartella / file | Cosa contiene |
|---|---|
| `esercizi/catalogo/*.json` | Il catalogo esercizi: regole (angoli, soglie, messaggi), testi degli errori e schede tecniche. Una variante può ereditare da un esercizio base con `eredita_da`. |
| `config.yaml` | Sede, postazione, quale camera usare |
| `dati/eventi_DATA.jsonl` | Ripetizioni ed errori registrati. Nessuna immagine viene salvata. |
| `motore/` | Il motore di analisi (non serve toccarlo) |

## Problemi comuni

- **Schermo nero o "non riesco ad aprire la camera":** in `config.yaml` metti `camera: 1`. Chiudi anche Teams, Zoom e altri programmi che usano la webcam.
- **Lento (sotto 15 fps, premi D per vederlo):** in `config.yaml` metti `modello: lite`.
- **Non conta le ripetizioni:** premi D e guarda l'angolo mentre ti muovi, poi confrontalo con le soglie nel catalogo (`esercizi/catalogo`).

## App per telefono (cartella `web`)

- `web/app.html` (interfaccia) + `web/motore.js` (motore, identico a `motore/regole.py`).
- `python web/costruisci.py` genera la versione online e quella dentro Claude leggendo il catalogo in `esercizi/catalogo`.
- Per aggiungere esercizi: nuovo file JSON in `esercizi/catalogo`, poi rilancia `costruisci.py` e `prova_motore.py`.
