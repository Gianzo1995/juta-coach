# Juta Coach

App di **Juta Health & Fitness** che guarda come esegui un esercizio e ti corregge subito:
conta le ripetizioni, segnala gli errori a voce e mostra un manichino con la posizione corretta in verde.

**Prova l'app sul telefono:** https://gianzo1995.github.io/juta-coach/

> Versione beta: le soglie degli errori sono ancora da calibrare con gli istruttori.
> Le immagini restano sul telefono, niente viene inviato.

## Come si usa

1. Apri il link dal telefono e consenti la fotocamera.
2. Cerca l'esercizio (es. "squat", "piegamenti") e leggi **Come si fa** per la posizione della camera.
3. Appoggia il telefono a 2–3 metri e tocca **Avvia il live**: hai 5 secondi per metterti in posizione.
4. A fine serie tocca **Rivedi la serie** per rivedere gli errori sul manichino.

## Esercizi

Squat, panca piana, lat machine e i primi piegamenti (PET-001 … PET-005). Il catalogo è in
`esercizi/catalogo/`: per aggiungere esercizi basta un nuovo file JSON.

## Per chi sviluppa

Vedi [`CLAUDE.md`](CLAUDE.md) per struttura, regole e test. In breve:

```
python prova_motore.py     # autotest del motore
python prove/parita.py     # motore Python e telefono danno gli stessi risultati (serve Node)
python web/costruisci.py   # genera sito/ e sito_claude/
```

Ogni push su `main` esegue i test e, se passano, ripubblica il sito.
La versione per PC con webcam è descritta in [`LEGGIMI.md`](LEGGIMI.md).
