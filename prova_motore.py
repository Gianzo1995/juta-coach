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
def posa_alzata(braccio_dx, braccio_sx=15.0):
    """Alzata laterale vista di fronte: braccio = angolo anca-spalla-gomito, braccia tese."""
    posa = {n: (500, 180, 0.99) for n in ("naso", "naso_sx", "naso_dx")}   # come la posa reale (naso con lato)
    for lato, x, verso, a in (("dx", 420, -1, braccio_dx), ("sx", 580, 1, braccio_sx)):
        r = math.radians(a)
        g = (x + verso * 150 * math.sin(r), 300 + 150 * math.cos(r))
        po = (x + verso * 290 * math.sin(r), 300 + 290 * math.cos(r))
        for n, pt in (("spalla", (x, 300)), ("anca", (x, 560)), ("gomito", g), ("polso", po),
                      ("ginocchio", (x, 760)), ("caviglia", (x, 950))):
            posa[f"{n}_{lato}"] = (pt[0], pt[1], 0.95)
    return posa


def ruota(v, gradi):
    r = math.radians(gradi)
    return (v[0] * math.cos(r) - v[1] * math.sin(r), v[0] * math.sin(r) + v[1] * math.cos(r))


def posa_ponte(anca, ginocchio=90.0):
    """Ponte glutei visto di lato: anca = angolo spalla-anca-ginocchio, ginocchio = anca-ginocchio-caviglia."""
    a, k = (500, 700), (700, 600)
    u = ((k[0] - a[0]) / 223.6, (k[1] - a[1]) / 223.6)
    sp = ruota(u, anca)
    sp = (a[0] + 250 * sp[0], a[1] + 250 * sp[1])
    c = ruota((-u[0], -u[1]), -ginocchio)
    c = (k[0] + 200 * c[0], k[1] + 200 * c[1])
    return punti_entrambi_lati({"spalla": sp, "anca": a, "ginocchio": k, "caviglia": c,
                                "gomito": (sp[0] + 60, sp[1]), "polso": (sp[0] + 120, sp[1])}, vis_sx=0.95, vis_dx=0.4)


def posa_polpaccio(caviglia, ginocchio=178.0):
    """Calf raise visto di lato: caviglia = angolo ginocchio-caviglia-punta del piede (90 circa = piede a terra)."""
    cv, k = (500, 900), (500, 700)
    an = (500 - 250 * math.sin(math.radians(180 - ginocchio)), 450)
    d = ruota((0, -1), caviglia)
    pt = (cv[0] + 70 * d[0], cv[1] + 70 * d[1])
    return punti_entrambi_lati({"spalla": (an[0], 200), "anca": an, "ginocchio": k, "caviglia": cv,
                                "tallone": (cv[0] - 20, cv[1] + 15), "punta": pt, "punta_piede": pt},
                               vis_sx=0.95, vis_dx=0.4)


def posa_seduto_fronte(ginocchia):
    """Seduto alla adductor/abductor machine visto di fronte: ginocchia = distanza tra le ginocchia
    in percentuale della larghezza delle anche (anche larghe 100 px)."""
    posa = {n: (500, 200, 0.99) for n in ("naso", "naso_sx", "naso_dx")}
    for lato, verso in (("dx", -1), ("sx", 1)):
        x = 500 + verso * 50
        for n, pt in (("spalla", (500 + verso * 80, 300)), ("gomito", (500 + verso * 110, 400)), ("polso", (500 + verso * 120, 480)),
                      ("anca", (x, 500)), ("ginocchio", (500 + verso * ginocchia / 2, 560)),
                      ("caviglia", (500 + verso * ginocchia / 2, 720))):
            posa[f"{n}_{lato}"] = (pt[0], pt[1], 0.95)
    return posa


