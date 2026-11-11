"""Motore delle regole: conta le ripetizioni e controlla gli errori.

Tutto cio' che riguarda un esercizio (angoli, soglie, messaggi) sta nel file
YAML in /esercizi. Questo codice non conosce lo squat o la panca: legge le
regole e le applica. Per aggiungere un esercizio basta un nuovo file YAML.

v0.3: correzione anticipata al punto di inversione, eventi "errore" con
momento, valore e soglia, tempi della ripetizione, fine serie per inattivita'.
La versione JavaScript (web/motore.js) deve restare identica a questa.
"""
from collections import deque
import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
import time

from . import geometria

LATI = ("sx", "dx")
GRAVITA = {"verde": 0, "giallo": 1, "rosso": 2}
ISTERESI_INVERSIONE = 5.0
SOSTA_MINIMA = 0.5          # secondi fermi nella posizione di partenza prima della PRIMA ripetizione della serie
RITORNO_INDIETRO = 12.0     # gradi: se dopo l'inversione si torna verso l'estremo, la ripetizione non e' stata chiusa
MESSAGGIO_NON_CHIUSA = "Ripetizione non contata: torna fino alla posizione di partenza"   # di quanto deve "tornare indietro" la misura per dire che il movimento si e' invertito


# --------------------------------------------------------------------------
# Catalogo esercizi (file JSON in esercizi/catalogo) ed ereditarieta'
# --------------------------------------------------------------------------
TIPI_MISURA = {"angolo", "angolo_orientato", "inclinazione", "posizione", "distanza", "durata"}
# misure calcolate dal motore a fine ripetizione (in secondi), usabili negli errori con momento "fine"
MISURE_TEMPO = {"durata", "discesa", "pausa", "salita"}


UNITI_PER_NOME = {"misure", "testi_errori"}
# nomi dei punti usabili nelle misure (con _sx/_dx nella posa; naso_sx/naso_dx = naso, punta_piede = punta)
NOMI_PUNTI = {"naso", "spalla", "gomito", "polso", "anca", "ginocchio", "caviglia", "tallone", "punta", "punta_piede"}


def con_lato(nome):
    """True se il nome del punto indica gia' il lato (es. "ginocchio_sx"): non dipende dal lato analizzato."""
    return nome.endswith(("_sx", "_dx"))


def punto_noto(nome):
    return (nome[:-3] if con_lato(nome) else nome) in NOMI_PUNTI


def unisci(base, variante):
    """Una variante parte dal base e sovrascrive solo i campi indicati.
    - null toglie il campo (o la singola misura / il singolo testo)
    - misure e testi_errori si uniscono per nome
    - tutto il resto (ripetizione, errori, liste, testi...) se presente sostituisce quello del base"""
    out = copy.deepcopy(base)
    for k, v in variante.items():
        if k == "eredita_da":
            continue
        if v is None:
            out.pop(k, None)
        elif k in UNITI_PER_NOME and isinstance(v, dict) and isinstance(out.get(k), dict):
            d = dict(out[k])
            for kk, vv in v.items():
                if vv is None:
                    d.pop(kk, None)
                else:
                    d[kk] = copy.deepcopy(vv)
            out[k] = d
        else:
            out[k] = copy.deepcopy(v)
    return out


def risolvi_catalogo(voci):
    """voci: lista di {"id", "config_app", ...}. Restituisce {id: config risolta}."""
    per_id = {v["id"]: v for v in voci}
    risolte = {}

    def risolvi(i, catena=()):
        if i in risolte:
            return risolte[i]
        if i in catena:
            raise ValueError(f"Ereditarieta' circolare: {' -> '.join(catena + (i,))}")
        if i not in per_id:
            raise ValueError(f"Esercizio base non trovato: {i}")
        cfg = per_id[i].get("config_app") or {}
        padre = cfg.get("eredita_da")
        cfg = unisci(risolvi(padre, catena + (i,)), cfg) if padre else unisci({}, cfg)
        cfg["id"] = i
        risolte[i] = cfg
        return cfg

    for i in per_id:
        risolvi(i)
    return risolte


