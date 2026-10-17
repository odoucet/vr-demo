"""Skydome provisoire : panorama de crépuscule 2:1 généré en local (Z-Image Turbo), raccordé horizontalement.

    python pipeline/comfy/sky.py                    # graines 1 à 3 → assets/sky/ciel_s<graine>.png
    python pipeline/comfy/sky.py --seeds 7 --pick 7 # retient une graine → assets/sky/ciel.png

Prompt : section « Ciel et lointain » de PROMPTS.md (bloc de style commun). Le panorama est rendu
raccordable (fondu circulaire des bords gauche/droit) pour se refermer sur la sphère du ciel. Substitut :
le skydome final viendra du pipeline de rendu du lointain (CLAUDE.md). Idempotent par graine.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from comfy import client  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "sky"
STYLE = ("hand-painted 1980s Japanese animation background art, gouache and watercolor, soft painterly edges, flat "
         "color shapes, gentle diffuse light, lush saturated greens, towering cumulus clouds, nostalgic and serene mood")
PROMPT = ("wide 360 degree panoramic dusk sky, equirectangular, towering cumulus clouds lit pink and gold from below, "
          "deep blue zenith, distant dark forest silhouette along the horizon, first stars, hand-painted, " + STYLE)


def make_seamless(path, blend=0.08):
    """Raccord horizontal : les `blend` derniers pourcents se fondent dans le bord gauche puis sont retirés ;
    la dernière colonne enchaîne alors sur la première. Image remise au format 2:1."""
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    h, w, _ = im.shape
    b = int(w * blend)
    t = np.linspace(0, 1, b, endpoint=False)[None, :, None]
    out = im[:, : w - b].copy()
    out[:, :b] = im[:, :b] * t + im[:, w - b:] * (1 - t)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((w, w // 2), Image.LANCZOS).save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--pick", type=int)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with gpu_lock("sky.py (Z-Image Turbo)"):
        for seed in args.seeds:
            dest = OUT / f"ciel_s{seed}.png"
            if dest.exists():
                continue
            wf = client.load_workflow("z_image_turbo_t2i.json")
            wf["27"]["inputs"]["text"] = PROMPT
            wf["3"]["inputs"]["seed"] = seed
            wf["9"]["inputs"]["filename_prefix"] = f"barque/sky/ciel_s{seed}"
            entry = client.wait(client.submit(wf), timeout=1800)
            client.download(client.output_files(entry, "9", "images")[0], dest)
            make_seamless(dest)
            print(f"  {dest.relative_to(ROOT)}")
    if args.pick:
        shutil.copyfile(OUT / f"ciel_s{args.pick}.png", OUT / "ciel.png")
        (OUT / "params.json").write_text(json.dumps({"seed": args.pick, "prompt": PROMPT, "model": "z_image_turbo_bf16",
                                                     "workflow": "pipeline/comfy/workflows/z_image_turbo_t2i.json"},
                                                    indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Retenu : assets/sky/ciel.png (graine {args.pick})")


if __name__ == "__main__":
    main()
