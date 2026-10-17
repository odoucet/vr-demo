"""Reconstruction complète du projet, étape par étape, depuis les sources versionnées.

    python pipeline/build.py                 # toutes les étapes disponibles
    python pipeline/build.py layout cameras  # seulement certaines étapes
    python pipeline/build.py --list

Chaque étape est un script idempotent. Une étape dont l'outil n'est pas encore installé (Unreal, Blender)
est signalée et sautée, sans bloquer les suivantes qui n'en dépendent pas.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

# (nom, description, commande, outil requis ou None)
STAGES = [
    ("music", "analyse de structure de la musique", [PY, "pipeline/audio/structure.py"], None),
    ("layout", "tracé de la rivière et trajectoire", [PY, "pipeline/layout/river.py"], None),
    ("cameras", "caméras de revue", [PY, "pipeline/review/cameras.py"], None),
    # À venir : assets (image → 3D, ComfyUI), blender (nettoyage, LOD, FBX), unreal (projet, niveau,
    # séquence, import), review (shoot.py). Ajoutés au fur et à mesure qu'ils existent.
]

TOOLS = {
    "unreal": lambda: os.environ.get("UE_EDITOR_CMD") and Path(os.environ["UE_EDITOR_CMD"]).exists(),
    "blender": lambda: os.environ.get("BLENDER_EXE") and Path(os.environ["BLENDER_EXE"]).exists(),
    "comfyui": lambda: shutil.which("curl") and subprocess.run(
        ["curl", "-s", "-m", "3", "-o", os.devnull, "http://127.0.0.1:8188/system_stats"]).returncode == 0,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stages", nargs="*")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for name, desc, _, tool in STAGES:
            print(f"{name:10s} {desc}" + (f"  (requiert {tool})" if tool else ""))
        return
    selected = [s for s in STAGES if not args.stages or s[0] in args.stages]
    unknown = set(args.stages) - {s[0] for s in STAGES}
    if unknown:
        raise SystemExit(f"Étapes inconnues : {', '.join(sorted(unknown))}")
    for name, desc, cmd, tool in selected:
        if tool and not TOOLS[tool]():
            print(f"── {name} : sautée ({tool} indisponible)")
            continue
        print(f"── {name} : {desc}")
        subprocess.run(cmd, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
