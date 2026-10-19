"""Sprites peints : arbres, buissons, fleurs, lisières, feuillages, oiseaux… générés en local (Z-Image Turbo), détourés
(BiRefNet, nœud RemoveBackground du cœur de ComfyUI), assemblés en atlas. Catalogue : pipeline/comfy/sprites.yaml.

    python pipeline/comfy/sprites.py --test buissons        # 3 essais → assets/textures/sprites/buissons/essai_<n>.png
    python pipeline/comfy/sprites.py buissons fourres        # familles listées (toutes si aucune) → images + atlas
    python pipeline/comfy/sprites.py --atlas-only            # réassemble les atlas depuis les images existantes

Pour chaque famille : images <famille>_<n>.png (RGBA rogné sur le sujet) dans assets/textures/sprites/<famille>/,
atlas assets/textures/sprite_<famille>.png (cases de la taille `cell`, sujet en bas au centre, ou centré pour les
feuillages et la petite faune) et assets/textures/sprites/<famille>.json (emprise du sujet dans chaque case, lue par
le placement). Retour d'Olivier du 18/10 : l'image à plat tournée vers l'œil « rend vachement bien » et libère les
polygones ; détourage repris (pas de liseré). Idempotent par graine ; substituts (placeholder) au manifeste.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from comfy import client  # noqa: E402
from comfy.sky import STYLE  # noqa: E402
from gpu import gpu_lock  # noqa: E402

CATALOG = yaml.safe_load((Path(__file__).with_name("sprites.yaml")).read_text(encoding="utf-8"))
TEX = ROOT / "assets" / "textures"
OUT = TEX / "sprites"
CENTERED = {"foliage", "small", "top"}
# bloc de style du ciel sans ses nuages (ils s'invitaient derrière chaque sujet et collaient au détourage)
SPRITE_STYLE = STYLE.replace(", towering cumulus clouds", "")


def workflow(prompt, seed, size, prefix):
    wf = client.load_workflow("z_image_turbo_t2i.json")
    wf["27"]["inputs"]["text"] = prompt
    wf["3"]["inputs"]["seed"] = seed
    wf["13"]["inputs"]["width"], wf["13"]["inputs"]["height"] = size
    wf["9"]["inputs"]["filename_prefix"] = prefix
    # détourage : masque BiRefNet enregistré à part (composition RGBA en Python)
    wf["50"] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}}
    wf["51"] = {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["50", 0], "image": ["8", 0]}}
    wf["52"] = {"class_type": "MaskToImage", "inputs": {"mask": ["51", 0]}}
    wf["53"] = {"class_type": "SaveImage", "inputs": {"images": ["52", 0], "filename_prefix": prefix + "_masque"}}
    return wf


def generate(prompt, seed, size, dest):
    if dest.exists():
        return dest
    raw, mask = dest.with_name(dest.stem + "_brut.png"), dest.with_name(dest.stem + "_masque.png")
    entry = client.wait(client.submit(workflow(prompt, seed, size, f"barque/sprites/{dest.stem}")), timeout=1800)
    client.download(client.output_files(entry, "9", "images")[0], raw)
    client.download(client.output_files(entry, "53", "images")[0], mask)
    rgb = np.asarray(Image.open(raw).convert("RGB"))
    a = np.asarray(Image.open(mask).convert("L")).astype(np.float32) / 255.0
    a = np.clip((a - 0.15) / 0.7, 0, 1)
    rgba = np.dstack([rgb, (a * 255).astype(np.uint8)])
    ys, xs = np.nonzero(a > 0.5)
    Image.fromarray(rgba, "RGBA").crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).save(dest)
    return dest


def bleed(arr, opaque=250):
    """Couleur du sujet propagée sous la transparence : chaque pixel non opaque prend la couleur du pixel opaque le plus
    proche (le filtrage et les mipmaps ne ramènent plus le gris du fond d'origine au bord du sujet)."""
    from scipy import ndimage
    solid = arr[..., 3] >= opaque
    if not solid.any():
        return arr
    _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
    out = arr.copy()
    out[..., :3] = arr[iy, ix, :3]
    return out


def crown_only(a):
    """Option crown : garde le houppier, retire le tronc (lignes sous la couronne où le sujet devient étroit) et ferme le
    bas par un bord festonné (touffes des grands houppiers : le générateur dessine toujours un arbre entier)."""
    widths = (a > 0.5).sum(axis=1)
    top = int(np.argmax(widths > 0))
    widest = int(np.argmax(widths))
    cut = widest + int(np.argmax(widths[widest:] < 0.45 * widths.max())) if (widths[widest:] < 0.45 * widths.max()).any() else a.shape[0]
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, ry = (top + cut) / 2, max((cut - top) / 2, 1)
    xs = np.nonzero(widths > 0)[0]
    cols = np.nonzero((a > 0.5).any(axis=0))[0]
    cx, rx = (cols.min() + cols.max()) / 2, max((cols.max() - cols.min()) / 2, 1)
    ell = ((xx - cx) / rx) ** 2 + ((yy - cy) / (ry * 1.05)) ** 2
    # bord festonné et propre à chaque image : avec une ellipse lisse, toutes les touffes avaient le même bas en arc,
    # très visible vu d'en dessous (retour d'Olivier du 19/10) ; bruit à deux échelles (grappes, puis feuilles)
    from scipy import ndimage
    rng = np.random.default_rng(int(a.sum()) % (2 ** 32))
    noise = (ndimage.gaussian_filter(rng.normal(size=a.shape), w / 14) * 1.0
             + ndimage.gaussian_filter(rng.normal(size=a.shape), w / 45) * 0.5)
    noise /= max(noise.std(), 1e-6)
    edge = ell + 0.28 * noise
    out = a.copy()
    out[yy > cy] *= np.clip((1.0 - edge[yy > cy]) * 25.0, 0, 1)   # moitié basse : bord irrégulier (plus de tronc)
    return out


def no_ground(a):
    """Arbres : retire la plaque d'herbe et l'ombre peintes sous le tronc (le même ovale revenait sous chaque arbre,
    retour d'Olivier du 19/10). Dans le bas de l'image, seules les colonnes du tronc restent, et le pied s'estompe."""
    solid = a > 0.5
    rows = np.nonzero(solid.any(axis=1))[0]
    if len(rows) < 20:
        return a
    top, bottom = rows.min(), rows.max()
    h = bottom - top
    probe = bottom - int(0.12 * h)                       # hauteur où l'on ne voit plus que le tronc
    cols = np.nonzero(solid[probe])[0]
    if len(cols) == 0:
        return a
    runs = np.split(cols, np.nonzero(np.diff(cols) > 3)[0] + 1)
    trunk = max(runs, key=len)                           # le tronc : le plus large segment plein à cette hauteur
    x0, x1 = trunk.min(), trunk.max()
    pad = max(3, int(0.25 * (x1 - x0)))
    out = a.copy()
    zone = slice(probe, None)
    keep = np.zeros(a.shape[1], bool)
    keep[max(0, x0 - pad):x1 + pad + 1] = True
    out[zone, ~keep] = 0.0
    fade = np.clip((bottom - np.arange(a.shape[0])) / max(0.03 * h, 1.0), 0, 1)   # pied estompé (il s'enfonce dans la berge)
    return out * fade[:, None]


def clean(im, kind="tree", drop=None, crown=False):
    """Restes de fond retirés : pour les sujets posés au sol (arbres, plantes, lisières), seules les parties reliées au
    bas de l'image restent (plus d'îlots de nuages) et les gris clairs reliés au fond sont effacés ; pour la petite
    faune et les feuillages, les fragments minuscules disparaissent (le blanc d'un héron reste). Puis alpha rogné d'un
    pixel et couleurs propagées sous la transparence."""
    from scipy import ndimage
    arr = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb, a = arr[..., :3], arr[..., 3] / 255.0
    if kind not in CENTERED and kind != "glow":            # (fond sombre pour les sujets lumineux : rien de gris à retirer)
        mx, mn = rgb.max(axis=2), rgb.min(axis=2)
        sat = (mx - mn) / np.maximum(mx, 1.0)
        greyish = (sat < 0.14) & (mx > 150)
        lab, _ = ndimage.label(greyish)
        edge = ndimage.binary_dilation(a < 0.5, iterations=2)
        touching = np.unique(lab[edge & greyish])
        a[np.isin(lab, touching[touching > 0])] = 0.0
    if kind == "strip":                                     # nuages crème soudés aux cimes
        mx, mn = rgb.max(axis=2), rgb.min(axis=2)
        a[(mx > 195) & ((mx - mn) / np.maximum(mx, 1.0) < 0.32)] = 0.0
    elif kind not in ("small", "glow"):                     # nuage crème accroché à une plante : grandes plages
        mx, mn = rgb.max(axis=2), rgb.min(axis=2)          # seulement (les petites fleurs blanches restent)
        cream = (mx > 185) & ((mx - mn) / np.maximum(mx, 1.0) < 0.32) & (a > 0.3)
        lab, n = ndimage.label(cream)
        if n:
            sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
            edge = ndimage.binary_dilation(a < 0.5, iterations=3)
            touching = set(np.unique(lab[edge & cream]).tolist()) - {0}
            big = [i + 1 for i, sz in enumerate(sizes) if sz > 0.004 * a.size and (i + 1) in touching]
            a[np.isin(lab, big)] = 0.0
    if drop == "green":                                     # végétation ajoutée d'office derrière un oiseau
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        a[(g > r * 1.08) & (g > b * 1.02) & (g - np.minimum(r, b) > 18)] = 0.0
    if crown:
        a = crown_only(a)
    if kind == "tree":
        a = no_ground(a)
    lab, n = ndimage.label(a > 0.3)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
        if kind in CENTERED:
            keep = [i + 1 for i, sz in enumerate(sizes) if sz >= 0.02 * sizes.max()]
        else:
            bottom = set(np.unique(lab[int(a.shape[0] * 0.9):, :]).tolist()) - {0}
            keep = [i + 1 for i, sz in enumerate(sizes) if (i + 1) in bottom or sz >= 0.25 * sizes.max()]
        a[(lab > 0) & ~np.isin(lab, keep)] = 0.0
    a = ndimage.grey_erosion(a, size=3)
    arr[..., 3] = a * 255.0
    return Image.fromarray(bleed(arr.astype(np.uint8)), "RGBA")


def atlas(name, spec, paths):
    cw, ch = spec["cell"]
    cols, rows = spec["grid"]
    centered = spec["type"] in CENTERED
    strip = spec["type"] == "strip"
    sheet = np.zeros((ch * rows, cw * cols, 4), np.uint8)
    info = []
    for i, p in enumerate(paths):
        opts = spec["items"][i][2] if len(spec["items"][i]) > 2 else {}
        im = clean(Image.open(p), spec["type"], opts.get("drop"), opts.get("crown", False))
        k = (cw / im.width) if strip else min(cw / im.width, ch / im.height) * 0.98
        im = im.resize((max(1, round(im.width * k)), max(1, min(ch, round(im.height * k)))), Image.LANCZOS)
        cx, cy = (i % cols) * cw, (i // cols) * ch
        ox = cx + (cw - im.width) // 2
        oy = cy + ((ch - im.height) // 2 if centered else ch - im.height)
        cell = np.zeros((ch, cw, 4), np.uint8)
        cell[oy - cy:oy - cy + im.height, ox - cx:ox - cx + im.width] = np.asarray(im)
        if strip:   # extrémités en biseau irrégulier : les bandes voisines se fondent au lieu de s'arrêter net
            xs = np.arange(cw) / cw
            ys = np.arange(ch)[:, None] / ch
            wob = 0.03 * np.sin(ys * 37.0 + i) + 0.02 * np.sin(ys * 91.0 + 2 * i)
            ramp = np.clip(np.minimum(xs[None, :] - wob, 1 - xs[None, :] - wob) / 0.12, 0, 1)
            ramp = np.where(ramp >= 1, 1.0, ramp * (0.85 + 0.15 * ys))   # le bas (sol) s'étire un peu plus loin
            base = np.clip((1.0 - ys) / 0.12, 0, 1)                      # pied estompé (enfoui dans le sol et la brume)
            cell[..., 3] = (cell[..., 3] * np.clip(ramp * 1.6 - 0.3, 0, 1) * base).astype(np.uint8)
        sheet[cy:cy + ch, cx:cx + cw] = bleed(cell)
        # emprise du sujet dans sa case (0-1) : le placement en déduit l'échelle du plan
        info.append({"name": p.stem, "u0": (ox - cx) / cw, "u1": (ox - cx + im.width) / cw,
                     "v0": (oy - cy) / ch, "v1": (oy - cy + im.height) / ch})
    Image.fromarray(sheet, "RGBA").save(TEX / f"sprite_{name}.png")
    (OUT / f"{name}.json").write_text(json.dumps({"cell": spec["cell"], "grid": spec["grid"], "type": spec["type"],
                                                  "items": info}, indent=1), encoding="utf-8")
    print(f"→ assets/textures/sprite_{name}.png ({len(paths)} images)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sets", nargs="*", help="familles (toutes par défaut)")
    ap.add_argument("--test", action="store_true", help="3 essais de la première famille listée")
    ap.add_argument("--atlas-only", action="store_true")
    args = ap.parse_args()
    names = args.sets or list(CATALOG["sets"])
    for name in names:
        spec = CATALOG["sets"][name]
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        items = spec["items"][:3] if args.test else spec["items"]
        paths = []
        if args.atlas_only:
            paths = [d / f"{name}_{i}.png" for i in range(len(items))]
        else:
            with gpu_lock(f"comfy-sprites-{name}"):
                for i, item in enumerate(items):
                    iname, kind = item[0], item[1]
                    dest = d / (f"essai_{i}.png" if args.test else f"{name}_{i}.png")
                    prompt = CATALOG["prompts"][spec["type"]].format(kind=kind, style=SPRITE_STYLE)
                    opts = item[2] if len(item) > 2 else {}
                    paths.append(generate(prompt, opts.get("seed", spec["seed"] + i), spec["size"], dest))
                    print(f"  {name}/{iname} → {dest.relative_to(ROOT)}", flush=True)
        if not args.test:
            atlas(name, spec, paths)
        if args.test:
            break


if __name__ == "__main__":
    main()
