"""Arbre de l'île du lac (image finale de la balade) : image d'Olivier détourée en plan peint unique (famille « ile »).

    python pipeline/style/ile_sprite.py      # refs/inbox/arbre-ile.png → assets/textures/sprite_ile.png + sprites/ile.json

Détourage BiRefNet (ComfyUI local, même outil que projection.py), plus gros morceau gardé (l'arbre, pas les buissons ni
l'herbe), bord adouci, cadre serré sur l'arbre ; couleur prolongée sous les zones transparentes (pas de liseré de ciel au
loin, mipmaps). Remplace dans le décor l'ancien arbre en volume (vegetation.py, sprites_layout.py) : posé debout, fixe,
tourné vers le parcours comme les autres héros. Idempotent : refait seulement si l'image source change.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
SRC = ROOT / "refs" / "inbox" / "arbre-ile.png"
ATLAS = ROOT / "assets" / "textures" / "sprite_ile.png"
META = ROOT / "assets" / "textures" / "sprites" / "ile.json"
HEIGHT = 1536                      # hauteur de la case (px)


def main():
    if not SRC.exists():
        print("arbre-ile.png absent : arbre en volume conservé")
        return
    digest = hashlib.sha1(SRC.read_bytes()).hexdigest()[:12]
    if META.exists() and ATLAS.exists() and json.loads(META.read_text(encoding="utf-8")).get("source_sha1") == digest:
        print("sprite_ile.png à jour")
        return
    from style.projection import silhouette
    from comfy.sprites import bleed
    rgb = np.asarray(Image.open(SRC).convert("RGB"))
    m = silhouette(SRC)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((rgb.shape[1], rgb.shape[0]))) / 255.0
    lab, n = ndimage.label(m > 0.5)
    if n > 1:                                              # l'arbre, pas les buissons détachés ni l'herbe
        sizes = ndimage.sum(m > 0.5, lab, range(1, n + 1))
        keep = ndimage.binary_dilation(lab == int(np.argmax(sizes)) + 1, iterations=6)
        m = m * keep
    # le nuage derrière la cime passe dans le détourage : grandes plages claires et peu vertes retirées (les lanternes,
    # claires aussi, sont de petites taches isolées et restent)
    f = rgb.astype(np.float32) / 255.0
    lum = f @ np.array([0.3, 0.59, 0.11])
    cloud = ((lum > 0.5) & (f[..., 2] > 0.35) & (f[..., 1] - f[..., 0] < 0.03)) \
        | ((lum > 0.25) & (f[..., 2] >= f[..., 1] - 0.02))                   # partie ombrée, gris-bleu
    lab, n = ndimage.label(ndimage.binary_closing(cloud, iterations=2))
    if n:
        sizes = ndimage.sum(cloud, lab, range(1, n + 1))
        big = np.isin(lab, np.nonzero(sizes > 3000)[0] + 1)
        m = m * (1.0 - ndimage.binary_dilation(big, iterations=3))
        m = ndimage.gaussian_filter(m, 0.8)
    ys, xs = np.nonzero(m > 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    pad = 8
    y0, x0 = max(y0 - pad, 0), max(x0 - pad, 0)
    y1, x1 = min(y1 + pad, rgb.shape[0]), min(x1 + pad, rgb.shape[1])
    rgba = np.dstack([rgb, (np.clip(m, 0, 1) * 255).astype(np.uint8)])[y0:y1, x0:x1]
    w = int(round(HEIGHT * (x1 - x0) / (y1 - y0) / 4)) * 4
    cell = np.asarray(Image.fromarray(rgba, "RGBA").resize((w, HEIGHT), Image.LANCZOS))
    ATLAS.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(bleed(cell.copy()), "RGBA").save(ATLAS)
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps({"cell": [w, HEIGHT], "grid": [1, 1], "type": "plant", "source_sha1": digest,
                                "source": "refs/inbox/arbre-ile.png (Olivier, Midjourney, prompt « arbre-ile »)",
                                "items": [{"name": "arbre-ile", "u0": 0.0, "u1": 1.0, "v0": 0.0, "v1": 1.0}]}, indent=1),
                    encoding="utf-8")
    print(f"→ {ATLAS.relative_to(ROOT)} ({w}×{HEIGHT}), {META.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
