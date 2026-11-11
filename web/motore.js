// Motore di analisi Juta v0.3 (versione JavaScript, identica a motore/regole.py).
// Non sa niente di squat o panca: applica le regole definite in ESERCIZI.

// Gli esercizi arrivano dal catalogo (file JSON in esercizi/catalogo): vedi costruisciCatalogo().

// Indici MediaPipe (sx/dx = sinistra/destra della persona)
// naso_sx/naso_dx: il naso e' unico, ma cosi' le misure lo trovano come gli altri punti (es. naso-spalla-gomito);
// punta_piede = punta (nome usato nel catalogo gambe)
const PUNTI = {
  naso: 0, naso_sx: 0, naso_dx: 0, spalla_sx: 11, spalla_dx: 12, gomito_sx: 13, gomito_dx: 14, polso_sx: 15, polso_dx: 16,
  anca_sx: 23, anca_dx: 24, ginocchio_sx: 25, ginocchio_dx: 26, caviglia_sx: 27, caviglia_dx: 28,
  tallone_sx: 29, tallone_dx: 30, punta_sx: 31, punta_dx: 32, punta_piede_sx: 31, punta_piede_dx: 32,
};
const NOMI_PUNTI = new Set(Object.keys(PUNTI).filter(n => /_(sx|dx)$/.test(n)).map(n => n.slice(0, -3)));
// un nome con il lato (es. "ginocchio_sx") non dipende dal lato analizzato: serve alle distanze tra i due lati
const conLato = n => /_(sx|dx)$/.test(n);
const puntoNoto = n => NOMI_PUNTI.has(conLato(n) ? n.slice(0, -3) : n);
const nomePunto = (n, l) => conLato(n) ? n : `${n}_${l}`;

const LATI = ["sx", "dx"];
const GRAVITA = { verde: 0, giallo: 1, rosso: 2 };
const ISTERESI_INVERSIONE = 5;
const SOSTA_MINIMA = 0.5;        // secondi fermi in partenza prima della PRIMA ripetizione della serie
const RITORNO_INDIETRO = 12;     // gradi: tornare verso l'estremo dopo l'inversione = ripetizione non chiusa
const USCITA_TENUTA = 1;         // secondi fuori dalla posizione prima di chiudere una tenuta (modalita' isometrica)
const MESSAGGIO_TENUTA = "Tieni la posizione";
const PERSISTENZA_TENUTA = 1;    // nelle tenute un errore "durante" conta solo se dura almeno questi secondi di fila
const ASSESTAMENTO_TENUTA = 1;   // secondi all'inizio della tenuta senza controlli "durante" (ci si sta assestando)
const MESSAGGIO_NON_CHIUSA = "Ripetizione non contata: torna fino alla posizione di partenza";
const r2 = v => Math.round(v * 100) / 100, r3 = v => Math.round(v * 1000) / 1000;

const geo = {
  angolo(a, b, c) {
    const bax = a[0] - b[0], bay = a[1] - b[1], bcx = c[0] - b[0], bcy = c[1] - b[1];
    const den = Math.hypot(bax, bay) * Math.hypot(bcx, bcy);
    if (!den) return null;
    return Math.acos(Math.max(-1, Math.min(1, (bax * bcx + bay * bcy) / den))) * 180 / Math.PI;
  },
  // 180 = in linea; meno di 180 = b sotto la retta a-c (bacino che cede); piu' di 180 = b sopra (sedere alto)
  angoloOrientato(a, b, c) {
    const th = geo.angolo(a, b, c);
    if (th === null) return null;
    const dx = c[0] - a[0];
    if (Math.abs(dx) < 1e-6) return th;
    const yRetta = a[1] + (c[1] - a[1]) * (b[0] - a[0]) / dx;
    return b[1] >= yRetta ? th : 360 - th;
  },
  inclinazione(basso, alto) {
    return Math.atan2(Math.abs(alto[0] - basso[0]), basso[1] - alto[1]) * 180 / Math.PI;
  },
  distanza(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); },
};

