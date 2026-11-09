"""Costruisce l'app per telefono a partire da app.html + motore.js + catalogo JSON.

    python web/costruisci.py

Crea due cartelle (non vanno salvate nel repository, si rigenerano sempre):
  sito/          versione online (GitHub Pages / Netlify): live con fotocamera + revisione
  sito_claude/   versione da pubblicare come artifact in claude.ai: solo video + revisione

Per aggiungere esercizi: nuovo file JSON in esercizi/catalogo/, poi rilancia questo script.
"""
import base64
import json
import shutil
import sys
from pathlib import Path

QUI = Path(__file__).parent
RADICE = QUI.parent
VENDOR = QUI / "vendor"          # MediaPipe (motore di riconoscimento) e modello della posa


def leggi_catalogo():
    """Catalogo con le integrazioni dell'app (stessa funzione usata dal motore Python)."""
    sys.path.insert(0, str(RADICE))
    from motore.regole import leggi_catalogo as leggi
    try:
        return leggi(str(RADICE / "esercizi"))
    except ValueError as e:
        raise SystemExit(f"ERRORE nel catalogo: {e}")


def pulisci(cartella):
    if cartella.exists():
        shutil.rmtree(cartella)
    cartella.mkdir(parents=True)


def copia_vendor(dest, con_modello):
    shutil.copy(VENDOR / "vision_bundle.mjs", dest)
    shutil.copytree(VENDOR / "wasm", dest / "wasm")
    if con_modello:
        shutil.copytree(VENDOR / "modello", dest / "modello")


def main():
    voci = leggi_catalogo()
    catalogo = "const CATALOGO_GREZZO = " + json.dumps(voci, ensure_ascii=False) + ";"
    app = (QUI / "app.html").read_text(encoding="utf-8")
    motore = (QUI / "motore.js").read_text(encoding="utf-8")
    corpo = app.replace("/*__CATALOGO__*/", catalogo).replace("/*__MOTORE__*/", motore)

    # --- versione online ---
    sito = RADICE / "sito"
    pulisci(sito)
    web = ('<!doctype html>\n<html lang="it">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
           '<meta name="theme-color" content="#101418">\n<meta name="apple-mobile-web-app-capable" content="yes">\n'
           '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'
           + corpo.replace("<!--__AVVIO__-->", '<script>window.JUTA_DISTRIBUZIONE="web";</script>') + "</html>\n")
    (sito / "index.html").write_text(web, encoding="utf-8")
    copia_vendor(sito, con_modello=True)
    shutil.copy(VENDOR / "_headers", sito)      # usato da Netlify, ignorato da GitHub Pages
    (sito / ".nojekyll").write_text("")

    # --- versione artifact claude.ai (il modello va incorporato in un file .js) ---
    claude = RADICE / "sito_claude"
    pulisci(claude)
    artifact = corpo.replace("<!--__AVVIO__-->",
                             '<script>window.JUTA_DISTRIBUZIONE="artifact";</script>\n<script src="modello.js"></script>')
    (claude / "artifact.html").write_text(artifact, encoding="utf-8")
    b64 = base64.b64encode((VENDOR / "modello" / "pose_landmarker_full.task").read_bytes()).decode()
    (claude / "modello.js").write_text(f'window.MODELLO_POSA_B64="{b64}";\n')
    copia_vendor(claude, con_modello=False)

    print(f"ok: {len(voci)} esercizi -> {sito.relative_to(RADICE)}/ e {claude.relative_to(RADICE)}/")


if __name__ == "__main__":
    main()
