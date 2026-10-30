"""Graphiques de l'article, calculés depuis les données du dépôt.

    python pipeline/article/graphiques.py              # tous
    python pipeline/article/graphiques.py commits      # un seul

commits : les commits de la production (17/10 14 h → 23/10 midi) heure par heure, la nuit en bandes, et au-dessus
les moments-clés tirés de HISTORY.md (heures du journal ; « ≈ » quand le journal ne donne qu'un encadrement).
leviers : le temps GPU gagné en coupant chaque élément, essais A/B au casque (review/perf/ab-20261018-142*.txt).
lac : l'enregistrement de l'ambiance du lac lu sans l'écouter (spectre, niveau des graves), les zones écartées.
balade : la rivière vue de dessus, une image par beat, la musique et ses beats (pipeline/layout/river.json,
sequencer.yaml, animatique iter-064).
son : les stems de la musique placés autour du spectateur, vue de dessus (pipeline/audio/stems.yaml).

Sorties : builds/article/graphiques/<nom>.png (2600 px de large, maîtres hors dépôt ; versions web :
pipeline/article/export_web.py). Couleurs validées sur le fond papier (outil de
validation de palette : bleu eau #2a79a5 et orange lanterne #c8742b, contrastes et daltonismes conformes).
"""
import argparse
import io
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "builds" / "article" / "graphiques"

PAPIER, ENCRE, ENCRE_2, FILET, NUIT = "#f6f1e7", "#1d2b3a", "#5b6670", "#dcd4c4", "#ebe4d5"
EAU, LANTERNE = "#2a79a5", "#c8742b"
FONTS = Path("/mnt/c/Windows/Fonts")
for f in ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf"):
    if (FONTS / f).exists():
        font_manager.fontManager.addfont(str(FONTS / f))
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 15, "text.color": ENCRE,
                     "axes.labelcolor": ENCRE_2, "xtick.color": ENCRE_2, "ytick.color": ENCRE_2})

DEBUT, FIN = datetime(2026, 10, 17, 14), datetime(2026, 10, 23, 12)
JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

# (heure, texte, niveau de la ligne d'étiquettes) — sources : HISTORY.md et messages de commit.
MOMENTS = [
    (datetime(2026, 10, 17, 14, 30), "« C'est long et c'est moche »\n30 musiques générées, aucune écoutée", 4),
    (datetime(2026, 10, 17, 23, 7), "Itération 1\nle greybox", 1),
    (datetime(2026, 10, 18, 9, 20), "« Je ne vois pas le rendu\ndessin animé »", 3),
    (datetime(2026, 10, 18, 20, 40), "« Le truc le plus moche\nce sont les arbres »", 2),
    (datetime(2026, 10, 19, 0, 38), "Toute la forêt\nen images peintes", 1),
    (datetime(2026, 10, 19, 18, 45), "≈ « Waouh » :\nle pont, au casque", 3),
    (datetime(2026, 10, 20, 21, 40), "≈ Niagara Fluids :\n« c'est très moche »", 2),
    (datetime(2026, 10, 23, 11, 45), "Version finale\ndans le casque", 1),
]


def heures(d):
    return (d - DEBUT).total_seconds() / 3600