// ---------------------------------------------------------------------------
// Catalogo ed ereditarieta' (identico a motore/regole.py)
// ---------------------------------------------------------------------------
const TIPI_MISURA = new Set(["angolo", "angolo_orientato", "inclinazione", "posizione", "distanza", "durata"]);
// misure calcolate dal motore a fine ripetizione (in secondi), usabili negli errori con momento "fine"
const MISURE_TEMPO = new Set(["durata", "discesa", "pausa", "salita"]);
const copia = v => v === undefined ? v : JSON.parse(JSON.stringify(v));
const eOggetto = v => v !== null && typeof v === "object" && !Array.isArray(v);

// null toglie il campo; misure e testi_errori si uniscono per nome; tutto il resto sostituisce
const UNITI_PER_NOME = new Set(["misure", "testi_errori"]);
function unisci(base, variante) {
  const out = copia(base);
  for (const [k, v] of Object.entries(variante)) {
    if (k === "eredita_da") continue;
    if (v === null) delete out[k];
    else if (UNITI_PER_NOME.has(k) && eOggetto(v) && eOggetto(out[k])) {
      const d = { ...out[k] };
      for (const [kk, vv] of Object.entries(v)) { if (vv === null) delete d[kk]; else d[kk] = copia(vv); }
      out[k] = d;
    } else out[k] = copia(v);
  }
  return out;
}

function risolviCatalogo(voci) {
  const perId = Object.fromEntries(voci.map(v => [v.id, v]));
  const risolte = {};
  const risolvi = (id, catena = []) => {
    if (risolte[id]) return risolte[id];
    if (catena.includes(id)) throw new Error("Ereditarieta' circolare: " + [...catena, id].join(" -> "));
    if (!perId[id]) throw new Error("Esercizio base non trovato: " + id);
    const cfg = perId[id].config_app || {};
    const padre = cfg.eredita_da;
    const r = padre ? unisci(risolvi(padre, [...catena, id]), cfg) : unisci({}, cfg);
    r.id = id;
    return (risolte[id] = r);
  };
  for (const id of Object.keys(perId)) risolvi(id);
  return risolte;
}

function completa(cfg) {
  cfg.lato ??= "auto"; cfg.visibilita_minima ??= 0.5;
  cfg.messaggio_posizione ??= "Mettiti in posizione davanti alla camera"; cfg.errori ??= [];
  cfg.ripetizione.direzione ??= "diminuisce"; cfg.ripetizione.durata_massima ??= cfg.modalita === "balistica" ? 3 : 10; cfg.ripetizione.tolleranza_pausa ??= 5;
  for (const e of cfg.errori) { e.gravita ??= "giallo"; e.momento ??= "fine"; e.statistica ??= "minimo"; e.anticipa ??= true; }
  return cfg;
}

// Secondi previsti da un tempo "2-1-1-0 (...)": somma delle prime quattro cifre (X = 1 s). Identico a regole.py
function durataPrevista(tempo) {
  if (!tempo) return null;
  const parti = (tempo.match(/\d+(?:[.,]\d+)?|X/g) || []).slice(0, 4);
  if (parti.length < 4) return null;
  return parti.reduce((s, x) => s + (x === "X" ? 1 : parseFloat(x.replace(",", "."))), 0);
}
function durataMassimaDaScheda(cfg, scheda) {
  const prevista = durataPrevista(scheda?.tempo);
  if (prevista && cfg.ripetizione && cfg.ripetizione.durata_massima === undefined)
    cfg.ripetizione.durata_massima = Math.max(6, Math.round(3 * prevista * 100) / 100);
  return cfg;
}

const analizzabile = cfg => cfg.analizzabilita !== "non_analizzabile" && !!cfg.ripetizione && Object.keys(cfg.ripetizione).length > 0;

