"""Planche de comparaison image → 3D : source + turntables de chaque variante, une ligne par asset.

    python pipeline/review/compare_3d.py lanterne barque abysses     # → review/3d/comparaison.jpg
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "3d"
OUT = ROOT / "review" / "3d"
CELL = 512


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def fit(im, size):
    im = im.convert("RGB")
    im.thumbnail((size, size))
    canvas = Image.new("RGB", (size, size), "#9a9a9a")
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    return canvas


def main(names):
    rows = []
    for name in names:
        variants = sorted(p for p in (ASSETS / name).iterdir() if (p / "turntable.jpg").exists())
        src = next((ROOT / "refs").glob(f"{name}.*"))
        cells = [(fit(Image.open(src), CELL), f"{name} — source")]
        for v in variants:
            sheet = Image.open(v / "turntable.jpg")
            cells.append((sheet.crop((0, 40, 1024, 1064)).resize((CELL, CELL)), v.name))
        rows.append(cells)
    width = max(len(r) for r in rows) * CELL
    board = Image.new("RGB", (width, len(rows) * (CELL + 36)), "#202020")
    draw = ImageDraw.Draw(board)
    for y, cells in enumerate(rows):
        for x, (im, label) in enumerate(cells):
            board.paste(im, (x * CELL, y * (CELL + 36) + 36))
            draw.text((x * CELL + 8, y * (CELL + 36) + 8), label, fill="white", font=font(20))
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "comparaison.jpg"
    board.save(dest, quality=88)
    print(dest.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])
