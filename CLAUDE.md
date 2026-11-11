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
| `esercizi/catalogo/*.json` | **Catalogo esercizi**: regole (`config_app`) + scheda tecnica (`scheda`). Fonte unica per PC e telefono. La vecchia `panca` è stata sostituita da PET-012, la vecchia `lat_machine` da DOR-020. Cataloghi: base, PETTORALI 001-080, DORSALI 001-064, SPALLE DEA/DEL/DEP (gruppo «Spalle»). |
| `motore/regole.py` | Motore delle regole (Python, versione PC). |
| `web/motore.js` | Lo stesso motore in JavaScript (telefono). **Deve restare identico a `regole.py`.** |
| `web/app.html` | Interfaccia telefono: live, manichino digitale, revisione, ricerca esercizi, "Come si fa". |
| `web/costruisci.py` | Genera `sito/` (versione online) e `sito_claude/` (artifact claude.ai). |
| `web/vendor/` | MediaPipe tasks-vision 0.10.21 (wasm, bundle) e modelli `pose_landmarker_full.task` (in uso) e `_lite` (ripiego). Non modificare. |
| `prova_motore.py` | Autotest del motore con movimenti simulati (squat, panca, lat DOR-020, piegamenti, alzate). |
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
   Nei dati simulati evita valori che cadono esattamente su una soglia (es. angoli interi a 5° dal minimo):
   Python e JavaScript possono differire nell'ultima cifra di `acos` e contare un fotogramma diverso.
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
  `misure` e `testi_errori` si uniscono per nome (`null` toglie una singola misura/testo); **tutto il resto
  (`ripetizione`, `errori`, testi, liste…) se presente sostituisce** quello del base (regola del generatore del catalogo).
- **Integrazioni dell'app** (`esercizi/integrazioni.json`): il catalogo di Gianluca resta intatto; le aggiunte dell'app
  (conversione dei controlli di velocità a discesa/pausa/salita, impostazioni, avvisi di sicurezza, testi superati)
  stanno qui come `{"id", "imposta": {percorso: valore}, "motivo"}` e vengono applicate prima dell'ereditarietà
  da `leggi_catalogo()` in `motore/regole.py` (usata anche da `costruisci.py` e dalla prova di parità).
  Se un percorso non trova il campo o l'errore, il caricamento si ferma con un messaggio: va aggiornata l'integrazione.
  Quando arriva un nuovo catalogo: sostituire il file in `esercizi/catalogo/`, rilanciare i test, sistemare le integrazioni.
