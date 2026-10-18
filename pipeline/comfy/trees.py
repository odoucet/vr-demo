"""Arbres peints en plans (variante B de la forêt) : silhouettes d'arbres peintes, générées en local (Z-Image Turbo),
détourées (BiRefNet, nœud RemoveBackground du cœur de ComfyUI), assemblées en atlas.

    python pipeline/comfy/trees.py --test            # 3 essais → assets/textures/arbres/essai_<n>.png (à relire)
    python pipeline/comfy/trees.py                   # lot complet → assets/textures/arbres/arbre_<n>.png + atlas
    python pipeline/comfy/trees.py --atlas-only      # réassemble l'atlas depuis les PNG existants

Chaque arbre : image 832×1216 sur fond gris uni, masque de détourage, puis RGBA rogné sur l'arbre et posé dans une
case de l'atlas (4 × 2 cases de 512 × 1024 → assets/textures/arbres_atlas.png 2048 × 2048), pied de l'arbre en bas de la case.
Prompt : bloc de style commun du ciel (PROMPTS.md). Idempotent par graine ; substitut (placeholder) en attendant
des arbres validés par Olivier.
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
from comfy.sky import STYLE  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "textures" / "arbres"
BASE = ("single isolated tree, the whole tree visible from the base of the trunk to the top of the crown, {kind}, "
        "lit by soft warm dusk light from the left, darker cool shadow side, centered, plain flat light grey background, "
        "no ground, no grass, no shadow on the ground, hand-painted, " + STYLE)
KINDS = [
    ("feuillu-rond", "broad deciduous tree with a wide rounded crown made of big billowing foliage clumps, thick trunk"),
    ("feuillu-haut", "tall deciduous tree with a tall oval crown of layered foliage clumps, slender trunk"),
    ("chene", "old gnarled oak tree with a broad irregular crown of dense foliage masses, twisted trunk and branches"),
    ("resineux", "tall conical fir tree with layered drooping branches, dark blue-green needles"),
    ("feuillu-leger", "young deciduous tree with an airy crown of small foliage clumps and visible branches"),
    ("saule", "weeping willow tree with long cascading foliage hanging down, rounded silhouette"),
    ("feuillu-large", "massive spreading deciduous tree with a flat-topped umbrella crown of foliage clumps"),
    ("resineux-fin", "slender pine tree with a tall straight trunk and a few dark foliage tufts near the top"),
]
W, H = 832, 1216
CELL = (512, 1024)
ATLAS_COLS, ATLAS_ROWS = 4, 2


def workflow(prompt, seed, prefix):
    wf = client.load_workflow("z_image_turbo_t2i.json")
    wf["27"]["inputs"]["text"] = prompt
    wf["3"]["inputs"]["seed"] = seed
    wf["13"]["inputs"]["width"], wf["13"]["inputs"]["height"] = W, H
    wf["9"]["inputs"]["filename_prefix"] = prefix
    # détourage : masque BiRefNet enregistré à part (composition RGBA en Python)
    wf["50"] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}}
    wf["51"] = {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["50", 0], "image": ["8", 0]}}
    wf["52"] = {"class_type": "MaskToImage", "inputs": {"mask": ["51", 0]}}
    wf["53"] = {"class_type": "SaveImage", "inputs": {"images": ["52", 0], "filename_prefix": prefix + "_masque"}}
    return wf


def generate(name, kind, seed, dest):
    if dest.exists():
        return dest
    raw, mask = dest.with_name(dest.stem + "_brut.png"), dest.with_name(dest.stem + "_masque.png")
    entry = client.wait(client.submit(workflow(BASE.format(kind=kind), seed, f"barque/arbres/{dest.stem}")), timeout=1800)
    client.download(client.output_files(entry, "9", "images")[0], raw)
    client.download(client.output_files(entry, "53", "images")[0], mask)
    rgb = np.asarray(Image.open(raw).convert("RGB"))
    a = np.asarray(Image.open(mask).convert("L")).astype(np.float32) / 255.0
    a = np.clip((a - 0.15) / 0.7, 0, 1)                    # bord net (test alpha au Quest), sans halo gris
    rgba = np.dstack([rgb, (a * 255).astype(np.uint8)])
    ys, xs = np.nonzero(a > 0.5)
    im = Image.fromarray(rgba, "RGBA").crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    im.save(dest)
    return dest


def bleed(arr, opaque=250):
    """Couleur du feuillage propagée sous la transparence : chaque pixel non opaque prend la couleur du pixel opaque
    le plus proche (le filtrage et les mipmaps ne ramènent plus le gris du fond d'origine au bord des arbres)."""
    from scipy import ndimage
    solid = arr[..., 3] >= opaque
    if not solid.any():
        return arr
    _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
    out = arr.copy()
    out[..., :3] = arr[iy, ix, :3]
    return out


def clean(im):
    """Détourage repris (retour d'Olivier : « on le voit un peu ») : restes de fond gris clair ou de nuages retirés
    (couleurs peu saturées et claires), alpha rogné d'un pixel, puis couleurs propagées sous la transparence."""
    from scipy import ndimage
    arr = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb, a = arr[..., :3], arr[..., 3] / 255.0
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    a[(sat < 0.14) & (mx > 150)] = 0.0
    a = ndimage.grey_erosion(a, size=3)
    arr[..., 3] = a * 255.0
    return Image.fromarray(bleed(arr.astype(np.uint8)), "RGBA")


def atlas(paths):
    """Atlas 2048 × 2048 : une case par arbre, l'arbre mis à l'échelle dans la case, pied en bas au centre ; les
    couleurs débordent sous le masque (pas de liseré gris au filtrage ni dans les mipmaps)."""
    sheet = np.zeros((CELL[1] * ATLAS_ROWS, CELL[0] * ATLAS_COLS, 4), np.uint8)
    info = []
    for i, p in enumerate(paths):
        im = clean(Image.open(p))
        k = min(CELL[0] / im.width, CELL[1] / im.height) * 0.98
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
        cx, cy = (i % ATLAS_COLS) * CELL[0], (i // ATLAS_COLS) * CELL[1]
        ox, oy = cx + (CELL[0] - im.width) // 2, cy + CELL[1] - im.height
        cell = np.zeros((CELL[1], CELL[0], 4), np.uint8)
        cell[oy - cy:oy - cy + im.height, ox - cx:ox - cx + im.width] = np.asarray(im)
        sheet[cy:cy + CELL[1], cx:cx + CELL[0]] = bleed(cell)
        # largeur / hauteur relatives de l'arbre dans sa case (le maillage du plan prend ces proportions)
        info.append({"name": p.stem, "u0": ox / sheet.shape[1], "u1": (ox + im.width) / sheet.shape[1],
                     "v0": oy / sheet.shape[0], "v1": (oy + im.height) / sheet.shape[0], "aspect": im.width / im.height})
    Image.fromarray(sheet, "RGBA").save(OUT.parent / "arbres_atlas.png")   # importé par greybox.py (look_texture)
    (OUT / "arbres_atlas.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(f"→ assets/textures/arbres_atlas.png ({len(paths)} arbres)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--atlas-only", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.atlas_only:
        atlas(sorted(OUT.glob("arbre_*[0-9].png")))
        return
    kinds = KINDS[:3] if args.test else KINDS
    paths = []
    with gpu_lock("comfy-arbres"):
        for i, (name, kind) in enumerate(kinds):
            dest = OUT / (f"essai_{i}.png" if args.test else f"arbre_{i}.png")
            paths.append(generate(name, kind, 1000 + i, dest))
            print(f"  {name} → {dest.relative_to(ROOT)}", flush=True)
    if not args.test:
        atlas(paths)


if __name__ == "__main__":
    main()