function valida(cfg) {
  const problemi = [], misure = cfg.misure || {};
  for (const [nome, m] of Object.entries(misure)) if (!TIPI_MISURA.has(m.tipo)) problemi.push(`misura '${nome}': tipo sconosciuto '${m.tipo}'`);
  const note = new Set([...Object.keys(misure), ...MISURE_TEMPO, ...Object.keys(misure).map(n => n + "_asimmetria")]);
  for (const [nome, m] of Object.entries(misure)) {
    for (const n of [...(m.punti || []), ...(m.punto ? [m.punto] : []), ...(m.scala || [])])
      if (!puntoNoto(n)) problemi.push(`misura '${nome}': punto sconosciuto '${n}'`);
  }
  const rip = cfg.ripetizione || {};
  if (cfg.modalita === "isometrica" && !("tenuta_minimo" in rip) && !("tenuta_massimo" in rip))
    problemi.push("ripetizione: in modalita' isometrica serve tenuta_minimo o tenuta_massimo");
  if (!(rip.misura in misure)) problemi.push(`ripetizione: misura '${rip.misura}' non definita`);
  for (const e of cfg.errori || []) {
    if (!note.has(e.misura)) problemi.push(`errore '${e.id}': misura '${e.misura}' non definita`);
    if (e.maggiore_di === undefined && e.minore_di === undefined) problemi.push(`errore '${e.id}': manca la soglia`);
  }
  return problemi;
}

// Scelte fatte prima della serie (es. {"lato": "dx"} o {"errori.profondita": {...}}): identico a regole.py
function applicaImpostazioni(cfg, imposta) {
  const out = copia(cfg);
  for (const [percorso, valore] of Object.entries(imposta)) {
    const parti = percorso.split(".");
    if (parti[0] === "errori" && parti.length >= 2) {
      const idx = out.errori.findIndex(e => e.id === parti[1]);
      if (parti.length === 2 && valore === null) { if (idx >= 0) out.errori.splice(idx, 1); }   // null = controllo disattivato
      else if (parti.length === 2) {
        const nuovo = { ...copia(valore), id: parti[1] };
        if (idx < 0) out.errori.push(nuovo); else out.errori[idx] = nuovo;
      } else if (idx >= 0) out.errori[idx][parti[2]] = copia(valore);
      continue;
    }
    let o = out;
    for (const p of parti.slice(0, -1)) o = (o[p] ??= {});
    o[parti[parti.length - 1]] = copia(valore);
  }
  return completa(out);
}

const GRUPPI = { PET: "Petto", DOR: "Schiena", SCH: "Schiena", GAM: "Gambe", SPA: "Spalle", DEA: "Spalle", DEL: "Spalle", DEP: "Spalle", BRA: "Braccia",
  GLU: "Glutei", QUA: "Quadricipiti", FEM: "Femorali", ADD: "Adduttori", ABD: "Abduttori", POL: "Polpacci" };

// Catalogo per l'app: nome e gruppo (ricavati se mancano), scheda, config risolta, esercizi analizzabili
function costruisciCatalogo(voci) {
  const risolte = risolviCatalogo(voci);
  const nomiDaRiferimenti = {};
  for (const v of voci) {
    const rp = v.scheda?.regressione_progressione || {};
    for (const s of [...(rp.regressione || []), ...(rp.progressione || [])]) {
      const m = /^([A-Z]{2,4}-\d{3})\s+(.+?)(\s*\(.*\))?$/.exec(s);
      if (m && /^[A-ZÀ-Ý]/.test(m[2]) && !nomiDaRiferimenti[m[1]]) nomiDaRiferimenti[m[1]] = m[2];
    }
  }
  const esercizi = {}, elenco = [];
  for (const v of voci) {
    const cfg = risolte[v.id];
    const nome = v.nome || cfg.nome || nomiDaRiferimenti[v.id] || v.id;
    const gruppo = v.gruppo || GRUPPI[v.id.split("-")[0]] || "Altro";
    const ok = analizzabile(cfg), problemi = ok ? valida(cfg) : [];
    if (problemi.length) console.warn(`Esercizio ${v.id} escluso dall'analisi:`, problemi);
    if (ok && !problemi.length) esercizi[v.id] = completa(durataMassimaDaScheda(copia({ ...cfg, nome }), v.scheda));
    elenco.push({ id: v.id, nome, gruppo, scheda: v.scheda || null, cfg, analizzabile: ok && !problemi.length, problemi });
  }
  return { elenco, esercizi };
}