def posa_front_lever(corpo, abbassa_bacino=0.0):
    """Front lever visto di lato: corpo = inclinazione spalla-caviglia (90 = orizzontale, 180 = appesi)."""
    sp, L = (400, 300), 300
    d = (math.sin(math.radians(corpo)), -math.cos(math.radians(corpo)))
    an = (sp[0] + 0.5 * L * d[0], sp[1] + 0.5 * L * d[1] + abbassa_bacino)
    cv = (sp[0] + L * d[0], sp[1] + L * d[1])
    return punti_entrambi_lati({"spalla": sp, "gomito": (sp[0] - 5, sp[1] - 120), "polso": (sp[0] - 10, sp[1] - 240),
                                "anca": an, "ginocchio": (sp[0] + 0.75 * L * d[0], sp[1] + 0.75 * L * d[1] + abbassa_bacino / 2),
                                "caviglia": cv, "tallone": cv, "punta": (cv[0] + 15, cv[1])}, vis_sx=0.95, vis_dx=0.4)


def tenuta(fn_posa, fuori, dentro, secondi, entrata=1.0, **extra):
    """Tenuta isometrica: da 'fuori' a 'dentro' in 'entrata' s, ferma 'secondi' s, poi ritorno e 2 s fuori."""
    frames = [fn_posa(fuori + (dentro - fuori) * i / (entrata * FPS)) for i in range(int(entrata * FPS))]
    frames += [fn_posa(dentro, **extra)] * int(secondi * FPS)
    frames += [fn_posa(dentro + (fuori - dentro) * i / FPS) for i in range(FPS)]
    return frames + [fn_posa(fuori)] * (2 * FPS)


def posa_fronte_gambe(gamba_dx, gamba_sx=90.0):
    """In piedi visto di fronte: gamba = angolo tra la linea delle anche e la gamba (90 = sotto l'anca,
    piu' di 90 = aperta verso l'esterno, meno di 90 = oltre il centro)."""
    posa = {n: (500, 150, 0.99) for n in ("naso", "naso_sx", "naso_dx")}
    for lato, x, verso, g in (("dx", 450, -1, gamba_dx), ("sx", 550, 1, gamba_sx)):
        a = math.radians(g - 90)
        d = (verso * math.sin(a), math.cos(a))
        for n, pt in (("spalla", (500 + verso * 80, 250)), ("gomito", (500 + verso * 100, 360)), ("polso", (500 + verso * 105, 460)),
                      ("anca", (x, 500)), ("ginocchio", (x + 200 * d[0], 500 + 200 * d[1])),
                      ("caviglia", (x + 400 * d[0], 500 + 400 * d[1]))):
            posa[f"{n}_{lato}"] = (pt[0], pt[1], 0.95)
    return posa


def posa_kickback(anca, verso=1):
    """Kickback in piedi visto di lato, busto inclinato in avanti. anca = angolo dal davanti
    (meno di 180 = gamba avanti, piu' di 180 = gamba oltre la linea del busto). verso: +1 guarda a destra."""
    an = (500, 500)
    u = (math.sin(math.radians(30)) * verso, -math.cos(math.radians(30)))       # verso la spalla
    sp = (an[0] + 250 * u[0], an[1] + 250 * u[1])
    phi = -math.radians(180 - anca) * verso
    d = (-u[0] * math.cos(phi) + u[1] * math.sin(phi), -u[0] * math.sin(phi) - u[1] * math.cos(phi))
    g = (an[0] + 220 * d[0], an[1] + 220 * d[1])
    c = (an[0] + 420 * d[0], an[1] + 420 * d[1])
    posa = punti_entrambi_lati({"spalla": sp, "anca": an, "ginocchio": g, "caviglia": c,
                                "gomito": (sp[0] + 60 * verso, sp[1] + 80), "polso": (sp[0] + 120 * verso, sp[1] + 120),
                                "tallone": c, "punta": c}, vis_sx=0.4, vis_dx=0.95)
    for n in ("naso", "naso_sx", "naso_dx"):
        posa[n] = (sp[0] + 50 * verso, sp[1] - 30, 0.99)
    return posa


def posa_braccio(gomito):
    """Curl visto di lato, braccio destro verso la camera: gomito = angolo spalla-gomito-polso."""
    sp, gm = (500, 300), (500, 450)
    d = ruota((0, 1), -(180 - gomito))
    pl = (gm[0] + 140 * d[0], gm[1] + 140 * d[1])
    posa = punti_entrambi_lati({"spalla": sp, "gomito": gm, "polso": pl, "anca": (500, 560), "ginocchio": (505, 760),
                                "caviglia": (500, 950), "tallone": (480, 960), "punta": (560, 965)}, vis_sx=0.4, vis_dx=0.95)
    for n in ("naso", "naso_sx", "naso_dx"):
        posa[n] = (530, 230, 0.99)
    return posa


