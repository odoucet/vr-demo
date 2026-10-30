"""Schémas de l'article : sources HTML/SVG versionnées (pipeline/article/schemas/), rendues en PNG.

La taille du rendu vient du viewBox du SVG, ou de l'attribut data-taille="LxH" pour une page en HTML seul.

    python pipeline/article/schemas.py              # tous les schémas
    python pipeline/article/schemas.py atelier      # un seul

Rendu par le navigateur de Windows en mode headless (pipeline/tools.yaml, navigateur), à deux fois la taille du
viewBox : builds/article/schemas/<nom>.png (maîtres hors dépôt ; versions web : pipeline/article/export_web.py).
Un profil jetable par schéma (builds/navigateur/<nom>/) : le navigateur
headless reste parfois bloqué ; il est alors arrêté (il garderait son profil verrouillé) et le rendu relancé une fois.
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
OUT = ROOT / "builds" / "article" / "schemas"
PROFILE = ROOT / "builds" / "navigateur"
SCALE = 2
TIMEOUT = 45


def stop(profile):
    """Arrête les processus du navigateur ouverts sur ce profil (côté Windows : le délai ne tue que le côté WSL)."""
    motif = re.escape(to_windows(profile))
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine "
                    f"-match '{motif}' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force "
                    "-ErrorAction SilentlyContinue }"], capture_output=True)


def render(html):
    source = html.read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', source) or re.search(r'data-taille="(\d+)x(\d+)"', source)
    if not m:
        sys.exit(f"{html.name} : taille introuvable (viewBox du SVG, ou data-taille=\"LxH\" sur la page)")
    w, h = m.groups()
    out = OUT / f"{html.stem}.png"
    url = "file:///" + to_windows(html).replace("\\", "/")
    profile = PROFILE / html.stem
    profile.mkdir(parents=True, exist_ok=True)
    for essai in (1, 2):
        try:
            subprocess.run([str(from_windows(CONFIG["navigateur"]["exe"])), "--headless=new", "--disable-gpu",
                            "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                            f"--user-data-dir={to_windows(profile)}",
                            f"--force-device-scale-factor={SCALE}", f"--window-size={w},{h}",
                            f"--screenshot={to_windows(out)}", url],
                           check=True, capture_output=True, text=True, timeout=TIMEOUT)
            break
        except subprocess.TimeoutExpired:
            stop(profile)
            if essai == 2:
                sys.exit(f"{html.name} : le navigateur n'a pas rendu en {TIMEOUT} s, deux fois")
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
