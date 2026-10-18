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


def ao_vertical(z, z0, z1, low=0.45):
    """Occlusion peinte : sombre en bas (contre le sol, sous le houppier), pleine en haut."""
    return low + (1 - low) * np.clip((z - z0) / max(z1 - z0, 1e-6), 0, 1)


def blob(mesh, center, radii, color, rng, subdiv=1, normal_center=None, normal_blend=0.75, ao=(None, None, 0.5),
         wobble=0.12):
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
    mesh.add(verts, sf, normals, colors)


def cylinder(mesh, base, top, r0, r1, color, sides=7, ao_low=0.5, cap=False):
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
    mesh.add(verts, tris, normals, colors)


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
    n = (rng.integers(7, 11), rng.integers(6, 10), rng.integers(3, 5))[2 - detail]
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
        blob(mesh, c, [r, r, r * 0.85], jitter(base_col, rng, 0.05), rng, subdiv=1 if detail == 2 else 0,
             normal_center=crown_c, ao=(z_bottom, z_top, 0.4))
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
        mesh.add(verts, tris, normals, colors)


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
            blob(mesh, p, [0.06] * 3, jitter(flowers, rng, 0.05), rng, subdiv=0, ao=(None, None, 1.0), wobble=0)


def rock(mesh, x, y, z, size, rng, color):
    """Rocher : boule aplatie, normales adoucies vers le haut (dessus clair, flancs dans l'ombre)."""
    r = np.array([size, size * rng.uniform(0.6, 0.9), size * rng.uniform(0.35, 0.6)])
    c = np.array([x, y, z + r[2] * 0.3])
    blob(mesh, c, r, jitter(color, rng, 0.06), rng, subdiv=1, normal_center=c - [0, 0, size * 0.6], normal_blend=0.6,
         ao=(z - r[2] * 0.2, z + r[2] * 1.2, 0.45), wobble=0.22)


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
        mesh.add([p0, p1, p2], [[0, 1, 2], [0, 2, 1]], [nrm] * 3, colors)


def log(mesh, a, b, radius, rng, color):
    cylinder(mesh, a, b, radius, radius * 0.9, jitter(color, rng), sides=7, ao_low=0.55, cap=True)
