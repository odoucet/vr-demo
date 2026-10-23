"""Skydome provisoire : panorama de crépuscule 2:1 généré en local (Z-Image Turbo), raccordé horizontalement.

    python pipeline/comfy/sky.py                    # graines 1 à 3 → assets/sky/ciel_s<graine>.png
    python pipeline/comfy/sky.py --seeds 7 --pick 7 # retient une graine → assets/sky/ciel.png (agrandi en 4096×2048)
    python pipeline/comfy/sky.py --upscale          # réagrandit la graine retenue (params.json)
    python pipeline/comfy/sky.py --olivier          # ciel HD d'Olivier (refs/ciel.png) → assets/sky/ciel.png
    python pipeline/comfy/sky.py --nuit             # ciel de nuit d'Olivier (refs/inbox/ciel-nuit.png) → assets/sky/ciel-nuit.png

Prompt : section « Ciel et lointain » de PROMPTS.md (bloc de style commun). Le panorama est rendu
raccordable (fondu circulaire des bords gauche/droit) pour se refermer sur la sphère du ciel. Substitut :
ciel définitif de la démo (tout en temps réel, D19). Idempotent par graine.
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


def night_panorama(src, dest, w=2000, horizon=0.82, ground=0.97, tree_top=0.62, tree_band=0.17):
    """Ciel de nuit d'Olivier (16:9, forêt en bas) → panorama 2:1 calé comme le ciel de jour : deux moitiés en miroir
    (idée d'Olivier, 20/10 : retourné, ses nuages tombent à peu près sur ceux du ciel de jour ; le miroir referme aussi
    le tour sans couture), sol à `horizon` de la hauteur, cimes des arbres ramenées à la hauteur de celles du jour
    (`tree_band` sous l'horizon : à pleine taille, elles monteraient à ~40° au-dessus de l'horizon), zénith prolongé
    dans le bleu nuit du haut de l'image, sol sombre sous l'horizon."""
    im = Image.open(src).convert("RGB")
    iw, ih = im.size
    s = tree_band * (w // 2) / ((ground - tree_top) * ih)          # échelle verticale (hauteur finale = w / 2)
    half = im.resize((w // 2, int(ih * s)), Image.LANCZOS)
    pano = np.concatenate([np.asarray(half.transpose(Image.FLIP_LEFT_RIGHT)), np.asarray(half)], axis=1).astype(np.float32)
    H = w // 2
    y0 = int(horizon * H - ground * pano.shape[0])                 # haut de l'image dans le panorama
    out = np.zeros((H, w, 3), np.float32)
    from scipy import ndimage
    # bleu nuit du haut, colonne par colonne, très lissé (sinon chaque étoile fait une strie verticale)
    top = ndimage.uniform_filter1d(np.median(pano[:40], axis=0), 300, axis=0, mode="wrap")
    zen = top.mean(axis=0) * 0.8
    for y in range(max(y0, 0)):
        t = y / max(y0, 1)
        out[y] = zen * (1 - t) + top * t
    yb = y0 + pano.shape[0]
    out[max(y0, 0):min(yb, H)] = pano[max(-y0, 0):max(-y0, 0) + min(yb, H) - max(y0, 0)]
    if y0 > 0:                                                      # raccord adouci zénith / image
        for k in range(min(30, pano.shape[0])):
            a = k / 30
            out[y0 + k] = out[y0 + k] * a + top * (1 - a)
    if yb < H:
        out[yb:] = ndimage.uniform_filter1d(np.median(pano[-20:], axis=0), 300, axis=0, mode="wrap") * 0.7
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dest)


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
    ap.add_argument("--nuit", action="store_true", help="ciel de nuit d'Olivier (refs/inbox/ciel-nuit.png)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.nuit:
        src = OUT / "ciel-nuit_olivier.png"
        night_panorama(ROOT / "refs" / "inbox" / "ciel-nuit.png", src)
        with gpu_lock("sky.py (agrandissement)"):
            upscale(src, OUT / "ciel-nuit.png")
        (OUT / "params-nuit.json").write_text(json.dumps({"source": "refs/inbox/ciel-nuit.png (Olivier, Midjourney, prompt « ciel-nuit »)",
                                                          "montage": "deux moitiés en miroir, horizon à 82 %, zénith prolongé",
                                                          "upscale": "4x_foolhardy_Remacri → 4096x2048"}, indent=2, ensure_ascii=False),
                                              encoding="utf-8")
        print("Retenu : assets/sky/ciel-nuit.png")
        return
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