def commits_par_heure():
    log = subprocess.run(["git", "log", "--pretty=%aI", f"--until={FIN.isoformat()}+02:00"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    n = int(heures(FIN))
    bins = [0] * n
    for s in log:
        d = datetime.fromisoformat(s).replace(tzinfo=None)   # heure de Paris (fuseau des commits)
        if DEBUT <= d < FIN:
            bins[int(heures(d))] += 1
    return bins, len(log)


def nuits(ax):
    d = DEBUT.replace(hour=22) - timedelta(days=1)
    while d < FIN:
        a, b = max(heures(d), 0), min(heures(d + timedelta(hours=9)), heures(FIN))
        if b > a:
            ax.axvspan(a, b, color=NUIT, lw=0, zorder=0)
        d += timedelta(days=1)


def commits():
    bins, total = commits_par_heure()
    fig = plt.figure(figsize=(13, 7.8), dpi=200, facecolor=PAPIER)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.3, 1], hspace=0.04, left=0.06, right=0.985, top=0.845, bottom=0.09)
    haut, bas = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    span = heures(FIN)
    for ax in (haut, bas):
        ax.set_facecolor(PAPIER)
        ax.set_xlim(0, span + 1.5)
        nuits(ax)
        for s in ax.spines.values():
            s.set_visible(False)

    fig.text(0.06, 0.935, f"Six jours, {total} commits", fontsize=25, fontweight="bold", color=ENCRE)
    fig.text(0.06, 0.885, "Commits de l'agent, heure par heure, de la création du dépôt à la version finale. "
             "En bandes : la nuit, de 22 h à 7 h.", fontsize=15, color=ENCRE_2)

    # Barres : traits à bout arrondi, le bout bas caché sous la ligne de base ; raccourcis du rayon du bout
    # rond pour que le sommet tombe exactement sur la valeur.
    ymax = 12
    bas.set_ylim(0, ymax)
    fig.canvas.draw()
    h_px = bas.get_window_extent().height
    lw_pt = 4.2
    r = (lw_pt * fig.dpi / 72 / 2) * ymax / h_px
    for i, n in enumerate(bins):
        if n:
            bas.plot([i + 0.5, i + 0.5], [-1, n - r], color=EAU, lw=lw_pt, solid_capstyle="round", zorder=3)
    bas.set_yticks([0, 4, 8, 12])
    bas.yaxis.grid(True, color=FILET, lw=0.8, zorder=1)
    bas.tick_params(axis="y", length=0, labelsize=14)
    bas.set_ylabel("commits par heure", fontsize=14)
    bas.axhline(0, color=ENCRE_2, lw=1, zorder=4)
    jours = [DEBUT.replace(hour=0) + timedelta(days=k) for k in range(7)]
    bas.set_xticks([heures(j) for j in jours[1:]])
    bas.set_xticklabels([])
    bas.tick_params(axis="x", length=8, color=ENCRE_2)
    for j in jours:
        mid = (max(heures(j), 0) + min(heures(j + timedelta(days=1)), span)) / 2
        bas.text(mid, -1.1, f"{JOURS[j.weekday()]} {j:%d/%m}", ha="center", va="top", fontsize=14, color=ENCRE_2)
    a, b = heures(datetime(2026, 10, 21, 10, 45)), heures(datetime(2026, 10, 23, 0, 6))
    bas.text((a + b) / 2, 2.2, "37 h sans commit", ha="center", fontsize=14, color=ENCRE_2, style="italic")
    bas.annotate("", xy=(a + 1, 1.3), xytext=(b - 1, 1.3),
                 arrowprops=dict(arrowstyle="<->", color=ENCRE_2, lw=1))

    # Moments : une ligne de temps, un point par moment, l'étiquette au-dessus sur trois rangs.
    haut.set_ylim(-0.6, 5.5)
    haut.set_yticks([])
    haut.set_xticks([])
    haut.axhline(0, color=ENCRE_2, lw=1, zorder=2)
    for d, txt, niveau in MOMENTS:
        x = heures(d)
        y = niveau * 1.25 - 0.55
        haut.plot([x, x], [0, y - 0.08], color=LANTERNE, lw=1.2, zorder=2)
        haut.plot(x, 0, "o", ms=9, color=LANTERNE, mec=PAPIER, mew=2, zorder=3)
        ha = "right" if x > span * 0.9 else "left"
        dx = -0.6 if ha == "right" else 0.6
        haut.text(x + dx, y, txt, ha=ha, va="bottom", fontsize=14, color=ENCRE, linespacing=1.15, zorder=4)

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "commits.png"
    fig.savefig(out, facecolor=PAPIER)
    print(f"{out.relative_to(ROOT)} ({total} commits, max {max(bins)} par heure)")


