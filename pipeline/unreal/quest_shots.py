"""Captures réelles au casque (Quest branché) aux moments clés de la balade, assemblées en planche.

    python pipeline/unreal/quest_shots.py --iter 12           # → review/iter-012/casque/*.jpg + planche-casque.jpg
    python pipeline/unreal/quest_shots.py --iter 12 --times 30 112

Lance l'APK greybox, puis à chaque instant demande une capture à l'outil de capture du Quest (vue de l'œil,
telle qu'affichée au casque, sans les approximations du rendu PC). Le casque doit « voir » quelqu'un (objet
devant le capteur de présence, comme le 18/10) et suivre la pièce (sinon le système bloque l'application).
Le regard est celui du casque posé : il ne vise pas forcément droit devant.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from tools import CONFIG, from_windows, to_windows  # noqa: E402

ADB = str(from_windows(CONFIG["android"]["root"]) / "sdk" / "platform-tools" / "adb.exe")
PKG = "com.odoucet.barque.greybox"
SHOTS_DIR = "/sdcard/Oculus/Screenshots"
TIMES = [30, 62, 76, 100, 112, 140, 165, 181, 196, 214, 232]


def adb(*a):
    return subprocess.run([ADB, *a], capture_output=True, text=True)


def latest():
    out = adb("shell", "ls", "-t", SHOTS_DIR).stdout.split()
    return out[0].strip() if out else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iter", type=int, required=True)
    ap.add_argument("--times", type=float, nargs="+", default=TIMES)
    args = ap.parse_args()
    out_dir = ROOT / "review" / f"iter-{args.iter:03d}" / "casque"
    out_dir.mkdir(parents=True, exist_ok=True)
    if "Asleep" in adb("shell", "dumpsys", "power").stdout:     # réveil seulement si endormi (sinon ouvre le menu)
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "cmd", "media_session", "volume", "--stream", "3", "--set", "1")   # volume bas (Olivier, 18/10)
    adb("shell", "am", "broadcast", "-a", "com.oculus.vrpowermanager.prox_close")
    adb("shell", "am", "force-stop", PKG)
    adb("shell", "am", "start", "-n", f"{PKG}/com.epicgames.unreal.GameActivity")
    t0 = time.time()
    shots = []
    for t in sorted(args.times):
        while time.time() - t0 < t:
            time.sleep(0.2)
        before = latest()
        adb("shell", "am", "startservice", "-n", "com.oculus.metacam/.capture.CaptureService", "-a", "TAKE_SCREENSHOT")
        for _ in range(30):
            time.sleep(0.3)
            name = latest()
            if name and name != before and PKG in name:
                break
        else:
            print(f"  {t:g} s : pas de capture (application au premier plan ?)")
            continue
        dest = out_dir / f"{int(t):03d}s.jpg"
        time.sleep(0.5)
        adb("pull", f"{SHOTS_DIR}/{name}", to_windows(dest))
        shots.append((t, dest))
        print(f"  {t:g} s → {dest.relative_to(ROOT)}", flush=True)
    adb("shell", "am", "broadcast", "-a", "com.oculus.vrpowermanager.automation_disable")
    adb("shell", "am", "force-stop", PKG)
    # planche de toutes les captures du dossier (une reprise partielle remplace ses images sans perdre les autres)
    shots = sorted((int(q.stem.rstrip("s")), q) for q in out_dir.glob("*s.jpg"))
    w = 480
    cols = 3
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, w * rows), "#141414")
    for i, (t, p) in enumerate(shots):
        im = Image.open(p).convert("RGB").resize((w, w))
        ImageDraw.Draw(im).text((8, 8), f"{t:g} s (casque)", fill="yellow")
        sheet.paste(im, ((i % cols) * w, (i // cols) * w))
    planche = out_dir.parent / "planche-casque.jpg"
    sheet.save(planche, quality=88)
    print(planche.relative_to(ROOT))


if __name__ == "__main__":
    main()
