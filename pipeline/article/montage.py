"""Montages vidéo de l'article, remontés depuis les animatics de review/ (définitions : montages.yaml).

    python pipeline/article/montage.py                  # tous les montages
    python pipeline/article/montage.py pont-versions    # un seul
    python pipeline/article/montage.py --planche-seule  # seulement les planches fixes (rapide)

Sorties dans article/montages/ : <nom>.mp4 (1920×1080, 30 i/s, hors dépôt) et <nom>.jpg, la planche fixe des
versions au même instant (versionnée). Les animatics sources sont hors dépôt : les régénérer avec
pipeline/review/animatic.py si elles manquent. ffmpeg tourne sur le processeur : pas de verrou GPU.
"""
import argparse
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "article" / "montages"
W, H, FPS = 1920, 1080, 30

FONTS = Path("/mnt/c/Windows/Fonts")
REGULAR = FONTS / "segoeui.ttf"
BOLD = FONTS / "segoeuib.ttf"

# Frise des six jours au bas de l'image : de la création du dépôt à la version finale.
DEBUT, FIN = datetime(2026, 10, 17, 14), datetime(2026, 10, 23, 12)
LUCIOLE = "0xE8D46A"
PAPIER, ENCRE, ENCRE_2 = "#f6f1e7", "#1d2b3a", "#5b6670"


def quand(d):
    return f"{d:%d/%m} · {d.hour} h {d:%M}"


def frise_x(d, x0, x1):
    return x0 + (x1 - x0) * (d - DEBUT).total_seconds() / (FIN - DEBUT).total_seconds()


def textfile(tmp, name, text):
    p = Path(tmp) / f"{name}.txt"
    p.write_text(text, encoding="utf-8")
    return p


def overlays(tmp, i, v, date, titre, premier, dernier, duree):
    """Filtres d'incrustation d'un segment : date, ce qui a changé, frise des six jours, titre au début."""
    f = []
    x0, x1, yf = 80, W - 80, H - 54
    f.append(f"drawtext=fontfile={BOLD}:textfile={textfile(tmp, f'q{i}', quand(date))}:expansion=none"
             f":fontsize=46:fontcolor=white:x=80:y={H - 210}:box=1:boxcolor=black@0.45:boxborderw=12")
    f.append(f"drawtext=fontfile={REGULAR}:textfile={textfile(tmp, f'c{i}', v['quoi'])}:expansion=none"
             f":fontsize=34:fontcolor=white:x=80:y={H - 140}:box=1:boxcolor=black@0.45:boxborderw=12")
    f.append(f"drawbox=x=0:y={yf - 22}:w={W}:h={H - yf + 22}:color=black@0.35:t=fill")
    f.append(f"drawbox=x={x0}:y={yf}:w={x1 - x0}:h=2:color=white@0.55:t=fill")
    day = DEBUT.replace(hour=0)
    for k in range(7):
        d = day.replace(day=day.day + k)
        x = frise_x(max(d, DEBUT), x0, x1)
        f.append(f"drawbox=x={x:.0f}:y={yf - 6}:w=2:h=14:color=white@0.55:t=fill")
        f.append(f"drawtext=fontfile={REGULAR}:text='{d:%d}/{d:%m}':expansion=none:fontsize=20"
                 f":fontcolor=white@0.8:x={x + 6:.0f}:y={yf + 8}")
    xm = frise_x(date, x0, x1)
    f.append(f"drawbox=x={x0}:y={yf - 1}:w={xm - x0:.0f}:h=4:color={LUCIOLE}@0.95:t=fill")
    f.append(f"drawbox=x={xm - 7:.0f}:y={yf - 6}:w=14:h=14:color={LUCIOLE}:t=fill")
    if premier:
        f.append(f"drawtext=fontfile={BOLD}:textfile={textfile(tmp, 'titre', titre)}:expansion=none:fontsize=50"
                 f":fontcolor=white:x=80:y=70:box=1:boxcolor=black@0.45:boxborderw=14:enable='lt(t,3.5)'")
        f.append("fade=t=in:st=0:d=0.6")
    if dernier:
        f.append(f"fade=t=out:st={duree - 0.8:.2f}:d=0.8")
    return ",".join(f)


