"""Animatic vidéo (J2) : rendu Movie Render Queue de LS_Animatic, puis montage avec la musique.

    python pipeline/review/animatic.py --iter 1     # → review/iter-001/animatic.mp4

Nécessite l'éditeur ouvert. Images intermédiaires dans builds/animatic/frames/ (hors dépôt). La musique
est posée à offset_s (pipeline/sequencer.yaml) ; S1 (0:00-0:20) est en noir, comme dans la séquence.
Verrou GPU tenu pendant le rendu.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "pipeline" / "unreal"))
from gpu import gpu_lock  # noqa: E402
from tools import to_windows  # noqa: E402
import run as ue_run  # noqa: E402

FRAMES = ROOT / "builds" / "animatic" / "frames"
FPS = 30


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iter", type=int, required=True)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--mux-only", action="store_true", help="monter la vidéo à partir des images déjà rendues")
    args = ap.parse_args()
    seq = yaml.safe_load((ROOT / "pipeline" / "sequencer.yaml").read_text(encoding="utf-8"))
    duration = seq["music"]["offset_s"] + seq["music"]["duration_s"]
    expected = int(round(duration * FPS))
    if args.mux_only:
        mux(args.iter, seq, duration, len(list(FRAMES.glob("*.jpeg"))))
        return
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)

    with gpu_lock("animatic.py (rendu Movie Render Queue)"):
        wrapper = ROOT / "Unreal" / "Saved" / "barque_render.py"
        wrapper.write_text(f"import os\nos.environ['BARQUE_FRAMES'] = r'{to_windows(FRAMES)}'\n"
                           f"exec(open(r'{to_windows(ROOT / 'pipeline/unreal/scripts/render_animatic.py')}', encoding='utf-8').read())\n",
                           encoding="utf-8")
        if ue_run.run_live(wrapper) is None:
            raise SystemExit("Éditeur Unreal non joignable : le rendu de l'animatic a besoin de l'éditeur ouvert.")
        t0, last, last_change = time.time(), -1, time.time()
        while True:
            n = len(list(FRAMES.glob("*.jpeg")))
            if n != last:
                last, last_change = n, time.time()
                print(f"\r  {n}/{expected} images ({(time.time() - t0) / 60:.1f} min)", end="", flush=True)
            if n >= expected - 1 and time.time() - last_change > 10:
                break
            stall = 300 if n > 0 else 2400   # avant la 1re image : compilation des shaders, parfois longue
            if time.time() - last_change > stall or time.time() - t0 > args.timeout:
                raise SystemExit(f"\nRendu bloqué ou trop long ({n}/{expected} images)")
            time.sleep(5)
    print()
    mux(args.iter, seq, duration, last)


def mux(iteration, seq, duration, last):
    out = ROOT / "review" / f"iter-{iteration:03d}" / "animatic.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    music = ROOT / seq["music"]["file"]
    first = min(int(p.stem) for p in FRAMES.glob("*.jpeg"))
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-framerate", str(FPS), "-start_number", str(first), "-i", str(FRAMES / "%05d.jpeg"),
                    "-itsoffset", str(seq["music"]["offset_s"]), "-i", str(music),
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-movflags", "+faststart", str(out)], check=True)
    print(f"{out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.0f} Mo, {last} images)")


if __name__ == "__main__":
    main()
