# Juta Coach — istruzioni per Claude Code

App di analisi del movimento per **Juta Health & Fitness** (3 sedi in Trentino: Trento Centro, Ravina, Rovereto).
Una camera riprende chi si allena, il riconoscimento della posa (MediaPipe) trova i punti del corpo, un motore
di regole conta le ripetizioni, rileva gli errori di esecuzione e dà un feedback immediato (voce, colore, manichino).

## Chi è l'utente

Gianluca, titolare di Juta. **Non è uno sviluppatore.**
- Rispondi in italiano, con parole semplici; spiega le scelte tecniche in una o due frasi.
- Sii diretto e onesto sui limiti: se qualcosa non è affidabile (camera, angolazione, soglie), dillo chiaramente.
- Preferisce procedere a piccoli passi e provare subito.
- Le soglie degli errori vanno calibrate con i suoi istruttori: non presentarle mai come valori validati.

## Struttura

| Percorso | Cosa contiene |
|---|---|
| `esercizi/catalogo/*.json` | **Catalogo esercizi**: regole (`config_app`) + scheda tecnica (`scheda`). Fonte unica per PC e telefono. La vecchia `panca` è stata sostituita da PET-012. |
| `motore/regole.py` | Motore delle regole (Python, versione PC). |
| `web/motore.js` | Lo stesso motore in JavaScript (telefono). **Deve restare identico a `regole.py`.** |
| `web/app.html` | Interfaccia telefono: live, manichino digitale, revisione, ricerca esercizi, "Come si fa". |
| `web/costruisci.py` | Genera `sito/` (versione online) e `sito_claude/` (artifact claude.ai). |
| `web/vendor/` | MediaPipe tasks-vision 0.10.21 (wasm, bundle) e modello `pose_landmarker_lite.task`. Non modificare. |
| `prova_motore.py` | Autotest del motore con movimenti simulati (squat, panca, lat, piegamenti). |
| `prove/parita.py` | Verifica che Python e JavaScript diano gli stessi risultati (richiede Node). |
| `avvia.py`, `motore/posa.py`, `*.bat`, `config.yaml` | Versione PC con webcam (Windows, Python 3.12). |

## Regole di lavoro

1. **Ogni modifica al motore va fatta in entrambi** (`motore/regole.py` e `web/motore.js`), poi:
   ```
   python prova_motore.py
   python prove/parita.py
   python web/costruisci.py
   ```
   Tutti e tre devono passare prima di un commit. La GitHub Action li riesegue ad ogni push.
