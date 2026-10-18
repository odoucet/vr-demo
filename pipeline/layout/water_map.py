"""Carte de l'eau, vue de dessus, calculée sur le terrain du greybox (lue par le matériau de l'eau).

    python pipeline/layout/water_map.py      # → assets/textures/eau_carte.png + pipeline/layout/water_map.json

Canaux : R, G = direction du courant (cap du tracé le plus proche, encodé 0-1) ; B = distance à la berge dans
l'eau (0 sur la rive, 1 à 8 m et plus) ; A = 1. Le matériau s'en sert pour faire couler les rides dans le sens
du courant, poser l'écume le long des berges, assombrir le reflet des arbres près des rives et foncer le
chenal profond. Emprise (repère du tracé, m) dans water_map.json. 1024 px de côté. Déterministe.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LAYOUT = Path(__file__).resolve().parent
ROOT = LAYOUT.parents[1]
sys.path.insert(0, str(LAYOUT))
from greybox_geometry import polyline_distance, terrain  # noqa: E402

OUT = ROOT / "assets" / "textures" / "eau_carte.png"
N = 1024


def main():
    river = json.loads((LAYOUT / "river.json").read_text(encoding="utf-8"))
    _, b, _ = terrain(river)
    size = max(b["x1"] - b["x0"], b["y1"] - b["y0"])
    xs = np.linspace(b["x0"], b["x0"] + size, N)
    ys = np.linspace(b["y0"], b["y0"] + size, N)
    gx, gy = np.meshgrid(xs, ys)
    s = river["samples"]
    px, py = np.array([p["x"] for p in s]), np.array([p["y"] for p in s])
    width = np.array([p["width_m"] for p in s])
    head = np.radians([p["heading_deg"] for p in s])
    dist, seg = polyline_distance(gx, gy, px, py)
    d_river = dist - width[seg] / 2
    lake = river["lake"]
    d_lake = np.hypot(gx - lake["x"], gy - lake["y"]) - lake["radius_m"]
    d = np.minimum(d_river, d_lake)
    shore = np.clip(-d / 8.0, 0, 1)
    flow_h = head[seg]
    # Lac : courant presque nul, direction tournante douce
    calm = d_lake < d_river
    fx, fy = np.cos(flow_h), np.sin(flow_h)
    fx = np.where(calm, fx * 0.25, fx)
    fy = np.where(calm, fy * 0.25, fy)
    img = np.stack([fx * 0.5 + 0.5, fy * 0.5 + 0.5, shore, np.ones_like(shore)], axis=-1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA").save(OUT)
    (LAYOUT / "water_map.json").write_text(json.dumps({"x0": b["x0"], "y0": b["y0"], "size_m": size}), encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({N}×{N}, {size:.0f} m de côté)")


if __name__ == "__main__":
    main()
