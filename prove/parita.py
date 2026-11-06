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
        "lat_machine": [pm.posa_lat(170, 170)] * FPS + R(lambda g: pm.posa_lat(g, g), 170, 60)
                       + R(lambda g: pm.posa_lat(g, min(170, g + 40)), 170, 60),
        "PET-001": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 115, secondi=3.0)
                   + R(pp, 175, 80, secondi=3.0, abbassa_bacino=70) + R(pp, 175, 80, secondi=1.0)
                   + R(pp, 175, 80, secondi=3.0, gambe=140),
        "PET-007": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 80, secondi=3.0, abbassa_bacino=70),
        "PET-008": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 115, secondi=3.0),
        "PET-002": [pp(175)] * FPS + R(pp, 175, 80, secondi=3.0) + R(pp, 175, 80, secondi=3.0, abbassa_bacino=70),
    }


def main():
    es = carica_tutti(str(RADICE / "esercizi"))
    voci = []
    for f in sorted((RADICE / "esercizi" / "catalogo").glob("*.json")):
        voci += json.loads(f.read_text(encoding="utf-8"))
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
