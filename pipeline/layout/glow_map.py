"""Carte des lueurs vue de dessus, pour leur reflet dans l'eau la nuit (lue par le matériau de l'eau).

    python pipeline/layout/glow_map.py      # → assets/textures/eau_lueurs.png

Même emprise que la carte de l'eau (pipeline/layout/water_map.json). Canaux : R = plantes lumineuses de nuit (sprites
« nuit », sprites_layout.py), G = lucioles des berges, B = nuée finale du lac (greybox_geometry.py). Chaque source est
étalée en tache douce (~1,5 m). Le matériau de l'eau lit cette carte au point de la rive que touche le rayon réfléchi
(celui qui sert déjà au reflet de la lisière) : les lueurs y dessinent des traînées sur l'eau, une seule lecture de
plus. Retour d'Olivier (19/10) : l'eau paraissait terne. Déterministe.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

LAYOUT = Path(__file__).resolve().parent
ROOT = LAYOUT.parents[1]
sys.path.insert(0, str(LAYOUT))
from greybox_geometry import bank_fireflies, lake_fireflies  # noqa: E402

OUT = ROOT / "assets" / "textures" / "eau_lueurs.png"
N = 1024


def splat(points, weights, m, sigma_m):
    img = np.zeros((N, N), np.float32)
    for (x, y), w in zip(points, weights):
        i, j = int((y - m["y0"]) / m["size_m"] * N), int((x - m["x0"]) / m["size_m"] * N)
        if 0 <= i < N and 0 <= j < N:
            img[i, j] += w
    img = ndimage.gaussian_filter(img, sigma_m / m["size_m"] * N)
    return img


def main():
    river = json.loads((LAYOUT / "river.json").read_text(encoding="utf-8"))
    m = json.loads((LAYOUT / "water_map.json").read_text(encoding="utf-8"))
    sets = json.loads((LAYOUT / "sprites.json").read_text(encoding="utf-8"))["sets"]
    night = [i for k, v in sets.items() if k.split("@")[0] == "nuit" for i in v["instances"]]
    r = splat([(i[0], i[1]) for i in night], [i[3] for i in night], m, 1.5)
    banks = np.array(bank_fireflies(river)["vertices"])[::4]
    g = splat(banks[:, :2], np.ones(len(banks)), m, 1.5)
    lake = np.array(lake_fireflies(river)["vertices"])[::4]
    b = splat(lake[:, :2], np.ones(len(lake)), m, 1.5)
    rgb = []
    for ch in (r, g, b):
        top = np.percentile(ch[ch > 1e-6], 99) if (ch > 1e-6).any() else 1.0
        rgb.append(np.clip(ch / max(top, 1e-6), 0, 1))
    Image.fromarray((np.dstack(rgb) * 255).astype(np.uint8), "RGB").save(OUT)
    print(f"→ {OUT.relative_to(ROOT)} : {len(night)} plantes lumineuses, {len(banks)} lucioles des berges, "
          f"{len(lake)} lucioles du lac")


if __name__ == "__main__":
    main()
