"""Image → mesh 3D texturé (PBR) avec TRELLIS.2 ou Pixal3D, via ComfyUI local.

    python pipeline/comfy/image_to_3d.py refs/barque.png                       # les deux modèles
    python pipeline/comfy/image_to_3d.py refs/barque.png --models pixal3d --seed 7

Part du template officiel Comfy-Org (pipeline/comfy/workflows/3d_pixal3d_trellis2_image_to_model.ui.json),
converti en format API au lancement, puis ajusté : modèles bf16, texture 2048 (Quest), seeds fixes,
turntable 4 vues. Sorties dans assets/3d/<nom>/<modèle>-s<seed>/ : model.glb, textures PBR,
turntable_*.png et turntable.jpg (planche 2×2). Idempotent : un dossier déjà complet est sauté.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))

from comfy import client  # noqa: E402
from comfy.ui2api import convert  # noqa: E402
from gpu import gpu_lock  # noqa: E402

TEMPLATE = client.WORKFLOWS / "3d_pixal3d_trellis2_image_to_model.ui.json"
OUT = ROOT / "assets" / "3d"
MODELS = {"trellis2": "trellis_2_bf16.safetensors", "pixal3d": "pixal3d_bf16.safetensors"}
TEXTURES = {"164": "base_color", "207": "metallic", "208": "roughness", "226": "normal", "235": "occlusion"}
YAWS = (0, 90, 180, 270)


def reachable(api, info):
    """Ne garde que les nœuds nécessaires aux nœuds de sortie restants."""
    keep, stack = set(), [k for k, n in api.items() if info[n["class_type"]].get("output_node")]
    while stack:
        k = stack.pop()
        if k in keep or k not in api:
            continue
        keep.add(k)
        stack += [v[0] for v in api[k]["inputs"].values() if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)]
    return {k: v for k, v in api.items() if k in keep}


def build(info, image, model, seed, prefix, texture_size, decimate):
    api = convert(json.loads(TEMPLATE.read_text(encoding="utf-8")), info)
    for nid in ("246", "323"):  # aperçus intermédiaires de l'UI (structure voxel, couleurs par sommet)
        api.pop(nid, None)
    api["122"]["inputs"]["image"] = image
    api["316"]["inputs"]["value"] = model == "trellis2"
    api["40"]["inputs"]["unet_name"] = MODELS["trellis2"]
    api["319"]["inputs"]["unet_name"] = MODELS["pixal3d"]
    for i, nid in enumerate(("3", "18", "23", "12")):
        api[nid]["inputs"]["seed"] = seed + i
    api["288"]["inputs"]["value"] = texture_size
    api["186"]["inputs"]["target_face_count"] = decimate
    api["322"]["inputs"]["filename_prefix"] = f"{prefix}/model"
    for yaw in YAWS:
        # Le mesh sort normalisé dans un cube unité centré : distance 2 à 35° de champ cadre tout l'objet.
        api[f"cam{yaw}"] = {"class_type": "CreateCameraInfo",
                            "inputs": {"mode": "orbit", "mode.yaw": yaw, "mode.pitch": 20.0, "mode.distance": 2.0,
                                       "target_x": 0.0, "target_y": 0.0, "target_z": 0.0, "roll": 0.0,
                                       "fov": 35.0, "zoom": 1.0, "camera_type": "perspective"}}
        api[f"render{yaw}"] = {"class_type": "RenderMesh",
                               "inputs": {"mesh": ["260", 0], "mode": "texture", "width": 1024, "height": 1024,
                                          "background": "#9a9a9a", "camera_info": [f"cam{yaw}", 0]}}
        api[f"save{yaw}"] = {"class_type": "SaveImage",
                             "inputs": {"images": [f"render{yaw}", 0], "filename_prefix": f"{prefix}/turntable_{yaw:03d}"}}
    return reachable(api, info)


def contact_sheet(paths, dest, label):
    ims = [Image.open(p).convert("RGB").resize((512, 512)) for p in paths]
    sheet = Image.new("RGB", (1024, 1024 + 40), "#202020")
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % 2) * 512, 40 + (i // 2) * 512))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    ImageDraw.Draw(sheet).text((10, 10), label, fill="white", font=font)
    sheet.save(dest, quality=90)


def run(src, model, seed, texture_size, decimate, info):
    name = Path(src).stem
    out = OUT / name / f"{model}-s{seed}"
    if (out / "model.glb").exists() and (out / "turntable.jpg").exists():
        print(f"{out.relative_to(ROOT)} déjà présent, ignoré.")
        return out
    out.mkdir(parents=True, exist_ok=True)
    image = client.upload_image(src)
    prefix = f"barque/3d/{name}-{model}-s{seed}"
    api = build(info, image, model, seed, prefix, texture_size, decimate)
    t0 = time.time()
    entry = client.wait(client.submit(api), timeout=7200)
    outputs = entry["outputs"]

    glb = [f for v in outputs.get("322", {}).values() if isinstance(v, list) for f in v
           if isinstance(f, dict) and str(f.get("filename", "")).endswith(".glb")]
    if not glb:
        raise client.ComfyError(f"Pas de GLB dans les sorties : {json.dumps(outputs.get('322'))[:500]}")
    client.download(glb[0], out / "model.glb")
    for nid, tex in TEXTURES.items():
        files = client.output_files(entry, nid, "images")
        if files:
            client.download(files[0], out / f"tex_{tex}.png")
    shots = []
    for yaw in YAWS:
        files = client.output_files(entry, f"save{yaw}", "images")
        if files:
            shots.append(client.download(files[0], out / f"turntable_{yaw:03d}.png"))
    if len(shots) == 4:
        contact_sheet(shots, out / "turntable.jpg", f"{name} — {model} — seed {seed}")
    meta = {"source": str(Path(src).resolve().relative_to(ROOT)), "model": MODELS[model], "seed": seed,
            "texture_size": texture_size, "target_faces": decimate, "seconds": round(time.time() - t0),
            "workflow": str(TEMPLATE.relative_to(ROOT)), "script": "pipeline/comfy/image_to_3d.py"}
    (out / "params.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}  ({meta['seconds']} s, GLB {(out / 'model.glb').stat().st_size / 1e6:.1f} Mo)")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--models", nargs="+", choices=list(MODELS), default=list(MODELS))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--texture", type=int, default=2048)
    ap.add_argument("--faces", type=int, default=200000, help="faces visées après décimation")
    args = ap.parse_args()
    info = client.requests.get(f"{client.COMFY_URL}/object_info", timeout=60).json()
    with gpu_lock("image_to_3d.py (ComfyUI TRELLIS.2 / Pixal3D)"):
        for src in args.images:
            for model in args.models:
                run(src, model, args.seed, args.texture, args.faces, info)


if __name__ == "__main__":
    main()
