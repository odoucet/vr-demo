"""Cartes de relief des sprites peints (volume en stéréo des sujets proches).

    python pipeline/comfy/relief.py arbres buissons     # → assets/textures/relief_<famille>.png

La silhouette de chaque case de l'atlas (assets/textures/sprite_<famille>.png) est « gonflée » : la hauteur suit un
profil de dôme selon la distance au bord (un houppier se bombe, un tronc fin reste presque plat), modulée par les
touches claires du feuillage (les touffes éclairées avancent). 0 = plan du sprite, 1 = le plus proche de l'œil.
greybox.py en tire, pour les sujets proches, une grille creusée selon cette carte au lieu du plan plat.
Depth Anything V3 (ComfyUI) a été essayé le 19/10 : son nœud échoue dans son environnement isolé (module manquant), et
selon Olivier ces modèles ne savent pas traiter des images peintes, façon dessin animé. Piste écartée : le gonflement
de silhouette suffit pour des sujets peints isolés et ne demande pas de GPU.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT / "assets" / "textures"
OUT = TEX / "sprites"


def inflate(rgba):
    """Relief 0-1 d'une case RGBA."""
    a = rgba[..., 3].astype(np.float32) / 255.0
    solid = a > 0.5
    if solid.sum() < 50:
        return np.zeros(a.shape, np.float32)
    e = ndimage.distance_transform_edt(solid)
    labels, n = ndimage.label(solid)
    rmax = ndimage.maximum(e, labels, index=np.arange(1, n + 1))       # rayon de chaque morceau de silhouette
    R = np.zeros_like(e)
    R[solid] = np.asarray(rmax)[labels[solid] - 1]
    R = np.maximum(R, 1.0)
    g = max(rmax)
    # profil parabolique (flancs doux : un dôme sphérique a des flancs verticaux au bord de la silhouette, qui étirent la
    # texture vue de biais), à l'échelle du plus gros morceau
    u = np.clip(e / R, 0, 1)
    dome = u * (2.0 - u) * (R / g)
    lum = rgba[..., :3].astype(np.float32).mean(axis=2) / 255.0
    detail = ndimage.gaussian_filter(lum, 2) - ndimage.gaussian_filter(lum, 12)   # touffes claires en avant
    h = dome * (0.8 + 1.2 * detail)
    h = ndimage.gaussian_filter(h * solid, 2) / np.maximum(ndimage.gaussian_filter(solid.astype(np.float32), 2), 1e-3)
    return np.clip(np.where(solid, h, 0.0), 0, 1)


def relief(name):
    meta = json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))
    atlas = np.asarray(Image.open(TEX / f"sprite_{name}.png").convert("RGBA"))
    cols, rows = meta["grid"]
    ch, cw = atlas.shape[0] // rows, atlas.shape[1] // cols
    out = np.zeros(atlas.shape[:2], np.float32)
    for i in range(len(meta["items"])):
        r, c = divmod(i, cols)
        out[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] = inflate(atlas[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw])
    dest = TEX / f"relief_{name}.png"           # demi-résolution, niveaux de gris : léger au Quest
    Image.fromarray((out * 255).astype(np.uint8), "L").resize((atlas.shape[1] // 2, atlas.shape[0] // 2),
                                                               Image.BILINEAR).save(dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sets", nargs="+")
    args = ap.parse_args()
    for name in args.sets:
        print(f"→ {relief(name).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
