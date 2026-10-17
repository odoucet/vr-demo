"""Vues manquantes d'un asset (étape 2 de l'image → 3D, CLAUDE.md) : Qwen-Image-Edit 2509 + LoRA « multiple angles ».

    python pipeline/comfy/views.py refs/barque.png                  # avant, gauche, arrière, droite
    python pipeline/comfy/views.py refs/barque.png --views left back

Sorties : assets/views/<nom>/<vue>.png + params.json (consignes, graine, empreinte de la source).
Les consignes sont celles du LoRA 2509 (en chinois) : rotation de caméra autour du sujet, sujet conservé.
Idempotent par empreinte de l'image source. Verrou GPU.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from comfy import client  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "views"
# Consignes du LoRA Qwen-Edit-2509-Multiple-angles. Rotation de caméra autour du sujet ; on demande en plus
# une vue orthogonale et un fond uni pour la reconstruction multi-vues.
VIEWS = {
    "front": "将镜头向左旋转90度，正面视角，纯浅灰色背景",
    "left": "将镜头向右旋转90度，侧面视角，纯浅灰色背景",
    "back": "将镜头旋转180度，背面视角，纯浅灰色背景",
    "right": "将镜头向左旋转90度，侧面视角，物体另一侧，纯浅灰色背景",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--views", nargs="+", choices=list(VIEWS), default=list(VIEWS))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    src = Path(args.image)
    digest = hashlib.sha1(src.read_bytes()).hexdigest()[:12]
    out = OUT / src.stem
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "params.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if meta.get("source_sha1") != digest:
        meta = {"source": str(src.resolve().relative_to(ROOT)), "source_sha1": digest, "seed": args.seed,
                "workflow": "pipeline/comfy/workflows/qwen_edit_2509_angle.json", "views": {}}
    with gpu_lock("views.py (Qwen-Image-Edit)"):
        image = client.upload_image(src)
        for view in args.views:
            dest = out / f"{view}.png"
            if dest.exists() and view in meta["views"]:
                continue
            wf = client.load_workflow("qwen_edit_2509_angle.json")
            wf["8"]["inputs"]["image"] = image
            wf["11"]["inputs"]["prompt"] = VIEWS[view]
            wf["13"]["inputs"]["seed"] = args.seed
            wf["15"]["inputs"]["filename_prefix"] = f"barque/views/{src.stem}_{view}"
            entry = client.wait(client.submit(wf), timeout=1800)
            client.download(client.output_files(entry, "15", "images")[0], dest)
            meta["views"][view] = VIEWS[view]
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