def titres(fig, titre, sous_titre, x=0.06):
    fig.text(x, 0.94, titre, fontsize=25, fontweight="bold", color=ENCRE)
    fig.text(x, 0.895, sous_titre, fontsize=15, color=ENCRE_2)


def sauver(fig, nom):
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{nom}.png"
    fig.savefig(out, facecolor=PAPIER)
    plt.close(fig)
    print(f"{out.relative_to(ROOT)}")


def nu(ax):
    ax.set_facecolor(PAPIER)
    for s in ax.spines.values():
        s.set_visible(False)


def mmss(s):
    return f"{int(s // 60)}:{int(s % 60):02d}"


# Essais A/B du 18/10 au casque, au même instant de la balade (0:28), à deux minutes d'écart. L'anticrénelage était
# encore au réglage d'origine (l'essai suivant compare 2× à cette même référence) : la barre compare le réglage
# d'origine à l'anticrénelage coupé.
LEVIERS = {
    "showflag.staticmeshes 0": "cacher les maillages du décor",
    "r.MSAACount 1": "couper l'anticrénelage (MSAA)",
    "showflag.fog 0": "couper la brume",
    "vr.PixelDensity 0.6": "densité de pixels à 60 %",
    "showflag.translucency 0": "cacher les transparences",
    "r.ScreenPercentage 60": "résolution à 60 %",
}


def leviers():
    gains = {}
    for f in ("review/perf/ab-20261018-1422.txt", "review/perf/ab-20261018-1424.txt"):
        for line in (ROOT / f).read_text(encoding="utf-8").splitlines():
            m = re.match(r"(\S+ \S+)\s+réf .*gain ([+-][\d.]+) ms", line)
            if m and m.group(1) in LEVIERS:
                gains[m.group(1)] = float(m.group(2))
    items = sorted(gains.items(), key=lambda kv: kv[1])
    fig = plt.figure(figsize=(13, 6.6), dpi=200, facecolor=PAPIER)
    ax = fig.add_axes([0.3, 0.1, 0.66, 0.7])
    nu(ax)
    titres(fig, "Où passait le temps de calcul, mesuré au casque",
           "Temps de calcul gagné par image en coupant un élément, le 18/10 (il faut moins de 13,9 ms pour 72 i/s).")
    xmax = 9
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.6, len(items) - 0.4)
    fig.canvas.draw()
    w_px = ax.get_window_extent().width
    lw_pt = 26
    r = (lw_pt * fig.dpi / 72 / 2) * xmax / w_px
    for i, (cmd, g) in enumerate(items):
        couleur = EAU if cmd == "showflag.staticmeshes 0" else "#a9bccb"
        ax.plot([-1, max(g - r, 0.01)], [i, i], color=couleur, lw=lw_pt, solid_capstyle="round", zorder=3)
        ax.text(g + 0.12, i, f"{g:.2f} ms".replace(".", ","), va="center", fontsize=15, color=ENCRE)
        ax.text(-0.2, i, LEVIERS[cmd], va="center", ha="right", fontsize=15, color=ENCRE)
    ax.set_yticks([])
    ax.set_xticks([0, 2, 4, 6, 8])
    ax.set_xticklabels(["0", "2", "4", "6", "8 ms"])
    ax.xaxis.grid(True, color=FILET, lw=0.8, zorder=0)
    ax.tick_params(length=0, labelsize=14)
    ax.axvline(0, color=ENCRE_2, lw=1, zorder=4)
    sauver(fig, "leviers")


