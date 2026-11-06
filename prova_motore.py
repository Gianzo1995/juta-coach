"""Autotest del motore: simula delle ripetizioni (senza camera) e controlla
che conteggio ed errori siano corretti. Se vedi 'TUTTO OK' il motore funziona.

Uso:  python prova_motore.py
"""
import math
from pathlib import Path

from motore.regole import Analizzatore, carica_tutti

FPS = 30


def punti_entrambi_lati(punti, vis_sx=0.95, vis_dx=0.95):
    posa = {}
    for nome, (x, y) in punti.items():
        posa[f"{nome}_sx"] = (x, y, vis_sx)
        posa[f"{nome}_dx"] = (x, y, vis_dx)
    return posa


# ---------------- figure sintetiche ----------------
def posa_squat(ginocchio, busto=30, tallone=0.0):
    s = math.radians((180 - ginocchio) / 2)
    caviglia = (500, 600)
    g = (caviglia[0] + 160 * math.sin(s), caviglia[1] - 160 * math.cos(s))
    a = (g[0] - 160 * math.sin(s), g[1] - 160 * math.cos(s))
    l = math.radians(busto)
    sp = (a[0] + 200 * math.sin(l), a[1] - 200 * math.cos(l))
    return punti_entrambi_lati({
        "caviglia": caviglia, "ginocchio": g, "anca": a, "spalla": sp,
        "gomito": (sp[0] + 20, sp[1] + 40), "polso": (sp[0] + 30, sp[1]),
        "tallone": (470, 620 - tallone * 160), "punta": (560, 625),
    }, vis_sx=0.95, vis_dx=0.4)


def braccio(spalla, gomito_ang, verso):
    """Braccio: omero verso il basso/esterno, avambraccio piegato di gomito_ang."""
    a1 = math.radians(150 if verso > 0 else 30)   # direzione omero
    g = (spalla[0] + 120 * math.cos(a1), spalla[1] + 120 * math.sin(a1))
    a2 = a1 + verso * math.radians(180 - gomito_ang)
    p = (g[0] + 120 * math.cos(a2), g[1] + 120 * math.sin(a2))
    return g, p


def posa_panca_piana(gomito, sollevamento=0.0, avambraccio=0.0, gambe=180.0):
    """Panca piana vista di lato: testa a sinistra, piedi a destra, avambraccio verticale.
    sollevamento = bacino che si stacca (in lunghezze del busto), avambraccio = inclinazione in gradi."""
    L, sp = 110, (500, 450)
    t = math.radians(gomito)
    v = (math.sin(t), -math.cos(t))                           # dal gomito verso la spalla
    g = (sp[0] - L * v[0], sp[1] - L * v[1])
    a = math.radians(avambraccio)
    po = (g[0] + L * math.sin(a), g[1] - L * math.cos(a))
    an = (sp[0] + 230, sp[1] - sollevamento * 230)
    posa = {"naso": (sp[0] - 60, sp[1] - 15, 0.99)}
    gi = (an[0] + 200, an[1])
    k = math.radians(180 - gambe)                              # gambe piegate verso il basso
    ca = (gi[0] + 200 * math.cos(k), gi[1] + 200 * math.sin(k))
    for nome, (x, y) in {"spalla": sp, "gomito": g, "polso": po, "anca": an, "ginocchio": gi, "caviglia": ca}.items():
        posa[f"{nome}_sx"] = (x, y, 0.95)
        posa[f"{nome}_dx"] = (x + 5, y - 4, 0.4)
    return posa


def posa_panca(gomito, sollevamento=0.0):
    sp, an = (400, 500), (600, 500 - sollevamento * 200)
    g, p = braccio(sp, gomito, 1)
    return punti_entrambi_lati({"spalla": sp, "anca": an, "gomito": g, "polso": p},
                               vis_dx=0.3)


def posa_lat(gomito_sx, gomito_dx):
    posa = {}
    for lato, sp, ang, verso in (("sx", (600, 300), gomito_sx, -1),
                                 ("dx", (400, 300), gomito_dx, 1)):
        g, p = braccio(sp, ang, verso)
        for nome, pt in (("spalla", sp), ("gomito", g), ("polso", p)):
            posa[f"{nome}_{lato}"] = (pt[0], pt[1], 0.95)
    return posa