2. **Push su `main` = pubblicazione automatica** su GitHub Pages (https://gianzo1995.github.io/juta-coach/).
   Il sito è pubblico: niente dati di clienti, chiavi o informazioni riservate nel repository.
3. **Privacy**: nessun video o immagine lascia il telefono. Non aggiungere invii di immagini a server o API.
   L'unica chiamata esterna ammessa è "Spiegamelo meglio" nella versione artifact, che invia solo numeri.
4. Le cartelle `sito/` e `sito_claude/` sono generate: non modificarle a mano e non salvarle nel repository.
5. Per provare l'app senza camera esiste un aggancio di test: se `window.__JUTA_PROVA = { posa(tv, w, h) }`
   è definito prima del caricamento, sostituisce il riconoscimento della posa (usato nei test con Playwright).

## Formato del catalogo

Ogni voce: `{ "id", "nome"?, "gruppo"?, "scheda", "config_app" }`.
- `nome` va sempre indicato (se manca si ricava dai riferimenti in `regressione_progressione` che iniziano con la
  maiuscola, altrimenti si usa l'id). `gruppo` è facoltativo: si ricava dal prefisso dell'id (PET → Petto).
- `config_app.eredita_da`: la variante parte dalla config del base e sovrascrive solo i campi indicati.
  `null` toglie un campo/misura/testo; gli oggetti si uniscono campo per campo; **le liste (es. `errori`) sostituiscono**.
  Un oggetto vuoto `{}` non cancella niente.
- Tipi di misura: `angolo` (3 punti), `inclinazione` (2 punti, rispetto alla verticale),
  `posizione` (spostamento verticale rispetto all'inizio, in unità di un segmento `scala`),
  `durata` (solo dichiarativa: la durata la calcola il motore a fine ripetizione).
- **Misure di tempo automatiche** (secondi, usabili negli errori con `momento: "fine"`):
  `durata` (da `inizio_movimento` al ritorno oltre `posizione_iniziale`), `discesa` (dall'uscita dalla posizione
  iniziale all'arrivo in basso), `pausa` (tempo entro `ripetizione.tolleranza_pausa`, default 5, dal punto più basso),
  `salita` (dal basso al ritorno in posizione iniziale). Per velocità e fermi usare `discesa`/`pausa`, non `durata`.
- `impostazioni` (facoltativo): scelte del cliente prima della serie, es.
  `[{"id": "lato", "domanda": "Quale braccio lavora?", "opzioni": [{"etichetta": "Destro", "imposta": {"lato": "dx"}}, ...]}]`.
  `imposta` accetta percorsi: `"lato"`, `"ripetizione.<campo>"`, `"errori.<id>"` (aggiunge/sostituisce un errore),
  `"errori.<id>.<campo>"`. Applicate da `applica_impostazioni` / `applicaImpostazioni` (identiche).
- `avviso_sicurezza` (facoltativo): testo mostrato in rosso nella scelta dell'esercizio e in cima a "Come si fa".
  Con `lato: "entrambi"` il motore crea anche `<misura>_asimmetria`.
- `ancora` (facoltativo, misure ad angolo): punto che resta fermo nel "fantasma" del manichino.
  Se manca, resta fermo l'estremo più vicino al pavimento.
- `analizzabilita: "non_analizzabile"` → l'esercizio compare solo come scheda, senza analisi.
- `testi_errori[id]`: `cosa_succede`, `perche_conta`, `come_correggere`, `frase_da_ricordare`
  (detta a voce in diretta), `frase_alternativa` (facoltativa, se l'errore si ripete 3 volte).
  `{valore}` e `{soglia}` nei testi vengono sostituiti con i numeri misurati.

**Attenzione alla durata**: la "durata" misurata va da quando la misura di ripetizione supera `inizio_movimento`
a quando torna oltre `posizione_iniziale`, quindi è più corta della ripetizione intera.

## Comportamento del motore (da non rompere)

- Correzione anticipata: gli errori di ampiezza (stessa misura della ripetizione, statistica verso il fondo)
  vengono segnalati al punto di inversione (isteresi 5), non a fine ripetizione. A fine ripetizione si
  ricontrollano con i valori finali.
- Eventi: `ripetizione` (con `inizio_t`, `fondo_t`, `fine_t`, minimi/massimi), `errore` (con `t`, `t_origine`,
  `valore`, `soglia`, `anticipato`), `serie` (dopo 6 s senza persona o senza movimento, o con `termina()`).

## Decisioni già prese

- Uso anonimo per ora (nessun riconoscimento del cliente). Notifiche all'istruttore rimandate.
- Gestionale della palestra: Angel1 (integrazione futura, API da verificare).
- Prima del pilota in sede servono informativa e valutazione d'impatto GDPR e l'accordo/autorizzazione
  per le riprese dello staff (art. 4 Statuto dei Lavoratori).

## Prossimi passi consigliati (richieste dal catalogo, non ancora fatte)

- **A. Angolo con segno**: distinguere bacino che cede da sedere alto (piegamenti, plank, stacchi).
- ~~B. Fasi della ripetizione~~ (fatto: misure `discesa`, `pausa`, `salita`).
- **C. Controllo in alto** tra una ripetizione e l'altra (braccia/gambe distese).
- **D. Misura `distanza`** tra due punti rispetto a un segmento (larghezza presa, ginocchia-mani).
- ~~E. Scelta del lato che lavora~~ (fatto con `impostazioni`, es. PET-006; anche numero di tavolette PET-020).
- ~~Avviso di sicurezza per esercizi solo-scheda~~ (fatto: `avviso_sicurezza`, es. PET-018).
- Dopo: inclinazione delle spalle / rotazione del tronco (vista frontale), ripetizioni alternate sx/dx (PET-008),
  allineamento misurato sulla gamba che resta a terra (PET-008), conteggio sull'altezza della spalla,
  velocità del movimento e confronto tra ripetizioni della serie (PET-011 esplosivi).
- Rimandati: soglie per cliente (serve identificazione, insieme ad Angel1), due camere / vista dall'alto.