def lac():
    sr = 22050
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ROOT / "audio/sfx/amb-lac-nuit.ogg"), "-ac", "1", "-ar",
                          str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    duree = len(x) / sr
    n, hop = 2048, 512
    win = np.hanning(n)
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * win
    spec = 20 * np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-7).T
    freqs = np.fft.rfftfreq(n, 1 / sr)
    keep = freqs <= 1500
    half = sr // 2
    t_low, low = [], []
    for i in range(0, len(x) - half, half):
        seg = x[i:i + half]
        S = np.abs(np.fft.rfft(seg * np.hanning(half))) ** 2
        f = np.fft.rfftfreq(half, 1 / sr)
        t_low.append(i / sr + 0.25)
        low.append(10 * np.log10(S[f < 150].sum() + 1e-12))
    debut = yaml.safe_load((ROOT / "pipeline/audio/sounds.yaml").read_text(encoding="utf-8"))
    debut = next(s.get("debut_s", 0) for s in debut["sounds"] if s["id"] == "amb-lac-nuit")
    plan = yaml.safe_load((ROOT / "pipeline/audio/soundscape.yaml").read_text(encoding="utf-8"))
    joue = next(s for s in plan["sounds"] if s["id"] == "amb-lac-nuit")
    fin = debut + joue["end"] - joue["start"]

    fig = plt.figure(figsize=(13, 7.4), dpi=200, facecolor=PAPIER)
    titres(fig, "Écouter sans oreilles",
           "L'ambiance du lac (Freesound, CC0) lue par l'agent : spectre en haut, niveau des graves (< 150 Hz) en bas.")
    haut = fig.add_axes([0.07, 0.47, 0.9, 0.36])
    bas = fig.add_axes([0.07, 0.1, 0.9, 0.3], sharex=haut)
    cmap = LinearSegmentedColormap.from_list("eau", [PAPIER, "#9cc3da", EAU, "#0f2f45"])
    vmin = np.percentile(spec[keep], 5)
    haut.imshow(spec[keep], origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=np.percentile(spec[keep], 99.5),
                extent=[0, duree, 0, freqs[keep][-1]])
    haut.set_ylabel("fréquence (Hz)", fontsize=14)
    haut.tick_params(labelbottom=False, length=0, labelsize=13)
    nu(haut)
    bas.plot(t_low, low, color=EAU, lw=1.6, zorder=3)
    nu(bas)
    bas.set_ylabel("graves (dB)", fontsize=14)
    bas.tick_params(length=0, labelsize=13)
    bas.yaxis.grid(True, color=FILET, lw=0.8)
    bas.set_xlim(0, duree)
    ticks = list(range(0, int(duree) + 1, 30))
    bas.set_xticks(ticks)
    bas.set_xticklabels([mmss(t) for t in ticks])
    bas.set_xlabel("temps dans l'enregistrement", fontsize=14)
    lo, hi = bas.get_ylim()
    for ax in (haut, bas):
        ax.axvspan(0, 30, color=LANTERNE, alpha=0.16, lw=0, zorder=0 if ax is bas else 2)
        ax.axvspan(debut, fin, color=EAU, alpha=0.14, lw=0, zorder=0 if ax is bas else 2)
    bas.text(15, hi - (hi - lo) * 0.06, "une voix\n(Whisper)", ha="center", va="top", fontsize=14, color=ENCRE)
    bas.text((debut + fin) / 2, hi - (hi - lo) * 0.06, "le passage\njoué dans la démo", ha="center", va="top",
             fontsize=14, color=ENCRE)
    i = int(np.argmax(low[int(fin * 2):int(fin * 2) + 16])) + int(fin * 2)
    bas.annotate("le grondement :\n« une voiture qui démarre »", xy=(t_low[i] + 0.6, low[i] + 0.4),
                 xytext=(t_low[i] - 3, hi - (hi - lo) * 0.27), fontsize=14, color=ENCRE, va="center",
                 arrowprops=dict(arrowstyle="-", color=ENCRE_2, lw=1))
    j = int(np.argmax(low))
    bas.annotate("plus loin, d'autres grondements", xy=(t_low[j] + 1, low[j]), xytext=(t_low[j] + 12, hi - (hi - lo) * 0.08),
                 fontsize=14, color=ENCRE, va="center", arrowprops=dict(arrowstyle="-", color=ENCRE_2, lw=1))
    sauver(fig, "lac")


def frame(src, t):
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(ROOT / src), "-frames:v", "1",
                          "-vf", "scale=640:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True, check=True).stdout
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))