def completa(cfg):
    cfg.setdefault("lato", "auto")
    cfg.setdefault("visibilita_minima", 0.5)
    cfg.setdefault("messaggio_posizione", "Mettiti in posizione davanti alla camera")
    cfg.setdefault("errori", [])
    rip = cfg["ripetizione"]
    rip.setdefault("direzione", "diminuisce")
    rip.setdefault("durata_massima", 10.0)
    rip.setdefault("tolleranza_pausa", 5.0)
    for e in cfg["errori"]:
        e.setdefault("gravita", "giallo")
        e.setdefault("momento", "fine")
        e.setdefault("statistica", "minimo")
        e.setdefault("anticipa", True)
    return cfg


def durata_prevista(tempo):
    """Secondi previsti da un tempo tipo "2-1-1-0 (...)": somma delle prime quattro cifre (X = 1 s)."""
    if not tempo:
        return None
    parti = re.findall(r"\d+(?:[.,]\d+)?|X", tempo)[:4]
    if len(parti) < 4:
        return None
    return sum(1.0 if x == "X" else float(x.replace(",", ".")) for x in parti)


def durata_massima_da_scheda(cfg, scheda):
    """Finestra massima di una ripetizione: 3 volte la durata prevista dal tempo (minimo 6 s)."""
    prevista = durata_prevista((scheda or {}).get("tempo"))
    if prevista and cfg.get("ripetizione") and "durata_massima" not in cfg["ripetizione"]:
        cfg["ripetizione"]["durata_massima"] = max(6.0, round(3 * prevista, 2))
    return cfg


def analizzabile(cfg):
    return cfg.get("analizzabilita") != "non_analizzabile" and bool(cfg.get("ripetizione"))


def valida(cfg):
    """Elenco dei problemi di una configurazione (vuoto = tutto a posto)."""
    problemi = []
    misure = cfg.get("misure") or {}
    for nome, m in misure.items():
        if m.get("tipo") not in TIPI_MISURA:
            problemi.append(f"misura '{nome}': tipo sconosciuto '{m.get('tipo')}'")
    for nome, m in misure.items():
        for n in list(m.get("punti", [])) + ([m["punto"]] if "punto" in m else []) + list(m.get("scala", [])):
            if not punto_noto(n):
                problemi.append(f"misura '{nome}': punto sconosciuto '{n}'")
    note = set(misure) | MISURE_TEMPO | {f"{n}_asimmetria" for n in misure}
    rip = cfg.get("ripetizione") or {}
    if rip.get("misura") not in misure:
        problemi.append(f"ripetizione: misura '{rip.get('misura')}' non definita")
    for e in cfg.get("errori", []):
        if e.get("misura") not in note:
            problemi.append(f"errore '{e.get('id')}': misura '{e.get('misura')}' non definita")
        if "maggiore_di" not in e and "minore_di" not in e:
            problemi.append(f"errore '{e.get('id')}': manca la soglia (maggiore_di o minore_di)")
    return problemi


def applica_percorsi(cfg, imposta, rigido=False):
    """Modifica una config con percorsi tipo "lato", "ripetizione.x", "errori.<id>", "errori.<id>.<campo>".
    Con rigido=True un errore indicato ma non presente e' un problema (usato per le integrazioni)."""
    out = copy.deepcopy(cfg)
    for percorso, valore in imposta.items():
        parti = percorso.split(".")
        if parti[0] == "errori" and len(parti) >= 2:
            out.setdefault("errori", [])
            idx = next((k for k, e in enumerate(out["errori"]) if e["id"] == parti[1]), None)
            if len(parti) == 2 and valore is None:
                if idx is not None:
                    out["errori"].pop(idx)
            elif len(parti) == 2:
                nuovo = dict(copy.deepcopy(valore), id=parti[1])
                if idx is None:
                    out["errori"].append(nuovo)
                else:
                    out["errori"][idx] = nuovo
            elif idx is not None:
                out["errori"][idx][parti[2]] = copy.deepcopy(valore)
            elif rigido:
                raise ValueError(f"errore '{parti[1]}' non presente: impossibile applicare '{percorso}'")
            continue
        o = out
        for p in parti[:-1]:
            if rigido and p not in o:
                raise ValueError(f"campo '{p}' non presente: impossibile applicare '{percorso}'")
            o = o.setdefault(p, {})
        o[parti[-1]] = copy.deepcopy(valore)
    return out


