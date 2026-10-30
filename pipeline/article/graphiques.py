"""Graphiques de l'article, calculés depuis les données du dépôt.

    python pipeline/article/graphiques.py              # tous
    python pipeline/article/graphiques.py commits      # un seul

commits : les commits de la production (17/10 14 h → 23/10 midi) heure par heure, la nuit en bandes, et au-dessus
les moments-clés tirés de HISTORY.md (heures du journal ; « ≈ » quand le journal ne donne qu'un encadrement).

Sorties : article/graphiques/<nom>.png (2600 px de large). Couleurs validées sur le fond papier (outil de
validation de palette : bleu eau #2a79a5 et orange lanterne #c8742b, contrastes et daltonismes conformes).
"""
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "article" / "graphiques"

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


GRAPHIQUES = {"commits": commits}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("noms", nargs="*")
    args = ap.parse_args()
    for nom in args.noms or GRAPHIQUES:
        GRAPHIQUES[nom]()


if __name__ == "__main__":
    main()
