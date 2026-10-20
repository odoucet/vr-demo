"""Carte de l'eau, vue de dessus, calculée sur le terrain du greybox (lue par le matériau de l'eau).

    python pipeline/layout/water_map.py      # → assets/textures/eau_carte.png + pipeline/layout/water_map.json

Canaux : R = cap du courant (cap du tracé le plus proche, ±45° encodés 0-1) ; G = distance à la rive droite (0-40 m
→ 0-1), A = 0,5 + distance à la rive gauche (0-40 m → 0,5-1 : jamais transparent, l'import PNG d'Unreal remplace
la couleur des pixels d'alpha nul), perpendiculairement au tracé (continues dans le lac : le matériau y passe par un fondu autour du rivage) ;
B = distance à la berge la plus proche dans l'eau (0 sur la rive, 1 à 8 m et plus). Le matériau s'en sert pour
faire couler les rides dans le sens du courant, poser l'écume le long des berges, foncer le chenal profond et
placer le reflet de la lisière (distance à la rive dans la direction du rayon réfléchi, une seule lecture). Emprise (repère du tracé, m) dans water_map.json. 1024 px de côté. Déterministe.
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
    # écart latéral au tracé (positif à gauche) → distances aux deux rives ; lac : 0 et 0 (courant presque nul)
    lat = -(gx - px[seg]) * np.sin(flow_h) + (gy - py[seg]) * np.cos(flow_h)
    # continues jusque dans le lac (20/10) : la mise à zéro dans le lac faisait une frontière nette (bissectrice rivière /
    # cercle), visible dans le reflet en ligne droite ; le matériau passe au lac par un fondu autour de son rivage
    d_left = np.clip(width[seg] / 2 - lat, 0, 40)
    d_right = np.clip(width[seg] / 2 + lat, 0, 40)
    img = np.stack([np.degrees(flow_h) / 90.0 + 0.5, d_right / 40.0, shore, 0.5 + d_left / 80.0], axis=-1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA").save(OUT)
    (LAYOUT / "water_map.json").write_text(json.dumps({"x0": b["x0"], "y0": b["y0"], "size_m": size}), encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({N}×{N}, {size:.0f} m de côté)")


if __name__ == "__main__":
    main()