- Il motore richiede visibili solo i punti delle misure usate dalla ripetizione e dagli errori.
- Tipi di misura: `angolo` (3 punti, 0-180), `angolo_orientato` (3 punti: 180 = in linea, meno di 180 = punto
  centrale SOTTO la retta tra gli estremi, più di 180 = SOPRA; per corpi orizzontali/inclinati, es. bacino nei
  piegamenti), `inclinazione` (2 punti [A, B]: 0 = B sopra A, 90 = orizzontale, 180 = B sotto A),
  `posizione` (spostamento verticale rispetto all'inizio, in unità di un segmento `scala`),
  `durata` (solo dichiarativa: la durata la calcola il motore a fine ripetizione).
- **Misure di tempo automatiche** (secondi, usabili negli errori con `momento: "fine"`):
  `durata` (ripetizione intera: dall'uscita dalla posizione iniziale al ritorno), `discesa` (dall'uscita dalla posizione
  iniziale all'arrivo in basso), `pausa` (tempo entro `ripetizione.tolleranza_pausa`, default 5, dal punto più basso),
  `salita` (dal basso al ritorno in posizione iniziale). Per velocità e fermi usare `discesa`/`pausa`, non `durata`.
- `impostazioni` (facoltativo): scelte del cliente prima della serie, es.
  `[{"id": "lato", "domanda": "Quale braccio lavora?", "opzioni": [{"etichetta": "Destro", "imposta": {"lato": "dx"}}, ...]}]`.
  `imposta` accetta percorsi: `"lato"`, `"ripetizione.<campo>"`, `"errori.<id>"` (aggiunge/sostituisce un errore),
  `"errori.<id>.<campo>"`. Applicate da `applica_impostazioni` / `applicaImpostazioni` (identiche).
- `avviso_sicurezza` (facoltativo): testo mostrato in rosso nella scelta dell'esercizio e in cima a "Come si fa".
  Con `lato: "entrambi"` il motore crea anche `<misura>_asimmetria`.
- `ancora` (facoltativo, misure ad angolo): punto che resta fermo nel "fantasma" del manichino.
  Se manca: negli angoli di spalla (anca-spalla-braccio) resta fermo l'anca, altrimenti l'estremo più vicino al pavimento.
- `analizzabilita: "non_analizzabile"` → l'esercizio compare solo come scheda, senza analisi.
- `testi_errori[id]`: `cosa_succede`, `perche_conta`, `come_correggere`, `frase_da_ricordare`
  (detta a voce in diretta), `frase_alternativa` (facoltativa, se l'errore si ripete 3 volte).
  `{valore}` e `{soglia}` nei testi vengono sostituiti con i numeri misurati.


## App telefono: scelte tecniche

- Modello di posa **full** (più preciso del lite; ripiego automatico su lite se non si carica). Il pannello "Angoli"
  mostra fps, tempo di elaborazione, risoluzione camera e modello in uso.
- Camera richiesta a 1920×1080, registrazione per la revisione a 8 Mbit/s.
- Ogni fotogramma viene copiato su una canvas (`quadro`): lo stesso fotogramma viene analizzato e disegnato,
  così lo scheletro non resta indietro rispetto all'immagine.
- Vista di lato: i segmenti del lato lontano dalla camera (spesso stimati perché coperti) sono disegnati tenui.

## Comportamento del motore (da non rompere)

- Correzione anticipata: gli errori di ampiezza (stessa misura della ripetizione, statistica verso il fondo)
  vengono segnalati al punto di inversione (isteresi 5), non a fine ripetizione. A fine ripetizione si
  ricontrollano con i valori finali.
- Eventi: `ripetizione` (con `inizio_t`, `fondo_t`, `fine_t`, minimi/massimi), `errore` (con `t`, `t_origine`,
  `valore`, `soglia`, `anticipato`), `serie` (dopo 6 s senza persona o senza movimento, o con `termina()`),
  `annullata` (`ripetizione`, `inizio_t`, `motivo`: `non_chiusa` | `troppo_lunga`): la finestra non conta e l'app
  toglie dalla revisione gli errori di quella finestra.
- Regole della nota del catalogo (§4): gli errori "durante" si valutano solo a ripetizione in corso; `posizione`
  è misurata rispetto all'inizio della serie; la **prima** ripetizione di una serie si apre solo dopo 0,5 s fermi
  nella posizione di partenza (le successive no, così le ripetizioni continue contano); una finestra più lunga di
  `durata_massima` (3 × durata prevista da `scheda.tempo`, minimo 6 s) viene scartata; se dopo l'inversione si
  torna indietro di oltre 12° senza arrivare alla partenza → "ripetizione non chiusa".

## Decisioni già prese

- Uso anonimo per ora (nessun riconoscimento del cliente). Notifiche all'istruttore rimandate.
- Gestionale della palestra: Angel1 (integrazione futura, API da verificare).
- Prima del pilota in sede servono informativa e valutazione d'impatto GDPR e l'accordo/autorizzazione
  per le riprese dello staff (art. 4 Statuto dei Lavoratori).

## Prossimi passi consigliati (richieste dal catalogo, non ancora fatte)

- ~~A. Angolo con segno~~ (fatto: `angolo_orientato`; i piegamenti hanno "bacino_cede" e "sedere_alto" via integrazioni).
  Da fare: verso avanti/indietro per corpi verticali (busto in PET-047, PET-054), serve conoscere il verso del viso.
- ~~B. Fasi della ripetizione~~ (fatto: misure `discesa`, `pausa`, `salita`).
- **C. Controllo in alto** tra una ripetizione e l'altra (braccia/gambe distese).
- **D. Misura `distanza`** tra due punti rispetto a un segmento (larghezza presa, ginocchia-mani).
- ~~E. Scelta del lato che lavora~~ (fatto con `impostazioni`, es. PET-006; anche numero di tavolette PET-020).
  Funziona anche in vista frontale: DEL-007 reso analizzabile via integrazioni con le regole di DEL-005.
  Da valutare con Gianluca: DEL-009, DEL-013, DEL-014/015, DEP-007 (servono regole scritte da lui).
- ~~Avviso di sicurezza per esercizi solo-scheda~~ (fatto: `avviso_sicurezza`, es. PET-018).
- Dopo: inclinazione delle spalle / rotazione del tronco (vista frontale), ripetizioni alternate sx/dx (PET-008),
  allineamento misurato sulla gamba che resta a terra (PET-008), conteggio sull'altezza della spalla,
  velocità del movimento e confronto tra ripetizioni della serie (PET-011 esplosivi).
- Rimandati: soglie per cliente (serve identificazione, insieme ad Angel1), due camere / vista dall'alto.

## Stato attuale e come riprendere (aggiornato 11/11/2026)

- **Versione app**: Beta 0.9. Catalogo: 223 esercizi (squat di base + PET 001-080 + DOR 001-064 + SPALLE DEA/DEL/DEP),
  168 integrazioni in `esercizi/integrazioni.json`. Ultimi file ricevuti da Gianluca: `NOTE_PER_IL_MOTORE_nuovo.md`
  (regole §1-§7, tutte applicate) e i tre cataloghi.
- **Dove la usa**: dal telefono in Safari (sito GitHub Pages, ha la modalità live) e dentro l'app Claude
  (artifact privato https://claude.ai/artifact/WVtohRo9gD7CcymYtvYsqS, solo video caricato; i video scelti su iPhone
  vengono compressi da iOS, per questo per la qualità migliore va usata la versione Safari).
- **Pubblicare l'artifact**: dopo `python web/costruisci.py`, ripubblicare `sito_claude/artifact.html` sullo stesso URL
  (capacità `sample` per "Spiegamelo meglio"; il modello è in `sito_claude/modello.js`, già caricato: ripassarlo solo se cambia).
- **Pubblicazione GitHub**: se il deploy di Pages resta in "deployment_queued" e va in timeout, rilanciare
  `gh run rerun <id> --failed`.
- **Prove nel browser** (non nel repo): server locale su `sito/` e Playwright con `window.__JUTA_PROVA` per simulare la
  posa; controllare ricerca esercizi, scelta del braccio, avvisi rossi e uno squat in live con revisione.
- **In attesa da Gianluca**: regole per DEL-009, DEL-013, DEL-014/015, DEP-007 (a un braccio, vista frontale);
  taratura delle soglie in sala con gli istruttori; prossimi cataloghi (gambe, braccia, addome...).
- **Quando arriva un nuovo catalogo**: copiarlo in `esercizi/catalogo/` senza modificarlo, lanciare build e test,
  convertire i controlli di velocità su `durata` in `discesa`/`salita` (40% della fase prevista da `scheda.tempo`),
  aggiungere scelta del braccio agli esercizi a un braccio/alternati e `avviso_sicurezza` ai non analizzabili per
  sicurezza, tutto in `integrazioni.json`; se il prefisso dell'id è nuovo, aggiungerlo a `GRUPPI` in `web/motore.js`.
