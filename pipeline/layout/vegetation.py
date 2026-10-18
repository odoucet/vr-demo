"""Végétation et décor peints (look J2-J3), générés depuis le tracé et le terrain du greybox.

    python pipeline/layout/vegetation.py      # → pipeline/layout/vegetation.json (régénérable, hors dépôt)

Contenu : feuillus en cumulus et résineux étagés (forêt dense, plus fine près de la rivière), lisière de
masses de feuillage en bord de terrain, buissons fleuris, touffes d'herbe et rochers sur les berges, gros
plans de collines lointains, arbre colossal (S5) avec ses racines, arbre aux lanternes (S7) et ses lanternes.
Chaque maillage porte normales et couleurs par sommet pour le matériau M_Peint (pipeline/layout/painted.py).
Découpé en tronçons le long du parcours (culling) ; budgets de triangles affichés. Déterministe.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

LAYOUT = Path(__file__).resolve().parent
ROOT = LAYOUT.parents[1]
sys.path.insert(0, str(LAYOUT))
import painted as P  # noqa: E402
from greybox_geometry import GRID_M, herd_crossing, terrain  # noqa: E402

OUT = LAYOUT / "vegetation.json"
LOOK = yaml.safe_load((ROOT / "pipeline" / "style" / "look.yaml").read_text(encoding="utf-8"))
COL = {k: ([P.hex_rgb(c) for c in v] if isinstance(v, list) else P.hex_rgb(v)) for k, v in LOOK.items()}
CHUNK_S = 30          # un tronçon par 30 s de parcours


class Field:
    """Terrain du greybox échantillonné : hauteur et distance à l'eau en un point."""

    def __init__(self, river):
        _, self.bounds, (self.gx, self.gy, self.d, self.z) = terrain(river)

    def at(self, x, y):
        j = int(round((y - self.bounds["y0"]) / GRID_M))
        i = int(round((x - self.bounds["x0"]) / GRID_M))
        if not (0 <= j < self.d.shape[0] and 0 <= i < self.d.shape[1]):
            return None, None
        return float(self.z[j, i]), float(self.d[j, i])


