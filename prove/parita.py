"""Verifica che il motore Python (motore/regole.py) e quello del telefono (web/motore.js)
diano ESATTAMENTE gli stessi risultati: stesse configurazioni risolte dal catalogo e stessi
eventi (ripetizioni, errori, tempi) sugli stessi movimenti simulati.

    python prove/parita.py        (serve Node.js installato)
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

import prova_motore as pm  # noqa: E402
from motore.regole import Analizzatore, carica_tutti  # noqa: E402

FPS = 30
R = pm.ripetizione


def casi():
    sq = lambda k, **kw: pm.posa_squat(k, **kw)
    pp = lambda g, **kw: pm.posa_piegamento(g, **kw)
    pb = lambda g, **kw: pm.posa_panca_piana(g, **kw)
    return {
        "squat": [pm.posa_squat(175)] * FPS + R(sq, 175, 80) + R(sq, 175, 115)
                 + R(lambda k, busto=0, tallone=0: pm.posa_squat(k, 30 + busto, tallone), 175, 85, busto=40, tallone=0.2),
        "PET-012": [pb(170)] * FPS + R(pb, 170, 80, secondi=3.0) + R(pb, 170, 80, secondi=3.0, sollevamento=0.2)
                   + R(pb, 170, 80, secondi=3.0, avambraccio=35) + R(pb, 170, 80, secondi=1.0),
        "PET-017": [pb(170)] * FPS + R(pb, 170, 80, secondi=3.0) + R(pb, 170, 80, secondi=3.0, gambe=120),
        "PET-019": [pb(170)] * FPS + R(pb, 170, 115, secondi=3.0) + R(pb, 170, 130, secondi=3.0),
        "PET-020": [pb(170)] * FPS + R(pb, 170, 110, secondi=3.0) + R(pb, 170, 110, secondi=1.0),
        "PET-014": [pb(170)] * FPS + pm.ripetizione_fasi(pb, 170, 80, 2, 2, 1) + pm.ripetizione_fasi(pb, 170, 80, 2, 0, 1),
        "PET-025": [pm.posa_pullover(95)] * FPS + pm.ripetizione_fasi(lambda a, **kw: pm.posa_pullover(a, **kw), 95, 170, 3, 1, 2)
                   + pm.ripetizione_fasi(lambda a, **kw: pm.posa_pullover(a, **kw), 95, 170, 3, 1, 2, sollevamento=0.2),
        # valori non interi: dati simulati che cadono esattamente su una soglia possono differire di un fotogramma
        # tra Python e JavaScript (ultima cifra decimale di acos); con dati reali non succede
        "PET-021": [pb(110.3)] * FPS + pm.ripetizione_fasi(pb, 110.3, 170.2, 1, 1, 2) + pm.ripetizione_fasi(pb, 170.2, 110.3, 2, 2, 1)
                   + pm.ripetizione_fasi(pb, 170.2, 110.3, 2, 0.2, 1),
        "PET-015": [pb(170)] * FPS + R(pb, 170, 90, secondi=5.0) + R(pb, 170, 115, secondi=3.0),
        "PET-011": [pp(175)] * FPS + R(pp, 175, 80, secondi=1.5) + R(pp, 175, 80, secondi=1.5, abbassa_bacino=70),
        "DOR-020": [pm.posa_alzata(160.3, 160.3)] * FPS
                   + pm.ripetizione_fasi(lambda a: pm.posa_alzata(a, a), 160.3, 35.2, 1, 0.5, 2)
                   + pm.ripetizione_fasi(lambda a: pm.posa_alzata(a, a), 160.3, 70.4, 1, 0.5, 2)
                   + pm.ripetizione_fasi(lambda a: pm.posa_alzata(a, a), 160.3, 35.2, 1, 0.5, 0.6),
        "PET-001": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 115, secondi=3.0)
                   + R(pp, 175, 80, secondi=3.0, abbassa_bacino=70) + R(pp, 175, 80, secondi=3.0, abbassa_bacino=-70)
                   + R(pp, 175, 80, secondi=1.0)
                   + R(pp, 175, 80, secondi=3.0, gambe=140),
        "PET-007": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 80, secondi=3.0, abbassa_bacino=70),
        "PET-008": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 115, secondi=3.0),
        "DEL-007": [pm.posa_alzata(15.3)] * FPS + R(pm.posa_alzata, 15.3, 88.7, secondi=3.0)
                   + R(pm.posa_alzata, 15.3, 55.2, secondi=3.0) + R(pm.posa_alzata, 15.3, 88.7, secondi=0.8),
        "DEL-005": [pm.posa_alzata(15.3, 15.3)] * FPS + R(lambda a: pm.posa_alzata(a, a), 15.3, 88.7, secondi=3.0)
                   + R(lambda a: pm.posa_alzata(a, max(15.3, a - 35)), 15.3, 88.7, secondi=3.0),
        "GLU-001": [pm.posa_ponte(140.3)] * FPS + pm.ripetizione_fasi(pm.posa_ponte, 140.3, 175.2, 1, 2, 2)
                   + pm.ripetizione_fasi(pm.posa_ponte, 140.3, 160.4, 1, 1, 2) + pm.ripetizione_fasi(pm.posa_ponte, 140.3, 175.2, 1, 1, 0.4),
        "POL-001": [pm.posa_polpaccio(105.3)] * FPS + pm.ripetizione_fasi(pm.posa_polpaccio, 105.3, 135.2, 1, 1, 2)
                   + pm.ripetizione_fasi(pm.posa_polpaccio, 105.3, 121.4, 1, 1, 2),
        "DEP-003": [pm.posa_alzata(30.3, 30.3)] * FPS + R(lambda a: pm.posa_alzata(a, a), 30.3, 80.2, secondi=3.0),
        "ADD-007": [pm.posa_seduto_fronte(240.3)] * FPS + pm.ripetizione_fasi(pm.posa_seduto_fronte, 240.3, 80.2, 1, 1, 2)
                   + pm.ripetizione_fasi(pm.posa_seduto_fronte, 240.3, 150.4, 1, 1, 2)
                   + pm.ripetizione_fasi(pm.posa_seduto_fronte, 240.3, 80.2, 1, 1, 0.4),
        "ABD-006": [pm.posa_seduto_fronte(100.3)] * FPS + pm.ripetizione_fasi(pm.posa_seduto_fronte, 100.3, 260.2, 1, 1, 2)
                   + pm.ripetizione_fasi(pm.posa_seduto_fronte, 100.3, 190.4, 1, 1, 2),
        "QUA-006": [pm.posa_squat(175)] * FPS + pm.tenuta(pm.posa_squat, 175, 95.3, 10, entrata=2)
                   + pm.tenuta(pm.posa_squat, 175, 110.4, 5, entrata=2),
        "DOR-064": [pm.posa_front_lever(178.3)] * FPS + pm.tenuta(pm.posa_front_lever, 178.3, 90.3, 6)
                   + pm.tenuta(pm.posa_front_lever, 178.3, 112.4, 4) + pm.tenuta(pm.posa_front_lever, 178.3, 90.3, 4, abbassa_bacino=60),
        "ABD-005": [pm.posa_fronte_gambe(92.3)] * FPS + pm.ripetizione_fasi(pm.posa_fronte_gambe, 92.3, 125.2, 1, 1, 2)
                   + pm.ripetizione_fasi(pm.posa_fronte_gambe, 92.3, 110.4, 1, 1, 2),
        "ADD-006": [pm.posa_fronte_gambe(115.3)] * FPS + pm.ripetizione_fasi(pm.posa_fronte_gambe, 115.3, 75.2, 1, 1, 2)
                   + pm.ripetizione_fasi(pm.posa_fronte_gambe, 115.3, 92.4, 1, 1, 2),
        "PET-002": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 80, secondi=3.0, abbassa_bacino=70),
    }


def main():
    es = carica_tutti(str(RADICE / "esercizi"))
    from motore.regole import leggi_catalogo
    voci = leggi_catalogo(str(RADICE / "esercizi"))
    risultati = {}
    c = casi()
    for k, frames in c.items():
        a, ev, t = Analizzatore(es[k]), [], 0.0
        for p in frames:
            ev += a.aggiorna(p, t).eventi
            t += 1 / FPS
        for _ in range(8 * FPS):
            ev += a.aggiorna(None, t).eventi
            t += 1 / FPS
        risultati[k] = ev
    from motore.regole import applica_impostazioni
    impost = {}
    for i, cfg in es.items():
        for imp in cfg.get("impostazioni", []):
            for o in imp["opzioni"]:
                chiave = f"{i}|{imp['id']}|{o['etichetta']}"
                r = applica_impostazioni(cfg, o["imposta"])
                impost[chiave] = {"imposta": o["imposta"], "cfg": {c_: r.get(c_) for c_ in ("misure", "ripetizione", "errori", "lato")}}
    chiavi = ("misure", "ripetizione", "errori", "lato")
    dati = {
        "voci": voci,
        "cfg": {k: {c_: v.get(c_) for c_ in chiavi} for k, v in es.items()},
        "cases": {k: [{n: list(v) for n, v in p.items()} for p in fr] for k, fr in c.items()},
        "py": risultati,
        "impostazioni": impost,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(dati, f)
    esito = subprocess.run(["node", str(RADICE / "prove" / "parita.js"), f.name], capture_output=True, text=True)
    print(esito.stdout, esito.stderr, sep="")
    sys.exit(0 if esito.returncode == 0 else 1)


if __name__ == "__main__":
    main()