function violato(err, valore) {
  if (valore === undefined || valore === null) return false;
  return (err.maggiore_di !== undefined && valore > err.maggiore_di)
    || (err.minore_di !== undefined && valore < err.minore_di);
}
const soglia = err => err.maggiore_di ?? err.minore_di;

// Converte i punti MediaPipe (0-1) in {nome: [x, y, visibilita]} in pixel
function posaDaMediapipe(lms, w, h) {
  const posa = {};
  for (const [nome, i] of Object.entries(PUNTI)) {
    const p = lms[i];
    posa[nome] = [p.x * w, p.y * h, p.visibility ?? 1];
  }
  return posa;
}

class Analizzatore {
  constructor(cfg, durataMessaggio = 2.5, pausaFineSerie = 6) {
    this.cfg = cfg; this.durataMessaggio = durataMessaggio; this.pausaFineSerie = pausaFineSerie;
    this.visLati = { sx: 0, dx: 0 }; this.lisciate = {}; this.grezze = {};
    this.reset();
  }

  reset() {
    this.ripetizioni = 0; this.fase = "attesa";
    this.storicoPronto = []; this.base = {}; this.min = {}; this.max = {};
    this.erroriRip = new Set(); this.anticipati = new Set(); this.inizioRip = null;
    this.estremo = null; this.tEstremo = null; this.invertito = false; this.fineUltimaRip = null;
    this.serie = []; this.tAlto = null; this.tPartenza = null;
    this.tIngresso = null; this.sostaOk = false; this.baseSerie = null; this.piccoRitorno = null;
    this.erroriSerie = {}; this.msg = ["", "grigio", 0]; this.errMsg = null; this.ultimaPersona = null;
    this.tDentro = null;   // modalita' isometrica: ultimo istante nella posizione da tenere
    this.tViolazione = {}; // modalita' isometrica: da quando ogni errore "durante" e' violato
  }

  aggiorna(posa, t) {
    const stato = { colore: "grigio", messaggio: "", ripetizioni: this.ripetizioni, fase: this.fase,
      lato: "", misure: {}, eventi: [], punti_usati: [], errore: null, tenuta_s: 0 };
    if (!posa) {
      this.verificaUscitaTenuta(t, stato);
      if (this.ultimaPersona !== null && t - this.ultimaPersona > this.pausaFineSerie) this.chiudiSerie(stato);
      stato.messaggio = this.cfg.messaggio_posizione;
      return stato;
    }
    this.ultimaPersona = t;
    if (this.fase !== "movimento" && this.ripetizioni > 0 && this.fineUltimaRip !== null
        && t - this.fineUltimaRip > this.pausaFineSerie) this.chiudiSerie(stato);

    const lato = this.scegliLato(posa);
    stato.lato = lato;
    const punti = this.puntiNecessari(lato);
    stato.punti_usati = punti;
    if (Math.min(...punti.map(p => posa[p][2])) < this.cfg.visibilita_minima) {
      this.verificaUscitaTenuta(t, stato);
      stato.messaggio = this.cfg.messaggio_posizione;
      return this.applicaMessaggio(stato, t);
    }
    const misure = this.calcolaMisure(posa, lato);
    stato.misure = misure;
    if (this.isometrica()) {
      this.macchinaTenuta(misure, t, stato);
      if (this.fase === "movimento") stato.tenuta_s = Math.round((this.tDentro - this.inizioRip) * 10) / 10;
    } else this.macchina(misure, t, stato);
    stato.ripetizioni = this.ripetizioni; stato.fase = this.fase;
    return this.applicaMessaggio(stato, t);
  }

  termina() {
    const stato = { eventi: [] };
    if (this.isometrica() && this.fase === "movimento") this.chiudiTenuta(this.tDentro, stato);
    this.chiudiSerie(stato);
    return stato.eventi;
  }