def posa_piegamento(gomito, abbassa_bacino=0.0, gambe=180.0, w=1280, h=720):
    """Piegamento visto di lato: mani a terra a sinistra, piedi a destra.
    abbassa_bacino in pixel (positivo = bacino che cede), gambe = angolo del ginocchio."""
    pavimento = 600
    polso = (400, pavimento)
    g = (polso[0], pavimento - 120)                       # avambraccio verticale
    phi = math.radians(180 - gomito)                       # braccio ruota verso i piedi
    sp = (g[0] + 120 * math.sin(phi), g[1] - 120 * math.cos(phi))
    cav = (sp[0] + 420, pavimento - 10)
    an = ((sp[0] + cav[0]) / 2, (sp[1] + cav[1]) / 2 + abbassa_bacino)
    k = math.radians((180 - gambe) / 2)                    # ginocchia piegate verso il basso
    gi = ((an[0] + cav[0]) / 2, (an[1] + cav[1]) / 2 + 105 * math.sin(k))
    pts = {"polso": polso, "gomito": g, "spalla": sp, "anca": an, "ginocchio": gi, "caviglia": cav,
           "tallone": (cav[0] + 15, cav[1] - 15), "punta": (cav[0] + 5, pavimento)}
    posa = {"naso": (sp[0] - 60, sp[1] - 10, 0.99)}
    for nome, (x, y) in pts.items():
        posa[f"{nome}_sx"] = (x, y, 0.95)
        posa[f"{nome}_dx"] = (x + 6, y - 3, 0.4)
    return posa


# ---------------- simulazione ----------------
def ripetizione(fn_posa, inizio, fondo, secondi=2.0, **extra_fondo):
    """Genera una ripetizione: da 'inizio' a 'fondo' e ritorno, piu' una pausa."""
    n = int(secondi * FPS)
    frames = []
    for i in range(n):
        f = math.sin(math.pi * i / (n - 1))   # 0 -> 1 -> 0
        val = inizio + (fondo - inizio) * f
        extra = {k: v * f for k, v in extra_fondo.items()}
        frames.append(fn_posa(val, **extra))
    frames += [fn_posa(inizio)] * FPS          # 1 s di pausa in alto
    return frames


def ripetizione_fasi(fn_posa, inizio, fondo, discesa, pausa, salita, **extra_fondo):
    """Ripetizione a velocita' costante: discesa, fermo in basso, salita (in secondi), poi 1 s fermo in alto."""
    frames = []
    def posa(f):
        return fn_posa(inizio + (fondo - inizio) * f, **{k: v * f for k, v in extra_fondo.items()})
    for i in range(int(discesa * FPS)):
        frames.append(posa(i / (discesa * FPS)))
    frames += [posa(1.0)] * int(pausa * FPS)
    for i in range(int(salita * FPS)):
        frames.append(posa(1 - i / (salita * FPS)))
    return frames + [fn_posa(inizio)] * FPS


def esegui(analizzatore, frames):
    eventi, t = [], 0.0
    for posa in frames:
        stato = analizzatore.aggiorna(posa, t)
        eventi += stato.eventi
        t += 1 / FPS
    for _ in range(8 * FPS):                   # 8 s senza nessuno -> fine serie
        eventi += analizzatore.aggiorna(None, t).eventi
        t += 1 / FPS
    return eventi


def verifica(nome, eventi, attesi):
    rip = [e for e in eventi if e["tipo"] == "ripetizione"]
    serie = [e for e in eventi if e["tipo"] == "serie"]
    ottenuti = [e["errori"] for e in rip]
    ok = ottenuti == attesi and len(serie) == 1
    print(f"{'OK ' if ok else 'ERRORE'}  {nome}: {len(rip)} ripetizioni, errori {ottenuti}")
    if not ok:
        print(f"         attesi {attesi}")
    return ok


def verifica_anticipo(nome, eventi):
    """Gli errori di ampiezza devono arrivare al punto di inversione, prima della fine della ripetizione."""
    rip = {e["numero"]: e for e in eventi if e["tipo"] == "ripetizione"}
    anticipati = [e for e in eventi if e["tipo"] == "errore" and e["anticipato"]]
    ok = bool(anticipati) and all(e["t"] < rip[e["ripetizione"]]["fine_t"] and e["id"] in rip[e["ripetizione"]]["errori"]
                                  for e in anticipati)
    for e in anticipati:
        r = rip[e["ripetizione"]]
        print(f"         {e['id']}: avviso {r['fine_t'] - e['t']:.2f} s prima della fine, "
              f"{e['ritardo_s']:.2f} s dopo il punto piu' basso")
    print(f"{'OK ' if ok else 'ERRORE'}  {nome}: correzione anticipata")
    return ok


