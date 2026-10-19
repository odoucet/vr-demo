"""Bouche les trous de la texture de couleur d'un modèle glTF (petits triangles noirs sur les reconstructions TRELLIS).

    python pipeline/comfy/glb_trous.py assets/3d/arche-statues-droite/trellis2-s42/model.glb [...]

Le dépliage UV de TRELLIS laisse des texels jamais cuits (noir pur) ; les triangles dont les coordonnées y tombent, ou le
filtrage au bord des îlots, sortent noirs. Chaque texel noir prend la couleur du texel cuit le plus proche (comme le
« bleed » des sprites), dans le PNG embarqué du GLB (c'est lui qu'Unreal importe) et dans tex_base_color.png à côté.
Idempotent : un GLB déjà traité est reconnu (marque dans « asset.extras »).
"""
import io
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

MARK = "barque-trous-bouches-v1"


def fill(img):
    a = np.asarray(img.convert("RGB"))
    hole = a.max(axis=2) < 12
    if not hole.any() or hole.all():
        return img, 0.0
    _, (iy, ix) = ndimage.distance_transform_edt(hole, return_indices=True)
    return Image.fromarray(a[iy, ix], "RGB"), float(hole.mean())


def fix_glb(path):
    b = path.read_bytes()
    magic, version, _ = struct.unpack("<III", b[:12])
    jlen, _ = struct.unpack("<II", b[12:20])
    j = json.loads(b[20:20 + jlen])
    if j.get("asset", {}).get("extras", {}).get(MARK):
        return None
    off = 20 + jlen
    blen, _ = struct.unpack("<II", b[off:off + 8])
    binary = bytearray(b[off + 8:off + 8 + blen])
    mat = j["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    img_idx = j["textures"][mat]["source"]
    bv = j["bufferViews"][j["images"][img_idx]["bufferView"]]
    start, length = bv.get("byteOffset", 0), bv["byteLength"]
    filled, share = fill(Image.open(io.BytesIO(bytes(binary[start:start + length]))))
    out = io.BytesIO()
    filled.save(out, "PNG")
    new = out.getvalue()
    delta = len(new) - length
    binary[start:start + length] = new
    bv["byteLength"] = len(new)
    for other in j["bufferViews"]:                         # vues placées après l'image : décalées
        if other is not bv and other.get("byteOffset", 0) > start:
            other["byteOffset"] += delta
    pad = (-len(binary)) % 4
    binary += b"\x00" * pad
    j["buffers"][0]["byteLength"] = len(binary)
    j.setdefault("asset", {}).setdefault("extras", {})[MARK] = True
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    path.write_bytes(struct.pack("<III", magic, version, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
                     + struct.pack("<II", len(binary), 0x004E4942) + bytes(binary))
    png = path.with_name("tex_base_color.png")
    if png.exists():
        fill(Image.open(png))[0].save(png)
    return share


def main():
    for p in map(Path, sys.argv[1:]):
        share = fix_glb(p)
        print(f"{p} : {'déjà traité' if share is None else f'{100 * share:.2f} % de texels noirs bouchés'}")


if __name__ == "__main__":
    main()
