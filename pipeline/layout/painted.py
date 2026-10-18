"""Primitives du look peint (bibliothèque) : maillages avec normales choisies et couleurs par sommet.

Le rendu « dessin animé » ne passe pas par un filtre (pas de post-traitement sur Quest sans HDR mobile) mais
par le matériau M_Peint (pipeline/unreal/scripts/greybox.py) : ombrage en deux tons (lumière chaude, ombre
froide) à frontière douce, couleur = couleur du sommet, alpha du sommet = occlusion peinte. La forme peinte
vient donc surtout des normales : les feuillages ont des normales sphériques (un houppier entier s'éclaire
comme un seul nuage), les rochers des normales adoucies, les troncs des normales cylindriques.

Repère du tracé : mètres, x avant, y gauche, z haut. Couleurs en sRGB 0-1 (converties à l'import).
"""
import math

import numpy as np


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def jitter(rgb, rng, amount=0.06):
    """Variation de teinte et de valeur, comme des touches de peinture qui ne sont jamais identiques."""
    return np.clip(rgb * (1 + rng.uniform(-amount, amount)) + rng.uniform(-amount / 2, amount / 2, 3), 0, 1)


_ICO = {}


def icosphere(subdiv):
    """Sphère unité (sommets, triangles), mise en cache."""
    if subdiv in _ICO:
        return _ICO[subdiv]
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    verts = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(subdiv):
        mid, nf = {}, []

        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = verts[a] + verts[b]
                verts.append(p / np.linalg.norm(p))
                mid[k] = len(verts) - 1
            return mid[k]
        for a, b, c in f:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    _ICO[subdiv] = (np.array(verts), np.array(f, int))
    return _ICO[subdiv]


class Mesh:
    """Accumulateur : sommets, triangles (sens trigonométrique vu de l'extérieur), normales, couleurs RGBA."""

    def __init__(self):
        self.v, self.t, self.n, self.c = [], [], [], []
        self.count = 0

    def add(self, verts, tris, normals, colors):
        verts, normals = np.asarray(verts, float), np.asarray(normals, float)
        normals = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)
        colors = np.asarray(colors, float)
        if colors.ndim == 1:
            colors = np.tile(colors, (len(verts), 1))
        self.v.append(verts)
        self.n.append(normals)
        self.c.append(colors)
        self.t.append(np.asarray(tris, int) + self.count)
        self.count += len(verts)

    def extend(self, other):
        """Ajoute un autre Mesh (ses indices sont relatifs à lui-même)."""
        offset = self.count
        for v, t, n, c in zip(other.v, other.t, other.n, other.c):
            self.v.append(v)
            self.n.append(n)
            self.c.append(c)
            self.t.append(t + offset)
        self.count += other.count

    @property
    def triangles(self):
        return sum(len(t) for t in self.t)

    def to_dict(self):
        if not self.v:
            return {"vertices": [], "triangles": [], "normals": [], "colors": []}
        return {"vertices": np.round(np.concatenate(self.v), 3).tolist(),
                "triangles": np.concatenate(self.t).tolist(),
                "normals": np.round(np.concatenate(self.n), 3).tolist(),
                "colors": np.round(np.concatenate(self.c), 3).tolist()}


class Bundle:
    """Un Mesh par type de surface (feuillage, bois, sol, roche) : chaque type a son matériau et sa texture
    de détail. Les primitives écrivent dans le bon Mesh via part()."""
    KINDS = ("feuillage", "bois", "sol", "roche")

    def __init__(self):
        self.parts = {k: Mesh() for k in self.KINDS}

    @property
    def triangles(self):
        return sum(m.triangles for m in self.parts.values())


def part(mesh, kind):
    return mesh.parts[kind] if isinstance(mesh, Bundle) else mesh


def ao_vertical(z, z0, z1, low=0.45):
    """Occlusion peinte : sombre en bas (contre le sol, sous le houppier), pleine en haut."""
    return low + (1 - low) * np.clip((z - z0) / max(z1 - z0, 1e-6), 0, 1)


