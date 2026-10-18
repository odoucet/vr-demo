"""Mesure de performance au casque : fréquence d'image et charge CPU/GPU du Quest, beat par beat.

    python pipeline/unreal/quest_perf.py --variant greybox            # lance l'APK installé, mesure 260 s
    python pipeline/unreal/quest_perf.py --variant j1 --duration 65
    python pipeline/unreal/quest_perf.py --parse review/perf/greybox-20261019-1030.log --load-s 9

Quest branché en USB, débogage accepté, APK déjà installé (package_android.py / Install_Barque-arm64.bat).
Lit les lignes de télémétrie que le runtime du Quest écrit chaque seconde dans logcat (étiquette VrApi :
FPS=72/72, GPU%=..., CPU%=..., Stale=...), y compris pour une application OpenXR. Le casque doit être porté
(capteur de proximité) ou le capteur désactivé, sinon le rendu est en pause.

Sorties dans review/perf/ : journal brut, résumé par beat (temps de sequencer.yaml, t0 = lancement de
l'application), courbe PNG. Les budgets de départ (CLAUDE.md) : 72 Hz minimum.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from tools import CONFIG, from_windows  # noqa: E402

OUT = ROOT / "review" / "perf"
PACKAGES = {"j1": "com.odoucet.barque", "greybox": "com.odoucet.barque.greybox", "j1b": "com.odoucet.barque.j1b",
            "hd": "com.odoucet.barque.hd"}
ACTIVITY = "com.epicgames.unreal.GameActivity"
LINE = re.compile(r"FPS=(\d+)/(\d+).*?Stale=(\d+).*?GPU%=([\d.]+).*?CPU%=([\d.]+)")
TARGET_FPS = 72


def adb(*args, **kw):
    exe = from_windows(CONFIG["android"]["root"]) / "sdk" / "platform-tools" / "adb.exe"
    return subprocess.run([str(exe), *args], capture_output=True, text=True, **kw)


def record(variant, duration, log_path):
    devices = [l for l in adb("devices").stdout.splitlines()[1:] if l.strip().endswith("device")]
    if not devices:
        raise SystemExit("Aucun casque : brancher le Quest en USB et accepter le débogage.")
    pkg = PACKAGES[variant]
    adb("shell", "am", "force-stop", pkg)
    adb("logcat", "-c")
    adb("shell", "am", "start", "-n", f"{pkg}/{ACTIVITY}", check=True)
    t0 = time.time()
    print(f"{pkg} lancé, mesure pendant {duration} s (porter le casque)…")
    import queue
    import threading
    with log_path.open("w", encoding="utf-8") as f:
        exe = from_windows(CONFIG["android"]["root"]) / "sdk" / "platform-tools" / "adb.exe"
        proc = subprocess.Popen([str(exe), "logcat", "-v", "epoch", "-s", "VrApi:I"], stdout=subprocess.PIPE, text=True)
        f.write(f"# t0={t0:.3f} {pkg}\n")
        lines = queue.Queue()
        threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout], daemon=True).start()
        last = time.time()
        try:
            while time.time() - t0 < duration:
                try:
                    f.write(lines.get(timeout=1.0))
                    last = time.time()
                except queue.Empty:
                    # Plus de télémétrie : l'application a perdu le premier plan (casque retiré, suivi perdu).
                    if time.time() - last > 15 and time.time() - t0 > 30:
                        print(f"Télémétrie interrompue à {last - t0:.0f} s (casque retiré ou mis en veille ?)")
                        break
        finally:
            proc.terminate()


def parse(log_path):
    lines = log_path.read_text(encoding="utf-8").splitlines()
    t0 = float(re.search(r"t0=([\d.]+)", lines[0]).group(1))
    rows = []
    for l in lines[1:]:
        m = LINE.search(l)
        if m:
            ts = float(l.split()[0])
            rows.append((ts - t0, int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5))))
    return rows


def summarize(rows, log_path, load_s):
    seq = yaml.safe_load((PIPELINE / "sequencer.yaml").read_text(encoding="utf-8"))
    offset = seq["music"]["offset_s"]
    rows = [(r[0] - load_s, *r[1:]) for r in rows]
    beats = [(b["id"], offset + b["music_s"]) for b in seq["beats"]]
    report = [f"Mesure : {log_path.name}, {len(rows)} échantillons (1/s), chargement estimé à {load_s} s", ""]
    report.append(f"{'beat':12s} {'FPS min':>8s} {'FPS moy':>8s} {'images perdues':>15s} {'GPU % max':>10s} {'CPU % max':>10s}")
    for i, (bid, start) in enumerate(beats):
        end = beats[i + 1][1] if i + 1 < len(beats) else offset + seq["music"]["duration_s"]
        sel = [r for r in rows if start <= r[0] < end]
        if not sel:
            continue
        fps = [r[1] for r in sel]
        flag = "  ⚠" if min(fps) < TARGET_FPS else ""
        report.append(f"{bid:12s} {min(fps):8d} {sum(fps) / len(fps):8.1f} {sum(r[3] for r in sel):15d} "
                      f"{max(r[4] for r in sel) * 100:10.0f} {max(r[5] for r in sel) * 100:10.0f}{flag}")
    text = "\n".join(report) + "\n"
    log_path.with_suffix(".txt").write_text(text, encoding="utf-8")
    print(text)

    W, H, pad = 1600, 400, 40
    im = Image.new("RGB", (W, H), "#141414")
    d = ImageDraw.Draw(im)
    rows = [r for r in rows if r[0] >= 0]
    tmax = max(r[0] for r in rows) or 1
    x = lambda t: pad + (W - 2 * pad) * t / tmax                     # noqa: E731
    y = lambda v: H - pad - (H - 2 * pad) * v / 100                   # noqa: E731
    for bid, start in beats:
        d.line([x(start), pad, x(start), H - pad], fill="#444")
        d.text((x(start) + 3, pad - 16), bid, fill="#ffd27a")
    for key, col in ((1, "#7fd67f"), (4, "#7fb0ff"), (5, "#ff9f6f")):
        scale = 1 if key == 1 else 100
        pts = [(x(r[0]), y(r[key] * scale)) for r in rows]
        if len(pts) > 1:
            d.line(pts, fill=col, width=2)
    for x0 in range(pad, W - pad, 12):                                 # 72 Hz en pointillé, par-dessus
        d.line([x0, y(TARGET_FPS), x0 + 6, y(TARGET_FPS)], fill="#ff5050")
    d.text((pad, H - pad + 8), "vert : FPS · bleu : GPU % · orange : CPU % · rouge : 72 Hz", fill="white")
    im.save(log_path.with_suffix(".png"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", default="greybox", choices=list(PACKAGES))
    ap.add_argument("--duration", type=int, default=260)
    ap.add_argument("--parse", type=Path, help="relire un journal existant au lieu de mesurer")
    ap.add_argument("--load-s", type=float, default=0.0,
                    help="durée de chargement entre le lancement et le début de la séquence (décale les beats)")
    args = ap.parse_args()
    if args.parse:
        log_path = args.parse
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        log_path = OUT / f"{args.variant}-{time.strftime('%Y%m%d-%H%M')}.log"
        record(args.variant, args.duration, log_path)
    rows = parse(log_path)
    if not rows:
        raise SystemExit(f"Aucune ligne de télémétrie VrApi dans {log_path} (casque porté ? application lancée ?)")
    summarize(rows, log_path, args.load_s)


if __name__ == "__main__":
    main()
