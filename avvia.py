"""Prototipo Juta - analisi del movimento con webcam.

Avvio:   python avvia.py
         python avvia.py --esercizio panca
         python avvia.py --video prova.mp4      (analizza un video invece della webcam)

Tasti nella finestra:
  1 / 2 / 3   cambia esercizio (squat / panca / lat machine)
  R           azzera il conteggio
  D           mostra/nasconde i numeri tecnici (angoli)
  Q o ESC     esci
"""
import argparse
from datetime import datetime
import json
import sys
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import yaml

from motore.posa import COLLEGAMENTI, RilevatorePosa
from motore.regole import Analizzatore, carica_tutti

COLORI = {  # BGR per OpenCV, RGB per i testi
    "verde": (60, 180, 75), "giallo": (0, 200, 255), "rosso": (40, 40, 220), "grigio": (120, 120, 120),
}


# --------------------------------------------------------------------------
# Testi con accenti (OpenCV da solo non scrive "più")
# --------------------------------------------------------------------------
def carica_font(dimensione):
    for nome in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(nome, dimensione)
        except OSError:
            continue
    return ImageFont.load_default(size=dimensione)


FONT_ENORME, FONT_GRANDE, FONT_MEDIO, FONT_PICCOLO = carica_font(80), carica_font(48), carica_font(34), carica_font(20)


def scrivi(frame, testi):
    """testi: lista di (testo, (x, y), font, colore_bgr)"""
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)
    for testo, pos, font, bgr in testi:
        d.text(pos, testo, font=font, fill=(bgr[2], bgr[1], bgr[0]))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# --------------------------------------------------------------------------
# Disegno
# --------------------------------------------------------------------------
def disegna(frame, posa, stato, nome_esercizio, debug, fps):
    h, w = frame.shape[:2]
    colore = COLORI.get(stato.colore, COLORI["grigio"])

    if posa:
        usati = set(stato.punti_usati)
        for a, b in COLLEGAMENTI:
            pa, pb = posa[a], posa[b]
            if min(pa[2], pb[2]) < 0.5:
                continue
            evidenzia = a in usati and b in usati
            cv2.line(frame, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])),
                     colore if evidenzia else (200, 200, 200), 6 if evidenzia else 2, cv2.LINE_AA)
        for nome in usati:
            x, y, v = posa[nome]
            if v >= 0.5:
                cv2.circle(frame, (int(x), int(y)), 7, (255, 255, 255), -1, cv2.LINE_AA)

    # banda in alto con il messaggio
    cv2.rectangle(frame, (0, 0), (w, 90), colore, -1)
    # riquadro ripetizioni in basso a destra
    cv2.rectangle(frame, (w - 230, h - 150), (w, h), (30, 30, 30), -1)

    testi = [
        (stato.messaggio, (20, 18), FONT_GRANDE, (255, 255, 255)),
        ("Ripetizioni", (w - 210, h - 140), FONT_PICCOLO, (200, 200, 200)),
        (str(stato.ripetizioni), (w - 210, h - 115), FONT_ENORME, (255, 255, 255)),
        (nome_esercizio, (20, h - 50), FONT_MEDIO, (255, 255, 255)),
    ]
    if debug:
        righe = [f"{fps:4.1f} fps  lato: {stato.lato}  fase: {stato.fase}"]
        righe += [f"{k}: {v:.2f}" for k, v in stato.misure.items()]
        for i, r in enumerate(righe):
            testi.append((r, (20, 110 + i * 26), FONT_PICCOLO, (0, 255, 255)))
    return scrivi(frame, testi)


# --------------------------------------------------------------------------
# Registro eventi (in futuro: inviati alla dashboard). Nessuna immagine salvata.
# --------------------------------------------------------------------------
class Registro:
    def __init__(self, cfg):
        cartella = Path("dati")
        cartella.mkdir(exist_ok=True)
        self.file = cartella / f"eventi_{datetime.now():%Y-%m-%d}.jsonl"
        self.base = {"sede": cfg["sede"], "postazione": cfg["postazione"]}

    def scrivi(self, evento):
        riga = {"ora": datetime.now().isoformat(timespec="seconds"), **self.base, **evento}
        with open(self.file, "a", encoding="utf-8") as f:
            f.write(json.dumps(riga, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
def main():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    parser = argparse.ArgumentParser()
    parser.add_argument("--esercizio", default=cfg["esercizio_iniziale"])
    parser.add_argument("--video", help="file video da analizzare al posto della webcam")
    args = parser.parse_args()

    esercizi = carica_tutti("esercizi")
    tasti = {ord("1"): "squat", ord("2"): "PET-012", ord("3"): "lat_machine"}
    attuale = args.esercizio
    analizzatore = Analizzatore(esercizi[attuale])

    print("Avvio il rilevatore di posa...")
    rilevatore = RilevatorePosa(cfg.get("modello", "full"))

    if args.video:
        cap = cv2.VideoCapture(args.video)
        fps_video = cap.get(cv2.CAP_PROP_FPS) or 30
    else:
        # su Windows DirectShow apre le webcam piu' velocemente
        cap = cv2.VideoCapture(cfg["camera"], cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(cfg["camera"])
        if not cap.isOpened():
            cap = cv2.VideoCapture(cfg["camera"])
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["larghezza"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["altezza"])
    if not cap.isOpened():
        print("ERRORE: non riesco ad aprire la camera/il video. Prova camera: 1 in config.yaml")
        return

    registro = Registro(cfg)
    debug, n_frame, fps, t_prec = False, 0, 0.0, time.monotonic()
    finestra = "Juta - Analisi movimento"
    cv2.namedWindow(finestra, cv2.WINDOW_NORMAL)
    print("Pronto. Tasti: 1 squat, 2 panca, 3 lat machine, R azzera, D numeri, Q esci")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if cfg.get("specchia_immagine") and not args.video:
            frame = cv2.flip(frame, 1)

        # tempo: reale per la webcam, quello del video per i file
        t = n_frame / fps_video if args.video else time.monotonic()
        n_frame += 1

        posa = rilevatore.rileva(frame, t * 1000)
        stato = analizzatore.aggiorna(posa, t)
        for evento in stato.eventi:
            registro.scrivi(evento)
            if evento["tipo"] == "ripetizione":
                errori = ", ".join(evento["errori"]) or "nessun errore"
                print(f"Ripetizione {evento['numero']}: {errori}")

        ora = time.monotonic()
        fps = 0.9 * fps + 0.1 * (1 / max(ora - t_prec, 1e-6))
        t_prec = ora

        cv2.imshow(finestra, disegna(frame, posa, stato, esercizi[attuale]["nome"], debug, fps))
        tasto = cv2.waitKey(1) & 0xFF
        if tasto in (ord("q"), ord("Q"), 27):
            break
        if tasto in (ord("d"), ord("D")):
            debug = not debug
        if tasto in (ord("r"), ord("R")):
            analizzatore.reset()
        if tasto in tasti and tasti[tasto] in esercizi:
            attuale = tasti[tasto]
            analizzatore = Analizzatore(esercizi[attuale])
        if cv2.getWindowProperty(finestra, cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    rilevatore.chiudi()
    cv2.destroyAllWindows()
    print(f"Fine. Eventi salvati in {registro.file}")


if __name__ == "__main__":
    main()