def integra(voci, integrazioni):
    """Applica le integrazioni dell'app (esercizi/integrazioni.json) sopra il catalogo, senza toccare i file
    del catalogo. Ogni integrazione: {"id", "imposta": {percorso: valore}, "motivo"}. Agisce sulla config
    dell'esercizio PRIMA dell'ereditarieta', quindi vale anche per le varianti che ereditano quel campo."""
    per_id = {v["id"]: copy.deepcopy(v) for v in voci}
    for it in integrazioni:
        if it["id"] not in per_id:
            raise ValueError(f"integrazione per un esercizio inesistente: {it['id']}")
        v = per_id[it["id"]]
        try:
            v["config_app"] = applica_percorsi(v.get("config_app") or {}, it.get("imposta", {}), rigido=True)
        except ValueError as e:
            raise ValueError(f"integrazione {it['id']}: {e}") from None
    return list(per_id.values())


def leggi_catalogo(cartella="esercizi"):
    """Voci del catalogo (catalogo/*.json) con le integrazioni dell'app gia' applicate."""
    voci = []
    for p in sorted(Path(cartella, "catalogo").glob("*.json")):
        voci += json.loads(p.read_text(encoding="utf-8"))
    ids = [v["id"] for v in voci]
    doppi = sorted({i for i in ids if ids.count(i) > 1})
    if doppi:
        raise ValueError(f"id duplicati nel catalogo: {doppi}")
    f = Path(cartella, "integrazioni.json")
    return integra(voci, json.loads(f.read_text(encoding="utf-8"))) if f.exists() else voci


def applica_impostazioni(cfg, imposta):
    """Applica le scelte fatte prima della serie (es. {"lato": "dx"} o {"errori.profondita": {...}}).
    "errori.<id>" aggiunge o sostituisce un errore (null lo toglie), "errori.<id>.<campo>" ne cambia un campo,
    gli altri percorsi (es. "ripetizione.posizione_iniziale") cambiano il campo indicato."""
    return completa(applica_percorsi(cfg, imposta))


def carica_tutti(cartella="esercizi"):
    """Carica il catalogo (con le integrazioni). Restituisce solo gli esercizi analizzabili."""
    voci = leggi_catalogo(cartella)
    schede = {v["id"]: v.get("scheda") for v in voci}
    esercizi = {}
    for i, cfg in risolvi_catalogo(voci).items():
        if not analizzabile(cfg):
            continue
        problemi = valida(cfg)
        if problemi:
            print(f"ATTENZIONE {i}: " + "; ".join(problemi))
            continue
        esercizi[i] = completa(durata_massima_da_scheda(cfg, schede.get(i)))
    return esercizi


# --------------------------------------------------------------------------
# Stato restituito all'interfaccia
# --------------------------------------------------------------------------
@dataclass
class Stato:
    colore: str = "grigio"          # grigio | verde | giallo | rosso
    messaggio: str = ""
    ripetizioni: int = 0
    fase: str = "attesa"            # attesa | pronto | movimento
    lato: str = ""
    misure: dict = field(default_factory=dict)
    eventi: list = field(default_factory=list)  # eventi nuovi in questo fotogramma
    punti_usati: list = field(default_factory=list)
    errore: dict = None             # errore mostrato in questo momento (per il manichino)


def violato(err, valore):
    if valore is None:
        return False
    return (("maggiore_di" in err and valore > err["maggiore_di"])
            or ("minore_di" in err and valore < err["minore_di"]))


def soglia(err):
    return err.get("maggiore_di", err.get("minore_di"))


