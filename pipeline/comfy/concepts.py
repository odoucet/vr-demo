"""Concepts d'ambiance provisoires pour les beats sans image d'Olivier (génération locale, Z-Image Turbo).

    python pipeline/comfy/concepts.py                 # beats manquants dans refs/ → assets/concepts/<beat>.png
    python pipeline/comfy/concepts.py S3-ABYSSE --seed 5

Prompts lus dans PROMPTS.md (section « Concepts d'ambiance », bloc [style] substitué), 16:9 (1344×768).
Substituts : dès qu'Olivier dépose refs/<beat>.png, c'est sa version qui fait foi. Idempotent.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from comfy import client  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "concepts"
BEATS = ["S1-NOIR", "S2-PONTON", "S3-ABYSSE", "S4-GUE", "S5-RACINES", "S6-LUNE", "S7-LAC"]


def prompts():
    text = (ROOT / "PROMPTS.md").read_text(encoding="utf-8")
    style = re.search(r"\*\*\[style\]\*\*.*?```\n(.*?)\n```", text, re.S).group(1).strip()
    found = dict(re.findall(r"- `(S\d-[A-Z]+)` : `(.*?)`", text))
    return {b: p.replace("[style]", style) for b, p in found.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("beats", nargs="*")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    table = prompts()
    beats = args.beats or [b for b in BEATS if not (ROOT / "refs" / f"{b}.png").exists()]
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = OUT / "params.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    with gpu_lock("concepts.py (Z-Image Turbo)"):
        for beat in beats:
            dest = OUT / f"{beat}.png"
            if dest.exists() and meta.get(beat, {}).get("seed") == args.seed:
                continue
            wf = client.load_workflow("z_image_turbo_t2i.json")
            wf["27"]["inputs"]["text"] = table[beat]
            wf["13"]["inputs"].update(width=1344, height=768)
            wf["3"]["inputs"]["seed"] = args.seed
            wf["9"]["inputs"]["filename_prefix"] = f"barque/concepts/{beat}"
            entry = client.wait(client.submit(wf), timeout=1800)
            client.download(client.output_files(entry, "9", "images")[0], dest)
            meta[beat] = {"seed": args.seed, "prompt": table[beat], "model": "z_image_turbo_bf16",
                          "workflow": "pipeline/comfy/workflows/z_image_turbo_t2i.json"}
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