def main():
    es = carica_tutti(str(Path(__file__).resolve().parent / "esercizi"))
    risultati = []

    # SQUAT: buona, troppo alta, busto inclinato + talloni
    frames = [posa_squat(175)] * FPS
    frames += ripetizione(lambda k, **kw: posa_squat(k, **kw), 175, 80)
    frames += ripetizione(lambda k, **kw: posa_squat(k, **kw), 175, 115)
    frames += ripetizione(lambda k, busto=0, tallone=0: posa_squat(k, 30 + busto, tallone),
                          175, 85, busto=40, tallone=0.2)
    ev = esegui(Analizzatore(es["squat"]), frames)
    risultati.append(verifica("Squat", ev, [[], ["profondita"], ["busto_inclinato", "talloni"]]))
    risultati.append(verifica_anticipo("Squat", ev))

    # PANCA PIANA (PET-012): buona, non arriva al petto, glutei staccati, avambraccio inclinato, rimbalzo
    pb = lambda g, **kw: posa_panca_piana(g, **kw)
    frames = [pb(170)] * FPS
    frames += ripetizione(pb, 170, 80, secondi=3.0)
    frames += ripetizione(pb, 170, 110, secondi=3.0)
    frames += ripetizione(pb, 170, 80, secondi=3.0, sollevamento=0.2)
    frames += ripetizione(pb, 170, 80, secondi=3.0, avambraccio=35)
    frames += ripetizione(pb, 170, 80, secondi=1.0)
    risultati.append(verifica("Panca piana PET-012", esegui(Analizzatore(es["PET-012"]), frames),
                              [[], ["profondita"], ["glutei_staccati"], ["avambraccio_inclinato"], ["rimbalzo"]]))

    # PANCA CON FERMO (PET-014): tempo 2-2-1 ok, stessa ripetizione senza fermo = fermo mancato
    frames = [pb(170)] * FPS + ripetizione_fasi(pb, 170, 80, 2, 2, 1) + ripetizione_fasi(pb, 170, 80, 2, 0, 1)
    ev = esegui(Analizzatore(es["PET-014"]), frames)
    risultati.append(verifica("Panca con fermo PET-014", ev, [[], ["fermo_breve"]]))

    # FASI: i tempi misurati devono somigliare a quelli eseguiti (2-2-1 e 0,5-0-1)
    frames = [pb(170)] * FPS + ripetizione_fasi(pb, 170, 80, 2, 2, 1) + ripetizione_fasi(pb, 170, 80, 0.5, 0, 1)
    ev = esegui(Analizzatore(es["PET-012"]), frames)
    rip = [e for e in ev if e["tipo"] == "ripetizione"]
    f1, f2 = rip[0]["fasi"], rip[1]["fasi"]
    ok = (1.6 <= f1["discesa"] <= 2.1 and 1.8 <= f1["pausa"] <= 2.4 and 0.7 <= f1["salita"] <= 1.1
          and f2["discesa"] < 0.8 and rip[0]["errori"] == [] and rip[1]["errori"] == ["rimbalzo"])
    print(f"{'OK ' if ok else 'ERRORE'}  Fasi misurate: 2-2-1 -> {f1}, discesa veloce -> {f2} {rip[1]['errori']}")
    risultati.append(ok)

    # IMPOSTAZIONI prima della serie: lato scelto (PET-006) e tavolette (PET-020)
    from motore.regole import applica_impostazioni
    c6 = applica_impostazioni(es["PET-006"], {"lato": "sx"})
    c20 = applica_impostazioni(es["PET-020"], {"errori.profondita": {"messaggio": "x", "misura": "gomito", "statistica": "minimo", "maggiore_di": 125}})
    ok = c6["lato"] == "sx" and es["PET-006"]["lato"] == "auto" and any(e["id"] == "profondita" and e["momento"] == "fine" for e in c20["errori"])
    print(f"{'OK ' if ok else 'ERRORE'}  Impostazioni: lato scelto e soglia per numero di tavolette")
    risultati.append(ok)

    # LAT: buona, asimmetrica, ampiezza ridotta
    frames = [posa_lat(170, 170)] * FPS
    frames += ripetizione(lambda g: posa_lat(g, g), 170, 60)
    frames += ripetizione(lambda g: posa_lat(g, min(170, g + 40)), 170, 60)
    frames += ripetizione(lambda g: posa_lat(g, g), 170, 100)
    ev = esegui(Analizzatore(es["lat_machine"]), frames)
    risultati.append(verifica("Lat machine", ev, [[], ["asimmetria"], ["ampiezza"]]))
    risultati.append(verifica_anticipo("Lat machine", ev))

    # PIEGAMENTI (PET-001, ereditato dal catalogo): buono, poco profondo, bacino che cede, troppo veloce
    pp = lambda g, **kw: posa_piegamento(g, **kw)
    frames = [pp(175)] * FPS
    frames += ripetizione(pp, 175, 80, secondi=3.0)
    frames += ripetizione(pp, 175, 115, secondi=3.0)
    frames += ripetizione(pp, 175, 80, secondi=3.0, abbassa_bacino=70)
    frames += ripetizione(pp, 175, 80, secondi=1.0)
    ev = esegui(Analizzatore(es["PET-001"]), frames)
    risultati.append(verifica("Piegamenti PET-001", ev, [[], ["profondita"], ["allineamento"], ["troppo_veloce"]]))
    # PET-002 (sulle ginocchia) eredita da PET-001 ma non ha piu' la misura "gambe"
    risultati.append("gambe" not in es["PET-002"]["misure"] and es["PET-002"]["misure"]["corpo"]["punti"][2] == "ginocchio")
    print(f"{'OK ' if risultati[-1] else 'ERRORE'}  Ereditarieta' PET-002: misura 'gambe' tolta, 'corpo' sostituita")

    print("\nTUTTO OK: il motore funziona." if all(risultati)
          else "\nATTENZIONE: qualche controllo non e' passato.")
    return all(risultati)


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
