"""Couleur de brume par beat, mesurée sur les références et partagée entre temps réel et offline.

    python pipeline/style/ambiance.py      # → pipeline/style/ambiance.json + review/bible/brume.png

Teinte : partie claire (quart supérieur en luminance) de la bande d'horizon (35-50 % de la hauteur) de
refs/<beat>.png, à défaut assets/concepts/<beat>.png : c'est là que la brume se voit dans les références.
Saturation, luminance et densité : pipeline/style/ambiance.yaml. Temps des beats : pipeline/sequencer.yaml (temps démo).
Sortie en JSON (le Python d'Unreal n'a pas yaml). Déterministe.
"""
import json
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
STYLE = ROOT / "pipeline" / "style"


def source(beat):
    for p in (ROOT / "refs" / f"{beat}.png", ROOT / "assets" / "concepts" / f"{beat}.png"):
        if p.exists():
            return p
    return None


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def mist_tint(path):
    im = np.asarray(Image.open(path).convert("RGB").resize((320, 180))).astype(np.float64) / 255
    band = im[int(180 * 0.35):int(180 * 0.50)].reshape(-1, 3)
    lum = band @ [0.299, 0.587, 0.114]
    return np.median(band[lum >= np.quantile(lum, 0.75)], axis=0)    # sRGB 0-1


def main():
    cfg = yaml.safe_load((STYLE / "ambiance.yaml").read_text(encoding="utf-8"))
    seq = yaml.safe_load((ROOT / "pipeline" / "sequencer.yaml").read_text(encoding="utf-8"))
    offset = seq["music"]["offset_s"]
    out = {"fondu_s": cfg["fondu_s"], "beats": []}
    for b in seq["beats"]:
        src, params = source(b["id"]), cfg["beats"][b["id"]]
        tint = srgb_to_linear(mist_tint(src))
        y = float(tint @ [0.2126, 0.7152, 0.0722])
        tint = y + (tint - y) * cfg["saturation"]          # brume : teinte adoucie (la bande contient du feuillage)
        lin = tint * params["luminance"] / max(y, 1e-6)
        out["beats"].append({
            "id": b["id"], "debut_s": round(offset + b["music_s"], 2), "source": str(src.relative_to(ROOT)),
            "brume_lineaire": [round(float(v), 4) for v in lin], "densite": params["densite"],
            "brume_hex": "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in linear_to_srgb(lin / max(lin.max(), 1e-6))),
        })
    (STYLE / "ambiance.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    sheet = Image.new("RGB", (140 * len(out["beats"]), 170), "#141414")
    d = ImageDraw.Draw(sheet)
    for i, b in enumerate(out["beats"]):
        d.rectangle([i * 140 + 8, 8, i * 140 + 132, 132], fill=b["brume_hex"])
        d.text((i * 140 + 8, 140), b["id"] + " (teinte)", fill="white")
        d.text((i * 140 + 8, 154), f"lum {cfg['beats'][b['id']]['luminance']}  d {b['densite']}", fill="#aaa")
    out_png = ROOT / "review" / "bible" / "brume.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    print(f"{len(out['beats'])} brumes → pipeline/style/ambiance.json, {out_png.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
