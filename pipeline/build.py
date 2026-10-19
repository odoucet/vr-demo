"""Reconstruction complète du projet, étape par étape, depuis les sources versionnées.

    python pipeline/build.py                 # toutes les étapes disponibles
    python pipeline/build.py layout cameras  # seulement certaines étapes
    python pipeline/build.py --list

Chaque étape est un script idempotent. Les étapes listées dans SKIP_IF_UNCHANGED ne sont relancées que si leurs
entrées ont changé (empreinte dans Unreal/Saved/stamps/) ou si leurs sorties manquent : elles recréent leurs
assets de zéro, et les relancer sans raison réécrirait des binaires dans git. --force les relance.
Une étape dont l'outil n'est pas encore installé (Unreal, Blender) est signalée et sautée, sans bloquer les
suivantes qui n'en dépendent pas.
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
    ("palettes", "bible de style : palette par beat", [PY, "pipeline/style/palettes.py"], None),
    ("ambiance", "brume par beat (temps réel et offline)", [PY, "pipeline/style/ambiance.py"], None),
    ("unreal-project", "projet Unreal et configuration", [PY, "pipeline/unreal/create_project.py"], None),
    ("unreal-probe", "vérification du projet", [PY, "pipeline/unreal/run.py", "pipeline/unreal/scripts/probe.py"], "unreal"),
    ("music-wav", "musique en WAV pour Unreal", [PY, "pipeline/audio/prepare_music.py"], None),
    ("sounds", "sons retenus normalisés + plan de mixage pour Unreal", [PY, "pipeline/audio/prepare_sounds.py"], None),
    ("stems", "stems de la musique → sources spatialisées (si déposés)", [PY, "pipeline/audio/prepare_stems.py"], None),
    ("brush", "texture de touches de pinceau (look peint)", [PY, "pipeline/style/brush_texture.py"], None),
    ("greybox-geometry", "géométrie du greybox (terrain peint, arche, roseaux)", [PY, "pipeline/layout/greybox_geometry.py"], None),
    ("vegetation", "végétation et décor peints (forêt, berges, grands arbres, collines)", [PY, "pipeline/layout/vegetation.py"], None),
    ("sprites-layout", "placement des sprites peints (forêt, berges, lisières, houppiers, eau)", [PY, "pipeline/layout/sprites_layout.py"], None),
    ("creatures", "trajectoires des créatures (chenal, gué, vol)", [PY, "pipeline/layout/creatures.py"], None),
    ("water-map", "carte de l'eau (courant, distance aux berges)", [PY, "pipeline/layout/water_map.py"], None),
    ("unreal-greybox", "niveau greybox", [PY, "pipeline/unreal/run.py", "pipeline/unreal/scripts/greybox.py"], "unreal"),
    ("unreal-animatic", "séquence de l'animatic", [PY, "pipeline/unreal/run.py", "pipeline/unreal/scripts/animatic.py"], "unreal"),
    ("unreal-j1", "scène de test J1 (sphère 360 stéréo)", [PY, "pipeline/unreal/run.py", "pipeline/unreal/scripts/j1_spike.py"], "unreal"),
    ("unreal-j1b", "scène de test J1b (calque stéréo équirectangulaire)", [PY, "pipeline/unreal/run.py", "pipeline/unreal/scripts/j1b_stereolayer.py"], "unreal"),
    # Non lancées par défaut (longues ou dépendantes d'Olivier) : review/shoot.py (éditeur ouvert),
    # review/animatic.py (rendu MRQ), comfy/image_to_3d.py (GPU), comfy/sprites.py (GPU : images peintes, atlas versionnés),
    # unreal/package_android.py (APK).
]

# Étapes qui recréent tous leurs assets : relancées seulement si une entrée change ou si une sortie manque.
SKIP_IF_UNCHANGED = {
    "unreal-j1": (["pipeline/unreal/scripts/j1_spike.py", "Unreal/Content/Movies/test360_j1.mp4"],
                  ["Unreal/Content/Maps/J1_Spike.umap", "Unreal/Content/Spike/LS_J1.uasset"]),
    "unreal-j1b": (["pipeline/unreal/scripts/j1b_stereolayer.py", "pipeline/unreal/scripts/j1_spike.py",
                    "Unreal/Content/Movies/test360_j1.mp4"],
                   ["Unreal/Content/Maps/J1b_StereoLayer.umap", "Unreal/Content/Spike/LS_J1b.uasset"]),
}
STAMPS = ROOT / "Unreal" / "Saved" / "stamps"


def _inputs_digest(name):
    import hashlib
    h = hashlib.sha1()
    for rel in SKIP_IF_UNCHANGED[name][0]:
        h.update(rel.encode())
        h.update((ROOT / rel).read_bytes())
    return h.hexdigest()


def _unchanged(name):
    if name not in SKIP_IF_UNCHANGED:
        return False
    stamp = STAMPS / f"{name}.sha1"
    outputs_ok = all((ROOT / rel).exists() for rel in SKIP_IF_UNCHANGED[name][1])
    return outputs_ok and stamp.exists() and stamp.read_text().strip() == _inputs_digest(name)


def _tool_exists(name):
    sys.path.insert(0, str(ROOT / "pipeline"))
    import tools
    if name == "unreal":
        return tools.unreal("editor_cmd").exists()
    return False


def _comfy_url():
    sys.path.insert(0, str(ROOT / "pipeline"))
    import tools
    return tools.CONFIG["comfyui"]["url"]


TOOLS = {
    "unreal": lambda: _tool_exists("unreal"),
    "blender": lambda: os.environ.get("BLENDER_EXE") and Path(os.environ["BLENDER_EXE"]).exists(),
    "comfyui": lambda: shutil.which("curl") and subprocess.run(
        ["curl", "-s", "-m", "3", "-o", os.devnull, _comfy_url() + "/system_stats"]).returncode == 0,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stages", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--force", action="store_true", help="relancer aussi les étapes dont les entrées n'ont pas changé")
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
        if not args.force and _unchanged(name):
            print(f"── {name} : à jour (entrées inchangées)")
            continue
        print(f"── {name} : {desc}")
        subprocess.run(cmd, cwd=ROOT, check=True)
        if name in SKIP_IF_UNCHANGED:
            STAMPS.mkdir(parents=True, exist_ok=True)
            (STAMPS / f"{name}.sha1").write_text(_inputs_digest(name) + "\n")


if __name__ == "__main__":
    main()
