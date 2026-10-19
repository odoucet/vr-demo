"""Estimation de la charge des sprites par caméra de revue, sans casque (comparaison entre versions).

    python pipeline/review/charge.py                 # tableau par caméra → review/charge.txt
    python pipeline/review/charge.py --sans-relief   # même calcul si le relief était coupé

Pour chaque caméra de pipeline/review/cameras.json : instances de pipeline/layout/sprites.json dans le champ (90° de
large, à peu près 60° de haut sur le Quest), en deçà de leur distance de culling (SPRITE_CULL de greybox.py), et
triangles correspondants (2 par plan, grille du relief : 6 × 12 cases pour les arbres, 6 × 6 pour les petits sujets).
Ce n'est pas une mesure : ni la brume, ni l'occultation, ni le coût des pixels. Sert à voir une régression avant de la
mesurer au casque (la scène y est limitée par la géométrie).
"""
import argparse
import json
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SPRITES = ROOT / "pipeline" / "layout" / "sprites.json"
CAMERAS = ROOT / "pipeline" / "review" / "cameras.json"
GREYBOX = ROOT / "pipeline" / "unreal" / "scripts" / "greybox.py"
ASPECT = {"buissons": 1.0, "fourres": 1.0, "faune": 1.0, "heros": 0.5}   # largeur / hauteur de case (arbres : 0,5)


def cull_table():
    m = re.search(r"SPRITE_CULL = (\{[^}]*\})", GREYBOX.read_text(encoding="utf-8"))
    return {k: v / 100.0 for k, v in eval(m.group(1)).items()}   # cm → m


def relief_tris(fam):
    rows = 6 if fam in ("buissons", "fourres", "faune") else 12
    nx = max(5, round(rows * ASPECT.get(fam, 0.5)) + 1)
    return (nx - 1) * rows * 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-relief", action="store_true")
    args = ap.parse_args()
    sets = json.loads(SPRITES.read_text(encoding="utf-8"))["sets"]
    cams = json.loads(CAMERAS.read_text(encoding="utf-8"))["cameras"]
    cull = cull_table()
    rows = []
    for cam in cams:
        yaw = math.radians(cam["yaw_deg"])
        fx, fy = math.cos(yaw), math.sin(yaw)
        n_inst = n_tri = n_rel = 0
        for key, spec in sets.items():
            fam = key.split("@")[0]
            a = np.array([i[:3] for i in spec["instances"]])
            dx, dy = a[:, 0] - cam["x"], a[:, 1] - cam["y"]
            dist = np.hypot(dx, dy)
            ahead = (dx * fx + dy * fy) / np.maximum(dist, 1e-3)
            lim = cull.get(fam, 100.0) or 1e9
            vis = (ahead > math.cos(math.radians(55))) & (dist < lim)   # 90° + marge pour la taille des sujets
            k = int(vis.sum())
            n_inst += k
            if spec["mode"] == "relief" and not args.sans_relief:
                n_tri += k * relief_tris(fam)
                n_rel += k
            else:
                n_tri += k * 2
        rows.append((cam["id"], n_inst, n_rel, n_tri))
    lines = [f"{'caméra':14s} {'sprites':>8s} {'en relief':>10s} {'triangles':>10s}"]
    lines += [f"{c:14s} {i:8d} {r:10d} {t:10d}" for c, i, r, t in rows]
    lines.append(f"{'max':14s} {max(r[1] for r in rows):8d} {max(r[2] for r in rows):10d} {max(r[3] for r in rows):10d}")
    text = "\n".join(lines)
    print(text)
    if not args.sans_relief:
        (ROOT / "review" / "charge.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
