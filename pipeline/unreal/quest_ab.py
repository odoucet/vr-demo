"""Tests A/B de performance en direct au casque : commandes console envoyées par adb pendant la balade, temps GPU
de l'application relevé (télémétrie VrApi) avant / pendant chaque essai.

    python pipeline/unreal/quest_ab.py --at 25 "showflag.translucency 0" "showflag.fog 0" "r.MSAACount 1"

L'application est lancée, on attend --at secondes (le beat à étudier), puis pour chaque commande : référence
(6 s), commande (6 s), commande d'annulation (« 0 » ↔ « 1 », ou --undo). Build Development requis (console).
Résultat : temps GPU moyen de l'application (ms) et images/s pour chaque essai, dans review/perf/ab-*.txt.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from tools import CONFIG, from_windows  # noqa: E402

ADB = str(from_windows(CONFIG["android"]["root"]) / "sdk" / "platform-tools" / "adb.exe")
PKG = "com.odoucet.barque.greybox"
LINE = re.compile(r"FPS=(\d+)/.*?App=([\d.]+)ms.*?GPU%=([\d.]+)")


def adb(*a):
    return subprocess.run([ADB, *a], capture_output=True, text=True)


def console(cmd):
    adb("shell", "am", "broadcast", "-a", "android.intent.action.RUN", "-e", "cmd", f"'{cmd}'")


def sample(seconds):
    adb("logcat", "-c")
    time.sleep(seconds)
    out = adb("logcat", "-d", "-s", "VrApi:I").stdout
    rows = [tuple(float(x) for x in m.groups()) for m in LINE.finditer(out)]
    rows = rows[1:] or rows                       # la 1re seconde mélange avant / après
    if not rows:
        return None
    return (sum(r[0] for r in rows) / len(rows), sum(r[1] for r in rows) / len(rows))


def undo_of(cmd):
    head, _, val = cmd.rpartition(" ")
    return f"{head} {'1' if val == '0' else '0'}" if val in ("0", "1") else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commands", nargs="+")
    ap.add_argument("--at", type=float, default=25.0, help="secondes après le lancement")
    ap.add_argument("--undo", nargs="*", default=None, help="commandes d'annulation (même ordre)")
    ap.add_argument("--dwell", type=float, default=6.0)
    args = ap.parse_args()
    if "Asleep" in adb("shell", "dumpsys", "power").stdout:     # réveil seulement si endormi (sinon ouvre le menu)
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "am", "broadcast", "-a", "com.oculus.vrpowermanager.prox_close")
    adb("shell", "am", "force-stop", PKG)
    adb("shell", "am", "start", "-n", f"{PKG}/com.epicgames.unreal.GameActivity")
    time.sleep(args.at)
    report = [f"Essais A/B à t = {args.at:.0f} s (temps GPU de l'application, moyenne sur {args.dwell:.0f} s)", ""]
    for i, cmd in enumerate(args.commands):
        ref = sample(args.dwell)
        console(cmd)
        test = sample(args.dwell)
        undo = (args.undo[i] if args.undo and i < len(args.undo) else undo_of(cmd))
        if undo:
            console(undo)
        if ref and test:
            line = (f"{cmd:38s} réf {ref[1]:5.2f} ms ({ref[0]:4.1f} i/s) → {test[1]:5.2f} ms ({test[0]:4.1f} i/s)"
                    f"  gain {ref[1] - test[1]:+.2f} ms")
        else:
            line = f"{cmd:38s} pas de télémétrie"
        print(line, flush=True)
        report.append(line)
    adb("shell", "am", "broadcast", "-a", "com.oculus.vrpowermanager.automation_disable")
    out = ROOT / "review" / "perf" / f"ab-{time.strftime('%Y%m%d-%H%M')}.txt"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"→ {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
