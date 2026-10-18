"""Skydome provisoire : panorama de crépuscule 2:1 généré en local (Z-Image Turbo), raccordé horizontalement.

    python pipeline/comfy/sky.py                    # graines 1 à 3 → assets/sky/ciel_s<graine>.png
    python pipeline/comfy/sky.py --seeds 7 --pick 7 # retient une graine → assets/sky/ciel.png (agrandi en 4096×2048)
    python pipeline/comfy/sky.py --upscale          # réagrandit la graine retenue (params.json)
    python pipeline/comfy/sky.py --olivier          # ciel HD d'Olivier (refs/ciel.png) → assets/sky/ciel.png

Prompt : section « Ciel et lointain » de PROMPTS.md (bloc de style commun). Le panorama est rendu
raccordable (fondu circulaire des bords gauche/droit) pour se refermer sur la sphère du ciel. Substitut :
le skydome final viendra du pipeline de rendu du lointain (CLAUDE.md). Idempotent par graine.
Agrandissement : modèle 4x (Remacri, net sur les aplats peints) puis réduction à 4096×2048, la taille maximale
raisonnable sur Quest. L'image est prolongée de chaque côté par son bord opposé avant l'agrandissement pour que
le raccord gauche/droite reste continu.
"""
import argparse
import json
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


SIZE = (4096, 2048)
PAD = 64


def upscale(src, dest):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    padded = Image.new("RGB", (w + 2 * PAD, h))
    padded.paste(im.crop((w - PAD, 0, w, h)), (0, 0))
    padded.paste(im, (PAD, 0))
    padded.paste(im.crop((0, 0, PAD, h)), (w + PAD, 0))
    tmp = OUT / "_upscale_in.png"
    padded.save(tmp)
    wf = client.load_workflow("upscale_model.json")
    wf["1"]["inputs"]["image"] = client.upload_image(tmp)
    wf["4"]["inputs"]["filename_prefix"] = "barque/sky/upscale"
    entry = client.wait(client.submit(wf), timeout=1800)
    client.download(client.output_files(entry, "4", "images")[0], tmp)
    big = Image.open(tmp).convert("RGB")
    k = big.width / padded.width
    big = big.crop((round(PAD * k), 0, round((PAD + w) * k), big.height))
    big.resize(SIZE, Image.LANCZOS).save(dest)
    tmp.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--pick", type=int)
    ap.add_argument("--upscale", action="store_true", help="réagrandir la graine retenue")
    ap.add_argument("--olivier", action="store_true", help="partir de refs/ciel.png (dépôt d'Olivier)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.olivier:
        src = OUT / "ciel_olivier.png"
        Image.open(ROOT / "refs" / "ciel.png").convert("RGB").save(src)     # copie : refs/ n'est jamais modifié
        make_seamless(src)
        with gpu_lock("sky.py (agrandissement)"):
            upscale(src, OUT / "ciel.png")
        (OUT / "params.json").write_text(json.dumps({"source": "refs/ciel.png (Olivier, Midjourney, prompt « ciel »)",
                                                     "upscale": "pipeline/comfy/workflows/upscale_model.json "
                                                                "(4x_foolhardy_Remacri) → 4096x2048"},
                                                    indent=2, ensure_ascii=False), encoding="utf-8")
        print("Retenu : assets/sky/ciel.png (ciel HD d'Olivier, raccordé et agrandi)")
        return
    if args.upscale:
        args.pick, args.seeds = json.loads((OUT / "params.json").read_text(encoding="utf-8"))["seed"], []
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
            upscale(OUT / f"ciel_s{args.pick}.png", OUT / "ciel.png")
    if args.pick:
        (OUT / "params.json").write_text(json.dumps({"seed": args.pick, "prompt": PROMPT, "model": "z_image_turbo_bf16",
                                                     "workflow": "pipeline/comfy/workflows/z_image_turbo_t2i.json",
                                                     "upscale": "pipeline/comfy/workflows/upscale_model.json "
                                                                "(4x_foolhardy_Remacri) → 4096x2048"},
                                                    indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Retenu : assets/sky/ciel.png (graine {args.pick})")


if __name__ == "__main__":
    main()
