"""Captures prises par Olivier au casque avec le bouton A (BP_Recentrage, greybox.py) : récupérées et datées.

    python pipeline/unreal/quest_captures.py            # → review/casque-A/<date>/A-<instant>s.jpg, puis vidées du casque
    python pipeline/unreal/quest_captures.py --garder   # sans les effacer du casque

Chaque appui sur A enregistre l'image de l'œil gauche (commande « shot », 1680 × 1760) dans le dossier de l'appli et
écrit le temps de jeu dans son journal (Saved/Logs/Barque.log, une ligne LogBlueprintUserMessages par appui). Le temps
de jeu part du lancement de l'appli, comme la séquence : c'est l'instant de la balade, à une seconde près. Les journaux
des lancements précédents (Barque-backup-*.log) sont lus aussi ; une capture sans ligne de journal garde son numéro.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from tools import CONFIG, from_windows, to_windows  # noqa: E402

ADB = str(from_windows(CONFIG["android"]["root"]) / "sdk" / "platform-tools" / "adb.exe")
APP = "/sdcard/Android/data/com.odoucet.barque.greybox/files/UnrealGame/Barque/Barque/Saved"
SHOTS = f"{APP}/Screenshots/Android"
LINE = re.compile(r"LogBlueprintUserMessages: \[BP_Recentrage_C_\d+\] ([\d.]+)")


def adb(*a):
    return subprocess.run([ADB, *a], capture_output=True, text=True)


def press_times():
    """Temps de jeu de chaque appui, du plus ancien au plus récent (journaux de sauvegarde, puis journal courant)."""
    logs = sorted(l for l in adb("shell", "ls", f"{APP}/Logs").stdout.split() if l.endswith(".log"))
    logs.sort(key=lambda l: (l == "Barque.log", l))
    times = []
    for name in logs:
        times += [float(t) for t in LINE.findall(adb("shell", "cat", f"{APP}/Logs/{name}").stdout)]
    return times


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--garder", action="store_true", help="ne pas effacer les captures du casque")
    args = ap.parse_args()
    shots = sorted(s for s in adb("shell", "ls", SHOTS).stdout.split() if s.endswith(".png"))
    if not shots:
        print("aucune capture au casque")
        return
    times = press_times()
    # les dernières captures correspondent aux derniers appuis (une capture lancée par adb n'a pas de ligne de journal)
    times = [None] * (len(shots) - len(times)) + times[-len(shots):]
    out = ROOT / "review" / "casque-A" / time.strftime("%Y%m%d")
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp.png"
    for name, t in zip(shots, times):
        adb("pull", f"{SHOTS}/{name}", to_windows(tmp))
        stem = f"A-{t:06.1f}s" if t is not None else f"A-{Path(name).stem}"
        dst = out / f"{stem}.jpg"
        Image.open(tmp).convert("RGB").save(dst, quality=90)
        print(f"{name} → {dst.relative_to(ROOT)}" + (f"  (à {int(t // 60)}:{t % 60:04.1f})" if t is not None else ""))
        if not args.garder:
            adb("shell", "rm", f"{SHOTS}/{name}")
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
