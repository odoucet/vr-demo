"""Textures peintes raccordables (look J3) : générées en local (Z-Image Turbo) pour celles qu'Olivier n'a pas
déposées dans refs/.

    python pipeline/comfy/textures.py                     # textures manquantes → assets/textures/<id>.png
    python pipeline/comfy/textures.py tex-ecorce --seed 3

Prompts : section « Textures » de PROMPTS.md (identifiant = nom de fichier). Si refs/<id>.png existe (dépôt
d'Olivier, ex. tex-mousse), c'est lui qui fait foi : copié tel quel, rien n'est généré. Les autres sont
repeintes à partir de la texture de mousse d'Olivier (référence de style) par Qwen-Image-Edit 2509 : même
gouache, mêmes touches, autre sujet (le texte seul donnait des textures trop « vectorielles »). Les images générées
sont rendues raccordables : moitié décalée, fondu radial avec l'original (bords issus du centre de l'image,
donc continus d'un bord à l'autre). 1024×1024. Idempotent par graine.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))
from comfy import client  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "textures"
SUFFIX = ", top-down orthographic view, evenly lit, no cast shadows, no perspective, hand-painted, tileable"
STYLE_REF = ROOT / "refs" / "tex-mousse.png"
EDIT = ("Repaint this image as a {subject}. Keep exactly the same painting style: soft gouache, the same brush "
        "strokes, the same level of detail and texture density. Seamless tileable texture, top-down, evenly lit, "
        "no cast shadows, filling the whole frame.")


def prompts():
    text = (ROOT / "PROMPTS.md").read_text(encoding="utf-8")
    section = text.split("## Textures", 1)[1].split("\n## ", 1)[0]
    return dict(re.findall(r"- `(tex-[a-z]+)` : `(.*?)`", section))


def make_tileable(path):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    h, w, _ = im.shape
    rolled = np.roll(im, (h // 2, w // 2), axis=(0, 1))
    y, x = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(x, w - 1 - x) / (w / 2), np.minimum(y, h - 1 - y) / (h / 2))
    wgt = np.clip((edge - 0.15) / 0.35, 0, 1)[..., None]      # centre : original ; bords : version décalée
    out = im * wgt + rolled * (1 - wgt)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    table = prompts()
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = OUT / "params.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    ids = args.ids or list(table)
    with gpu_lock("textures.py (Z-Image Turbo)"):
        for tid in ids:
            dest = OUT / f"{tid}.png"
            ref = ROOT / "refs" / f"{tid}.png"
            if ref.exists():
                if not dest.exists() or dest.read_bytes() != ref.read_bytes():
                    shutil.copyfile(ref, dest)
                meta[tid] = {"source": f"refs/{tid}.png (Olivier)"}
                continue
            if dest.exists() and meta.get(tid, {}).get("seed") == args.seed:
                continue
            subject = re.sub(r"^seamless stylized (painted )?", "", table[tid])
            prompt = EDIT.format(subject=subject)
            wf = client.load_workflow("qwen_edit_2509_angle.json")
            wf["3"]["inputs"]["strength_model"] = 0.0            # sans le LoRA d'angles : édition simple
            wf["8"]["inputs"]["image"] = client.upload_image(STYLE_REF)
            wf["11"]["inputs"]["prompt"] = prompt
            wf["13"]["inputs"]["seed"] = args.seed
            wf["15"]["inputs"]["filename_prefix"] = f"barque/textures/{tid}"
            entry = client.wait(client.submit(wf), timeout=1800)
            client.download(client.output_files(entry, "15", "images")[0], dest)
            Image.open(dest).convert("RGB").resize((1024, 1024), Image.LANCZOS).save(dest)
            make_tileable(dest)
            meta[tid] = {"seed": args.seed, "prompt": prompt, "style_reference": "refs/tex-mousse.png",
                         "model": "qwen_image_edit_2509_fp8 + Lightning 4 pas",
                         "workflow": "pipeline/comfy/workflows/qwen_edit_2509_angle.json (LoRA d'angles à 0)"}
            print(f"  {dest.relative_to(ROOT)}")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    write_stats()


def write_stats():
    """Luminance linéaire moyenne de chaque texture (assets/textures/stats.json) : le matériau peint s'en sert
    pour que la texture module la couleur des sommets autour de 1 sans l'assombrir ni l'éclaircir."""
    stats = {}
    for f in sorted(OUT.glob("tex-*.png")):
        a = np.asarray(Image.open(f).convert("RGB").resize((256, 256))).astype(np.float64) / 255
        lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
        stats[f.stem] = round(float((lin @ [0.2126, 0.7152, 0.0722]).mean()), 4)
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
