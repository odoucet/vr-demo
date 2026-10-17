"""Vidéo de test J1 : équirectangulaire 360 stéréo haut/bas (œil gauche en haut) pour valider au casque
l'orientation, la stéréo, la résolution décodable par le Quest et la synchronisation vidéo / séquence.

    python pipeline/spike/test_video.py                         # 4096×4096, 30 i/s, 240 s
    python pipeline/spike/test_video.py --size 5760 --fps 30
    python pipeline/spike/test_video.py --size 4096 --fps 60 --duration 60

Contenu :
- grille tous les 15°, horizon et méridiens principaux épaissis, AVANT / DROITE / ARRIÈRE / GAUCHE ;
- œil indiqué sur chaque image (une inversion haut/bas se voit immédiatement) ;
- repères droit devant à 1,5 m, 3 m, 10 m et à l'infini, avec la disparité réelle (écart pupillaire 64 mm) :
  au casque, ils doivent paraître à ces distances ;
- compteur d'images et timecode incrustés devant et derrière ;
- flash blanc et bip court à chaque seconde, bip long toutes les 10 s : mesure du décalage son / image /
  séquence (l'horloge maître de la démo est le temps média de cette vidéo).
Sortie : assets/spike/test360_<taille>_<fps>fps_<durée>s.mp4 (HEVC, AAC). Idempotent.
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from gpu import gpu_lock  # noqa: E402

OUT = ROOT / "assets" / "spike"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
IPD = 0.064
DEPTHS = [(1.5, "1,5 m"), (3.0, "3 m"), (10.0, "10 m"), (math.inf, "∞")]


def x_of(yaw_deg, w):
    """Lacet → abscisse : 0° (avant) au centre, + vers la droite."""
    return (yaw_deg / 360.0 + 0.5) % 1.0 * w


def y_of(pitch_deg, h):
    return (0.5 - pitch_deg / 180.0) * h


def eye_image(w, eye):
    h = w // 2
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):  # ciel bleu crépuscule en haut, eau sombre en bas
        p = y / h
        c = (int(40 + 60 * p), int(60 + 50 * p), int(110 - 30 * p)) if p < 0.5 else (int(25 + 20 * (1 - p)), int(45 + 25 * (1 - p)), int(60 + 20 * (1 - p)))
        d.line([(0, y), (w, y)], fill=c)
    s = w / 4096
    for yaw in range(-180, 180, 15):
        major = yaw % 90 == 0
        d.line([(x_of(yaw, w), 0), (x_of(yaw, w), h)], fill=(230, 230, 230) if major else (120, 130, 150), width=max(1, int((4 if major else 1) * s)))
    for pitch in range(-75, 90, 15):
        d.line([(0, y_of(pitch, h)), (w, y_of(pitch, h))], fill=(255, 200, 80) if pitch == 0 else (120, 130, 150), width=max(1, int((4 if pitch == 0 else 1) * s)))
    big = ImageFont.truetype(FONT, int(70 * s))
    small = ImageFont.truetype(FONT, int(40 * s))
    for yaw, label in [(0, "AVANT"), (90, "DROITE"), (180, "ARRIÈRE"), (-90, "GAUCHE")]:
        d.text((x_of(yaw, w), y_of(20, h)), label, font=big, fill="white", anchor="mm")
        d.text((x_of(yaw, w), y_of(-30, h)), f"ŒIL {eye.upper()}", font=small, fill=(255, 120, 120) if eye == "gauche" else (120, 200, 255), anchor="mm")
    d.text((w / 2, y_of(75, h)), "ZÉNITH", font=small, fill="white", anchor="mm")
    d.text((w / 2, y_of(-75, h)), "NADIR", font=small, fill="white", anchor="mm")
    # Repères de profondeur, alignés sous l'horizon devant : décalage angulaire de ±atan(IPD/2/d).
    sign = 1 if eye == "gauche" else -1  # l'œil gauche voit un objet proche décalé vers la droite
    for i, (dist, label) in enumerate(DEPTHS):
        yaw = (i - 1.5) * 14 + sign * (0 if math.isinf(dist) else math.degrees(math.atan(IPD / 2 / dist)))
        cx, cy, r = x_of(yaw, w), y_of(-8, h), 28 * s
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="white", width=max(2, int(5 * s)))
        d.line([(cx, cy - r), (cx, cy + r)], fill="white", width=max(1, int(3 * s)))
        d.text((cx, cy + 2.2 * r), label, font=small, fill="white", anchor="mm")
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", type=int, default=4096, help="largeur = hauteur totale (haut/bas)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--duration", type=int, default=240)
    ap.add_argument("--bitrate", default=None, help="débit vidéo (défaut : 40M en 4K, 60M au-delà)")
    args = ap.parse_args()
    w = args.size
    out = OUT / f"test360_{w}_{args.fps}fps_{args.duration}s.mp4"
    if out.exists():
        print(f"{out.relative_to(ROOT)} déjà présent.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    bg = OUT / f"_test360_bg_{w}.png"
    if not bg.exists():
        frame = Image.new("RGB", (w, w))
        frame.paste(eye_image(w, "gauche"), (0, 0))
        frame.paste(eye_image(w, "droit"), (0, w // 2))
        frame.save(bg)

    h = w // 2
    fs = int(90 * w / 4096)
    text = []
    for eye_y in (0, h):
        for yaw in (0, 180):  # devant et derrière
            x = int(x_of(yaw, w))
            y = eye_y + int(y_of(-45, h))
            text.append(f"drawtext=fontfile={FONT}:fontsize={fs}:fontcolor=white:box=1:boxcolor=black@0.6:"
                        f"x={x}-text_w/2:y={y}:text='image %{{frame_num}}'")
            text.append(f"drawtext=fontfile={FONT}:fontsize={fs}:fontcolor=yellow:box=1:boxcolor=black@0.6:"
                        f"x={x}-text_w/2:y={y + int(1.4 * fs)}:timecode='00\\:00\\:00\\:00':rate={args.fps}")
    flash = f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=fill:enable='lt(mod(n\\,{args.fps})\\,1)'"
    # Grain animé léger : sans lui, l'image fixe se compresse à ~5 Mb/s et ne charge pas le décodeur.
    vf = ",".join(["noise=alls=7:allf=t", flash] + text)
    beep = ("aevalsrc='if(lt(mod(t\\,10)\\,0.2)\\,0.5*sin(2*PI*2000*t)\\,"
            "if(lt(mod(t\\,1)\\,0.06)\\,0.5*sin(2*PI*1000*t)\\,0))':s=48000:d=" + str(args.duration))
    bitrate = args.bitrate or ("40M" if w <= 4096 else "60M")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats",
           "-loop", "1", "-framerate", str(args.fps), "-i", str(bg), "-f", "lavfi", "-i", beep,
           "-t", str(args.duration), "-vf", vf, "-c:v", "hevc_nvenc", "-preset", "p5", "-rc", "cbr", "-b:v", bitrate,
           "-maxrate", bitrate, "-bufsize", bitrate, "-pix_fmt", "yuv420p", "-tag:v", "hvc1", "-g", str(args.fps),
           "-c:a", "aac", "-b:a", "128k", "-ac", "1", "-movflags", "+faststart", "-y", str(out)]
    with gpu_lock("test_video.py (encodage NVENC)"):
        subprocess.run(cmd, check=True)
    print(f"{out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    main()
