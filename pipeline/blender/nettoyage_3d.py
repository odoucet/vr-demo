"""Reprises des modèles 3D reconstruits (TRELLIS.2) dans Blender, avant l'import Unreal. Script bpy, lancé par :

    python pipeline/blender/run.py pipeline/blender/nettoyage_3d.py               # tous les modèles de REPRISES
    python pipeline/blender/run.py pipeline/blender/nettoyage_3d.py barque        # un seul
    python pipeline/blender/run.py pipeline/blender/nettoyage_3d.py --analyse ponton   # morceaux séparés, sans rien écrire

Entrée : assets/3d/<id>/<source>/model.glb ; sortie : assets/3d/<id>/blender/model.glb (+ params.json), que greybox.py
importe à la place du modèle brut quand il existe. Idempotent : sauté si la source et les réglages n'ont pas changé.

Reprises possibles par modèle :
- « garder » : morceaux séparés du maillage à conserver. "principal" = le plus gros seul (les autres flottent : bancs de
  la barque, débris) ; un nombre = part minimale des sommets (0.01 = morceaux d'au moins 1 % du plus gros).
- « retirer_boites » : boîtes (repère du modèle importé, Z en haut) dont les morceaux contenus en entier sont retirés.
Les sommets dupliqués aux coutures UV sont soudés pour le calcul des morceaux seulement (l'UV et la texture restent).
"""
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy

VERSION = "nettoyage-v2"     # v2 : tangentes exportées

# Pourquoi chaque reprise : voir SUIVI.md (retours au casque).
REPRISES = {
    # Les deux bancs ne touchent pas la coque (26 cm de large dans une coque de 52) : vus de la place assise, ils flottent
    # (Olivier, 19/10 : « tu peux pas les enlever du modèle 3D ? »). Ce sont deux morceaux séparés, comme la boucle de
    # corde sous l'étrave (sous l'eau) : on ne garde que la coque.
    "barque": {"source": "trellis2-s42", "garder": "principal"},
    "ponton": {"source": "trellis2-s42", "garder": "principal"},          # un débris sous un pieu
    # Les autres : seulement les miettes (< 0,1 % du corps : éclats de reconstruction). Les petits morceaux plus gros
    # (glands de la lanterne, nageoires des abysses, détails de la tête) restent.
    "tete-couchee": {"source": "trellis2-s42", "garder": 0.001},
    "lanterne": {"source": "trellis2-s42", "garder": 0.001},
    "abysses": {"source": "trellis2-s42", "garder": 0.001},
    "fly": {"source": "trellis2-s42", "garder": 0.001},
    "troupeau": {"source": "trellis2-s42", "garder": 0.001},
}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = Path(argv[argv.index("--root") + 1])
    rest = [a for i, a in enumerate(argv) if a != "--root" and (i == 0 or argv[i - 1] != "--root")]
    analyse = "--analyse" in rest
    ids = [a for a in rest if not a.startswith("--")]
    return root, analyse, ids


def load(glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"{glb} : {len(meshes)} maillages, 1 attendu")
    return meshes[0]


def parts(obj):
    """Morceaux séparés : liste de listes d'indices de sommets, du plus gros au plus petit (coutures UV soudées)."""
    me = obj.data
    n = len(me.vertices)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    first = {}
    for v in me.vertices:                                   # même position = même sommet (coutures UV)
        key = (round(v.co.x * 1e4), round(v.co.y * 1e4), round(v.co.z * 1e4))
        if key in first:
            union(v.index, first[key])
        else:
            first[key] = v.index
    for e in me.edges:
        union(e.vertices[0], e.vertices[1])
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=len, reverse=True)


def bbox(obj, ids):
    cs = [obj.matrix_world @ obj.data.vertices[i].co for i in ids]
    return [min(c[k] for c in cs) for k in range(3)], [max(c[k] for c in cs) for k in range(3)]


def describe(obj, groups, limit=25):
    for ids in groups[:limit]:
        lo, hi = bbox(obj, ids)
        print(f"  {len(ids):7d} sommets  x {lo[0]:+.2f}..{hi[0]:+.2f}  y {lo[1]:+.2f}..{hi[1]:+.2f}  z {lo[2]:+.2f}..{hi[2]:+.2f}")
    if len(groups) > limit:
        print(f"  … {len(groups) - limit} autres morceaux")


def to_remove(obj, groups, rule):
    keep = rule.get("garder", 0.0)
    out = []
    for k, ids in enumerate(groups):
        if keep == "principal":
            drop = k > 0
        else:
            drop = len(ids) < keep * len(groups[0])
        for lo_b, hi_b in rule.get("retirer_boites", []):
            lo, hi = bbox(obj, ids)
            if all(lo_b[a] <= lo[a] and hi[a] <= hi_b[a] for a in range(3)):
                drop = True
        if drop:
            out.append(ids)
    return out


def remove(obj, groups):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    doomed = [bm.verts[i] for ids in groups for i in ids]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()


def main():
    root, analyse, ids = args()
    failed = False
    for mid in ids or list(REPRISES):
        rule = REPRISES.get(mid, {"source": "trellis2-s42"})
        src = root / "assets" / "3d" / mid / rule["source"] / "model.glb"
        if not src.exists():
            print(f"{mid} : source absente ({src}), sauté")
            continue
        out = root / "assets" / "3d" / mid / "blender"
        digest = hashlib.sha1(src.read_bytes()).hexdigest()[:12] + "-" + hashlib.sha1(
            (VERSION + json.dumps(rule, sort_keys=True)).encode()).hexdigest()[:8]
        params = out / "params.json"
        if not analyse and params.exists() and (out / "model.glb").exists() \
                and json.loads(params.read_text(encoding="utf-8")).get("digest") == digest:
            print(f"{mid} : à jour")
            continue
        obj = load(src)
        groups = parts(obj)
        print(f"{mid} : {len(obj.data.polygons)} faces, {len(groups)} morceaux")
        if analyse:
            describe(obj, groups)
            continue
        doomed = to_remove(obj, groups, rule)
        if doomed:
            print(f"  retirés : {len(doomed)} morceaux")
            describe(obj, doomed, limit=10)
        remove(obj, doomed)
        out.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(out / "model.glb"), export_format="GLB", export_image_format="AUTO",
                                  export_yup=True, export_apply=False, export_animations=False, export_tangents=True)
        faces = len(obj.data.polygons)
        params.write_text(json.dumps({"source": f"assets/3d/{mid}/{rule['source']}/model.glb", "digest": digest,
                                      "reprise": rule, "version": VERSION, "faces": faces,
                                      "morceaux_retires": len(doomed)}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  → assets/3d/{mid}/blender/model.glb ({faces} faces)")
    sys.exit(1 if failed else 0)


try:
    main()
except Exception as exc:                                    # code retour non nul pour build.py
    import traceback
    traceback.print_exc()
    print(f"ÉCHEC : {exc}")
    sys.exit(1)
