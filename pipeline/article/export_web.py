"""Médias de l'article prêts pour WordPress : réduction, compression, affiches des vidéos, aperçu local.

    python pipeline/article/export_web.py                  # tout : images, vidéos, aperçu
    python pipeline/article/export_web.py --sans-video     # images et aperçu (rapide)
    python pipeline/article/export_web.py --mois 2026/11   # upload en novembre : dossier et liens du Markdown

Lit pipeline/article/medias.yaml (fichier publié → source et traitement) et écrit article/wp-content/uploads/<mois>/,
le dossier tel que WordPress le crée pour un upload du mois : envoyer ces fichiers dans la médiathèque sans les
renommer, et les liens du Markdown (/wp-content/uploads/<mois>/...) tombent juste. Vérifie que l'article et la liste
des médias concordent. Écrit aussi article/apercu.html, l'article mis en page avec ses images et ses vidéos, pour le
relire hors de WordPress (ouvrir dans un navigateur).

Réglages : JPEG progressif (qualité 82, 88 pour les graphiques à dégradés), PNG en palette de 256 couleurs pour les
schémas à aplats, vidéo H.264 à qualité constante (CRF 24) plafonnée à 3 Mb/s, son AAC 128 kb/s, métadonnées
retirées, lecture progressive (faststart), affiche JPEG de 1280 px. Les maîtres viennent de schemas.py,
graphiques.py, compositions.py et montage.py (builds/article/). Les vidéos web sont hors dépôt (.gitignore).
"""
import argparse
import io
import re
import subprocess
import sys
from pathlib import Path

import markdown
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name("medias.yaml")
# Plafond de 3 Mb/s : sur la bande-annonce (lucioles, feuillage), indiscernable de 4 Mb/s en recadrage à 100 %
# (essai du 30/10), et un quart plus léger ; chaque vidéo reste sous 20 Mo.
VIDEO = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-crf", "24", "-maxrate", "3M",
         "-bufsize", "6M", "-pix_fmt", "yuv420p", "-map_metadata", "-1", "-movflags", "+faststart"]
SON = ["-c:a", "aac", "-b:a", "128k", "-ar", "48000"]
AFFICHE = 1280
# Sans libimagequant dans Pillow, la coupe médiane donne des aplats nets ; pas de tramage, qui brouillerait le texte.
QUANT = Image.Quantize.MEDIANCUT


def reduire(im, largeur):
    if largeur and im.width > largeur:
        im = im.resize((largeur, round(im.height * largeur / im.width)), Image.LANCZOS)
    return im


def jpeg(im, out, qualite):
    im.convert("RGB").save(out, "JPEG", quality=qualite, optimize=True, progressive=True)


def image(src, out, m):
    im = Image.open(src)
    if "recadre" in m:
        g, h, d, b = m["recadre"]
        im = im.crop((round(g * im.width), round(h * im.height), round(d * im.width), round(b * im.height)))
    im = reduire(im.convert("RGB"), m.get("largeur"))
    if out.suffix == ".png":
        im.quantize(colors=256, method=QUANT, dither=Image.Dither.NONE).save(out, optimize=True)
    else:
        jpeg(im, out, m.get("qualite", 82))
    return f"{im.width}×{im.height}"


def a_du_son(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of",
                        "csv=p=0", str(src)], capture_output=True, text=True, check=True)
    return bool(r.stdout.strip())


def video(src, out, m):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale='min(iw,1920)':-2:flags=lanczos", *VIDEO]
    cmd += SON if a_du_son(src) else ["-an"]
    subprocess.run(cmd + [str(out)], check=True)
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(m.get("affiche", 0)), "-i", str(src), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    jpeg(reduire(Image.open(io.BytesIO(png)), AFFICHE), affiche(out), 80)
    dims = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height:format=duration", "-of", "default=nw=1:nk=1", str(out)],
                          capture_output=True, text=True, check=True).stdout.split()
    return f"{dims[0]}×{dims[1]}, {float(dims[2]):.0f} s"


def affiche(out):
    return out.with_name(f"{out.stem}-poster.jpg")


def references(texte, mois):
    return set(re.findall(rf"/wp-content/uploads/{re.escape(mois)}/([\w.-]+)", texte))