  scegliLato(posa) {
    const l = this.cfg.lato;
    if (l === "sx" || l === "dx" || l === "entrambi") return l;
    for (const lato of LATI) {
      const nomi = this.puntiNecessari(lato);
      const vis = nomi.reduce((s, n) => s + posa[n][2], 0) / nomi.length;
      this.visLati[lato] = 0.9 * this.visLati[lato] + 0.1 * vis;
    }
    return this.visLati.sx >= this.visLati.dx ? "sx" : "dx";
  }

  nomiBase() {
    // solo i punti delle misure usate (ripetizione ed errori), come in regole.py
    const usate = new Set([this.cfg.ripetizione.misura, ...this.cfg.errori.map(e => e.misura.replace("_asimmetria", ""))]);
    const s = new Set();
    for (const [nome, m] of Object.entries(this.cfg.misure)) {
      if (!usate.has(nome)) continue;
      (m.punti || []).forEach(n => s.add(n));
      if (m.punto) s.add(m.punto);
      (m.scala || []).forEach(n => s.add(n));
    }
    return s;
  }

  puntiNecessari(lato) {
    const lati = lato === "entrambi" ? LATI : [lato];
    const out = [];
    for (const n of this.nomiBase()) for (const l of lati) out.push(nomePunto(n, l));
    return [...new Set(out)].sort();
  }

  misuraSuLato(spec, posa, l) {
    const p = n => posa[nomePunto(n, l)];
    if (spec.tipo === "angolo") return geo.angolo(p(spec.punti[0]), p(spec.punti[1]), p(spec.punti[2]));
    if (spec.tipo === "angolo_orientato") return geo.angoloOrientato(p(spec.punti[0]), p(spec.punti[1]), p(spec.punti[2]));
    if (spec.tipo === "inclinazione") return geo.inclinazione(p(spec.punti[0]), p(spec.punti[1]));
    if (spec.tipo === "posizione") {
      const scala = geo.distanza(p(spec.scala[0]), p(spec.scala[1])) || 1;
      return -p(spec.punto)[1] / scala;
    }
    if (spec.tipo === "distanza") {   // distanza tra due punti in percentuale del segmento "scala"
      const scala = geo.distanza(p(spec.scala[0]), p(spec.scala[1]));
      if (!scala) return null;
      return 100 * geo.distanza(p(spec.punti[0]), p(spec.punti[1])) / scala;
    }
    throw new Error("Tipo di misura sconosciuto: " + spec.tipo);
  }

  calcolaMisure(posa, lato) {
    const misure = {};
    for (const [nome, spec] of Object.entries(this.cfg.misure)) {
      if (spec.tipo === "durata") continue;
      let valore;
      if (lato === "entrambi") {
        const v = LATI.map(l => this.misuraSuLato(spec, posa, l));
        if (v.includes(null)) continue;
        valore = (v[0] + v[1]) / 2;
        misure[`${nome}_asimmetria`] = this.liscia(`${nome}_asimmetria`, Math.abs(v[0] - v[1]));
      } else {
        valore = this.misuraSuLato(spec, posa, lato);
        if (valore === null) continue;
      }
      misure[nome] = this.liscia(nome, valore);
      if (spec.tipo === "posizione") {
        const base = this.base[nome];
        misure[nome] = base === undefined ? 0 : misure[nome] - base;
        this.grezze[nome] = this.lisciate[nome];
      }
    }
    return misure;
  }

  liscia(nome, valore, alfa = 0.5) {
    const prec = this.lisciate[nome];
    this.lisciate[nome] = prec === undefined ? valore : alfa * valore + (1 - alfa) * prec;
    return this.lisciate[nome];
  }

  segno() { return this.cfg.ripetizione.direzione === "diminuisce" ? 1 : -1; }

