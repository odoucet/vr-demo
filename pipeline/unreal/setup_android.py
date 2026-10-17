"""Outils Android pour l'empaquetage Quest (SDK, NDK, cmake, build-tools, JDK 21), sans Android Studio.

    python pipeline/unreal/setup_android.py            # installe ce qui manque, puis vérifie
    python pipeline/unreal/setup_android.py --check    # vérifie seulement

Versions lues dans pipeline/tools.yaml (celles exigées par UE 5.8, Engine/Config/Android/Android_SDK.json).
Installation dans android.root (G:\\android) : sdk\\ (cmdline-tools, paquets) et jdk-21\\. Le JDK 25 du poste
est trop récent pour Gradle 8.13 utilisé par UE. Variables d'environnement utilisateur Windows positionnées :
ANDROID_HOME, ANDROID_SDK_ROOT, NDKROOT, NDK_ROOT, JAVA_HOME (comme Engine/Extras/Android/SetupAndroid.bat).
Idempotent : ne télécharge que ce qui manque. Installation autorisée par Olivier (SUIVI.md, D10).
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import CONFIG, from_windows  # noqa: E402

A = CONFIG["android"]
ROOT_WIN = A["root"].replace("/", "\\")
SDK_WIN, JDK_WIN = ROOT_WIN + "\\sdk", ROOT_WIN + "\\jdk-21"
SDK, JDK = from_windows(SDK_WIN), from_windows(JDK_WIN)
CMDLINE_URL = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
CMDLINE_LOCAL = Path("/mnt/e/renpy/renpy-8.3.4-sdk/rapt/commandlinetools-win-11076708_latest.zip")  # copie déjà présente
JDK_URL = "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk"
PACKAGES = ["platform-tools", f"platforms;{A['platforms']}", f"build-tools;{A['build_tools']}",
            f"cmake;{A['cmake']}", f"ndk;{A['ndk']}"]
ENV = {"ANDROID_HOME": SDK_WIN, "ANDROID_SDK_ROOT": SDK_WIN, "NDKROOT": f"{SDK_WIN}\\ndk\\{A['ndk']}",
       "NDK_ROOT": f"{SDK_WIN}\\ndk\\{A['ndk']}", "JAVA_HOME": JDK_WIN}


def unzip_single_dir(archive, dest):
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(archive).extractall(tmp)
        (inner,) = list(Path(tmp).iterdir())
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(inner), dest)


def download(url, dest):
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            shutil.copyfileobj(r.raw, f)


def install():
    tools = SDK / "cmdline-tools" / "latest"
    if not (tools / "bin" / "sdkmanager.bat").exists():
        src = CMDLINE_LOCAL if CMDLINE_LOCAL.exists() else None
        if src is None:
            src = Path(tempfile.mkdtemp()) / "cmdline.zip"
            download(CMDLINE_URL, src)
        unzip_single_dir(src, tools)
    if not (JDK / "bin" / "java.exe").exists():
        tmp = Path(tempfile.mkdtemp()) / "jdk21.zip"
        download(JDK_URL, tmp)
        unzip_single_dir(tmp, JDK)
    missing = [p for p in PACKAGES if not (SDK / p.replace(";", "/")).exists()]
    if missing:
        # Licences : acceptation scriptée (installation autorisée par Olivier).
        cmd = (f'set JAVA_HOME={JDK_WIN}&& (for /l %i in (1,1,30) do @echo y) | '
               f'{SDK_WIN}\\cmdline-tools\\latest\\bin\\sdkmanager.bat --sdk_root={SDK_WIN} --licenses >nul && '
               f'{SDK_WIN}\\cmdline-tools\\latest\\bin\\sdkmanager.bat --sdk_root={SDK_WIN} --install ' + " ".join(missing))
        subprocess.run(["cmd.exe", "/c", cmd], cwd="/mnt/c", check=True)
    for name, value in ENV.items():
        subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                        f"[Environment]::SetEnvironmentVariable('{name}', '{value}', 'User')"], check=True)


def check():
    ok = True
    for p in PACKAGES:
        present = (SDK / p.replace(";", "/")).exists()
        ok &= present
        print(f"  {'ok ' if present else 'MANQUE'} {p}")
    java = subprocess.run([str(JDK / "bin" / "java.exe"), "-version"], capture_output=True, text=True)
    print(f"  {'ok ' if java.returncode == 0 else 'MANQUE'} JDK : {(java.stderr or '').splitlines()[0] if java.stderr else '-'}")
    ok &= java.returncode == 0
    for name, value in ENV.items():
        cur = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                              f"[Environment]::GetEnvironmentVariable('{name}', 'User')"], capture_output=True, text=True).stdout.strip()
        ok &= cur == value
        print(f"  {'ok ' if cur == value else 'ÉCART'} {name}={cur}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not args.check:
        install()
    sys.exit(0 if check() else 1)
