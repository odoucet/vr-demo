"""Montages vidéo de l'article, remontés depuis les animatics et les captures de review/ (définitions : montages.yaml).

    python pipeline/article/montage.py                  # tous les montages
    python pipeline/article/montage.py pont-versions    # un seul
    python pipeline/article/montage.py --planche-seule  # seulement les planches fixes (rapide)

Six types de montage :
  versions   la même fenêtre de la balade, un segment par version, sans coupure : la barque avance, le décor change
  extraits   des plans de l'animatique finale enchaînés en fondu, sur la musique en continu (bande-annonce)
  volet      deux versions au même instant ; un volet passe de l'une à l'autre
  cote       deux versions côte à côte, au même instant (le centre de chaque image)
  legendes   une fenêtre d'une animatique, avec des légendes datées
  diaporama  des captures du casque en fondu enchaîné, par suites (un même instant de la balade)

Toutes les animatics suivent la même trajectoire de caméra : un instant de la balade se retrouve, au même cadrage,
dans chaque version. Trois d'entre elles sont tronquées (iter-031 à 2:22, iter-033 à 2:19, iter-059 à 1:49) : le
script refuse une fenêtre qui dépasse la vidéo.

Sorties : builds/article/montages/<nom>.mp4, maîtres en haute qualité (hors dépôt), et <nom>.jpg, la planche fixe
d'un montage « versions ». Les versions web sont faites par pipeline/article/export_web.py. Les animatics sources sont
hors dépôt : pipeline/review/animatic.py les régénère. ffmpeg tourne sur le processeur : pas de verrou GPU.
"""
import argparse
import os
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "builds" / "article" / "montages"
W, H, FPS = 1920, 1080, 30
MAITRE = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p"]
AUDIO = ["-c:a", "aac", "-b:a", "192k"]

FONTS = Path("/mnt/c/Windows/Fonts")
REGULAR = FONTS / "segoeui.ttf"
BOLD = FONTS / "segoeuib.ttf"

# Frise des six jours au bas de l'image : de la création du dépôt à la version finale.
DEBUT, FIN = datetime(2026, 10, 17, 14), datetime(2026, 10, 23, 12)
LUCIOLE = "0xE8D46A"
PAPIER, ENCRE, ENCRE_2 = "#f6f1e7", "#1d2b3a", "#5b6670"


def quand(d):
    return f"{d:%d/%m} · {d.hour} h {d:%M}"


def date(v):
    return datetime.strptime(v, "%Y-%m-%d %H:%M")


def mmss(s):
    return f"{int(s // 60)}:{int(s % 60):02d}"


def frise_x(d, x0, x1):
    return x0 + (x1 - x0) * (d - DEBUT).total_seconds() / (FIN - DEBUT).total_seconds()


class Textes:
    """Incrustations drawtext : chaque texte passe par un fichier UTF-8 (accents, deux-points, apostrophes)."""

    def __init__(self, tmp):
        self.tmp, self.n = Path(tmp), 0

    def __call__(self, texte, taille, x, y, gras=False, enable=None, boite=True, alpha=None):
        self.n += 1
        p = self.tmp / f"t{self.n}.txt"
        p.write_text(texte, encoding="utf-8")
        f = (f"drawtext=fontfile={BOLD if gras else REGULAR}:textfile={p}:expansion=none:fontsize={taille}"
             f":fontcolor=white:x='{x}':y='{y}'")
        if boite:
            f += ":box=1:boxcolor=black@0.45:boxborderw=12"
        if alpha:
            f += f":alpha='{alpha}'"
        if enable:
            f += f":enable='{enable}'"
        return f


def duree_video(src):
    n = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames",
                        "-of", "csv=p=0", str(ROOT / src)], capture_output=True, text=True, check=True).stdout.strip()
    return int(n) / FPS


def verifier(nom, src, fin):
    if not (ROOT / src).exists():
        sys.exit(f"{nom} : {src} manquant (pipeline/review/animatic.py le régénère)")
    if fin > duree_video(src) + 0.01:
        sys.exit(f"{nom} : {src} s'arrête à {mmss(duree_video(src))}, avant la fin de la fenêtre ({mmss(fin)})")


def norme(entree, sortie, recadre=""):
    """Une entrée vidéo ramenée à 1920×1080, 30 i/s, depuis l'instant 0."""
    return (f"[{entree}]setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}:flags=lanczos,setsar=1{recadre},"
            f"format=yuv420p[{sortie}]")


def encoder(cmd, out, audio=True):
    subprocess.run(cmd + MAITRE + (AUDIO if audio else ["-an"]) + ["-movflags", "+faststart", str(out)], check=True)
    print(f"{out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} Mo)")


# ---------------------------------------------------------------------------------------------------- versions


