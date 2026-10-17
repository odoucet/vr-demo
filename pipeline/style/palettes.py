"""Bible de style (J0) : palette dominante par beat, extraite des concepts d'ambiance.

    python pipeline/style/palettes.py      # → pipeline/style/palettes.yaml + review/bible/palettes.png

Source par beat : refs/<beat>.png (images d'Olivier) si elle existe, sinon assets/concepts/<beat>.png (concept
provisoire généré). 6 couleurs par k-means (espace Lab approximatif), triées par luminance, avec leur part.
Les palettes servent de référence aux matériaux et à l'éclairage par beat ; elles changent dès qu'une
référence change. Déterministe.
"""
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BEATS = ["S1-NOIR", "S2-PONTON", "S3-ABYSSE", "S4-GUE", "S5-RACINES", "S6-LUNE", "S7-LAC"]
K = 6


def source(beat):
    for p in (ROOT / "refs" / f"{beat}.png", ROOT / "assets" / "concepts" / f"{beat}.png"):
        if p.exists():
            return p
    return None


def kmeans(pixels, k, iters=25, seed=0):
    rng = np.random.default_rng(seed)
    centers = pixels[rng.choice(len(pixels), k, replace=False)]
    for _ in range(iters):
        labels = np.argmin(((pixels[:, None, :] - centers[None]) ** 2).sum(-1), axis=1)
        centers = np.array([pixels[labels == i].mean(0) if np.any(labels == i) else centers[i] for i in range(k)])
    return centers, np.bincount(labels, minlength=k) / len(labels)


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main():
    data, rows = {}, []
    for beat in BEATS:
        src = source(beat)
        if src is None:
            continue
        im = Image.open(src).convert("RGB")
        small = np.asarray(im.resize((160, 90))).reshape(-1, 3).astype(np.float32)
        centers, share = kmeans(small, K)
        order = np.argsort(centers @ np.array([0.299, 0.587, 0.114]))
        colors = [("#%02x%02x%02x" % tuple(int(round(c)) for c in centers[i]), float(share[i])) for i in order]
        data[beat] = {"source": str(src.relative_to(ROOT)), "provisoire": "assets/concepts" in str(src),
                      "couleurs": [{"hex": h, "part": round(p, 3)} for h, p in colors]}
        rows.append((beat, im, colors, "assets/concepts" in str(src)))
    (ROOT / "pipeline" / "style" / "palettes.yaml").write_text(
        "# Palettes par beat (générées par pipeline/style/palettes.py, ne pas éditer à la main)\n" +
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    W, H = 1500, 230
    sheet = Image.new("RGB", (W, H * len(rows) + 60), "#141414")
    d = ImageDraw.Draw(sheet)
    d.text((16, 16), "Bible de style — palette par beat (J0)", fill="white", font=font(24))
    for r, (beat, im, colors, prov) in enumerate(rows):
        y = 60 + r * H
        sheet.paste(im.resize((360, 205)), (16, y))
        d.text((392, y + 4), beat + ("  (concept provisoire généré)" if prov else ""), fill="#ffd27a", font=font(20))
        x = 392
        widths = [max(60, 1080 * p) for _, p in colors]
        widths = [int(w * 1080 / sum(widths)) for w in widths]   # tient dans la largeur disponible
        for (h, p), w in zip(colors, widths):
            d.rectangle([x, y + 40, x + w - 6, y + 200], fill=h)
            d.text((x + 6, y + 176), h, fill="white" if np.mean([int(h[i:i + 2], 16) for i in (1, 3, 5)]) < 128 else "black", font=font(14))
            x += w
    out = ROOT / "review" / "bible" / "palettes.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"{len(rows)} palettes → pipeline/style/palettes.yaml, {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
