"""Images composées de l'article, à partir des captures, rendus et images du dépôt.

    python pipeline/article/compositions.py               # toutes
    python pipeline/article/compositions.py heros         # une seule

Sorties : builds/article/compositions/<nom>.jpg, maîtres en pleine définition, hors dépôt (l'export web réduit
et compresse : pipeline/article/export_web.py). Les images tirées des animatics demandent les vidéos de review/
(hors dépôt).
"""
import argparse
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "builds" / "article" / "compositions"
FONTS = Path("/mnt/c/Windows/Fonts")
PAPIER, ENCRE, ENCRE_2, LANTERNE = "#f6f1e7", "#1d2b3a", "#5b6670", "#c8742b"
FINALE = "review/iter-064/animatic-hd.mp4"


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ("segoeuib.ttf" if bold else "segoeui.ttf")), size)


def frame(src, t):
    """Image d'une animatique à l'instant t (secondes de balade)."""
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(ROOT / src), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB")


def image(rel):
    return Image.open(ROOT / rel).convert("RGB")


def fit(im, w, h):
    """Recadre au centre puis redimensionne à w×h."""
    r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def contain(im, w, h):
    im = im.copy()
    im.thumbnail((w, h), Image.LANCZOS)
    return im


def panneaux(cases, w, h, cols, titre=None, pad=24, legende_h=78, fleches=False):
    """Grille de panneaux légendés sur fond papier. cases : [(image, ligne en gras, ligne secondaire)]."""
    rows = -(-len(cases) // cols)
    gap = 64 if fleches else pad
    head = 76 if titre else pad
    W = pad * 2 + cols * w + (cols - 1) * gap
    H = head + rows * (h + legende_h) + (rows - 1) * pad + pad
    img = Image.new("RGB", (W, H), PAPIER)
    g = ImageDraw.Draw(img)
    if titre:
        g.text((pad, 20), titre, font=font(34, True), fill=ENCRE)
    for i, (im, haut, bas) in enumerate(cases):
        x = pad + (i % cols) * (w + gap)
        y = head + (i // cols) * (h + legende_h + pad)
        img.paste(im if im.size == (w, h) else contain(im, w, h), (x + (w - min(im.width, w)) // 2, y))
        g.text((x, y + h + 10), haut, font=font(26, True), fill=ENCRE)
        if bas:
            g.text((x, y + h + 44), bas, font=font(22), fill=ENCRE_2)
        if fleches and i % cols < cols - 1:
            ax, ay = x + w + 12, y + h // 2
            g.polygon([(ax, ay - 16), (ax + 40, ay), (ax, ay + 16)], fill=LANTERNE)
    return img


def heros():
    return frame(FINALE, 232)


def arbres_abc():
    """Première rangée de la planche iter-022 : la même forêt en A, B, C au casque."""
    planche = image("review/iter-022/planche-casque.jpg")
    return planche.crop((0, 0, planche.width, planche.height // 3))


def avant_apres():
    cases = [(fit(image("review/iter-001/S4-GUE-A.png"), 960, 540), "17/10, premier soir", "le greybox, construit par script"),
             (fit(frame(FINALE, 100), 960, 540), "23/10", "même place dans la barque, même instant (1:40)")]
    return panneaux(cases, 960, 540, 2)


def reference_resultat():
    cases = [(fit(image("refs/S2-PONTON.png"), 800, 450), "Image de référence", "Olivier, Midjourney : le départ"),
             (fit(frame(FINALE, 16), 800, 450), "Dans la démo", "le ponton à 0:16"),
             (fit(image("refs/S7-LAC.png"), 800, 450), "Image de référence", "Olivier, Midjourney : le lac final"),
             (fit(frame(FINALE, 232), 800, 450), "Dans la démo", "le lac à 3:52 ; les lanternes devenues lucioles")]
    return panneaux(cases, 800, 450, 2)


def filtre_pc():
    cases = [(fit(frame("review/iter-031/animatic.mp4", 30), 960, 540), "Rendu PC, filtre de peinture", "19/10, 11 h 50"),
             (fit(frame("review/iter-033/animatic.mp4", 30), 960, 540), "Sans le filtre", "ce que le Quest sait afficher (19/10, 12 h 07)")]
    return panneaux(cases, 960, 540, 2)


def chaine_3d():
    trellis = image("review/explorations/pont/trellis_vs_hunyuan.jpg")
    trellis = trellis.crop((0, 0, trellis.width // 2, trellis.height))
    cases = [(fit(image("refs/inbox/arche-statues.png"), 640, 400), "1. L'image d'Olivier", "Midjourney, une seule vue"),
             (fit(trellis, 640, 400), "2. Le modèle 3D", "TRELLIS.2, reconstruit en local"),
             (fit(frame(FINALE, 112), 640, 400), "3. Dans la scène", "rendu PC, 23/10"),
             (fit(image("review/iter-067/casque/112s.jpg"), 640, 400), "4. Au casque", "capture du Quest, 23/10")]
    return panneaux(cases, 640, 400, 4, fleches=True)


def chaine_sprites():
    d = "assets/textures/sprites/arbres"
    brut, masque, final = image(f"{d}/arbres_0_brut.png"), image(f"{d}/arbres_0_masque.png"), Image.open(ROOT / f"{d}/arbres_0.png")
    damier = Image.new("RGB", final.size, "#ffffff")
    g = ImageDraw.Draw(damier)
    for y in range(0, final.height, 32):
        for x in range(0, final.width, 32):
            if (x // 32 + y // 32) % 2:
                g.rectangle((x, y, x + 31, y + 31), fill="#e3e3e3")
    damier.paste(final.convert("RGBA"), (0, 0), final.convert("RGBA"))
    scene = image("review/iter-067/casque/062s.jpg")
    cases = [(fit(brut, 420, 560), "1. Image générée", "Z-Image Turbo, en local"),
             (fit(masque, 420, 560), "2. Masque", "détourage BiRefNet"),
             (fit(damier, 420, 560), "3. Image détourée", "nettoyée, prête à poser"),
             (fit(scene, 420, 560), "4. Dans la scène", "des milliers de plans peints")]
    return panneaux(cases, 420, 560, 4, fleches=True)


def statues():
    d = "review/explorations/statues"
    cases = [(fit(image(f"{d}/gardiens.png"), 640, 366), "Deux gardiens", "non retenus"),
             (fit(image(f"{d}/tete.png"), 640, 366), "Une tête couchée", "posée sur une berge"),
             (fit(image(f"{d}/arche-sculptee.png"), 640, 366), "Une arche de deux figures", "devenue le pont")]
    return panneaux(cases, 640, 366, 3)


# Une rangée de végétation, une rangée de vie : 16 des 114 images peintes (assets/textures/sprites/). Les hérons
# (vie_0, heron_*) gardent derrière eux un fond de feuillage que le jeu retire à l'affichage (« drop: green ») : écartés.
SELECTION = ["arbres/arbres_0", "arbres/arbres_5", "arbres/arbres_3", "arbres2/arbres2_5", "buissons/buissons_2",
             "fourres/fourres_3", "heros/heros_0", "eau/eau_2",
             "faune/faune_0", "faune/faune_1", "faune/faune_5", "faune/faune_3", "vie/vie_1", "vie/vie_2",
             "faune/faune_6", "nuit/nuit_0"]


def images_peintes():
    tw, th, pad, cols = 300, 380, 24, 8
    rows = -(-len(SELECTION) // cols)
    img = Image.new("RGB", (pad * 2 + cols * tw, pad + rows * (th + pad)), PAPIER)
    for i, nom in enumerate(SELECTION):
        sp = Image.open(ROOT / "assets" / "textures" / "sprites" / f"{nom}.png").convert("RGBA")
        sp = sp.crop(sp.getbbox())
        sp.thumbnail((tw - 30, th - 30), Image.LANCZOS)
        x = pad + (i % cols) * tw + (tw - sp.width) // 2
        y = pad + (i // cols) * (th + pad) + (th - sp.height)
        img.paste(sp, (x, y), sp)
    return img


COMPOSITIONS = {"heros": heros, "arbres-abc": arbres_abc, "avant-apres": avant_apres,
                "reference-resultat": reference_resultat, "filtre-pc": filtre_pc, "chaine-3d": chaine_3d,
                "chaine-sprites": chaine_sprites, "statues": statues, "images-peintes": images_peintes}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("noms", nargs="*")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for nom in args.noms or COMPOSITIONS:
        im = COMPOSITIONS[nom]()
        out = OUT / f"{nom}.jpg"
        im.save(out, quality=92)
        print(f"{out.relative_to(ROOT)} ({im.width}×{im.height})")


if __name__ == "__main__":
    main()
