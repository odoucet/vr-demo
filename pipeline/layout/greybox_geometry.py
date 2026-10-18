"""Géométrie du greybox (J2), calculée à partir du tracé : terrain peint, arche des racines, roseaux, nénuphars, lucioles.
La forêt et les grands arbres sont dans pipeline/layout/vegetation.py.

    python pipeline/layout/greybox_geometry.py      # → pipeline/layout/greybox.json

Repère du tracé (mètres, x avant au départ, y gauche, z haut, eau à z = 0). Le script Unreal
(pipeline/unreal/scripts/greybox.py) convertit en centimètres et en repère Unreal (y inversé).
Couleurs du look peint : pipeline/style/look.yaml (couleurs par sommet, matériau M_Peint).
Déterministe (graine fixe).
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RIVER = ROOT / "pipeline" / "layout" / "river.json"
OUT = ROOT / "pipeline" / "layout" / "greybox.json"

GRID_M = 2.0   # ~50 k triangles (budget Quest : ≤ 500 k triangles visibles)
ARCH_HEIGHT_M = 8.0          # SUIVI.md D4 : arche à 8 m au-dessus de l'eau
LOOK = None


def look():
    """Couleurs propres du look peint (pipeline/style/look.yaml), sRGB 0-1."""
    global LOOK
    if LOOK is None:
        import yaml
        raw = yaml.safe_load((ROOT / "pipeline" / "style" / "look.yaml").read_text(encoding="utf-8"))
        hx = lambda h: [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]     # noqa: E731
        LOOK = {k: ([hx(c) for c in v] if isinstance(v, list) else hx(v)) for k, v in raw.items()}
    return LOOK


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mesh_dict(verts, tris, uv=None):
    d = {"vertices": np.round(np.asarray(verts, float), 3).tolist(), "triangles": np.asarray(tris, int).tolist()}
    if uv is not None:      # UV explicites (sinon projection plane à l'import) : ici, phase d'animation par objet
        d["uv"] = np.round(np.asarray(uv, float), 4).tolist()
    return d


def polyline_distance(px, py, xs, ys):
    """Distance de chaque point (px, py) à la polyligne (xs, ys) et indice du segment le plus proche."""
    best = np.full(px.shape, np.inf)
    idx = np.zeros(px.shape, int)
    for i in range(len(xs) - 1):
        ax, ay, bx, by = xs[i], ys[i], xs[i + 1], ys[i + 1]
        dx, dy = bx - ax, by - ay
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        d = np.hypot(px - (ax + t * dx), py - (ay + t * dy))
        closer = d < best
        best[closer], idx[closer] = d[closer], i
    return best, idx


def herd_crossing(river):
    """Gué du troupeau : point de traversée (14 m devant la barque à t = 112 s) et direction travers (vers la
    gauche). Partagé par le terrain (sentier creusé dans les berges), la végétation (dégagée) et les clés des
    animaux (pipeline/layout/creatures.py)."""
    m = next(x for x in river["landmarks"] if x["id"] == "troupeau-gue")
    p = min(river["samples"], key=lambda q: abs(q["t"] - m["t"]))
    h = math.radians(p["heading_deg"])
    cx, cy = p["x"] + m["ahead_m"] * math.cos(h), p["y"] + m["ahead_m"] * math.sin(h)
    return cx, cy, -math.sin(h), math.cos(h)


ABYSS_PIT_T = 90.0     # fosse où plonge la créature des abysses, devant la barque (temps du tracé)


def terrain(river):
    s = river["samples"]
    xs, ys = np.array([p["x"] for p in s]), np.array([p["y"] for p in s])
    width, ts = np.array([p["width_m"] for p in s]), np.array([p["t"] for p in s])
    lake = river["lake"]
    marks = {m["id"]: m for m in river["landmarks"]}
    x0, x1 = xs.min() - 40, max(xs.max(), lake["x"] + lake["radius_m"]) + 40
    y0, y1 = min(ys.min(), lake["y"] - lake["radius_m"]) - 60, max(ys.max(), lake["y"] + lake["radius_m"]) + 60
    gx, gy = np.meshgrid(np.arange(x0, x1 + GRID_M, GRID_M), np.arange(y0, y1 + GRID_M, GRID_M))
    dist, seg = polyline_distance(gx, gy, xs, ys)
    d_river = dist - width[seg] / 2
    d_lake = np.hypot(gx - lake["x"], gy - lake["y"]) - lake["radius_m"]
    d = np.minimum(d_river, d_lake)
    t_near = ts[seg]

    # Profondeur du lit : 1,5 m ; 5 m en S3 (la créature passe dessous) ; 0,6 m au gué ; lac 3 m.
    def window(t, a, b, ramp=8.0):
        return smoothstep(a - ramp, a + ramp, t) * (1 - smoothstep(b - ramp, b + ramp, t))

    # Transitions douces entre zones : l'eau translucide laisse voir le fond, sans marches.
    # S3 : chenal profond dès 0:40 (la créature arrive de derrière la barque), fosse de 9 m devant où elle plonge.
    depth = 1.5 + 3.5 * window(t_near, 40, 92) - 0.9 * window(t_near, 100, 132)
    depth = depth + 4.0 * np.exp(-((t_near - ABYSS_PIT_T) / 4.0) ** 2) * smoothstep(-2, -6, d)
    lake_w = smoothstep(-6, 6, d_river - d_lake)
    depth = depth * (1 - lake_w) + 3.0 * lake_w
    bed = -depth * smoothstep(0, 4, -d)
    # Berges : montée douce, puis sol de forêt ondulé.
    rng = np.random.default_rng(3)
    phase = rng.uniform(0, 2 * math.pi, 4)
    hills = (1.5 * np.sin(gx / 23 + phase[0]) * np.sin(gy / 19 + phase[1]) + 1.0 * np.sin(gx / 9 + phase[2]) * np.cos(gy / 11 + phase[3]))
    bank = 0.4 + 2.0 * smoothstep(0, 10, d) + np.clip(hills, 0, None) * smoothstep(10, 30, d)
    z = np.where(d < 0, bed, bank)
    # Sentier du troupeau : berges creusées en pente douce de part et d'autre du gué (6 m de large).
    hx, hy, ux, uy = herd_crossing(river)
    along = (gx - hx) * ux + (gy - hy) * uy            # distance le long de la traversée
    across = np.abs((gx - hx) * uy - (gy - hy) * ux)    # écart au sentier
    trail = smoothstep(4.0, 2.0, across)
    ramp = np.where(d < 0, z, 0.12 * np.maximum(d, 0) - 0.05)
    z = z * (1 - trail) + np.minimum(z, ramp) * trail
    # Île de l'arbre aux lanternes.
    isl = marks["ile-lanternes"]
    d_isl = np.hypot(gx - isl["x"], gy - isl["y"])
    z = np.where(d_isl < 11, np.maximum(z, 1.0 - 1.6 * smoothstep(6, 11, d_isl)), z)

    # Couleurs peintes : herbe en grandes plages de trois verts, terre nue près de l'eau, bande mouillée,
    # fond du lit ; alpha = occlusion (creux et pieds de berge plus sombres).
    L = look()
    g = [np.array(c) for c in L["herbe"]]
    w = (np.sin(gx / 17 + phase[1]) * np.cos(gy / 13 + phase[2]) + 0.5 * np.sin(gx / 6.5 + gy / 7.5)) * 0.5 + 0.5
    grass = np.where(w[..., None] < 0.45, g[2], np.where(w[..., None] < 0.75, g[0], g[1]))
    earth = np.array(L["terre"])
    col = grass * (1 - smoothstep(2.5, 0.6, d))[..., None] + earth * smoothstep(2.5, 0.6, d)[..., None]
    col = np.where((d < 0.4)[..., None], np.array(L["terre_mouillee"]), col)
    col = np.where((d < -0.6)[..., None], np.array(L["fond"]), col)
    ao = 0.55 + 0.45 * smoothstep(-1.0, 3.0, d) * (0.8 + 0.2 * np.clip(hills, 0, 1))
    colors = np.concatenate([col.reshape(-1, 3), ao.reshape(-1, 1)], axis=1)

    ny, nx = gx.shape
    verts = np.stack([gx.ravel(), gy.ravel(), z.ravel()], axis=1)
    i = np.arange(ny * nx).reshape(ny, nx)
    a, b, c, e = i[:-1, :-1].ravel(), i[:-1, 1:].ravel(), i[1:, :-1].ravel(), i[1:, 1:].ravel()
    tris = np.concatenate([np.stack([a, b, e], 1), np.stack([a, e, c], 1)])  # sens trigonométrique vu du dessus
    m = mesh_dict(verts, tris)
    m["colors"] = np.round(colors, 3).tolist()
    return m, {"x0": float(x0), "x1": float(x1), "y0": float(y0), "y1": float(y1)}, (gx, gy, d, z)


def tube_arch(center, heading, span, height, radius=1.4, seg=24, ring=10):
    """Arche en demi-ellipse enjambant la rivière, perpendiculaire au cap, pieds sur les berges."""
    cx, cy = center
    ux, uy = -math.sin(heading), math.cos(heading)       # travers (vers la gauche)
    fx, fy = math.cos(heading), math.sin(heading)        # avant
    verts, tris = [], []
    for k in range(seg + 1):
        a = math.pi * k / seg
        lat, up = span / 2 * math.cos(a), height * math.sin(a) + radius * 0.5
        dlat, dup = -span / 2 * math.sin(a), height * math.cos(a)   # tangente
        n = math.hypot(dlat, dup)
        nlat, nup = -dup / n, dlat / n                      # normale dans le plan de l'arche
        for r in range(ring):
            b = 2 * math.pi * r / ring
            off_plane, off_fwd = math.cos(b) * radius * (1.3 - 0.4 * math.sin(a)), math.sin(b) * radius * 1.6
            l, u = lat + nlat * off_plane, up + nup * off_plane
            verts.append([cx + ux * l + fx * off_fwd, cy + uy * l + fy * off_fwd, u - 1.0])
    for k in range(seg):
        for r in range(ring):
            p0, p1 = k * ring + r, k * ring + (r + 1) % ring
            q0, q1 = p0 + ring, p1 + ring
            tris += [[p0, q0, q1], [p0, q1, p1]]
    return mesh_dict(verts, tris)


def reeds(river, field, bounds, seed=5):
    """Roseaux (S2) : lames fines doubles le long des berges entre 0:12 et 0:52, et une touffe qui avance dans
    l'eau à gauche de 0:32 à 0:40 jusqu'à ~1,5 m de la trajectoire (« roseaux qui frôlent la barque »)."""
    gx, gy, d, z = field
    rng = np.random.default_rng(seed)
    s = [p for p in river["samples"] if 12 <= p["t"] <= 52]
    verts, tris = [], []

    def blade(x, y, z0, h, lean, ang):
        w = 0.035
        dx, dy = math.cos(ang) * w, math.sin(ang) * w
        lx, ly = math.cos(ang + 1.3) * lean, math.sin(ang + 1.3) * lean
        b = len(verts)
        verts.extend([[x - dx, y - dy, z0], [x + dx, y + dy, z0], [x + lx, y + ly, z0 + h]])
        tris.extend([[b, b + 1, b + 2], [b, b + 2, b + 1]])     # double face

    for p in s:
        h0 = math.radians(p["heading_deg"])
        nx, ny = -math.sin(h0), math.cos(h0)
        for side in (1, -1):
            for _ in range(40):
                off = side * (p["width_m"] / 2 + rng.uniform(-1.5, 2.5))
                if side == 1 and 32 <= p["t"] <= 40:
                    off = rng.uniform(1.5, p["width_m"] / 2 + 2)   # la touffe qui frôle, à gauche
                x = p["x"] + nx * off + rng.uniform(-0.5, 0.5)
                y = p["y"] + ny * off + rng.uniform(-0.5, 0.5)
                blade(x, y, -0.3, rng.uniform(1.1, 2.1), rng.uniform(0.05, 0.3), rng.uniform(0, 2 * math.pi))
    return mesh_dict(verts, tris)


def lily_pads(river, seed=9):
    """Nénuphars (S3) : disques posés sur l'eau entre 0:48 et 1:30, à plus de 2 m de la trajectoire."""
    rng = np.random.default_rng(seed)
    s = [p for p in river["samples"] if 48 <= p["t"] <= 90]
    verts, tris = [], []
    for p in s:
        h0 = math.radians(p["heading_deg"])
        nx, ny = -math.sin(h0), math.cos(h0)
        for _ in range(7):
            off = rng.choice([-1, 1]) * rng.uniform(2.0, p["width_m"] / 2 - 0.5)
            cx, cy, r = p["x"] + nx * off, p["y"] + ny * off, rng.uniform(0.25, 0.6)
            b = len(verts)
            verts.append([cx, cy, 0.03])
            for k in range(8):
                a = 2 * math.pi * k / 8
                verts.append([cx + r * math.cos(a), cy + r * math.sin(a), 0.03])
            tris.extend([[b, b + 1 + k, b + 1 + (k + 1) % 8] for k in range(7)])   # encoche : 7 secteurs sur 8
    return mesh_dict(verts, tris)


