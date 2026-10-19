"""Comparaison des itérations du pont aux statues (D18) : vue tournante avant import + trois vues depuis la barque.

    python review/explorations/pont/comparer.py v01 "1536, 5 passes, projection"    # → review/explorations/pont/v01.jpg

Vues depuis la barque (place assise, 1,10 m) : de loin (110 s), à l'approche (126 s), dessous (138 s, regard levé).
La vue tournante est celle du modèle importé (assets/3d/arche-statues/<dossier>/turntable.jpg). Éditeur ouvert requis.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
POSES = [(110, 108.129, 13.622, 17.189, 6), (126, 123.415, 18.35, 17.189, 8), (138, 135.012, 21.389, 9.192, 22)]


def main():
    tag, note = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""
    model_dir = sys.argv[3] if len(sys.argv) > 3 else "trellis2-s42"
    shots = []
    for t, x, y, yaw, pitch in POSES:
        dest = OUT / "captures" / f"{tag}_{t}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "review" / "shoot.py"), "--pose", str(t), str(x), str(y),
                        "1.1", str(yaw), str(pitch), str(dest)], check=True, capture_output=True)
        shots.append(Image.open(dest).convert("RGB").resize((640, 360)))
    turn = Image.open(ROOT / "assets" / "3d" / "arche-statues" / model_dir / "turntable.jpg").convert("RGB")
    turn = turn.crop((0, 40, turn.width // 2, 40 + (turn.height - 40) // 2)).resize((360, 360))
    sheet = Image.new("RGB", (360 + 640 * 3, 400), (20, 20, 20))
    sheet.paste(turn, (0, 40))
    for i, im in enumerate(shots):
        sheet.paste(im, (360 + 640 * i, 40))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font = None
    d.text((10, 8), f"pont {tag} — {note}   |   3D avant import   |   barque : 110 s, 126 s, 138 s", fill=(255, 220, 120), font=font)
    sheet.save(OUT / f"{tag}.jpg", quality=88)
    print(OUT / f"{tag}.jpg")


if __name__ == "__main__":
    main()