def video(nom, m):
    a, b = m["fenetre"]
    versions = m["versions"]
    n = len(versions)
    d = (b - a) / n
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for i, v in enumerate(versions):
        cmd += ["-ss", f"{a + i * d:.3f}", "-t", f"{d:.3f}", "-i", str(ROOT / v["src"])]
    cmd += ["-ss", str(a), "-t", str(b - a), "-i", str(ROOT / m["audio"])]
    with tempfile.TemporaryDirectory() as tmp:
        chains = []
        for i, v in enumerate(versions):
            date = datetime.strptime(v["date"], "%Y-%m-%d %H:%M")
            ov = overlays(tmp, i, v, date, m["titre"], i == 0, i == n - 1, d)
            chains.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}:flags=lanczos,setsar=1,"
                          f"format=yuv420p,{ov}[v{i}]")
        chains.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
        chains.append(f"[{n}:a]asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.6,afade=t=out:st={b - a - 0.8}:d=0.8[aout]")
        out = OUT / f"{nom}.mp4"
        cmd += ["-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
    print(f"{out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} Mo)")


def planche(nom, m):
    """Les versions au même instant, côte à côte : la vidéo en image fixe."""
    t = m["pose"]
    cols, tw, th, cap, pad = 4, 640, 360, 92, 16
    rows = -(-(len(m["versions"]) + 1) // cols)
    head = 84
    img = Image.new("RGB", (pad + cols * (tw + pad), head + rows * (th + cap + pad)), PAPIER)
    g = ImageDraw.Draw(img)
    fb, fr, fs = ImageFont.truetype(str(BOLD), 34), ImageFont.truetype(str(BOLD), 24), ImageFont.truetype(str(REGULAR), 19)
    g.text((pad, 22), f"{m['titre']} — instant {t // 60}:{t % 60:02d} de la balade", font=fb, fill=ENCRE)
    with tempfile.TemporaryDirectory() as tmp:
        for i, v in enumerate(m["versions"]):
            p = Path(tmp) / f"{i}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(ROOT / v["src"]), "-frames:v", "1",
                            "-vf", f"scale={tw}:{th}:flags=lanczos", str(p)], check=True)
            x, y = pad + (i % cols) * (tw + pad), head + (i // cols) * (th + cap + pad)
            img.paste(Image.open(p), (x, y))
            date = datetime.strptime(v["date"], "%Y-%m-%d %H:%M")
            g.text((x, y + th + 8), quand(date), font=fr, fill=ENCRE)
            for k, line in enumerate(textwrap.wrap(v["quoi"], 58)[:2]):
                g.text((x, y + th + 40 + k * 24), line, font=fs, fill=ENCRE_2)
    i = len(m["versions"])
    x, y = pad + (i % cols) * (tw + pad), head + (i // cols) * (th + cap + pad)
    note = ("Même trajectoire de caméra dans toutes les animatics : seul le décor change. "
            f"Les versions vont du {quand(datetime.strptime(m['versions'][0]['date'], '%Y-%m-%d %H:%M'))} "
            f"au {quand(datetime.strptime(m['versions'][-1]['date'], '%Y-%m-%d %H:%M'))}.")
    for k, line in enumerate(textwrap.wrap(note, 46)):
        g.text((x + 12, y + 12 + k * 30), line, font=ImageFont.truetype(str(REGULAR), 23), fill=ENCRE_2)
    out = OUT / f"{nom}.jpg"
    img.save(out, quality=88)
    print(f"{out.relative_to(ROOT)} ({img.width}×{img.height})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("noms", nargs="*")
    ap.add_argument("--planche-seule", action="store_true")
    args = ap.parse_args()
    defs = yaml.safe_load((Path(__file__).with_name("montages.yaml")).read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for nom in args.noms or defs:
        m = defs[nom]
        missing = [v["src"] for v in m["versions"] if not (ROOT / v["src"]).exists()]
        if missing:
            sys.exit(f"{nom} : animatics manquantes ({', '.join(missing)}) : pipeline/review/animatic.py")
        planche(nom, m)
        if not args.planche_seule:
            video(nom, m)


if __name__ == "__main__":
    main()
