"""Empaquette le projet en APK Quest (Android arm64, textures ASTC), via RunUAT BuildCookRun.

    python pipeline/unreal/package_android.py                 # Development → builds/android/
    python pipeline/unreal/package_android.py --config Shipping

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
OUT = ROOT / "builds" / "android"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="Development", choices=["Development", "Shipping"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
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
