"""Végétation et décor peints (look J2-J3), générés depuis le tracé et le terrain du greybox.

    python pipeline/layout/vegetation.py      # → pipeline/layout/vegetation.json (régénérable, hors dépôt)

Contenu : feuillus en cumulus et résineux étagés (forêt dense, plus fine près de la rivière), lisière de
masses de feuillage en bord de terrain, buissons fleuris, touffes d'herbe et rochers sur les berges, gros
plans de collines lointains, arbre colossal (S5) avec ses racines, arbre aux lanternes (S7) et ses lanternes.
Chaque maillage porte normales et couleurs par sommet pour le matériau M_Peint (pipeline/layout/painted.py).
Découpé en tronçons le long du parcours (culling), et par type de surface (feuillage, bois, sol, roche :
un matériau et une texture de détail chacun) ; budgets de triangles affichés. Déterministe.
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
SPRITES = True       # forêt, lisière et grands houppiers en sprites peints (pipeline/layout/sprites_layout.py)
DETAIL_KEEP = (1.0, 0.45, 0.15)   # part des touffes gardée par niveau de détail des tronçons (mesure Quest du 18/10)


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
        return chunks.setdefault(k, P.Bundle())

    def path_dist(x, y):
        return float(np.sqrt(np.min((sx - x) ** 2 + (sy - y) ** 2)))

    def excluded(x, y):
        return (math.hypot(x - clearing["x"], y - clearing["y"]) < 30
                or math.hypot(x - colossal_xy[0], y - colossal_xy[1]) < 30
                or math.hypot(x - arch["x"], y - arch["y"]) < 14
                or math.hypot(x - isl["x"], y - isl["y"]) < 14
                or (abs((x - hx) * huy - (y - hy) * hux) < 5 and abs((x - hx) * hux + (y - hy) * huy) < 60))   # sentier du troupeau

    # --- Forêt : arbres instanciés (6 feuillus, 3 résineux, 3 niveaux de détail chacun), cellules de 4,2 m ----
    protos = {}
    for i in range(6):
        prng = np.random.default_rng(100 + i)
        protos[f"Feuillu{i}"] = ("feuillu", P.broadleaf_plan(prng, COL["feuillage"][i % 5], COL["tronc"]))
    for i in range(3):
        prng = np.random.default_rng(200 + i)
        protos[f"Resineux{i}"] = ("resineux", P.conifer_plan(prng, COL["resineux"][i], COL["tronc"]))
    instances = {k: [] for k in protos}
    trees = 0
    for x in np.arange(b["x0"], b["x1"], 4.2):
        for y in np.arange(b["y0"], b["y1"], 4.2):
            px, py = x + rng.uniform(0, 4.2), y + rng.uniform(0, 4.2)
            z, d = F.at(px, py)
            if z is None or d < 3.5 + rng.uniform(0, 3) or excluded(px, py):
                continue
            pd = path_dist(px, py)
            if pd > 45 and rng.uniform() < 0.55:      # au loin, la lisière (plus bas) prend le relais
                continue
            # au-delà de 65 m de la rivière, cachés par les premiers rangs et la brume : 7 sur 10 retirés (tirage
            # fixe par position, sans décaler les autres arbres), sauf autour du lac, vu de loin. Mesure Quest du
            # 18/10 : la forêt instanciée coûte ~5 ms par image, surtout par le nombre d'instances.
            far_lake = math.hypot(px - river["lake"]["x"], py - river["lake"]["y"]) > river["lake"]["radius_m"] + 70
            if pd > 65 and far_lake and (math.sin(px * 12.9898 + py * 78.233) * 43758.5453) % 1.0 < 0.7:
                continue
            h = rng.uniform(10, 20) * (1.15 if pd > 30 else 1.0)
            conifer = rng.uniform() < 0.25
            name = f"Resineux{rng.integers(3)}" if conifer else f"Feuillu{rng.integers(6)}"
            scale = h * (1.1 if conifer else 1.0) / P.PROTO_HEIGHT
            instances[name].append([round(px, 2), round(py, 2), round(z - 0.1, 2), round(float(rng.uniform(0, 360)), 1),
                                    round(scale * rng.uniform(0.95, 1.05), 3), round(scale, 3)])
            trees += 1
    # Positions des arbres : [x, y, z, hauteur (m), résineux]. En mode SPRITES (retour d'Olivier du 18/10 : les arbres
    # peints « rendent vachement bien »), la forêt est faite d'arbres peints posés par pipeline/layout/sprites_layout.py ;
    # sinon, forêt 3D instanciée à niveaux de détail (prototypes ci-dessous).
    forest = [[x, y, z, round(sz * P.PROTO_HEIGHT, 2), int(name.startswith("Resineux"))]
              for name, inst in instances.items() for x, y, z, _yaw, _sxy, sz in inst]
    prototypes = {}
    if SPRITES:
        instances = {}
    for name, (kind, plan) in ({} if SPRITES else protos).items():
        prototypes[name] = {}
        for lod in range(3):
            bnd = P.Bundle()
            (P.build_broadleaf if kind == "feuillu" else P.build_conifer)(bnd, plan, lod)
            prototypes[name][f"lod{lod}"] = {k: m.to_dict() for k, m in bnd.parts.items() if m.triangles}
        print(f"  {name:10s} LOD " + " / ".join(str(sum(len(m['triangles']) for m in prototypes[name][f'lod{l}'].values()))
                                                for l in range(3)) + f" triangles, {len(instances[name])} instances")

    # --- Lisière : masses de feuillage en bord de terrain, qui ferment le monde ---------------------------------
    edges = {}       # découpée en 8 morceaux (côté × moitié) : ce qui est hors du champ n'est plus traité par le GPU
    for _ in range(620):
        side = rng.integers(4)
        u = rng.uniform()
        edge = edges.setdefault(f"Lisiere{side}{int(u * 2)}", P.Bundle())
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

    rocks = []                                   # rochers 3D [x, y, taille] (écrits dans vegetation.json)
    # --- Berges : herbe, buissons fleuris, rochers -------------------------------------------------------------
    for p in s:
        if p["t"] < 14:
            continue
        h0 = math.radians(p["heading_deg"])
        nx, ny = -math.sin(h0), math.cos(h0)
        for side in (1, -1):
            for _ in range(4):                                       # fougères et massifs de fleurs
                off = side * (p["width_m"] / 2 + rng.uniform(1.0, 9))
                px, py = p["x"] + nx * off + rng.uniform(-0.5, 0.5), p["y"] + ny * off + rng.uniform(-0.5, 0.5)
                z, d = F.at(px, py)
                if z is None or d < 0.6 or excluded(px, py):
                    continue
                if SPRITES:                                            # fougères et fleurs peintes (sprites)
                    continue
                if rng.uniform() < 0.45:
                    P.fern(chunk(px, py), px, py, z, rng.uniform(0.5, 1.1), rng, COL["herbe"][rng.integers(3)] * 0.85)
                else:
                    P.flower_patch(chunk(px, py), px, py, z, rng, COL["fleurs"][rng.integers(4)])
            if rng.uniform() < 0.35:                                  # galets au bord de l'eau
                off = side * (p["width_m"] / 2 + rng.uniform(-0.6, 0.8))
                px, py = p["x"] + nx * off, p["y"] + ny * off
                z, d = F.at(px, py)
                if z is not None and not excluded(px, py):
                    P.pebbles(chunk(px, py), px, py, max(z, -0.2), rng, COL["rocher"])
            if rng.uniform() < 0.04:                                  # bois mort couché sur la berge
                # parallèle à la berge (jamais vers la rivière), sol mesuré aux deux bouts : il repose sur la
                # pente (retour d'Olivier : un tronc dépassait au-dessus de l'eau à 78 s)
                off = side * (p["width_m"] / 2 + rng.uniform(2.0, 6))
                px, py = p["x"] + nx * off, p["y"] + ny * off
                L = rng.uniform(2.5, 5)
                a = h0 + rng.uniform(-0.35, 0.35)
                qx, qy = px + math.cos(a) * L, py + math.sin(a) * L
                (za, da), (zb, db) = F.at(px, py), F.at(qx, qy)
                if (za is not None and zb is not None and min(da, db) > 1.2 and abs(za - zb) < 0.8
                        and not excluded(px, py) and not excluded(qx, qy)):
                    P.log(chunk(px, py), [px, py, za + 0.12], [qx, qy, zb + 0.12], rng.uniform(0.15, 0.3), rng, COL["tronc"])
            for _ in range(6 if SPRITES else 11):                    # touffes d'herbe (moins : herbes peintes)
                off = side * (p["width_m"] / 2 + rng.uniform(0.2, 9))
                px, py = p["x"] + nx * off + rng.uniform(-0.5, 0.5), p["y"] + ny * off + rng.uniform(-0.5, 0.5)
                z, d = F.at(px, py)
                if z is None or d < 0.2 or excluded(px, py):
                    continue
                P.grass_tuft(chunk(px, py), px, py, z, rng.uniform(0.35, 0.8), rng, COL["herbe"][rng.integers(3)])
            if rng.uniform() < 0.9:                                   # buisson
                off = side * (p["width_m"] / 2 + rng.uniform(1.5, 9))
                px, py = p["x"] + nx * off, p["y"] + ny * off
                z, d = F.at(px, py)
                if z is not None and d > 0.8 and not excluded(px, py) and not SPRITES:   # buissons peints en sprites
                    fl = COL["fleurs"][rng.integers(4)] if rng.uniform() < 0.55 else None
                    P.bush(chunk(px, py), px, py, z, rng.uniform(0.9, 2.2), rng, COL["feuillage"][rng.integers(5)], fl)
            if rng.uniform() < 0.25 and side > 0:                     # rocher au bord de l'eau, rive gauche (19/10 : inutiles à droite)
                off = side * (p["width_m"] / 2 + rng.uniform(-0.8, 1.5))
                px, py = p["x"] + nx * off, p["y"] + ny * off
                z, d = F.at(px, py)
                if z is not None and not excluded(px, py):
                    rs = rng.uniform(0.4, 1.3)
                    rocks.append([round(px, 2), round(py, 2), round(rs, 2)])     # les sprites les évitent (sprites_layout.py)
                    P.rock(chunk(px, py), px, py, max(z, -0.3), rs, rng, COL["rocher"])

    # --- Fleurs de nénuphar (S3) et roseaux du lac (S7) -----------------------------------------------------------
    for p in s:
        h0 = math.radians(p["heading_deg"])
        nx, ny = -math.sin(h0), math.cos(h0)
        if 48 <= p["t"] <= 92 and rng.uniform() < 0.8:
            off = rng.choice([-1, 1]) * rng.uniform(2.2, p["width_m"] / 2 - 0.4)
            px, py = p["x"] + nx * off, p["y"] + ny * off
            col = COL["fleurs"][1] if rng.uniform() < 0.7 else COL["fleurs"][0]
            m = chunk(px, py)
            for k in range(6):                                      # pétales en couronne autour d'un cœur
                a = 2 * math.pi * k / 6
                P.blob(m, [px + math.cos(a) * 0.09, py + math.sin(a) * 0.09, 0.1], [0.09, 0.05, 0.05],
                       P.jitter(col, rng, 0.04), rng, subdiv=0, ao=(None, None, 1.0), wobble=0, kind="sol")
            P.blob(m, [px, py, 0.14], [0.05] * 3, COL["fleurs"][2], rng, subdiv=0, ao=(None, None, 1.0), wobble=0, kind="sol")
    lake = river["lake"]
    for k in range(260):                                             # roseaux en touffes sur le pourtour du lac
        a = rng.uniform(0, 2 * math.pi)
        r = lake["radius_m"] + rng.uniform(-2.5, 1.5)
        px, py = lake["x"] + r * math.cos(a), lake["y"] + r * math.sin(a)
        if path_dist(px, py) < 6:
            continue
        z, d = F.at(px, py)
        P.grass_tuft(chunk(px, py), px, py, min(z if z is not None else 0, 0.1) if z is not None else -0.2,
                     rng.uniform(1.2, 2.2), rng, COL["roseau"], blades=9)

    # --- Gué (S4) : pierres plates en travers de la rivière, devant la barque, hors de sa trajectoire ---------
    ford = next(p for p in s if p["t"] >= 112)
    h0 = math.radians(ford["heading_deg"])
    for k in range(-6, 7):
        if abs(k) < 2:
            continue
        off = k * ford["width_m"] / 13
        px, py = ford["x"] + 18 * math.cos(h0) - math.sin(h0) * off, ford["y"] + 18 * math.sin(h0) + math.cos(h0) * off
        rs = rng.uniform(0.5, 0.9)
        rocks.append([round(px, 2), round(py, 2), round(rs, 2)])
        P.rock(chunk(px, py), px, py, -0.25, rs, rng, COL["rocher"])

    # --- Arbre colossal (S5) : tronc évasé sur la berge gauche, contreforts de racines, houppier immense ----------
    colossal = P.Bundle()
    cx, cy = colossal_xy
    bark = COL["ecorce_colossal"]
    if not SPRITES:                                       # en sprites : tronc peint face à l'œil (sprites_layout.py)
        P.cylinder(colossal, [cx, cy, -1.5], [cx, cy, 34], 6.5, 4.0, bark, sides=28, ao_low=0.35)
    for k in range(14):                                                    # écorce en côtes verticales
        a = 2 * math.pi * k / 14
        rib = P.jitter(bark, rng, 0.06)
        if not SPRITES:
            P.cylinder(colossal, [cx + math.cos(a) * 6.3, cy + math.sin(a) * 6.3, -1.5],
                       [cx + math.cos(a) * 3.9, cy + math.sin(a) * 3.9, 34], 0.9, 0.5, rib, sides=6, ao_low=0.4)
    for k in range(13):                                                    # contreforts
        a = 2 * math.pi * k / 9 + rng.uniform(-0.2, 0.2)
        reach = rng.uniform(9, 15)
        top_z, col_b = rng.uniform(7, 12), P.jitter(bark, rng, 0.05)
        if not SPRITES:
            P.cylinder(colossal, [cx + math.cos(a) * reach, cy + math.sin(a) * reach, -1.5],
                       [cx + math.cos(a) * 3, cy + math.sin(a) * 3, top_z], 1.4, 2.6, col_b, sides=12, ao_low=0.35)
    crown_c = np.array([cx, cy, 52.0])
    core = 0.7 if SPRITES else 1.0                  # en sprites : cœur plus petit, habillé de touffes peintes (sprites_layout)
    P.blob(colossal, crown_c, [30 * core, 30 * core, 18 * core], P.jitter(COL["feuillage"][1], rng), rng, subdiv=2,
           normal_center=crown_c, ao=(30, 72, 0.35))
    crowns = [[*crown_c.tolist(), 30.0, 30.0, 18.0, "colossal"]]   # enveloppes des grands houppiers (sprites)
    for i in range(60):                                                    # touffes, puis petites touffes en surface
        d = rng.normal(0, 1, 3)
        d[2] = d[2] * 0.4 if i < 24 else abs(d[2]) * 0.7 - 0.1
        d /= np.linalg.norm(d)
        c = crown_c + d * (np.array([26, 26, 14]) if i < 24 else np.array([31, 31, 18]))
        r = rng.uniform(9, 15) if i < 24 else rng.uniform(4, 7)
        col = P.jitter(COL["feuillage"][rng.integers(5)], rng, 0.05)
        if SPRITES:                                       # touffes peintes autour d'un cœur sombre (sprites_layout.py)
            pass                                          # touffes peintes posées par sprites_layout.py
        else:
            P.blob(colossal, c, [r, r, r * 0.8], col, rng, subdiv=2 if i < 24 else 1, normal_center=crown_c, ao=(30, 72, 0.35))
    for k in range(6):                                                     # branches maîtresses
        a = 2 * math.pi * k / 6 + 0.3
        if not SPRITES:
            P.cylinder(colossal, [cx, cy, 30], [cx + math.cos(a) * 18, cy + math.sin(a) * 18, 44], 2.2, 1.0, bark, sides=6)

    # --- Arbre aux lanternes (S7) : large houppier en ombrelle sur l'île, lanternes suspendues dessous --------
    lantern = P.Bundle()
    lx, ly = isl["x"], isl["y"]
    P.cylinder(lantern, [lx, ly, 0.0], [lx, ly, 11], 1.6, 0.9, COL["tronc"], sides=10, ao_low=0.4)
    for k in range(5):
        a = 2 * math.pi * k / 5
        P.cylinder(lantern, [lx, ly, 8], [lx + math.cos(a) * 7, ly + math.sin(a) * 7, 13], 0.6, 0.3, COL["tronc"], sides=5)
    lc = np.array([lx, ly, 15.0])
    lcore = 0.7 if SPRITES else 1.0
    P.blob(lantern, lc, [12 * lcore, 12 * lcore, 6 * lcore], P.jitter(COL["feuillage"][2], rng), rng, subdiv=2,
           normal_center=lc, ao=(9, 21, 0.35))
    crowns.append([*lc.tolist(), 12.5, 12.5, 6.0, "ile"])
    for i in range(40):
        d = rng.normal(0, 1, 3)
        d[2] = d[2] * 0.35 if i < 16 else abs(d[2]) * 0.6
        d /= np.linalg.norm(d)
        c = lc + d * (np.array([10, 10, 4]) if i < 16 else np.array([12.5, 12.5, 5.5]))
        r = rng.uniform(4, 6.5) if i < 16 else rng.uniform(1.8, 3)
        col = P.jitter(COL["feuillage"][2], rng, 0.05)
        if SPRITES:
            pass
        else:
            P.blob(lantern, c, [r, r, r * 0.7], col, rng, subdiv=1, normal_center=lc, ao=(9, 21, 0.35))
    lanterns = []
    for i in range(48):                                                    # sous le houppier, sur ses bords
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(0.05, 1)) * 13
        lanterns.append([round(lx + r * math.cos(a), 2), round(ly + r * math.sin(a), 2),
                         round(10.5 - 2.5 * (r / 13) ** 2 + rng.uniform(-1.2, 1.5), 2)])

    # --- Collines lointaines : trois plans de reliefs arrondis autour de la scène (la brume les éclaircit) -----
    hills = P.Bundle()
    cxs, cys = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2
    for layer, (rad, col) in enumerate(zip((380, 600, 900), COL["collines"])):
        for k in range(22):
            a = 2 * math.pi * k / 22 + rng.uniform(-0.1, 0.1) + layer * 0.4
            r = rad * rng.uniform(0.9, 1.1)
            c = np.array([cxs + r * math.cos(a), cys + r * math.sin(a), -20])
            w = rad * rng.uniform(0.22, 0.32)
            P.blob(hills, c, [w, w * 0.8, rad * rng.uniform(0.10, 0.16)], P.jitter(col, rng, 0.04), rng, subdiv=2,
                   normal_center=c - [0, 0, 30], ao=(-20, rad * 0.2, 0.6), wobble=0.08)

    bundles = dict(sorted(chunks.items()))
    if not SPRITES:                                       # remplacées par les bandes de lisière peintes
        bundles.update(dict(sorted(edges.items())))
        bundles["Collines"] = hills
    bundles["ArbreColossalPeint"] = colossal
    # arbre de l'île : en volume seulement sans l'image d'Olivier (20/10, style/ile_sprite.py → plan peint)
    if not (ROOT / "assets" / "textures" / "sprites" / "ile.json").exists():
        bundles["ArbreLanternesPeint"] = lantern
    meshes, total = {}, 0
    for k, bnd in bundles.items():
        print(f"  {k:22s} {bnd.triangles:8d} triangles  " +
              " ".join(f"{kind}={m.triangles}" for kind, m in bnd.parts.items() if m.triangles))
        total += bnd.triangles
        for kind, m in bnd.parts.items():
            if m.triangles:
                meshes[f"{k}_{kind}"] = m
    print(f"  {'total':22s} {total:8d} triangles hors arbres ({trees} arbres instanciés)")
    # herbe, fougères et fleurs des tronçons : 3 niveaux de détail (tous les groupes, DETAIL_KEEP[1], DETAIL_KEEP[2])
    out = {k: ({"lods": [m.to_dict(f) for f in DETAIL_KEEP]} if m.has_detail else m.to_dict()) for k, m in meshes.items()}
    OUT.write_text(json.dumps({"units": "m", "meshes": out,
                               "lanternes": lanterns, "prototypes": prototypes, "instances": instances,
                               "forest": forest, "crowns": crowns, "rochers": rocks}),
                   encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