def octahedra(centers, size, rng):
    """Octaèdres (lucioles) ; les 6 sommets de chacun partagent un UV aléatoire = phase de vol et de clignotement
    lue par le matériau (dérive en WPO, aucun coût CPU)."""
    verts, tris, uv = [], [], []
    for c in centers:
        r = size * rng.uniform(0.6, 1.4)
        base = len(verts)
        verts += [c + d for d in (np.array(v) * r for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))]
        tris += [[base + a, base + b, base + c_] for a, b, c_ in
                 ((0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5))]
        uv += [rng.uniform(0, 1, 2).tolist()] * 6
    return mesh_dict(verts, tris, uv)


def fireflies(n=400, size=0.07, extent=(28.0, 22.0, 7.0), seed=11):
    """Nuage de lucioles, centré sur l'origine, animé par la séquence (envol de S5/S6)."""
    rng = np.random.default_rng(seed)
    return octahedra(rng.normal(0, 1, (n, 3)) * np.array(extent) / 3, size, rng)


def bank_fireflies(river, per_sample=2, size=0.06, seed=13):
    """Lucioles éparses au-dessus des berges et de l'eau près des rives, de S2 à la fin (0:20-4:00)."""
    rng = np.random.default_rng(seed)
    pts = []
    for p in river["samples"]:
        if p["t"] < 20 or p["t"] % 2:
            continue
        h0 = math.radians(p["heading_deg"])
        nx, ny = -math.sin(h0), math.cos(h0)
        for _ in range(per_sample * 2):
            off = rng.choice([-1, 1]) * (p["width_m"] / 2 + rng.uniform(-2.5, 4.0))
            pts.append([p["x"] + nx * off + rng.uniform(-1, 1), p["y"] + ny * off + rng.uniform(-1, 1),
                        rng.uniform(0.4, 2.8)])
    return octahedra(np.array(pts), size, rng)


