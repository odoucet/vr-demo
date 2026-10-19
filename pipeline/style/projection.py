"""Images d'Olivier projetées sur la face avant de ses statues 3D (le détail peint que la reconstruction perd).

    python pipeline/style/projection.py      # → assets/textures/proj-<id>.png + assets/textures/proj-<id>.json

Pour chaque image de PROJECTIONS : silhouette du sujet (détourage BiRefNet dans ComfyUI), cadre de la silhouette en coordonnées d'image (u0, u1, v0, v1 : le matériau y fait correspondre la boîte du
modèle 3D), puis couleur du sujet prolongée sur le fond (pas de liseré de ciel au bord du volume). Une seule vue : la
reconstruction 3D a été faite depuis la même image, son repère est aligné sur elle (largeur = X, hauteur = Z).
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "textures"
PROJECTIONS = {"arche-statues": ROOT / "refs" / "inbox" / "arche-statues.png"}
GROUND_V = {"arche-statues": 0.93}       # hauteur relative du sol dans l'image (en dessous : bande de sable)
MASKS = ROOT / "Unreal" / "Saved" / "import"


def silhouette(src):
    """Masque du sujet (0-1) par BiRefNet (ComfyUI local, nœud RemoveBackground), mis en cache à côté des imports."""
    import sys
    sys.path.insert(0, str(ROOT / "pipeline"))
    from comfy import client
    dest = MASKS / f"masque-{src.stem}.png"
    if not dest.exists():
        wf = {"1": {"class_type": "LoadImage", "inputs": {"image": client.upload_image(src)}},
              "2": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}},
              "3": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
              "4": {"class_type": "MaskToImage", "inputs": {"mask": ["3", 0]}},
              "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": f"barque/proj/{src.stem}"}}}
        entry = client.wait(client.submit(wf), timeout=600)
        dest.parent.mkdir(parents=True, exist_ok=True)
        client.download(client.output_files(entry, "5", "images")[0], dest)
    return np.asarray(Image.open(dest).convert("L")).astype(np.float32) / 255.0


def main():
    for pid, src in PROJECTIONS.items():
        if not src.exists():
            continue
        rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
        subj = silhouette(src) > 0.5
        subj[int(subj.shape[0] * GROUND_V[pid]):] = False     # bande de sol de l'image (le socle s'y pose)
        lab, n = ndimage.label(subj)
        if n > 1:                                         # garde le plus grand morceau (le pont), pas le sol ni les collines
            sizes = ndimage.sum(subj, lab, range(1, n + 1))
            subj = lab == (int(np.argmax(sizes)) + 1)
        ys, xs = np.nonzero(subj)
        h, w = subj.shape
        # bas du cadre : sol de l'image (le socle s'y pose), pas la bande de sol elle-même
        box = {"u0": round(xs.min() / w, 4), "u1": round((xs.max() + 1) / w, 4),
               "v0": round(ys.min() / h, 4), "v1": round((ys.max() + 1) / h, 4)}
        _, (iy, ix) = ndimage.distance_transform_edt(~subj, return_indices=True)
        out = rgb[iy, ix]                                  # couleur du sujet prolongée sur le fond
        Image.fromarray(out.astype(np.uint8), "RGB").save(OUT / f"proj-{pid}.png")
        (OUT / f"proj-{pid}.json").write_text(json.dumps(box), encoding="utf-8")
        print(f"→ assets/textures/proj-{pid}.png  cadre {box}")


if __name__ == "__main__":
    main()