def posa_appeso(braccio, oscilla=0.0, gomito_lato="sx"):
    """Appeso alla sbarra visto di lato: braccio = angolo anca-spalla-gomito (20 = braccia lungo i fianchi,
    170 = sopra la testa); oscilla = gradi del corpo rispetto alla verticale."""
    sp = (500, 300)
    t = math.radians(oscilla)
    giu = (math.sin(t), math.cos(t))
    an = (sp[0] + 250 * giu[0], sp[1] + 250 * giu[1])
    cv = (sp[0] + 550 * giu[0], sp[1] + 550 * giu[1])
    b = ruota(giu, -braccio)
    gm = (sp[0] + 130 * b[0], sp[1] + 130 * b[1])
    pl = (sp[0] + 260 * b[0], sp[1] + 260 * b[1])
    posa = punti_entrambi_lati({"spalla": sp, "gomito": gm, "polso": pl, "anca": an,
                                "ginocchio": ((an[0] + cv[0]) / 2, (an[1] + cv[1]) / 2), "caviglia": cv, "tallone": cv, "punta": cv},
                               vis_sx=0.95 if gomito_lato == "sx" else 0.4, vis_dx=0.95 if gomito_lato == "dx" else 0.4)
    for n in ("naso", "naso_sx", "naso_dx"):
        posa[n] = (sp[0] + 30, sp[1] - 60, 0.99)
    return posa


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