def frise(t, d):
    """La frise des six jours en bas de l'image, le curseur à la date d."""
    f = []
    x0, x1, yf = 80, W - 80, H - 54
    f.append(f"drawbox=x=0:y={yf - 22}:w={W}:h={H - yf + 22}:color=black@0.35:t=fill")
    f.append(f"drawbox=x={x0}:y={yf}:w={x1 - x0}:h=2:color=white@0.55:t=fill")
    day = DEBUT.replace(hour=0)
    for k in range(7):
        j = day.replace(day=day.day + k)
        x = frise_x(max(j, DEBUT), x0, x1)
        f.append(f"drawbox=x={x:.0f}:y={yf - 6}:w=2:h=14:color=white@0.55:t=fill")
        f.append(t(f"{j:%d}/{j:%m}", 20, f"{x + 6:.0f}", yf + 8, boite=False))
    xm = frise_x(d, x0, x1)
    f.append(f"drawbox=x={x0}:y={yf - 1}:w={xm - x0:.0f}:h=4:color={LUCIOLE}@0.95:t=fill")
    f.append(f"drawbox=x={xm - 7:.0f}:y={yf - 6}:w=14:h=14:color={LUCIOLE}:t=fill")
    return f


def versions(nom, m):
    a, b = m["fenetre"]
    vs = m["versions"]
    n = len(vs)
    d = (b - a) / n
    for i, v in enumerate(vs):
        verifier(nom, v["src"], a + (i + 1) * d)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for i, v in enumerate(vs):
        cmd += ["-ss", f"{a + i * d:.3f}", "-t", f"{d:.3f}", "-i", str(ROOT / v["src"])]
    cmd += ["-ss", str(a), "-t", str(b - a), "-i", str(ROOT / m["audio"])]
    with tempfile.TemporaryDirectory() as tmp:
        t = Textes(tmp)
        chains = []
        for i, v in enumerate(vs):
            ov = [t(quand(date(v["date"])), 46, 80, H - 210, gras=True), t(v["quoi"], 34, 80, H - 140)]
            ov += frise(t, date(v["date"]))
            if i == 0:
                ov += [t(m["titre"], 50, 80, 70, gras=True, enable="lt(t,3.5)"), "fade=t=in:st=0:d=0.6"]
            if i == n - 1:
                ov.append(f"fade=t=out:st={d - 0.8:.2f}:d=0.8")
            chains.append(norme(f"{i}:v", f"n{i}"))
            chains.append(f"[n{i}]" + ",".join(ov) + f"[v{i}]")
        chains.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
        chains.append(f"[{n}:a]asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.6,afade=t=out:st={b - a - 0.8}:d=0.8[aout]")
        encoder(cmd + ["-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]"], OUT / f"{nom}.mp4")