def main():
    river = json.loads((LAYOUT / "river.json").read_text(encoding="utf-8"))
    F = Field(river)
    b = F.bounds
    s = river["samples"]
    sx, sy, st = (np.array([p[k] for p in s]) for k in ("x", "y", "t"))
    marks = {m["id"]: m for m in river["landmarks"]}
    clearing = next(p for p in s if p["t"] >= 180)
    arch = marks["arche-racines"]
    arch_pose = min(s, key=lambda p: abs(p["t"] - arch["t"]))
    ah = math.radians(arch_pose["heading_deg"])
    colossal_xy = (arch["x"] - math.sin(ah) * 16, arch["y"] + math.cos(ah) * 16)
    isl = marks["ile-lanternes"]
    hx, hy, hux, huy = herd_crossing(river)
    rng = np.random.default_rng(17)

    chunks = {}

    def chunk(x, y):
        """Tronçon du point de parcours le plus proche (les objets d'un même passage sont regroupés)."""
        t = st[np.argmin((sx - x) ** 2 + (sy - y) ** 2)]
        k = f"Vegetation{int(t // CHUNK_S):02d}"
        return chunks.setdefault(k, P.Mesh())

    def path_dist(x, y):
        return float(np.sqrt(np.min((sx - x) ** 2 + (sy - y) ** 2)))

    def excluded(x, y):
        return (math.hypot(x - clearing["x"], y - clearing["y"]) < 30
                or math.hypot(x - colossal_xy[0], y - colossal_xy[1]) < 30
                or math.hypot(x - arch["x"], y - arch["y"]) < 14
                or math.hypot(x - isl["x"], y - isl["y"]) < 14
                or (abs((x - hx) * huy - (y - hy) * hux) < 5 and abs((x - hx) * hux + (y - hy) * huy) < 60))   # sentier du troupeau

    # --- Forêt : échantillonnage par cellules de 5 m, densité et détail selon la distance au parcours ---------
    trees = 0
    for x in np.arange(b["x0"], b["x1"], 5.0):
        for y in np.arange(b["y0"], b["y1"], 5.0):
            px, py = x + rng.uniform(0, 5), y + rng.uniform(0, 5)
            z, d = F.at(px, py)
            if z is None or d < 3.5 + rng.uniform(0, 3) or excluded(px, py):
                continue
            pd = path_dist(px, py)
            if pd > 45 and rng.uniform() < 0.55:      # au loin, la lisière (plus bas) prend le relais
                continue
            detail = 2 if pd < 16 else 1 if pd < 34 else 0
            h = rng.uniform(10, 20) * (1.15 if pd > 30 else 1.0)
            m = chunk(px, py)
            if rng.uniform() < 0.25:
                P.conifer(m, px, py, z, h * 1.1, rng, COL["resineux"][rng.integers(3)], COL["tronc"], detail=min(detail, 1))
            else:
                P.broadleaf_tree(m, px, py, z, h, rng, COL["feuillage"][rng.integers(5)], COL["tronc"], detail=detail)
            trees += 1

    # --- Lisière : masses de feuillage en bord de terrain, qui ferment le monde ---------------------------------
    edge = P.Mesh()
    for _ in range(420):
        side = rng.integers(4)
        u = rng.uniform()
        px = b["x0"] + (b["x1"] - b["x0"]) * (u if side < 2 else (0.02 if side == 2 else 0.98)) + rng.normal(0, 4)
        py = b["y0"] + (b["y1"] - b["y0"]) * ((0.02 if side == 0 else 0.98) if side < 2 else u) + rng.normal(0, 4)
        z, d = F.at(min(max(px, b["x0"]), b["x1"] - 1), min(max(py, b["y0"]), b["y1"] - 1))
        if z is None or (d is not None and d < 8):
            continue
        r = rng.uniform(6, 11)
        c = np.array([px, py, (z or 0) + rng.uniform(7, 15)])
        P.blob(edge, c, [r, r, r * 0.8], P.jitter(COL["feuillage"][rng.integers(5)] * 0.8, rng, 0.08), rng, subdiv=1,
               normal_center=c - [0, 0, r * 0.3], ao=(c[2] - r, c[2] + r, 0.45))
        P.cylinder(edge, [px, py, (z or 0) - 0.5], [px, py, c[2] - r * 0.5], 0.5, 0.35, COL["tronc"], sides=4)

    # --- Berges : herbe, buissons fleuris, rochers -------------------------------------------------------------
    for p in s:
        if p["t"] < 14:
            continue
        h0 = math.radians(p["heading_deg"])
        nx, ny = -math.sin(h0), math.cos(h0)
        for side in (1, -1):
            for _ in range(5):                                       # touffes d'herbe
                off = side * (p["width_m"] / 2 + rng.uniform(0.2, 7))
                px, py = p["x"] + nx * off + rng.uniform(-0.5, 0.5), p["y"] + ny * off + rng.uniform(-0.5, 0.5)
                z, d = F.at(px, py)
                if z is None or d < 0.2 or excluded(px, py):
                    continue
                P.grass_tuft(chunk(px, py), px, py, z, rng.uniform(0.35, 0.8), rng, COL["herbe"][rng.integers(3)])
            if rng.uniform() < 0.55:                                  # buisson
                off = side * (p["width_m"] / 2 + rng.uniform(1.5, 9))
                px, py = p["x"] + nx * off, p["y"] + ny * off
                z, d = F.at(px, py)
                if z is not None and d > 0.8 and not excluded(px, py):
                    fl = COL["fleurs"][rng.integers(4)] if rng.uniform() < 0.35 else None
                    P.bush(chunk(px, py), px, py, z, rng.uniform(0.9, 2.2), rng, COL["feuillage"][rng.integers(5)], fl)
            if rng.uniform() < 0.25:                                  # rocher au bord de l'eau
                off = side * (p["width_m"] / 2 + rng.uniform(-0.8, 1.5))
                px, py = p["x"] + nx * off, p["y"] + ny * off
                z, d = F.at(px, py)
                if z is not None and not excluded(px, py):
                    P.rock(chunk(px, py), px, py, max(z, -0.3), rng.uniform(0.4, 1.3), rng, COL["rocher"])

    # --- Gué (S4) : pierres plates en travers de la rivière, devant la barque, hors de sa trajectoire ---------
    ford = next(p for p in s if p["t"] >= 112)
    h0 = math.radians(ford["heading_deg"])
    for k in range(-6, 7):
        if abs(k) < 2:
            continue
        off = k * ford["width_m"] / 13
        px, py = ford["x"] + 18 * math.cos(h0) - math.sin(h0) * off, ford["y"] + 18 * math.sin(h0) + math.cos(h0) * off
        P.rock(chunk(px, py), px, py, -0.25, rng.uniform(0.5, 0.9), rng, COL["rocher"])

    # --- Arbre colossal (S5) : tronc évasé sur la berge gauche, contreforts de racines, houppier immense ----------
    colossal = P.Mesh()
    cx, cy = colossal_xy
    bark = COL["ecorce_colossal"]
    P.cylinder(colossal, [cx, cy, -1.5], [cx, cy, 34], 6.5, 4.0, bark, sides=14, ao_low=0.35)
    for k in range(9):                                                     # contreforts
        a = 2 * math.pi * k / 9 + rng.uniform(-0.2, 0.2)
        reach = rng.uniform(9, 15)
        P.cylinder(colossal, [cx + math.cos(a) * reach, cy + math.sin(a) * reach, -1.5],
                   [cx + math.cos(a) * 3, cy + math.sin(a) * 3, rng.uniform(7, 12)], 1.4, 2.6, P.jitter(bark, rng, 0.05),
                   sides=7, ao_low=0.35)
    crown_c = np.array([cx, cy, 52.0])
    P.blob(colossal, crown_c, [30, 30, 18], P.jitter(COL["feuillage"][1], rng), rng, subdiv=2, normal_center=crown_c,
           ao=(30, 72, 0.35))
    for _ in range(16):
        d = rng.normal(0, 1, 3)
        d[2] = d[2] * 0.4
        d /= np.linalg.norm(d)
        c = crown_c + d * np.array([26, 26, 14])
        r = rng.uniform(9, 15)
        P.blob(colossal, c, [r, r, r * 0.8], P.jitter(COL["feuillage"][rng.integers(5)], rng, 0.05), rng, subdiv=1,
               normal_center=crown_c, ao=(30, 72, 0.35))
    for k in range(6):                                                     # branches maîtresses
        a = 2 * math.pi * k / 6 + 0.3
        P.cylinder(colossal, [cx, cy, 30], [cx + math.cos(a) * 18, cy + math.sin(a) * 18, 44], 2.2, 1.0, bark, sides=6)

    # --- Arbre aux lanternes (S7) : large houppier en ombrelle sur l'île, lanternes suspendues dessous --------
    lantern = P.Mesh()
    lx, ly = isl["x"], isl["y"]
    P.cylinder(lantern, [lx, ly, 0.0], [lx, ly, 11], 1.6, 0.9, COL["tronc"], sides=10, ao_low=0.4)
    for k in range(5):
        a = 2 * math.pi * k / 5
        P.cylinder(lantern, [lx, ly, 8], [lx + math.cos(a) * 7, ly + math.sin(a) * 7, 13], 0.6, 0.3, COL["tronc"], sides=5)
    lc = np.array([lx, ly, 15.0])
    P.blob(lantern, lc, [12, 12, 6], P.jitter(COL["feuillage"][2], rng), rng, subdiv=2, normal_center=lc, ao=(9, 21, 0.35))
    for _ in range(12):
        d = rng.normal(0, 1, 3)
        d[2] *= 0.35
        d /= np.linalg.norm(d)
        c = lc + d * np.array([10, 10, 4])
        r = rng.uniform(4, 6.5)
        P.blob(lantern, c, [r, r, r * 0.7], P.jitter(COL["feuillage"][2], rng, 0.05), rng, subdiv=1,
               normal_center=lc, ao=(9, 21, 0.35))
    lanterns = []
    for i in range(48):                                                    # sous le houppier, sur ses bords
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(0.05, 1)) * 13
        lanterns.append([round(lx + r * math.cos(a), 2), round(ly + r * math.sin(a), 2),
                         round(10.5 - 2.5 * (r / 13) ** 2 + rng.uniform(-1.2, 1.5), 2)])

    # --- Collines lointaines : trois plans de reliefs arrondis autour de la scène (la brume les éclaircit) -----
    hills = P.Mesh()
    cxs, cys = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2
    for layer, (rad, col) in enumerate(zip((380, 600, 900), COL["collines"])):
        for k in range(22):
            a = 2 * math.pi * k / 22 + rng.uniform(-0.1, 0.1) + layer * 0.4
            r = rad * rng.uniform(0.9, 1.1)
            c = np.array([cxs + r * math.cos(a), cys + r * math.sin(a), -20])
            w = rad * rng.uniform(0.22, 0.32)
            P.blob(hills, c, [w, w * 0.8, rad * rng.uniform(0.10, 0.16)], P.jitter(col, rng, 0.04), rng, subdiv=2,
                   normal_center=c - [0, 0, 30], ao=(-20, rad * 0.2, 0.6), wobble=0.08)

    meshes = dict(sorted(chunks.items()))
    meshes.update({"Lisiere": edge, "ArbreColossalPeint": colossal, "ArbreLanternesPeint": lantern, "Collines": hills})
    total = 0
    for k, m in meshes.items():
        print(f"  {k:22s} {m.triangles:8d} triangles")
        total += m.triangles
    print(f"  {'total':22s} {total:8d} triangles ({trees} arbres)")
    OUT.write_text(json.dumps({"units": "m", "meshes": {k: m.to_dict() for k, m in meshes.items()},
                               "lanternes": lanterns}), encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