def main():
    river = json.loads(RIVER.read_text(encoding="utf-8"))
    terrain_mesh, bounds, field = terrain(river)
    arch_mark = next(x for x in river["landmarks"] if x["id"] == "arche-racines")
    pose = min(river["samples"], key=lambda p: abs(p["t"] - arch_mark["t"]))
    data = {
        "units": "m", "axes": "x avant, y gauche, z haut (repère du tracé)", "bounds": bounds,
        "meshes": {
            "Terrain": terrain_mesh,
            "ArcheRacines": tube_arch((arch_mark["x"], arch_mark["y"]), math.radians(pose["heading_deg"]),
                                      span=pose["width_m"] + 10, height=ARCH_HEIGHT_M),
            "Lucioles": fireflies(),
            "LuciolesBerges": bank_fireflies(river),
            "Roseaux": reeds(river, field, bounds),
            "Nenuphars": lily_pads(river),
        },
    }
    # Couleur unique (look peint) pour les maillages sans couleurs par sommet ; alpha = occlusion.
    L = look()
    for name, key, ao in (("ArcheRacines", "ecorce_colossal", 0.8), ("Roseaux", "roseau", 0.9), ("Nenuphars", "nenuphar", 1.0)):
        data["meshes"][name]["color"] = L[key] + [ao]
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    for name, m in data["meshes"].items():
        print(f"  {name:15s} {len(m['vertices']):7d} sommets  {len(m['triangles']):7d} triangles")
    print(f"{OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