class Analizzatore:
    """Analizza una sequenza di pose per UN esercizio su UNA postazione."""

    def __init__(self, cfg, durata_messaggio=2.5, pausa_fine_serie=6.0):
        self.cfg = cfg
        self.durata_messaggio = durata_messaggio
        self.pausa_fine_serie = pausa_fine_serie
        self._vis_lati = {"sx": 0.0, "dx": 0.0}
        self._lisciate = {}
        self._grezze = {}   # posizioni assolute, per calcolare gli spostamenti
        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        self.ripetizioni = 0
        self.fase = "attesa"
        self._storico_pronto = deque(maxlen=10)
        self._base = {}
        self._min, self._max = {}, {}
        self._errori_rip = set()
        self._anticipati = set()
        self._inizio_rip = None
        self._estremo = None
        self._t_estremo = None
        self._invertito = False
        self._fine_ultima_rip = None
        self._serie = []            # (t, valore) della misura di ripetizione durante il movimento
        self._t_alto = None         # ultimo istante in posizione iniziale
        self._t_ingresso = None     # da quando si e' fermi nella posizione iniziale
        self._sosta_ok = False
        self._base_serie = None     # riferimento delle misure "posizione": inizio della serie
        self._picco_ritorno = None
        self._t_partenza = None
        self._errori_serie = {}
        self._msg = ("", "grigio", 0.0)
        self._err_msg = None
        self._ultima_persona = None

    # ------------------------------------------------------------------
    def aggiorna(self, posa, t=None):
        """posa: dizionario dei punti (o None). t: tempo in secondi."""
        t = time.monotonic() if t is None else t
        stato = Stato(ripetizioni=self.ripetizioni, fase=self.fase)

        # Nessuno nell'inquadratura: se dura, chiudo la serie
        if posa is None:
            if (self._ultima_persona is not None
                    and t - self._ultima_persona > self.pausa_fine_serie):
                self._chiudi_serie(stato)
            stato.messaggio = self.cfg["messaggio_posizione"]
            return stato
        self._ultima_persona = t

        # Persona ferma da troppo tempo dopo almeno una ripetizione: serie finita
        if (self.fase != "movimento" and self.ripetizioni > 0
                and self._fine_ultima_rip is not None
                and t - self._fine_ultima_rip > self.pausa_fine_serie):
            self._chiudi_serie(stato)

        lato = self._scegli_lato(posa)
        stato.lato = lato
        punti = self._punti_necessari(lato)
        stato.punti_usati = punti

        if min(posa[p][2] for p in punti) < self.cfg["visibilita_minima"]:
            stato.messaggio = self.cfg["messaggio_posizione"]
            return self._applica_messaggio(stato, t)

        misure = self._calcola_misure(posa, lato)
        stato.misure = misure
        self._macchina_ripetizioni(misure, t, stato)
        stato.ripetizioni = self.ripetizioni
        stato.fase = self.fase
        return self._applica_messaggio(stato, t)

    def termina(self, t=None):
        """Chiude la serie in corso (es. tasto Stop o fine del video)."""
        stato = Stato()
        self._chiudi_serie(stato)
        return stato.eventi

    # ------------------------------------------------------------------
    # Lati del corpo
    # ------------------------------------------------------------------
    def _scegli_lato(self, posa):
        if self.cfg["lato"] in ("sx", "dx", "entrambi"):
            return self.cfg["lato"]
        for lato in LATI:
            nomi = self._punti_necessari(lato)
            vis = sum(posa[n][2] for n in nomi) / len(nomi)
            self._vis_lati[lato] = 0.9 * self._vis_lati[lato] + 0.1 * vis
        return max(LATI, key=lambda l: self._vis_lati[l])

    def _nomi_base(self):
        # solo i punti delle misure usate (ripetizione ed errori): una misura ereditata ma inutilizzata
        # non deve sospendere l'analisi se i suoi punti non si vedono
        usate = {self.cfg["ripetizione"]["misura"]} | {e["misura"].replace("_asimmetria", "") for e in self.cfg["errori"]}
        nomi = set()
        for nome, m in self.cfg["misure"].items():
            if nome not in usate:
                continue
            nomi.update(m.get("punti", []))
            if "punto" in m:
                nomi.add(m["punto"])
            nomi.update(m.get("scala", []))
        return nomi

    def _punti_necessari(self, lato):
        lati = LATI if lato == "entrambi" else (lato,)
        return sorted({n if con_lato(n) else f"{n}_{l}" for n in self._nomi_base() for l in lati})

    # ------------------------------------------------------------------
    # Misure
    # ------------------------------------------------------------------
    def _misura_su_lato(self, spec, posa, l):
        p = lambda n: posa[n if con_lato(n) else f"{n}_{l}"][:2]
        tipo = spec["tipo"]
        if tipo == "angolo":
            a, b, c = spec["punti"]
            return geometria.angolo(p(a), p(b), p(c))
        if tipo == "angolo_orientato":
            a, b, c = spec["punti"]
            return geometria.angolo_orientato(p(a), p(b), p(c))
        if tipo == "inclinazione":
            basso, alto = spec["punti"]
            return geometria.inclinazione(p(basso), p(alto))
        if tipo == "posizione":
            s1, s2 = spec["scala"]
            scala = geometria.distanza(p(s1), p(s2)) or 1.0
            return -p(spec["punto"])[1] / scala
        if tipo == "distanza":
            # distanza tra due punti in percentuale del segmento "scala" (100 = lunga quanto il segmento)
            scala = geometria.distanza(p(spec["scala"][0]), p(spec["scala"][1]))
            if not scala:
                return None
            a, b = spec["punti"]
            return 100.0 * geometria.distanza(p(a), p(b)) / scala
        raise ValueError(f"Tipo di misura sconosciuto: {tipo}")

    def _calcola_misure(self, posa, lato):
        misure = {}
        for nome, spec in self.cfg["misure"].items():
            if spec["tipo"] == "durata":
                continue
            if lato == "entrambi":
                valori = [self._misura_su_lato(spec, posa, l) for l in LATI]
                if None in valori:
                    continue
                valore = sum(valori) / 2
                misure[f"{nome}_asimmetria"] = self._liscia(
                    f"{nome}_asimmetria", abs(valori[0] - valori[1]))
            else:
                valore = self._misura_su_lato(spec, posa, lato)
                if valore is None:
                    continue
            misure[nome] = self._liscia(nome, valore)
            if spec["tipo"] == "posizione":
                base = self._base.get(nome)
                misure[nome] = 0.0 if base is None else misure[nome] - base
                self._grezze[nome] = self._lisciate[nome]
        return misure

    def _liscia(self, nome, valore, alfa=0.5):
        prec = self._lisciate.get(nome)
        self._lisciate[nome] = valore if prec is None else alfa * valore + (1 - alfa) * prec
        return self._lisciate[nome]

    # ------------------------------------------------------------------
    # Conteggio ripetizioni
    # ------------------------------------------------------------------
    def _segno(self):
        return 1 if self.cfg["ripetizione"]["direzione"] == "diminuisce" else -1

    def _macchina_ripetizioni(self, misure, t, stato):
        rip = self.cfg["ripetizione"]
        valore = misure.get(rip["misura"])
        if valore is None:
            return
        segno = self._segno()
        in_posizione = segno * valore > segno * rip["posizione_iniziale"]
        in_movimento = segno * valore < segno * rip["inizio_movimento"]

        if self.fase in ("attesa", "pronto"):
            if in_posizione:
                if self._t_ingresso is None:
                    self._t_ingresso = t
                self.fase = "pronto"
                self._t_alto = t
                self._sosta_ok = t - self._t_ingresso >= SOSTA_MINIMA
                self._storico_pronto.append(dict(self._grezze))
            else:
                self._t_ingresso = None
                # la prima ripetizione della serie parte solo dopo una sosta nella posizione di partenza
                # (non conta gesti come raccogliere i manubri); le successive possono essere continue
                if self.fase == "pronto" and in_movimento and (self._sosta_ok or self.ripetizioni > 0):
                    self._inizia_ripetizione(misure, t)
            return

        # fase == "movimento"
        for nome, v in misure.items():
            self._min[nome] = min(self._min.get(nome, v), v)
            self._max[nome] = max(self._max.get(nome, v), v)
        self._serie.append((t, valore))
        if segno * valore < segno * self._estremo:
            self._estremo, self._t_estremo = valore, t
        self._controlla_errori("durante", misure, t, stato, self.ripetizioni + 1)

        # punto di inversione: segnalo subito gli errori di ampiezza
        if not self._invertito and segno * (valore - self._estremo) > ISTERESI_INVERSIONE:
            self._invertito = True
            self._picco_ritorno = valore
            self._controlla_errori("inversione", None, t, stato, self.ripetizioni + 1)
        elif self._invertito:
            if segno * valore > segno * self._picco_ritorno:
                self._picco_ritorno = valore
            elif segno * (self._picco_ritorno - valore) > RITORNO_INDIETRO and not in_posizione:
                # si torna verso l'estremo senza essere arrivati alla posizione di partenza
                return self._annulla_ripetizione(t, stato, "non_chiusa")

        if in_posizione:
            self._chiudi_ripetizione(t, stato)
        elif t - self._inizio_rip > rip["durata_massima"]:
            self._annulla_ripetizione(t, stato, "troppo_lunga")

    def _annulla_ripetizione(self, t, stato, motivo):
        """Finestra scartata: la ripetizione non viene contata e i suoi errori vanno ignorati."""
        stato.eventi.append({"tipo": "annullata", "esercizio": self.cfg["id"], "ripetizione": self.ripetizioni + 1,
                             "inizio_t": round(self._inizio_rip, 3), "t": round(t, 3), "motivo": motivo})
        self.fase = "attesa"
        self._t_ingresso = None
        self._mostra(self.cfg.get("messaggio_non_chiusa", MESSAGGIO_NON_CHIUSA), "giallo", t)

    def _inizia_ripetizione(self, misure, t):
        self.fase = "movimento"
        self._inizio_rip = t
        self._errori_rip = set()
        self._anticipati = set()
        self._estremo = misure[self.cfg["ripetizione"]["misura"]]
        self._t_estremo = t
        self._serie = [(t, self._estremo)]
        self._t_partenza = self._t_alto if self._t_alto is not None else t
        self._invertito = False
        self._picco_ritorno = None
        # misure "posizione": spostamento rispetto alla posizione di inizio della serie
        if self._base_serie is None and self._storico_pronto:
            self._base_serie = dict(self._storico_pronto[0])
        self._base = dict(self._base_serie or {})
        self._storico_pronto.clear()
        self._min = dict(misure)
        self._max = dict(misure)

    def _chiudi_ripetizione(self, t, stato):
        self.fase = "pronto"
        self.ripetizioni += 1
        durata = t - self._t_partenza          # ripetizione intera: dall'uscita dalla posizione iniziale al ritorno
        self._min["durata"] = self._max["durata"] = durata
        fasi = self._calcola_fasi(t)
        for k, v in fasi.items():
            self._min[k] = self._max[k] = v

        # gli errori anticipati restano solo se valgono anche con i valori finali
        for eid in list(self._anticipati):
            err = next(e for e in self.cfg["errori"] if e["id"] == eid)
            fonte = self._min if err["statistica"] == "minimo" else self._max
            if not violato(err, fonte.get(err["misura"])):
                self._errori_rip.discard(eid)
                self._anticipati.discard(eid)
        self._controlla_errori("fine", None, t, stato, self.ripetizioni)

        errori = sorted(self._errori_rip)
        for e in errori:
            self._errori_serie[e] = self._errori_serie.get(e, 0) + 1
        stato.eventi.append({
            "tipo": "ripetizione",
            "esercizio": self.cfg["id"],
            "numero": self.ripetizioni,
            "durata_s": round(durata, 2),
            "errori": errori,
            "fasi": {k: round(v, 2) for k, v in fasi.items()},
            "inizio_t": round(self._inizio_rip, 3),
            "fondo_t": round(self._t_estremo, 3),
            "fine_t": round(t, 3),
            "minimi": {k: round(v, 2) for k, v in self._min.items()},
            "massimi": {k: round(v, 2) for k, v in self._max.items()},
        })
        if not errori:
            self._mostra(self.cfg.get("messaggio_ok", "Ottima ripetizione!"), "verde", t)
        self._base = {}
        self._fine_ultima_rip = t

    def _calcola_fasi(self, t_fine):
        """Discesa: dall'uscita dalla posizione iniziale all'arrivo in basso.
        Pausa: tempo passato entro 'tolleranza_pausa' dal punto piu' basso.
        Salita: da quando si lascia il basso al ritorno in posizione iniziale."""
        toll = self.cfg["ripetizione"].get("tolleranza_pausa", 5.0)
        serie = self._serie
        i = min(range(len(serie)), key=lambda k: abs(serie[k][0] - self._t_estremo))
        i0 = i
        while i0 > 0 and abs(serie[i0 - 1][1] - self._estremo) <= toll:
            i0 -= 1
        i1 = i
        while i1 < len(serie) - 1 and abs(serie[i1 + 1][1] - self._estremo) <= toll:
            i1 += 1
        return {"discesa": serie[i0][0] - self._t_partenza,
                "pausa": serie[i1][0] - serie[i0][0],
                "salita": t_fine - serie[i1][0]}

    def _chiudi_serie(self, stato):
        if self.ripetizioni > 0:
            stato.eventi.append({
                "tipo": "serie",
                "esercizio": self.cfg["id"],
                "ripetizioni": self.ripetizioni,
                "errori": dict(self._errori_serie),
            })
        self.reset()

    # ------------------------------------------------------------------
    # Errori
    # ------------------------------------------------------------------
    def _anticipabile(self, err):
        rip = self.cfg["ripetizione"]
        estremo = "minimo" if rip["direzione"] == "diminuisce" else "massimo"
        return (err.get("anticipa", True) and err["momento"] == "fine"
                and err["misura"] == rip["misura"] and err["statistica"] == estremo)

    def _controlla_errori(self, momento, misure, t, stato, numero):
        for err in self.cfg["errori"]:
            if err["id"] in self._errori_rip:
                continue
            if momento == "inversione":
                if not self._anticipabile(err):
                    continue
            elif err["momento"] != momento:
                continue
            if momento == "durante":
                valore = misure.get(err["misura"])
            else:
                fonte = self._min if err["statistica"] == "minimo" else self._max
                valore = fonte.get(err["misura"])
            if not violato(err, valore):
                continue

            self._errori_rip.add(err["id"])
            if momento == "inversione":
                self._anticipati.add(err["id"])
            # il momento "vero" dell'errore: il punto piu' basso per gli errori di ampiezza
            ampiezza = err["misura"] == self.cfg["ripetizione"]["misura"] and momento != "durante"
            t_origine = self._t_estremo if ampiezza else t
            stato.eventi.append({
                "tipo": "errore",
                "esercizio": self.cfg["id"],
                "id": err["id"],
                "ripetizione": numero,
                "t": round(t, 3),
                "t_origine": round(t_origine, 3),
                "ritardo_s": round(t - t_origine, 3),
                "anticipato": momento == "inversione",
                "misura": err["misura"],
                "valore": round(valore, 2),
                "soglia": soglia(err),
                "gravita": err["gravita"],
            })
            self._mostra(err["messaggio"], err["gravita"], t, err, valore)

    # ------------------------------------------------------------------
    # Messaggio a schermo
    # ------------------------------------------------------------------
    def _mostra(self, testo, colore, t, err=None, valore=None):
        attuale_testo, attuale_colore, scadenza = self._msg
        if t < scadenza and GRAVITA.get(attuale_colore, 0) > GRAVITA.get(colore, 0):
            return
        self._msg = (testo, colore, t + self.durata_messaggio)
        self._err_msg = None if err is None else {
            "id": err["id"], "misura": err["misura"], "momento": err["momento"],
            "gravita": err["gravita"], "valore": valore, "soglia": soglia(err),
        }

    def _applica_messaggio(self, stato, t):
        testo, colore, scadenza = self._msg
        if t < scadenza:
            stato.messaggio, stato.colore = testo, colore
            stato.errore = self._err_msg
        elif not stato.messaggio:
            stato.colore = "verde" if self.fase != "attesa" else "grigio"
            stato.messaggio = {
                "attesa": self.cfg["messaggio_posizione"],
                "pronto": "Pronto",
                "movimento": "",
            }[self.fase]
        return stato
