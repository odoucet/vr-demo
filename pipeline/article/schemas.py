"""Schémas de l'article : sources HTML/SVG versionnées (pipeline/article/schemas/), rendues en PNG.

    python pipeline/article/schemas.py              # tous les schémas
    python pipeline/article/schemas.py atelier      # un seul

Rendu par le navigateur de Windows en mode headless (pipeline/tools.yaml, navigateur), à deux fois la taille du
viewBox : article/schemas/<nom>.png. Le profil du navigateur est jetable (builds/navigateur/), pour ne pas
dépendre d'une fenêtre déjà ouverte.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from tools import CONFIG, from_windows, to_windows  # noqa: E402

SRC = Path(__file__).with_name("schemas")
OUT = ROOT / "article" / "schemas"
PROFILE = ROOT / "builds" / "navigateur"
SCALE = 2


def render(html):
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', html.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"{html.name} : viewBox introuvable")
    w, h = m.groups()
    out = OUT / f"{html.stem}.png"
    url = "file:///" + to_windows(html).replace("\\", "/")
    subprocess.run([str(from_windows(CONFIG["navigateur"]["exe"])), "--headless=new", "--disable-gpu",
                    "--hide-scrollbars", f"--user-data-dir={to_windows(PROFILE)}",
                    f"--force-device-scale-factor={SCALE}", f"--window-size={w},{h}",
                    f"--screenshot={to_windows(out)}", url],
                   check=True, capture_output=True, text=True)
    print(f"{out.relative_to(ROOT)} ({int(w) * SCALE}×{int(h) * SCALE})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("noms", nargs="*")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    for html in sorted(SRC.glob("*.html")):
        if not args.noms or html.stem in args.noms:
            render(html)


if __name__ == "__main__":
    main()