  macchina(misure, t, stato) {
    const rip = this.cfg.ripetizione;
    const valore = misure[rip.misura];
    if (valore === undefined) return;
    const segno = this.segno();
    const inPosizione = segno * valore > segno * rip.posizione_iniziale;
    const inMovimento = segno * valore < segno * rip.inizio_movimento;

    if (this.fase === "attesa" || this.fase === "pronto") {
      if (inPosizione) {
        if (this.tIngresso === null) this.tIngresso = t;
        this.fase = "pronto";
        this.tAlto = t;
        this.sostaOk = t - this.tIngresso >= SOSTA_MINIMA;
        this.storicoPronto.push({ ...this.grezze });
        if (this.storicoPronto.length > 10) this.storicoPronto.shift();
      } else {
        this.tIngresso = null;
        // in modalita' balistica (salti, swing continui) nessuna attesa: si parte subito
        if (this.fase === "pronto" && inMovimento && (this.sostaOk || this.ripetizioni > 0 || this.cfg.modalita === "balistica")) this.iniziaRipetizione(misure, t);
      }
      return;
    }
    for (const [n, v] of Object.entries(misure)) {
      this.min[n] = Math.min(this.min[n] ?? v, v);
      this.max[n] = Math.max(this.max[n] ?? v, v);
    }
    this.serie.push([t, valore]);
    if (segno * valore < segno * this.estremo) { this.estremo = valore; this.tEstremo = t; }
    this.controllaErrori("durante", misure, t, stato, this.ripetizioni + 1);
    if (!this.invertito && segno * (valore - this.estremo) > ISTERESI_INVERSIONE) {
      this.invertito = true;
      this.piccoRitorno = valore;
      this.controllaErrori("inversione", null, t, stato, this.ripetizioni + 1);
    } else if (this.invertito) {
      if (segno * valore > segno * this.piccoRitorno) this.piccoRitorno = valore;
      else if (segno * (this.piccoRitorno - valore) > RITORNO_INDIETRO && !inPosizione) return this.annullaRipetizione(t, stato, "non_chiusa");
    }
    if (inPosizione) this.chiudiRipetizione(t, stato);
    else if (t - this.inizioRip > rip.durata_massima) this.annullaRipetizione(t, stato, "troppo_lunga");
  }

  // Modalita' isometrica: una "ripetizione" e' una tenuta (cronometro al posto del conteggio). Identica a regole.py
  isometrica() { return this.cfg.modalita === "isometrica"; }

  macchinaTenuta(misure, t, stato) {
    const rip = this.cfg.ripetizione, valore = misure[rip.misura];
    if (valore === undefined) return;
    const dentro = (rip.tenuta_minimo ?? -Infinity) <= valore && valore <= (rip.tenuta_massimo ?? Infinity);
    if (this.fase === "attesa" || this.fase === "pronto") {
      if (!dentro) { this.tIngresso = null; this.fase = "attesa"; return; }
      if (this.tIngresso === null) this.tIngresso = t;
      this.fase = "pronto";
      this.storicoPronto.push({ ...this.grezze });
      if (this.storicoPronto.length > 10) this.storicoPronto.shift();
      if (t - this.tIngresso >= SOSTA_MINIMA) {     // in posizione da mezzo secondo: parte il cronometro
        this.tAlto = this.tIngresso;
        this.iniziaRipetizione(misure, this.tIngresso);
        this.tDentro = t;
        this.tViolazione = {};
      }
      return;
    }
    if (dentro) {
      this.tDentro = t;
      for (const [n, v] of Object.entries(misure)) {
        this.min[n] = Math.min(this.min[n] ?? v, v);
        this.max[n] = Math.max(this.max[n] ?? v, v);
      }
      if (t - this.inizioRip >= ASSESTAMENTO_TENUTA) this.controllaErrori("durante", misure, t, stato, this.ripetizioni + 1);
    } else this.verificaUscitaTenuta(t, stato);
  }

  verificaUscitaTenuta(t, stato) {
    if (this.isometrica() && this.fase === "movimento" && t - this.tDentro > USCITA_TENUTA) this.chiudiTenuta(this.tDentro, stato);
  }

