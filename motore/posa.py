"""Rilevamento della posa con MediaPipe Pose Landmarker.

Trasforma un'immagine della camera in un dizionario di punti del corpo:
    {"spalla_sx": (x, y, visibilita), ...}
con x, y in pixel e visibilita tra 0 e 1.
"""
from pathlib import Path
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Indici dei punti MediaPipe (sx/dx = sinistra/destra DELLA PERSONA)
PUNTI = {
    "naso": 0, "naso_sx": 0, "naso_dx": 0,   # il naso e' unico: _sx/_dx per le misure (naso-spalla-gomito)
    "spalla_sx": 11, "spalla_dx": 12,
    "gomito_sx": 13, "gomito_dx": 14,
    "polso_sx": 15, "polso_dx": 16,
    "anca_sx": 23, "anca_dx": 24,
    "ginocchio_sx": 25, "ginocchio_dx": 26,
    "caviglia_sx": 27, "caviglia_dx": 28,
    "tallone_sx": 29, "tallone_dx": 30,
    "punta_sx": 31, "punta_dx": 32,
    "punta_piede_sx": 31, "punta_piede_dx": 32,   # nome usato nel catalogo gambe
}

# Linee da disegnare per lo scheletro
COLLEGAMENTI = [
    ("spalla_sx", "spalla_dx"), ("anca_sx", "anca_dx"),
    ("spalla_sx", "anca_sx"), ("spalla_dx", "anca_dx"),
    ("spalla_sx", "gomito_sx"), ("gomito_sx", "polso_sx"),
    ("spalla_dx", "gomito_dx"), ("gomito_dx", "polso_dx"),
    ("anca_sx", "ginocchio_sx"), ("ginocchio_sx", "caviglia_sx"),
    ("anca_dx", "ginocchio_dx"), ("ginocchio_dx", "caviglia_dx"),
    ("caviglia_sx", "tallone_sx"), ("tallone_sx", "punta_sx"), ("caviglia_sx", "punta_sx"),
    ("caviglia_dx", "tallone_dx"), ("tallone_dx", "punta_dx"), ("caviglia_dx", "punta_dx"),
]

MODELLI = {
    "lite": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
    "full": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    "heavy": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
}


def scarica_modello(tipo="full", cartella="modelli"):
    """Scarica il modello la prima volta (circa 10 MB) e poi lo riusa."""
    cartella = Path(cartella)
    cartella.mkdir(exist_ok=True)
    percorso = cartella / f"pose_landmarker_{tipo}.task"
    if not percorso.exists():
        print(f"Scarico il modello '{tipo}' (solo la prima volta)...")
        urllib.request.urlretrieve(MODELLI[tipo], percorso)
        print("Modello scaricato.")
    return percorso


class RilevatorePosa:
    def __init__(self, tipo_modello="full"):
        percorso = scarica_modello(tipo_modello)
        opzioni = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(percorso)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(opzioni)
        self._ultimo_ts = -1

    def rileva(self, frame_bgr, timestamp_ms):
        """Restituisce il dizionario dei punti, oppure None se non c'e' nessuno."""
        # MediaPipe richiede tempi sempre crescenti
        timestamp_ms = max(int(timestamp_ms), self._ultimo_ts + 1)
        self._ultimo_ts = timestamp_ms

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        immagine = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        risultato = self._landmarker.detect_for_video(immagine, timestamp_ms)
        if not risultato.pose_landmarks:
            return None

        punti_mp = risultato.pose_landmarks[0]
        h, w = frame_bgr.shape[:2]
        posa = {}
        for nome, indice in PUNTI.items():
            p = punti_mp[indice]
            vis = getattr(p, "visibility", None)
            posa[nome] = (p.x * w, p.y * h, 1.0 if vis is None else float(vis))
        return posa

    def chiudi(self):
        self._landmarker.close()