def blob(mesh, center, radii, color, rng, subdiv=1, normal_center=None, normal_blend=0.75, ao=(None, None, 0.5),
         wobble=0.12, kind="feuillage"):
    """Boule déformée. normal_center : centre des normales sphériques partagées (houppier entier) ; le mélange
    avec la normale propre de la boule garde un léger modelé de chaque touffe."""
    sv, sf = icosphere(subdiv)
    k = 1 + wobble * np.sin(sv @ rng.normal(0, 3, 3) + rng.uniform(0, 6.3))
    local = sv * np.asarray(radii) * k[:, None]
    verts = local + np.asarray(center)
    own = sv / np.asarray(radii)
    own /= np.linalg.norm(own, axis=1, keepdims=True)
    if normal_center is not None:
        shared = verts - np.asarray(normal_center)
        shared /= np.linalg.norm(shared, axis=1, keepdims=True)
        normals = normal_blend * shared + (1 - normal_blend) * own
    else:
        normals = own
    z0, z1, low = ao
    z0 = verts[:, 2].min() if z0 is None else z0
    z1 = verts[:, 2].max() if z1 is None else z1
    a = ao_vertical(verts[:, 2], z0, z1, low)
    colors = np.column_stack([np.tile(color, (len(verts), 1)), a])
    part(mesh, kind).add(verts, sf, normals, colors)