  chiudiTenuta(tFine, stato) {
    this.fase = "attesa"; this.tIngresso = null; this.ripetizioni += 1;
    const durata = tFine - this.inizioRip;
    this.min.durata = this.max.durata = durata;
    this.controllaErrori("fine", null, tFine, stato, this.ripetizioni);
    const errori = [...this.erroriRip].sort();
    for (const e of errori) this.erroriSerie[e] = (this.erroriSerie[e] || 0) + 1;
    const arrot = o => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, r2(v)]));
    stato.eventi.push({ tipo: "ripetizione", esercizio: this.cfg.id, numero: this.ripetizioni, tenuta: true,
      durata_s: r2(durata), errori, fasi: {}, inizio_t: r3(this.inizioRip), fondo_t: r3(this.inizioRip), fine_t: r3(tFine),
      minimi: arrot(this.min), massimi: arrot(this.max) });
    if (!errori.length) this.mostra(this.cfg.messaggio_ok || "Ottima tenuta!", "verde", tFine);
    this.base = {};
    this.fineUltimaRip = tFine;
  }

  // finestra scartata: la ripetizione non viene contata e i suoi errori vanno ignorati
  annullaRipetizione(t, stato, motivo) {
    stato.eventi.push({ tipo: "annullata", esercizio: this.cfg.id, ripetizione: this.ripetizioni + 1,
      inizio_t: r3(this.inizioRip), t: r3(t), motivo });
    this.fase = "attesa";
    this.tIngresso = null;
    this.mostra(this.cfg.messaggio_non_chiusa || MESSAGGIO_NON_CHIUSA, "giallo", t);
  }

  iniziaRipetizione(misure, t) {
    this.fase = "movimento"; this.inizioRip = t; this.erroriRip = new Set(); this.anticipati = new Set();
    this.estremo = misure[this.cfg.ripetizione.misura]; this.tEstremo = t; this.invertito = false; this.piccoRitorno = null;
    this.serie = [[t, this.estremo]]; this.tPartenza = this.tAlto !== null ? this.tAlto : t;
    // misure "posizione": spostamento rispetto alla posizione di inizio della serie
    if (this.baseSerie === null && this.storicoPronto.length) this.baseSerie = { ...this.storicoPronto[0] };
    this.base = { ...(this.baseSerie || {}) };
    this.storicoPronto = [];
    this.min = { ...misure }; this.max = { ...misure };
  }

  chiudiRipetizione(t, stato) {
    this.fase = "pronto"; this.ripetizioni += 1;
    const durata = t - this.tPartenza;     // ripetizione intera: dall'uscita dalla posizione iniziale al ritorno
    this.min.durata = this.max.durata = durata;
    const fasi = this.calcolaFasi(t);
    for (const [k, v] of Object.entries(fasi)) this.min[k] = this.max[k] = v;
    for (const id of [...this.anticipati]) {
      const err = this.cfg.errori.find(e => e.id === id);
      const fonte = err.statistica === "minimo" ? this.min : this.max;
      if (!violato(err, fonte[err.misura])) { this.erroriRip.delete(id); this.anticipati.delete(id); }
    }
    this.controllaErrori("fine", null, t, stato, this.ripetizioni);
    const errori = [...this.erroriRip].sort();
    for (const e of errori) this.erroriSerie[e] = (this.erroriSerie[e] || 0) + 1;
    const arrot = o => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, r2(v)]));
    stato.eventi.push({ tipo: "ripetizione", esercizio: this.cfg.id, numero: this.ripetizioni,
      durata_s: r2(durata), errori, fasi: Object.fromEntries(Object.entries(fasi).map(([k, v]) => [k, r2(v)])), inizio_t: r3(this.inizioRip), fondo_t: r3(this.tEstremo), fine_t: r3(t),
      minimi: arrot(this.min), massimi: arrot(this.max) });
    if (!errori.length) this.mostra(this.cfg.messaggio_ok || "Ottima ripetizione!", "verde", t);
    this.base = {};
    this.fineUltimaRip = t;
  }

  // discesa: dall'uscita dalla posizione iniziale all'arrivo in basso; pausa: entro tolleranza dal punto
  // piu' basso; salita: da quando si lascia il basso al ritorno in posizione iniziale
  calcolaFasi(tFine) {
    const toll = this.cfg.ripetizione.tolleranza_pausa ?? 5, serie = this.serie;
    let i = 0;
    for (let k = 1; k < serie.length; k++) if (Math.abs(serie[k][0] - this.tEstremo) < Math.abs(serie[i][0] - this.tEstremo)) i = k;
    let i0 = i, i1 = i;
    while (i0 > 0 && Math.abs(serie[i0 - 1][1] - this.estremo) <= toll) i0--;
    while (i1 < serie.length - 1 && Math.abs(serie[i1 + 1][1] - this.estremo) <= toll) i1++;
    return { discesa: serie[i0][0] - this.tPartenza, pausa: serie[i1][0] - serie[i0][0], salita: tFine - serie[i1][0] };
  }

  chiudiSerie(stato) {
    if (this.ripetizioni > 0) stato.eventi.push({ tipo: "serie", esercizio: this.cfg.id,
      ripetizioni: this.ripetizioni, errori: { ...this.erroriSerie } });
    this.reset();
  }

  anticipabile(err) {
    const rip = this.cfg.ripetizione;
    const estremo = rip.direzione === "diminuisce" ? "minimo" : "massimo";
    return err.anticipa !== false && err.momento === "fine" && err.misura === rip.misura && err.statistica === estremo;
  }

  controllaErrori(momento, misure, t, stato, numero) {
    for (const err of this.cfg.errori) {
      if (this.erroriRip.has(err.id)) continue;
      if (momento === "inversione") { if (!this.anticipabile(err)) continue; }
      else if (err.momento !== momento) continue;
      const valore = momento === "durante" ? misure[err.misura]
        : (err.statistica === "minimo" ? this.min : this.max)[err.misura];
      if (!violato(err, valore)) { delete this.tViolazione[err.id]; continue; }
      let tInizio = t;
      if (momento === "durante" && this.isometrica()) {
        tInizio = this.tViolazione[err.id] ??= t;
        if (t - tInizio < PERSISTENZA_TENUTA) continue;
      }

      this.erroriRip.add(err.id);
      if (momento === "inversione") this.anticipati.add(err.id);
      const ampiezza = err.misura === this.cfg.ripetizione.misura && momento !== "durante";
      const tOrigine = ampiezza ? this.tEstremo : tInizio;
      stato.eventi.push({ tipo: "errore", esercizio: this.cfg.id, id: err.id, ripetizione: numero,
        t: r3(t), t_origine: r3(tOrigine), ritardo_s: r3(t - tOrigine), anticipato: momento === "inversione",
        misura: err.misura, valore: r2(valore), soglia: soglia(err), gravita: err.gravita });
      this.mostra(err.messaggio, err.gravita, t, err, valore);
    }
  }

  mostra(testo, colore, t, err = null, valore = null) {
    const [, c, scad] = this.msg;
    if (t < scad && (GRAVITA[c] || 0) > (GRAVITA[colore] || 0)) return;
    this.msg = [testo, colore, t + this.durataMessaggio];
    this.errMsg = err ? { id: err.id, misura: err.misura, momento: err.momento, gravita: err.gravita,
      valore, soglia: soglia(err) } : null;
  }

  applicaMessaggio(stato, t) {
    const [testo, colore, scad] = this.msg;
    if (t < scad) { stato.messaggio = testo; stato.colore = colore; stato.errore = this.errMsg; }
    else if (!stato.messaggio) {
      stato.colore = this.fase !== "attesa" ? "verde" : "grigio";
      stato.messaggio = { attesa: this.cfg.messaggio_posizione, pronto: "Pronto",
        movimento: this.isometrica() ? (this.cfg.messaggio_tenuta || MESSAGGIO_TENUTA) : "" }[this.fase];
    }
    return stato;
  }
}

if (typeof module !== "undefined") module.exports = { durataPrevista, Analizzatore, posaDaMediapipe, geo, violato, soglia, unisci, risolviCatalogo, costruisciCatalogo, completa, valida, applicaImpostazioni };
