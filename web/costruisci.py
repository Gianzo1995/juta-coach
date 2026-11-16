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


NASCOSTI = {"squat"}


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


FONTI = [("Barlow", 400, "barlow-latin-400-normal"), ("Barlow", 500, "barlow-latin-500-normal"),
         ("Barlow", 600, "barlow-latin-600-normal"), ("Barlow Condensed", 600, "barlow-condensed-latin-600-normal"),
         ("Barlow Condensed", 700, "barlow-condensed-latin-700-normal")]


def fonti_incorporate():
    """@font-face con i caratteri dentro la pagina: nessuna richiesta esterna per i font."""
    righe = []
    for famiglia, peso, file in FONTI:
        b64 = base64.b64encode((QUI / "fonti" / f"{file}.woff2").read_bytes()).decode()
        righe.append(f'@font-face{{font-family:"{famiglia}";font-weight:{peso};font-style:normal;font-display:swap;'
                     f'src:url(data:font/woff2;base64,{b64}) format("woff2")}}')
    return "\n".join(righe)


def copia_vendor(dest, con_modello):
    shutil.copy(VENDOR / "vision_bundle.mjs", dest)
    shutil.copytree(VENDOR / "wasm", dest / "wasm")
    if con_modello:
        shutil.copytree(VENDOR / "modello", dest / "modello")


AVATAR = QUI / "avatar"                       # avatar dimostrativo 3D ("Come si fa")
VENDOR_AVATAR = [VENDOR / "three" / "three.min.js", VENDOR / "three" / "OrbitControls.js",
                 VENDOR / "three" / "GLTFLoader.js", AVATAR / "manichino.js", AVATAR / "avatar.js"]


def leggi_avatar(ids):
    """Voci dell'avatar (esercizi/avatar.json): solo esercizi presenti nel catalogo e schemi conosciuti."""
    dati = json.loads((RADICE / "esercizi" / "avatar.json").read_text(encoding="utf-8"))
    schemi = {"accosciata", "piegamenti"}
    for a in dati["esercizi"]:
        if a["id"] not in ids:
            raise SystemExit(f"ERRORE in avatar.json: {a['id']} non è nel catalogo")
        if a["schema"] not in schemi:
            raise SystemExit(f"ERRORE in avatar.json: schema sconosciuto {a['schema']} ({a['id']})")
    return dati["esercizi"]


def copia_avatar(dest):
    cartella = dest / "avatar"
    cartella.mkdir()
    for f in VENDOR_AVATAR:
        shutil.copy(f, cartella)


def main():
    # lo squat di base resta solo come banco di prova del motore: sul telefono c'e' QUA-016, con le stesse regole
    voci = [v for v in leggi_catalogo() if v["id"] not in NASCOSTI]
    catalogo = "const CATALOGO_GREZZO = " + json.dumps(voci, ensure_ascii=False) + ";"
    avatar = leggi_avatar({v["id"] for v in voci})
    catalogo += "\nconst AVATAR_ESERCIZI = " + json.dumps(avatar, ensure_ascii=False) + ";"
    app = (QUI / "app.html").read_text(encoding="utf-8")
    motore = (QUI / "motore.js").read_text(encoding="utf-8")
    corpo = (app.replace("/*__CATALOGO__*/", catalogo).replace("/*__MOTORE__*/", motore)
             .replace("/*__FONTI__*/", fonti_incorporate()))

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
    copia_avatar(sito)
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
    copia_avatar(claude)

    print(f"ok: {len(voci)} esercizi ({len(avatar)} con avatar) -> {sito.relative_to(RADICE)}/ e {claude.relative_to(RADICE)}/")


if __name__ == "__main__":
    main()