def cylinder(mesh, base, top, r0, r1, color, sides=7, ao_low=0.5, cap=False, kind="bois"):
    """Tronc conique à normales cylindriques (ombrage doux tout autour)."""
    base, top = np.asarray(base, float), np.asarray(top, float)
    axis = top - base
    axis_n = axis / np.linalg.norm(axis)
    u = np.cross(axis_n, [0, 0, 1] if abs(axis_n[2]) < 0.9 else [1, 0, 0])
    u /= np.linalg.norm(u)
    w = np.cross(axis_n, u)
    verts, normals, tris = [], [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        d = math.cos(a) * u + math.sin(a) * w
        verts += [base + d * r0, top + d * r1]
        normals += [d, d]
    for k in range(sides):
        a0, a1, b0, b1 = 2 * k, 2 * k + 1, 2 * ((k + 1) % sides), 2 * ((k + 1) % sides) + 1
        tris += [[a0, b0, b1], [a0, b1, a1]]
    if cap:
        verts.append(top)
        normals.append(axis_n)
        c = len(verts) - 1
        tris += [[2 * k + 1, 2 * ((k + 1) % sides) + 1, c] for k in range(sides)]
    verts = np.array(verts)
    a = np.where(np.arange(len(verts)) % 2 == 0, ao_low, 1.0)
    colors = np.column_stack([np.tile(color, (len(verts), 1)), a])
    part(mesh, kind).add(verts, tris, normals, colors)


# --- Végétation et décor -----------------------------------------------------------------------------------
def broadleaf_tree(mesh, x, y, z, height, rng, leaf, trunk, detail=1, crown_scale=1.0):
    """Feuillu peint : tronc + houppier en cumulus de touffes, normales sphériques partagées.
    detail 2 : arbre vu de près (touffes à 80 triangles) ; 1 : touffe principale fine, autres à 20 triangles ;
    0 : lointain (3-4 touffes à 20 triangles)."""
    crown_r = height * rng.uniform(0.28, 0.36) * crown_scale
    crown_c = np.array([x, y, z + height - crown_r * 0.9])
    crown_c[:2] += rng.normal(0, 0.04, 2) * height
    cylinder(mesh, [x, y, z - 0.3], [crown_c[0], crown_c[1], crown_c[2] - crown_r * 0.2],
             height * 0.035, height * 0.022, jitter(trunk, rng), sides=6 if detail else 4)
    n = (rng.integers(7, 11), rng.integers(5, 8), rng.integers(3, 5))[2 - detail]
    base_col = jitter(leaf, rng, 0.08)
    z_bottom, z_top = crown_c[2] - crown_r * 1.0, crown_c[2] + crown_r * 1.1
    blob(mesh, crown_c, [crown_r] * 3, base_col, rng, subdiv=1 if detail else 0, normal_center=crown_c,
         ao=(z_bottom, z_top, 0.4))
    for _ in range(n - 1):
        d = rng.normal(0, 1, 3)
        d[2] = d[2] * 0.6 - 0.15
        d /= np.linalg.norm(d)
        r = crown_r * rng.uniform(0.45, 0.7)
        c = crown_c + d * crown_r * rng.uniform(0.6, 0.85)
        blob(mesh, c, [r, r, r * 0.85], jitter(base_col, rng, 0.05), rng, subdiv=1 if detail >= 1 else 0,
             normal_center=crown_c, ao=(z_bottom, z_top, 0.4))
    if detail == 2:      # petites touffes en surface : silhouette en chou-fleur, comme les feuillages peints
        for _ in range(rng.integers(6, 10)):
            d = rng.normal(0, 1, 3)
            d[2] = abs(d[2]) * 0.8 - 0.1
            d /= np.linalg.norm(d)
            r = crown_r * rng.uniform(0.18, 0.3)
            c = crown_c + d * crown_r * rng.uniform(0.95, 1.15)
            blob(mesh, c, [r, r, r * 0.8], jitter(base_col, rng, 0.07), rng, subdiv=0, normal_center=crown_c,
                 ao=(z_bottom, z_top, 0.4))
    # branches visibles sous le houppier
    for _ in range((3, 2, 0)[2 - detail]):
        a = rng.uniform(0, 2 * math.pi)
        tip = crown_c + np.array([math.cos(a), math.sin(a), 0]) * crown_r * 0.7 - [0, 0, crown_r * 0.3]
        cylinder(mesh, [x, y, crown_c[2] - crown_r * 0.9], tip, height * 0.012, height * 0.005, jitter(trunk, rng), sides=4)
    return crown_c, crown_r


def conifer(mesh, x, y, z, height, rng, leaf, trunk, detail=1):
    """Résineux peint : 3 à 4 étages coniques, normales inclinées vers l'extérieur et le haut (ombrage en
    bandes douces, silhouette dentelée)."""
    sides = 9 if detail else 6
    cylinder(mesh, [x, y, z - 0.3], [x, y, z + height * 0.3], height * 0.03, height * 0.02, jitter(trunk, rng), sides=4)
    tiers = 4 if detail else 3
    col = jitter(leaf, rng, 0.08)
    for i in range(tiers):
        f = i / tiers
        z0 = z + height * (0.22 + 0.62 * f)
        r = height * 0.24 * (1 - 0.65 * f)
        h = height * (0.36 - 0.05 * i)
        verts, normals = [], []
        for k in range(sides):
            a = 2 * math.pi * k / sides + rng.uniform(-0.15, 0.15)
            rr = r * rng.uniform(0.85, 1.1)
            verts.append([x + rr * math.cos(a), y + rr * math.sin(a), z0 - rng.uniform(0, 0.12) * h])
            normals.append([math.cos(a), math.sin(a), 0.55])
        verts.append([x, y, z0 + h])
        normals.append([0, 0, 1])
        tris = [[k, (k + 1) % sides, sides] for k in range(sides)]
        a = [0.5] * sides + [1.0]
        colors = np.column_stack([np.tile(jitter(col, rng, 0.03), (sides + 1, 1)), a])
        part(mesh, "feuillage").add(verts, tris, normals, colors)


def bush(mesh, x, y, z, size, rng, leaf, flowers=None):
    """Buisson : 2 à 4 touffes basses, normales sphériques communes ; fleurs éventuelles en petites touches."""
    c = np.array([x, y, z + size * 0.35])
    col = jitter(leaf, rng, 0.08)
    for i in range(rng.integers(2, 5)):
        off = rng.normal(0, size * 0.35, 3) * [1, 1, 0.3]
        r = size * rng.uniform(0.35, 0.6)
        blob(mesh, c + off, [r, r, r * 0.75], jitter(col, rng, 0.04), rng, subdiv=0, normal_center=c - [0, 0, size * 0.3],
             normal_blend=0.8, ao=(z, z + size * 0.9, 0.35))
    if flowers is not None:
        for _ in range(rng.integers(3, 9)):
            d = rng.normal(0, 1, 3)
            d[2] = abs(d[2]) + 0.3
            d /= np.linalg.norm(d)
            p = c + d * size * 0.55
            blob(mesh, p, [0.06] * 3, jitter(flowers, rng, 0.05), rng, subdiv=0, ao=(None, None, 1.0), wobble=0, kind="sol")


def rock(mesh, x, y, z, size, rng, color, subdiv=1):
    """Rocher : boule aplatie, normales adoucies vers le haut (dessus clair, flancs dans l'ombre)."""
    r = np.array([size, size * rng.uniform(0.6, 0.9), size * rng.uniform(0.35, 0.6)])
    c = np.array([x, y, z + r[2] * 0.3])
    blob(mesh, c, r, jitter(color, rng, 0.06), rng, subdiv=subdiv, normal_center=c - [0, 0, size * 0.6], normal_blend=0.6,
         ao=(z - r[2] * 0.2, z + r[2] * 1.2, 0.45), wobble=0.22, kind="roche")


def grass_tuft(mesh, x, y, z, height, rng, color, blades=7):
    """Touffe d'herbe : lames triangulaires double face, normales vers le haut et l'extérieur (lumière franche)."""
    col = jitter(color, rng, 0.08)
    for _ in range(blades):
        ang = rng.uniform(0, 2 * math.pi)
        w = 0.05
        dx, dy = math.cos(ang) * w, math.sin(ang) * w
        lean = rng.uniform(0.05, 0.35) * height
        lx, ly = math.cos(ang + 1.57) * lean, math.sin(ang + 1.57) * lean
        h = height * rng.uniform(0.6, 1.1)
        p0 = [x - dx + rng.normal(0, 0.08), y - dy + rng.normal(0, 0.08), z - 0.05]
        p1 = [p0[0] + 2 * dx, p0[1] + 2 * dy, p0[2]]
        p2 = [x + lx, y + ly, z + h]
        nrm = [math.cos(ang + 1.57) * 0.5, math.sin(ang + 1.57) * 0.5, 1]
        colors = np.array([[*col, 0.45], [*col, 0.45], [*col, 1.0]])
        part(mesh, "sol").add([p0, p1, p2], [[0, 1, 2]], [nrm] * 3, colors)     # matériau double face


def log(mesh, a, b, radius, rng, color):
    cylinder(mesh, a, b, radius, radius * 0.9, jitter(color, rng), sides=7, ao_low=0.55, cap=True)


def fern(mesh, x, y, z, size, rng, color, fronds=7):
    """Fougère : frondes arquées en éventail (deux segments), double face."""
    col = jitter(color, rng, 0.08)
    for k in range(fronds):
        a = 2 * math.pi * k / fronds + rng.uniform(-0.2, 0.2)
        dx, dy = math.cos(a), math.sin(a)
        L = size * rng.uniform(0.7, 1.1)
        w = L * 0.12
        px, py = -dy * w, dx * w
        p0 = [x, y, z]
        p1 = [x + dx * L * 0.55, y + dy * L * 0.55, z + L * 0.45]
        p2 = [x + dx * L, y + dy * L, z + L * 0.25]
        verts = [p0, [p1[0] + px, p1[1] + py, p1[2]], [p1[0] - px, p1[1] - py, p1[2]], p2]
        tris = [[0, 1, 2], [1, 3, 2]]                       # matériau double face : pas de faces dupliquées
        n = [dx * 0.3, dy * 0.3, 1]
        colors = np.array([[*col, 0.4], [*col, 0.8], [*col, 0.8], [*col, 1.0]])
        part(mesh, "sol").add(verts, tris, [n] * 4, colors)


def flower_patch(mesh, x, y, z, rng, color, stems=9, radius=0.5):
    """Massif de fleurs : tiges fines et têtes colorées (petites boules)."""
    for _ in range(stems):
        px, py = x + rng.normal(0, radius * 0.5), y + rng.normal(0, radius * 0.5)
        h = rng.uniform(0.25, 0.6)
        cylinder(mesh, [px, py, z - 0.02], [px, py, z + h], 0.01, 0.008, np.array([0.35, 0.5, 0.2]), sides=3, kind="sol")
        blob(mesh, [px, py, z + h], [0.05, 0.05, 0.035], jitter(color, rng, 0.05), rng, subdiv=0,
             ao=(None, None, 1.0), wobble=0, kind="sol")


def pebbles(mesh, x, y, z, rng, color, count=3, spread=0.8):
    for _ in range(count):
        s = rng.uniform(0.08, 0.25)
        rock(mesh, x + rng.normal(0, spread), y + rng.normal(0, spread), z - s * 0.2, s, rng, color, subdiv=0)


# --- Arbres instanciés à niveaux de détail (LOD) ---------------------------------------------------------------
# Un « plan » de houppier tiré une fois (troncs, touffes, petites touffes) puis construit à trois niveaux de détail :
# même silhouette générale, de plus en plus simplifiée. Les arbres sont posés en instances (variation de taille, de
# rotation et de teinte par instance), Unreal choisit le niveau selon la taille à l'écran.
PROTO_HEIGHT = 14.0


def broadleaf_plan(rng, leaf, trunk, height=PROTO_HEIGHT):
    crown_r = height * rng.uniform(0.29, 0.35)
    crown_c = np.array([rng.normal(0, 0.03) * height, rng.normal(0, 0.03) * height, height - crown_r * 0.9])
    col = jitter(leaf, rng, 0.06)
    plan = {"crown_c": crown_c, "crown_r": crown_r, "trunk": jitter(trunk, rng), "height": height, "blobs": [],
            "branches": []}
    plan["blobs"].append((crown_c, np.array([crown_r] * 3), col, 0))
    for _ in range(rng.integers(7, 10)):                                   # touffes principales
        d = rng.normal(0, 1, 3)
        d[2] = d[2] * 0.6 - 0.15
        d /= np.linalg.norm(d)
        r = crown_r * rng.uniform(0.45, 0.68)
        plan["blobs"].append((crown_c + d * crown_r * rng.uniform(0.6, 0.85), np.array([r, r, r * 0.85]),
                              jitter(col, rng, 0.05), 1))
    for _ in range(rng.integers(12, 16)):                                  # touffes de surface
        d = rng.normal(0, 1, 3)
        d[2] = abs(d[2]) * 0.8 - 0.15
        d /= np.linalg.norm(d)
        r = crown_r * rng.uniform(0.2, 0.32)
        plan["blobs"].append((crown_c + d * crown_r * rng.uniform(0.95, 1.12), np.array([r, r, r * 0.8]),
                              jitter(col, rng, 0.07), 2))
    for _ in range(rng.integers(22, 30)):                                  # petites touffes (gros plan seulement)
        d = rng.normal(0, 1, 3)
        d[2] = abs(d[2]) * 0.9 - 0.2
        d /= np.linalg.norm(d)
        r = crown_r * rng.uniform(0.08, 0.14)
        plan["blobs"].append((crown_c + d * crown_r * rng.uniform(1.1, 1.28), np.array([r, r, r * 0.8]),
                              jitter(col, rng, 0.09), 3))
    for _ in range(4):
        a = rng.uniform(0, 2 * math.pi)
        tip = crown_c + np.array([math.cos(a), math.sin(a), 0]) * crown_r * 0.75 - [0, 0, crown_r * 0.3]
        plan["branches"].append(tip)
    return plan


# par niveau : (subdivision des touffes de niveau 0..3 ou None si absentes, côtés du tronc, branches)
# (mesure au casque du 18/10 : la forêt instanciée coûtait 6,8 ms ; LOD1 allégé, LOD0 réservé aux arbres tout proches)
LOD_SPEC = {0: ((2, 1, 1, 0), 8, True), 1: ((1, 0, 0, None), 6, True), 2: ((0, 0, None, None), 4, False)}


def build_broadleaf(mesh, plan, lod):
    subs, sides, branches = LOD_SPEC[lod]
    c, r, h = plan["crown_c"], plan["crown_r"], plan["height"]
    z0, z1 = c[2] - r, c[2] + r * 1.2
    cylinder(mesh, [0, 0, -0.3], [c[0], c[1], c[2] - r * 0.2], h * 0.035, h * 0.022, plan["trunk"], sides=sides)
    rng = np.random.default_rng(7)                    # ondulation identique d'un niveau à l'autre
    blobs = plan["blobs"] if lod < 2 else plan["blobs"][:4]
    for center, radii, col, level in blobs:
        sd = subs[level]
        if sd is None:
            continue
        blob(mesh, center, radii, col, rng, subdiv=sd, normal_center=c, ao=(z0, z1, 0.4))
    if branches:
        for tip in plan["branches"]:
            cylinder(mesh, [0, 0, c[2] - r * 0.9], tip, h * 0.012, h * 0.005, plan["trunk"], sides=4)


def conifer_plan(rng, leaf, trunk, height=PROTO_HEIGHT):
    return {"height": height, "col": jitter(leaf, rng, 0.06), "trunk": jitter(trunk, rng),
            "jit": rng.uniform(-0.15, 0.15, 64), "drop": rng.uniform(0, 0.12, 64), "rr": rng.uniform(0.85, 1.1, 64)}


def build_conifer(mesh, plan, lod):
    """Résineux : étages à profil galbé (anneau extérieur dentelé, anneau intermédiaire, pointe)."""
    h = plan["height"]
    sides, tiers = {0: (16, 7), 1: (10, 5), 2: (6, 3)}[lod]
    cylinder(mesh, [0, 0, -0.3], [0, 0, h * 0.3], h * 0.03, h * 0.02, plan["trunk"], sides=4)
    for i in range(tiers):
        f = i / tiers
        z0 = h * (0.2 + 0.66 * f)
        r = h * 0.26 * (1 - 0.66 * f)
        th = h * (0.3 - 0.025 * i)
        verts, normals = [], []
        for k in range(sides):                                             # anneau extérieur
            a = 2 * math.pi * k / sides + plan["jit"][k]
            rr = r * plan["rr"][k] * (1.0 if k % 2 == 0 or lod == 2 else 0.84)
            verts.append([rr * math.cos(a), rr * math.sin(a), z0 - plan["drop"][k] * th])
            normals.append([math.cos(a), math.sin(a), 0.35])
        for k in range(sides):                                             # anneau intermédiaire
            a = 2 * math.pi * (k + 0.5) / sides
            verts.append([0.5 * r * math.cos(a), 0.5 * r * math.sin(a), z0 + th * 0.42])
            normals.append([math.cos(a), math.sin(a), 0.9])
        verts.append([0, 0, z0 + th])
        normals.append([0, 0, 1])
        tip = 2 * sides
        tris = []
        for k in range(sides):
            o0, o1, m0, mprev = k, (k + 1) % sides, sides + k, sides + (k - 1) % sides
            tris += [[o0, o1, m0], [o0, m0, mprev], [m0, sides + (k + 1) % sides, tip]]
        colors = np.column_stack([np.tile(plan["col"], (2 * sides + 1, 1)), [0.45] * sides + [0.8] * sides + [1.0]])
        part(mesh, "feuillage").add(verts, tris, normals, colors)
