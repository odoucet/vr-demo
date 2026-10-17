"""Pré-tri des brouillons musicaux et vérification « composition figée ».

Les scores ne remplacent pas l'écoute : ils servent à classer 30 brouillons pour écouter
les meilleurs en premier, et à vérifier objectivement qu'un rendu sft garde la composition
du brouillon turbo.
"""
from pathlib import Path

import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

SR = 22050
HOP = 512


def sections(cfg):
    """Sections relatives au début de la musique : (id, début, fin, énergie cible)."""
    secs = cfg["sections"]
    out = []
    for i, s in enumerate(secs):
        end = secs[i + 1]["start"] if i + 1 < len(secs) else cfg["end_s"]
        out.append((s["id"], s["start"] - cfg["offset_s"], end - cfg["offset_s"], s["energy"]))
    return out


def loudness_db(y):
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    return librosa.amplitude_to_db(rms, ref=np.max)


def analyze(path, cfg):
    y, _ = librosa.load(path, sr=SR, mono=True)
    db = loudness_db(y)
    t = librosa.frames_to_time(np.arange(len(db)), sr=SR, hop_length=HOP)
    secs = sections(cfg)

    # Arc dramatique : la sonie moyenne par section suit-elle l'énergie cible ?
    means = [float(db[(t >= a) & (t < b)].mean()) if np.any((t >= a) & (t < b)) else -80.0 for _, a, b, _ in secs]
    rho = spearmanr(means, [e for *_, e in secs]).statistic
    rho = 0.0 if np.isnan(rho) else float(rho)
    # Un ordre correct sur 0,5 dB d'écart ne vaut rien : on pondère par la dynamique réelle (12 dB = plein).
    dyn = float(max(means) - min(means))
    arc = rho * min(1.0, dyn / 12)

    # Découpage : la segmentation automatique retombe-t-elle sur les frontières du séquencier ?
    chroma = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    mfcc = librosa.feature.mfcc(y=y, sr=SR, hop_length=HOP, n_mfcc=13)
    feats = np.vstack([librosa.util.normalize(chroma, axis=1), librosa.util.normalize(mfcc, axis=1)])
    feats = librosa.util.sync(feats, np.arange(0, feats.shape[1], int(SR / HOP)), aggregate=np.mean)  # ~1 s
    found = librosa.segment.agglomerative(feats, len(secs))[1:] * (HOP * int(SR / HOP) / SR)
    targets = [a for _, a, _, _ in secs[1:]]
    boundary_err = float(np.mean([np.min(np.abs(found - b)) for b in targets])) if len(found) else 99.0

    # Trous : silences francs avant l'outro (ACE-Step coupe parfois trop tôt).
    body = t < secs[-1][1]
    silence = float(np.mean(db[body] < -45))

    tempo = float(np.atleast_1d(librosa.beat.beat_track(y=y, sr=SR)[0])[0])
    score = 0.5 * (arc + 1) / 2 + 0.5 * np.exp(-boundary_err / 8) - 2 * silence
    return {
        "file": str(path), "duration": len(y) / SR, "score": float(score), "arc_rho": rho, "arc": arc, "dyn_db": dyn,
        "boundary_err_s": boundary_err, "silence_ratio": silence, "tempo": tempo,
        "section_db": means, "found_bounds": found.tolist(), "curve_t": t[::20].tolist(), "curve_db": db[::20].tolist(),
    }


def report(results, cfg, out_dir):
    """Écrit report.md et planche.png (courbes de sonie + frontières), triés par score."""
    out_dir = Path(out_dir)
    results = sorted(results, key=lambda r: r["score"], reverse=True)
    secs = sections(cfg)

    lines = [
        f"# Brouillons — {cfg['name']}", "",
        "Pré-tri automatique : arc de sonie vs énergie cible, frontières détectées vs séquencier, trous.",
        "**À écouter dans l'ordre, l'oreille tranche.** Retenir une seed puis : "
        "`python pipeline/audio/music.py render --lm-seed N`", "",
        "| # | Fichier | Score | Arc pondéré | Ordre (ρ) | Dynamique | Écart frontières | Silences | Tempo |",
        "|---|---------|-------|-------------|-----------|-----------|------------------|----------|-------|",
    ]
    for i, r in enumerate(results, 1):
        name = Path(r["file"]).name
        lines.append(f"| {i} | [{name}]({name}) | {r['score']:.2f} | {r['arc']:+.2f} | {r['arc_rho']:+.2f} | {r['dyn_db']:.1f} dB | "
                     f"{r['boundary_err_s']:.1f} s | {r['silence_ratio']:.0%} | {r['tempo']:.0f} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(len(results), 1, figsize=(14, 1.1 * len(results) + 0.6), sharex=True, squeeze=False)
    for ax, r in zip(axes[:, 0], results):
        ax.fill_between(r["curve_t"], -60, np.maximum(r["curve_db"], -60), color="#4a7fa8", lw=0)
        for sid, a, b, e in secs:
            ax.axvline(a, color="#d08a2e", lw=1)
            ax.text(a + 1, -8, sid.split("-")[0], fontsize=6, color="#d08a2e", va="top")
            ax.hlines(-60 + e * 10, a, b, color="#d08a2e", lw=1, ls=":")
        for b in r["found_bounds"]:
            ax.axvline(b, color="#c03030", lw=0.8, ls="--")
        ax.set_ylim(-60, 0)
        ax.set_yticks([])
        ax.set_ylabel(Path(r["file"]).stem, rotation=0, ha="right", va="center", fontsize=7)
        ax.text(1.005, 0.5, f"{r['score']:.2f}", transform=ax.transAxes, fontsize=8, va="center")
    axes[-1, 0].set_xlabel("secondes (orange : séquencier et énergie cible, rouge : frontières détectées)")
    fig.tight_layout()
    fig.savefig(out_dir / "planche.png", dpi=110)
    plt.close(fig)
    return results


def chroma_blocks(path, block_s=0.5):
    y, _ = librosa.load(path, sr=SR, mono=True)
    c = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    step = max(1, int(block_s * SR / HOP))
    c = librosa.util.sync(c, np.arange(0, c.shape[1], step), aggregate=np.mean)
    return librosa.util.normalize(c, norm=2, axis=0)


def compare(paths):
    """Similarité harmonique moyenne (cosinus des chromas, cadre à cadre) entre fichiers.

    Même composition rendue par deux DiT : proche de 1. Seeds LM différentes : nettement plus bas.
    """
    blocks = [chroma_blocks(p) for p in paths]
    n = len(blocks)
    m = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            k = min(blocks[i].shape[1], blocks[j].shape[1])
            m[i, j] = m[j, i] = float(np.mean(np.sum(blocks[i][:, :k] * blocks[j][:, :k], axis=0)))
    return m
