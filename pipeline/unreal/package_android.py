"""Empaquette le projet en APK Quest (Android arm64, textures ASTC), via RunUAT BuildCookRun.

    python pipeline/unreal/package_android.py                     # version de travail (Development) → builds/android_greybox/
    python pipeline/unreal/package_android.py --variant finale    # version finale (Shipping) → builds/android_finale/
    python pipeline/unreal/package_android.py --variant exp --cvars "r.Mobile.EarlyZPass=1"   # essai de réglage

Journal complet : builds/android/package.log. L'APK et son script d'installation sont archivés dans
builds/android/Android_ASTC/. L'éditeur peut rester ouvert (le cook lit les assets sauvegardés).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import ROOT, from_windows, project, to_windows, unreal, CONFIG  # noqa: E402
from unreal.setup_android import ENV as ANDROID_ENV  # noqa: E402

RUNUAT = from_windows(CONFIG["unreal"]["root"]) / "Engine/Build/BatchFiles/RunUAT.bat"
OUT_ROOT = ROOT / "builds"
# Variantes : carte de démarrage, nom de paquet et nom affiché distincts, pour installer plusieurs versions côte à côte.
# (nom, paquet, dossier[, variables console]) ; la configuration (Development / Shipping) vient de CONFIGS ou de --config.
VARIANTS = {
    # version de travail : console (mesures adb, quest_ab.py), journal, capture au bouton A (quest_captures.py)
    "greybox": ("/Game/Maps/Barque_Greybox.Barque_Greybox", "com.odoucet.barque.greybox", "android_greybox"),
    # version finale (23/10) : Shipping, sans console ni journal, plus légère ; même contenu
    "finale": ("/Game/Maps/Barque_Greybox.Barque_Greybox", "com.odoucet.barque", "android_finale"),
    # Démo « HD » demandée par Olivier (comparer beaucoup plus de polygones à ~25 i/s) : arbres fins gardés bien plus
    # loin, pas de culling des arbres, MSAA 4x. Même contenu que greybox, autres réglages.
    "hd": ("/Game/Maps/Barque_Greybox.Barque_Greybox", "com.odoucet.barque.hd", "android_hd",
           "foliage.LODDistanceScale=8;foliage.CullDistanceScale=20;r.MSAACount=4;r.StaticMeshLODDistanceScale=0.2"),
    # Essais de réglages de rendu en lecture seule (ex. r.Mobile.EarlyZPass), passés par --cvars : paquet distinct.
    "exp": ("/Game/Maps/Barque_Greybox.Barque_Greybox", "com.odoucet.barque.exp", "android_exp", ""),
}

CONFIGS = {"finale": "Shipping"}
APP_NAMES = {"finale": "La barque des lucioles", "greybox": "Barque (travail)"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None, choices=["Development", "Shipping"], help="défaut : celle de la variante")
    ap.add_argument("--variant", default="greybox", choices=list(VARIANTS))
    ap.add_argument("--cvars", default="", help='variables ajoutées à celles de la variante, "a=1;b=2"')
    args = ap.parse_args()
    args.config = args.config or CONFIGS.get(args.variant, "Development")
    default_map, package_name, out_name, *extra = VARIANTS[args.variant]
    extra = [";".join(x for x in (extra[0] if extra else "", args.cvars) if x)]
    OUT = OUT_ROOT / out_name
    OUT.mkdir(parents=True, exist_ok=True)
    # Écrit la configuration de la variante, empaquette, puis restaure la configuration par défaut (version de travail).
    env = dict(os.environ, BARQUE_DEFAULT_MAP=default_map, BARQUE_PACKAGE_NAME=package_name,
               BARQUE_APP_NAME=APP_NAMES.get(args.variant, f"Barque ({args.variant})"), BARQUE_EXTRA_CVARS=extra[0])
    subprocess.run([sys.executable, str(ROOT / "pipeline/unreal/create_project.py")], env=env, check=True)
    try:
        package(args, OUT)
    finally:
        subprocess.run([sys.executable, str(ROOT / "pipeline/unreal/create_project.py")], check=True)


def package(args, OUT):
    # Un .bat évite les problèmes d'échappement des guillemets entre Python, WSL et cmd.exe.
    bat = OUT / "package.bat"
    bat.write_text("@echo off\r\n" + "".join(f"set {k}={v}\r\n" for k, v in ANDROID_ENV.items()) +
                   f'call "{to_windows(RUNUAT)}" BuildCookRun -project="{to_windows(project())}" -noP4 -platform=Android '
                   f"-cookflavor=ASTC -clientconfig={args.config} -build -cook -stage -pak -package -archive "
                   f'-archivedirectory="{to_windows(OUT)}" -unattended -utf8output -nocompileeditor '
                   # Projet sans code : sans -unrealexe, le cook cherche un éditeur propre au projet (BarqueEditor.target)
                   f'-unrealexe="{to_windows(unreal("editor_cmd"))}"\r\n', encoding="utf-8")
    log = OUT / "package.log"
    with log.open("w", encoding="utf-8") as f:
        proc = subprocess.run(["cmd.exe", "/c", to_windows(bat)], cwd="/mnt/c", stdout=f,
                              stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
    print("\n".join(tail))
    apks = sorted(OUT.rglob("*.apk"))
    if proc.returncode != 0 or not apks:
        raise SystemExit(f"Empaquetage en échec (code {proc.returncode}). Journal : {log.relative_to(ROOT)}")
    for apk in apks:
        print(f"APK : {apk.relative_to(ROOT)} ({apk.stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    main()