# Un instant par beat dans l'animatique finale, et le nom du beat dans l'article.
BEATS = {"S1-NOIR": ("le noir, la brume", 12), "S2-PONTON": ("le ponton", 30), "S3-ABYSSE": ("la bête sous l'eau", 70),
         "S4-GUE": ("le gué, le pont", 105), "S5-RACINES": ("sous le pont", 132), "S6-LUNE": ("la lune", 185),
         "S7-LAC": ("le lac", 232)}


def balade():
    river = json.loads((ROOT / "pipeline/layout/river.json").read_text(encoding="utf-8"))
    seq = yaml.safe_load((ROOT / "pipeline/sequencer.yaml").read_text(encoding="utf-8"))
    offset = seq["music"]["offset_s"]
    fin = offset + seq["music"]["duration_s"]
    debuts = [offset + b["music_s"] for b in seq["beats"]]

    fig = plt.figure(figsize=(13, 9.4), dpi=200, facecolor=PAPIER)
    titres(fig, "La balade : 239 mètres, quatre minutes, sept moments",
           "La rivière vue de dessus, une image par moment, et la musique sur laquelle tout est calé.")
    carte = fig.add_axes([0.04, 0.49, 0.92, 0.38])
    nu(carte)
    xs = [s["x"] for s in river["samples"]]
    ys = [s["y"] for s in river["samples"]]
    lake = river["lake"]
    carte.add_patch(Circle((lake["x"], lake["y"]), lake["radius_m"], color="#cfe0ea", lw=0, zorder=1))
    carte.plot(xs, ys, color="#cfe0ea", lw=22, solid_capstyle="round", zorder=1)
    carte.plot(xs, ys, color=EAU, lw=2.5, zorder=2)
    for k, b in enumerate(river["beats"]):
        carte.plot(b["x"], b["y"], "o", ms=11, color=LANTERNE, mec=PAPIER, mew=2.5, zorder=4)
        nom = BEATS[b["id"]][0]
        if k == 0:
            carte.text(b["x"] - 9, b["y"], f"{nom}\n{mmss(debuts[k])}", ha="right", va="center", fontsize=13,
                       color=ENCRE, linespacing=1.1, zorder=5)
            continue
        dy = 12 if k % 2 == 0 else -12
        carte.text(b["x"], b["y"] + dy, f"{nom}\n{mmss(debuts[k])}", ha="center", va="bottom" if dy > 0 else "top",
                   fontsize=13, color=ENCRE, linespacing=1.1, zorder=5)
    carte.set_aspect("equal")
    carte.set_xticks([])
    carte.set_yticks([])
    carte.plot([278, 328], [-22, -22], color=ENCRE_2, lw=2)
    carte.text(303, -26, "50 m", ha="center", va="top", fontsize=13, color=ENCRE_2)

    w = 0.92 / 7
    for k, b in enumerate(seq["beats"]):
        ax = fig.add_axes([0.04 + k * w + 0.004, 0.29, w - 0.008, w * 13 / 9.4 * 9 / 16])
        ax.imshow(frame("review/iter-064/animatic-hd.mp4", BEATS[b["id"]][1]))
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(BEATS[b["id"]][0], fontsize=12.5, color=ENCRE, pad=5)

    onde = fig.add_axes([0.04, 0.07, 0.92, 0.16])
    nu(onde)
    sr = 4000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ROOT / seq["music"]["file"]), "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32)
    step = sr // 5
    env = np.sqrt(np.convolve(a ** 2, np.ones(step) / step, mode="valid")[::step])
    t = offset + np.arange(len(env)) / 5
    onde.fill_between(t, -env, env, color="#a9bccb", lw=0)
    onde.set_xlim(0, fin)
    for k, d in enumerate(debuts):
        onde.axvline(d, color=LANTERNE, lw=1.2)
    ticks = list(range(0, int(fin) + 1, 30))
    onde.set_xticks(ticks)
    onde.set_xticklabels([mmss(x) for x in ticks])
    onde.set_yticks([])
    onde.tick_params(length=0, labelsize=13)
    onde.text(0, 1.04, "La musique, « Luminous Wonder » (Suno) ; en orange, le début de chaque moment",
              transform=onde.transAxes, fontsize=13, color=ENCRE_2, va="bottom")
    onde.text(0.8, -env.max() * 0.9, "noir,\nclapotis", fontsize=12, color=ENCRE_2, va="bottom")
    sauver(fig, "balade")


