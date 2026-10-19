"""Placement des sprites peints (pipeline/comfy/sprites.py) le long du parcours.

    python pipeline/layout/sprites_layout.py      # → pipeline/layout/sprites.json (lu par greybox.py)

Retour d'Olivier (18/10) : les arbres peints tournés vers l'œil « rendent vachement bien » ; la scène paraissait vide
et « low poly ». Les images peintes coûtent 2 triangles chacune : la forêt est redensifiée, les berges se garnissent de
buissons, fougères et fleurs, des bandes de lisière et de collines ferment l'horizon, les grands houppiers deviennent
des touffes peintes, des lotus et des pétales flottent.

Retour d'Olivier (19/10) : les sprites qui tournent avec la tête sont « trop bizarres », des arbres se rentrent dedans
selon l'orientation du regard. Tous les plans sont donc immobiles : leur orientation est calculée ici, une fois pour
toutes, vers le passage de la barque (voir facing()).

Modes (matériaux de greybox.py), tous immobiles :
- debout : plan vertical, pied au sol, tourné vers le passage de la barque (arbres, buissons, faune) ;
- relief : comme debout, mais grille creusée selon la carte de relief (pipeline/comfy/relief.py) : sujets proches du
           parcours, qui ont ainsi du volume en stéréo (RELIEF_M : distance maximale au parcours par famille) ;
- touffe : plan centré, tourné et incliné vers l'œil au passage (touffes des grands houppiers, vues d'en dessous) ;
- fixe   : plan vertical, pied au sol, orientation choisie au placement (bandes de lisière et de collines) ;
- sol    : plan horizontal posé sur l'eau (nénuphars, lotus, pétales).
Instance : [x, y, z, hauteur (m), case, cap (degrés, repère du tracé), éclat, inclinaison (degrés), miroir (0/1)].
Repère du tracé (m, x avant au départ, y gauche, z haut). Déterministe.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

LAYOUT = Path(__file__).resolve().parent
ROOT = LAYOUT.parents[1]
sys.path.insert(0, str(LAYOUT))
from greybox_geometry import herd_crossing  # noqa: E402
from vegetation import Field  # noqa: E402

OUT = LAYOUT / "sprites.json"
EYE = 1.1                     # hauteur des yeux au-dessus de l'eau (m)
RELIEF_M = {"arbres": 25, "arbres2": 25, "arbres3": 25, "arbres4": 25, "buissons": 12, "fourres": 12, "heros": 999,
            "faune": 999}
SPRITES = ROOT / "assets" / "textures" / "sprites"

# Choix des cases par usage : (famille, case, hauteur min, hauteur max, poids)
CONIFERS = [("arbres", 3), ("arbres", 7), ("arbres2", 3), ("arbres2", 7)]
# Retour d'Olivier (19/10) : les mêmes arbres revenaient trop souvent ; 16 feuillus de plus (arbres3, arbres4), deux
# voisins ne tirent pas le même arbre, et greybox.py retourne et teinte chaque image.
RIVERSIDE = [("arbres", 5), ("arbres2", 0), ("arbres2", 4), ("arbres", 4), ("arbres2", 5), ("arbres3", 3), ("arbres3", 7),
             ("arbres4", 2), ("arbres3", 2), ("arbres4", 6)]
BROADLEAF = [("arbres", 0), ("arbres", 1), ("arbres", 2), ("arbres", 6), ("arbres2", 1), ("arbres2", 2), ("arbres2", 6),
             ("arbres", 4), ("arbres3", 0), ("arbres3", 1), ("arbres3", 4), ("arbres3", 5), ("arbres3", 6), ("arbres4", 0),
             ("arbres4", 1), ("arbres4", 3), ("arbres4", 4), ("arbres4", 5), ("arbres4", 7), ("arbres3", 2)]
BANK = [("buissons", 0, 1.4, 2.4, 3), ("buissons", 1, 1.3, 2.1, 2), ("buissons", 2, 1.1, 1.7, 2), ("buissons", 3, 0.9, 1.4, 3),
        ("buissons", 4, 0.9, 1.4, 3), ("buissons", 6, 0.55, 0.9, 2), ("buissons", 7, 1.0, 1.5, 1), ("fourres", 0, 1.5, 2.3, 2),
        ("fourres", 2, 0.7, 1.0, 2), ("fourres", 3, 0.7, 1.0, 2), ("fourres", 5, 1.0, 1.7, 1), ("fourres", 6, 0.8, 1.1, 1),
        ("fourres", 7, 1.0, 1.5, 2)]
WATERLINE = [("buissons", 5, 1.3, 2.0, 3), ("fourres", 3, 0.7, 1.0, 1), ("buissons", 4, 0.9, 1.3, 1)]
FLOOR = [("buissons", 0, 1.6, 2.6, 3), ("buissons", 3, 1.0, 1.5, 3), ("fourres", 0, 1.6, 2.6, 2), ("fourres", 1, 3.0, 5.0, 2),
         ("fourres", 4, 2.5, 4.0, 2), ("fourres", 5, 1.2, 2.0, 1), ("fourres", 6, 0.9, 1.3, 1), ("buissons", 7, 1.1, 1.6, 1)]


def pick(rng, table):
    w = np.array([t[-1] for t in table], float)
    return table[rng.choice(len(table), p=w / w.sum())]


def main():
    river = json.loads((LAYOUT / "river.json").read_text(encoding="utf-8"))
    veg = json.loads((LAYOUT / "vegetation.json").read_text(encoding="utf-8"))
    F = Field(river)
    b = F.bounds
    s = river["samples"]
    sx, sy = np.array([p["x"] for p in s]), np.array([p["y"] for p in s])
    marks = {m["id"]: m for m in river["landmarks"]}
    clearing = next(p for p in s if p["t"] >= 180)
    arch = marks["arche-racines"]
    arch_pose = min(s, key=lambda p: abs(p["t"] - arch["t"]))
    ah = math.radians(arch_pose["heading_deg"])
    colossal_xy = (arch["x"] - math.sin(ah) * 16, arch["y"] + math.cos(ah) * 16)
    isl = marks["ile-lanternes"]
    lake = river["lake"]
    hx, hy, hux, huy = herd_crossing(river)
    pm = marks["ponton"]
    rng = np.random.default_rng(31)
    sets = {}

    def add(name, mode, inst):
        if name == "faune" and in_herd_path(inst[0], inst[1], 6.0):   # le troupeau passerait au travers
            return
        sets.setdefault(name, {"mode": mode, "instances": []})["instances"].append([round(float(v), 3) for v in inst] + [0.0, 0.0])

    last = {}

    def draw(table, key):
        """Tire un arbre de la table, différent du dernier tiré pour la même clé (voisins le long du parcours)."""
        while True:
            choice = table[rng.integers(len(table))]
            if choice != last.get(key) or len(table) == 1:
                last[key] = choice
                return choice

    def path_dist(x, y):
        return float(np.sqrt(np.min((sx - x) ** 2 + (sy - y) ** 2)))

    def excluded(x, y, big=False):
        r = 1.0 if big else 0.6                       # les petits sujets peuvent s'approcher davantage
        return (math.hypot(x - clearing["x"], y - clearing["y"]) < 30 * r
                or math.hypot(x - colossal_xy[0], y - colossal_xy[1]) < 22 * r
                or math.hypot(x - arch["x"], y - arch["y"]) < 12
                or math.hypot(x - isl["x"], y - isl["y"]) < 12
                or math.hypot(x - pm["x"], y - pm["y"]) < 6
                or in_herd_path(x, y))

    def in_herd_path(x, y, margin=4.0):              # couloir du troupeau au gué (S4)
        return abs((x - hx) * huy - (y - hy) * hux) < margin and abs((x - hx) * hux + (y - hy) * huy) < 60

    # --- Forêt : positions de vegetation.py, redensifiée au loin (les plans peints ne coûtent presque rien) --------
    for x, y, z, h, conifer in veg["forest"]:
        pd = path_dist(x, y)
        near_water = F.at(x, y)[1] is not None and F.at(x, y)[1] < 9
        table = CONIFERS if conifer else (RIVERSIDE if near_water and rng.uniform() < 0.6 else BROADLEAF)
        fam, cell = draw(table, "foret")
        add(fam, "debout", [x, y, z, h * rng.uniform(0.95, 1.1), cell, 0, rng.uniform(0.85, 1.05)])
        if pd > 40 and rng.uniform() < 0.8:          # rétablit la densité éclaircie pour la forêt 3D
            a, r = rng.uniform(0, 2 * math.pi), rng.uniform(2.2, 3.6)
            qx, qy = x + math.cos(a) * r, y + math.sin(a) * r
            qz, qd = F.at(qx, qy)
            if qz is not None and qd > 3 and not excluded(qx, qy, True):
                fam, cell = draw(CONIFERS if rng.uniform() < 0.25 else BROADLEAF, "dense")
                add(fam, "debout", [qx, qy, qz - 0.1, rng.uniform(11, 21), cell, 0, rng.uniform(0.8, 1.0)])

    # --- Premier rang d'arbres au bord de l'eau (cadre la rivière) et berges garnies ----------------------------
    for p in s:
        if p["t"] < 8:
            continue
        h0 = math.radians(p["heading_deg"])
        nx, ny = -math.sin(h0), math.cos(h0)
        for side in (-1, 1):
            edge = p["width_m"] / 2
            if p["t"] % 7 == (3 if side > 0 else 0):     # un arbre de berge tous les ~7 m de chaque côté
                off = side * (edge + rng.uniform(2.0, 4.5))
                x, y = p["x"] + nx * off + rng.uniform(-1, 1), p["y"] + ny * off + rng.uniform(-1, 1)
                z, d = F.at(x, y)
                if z is not None and d > 1.2 and not excluded(x, y, True):
                    fam, cell = draw(RIVERSIDE, ("berge", side))
                    add(fam, "debout", [x, y, z - 0.1, rng.uniform(8, 14), cell, 0, rng.uniform(0.9, 1.05)])
            for _ in range(3):                           # buissons, fougères, fleurs sur la berge (0,3 à 9 m de l'eau)
                off = side * (edge + 0.3 + 8.7 * rng.uniform() ** 1.5)
                x, y = p["x"] + nx * off + rng.uniform(-0.5, 0.5), p["y"] + ny * off + rng.uniform(-0.5, 0.5)
                z, d = F.at(x, y)
                if z is None or d < 0.25 or excluded(x, y):
                    continue
                fam, cell, h1, h2, _w = pick(rng, BANK)
                add(fam, "debout", [x, y, z - 0.05, rng.uniform(h1, h2), cell, 0, rng.uniform(0.85, 1.05)])
            if rng.uniform() < 0.55:                     # massettes et iris au ras de l'eau
                off = side * (edge + rng.uniform(-0.6, 0.5))
                x, y = p["x"] + nx * off, p["y"] + ny * off
                z, _d = F.at(x, y)
                if z is not None and not excluded(x, y):
                    fam, cell, h1, h2, _w = pick(rng, WATERLINE)
                    add(fam, "debout", [x, y, max(z, -0.25), rng.uniform(h1, h2), cell, 0, rng.uniform(0.85, 1.0)])

    # --- Sous-bois : entre les arbres, jusqu'à 45 m de la rivière ----------------------------------------------
    for _ in range(2600):
        p = s[rng.integers(len(s))]
        h0 = math.radians(p["heading_deg"])
        side = rng.choice([-1, 1])
        off = side * (p["width_m"] / 2 + rng.uniform(8, 45))
        x, y = p["x"] - math.sin(h0) * off + rng.uniform(-3, 3), p["y"] + math.cos(h0) * off + rng.uniform(-3, 3)
        z, d = F.at(x, y)
        if z is None or d < 6 or excluded(x, y):
            continue
        fam, cell, h1, h2, _w = pick(rng, FLOOR)
        add(fam, "debout", [x, y, z - 0.05, rng.uniform(h1, h2), cell, 0, rng.uniform(0.8, 1.0)])

    # --- Lisières et collines peintes : deux anneaux de bandes tournées vers la rivière -------------------------
    def strip_ring(lateral, height, cells, step, shift):
        for k, p in enumerate(s[int(shift)::step]):
            h0 = math.radians(p["heading_deg"])
            for side in (-1, 1):
                off = side * (p["width_m"] / 2 + lateral * rng.uniform(0.9, 1.1))
                x, y = p["x"] - math.sin(h0) * off, p["y"] + math.cos(h0) * off
                x = min(max(x, b["x0"] + 4), b["x1"] - 4)
                y = min(max(y, b["y0"] + 4), b["y1"] - 4)
                if math.hypot(x - lake["x"], y - lake["y"]) < lake["radius_m"] + 25 or path_dist(x, y) < 70:
                    continue
                z, _d = F.at(x, y)
                # face à la rivière (normale vers le point du tracé), légère rotation pour casser l'alignement
                yaw = math.degrees(math.atan2(p["y"] - y, p["x"] - x)) + rng.uniform(-12, 12)
                cell = cells[rng.integers(len(cells))]
                # collines et second anneau plus sombres et plus bleutés par la brume : ils reculent
                add("lisieres", "fixe", [x, y, (z or 0) - 4.0, height * rng.uniform(0.85, 1.15), cell, yaw,
                                          rng.uniform(0.6, 0.72) if (cell == 2 or lateral > 80) else rng.uniform(0.85, 1.0)])

    # un seul anneau, loin : à ~60 m, les bandes se voyaient comme des panneaux plats là où la forêt s'ouvre (gué, lac)
    strip_ring(120.0, 36.0, [0, 1, 2], 45, 10)
    # autour du lac : couronne de forêt et collines au loin (vue dégagée de S7)
    for k in range(16):
        a = 2 * math.pi * k / 16
        for dist, height, cells in ((lake["radius_m"] + 80, 38.0, [2, 0]),):
            x, y = lake["x"] + math.cos(a) * dist, lake["y"] + math.sin(a) * dist
            if not (b["x0"] < x < b["x1"] and b["y0"] < y < b["y1"]) or path_dist(x, y) < 70:
                continue
            z, _d = F.at(x, y)
            yaw = math.degrees(math.atan2(lake["y"] - y, lake["x"] - x))
            add("lisieres", "fixe", [x, y, (z or 0) - 4.0, height * rng.uniform(0.9, 1.1), cells[rng.integers(len(cells))], yaw, 0.7])

    # --- Grands houppiers : enveloppe remplie de touffes peintes (arbre colossal, arbre de l'île) ---------------
    # touffes face à l'œil dans toutes les directions : le houppier paraît plein sous tous les angles, même par en dessous
    for cx, cy, cz, rx, ry, rz, tree in veg.get("crowns", []):
        n_surf, n_core = (240, 50) if tree == "colossal" else (80, 16)
        for k in range(n_surf + n_core):
            d = rng.normal(0, 1, 3)
            d /= np.linalg.norm(d)
            r = rng.uniform(0.8, 1.02) if k < n_surf else rng.uniform(0.35, 0.65)
            x, y, z = cx + d[0] * rx * r, cy + d[1] * ry * r, cz + d[2] * rz * r
            size = (rx * rng.uniform(0.32, 0.48)) if k < n_surf else rx * rng.uniform(0.5, 0.7)
            top = d[2] > -0.2
            cell = int(rng.choice([0, 2, 4, 6]) if top and k < n_surf else rng.choice([1, 3, 5, 7] if d[2] < -0.5 else [1, 3]))
            bright = rng.uniform(0.9, 1.08) if top else rng.uniform(0.7, 0.85)
            add("feuillages", "touffe", [x, y, z, size, cell, 0, bright])

    # --- Arbre colossal : tronc peint face à l'œil (un tronc se voit pareil sous tous les angles), sommet caché dans
    # le houppier ; rochers géants moussus au bord de l'eau, souches géantes en lisière -------------------------
    gz = F.at(*colossal_xy)[0] or 0.0
    add("heros", "debout", [colossal_xy[0], colossal_xy[1], gz - 2.0, 42.0, 1, 0, 0.95])
    for t in (31, 57, 88, 101, 121, 158, 176, 195):
        p = min(s, key=lambda q: abs(q["t"] - t))
        h0 = math.radians(p["heading_deg"])
        o = rng.choice([-1, 1]) * (p["width_m"] / 2 + rng.uniform(-1.2, 0.5))
        x, y = p["x"] - math.sin(h0) * o, p["y"] + math.cos(h0) * o
        z, _d = F.at(x, y)
        if z is not None and not excluded(x, y):
            add("heros", "debout", [x, y, max(z, -0.9) - 0.4, rng.uniform(2.2, 3.6), 2, 0, rng.uniform(0.85, 0.95)])
    for t in (70, 168):
        p = min(s, key=lambda q: abs(q["t"] - t))
        h0 = math.radians(p["heading_deg"])
        o = rng.choice([-1, 1]) * (p["width_m"] / 2 + rng.uniform(5, 9))
        x, y = p["x"] - math.sin(h0) * o, p["y"] + math.cos(h0) * o
        z, d = F.at(x, y)
        if z is not None and d > 2 and not excluded(x, y):
            add("heros", "debout", [x, y, z - 0.2, rng.uniform(3.5, 4.5), 3, 0, 0.9])

    # --- Arbre colossal : rideaux de lianes tombant du houppier autour du tronc, mousses et fougères au pied -----
    cx, cy = colossal_xy
    for k in range(18):
        a = 2 * math.pi * k / 18 + rng.uniform(-0.15, 0.15)
        r = rng.uniform(6.5, 11.0)
        add("feuillages@debout", "debout", [cx + math.cos(a) * r, cy + math.sin(a) * r, rng.uniform(24.0, 30.0), rng.uniform(10.0, 15.0),
                                        7, 0, rng.uniform(0.7, 0.9)])
    for k in range(40):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(6.0, 13.0)
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        z, d = F.at(x, y)
        if z is None or d < 0.3:
            continue
        fam, cell, h1, h2 = [("fourres", 5, 1.4, 2.4), ("buissons", 3, 1.2, 1.8), ("fourres", 4, 3.0, 4.5), ("fourres", 6, 1.0, 1.4)][rng.integers(4)]
        add(fam, "debout", [x, y, z - 0.05, rng.uniform(h1, h2), cell, 0, rng.uniform(0.8, 0.95)])

    # --- Voûte : branches feuillues qui s'avancent au-dessus de l'eau (tronçons boisés), lianes qui pendent ------
    for p in s:
        if not (18 <= p["t"] <= 62 or 84 <= p["t"] <= 128 or 150 <= p["t"] <= 172):
            continue
        h0 = math.radians(p["heading_deg"])
        for side in (-1, 1):
            if rng.uniform() < 0.35:
                continue
            off = side * (p["width_m"] / 2 - rng.uniform(-1.0, 3.0))
            x, y = p["x"] - math.sin(h0) * off, p["y"] + math.cos(h0) * off
            if excluded(x, y, True):
                continue
            add("feuillages", "touffe", [x, y, rng.uniform(8.5, 14.0), rng.uniform(4.5, 8.0), int(rng.choice([0, 2, 4, 6, 5])), 0,
                                         rng.uniform(0.8, 1.0)])
            if rng.uniform() < 0.3:                     # rideau de lianes sous la branche, jusqu'à ~2 m de l'eau
                add("feuillages@debout", "debout", [x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), rng.uniform(1.8, 3.0),
                                                rng.uniform(5.0, 8.0), 7, 0, rng.uniform(0.8, 0.95)])

    # --- Sur l'eau : nénuphars, lotus, lentilles d'eau, feuilles et pétales peints vus de dessus ------------------
    WATER = [(0, 1.0, 1.8, 3), (1, 0.4, 0.7, 3), (2, 0.9, 1.5, 2), (3, 0.5, 1.0, 2), (4, 0.4, 0.7, 2), (5, 0.8, 1.4, 2),
             (6, 1.0, 1.7, 2), (7, 0.5, 0.8, 1)]
    wts = np.array([w[3] for w in WATER], float)
    pads = []                                        # (x, y, rayon) : deux plans à plat qui se recouvrent scintillent
    for _ in range(900):
        if rng.uniform() < 0.25:                     # lac : près des rives
            a, r = rng.uniform(0, 2 * math.pi), lake["radius_m"] * rng.uniform(0.55, 0.95)
            x, y = lake["x"] + math.cos(a) * r, lake["y"] + math.sin(a) * r
        else:                                        # rivière : plus dense dans le calme de S3 (0:48-1:30)
            p = s[rng.integers(len(s))] if rng.uniform() < 0.5 else min(s, key=lambda q: abs(q["t"] - rng.uniform(48, 90)))
            h0 = math.radians(p["heading_deg"])
            off = rng.choice([-1, 1]) * rng.uniform(2.0, max(p["width_m"] / 2 - 0.3, 2.1))
            x, y = p["x"] - math.sin(h0) * off, p["y"] + math.cos(h0) * off
        z, d = F.at(x, y)
        if z is None or z > -0.15 or path_dist(x, y) < 2.0:
            continue
        cell, s1, s2, _w = WATER[rng.choice(len(WATER), p=wts / wts.sum())]
        size = rng.uniform(s1, s2)
        r = size * 0.45
        if any(math.hypot(x - px, y - py) < r + pr for px, py, pr in pads):
            continue
        pads.append((x, y, r))
        add("eau", "sol", [x, y, 0.02 + 0.006 * (len(pads) % 5), size, cell, rng.uniform(0, 360), rng.uniform(0.85, 1.05)])

    # --- Faune des berges (sujets posés, aux moments du parcours où on les voit bien) ----------------------------
    def bank_spot(t, side, off):
        p = min(s, key=lambda q: abs(q["t"] - t))
        h0 = math.radians(p["heading_deg"])
        o = side * (p["width_m"] / 2 + off)
        x, y = p["x"] - math.sin(h0) * o, p["y"] + math.cos(h0) * o
        z, _d = F.at(x, y)
        return x, y, (z if z is not None else 0.0)

    for t, side in ((34, 1), (96, -1), (163, 1)):                    # cerfs qui boivent, au bord de l'eau
        x, y, z = bank_spot(t, side, rng.uniform(0.1, 0.6))
        add("faune", "debout", [x, y, max(z, -0.1), 1.45, 0, 0, 0.95])
    for t, side in ((52, -1), (118, 1)):                             # renards
        x, y, z = bank_spot(t, side, rng.uniform(1.5, 3.0))
        add("faune", "debout", [x, y, z, 0.75, 1, 0, 0.95])
    for t in (28, 44, 66, 103, 131, 146):                            # lapins
        x, y, z = bank_spot(t, rng.choice([-1, 1]), rng.uniform(1.5, 5.0))
        add("faune", "debout", [x, y, z, 0.38, 2, 0, 0.95])
    ducks = []                                                       # canards : nagent (vie animée, plus bas)
    sounds = {}                                                      # points d'émission des sons de faune (greybox.py)
    for t, n in ((40, 3), (72, 4), (88, 3), (198, 5)):
        x0, y0, _ = bank_spot(t, rng.choice([-1, 1]), -2.5)
        if in_herd_path(x0, y0, 9.0):
            continue
        sounds[f"canards-{t}"] = [x0, y0, 0.3]
        for _ in range(n):
            ducks.append((x0 + rng.uniform(-1.5, 1.5), y0 + rng.uniform(-1.5, 1.5)))
    for k in range(8):                                               # grenouilles près des nénuphars (S3)
        x, y, _z = bank_spot(rng.uniform(50, 88), rng.choice([-1, 1]), -rng.uniform(1.0, 3.0))
        add("faune", "debout", [x, y, 0.02, 0.16, 4, 0, 0.95])
    for t, side in ((58, 1), (80, -1)):                              # leur chœur, de part et d'autre
        x, y, _z = bank_spot(t, side, 1.0)
        sounds[f"grenouilles-{t}"] = [x, y, 0.3]
    add("faune", "debout", [pm["x"] + 0.4, pm["y"] - 0.2, 0.95, 0.28, 5, 0, 1.0])   # martin-pêcheur sur le ponton
    for t, side in ((150, -1), (172, 1)):                            # chouettes sur une souche (nuit)
        x, y, z = bank_spot(t, side, rng.uniform(2.0, 3.5))
        add("fourres", "debout", [x, y, z - 0.05, 1.0, 6, 0, 0.9])
        add("faune", "debout", [x, y, z + 0.62, 0.42, 6, 0, 0.95])
        sounds[f"chouette-{t}"] = [x, y, z + 0.8]
    for t in (58, 84, 110, 190):                                     # tortues au ras de l'eau
        x, y, z = bank_spot(t, rng.choice([-1, 1]), rng.uniform(-0.2, 0.3))
        add("faune", "debout", [x, y, max(z, -0.05), 0.22, 7, 0, 0.95])

    # --- Nuit (S6-S7) : champignons, fleurs et mousses lumineux sur les berges, au pied des grands arbres, autour
    # du lac ; éclat > 1,5 = lueur propre, allumée à la tombée de la nuit (VieJour) -----------------------------
    NIGHT = [(0, 0.5, 0.9, 3), (1, 0.7, 1.2, 2), (2, 0.6, 1.0, 2), (3, 0.9, 1.6, 1), (4, 0.5, 0.9, 2), (5, 0.9, 1.5, 2),
             (6, 1.0, 1.6, 1), (7, 0.8, 1.3, 2)]
    nw = np.array([n[3] for n in NIGHT], float)
    for _ in range(700):
        if rng.uniform() < 0.25:                         # rives du lac
            a = rng.uniform(0, 2 * math.pi)
            r = lake["radius_m"] + rng.uniform(0.5, 7.0)
            x, y = lake["x"] + math.cos(a) * r, lake["y"] + math.sin(a) * r
        elif rng.uniform() < 0.15:                       # pied de l'arbre colossal
            a, r = rng.uniform(0, 2 * math.pi), rng.uniform(7, 16)
            x, y = colossal_xy[0] + math.cos(a) * r, colossal_xy[1] + math.sin(a) * r
        else:                                            # berges, de l'arche au lac
            p = min(s, key=lambda q: abs(q["t"] - rng.uniform(132, 236)))
            h0 = math.radians(p["heading_deg"])
            off = rng.choice([-1, 1]) * (p["width_m"] / 2 + 0.3 + 4.0 * rng.uniform() ** 2.0)   # surtout au bord de l'eau
            x, y = p["x"] - math.sin(h0) * off, p["y"] + math.cos(h0) * off
        z, d = F.at(x, y)
        if z is None or d < 0.2 or (excluded(x, y) and math.hypot(x - colossal_xy[0], y - colossal_xy[1]) > 18):
            continue
        cell, h1, h2, _w = NIGHT[rng.choice(len(NIGHT), p=nw / nw.sum())]
        add("nuit", "debout", [x, y, z - 0.03, rng.uniform(h1, h2), cell, 0, rng.uniform(2.1, 2.6)])

    # --- Vie animée dans le shader (greybox.py, VIE_WPO_CODE) : [x, y, z, type, vitesse, rayon, phase] ----------
    # types : 0 héron (grand cercle lent, haut), 1 hirondelle (rase l'eau), 2 papillon, 3 libellule, 4-6 feuille, pétale,
    # feuille morte (tombent en boucle), 7 canard (nage en rond, image de la case 6). Centres le long du parcours, là où chaque animal a du sens.
    vie = []

    def along(t0, t1, n, lateral, z, typ, speed, radius):
        for _ in range(n):
            p = min(s, key=lambda q: abs(q["t"] - rng.uniform(t0, t1)))
            h0 = math.radians(p["heading_deg"])
            off = rng.choice([-1, 1]) * rng.uniform(*lateral)
            x, y = p["x"] - math.sin(h0) * off, p["y"] + math.cos(h0) * off
            zz = z if isinstance(z, float) else rng.uniform(*z)
            if lateral[1] > p["width_m"] / 2:                  # sur la berge : hauteur du terrain
                g = F.at(x, y)[0]
                zz += max(g or 0.0, 0.0)
            vie.append([x, y, zz, typ, rng.uniform(*speed), rng.uniform(*radius), rng.uniform()])

    along(22, 110, 4, (0, 30), (22.0, 34.0), 0, (0.04, 0.07), (25, 45))       # hérons
    along(60, 175, 14, (0, 5), (0.8, 3.0), 1, (0.35, 0.6), (5, 14))             # hirondelles au ras de l'eau
    along(25, 170, 46, (6, 12), (0.4, 1.8), 2, (0.15, 0.3), (1.0, 2.5))         # papillons sur les berges fleuries
    along(25, 200, 30, (2, 7), (0.3, 1.0), 3, (0.3, 0.6), (1.5, 4.0))           # libellules au-dessus de l'eau
    along(20, 230, 260, (3, 14), (7.0, 12.0), 4, (0.25, 0.5), (0.5, 1.0))       # feuilles qui tombent
    along(40, 120, 90, (3, 12), (6.0, 10.0), 5, (0.25, 0.45), (0.5, 1.0))       # pétales (cerisiers)
    along(120, 230, 120, (3, 14), (7.0, 12.0), 6, (0.25, 0.5), (0.5, 1.0))      # feuilles mortes
    for x, y in ducks:                                                         # canards : petits cercles, dans les deux sens
        vie.append([x, y, 0.0, 7, rng.choice([-1, 1]) * rng.uniform(0.12, 0.25), rng.uniform(0.6, 1.8), rng.uniform()])

    # --- Orientation des plans immobiles ------------------------------------------------------------------------
    st = np.array([p["t"] for p in s])
    beats = json.loads((ROOT / "pipeline" / "style" / "ambiance.json").read_text(encoding="utf-8"))["beats"]

    def sun_at(t):
        """Direction du soleil (repère du tracé) pendant le beat de l'instant t."""
        return next(b for b in reversed(beats) if b["debut_s"] <= t)["soleil_dir"]

    def facing(x, y, z):
        """Cap et inclinaison (degrés) d'un plan : il regarde l'œil au point du parcours situé un peu avant le plus
        proche, là où le sujet est vu à ~45° devant. De face en approchant, jamais vu par la tranche au passage ; deux
        voisins regardent presque le même point, leurs plans restent presque parallèles et ne se croisent pas."""
        d2 = (sx - x) ** 2 + (sy - y) ** 2
        i = int(np.argmin(d2))
        dist = math.sqrt(float(d2[i]) + (z - EYE) ** 2)
        j = int(np.argmin(np.abs(st - (st[i] - 0.8 * min(dist, 60.0)))))
        dx, dy, dz = sx[j] - x, sy[j] - y, EYE - z
        return math.degrees(math.atan2(dy, dx)), math.degrees(math.atan2(dz, math.hypot(dx, dy))), st[j]

    for spec in sets.values():
        if spec["mode"] not in ("debout", "touffe"):
            continue
        for inst in spec["instances"]:
            yaw, pitch, t_seen = facing(inst[0], inst[1], inst[2] + (0.0 if spec["mode"] == "touffe" else inst[3] * 0.5))
            inst[5] = round(yaw, 2)
            inst[7] = round(max(-70.0, min(70.0, pitch)), 2) if spec["mode"] == "touffe" else 0.0
            if spec["mode"] == "debout":
                # Les images sont peintes éclairées par la gauche ; sur le plan non retourné, ce côté apparaît à droite
                # de qui regarde. Miroir si le soleil (au moment où on voit le sujet) est de l'autre côté ; soleil
                # devant ou derrière : au hasard, pour la variété.
                d = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
                sun = sun_at(t_seen)
                side = -d[1] * sun[0] + d[0] * sun[1]           # > 0 : soleil à droite de qui regarde le sujet
                h = math.hypot(sun[0], sun[1]) or 1.0
                inst[8] = float(side / h < -0.25 or (abs(side / h) <= 0.25 and rng.uniform() < 0.5))

    # --- Sujets proches : versions en relief (mêmes données, grille creusée dans greybox.py) ---------------------
    for name in list(sets):
        spec = sets[name]
        if spec["mode"] != "debout" or name not in RELIEF_M:
            continue
        near = [i for i in spec["instances"] if path_dist(i[0], i[1]) < RELIEF_M[name]]
        if near:
            spec["instances"] = [i for i in spec["instances"] if path_dist(i[0], i[1]) >= RELIEF_M[name]]
            sets[f"{name}@relief"] = {"mode": "relief", "instances": near}
    sets = {k: v for k, v in sets.items() if v["instances"]}

    out = {"units": "m", "sons": {k: [round(float(c), 2) for c in v] for k, v in sounds.items()}, "sets": sets, "vie_animee": [[round(float(v), 3) for v in a] for a in vie]}
    OUT.write_text(json.dumps(out), encoding="utf-8")
    total = sum(len(v["instances"]) for v in sets.values())
    print(f"→ {OUT.relative_to(ROOT)} : {total} sprites, {len(vie)} animaux et feuilles animés")
    for k, v in sets.items():
        print(f"  {k:10s} {v['mode']:6s} {len(v['instances'])}")


if __name__ == "__main__":
    main()
