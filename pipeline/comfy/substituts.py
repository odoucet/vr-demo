"""Substituts locaux d'images d'assets en attendant celles d'Olivier (Midjourney), avec les prompts de PROMPTS.md.

    python pipeline/comfy/substituts.py arche-statues tete-couchee     # → assets/concepts/<id>.png

Prompt lu dans PROMPTS.md (ligne `- \\`<id>\\` : \\`...\\``), bloc [peint-3d] substitué, Z-Image Turbo 1024 × 1024,
graine fixe. Provisoire (placeholder) : dès qu'Olivier dépose refs/inbox/<id>.png, c'est son image qui passe en 3D.
Idempotent (image existante sautée).
"""
import argparse
import re
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from comfy import client  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "concepts"


def prompt(asset_id):
    text = (ROOT / "PROMPTS.md").read_text(encoding="utf-8")
    block = re.search(r"\*\*\[peint-3d\]\*\*.*?```\n(.*?)\n```", text, re.S).group(1).strip()
    line = re.search(r"- `" + re.escape(asset_id) + r"` : `(.*?)`$", text, re.M).group(1)
    return line.replace("[peint-3d]", block)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--seed", type=int, default=7)   # arche-statues : graine 13 (bras levés qui portent l'arche)
    args = ap.parse_args()
    with gpu_lock("substituts"):
        for asset_id in args.ids:
            dest = OUT / f"{asset_id}.png"
            if dest.exists():
                continue
            wf = client.load_workflow("z_image_turbo_t2i.json")
            wf["27"]["inputs"]["text"] = prompt(asset_id)
            wf["3"]["inputs"]["seed"] = args.seed
            wf["13"]["inputs"]["width"], wf["13"]["inputs"]["height"] = 1024, 1024
            wf["9"]["inputs"]["filename_prefix"] = f"barque/substituts/{asset_id}"
            entry = client.wait(client.submit(wf), timeout=900)
            client.download(client.output_files(entry, "9", "images")[0], dest)
            print(f"→ {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