def posa_pullover(spalla, gomito=160.0, sollevamento=0.0):
    """Pullover visto di lato, sdraiati lungo la panca: testa a sinistra.
    spalla = angolo anca-spalla-gomito (90 = braccia verticali, 180 = in linea con il busto)."""
    sp, L = (500, 450), 120
    t = math.radians(spalla)
    d = (math.cos(t), -math.sin(t))                          # direzione del braccio
    g = (sp[0] + L * d[0], sp[1] + L * d[1])
    k = math.radians(180 - gomito)                            # piega del gomito
    d2 = (d[0] * math.cos(k) - d[1] * math.sin(k), d[0] * math.sin(k) + d[1] * math.cos(k))
    po = (g[0] + 110 * d2[0], g[1] + 110 * d2[1])
    an = (sp[0] + 230, sp[1] - sollevamento * 230)
    posa = {"naso": (sp[0] - 60, sp[1] - 15, 0.99)}
    for nome, (x, y) in {"spalla": sp, "gomito": g, "polso": po, "anca": an}.items():
        posa[f"{nome}_sx"] = (x, y, 0.95)
        posa[f"{nome}_dx"] = (x + 5, y - 4, 0.4)
    return posa


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

    # PULLOVER (PET-025): movimento "al contrario" (l'angolo aumenta): buona, poco ampia, gomiti piegati, troppo veloce
    pv = lambda a, **kw: posa_pullover(a, **kw)
    frames = [pv(95)] * FPS + ripetizione_fasi(pv, 95, 170, 3, 1, 2) + ripetizione_fasi(pv, 95, 135, 3, 1, 2)
    frames += ripetizione_fasi(lambda a, gomito=0: posa_pullover(a, gomito=160 - gomito), 95, 170, 3, 1, 2, gomito=40)
    frames += ripetizione_fasi(pv, 95, 170, 1, 0, 1)
    ev = esegui(Analizzatore(es["PET-025"]), frames)
    risultati.append(verifica("Pullover PET-025", ev, [[], ["ampiezza"], ["gomiti_piegati"], ["troppo_veloce"]]))
    risultati.append(verifica_anticipo("Pullover PET-025", ev))

    # REGOLE DI INIZIO/FINE RIPETIZIONE (note, punto 4) sui piegamenti PET-001
    pp = lambda g, **kw: posa_piegamento(g, **kw)
    def scendi_sali(da, a_, sec):          # movimento lineare tra due angoli del gomito
        n = int(sec * FPS)
        return [pp(da + (a_ - da) * i / n) for i in range(n)]
    def eventi_di(frames):
        return esegui(Analizzatore(es["PET-001"]), frames)
    # 1) senza sosta iniziale (0,2 s) la prima discesa non conta; dopo 1 s di sosta si'
    ev = eventi_di([pp(175)] * 6 + ripetizione(pp, 175, 80, secondi=3.0) + [pp(175)] * FPS + ripetizione(pp, 175, 80, secondi=3.0))
    n = sum(e["tipo"] == "ripetizione" for e in ev)
    ok1 = n == 1
    print(f"{'OK ' if ok1 else 'ERRORE'}  Sosta di partenza: senza sosta la prima discesa non conta ({n} ripetizione contata su 2)")
    # 2) ripetizione non chiusa: sale solo fino a 150 e riscende -> scartata, poi una buona
    fr = [pp(175)] * FPS + scendi_sali(175, 80, 1.5) + scendi_sali(80, 150, 1.0) + scendi_sali(150, 80, 1.0) + scendi_sali(80, 175, 1.0)
    fr += [pp(175)] * FPS + ripetizione(pp, 175, 80, secondi=3.0)
    ev = eventi_di(fr)
    ann = [e for e in ev if e["tipo"] == "annullata"]; n = sum(e["tipo"] == "ripetizione" for e in ev)
    ok2 = len(ann) == 1 and ann[0]["motivo"] == "non_chiusa" and n == 1
    print(f"{'OK ' if ok2 else 'ERRORE'}  Ripetizione non chiusa: scartata ({[a['motivo'] for a in ann]}), contate {n}")
    # 3) finestra troppo lunga (fermo in basso 20 s, oltre 3 volte il tempo 2-1-1-0) -> scartata
    ev = eventi_di([pp(175)] * FPS + scendi_sali(175, 80, 1.5) + [pp(80)] * (20 * FPS) + scendi_sali(80, 175, 1.0))
    ann = [e for e in ev if e["tipo"] == "annullata"]; n = sum(e["tipo"] == "ripetizione" for e in ev)
    ok3 = len(ann) == 1 and ann[0]["motivo"] == "troppo_lunga" and n == 0
    print(f"{'OK ' if ok3 else 'ERRORE'}  Finestra troppo lunga (limite {es['PET-001']['ripetizione']['durata_massima']} s): scartata, contate {n}")
    risultati += [ok1, ok2, ok3]

    # IMPOSTAZIONI prima della serie: lato scelto (PET-006) e tavolette (PET-020)
    from motore.regole import applica_impostazioni
    c6 = applica_impostazioni(es["PET-006"], {"lato": "sx"})
    c20 = applica_impostazioni(es["PET-020"], {"errori.profondita": {"messaggio": "x", "misura": "gomito", "statistica": "minimo", "maggiore_di": 125}})
    c25 = applica_impostazioni(es["PET-025"], {"errori.schiena_inarcata": None})
    ok = (c6["lato"] == "sx" and es["PET-006"]["lato"] == "auto" and any(e["id"] == "profondita" and e["momento"] == "fine" for e in c20["errori"])
          and not any(e["id"] == "schiena_inarcata" for e in c25["errori"]) and any(e["id"] == "schiena_inarcata" for e in es["PET-025"]["errori"]))
    print(f"{'OK ' if ok else 'ERRORE'}  Impostazioni: lato scelto, soglia per numero di tavolette, controllo disattivato")
    risultati.append(ok)

    # LAT MACHINE (DOR-020, vista frontale): buona, ampiezza ridotta, risalita troppo veloce
    lat = lambda a: posa_alzata(a, a)
    frames = [lat(160.3)] * FPS
    frames += ripetizione_fasi(lat, 160.3, 35.2, 1, 0.5, 2)
    frames += ripetizione_fasi(lat, 160.3, 70.4, 1, 0.5, 2)
    frames += ripetizione_fasi(lat, 160.3, 35.2, 1, 0.5, 0.6)
    ev = esegui(Analizzatore(es["DOR-020"]), frames)
    risultati.append(verifica("Lat machine DOR-020", ev, [[], ["ampiezza"], ["troppo_veloce"]]))
    risultati.append(verifica_anticipo("Lat machine DOR-020", ev))

    # PIEGAMENTI (PET-001, ereditato dal catalogo): buono, poco profondo, bacino che cede, troppo veloce
    pp = lambda g, **kw: posa_piegamento(g, **kw)
    frames = [pp(175)] * FPS
    frames += ripetizione(pp, 175, 80, secondi=3.0)
    frames += ripetizione(pp, 175, 115, secondi=3.0)
    frames += ripetizione(pp, 175, 80, secondi=3.0, abbassa_bacino=70)
    frames += ripetizione(pp, 175, 80, secondi=3.0, abbassa_bacino=-70)
    frames += ripetizione(pp, 175, 80, secondi=1.0)
    ev = esegui(Analizzatore(es["PET-001"]), frames)
    risultati.append(verifica("Piegamenti PET-001", ev, [[], ["profondita"], ["bacino_cede"], ["sedere_alto"], ["troppo_veloce"]]))
    # PET-002 (sulle ginocchia) eredita da PET-001 ma non ha piu' la misura "gambe"
    # PET-002 (sulle ginocchia) eredita da PET-001: 'corpo' sostituita, 'gomito' ereditata;
    # la misura 'gambe' ereditata ma non usata non deve rendere obbligatorie le caviglie
    a2 = Analizzatore(es["PET-002"])
    ok = (es["PET-002"]["misure"]["corpo"]["punti"][2] == "ginocchio" and "gomito" in es["PET-002"]["misure"]
          and not any(n.startswith("caviglia") for n in a2._punti_necessari("sx")))
    risultati.append(ok)
    print(f"{'OK ' if ok else 'ERRORE'}  Ereditarieta' PET-002: 'corpo' sostituita, caviglie non richieste")

    # DEL-007 (alzata a un braccio, vista frontale): con la scelta del braccio conta solo quello che lavora
    from motore.regole import applica_impostazioni
    fr = ([posa_alzata(15.3)] * FPS + ripetizione(posa_alzata, 15.3, 88.7, secondi=3.0)
          + ripetizione(posa_alzata, 15.3, 55.2, secondi=3.0))
    risultati.append(verifica("Alzata a un braccio DEL-007 (destro)",
                              esegui(Analizzatore(applica_impostazioni(es["DEL-007"], {"lato": "dx"})), fr), [[], ["ampiezza"]]))
    ev = esegui(Analizzatore(applica_impostazioni(es["DEL-007"], {"lato": "sx"})), fr)
    ok = not [e for e in ev if e["tipo"] == "ripetizione"]
    risultati.append(ok)
    print(f"{'OK ' if ok else 'ERRORE'}  DEL-007 con braccio sinistro scelto: il braccio fermo non conta ripetizioni")

    # Gambe: ponte glutei (fasi), calf raise (punto "punta_piede" = punta del piede)
    po = lambda a, **kw: posa_ponte(a, **kw)
    fr = ([po(140.3)] * FPS + ripetizione_fasi(po, 140.3, 175.2, 1, 2, 2) + ripetizione_fasi(po, 140.3, 160.4, 1, 1, 2)
          + ripetizione_fasi(po, 140.3, 175.2, 1, 1, 0.4)
          + ripetizione_fasi(lambda a: posa_ponte(a, 130.3), 140.3, 175.2, 1, 1, 2))
    risultati.append(verifica("Ponte glutei GLU-001", esegui(Analizzatore(es["GLU-001"]), fr),
                              [[], ["lockout"], ["troppo_veloce"], ["piedi_lontani"]]))
    pc = lambda a, **kw: posa_polpaccio(a, **kw)
    fr = ([pc(105.3)] * FPS + ripetizione_fasi(pc, 105.3, 135.2, 1, 1, 2) + ripetizione_fasi(pc, 105.3, 121.4, 1, 1, 2)
          + ripetizione_fasi(pc, 105.3, 135.2, 1, 1, 0.4))
    risultati.append(verifica("Calf raise POL-001", esegui(Analizzatore(es["POL-001"]), fr),
                              [[], ["ampiezza"], ["troppo_veloce"]]))

    # Distanza tra le ginocchia (adductor / abductor machine, vista frontale)
    sf = lambda d, **kw: posa_seduto_fronte(d)
    fr = ([sf(240.3)] * FPS + ripetizione_fasi(sf, 240.3, 80.2, 1, 1, 2) + ripetizione_fasi(sf, 240.3, 150.4, 1, 1, 2)
          + ripetizione_fasi(sf, 240.3, 80.2, 1, 1, 0.4))
    risultati.append(verifica("Adductor machine ADD-007", esegui(Analizzatore(es["ADD-007"]), fr),
                              [[], ["ampiezza"], ["troppo_veloce"]]))
    fr = ([sf(100.3)] * FPS + ripetizione_fasi(sf, 100.3, 260.2, 1, 1, 2) + ripetizione_fasi(sf, 100.3, 190.4, 1, 1, 2))
    risultati.append(verifica("Abductor machine ABD-006", esegui(Analizzatore(es["ABD-006"]), fr), [[], ["ampiezza"]]))

    # Modalita' isometrica: wall sit e front lever (tenute al posto delle ripetizioni)
    fr = [posa_squat(175)] * FPS + tenuta(posa_squat, 175, 95.3, 10, entrata=2) + tenuta(posa_squat, 175, 110.4, 5, entrata=2)
    ev = esegui(Analizzatore(es["QUA-006"]), fr)
    risultati.append(verifica("Wall sit QUA-006 (tenute)", ev, [[], ["cosce_alte"]]))
    durate = [e["durata_s"] for e in ev if e["tipo"] == "ripetizione"]
    ok = len(durate) == 2 and 10 <= durate[0] <= 11.5 and 5 <= durate[1] <= 6.5
    risultati.append(ok)
    print(f"{'OK ' if ok else 'ERRORE'}  Wall sit: durata delle tenute {durate} s (attese circa 10,5 e 5,5)")
    fl = lambda c, **kw: posa_front_lever(c, **kw)
    fr = ([fl(178.3)] * FPS + tenuta(fl, 178.3, 90.3, 6) + tenuta(fl, 178.3, 112.4, 4)
          + tenuta(fl, 178.3, 90.3, 4, abbassa_bacino=60))
    risultati.append(verifica("Front lever DOR-064 (tenute)", esegui(Analizzatore(es["DOR-064"]), fr),
                              [[], ["piedi_bassi"], ["bacino_cede"]]))

    # Vista frontale con la scelta della gamba: gamba misurata rispetto alla linea delle anche
    fg = lambda g, **kw: posa_fronte_gambe(g)
    fr = ([fg(92.3)] * FPS + ripetizione_fasi(fg, 92.3, 125.2, 1, 1, 2) + ripetizione_fasi(fg, 92.3, 110.4, 1, 1, 2))
    risultati.append(verifica("Abduzione al cavo ABD-005 (destra)", esegui(Analizzatore(es["ABD-005"]), fr), [[], ["ampiezza"]]))
    sx = es["ABD-005"]["impostazioni"][0]["opzioni"][1]["imposta"]
    ev = esegui(Analizzatore(applica_impostazioni(es["ABD-005"], sx)), fr)
    ok = not [e for e in ev if e["tipo"] == "ripetizione"]
    risultati.append(ok)
    print(f"{'OK ' if ok else 'ERRORE'}  ABD-005 con gamba sinistra scelta: la gamba ferma non conta ripetizioni")
    fr = ([fg(115.3)] * FPS + ripetizione_fasi(fg, 115.3, 75.2, 1, 1, 2) + ripetizione_fasi(fg, 115.3, 92.4, 1, 1, 2))
    risultati.append(verifica("Adduzione al cavo ADD-006 (destra)", esegui(Analizzatore(es["ADD-006"]), fr), [[], ["ampiezza"]]))

    # Modalita' balistica: salti continui, il primo conta anche senza 0,5 s fermi in partenza
    sq = lambda k, **kw: posa_squat(k)
    fr = ([sq(175)] * 6 + ripetizione_fasi(sq, 175, 110.3, 0.4, 0, 0.4) + ripetizione_fasi(sq, 175, 135.4, 0.4, 0, 0.4)
          + ripetizione_fasi(sq, 175, 110.3, 0.4, 0, 0.4))
    risultati.append(verifica("Squat jump QUA-002 (balistica)", esegui(Analizzatore(es["QUA-002"]), fr), [[], ["profondita"], []]))

    # Angolo con verso (oltre 180): kickback, persona che guarda a destra e a sinistra
    for verso, nome in ((1, "guarda a destra"), (-1, "guarda a sinistra")):
        kb = lambda a, **kw: posa_kickback(a, verso)
        fr = ([kb(160.3)] * FPS + ripetizione_fasi(kb, 160.3, 195.2, 1, 1, 2) + ripetizione_fasi(kb, 160.3, 182.4, 1, 1, 2)
              + ripetizione_fasi(kb, 160.3, 222.3, 1, 1, 2))
        risultati.append(verifica(f"Kickback al cavo GLU-023 ({nome})", esegui(Analizzatore(es["GLU-023"]), fr),
                                  [[], ["lockout"], ["schiena_inarcata"]]))

    # Braccia: appeso alla sbarra (tenuta) e curl di concentrazione con il braccio scelto
    ap = lambda b, **kw: posa_appeso(b, **kw)
    fr = ([ap(20.3)] * FPS + tenuta(ap, 20.3, 172.3, 8) + tenuta(ap, 20.3, 172.3, 4, oscilla=25))
    ev = esegui(Analizzatore(es["AVA-001"]), fr)
    risultati.append(verifica("Appeso alla sbarra AVA-001 (tenute)", ev, [[], ["dondolio"]]))
    cu = lambda g, **kw: posa_braccio(g)
    fr = [cu(165.3)] * FPS + ripetizione_fasi(cu, 165.3, 50.2, 1, 1, 2) + ripetizione_fasi(cu, 165.3, 80.4, 1, 1, 2)
    scelte = es["BIC-020"]["impostazioni"][0]["opzioni"]
    risultati.append(verifica("Curl di concentrazione BIC-020 (braccio destro scelto)",
                              esegui(Analizzatore(applica_impostazioni(es["BIC-020"], scelte[0]["imposta"])), fr), [[], ["ampiezza"]]))
    ev = esegui(Analizzatore(applica_impostazioni(es["BIC-020"], scelte[1]["imposta"])), fr)
    ok = not [e for e in ev if e["tipo"] == "ripetizione"]
    risultati.append(ok)
    print(f"{'OK ' if ok else 'ERRORE'}  BIC-020 con braccio sinistro scelto: il braccio lontano dalla camera non conta ripetizioni")

    # Ogni esercizio analizzabile deve girare senza bloccarsi su una posa completa (tutti i punti, naso con lato)
    from motore.regole import applica_impostazioni
    bloccati = []
    for i, cfg in es.items():
        for imp in cfg.get("impostazioni") or []:
            cfg = applica_impostazioni(cfg, imp["opzioni"][0]["imposta"])
        try:
            a = Analizzatore(cfg)
            for k, f in enumerate(ripetizione(posa_squat, 175, 90, secondi=1.0)):
                f = dict(f, naso=(500, 100, 0.99), naso_sx=(500, 100, 0.99), naso_dx=(500, 100, 0.99))
                f.update({f"punta_piede_{l}": f[f"punta_{l}"] for l in ("sx", "dx")})
                a.aggiorna(f, k / FPS)
        except Exception as e:  # noqa: BLE001
            bloccati.append(f"{i}: {type(e).__name__} {e}")
    risultati.append(not bloccati)
    print(f"{'OK ' if not bloccati else 'ERRORE'}  {len(es)} esercizi analizzabili girano senza bloccarsi"
          + "".join(f"\n         {b}" for b in bloccati))

    print("\nTUTTO OK: il motore funziona." if all(risultati)
          else "\nATTENZIONE: qualche controllo non e' passato.")
    return all(risultati)


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