def apercu(md, out):
    """L'article en HTML, chemins relatifs, shortcodes [video] changés en balises <video>."""
    texte = md.read_text(encoding="utf-8")

    def balise(m):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        boucle = " loop" if a.get("loop") == "on" else ""
        return (f'<video controls preload="metadata" playsinline{boucle} poster="{a.get("poster", "")}" '
                f'src="{a.get("mp4", "")}" width="{a.get("width", "")}" height="{a.get("height", "")}"></video>')

    texte = re.sub(r"\[video ([^\]]*)\]\[/video\]", balise, texte)
    corps = markdown.markdown(texte, extensions=["extra"]).replace('="/wp-content/', '="wp-content/')
    titre = re.search(r"^# (.+)$", texte, re.M).group(1)
    out.write_text(f"""<!doctype html>
<html lang="fr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre}</title>
<!-- Aperçu local de l'article, régénéré par pipeline/article/export_web.py : ne pas éditer à la main. -->
<style>
  body {{ margin: 0; background: #fbfaf7; color: #1d2b3a; font: 18px/1.65 Georgia, "Times New Roman", serif; }}
  main {{ max-width: 760px; margin: 0 auto; padding: 32px 20px 96px; }}
  h1 {{ font: 700 40px/1.2 "Segoe UI", system-ui, sans-serif; margin: 24px 0 12px; }}
  h2 {{ font: 700 28px/1.3 "Segoe UI", system-ui, sans-serif; margin: 56px 0 8px; }}
  h3 {{ font: 700 21px/1.35 "Segoe UI", system-ui, sans-serif; margin: 36px 0 4px; }}
  img, video {{ display: block; width: 100%; height: auto; margin: 28px 0 6px; border-radius: 4px; background: #000; }}
  p > em:only-child {{ display: block; font: 15px/1.5 "Segoe UI", system-ui, sans-serif; color: #5b6670; }}
  h1 + p > em:only-child {{ font: italic 21px/1.5 Georgia, serif; color: #1d2b3a; }}
  blockquote {{ margin: 24px 0; padding: 4px 0 4px 20px; border-left: 3px solid #c8742b; font-style: italic; }}
  table {{ border-collapse: collapse; font: 15px/1.45 "Segoe UI", system-ui, sans-serif; margin: 24px 0; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #dcd4c4; vertical-align: top; }}
  code {{ font-size: 15px; background: #f1ece2; padding: 1px 4px; border-radius: 3px; }}
</style>
<main>
{corps}
</main>
""", encoding="utf-8")


def taille(p):
    n = p.stat().st_size
    return f"{n / 1e6:.1f} Mo" if n > 1e6 else f"{n / 1e3:.0f} ko"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mois", help="année/mois de l'upload (défaut : celui de medias.yaml)")
    ap.add_argument("--sans-video", action="store_true")
    args = ap.parse_args()
    conf = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    md = ROOT / conf["article"]
    mois = args.mois or conf["mois"]
    texte = md.read_text(encoding="utf-8")
    if mois != conf["mois"]:
        texte = texte.replace(f"/wp-content/uploads/{conf['mois']}/", f"/wp-content/uploads/{mois}/")
        md.write_text(texte, encoding="utf-8")
        CONFIG.write_text(CONFIG.read_text(encoding="utf-8").replace(f'mois: "{conf["mois"]}"', f'mois: "{mois}"'),
                          encoding="utf-8")
        print(f"liens du Markdown et medias.yaml passés à {mois}")

    attendus = set()
    for nom in conf["medias"]:
        attendus.add(nom)
        if nom.endswith(".mp4"):
            attendus.add(affiche(Path(nom)).name)
    refs = references(texte, mois)
    if refs - attendus:
        sys.exit(f"cités dans l'article mais absents de medias.yaml : {', '.join(sorted(refs - attendus))}")
    if attendus - refs:
        sys.exit(f"dans medias.yaml mais pas cités dans l'article : {', '.join(sorted(attendus - refs))}")

    dest = ROOT / "article" / "wp-content" / "uploads" / mois
    dest.mkdir(parents=True, exist_ok=True)
    for p in dest.iterdir():
        if p.name not in attendus:
            p.unlink()
            print(f"retiré : {p.name}")
    for nom, m in conf["medias"].items():
        src, out = ROOT / m["src"], dest / nom
        if not src.exists():
            sys.exit(f"{nom} : source manquante {m['src']} (lancer schemas.py, graphiques.py, compositions.py "
                     "ou montage.py)")
        if out.suffix == ".mp4":
            if args.sans_video and out.exists():
                continue
            info = video(src, out, m)
        else:
            info = image(src, out, m)
        print(f"{nom:34} {info:20} {taille(out)}")
    apercu(md, ROOT / "article" / "apercu.html")
    total = sum(p.stat().st_size for p in dest.iterdir())
    print(f"{len(attendus)} fichiers dans {dest.relative_to(ROOT)}, {total / 1e6:.0f} Mo ; aperçu : article/apercu.html")


if __name__ == "__main__":
    main()
