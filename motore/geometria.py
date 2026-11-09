"""Calcoli geometrici sui punti del corpo (coordinate in pixel, y verso il basso)."""
import math


def angolo(a, b, c):
    """Angolo in gradi nel punto b, formato dai segmenti b->a e b->c (0-180)."""
    bax, bay = a[0] - b[0], a[1] - b[1]
    bcx, bcy = c[0] - b[0], c[1] - b[1]
    den = math.hypot(bax, bay) * math.hypot(bcx, bcy)
    if den == 0:
        return None
    cos = (bax * bcx + bay * bcy) / den
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def inclinazione(basso, alto):
    """Inclinazione del segmento basso->alto rispetto alla verticale, in gradi.
    0 = perfettamente verticale, 90 = orizzontale."""
    dx = alto[0] - basso[0]
    dy = basso[1] - alto[1]  # positivo se 'alto' sta sopra
    return math.degrees(math.atan2(abs(dx), dy))


def distanza(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angolo_orientato(a, b, c):
    """Angolo in b con il verso: 180 = a, b, c in linea; meno di 180 = b SOTTO la retta a-c
    (es. bacino che cede nei piegamenti); piu' di 180 = b SOPRA la retta (es. sedere alto).
    Pensato per corpi orizzontali o inclinati: se la retta a-c e' verticale restituisce l'angolo senza verso."""
    th = angolo(a, b, c)
    if th is None:
        return None
    dx = c[0] - a[0]
    if abs(dx) < 1e-6:
        return th
    y_retta = a[1] + (c[1] - a[1]) * (b[0] - a[0]) / dx
    return th if b[1] >= y_retta else 360 - th