NOMS_STEMS = {"piano": "clavier", "cordes": "cordes", "basses": "basses", "bois": "bois", "cuivres": "cuivres",
              "guitare": "guitare", "nappe": "nappe de synthé", "percussions": "batterie, percussions"}


def son():
    stems = yaml.safe_load((ROOT / "pipeline/audio/stems.yaml").read_text(encoding="utf-8"))["stems"]
    deposes = [p.stem.lower() for p in (ROOT / "audio/music/stems").glob("*.flac")]
    fig = plt.figure(figsize=(13, 9.2), dpi=200, facecolor=PAPIER)
    titres(fig, "La musique, autour de la barque",
           "Vue de dessus : les pistes séparées du morceau (stems de Suno), chacune placée autour du spectateur assis.")
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.8])
    nu(ax)
    ax.set_aspect("equal")
    ax.set_xlim(-9, 9)
    ax.set_ylim(-7.5, 7.2)
    ax.set_xticks([])
    ax.set_yticks([])
    for rayon in (2, 4, 6):
        ax.add_patch(Circle((0, 0), rayon, fill=False, color=FILET, lw=1, zorder=0))
        ax.text(rayon * 0.71 + 0.1, -rayon * 0.71 - 0.1, f"{rayon} m", fontsize=12, color=ENCRE_2)
    coque = [(0, 2.95), (0.62, 1.6), (0.66, 0.2), (0.5, -0.55), (-0.5, -0.55), (-0.66, 0.2), (-0.62, 1.6)]
    ax.add_patch(Polygon(coque, closed=True, color="#b5794a", alpha=0.9, lw=0, zorder=2))
    ax.plot(0, 0, "o", ms=10, color=ENCRE, zorder=4)
    ax.text(-0.85, -0.1, "spectateur", fontsize=13, color=ENCRE, zorder=5, va="center", ha="right")
    ax.text(0, 3.2, "devant", fontsize=13, color=ENCRE_2, ha="center", va="bottom")
    for s in stems:
        if not any(any(m in d for m in s["motif"]) for d in deposes):
            continue
        devant, gauche, haut = s["position"]
        nom = NOMS_STEMS.get(s["nom"], s["nom"])
        ou = " (au-dessus)" if haut >= 1.5 else " (sous la barque)" if haut < 0 else ""
        points = [(-(gauche + s["large"]), devant), (-(gauche - s["large"]), devant)] if s.get("large") else [(-gauche, devant)]
        for x, y in points:
            if y > 6.5:
                ax.text(x + 0.5, 6.6, f"{nom}, à {devant:.0f} m devant", fontsize=14, color=ENCRE, va="center")
                ax.plot(x, 6.6, "o", ms=13, color=EAU, mec=PAPIER, mew=2.5, zorder=4)
                continue
            ax.plot(x, y, "o", ms=13, color=EAU, mec=PAPIER, mew=2.5, zorder=4)
            if abs(x) < 0.5:
                ax.text(x + 0.5, y, nom + ou, fontsize=14, color=ENCRE, va="center")
            else:
                ax.text(x + (0.4 if x >= 0 else -0.4), y + 0.35, nom + ou, fontsize=14, color=ENCRE,
                        ha="left" if x >= 0 else "right", va="bottom")
    ax.text(-8.8, -7.2, "La piste « autre » reste au centre, non spatialisée.", fontsize=13, color=ENCRE_2)
    sauver(fig, "son")


GRAPHIQUES = {"commits": commits, "leviers": leviers, "lac": lac, "balade": balade, "son": son}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("noms", nargs="*")
    args = ap.parse_args()
    for nom in args.noms or GRAPHIQUES:
        GRAPHIQUES[nom]()


if __name__ == "__main__":
    main()
