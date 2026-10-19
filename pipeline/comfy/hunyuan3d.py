"""Image → forme 3D avec Hunyuan3D 2.1 (ComfyUI local, modèle Comfy-Org repackagé), pour comparer à TRELLIS.2.

    python pipeline/comfy/hunyuan3d.py refs/inbox/arche-statues.png      # → assets/3d/<nom>/hunyuan21-s<seed>/

Forme seule (pas de texture : Hunyuan3D 2.1 sous ComfyUI ne fait que la géométrie). Fond de l'image remplacé par du blanc
(masque BiRefNet de pipeline/style/projection.py s'il existe), octree 512 (256 dans le modèle d'exemple), maillage par
« surface net ». Sorties : model.glb, turntable_*.png et turntable.jpg (rendu « argile », même cadrage que image_to_3d.py).
Autorisé par Olivier le 19/10 (téléchargement du modèle, 6,9 Go).
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from comfy import client  # noqa: E402
from comfy.image_to_3d import YAWS, contact_sheet  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "3d"
MASKS = ROOT / "Unreal" / "Saved" / "import"


def workflow(image, seed, octree, prefix):
    api = {
        "1": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {"ckpt_name": "hunyuan_3d_v2.1.safetensors"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image}},
        "3": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 1.0}},
        "13": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["1", 1], "image": ["2", 0], "crop": "center"}},
        "6": {"class_type": "Hunyuan3Dv2Conditioning", "inputs": {"clip_vision_output": ["13", 0]}},
        "4": {"class_type": "EmptyLatentHunyuan3Dv2", "inputs": {"resolution": 4096, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["3", 0], "positive": ["6", 0], "negative": ["6", 1], "latent_image": ["4", 0],
                                                 "seed": seed, "steps": 30, "cfg": 5.0, "sampler_name": "euler", "scheduler": "normal",
                                                 "denoise": 1.0}},
        "8": {"class_type": "VAEDecodeHunyuan3D", "inputs": {"samples": ["7", 0], "vae": ["1", 2], "num_chunks": 8000, "octree_resolution": octree}},
        "9": {"class_type": "VoxelToMesh", "inputs": {"voxel": ["8", 0], "algorithm": "surface net", "threshold": 0.6}},
        "10": {"class_type": "SaveGLB", "inputs": {"mesh": ["9", 0], "filename_prefix": f"{prefix}/model"}},
    }
    for yaw in YAWS:
        api[f"cam{yaw}"] = {"class_type": "CreateCameraInfo",
                            "inputs": {"mode": "orbit", "mode.yaw": yaw, "mode.pitch": 20.0, "mode.distance": 2.6,
                                       "target_x": 0.0, "target_y": 0.0, "target_z": 0.0, "roll": 0.0,
                                       "fov": 35.0, "zoom": 1.0, "camera_type": "perspective"}}
        api[f"render{yaw}"] = {"class_type": "RenderMesh", "inputs": {"mesh": ["9", 0], "mode": "solid", "width": 1024, "height": 1024,
                                                                     "background": "#9a9a9a", "camera_info": [f"cam{yaw}", 0]}}
        api[f"save{yaw}"] = {"class_type": "SaveImage", "inputs": {"images": [f"render{yaw}", 0], "filename_prefix": f"{prefix}/turntable_{yaw:03d}"}}
    return api


def white_background(src, tmp):
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    mpath = MASKS / f"masque-{src.stem}.png"
    if mpath.exists():
        m = np.asarray(Image.open(mpath).convert("L").resize((rgb.shape[1], rgb.shape[0]))).astype(np.float32)[..., None] / 255.0
        rgb = rgb * m + 255.0 * (1.0 - m)
    side = max(rgb.shape[:2])
    canvas = np.full((side, side, 3), 255.0, np.float32)
    y0, x0 = (side - rgb.shape[0]) // 2, (side - rgb.shape[1]) // 2
    canvas[y0:y0 + rgb.shape[0], x0:x0 + rgb.shape[1]] = rgb
    dest = Path(tmp) / f"{src.stem}_blanc.png"
    Image.fromarray(canvas.astype(np.uint8), "RGB").save(dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--octree", type=int, default=512)
    args = ap.parse_args()
    for src in (Path(a).resolve() for a in args.images):
        out = OUT / src.stem / f"hunyuan21-s{args.seed}"
        out.mkdir(parents=True, exist_ok=True)
        prefix = f"barque/3d/{src.stem}-hunyuan21-s{args.seed}"
        t0 = time.time()
        with tempfile.TemporaryDirectory() as tmp, gpu_lock(f"hunyuan3d {src.stem}"):
            image = client.upload_image(white_background(src, tmp))
            entry = client.wait(client.submit(workflow(image, args.seed, args.octree, prefix)), timeout=3600)
        glb = client.output_files(entry, "10", "3d") or client.output_files(entry, "10", "images") or client.output_files(entry, "10", "files")
        if glb:
            client.download(glb[0], out / "model.glb")
        shots = []
        for yaw in YAWS:
            files = client.output_files(entry, f"save{yaw}", "images")
            if files:
                shots.append(client.download(files[0], out / f"turntable_{yaw:03d}.png"))
        if shots:
            contact_sheet(shots, out / "turntable.jpg", f"{src.stem} — Hunyuan3D 2.1 — octree {args.octree}")
        (out / "params.json").write_text(json.dumps({"source": str(src.relative_to(ROOT)), "model": "hunyuan_3d_v2.1.safetensors",
                                                     "seed": args.seed, "octree": args.octree, "seconds": round(time.time() - t0)},
                                                    indent=2), encoding="utf-8")
        print(f"{out.relative_to(ROOT)}  ({round(time.time() - t0)} s, GLB {'oui' if glb else 'non : ' + str(list(entry.get('outputs', {}).get('10', {}).keys()))})")


if __name__ == "__main__":
    main()