def planche(nom, m):
    """Les versions au même instant, côte à côte : la vidéo en image fixe."""
    t = m["pose"]
    cols, tw, th, cap, pad = 4, 640, 360, 92, 16
    rows = -(-(len(m["versions"]) + 1) // cols)
    head = 84
    img = Image.new("RGB", (pad + cols * (tw + pad), head + rows * (th + cap + pad)), PAPIER)
    g = ImageDraw.Draw(img)
    fb, fr, fs = ImageFont.truetype(str(BOLD), 34), ImageFont.truetype(str(BOLD), 24), ImageFont.truetype(str(REGULAR), 19)
    g.text((pad, 22), f"{m['titre']} : instant {mmss(t)} de la balade", font=fb, fill=ENCRE)
    with tempfile.TemporaryDirectory() as tmp:
        for i, v in enumerate(m["versions"]):
            p = Path(tmp) / f"{i}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(ROOT / v["src"]), "-frames:v", "1",
                            "-vf", f"scale={tw}:{th}:flags=lanczos", str(p)], check=True)
            x, y = pad + (i % cols) * (tw + pad), head + (i // cols) * (th + cap + pad)
            img.paste(Image.open(p), (x, y))
            g.text((x, y + th + 8), quand(date(v["date"])), font=fr, fill=ENCRE)
            for k, line in enumerate(textwrap.wrap(v["quoi"], 58)[:2]):
                g.text((x, y + th + 40 + k * 24), line, font=fs, fill=ENCRE_2)
    i = len(m["versions"])
    x, y = pad + (i % cols) * (tw + pad), head + (i // cols) * (th + cap + pad)
    note = ("Même trajectoire de caméra dans toutes les animatics : seul le décor change. Les versions vont du "
            f"{quand(date(m['versions'][0]['date']))} au {quand(date(m['versions'][-1]['date']))}.")
    for k, line in enumerate(textwrap.wrap(note, 46)):
        g.text((x + 12, y + 12 + k * 30), line, font=ImageFont.truetype(str(REGULAR), 23), fill=ENCRE_2)
    out = OUT / f"{nom}.jpg"
    img.save(out, quality=92)
    print(f"{out.relative_to(ROOT)} ({img.width}×{img.height})")


# ---------------------------------------------------------------------------------------------------- extraits


def extraits(nom, m):
    plans, f = m["plans"], m["fondu"]
    for a, b in plans:
        verifier(nom, m["src"], b)
    seq = yaml.safe_load((ROOT / "pipeline" / "sequencer.yaml").read_text(encoding="utf-8"))
    total = sum(b - a for a, b in plans) - (len(plans) - 1) * f
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for a, b in plans:
        cmd += ["-ss", str(a), "-t", str(b - a), "-i", str(ROOT / m["src"])]
    cmd += ["-ss", str(m["musique"]), "-t", f"{total:.3f}", "-i", str(ROOT / seq["music"]["file"])]
    with tempfile.TemporaryDirectory() as tmp:
        t = Textes(tmp)
        chains = [norme(f"{i}:v", f"n{i}") for i in range(len(plans))]
        cur, offset = "n0", 0.0
        for i in range(1, len(plans)):
            offset += plans[i - 1][1] - plans[i - 1][0] - f
            chains.append(f"[{cur}][n{i}]xfade=transition=fade:duration={f}:offset={offset:.3f}[x{i}]")
            cur = f"x{i}"
        titre, sous_titre = m["titre"]
        apparition = "if(lt(t,1.4),max(0,(t-0.8)/0.6),if(lt(t,4.6),1,max(0,(5.2-t)/0.6)))"
        fin = total - 4.2
        disparition = f"if(lt(t,{fin + 0.6:.2f}),max(0,(t-{fin:.2f})/0.6),1)"
        ov = [t(titre, 80, "(w-tw)/2", "h*0.38", gras=True, boite=False, alpha=apparition, enable="lt(t,5.3)"),
              t(sous_titre, 44, "(w-tw)/2", "h*0.38+108", boite=False, alpha=apparition, enable="lt(t,5.3)"),
              t(m["fin"], 42, "(w-tw)/2", "h-160", boite=False, alpha=disparition, enable=f"gt(t,{fin:.2f})"),
              "fade=t=in:st=0:d=0.8", f"fade=t=out:st={total - 1.4:.2f}:d=1.4"]
        chains.append(f"[{cur}]" + ",".join(ov) + "[vout]")
        n = len(plans)
        chains.append(f"[{n}:a]asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1,afade=t=out:st={total - 2.5:.2f}:d=2.5[aout]")
        encoder(cmd + ["-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]"], OUT / f"{nom}.mp4")


# ---------------------------------------------------------------------------------------------------- volet


def volet(nom, m):
    a, b = m["fenetre"]
    t0, t1 = m["balayage"]
    av, ap = m["avant"], m["apres"]
    verifier(nom, av["src"], b)
    verifier(nom, ap["src"], b)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", str(ROOT / av["src"]),
           "-ss", str(a), "-t", str(b - a), "-i", str(ROOT / ap["src"])]
    # Position du volet (fraction de la largeur) : à gauche du trait l'avant, à droite l'après ; il part du bord droit.
    p = f"(1-max(0,min(1,(T-{t0})/{t1 - t0})))"
    pt = p.replace("T", "t")
    luma = f"if(lt(abs(X/W-{p}),0.0016),235,if(lt(X/W,{p}),A,B))"
    chroma = f"if(lt(abs(X/W-{p}),0.0032),128,if(lt(X/W,{p}),A,B))"
    with tempfile.TemporaryDirectory() as tmp:
        t = Textes(tmp)
        ov = [t(f"{av['quoi']} : {quand(date(av['date']))}", 38, f"w*{pt}-tw-36", 60, enable=f"gt({pt},0.3)"),
              t(f"{ap['quoi']} : {quand(date(ap['date']))}", 38, f"w*{pt}+36", 60, enable=f"lt({pt},0.7)"),
              "fade=t=in:st=0:d=0.6", f"fade=t=out:st={b - a - 0.8}:d=0.8"]
        chains = [norme("0:v", "av"), norme("1:v", "ap"),
                  f"[av][ap]blend=c0_expr='{luma}':c1_expr='{chroma}':c2_expr='{chroma}',{','.join(ov)}[vout]",
                  f"[1:a]asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.6,afade=t=out:st={b - a - 0.8}:d=0.8[aout]"]
        encoder(cmd + ["-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]"], OUT / f"{nom}.mp4")


# ---------------------------------------------------------------------------------------------------- côte à côte


def cote(nom, m):
    a, b = m["fenetre"]
    g, d = m["gauche"], m["droite"]
    verifier(nom, g["src"], b)
    verifier(nom, d["src"], b)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", str(ROOT / g["src"]),
           "-ss", str(a), "-t", str(b - a), "-i", str(ROOT / d["src"])]
    centre = f",crop={W // 2}:{H}:{W // 4}:0"
    with tempfile.TemporaryDirectory() as tmp:
        t = Textes(tmp)
        ov = [f"drawbox=x={W // 2 - 2}:y=0:w=4:h={H}:color=white@0.9:t=fill",
              t(g["legende"], 34, 36, 50), t(d["legende"], 34, W // 2 + 36, 50),
              "fade=t=in:st=0:d=0.6", f"fade=t=out:st={b - a - 0.8}:d=0.8"]
        audio = "1:a" if m.get("audio", "droite") == "droite" else "0:a"
        chains = [norme("0:v", "g", centre), norme("1:v", "d", centre),
                  f"[g][d]hstack=inputs=2,{','.join(ov)}[vout]",
                  f"[{audio}]asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.6,afade=t=out:st={b - a - 0.8}:d=0.8[aout]"]
        encoder(cmd + ["-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]"], OUT / f"{nom}.mp4")


# ---------------------------------------------------------------------------------------------------- légendes


def legendes(nom, m):
    a, b = m["fenetre"]
    verifier(nom, m["src"], b)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", str(ROOT / m["src"])]
    with tempfile.TemporaryDirectory() as tmp:
        t = Textes(tmp)
        ov = [t(f"{mmss(debut)} · {texte}", 40, 80, H - 140, enable=f"between(t,{debut - a:.2f},{fin - a:.2f})")
              for debut, fin, texte in m["legendes"]]
        ov += ["fade=t=in:st=0:d=0.6", f"fade=t=out:st={b - a - 0.8}:d=0.8"]
        chains = [norme("0:v", "n"), f"[n]{','.join(ov)}[vout]",
                  f"[0:a]asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.6,afade=t=out:st={b - a - 0.8}:d=0.8[aout]"]
        encoder(cmd + ["-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]"], OUT / f"{nom}.mp4")


# ---------------------------------------------------------------------------------------------------- diaporama


def diaporama(nom, m):
    """Captures du casque en fondu enchaîné, image par image en Python, envoyées à ffmpeg."""
    w, h = m["taille"]
    tenue, fondu = round(m["image"] * FPS), round(m["fondu"] * FPS)
    fb, fr = ImageFont.truetype(str(BOLD), 44), ImageFont.truetype(str(REGULAR), 36)
    images = []
    for s in m["suites"]:
        for it in s["iterations"]:
            p = ROOT / "review" / f"iter-{it:03d}" / "casque" / f"{s['instant']}.jpg"
            if not p.exists():
                sys.exit(f"{nom} : {p.relative_to(ROOT)} manquant")
            d = datetime.fromtimestamp(os.path.getmtime(p))
            images.append((Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS), s["titre"], quand(d)))

    def legender(im, titre, sous):
        im = im.copy()
        g = ImageDraw.Draw(im, "RGBA")
        for texte, police, y in ((titre, fb, 40), (sous, fr, h - 92)):
            x0, y0, x1, y1 = g.textbbox((40, y), texte, font=police)
            g.rectangle((x0 - 14, y0 - 10, x1 + 14, y1 + 10), fill=(0, 0, 0, 115))
            g.text((40, y), texte, font=police, fill="white")
        return im

    out = OUT / f"{nom}.mp4"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                             "-r", str(FPS), "-i", "-", *MAITRE, "-an", "-movflags", "+faststart", str(out)],
                            stdin=subprocess.PIPE)
    for i, (im, titre, sous) in enumerate(images):
        fixe = legender(im, titre, sous)
        for _ in range(tenue):
            proc.stdin.write(fixe.tobytes())
        if i + 1 < len(images):
            nxt, titre2, sous2 = images[i + 1]
            for k in range(1, fondu + 1):
                mix = Image.blend(im, nxt, k / (fondu + 1))
                lab = (titre, sous) if k <= fondu // 2 else (titre2, sous2)
                proc.stdin.write(legender(mix, *lab).tobytes())
    proc.stdin.close()
    if proc.wait():
        sys.exit(f"{nom} : ffmpeg a échoué")
    print(f"{out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} Mo, {len(images)} captures)")


TYPES = {"versions": versions, "extraits": extraits, "volet": volet, "cote": cote, "legendes": legendes,
         "diaporama": diaporama}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("noms", nargs="*")
    ap.add_argument("--planche-seule", action="store_true")
    args = ap.parse_args()
    defs = yaml.safe_load((Path(__file__).with_name("montages.yaml")).read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for nom in args.noms or defs:
        m = defs[nom]
        kind = m.get("type", "versions")
        if kind == "versions":
            planche(nom, m)
        if not args.planche_seule:
            TYPES[kind](nom, m)


if __name__ == "__main__":
    main()
