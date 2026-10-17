"""Analyse de structure de la musique et planche de recalage du séquencier.

    python pipeline/audio/structure.py            # analyse la musique de pipeline/sequencer.yaml

Détecte les frontières de sections (nouveauté sur matrice d'autosimilarité chroma + MFCC, blocs de 1 s),
décrit chaque section (sonie, brillance, graves) et produit review/music/structure.png : courbes en temps
démo, frontières détectées, beats du séquencier. Le choix des beats reste éditorial : il est écrit à la main
dans pipeline/sequencer.yaml, ce script ne fait que l'éclairer et le vérifier.
"""
from pathlib import Path

import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as ss
import yaml

ROOT = Path(__file__).resolve().parents[2]
SEQUENCER = ROOT / "pipeline" / "sequencer.yaml"
OUT = ROOT / "review" / "music"
SR = 22050
HOP = 512


def features(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    fps = SR / HOP
    step = int(round(fps))
    chroma = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    mfcc = librosa.feature.mfcc(y=y, sr=SR, hop_length=HOP, n_mfcc=20)
    S = np.abs(librosa.stft(y, hop_length=HOP))
    idx = np.arange(0, chroma.shape[1], step)
    mfcc = (mfcc - mfcc.mean(1, keepdims=True)) / mfcc.std(1, keepdims=True)
    F = np.vstack([librosa.util.normalize(librosa.util.sync(chroma, idx), axis=0), librosa.util.sync(mfcc, idx) / 3])
    return {
        "t": np.arange(F.shape[1]) * step / fps,
        "F": F,
        "chroma": librosa.util.sync(chroma, idx),
        "db": 20 * np.log10(librosa.util.sync(librosa.feature.rms(S=S), idx)[0] + 1e-9),
        "centroid": librosa.util.sync(librosa.feature.spectral_centroid(S=S, sr=SR), idx)[0],
        "bass": librosa.util.sync(S[:20].sum(0, keepdims=True) / (S.sum(0, keepdims=True) + 1e-9), idx)[0],
        "duration": len(y) / SR,
    }


def novelty(F, half=8):
    """Nouveauté par noyau en damier gaussien sur la matrice d'autosimilarité (cosinus)."""
    Fn = F / (np.linalg.norm(F, axis=0, keepdims=True) + 1e-9)
    ssm = Fn.T @ Fn
    sign = np.r_[-np.ones(half), np.ones(half)]
    g = ss.windows.gaussian(2 * half, half / 2)
    kernel = np.outer(sign, sign) * np.outer(g, g)
    P = np.pad(ssm, half, mode="edge")
    nov = np.array([np.sum(P[i:i + 2 * half, i:i + 2 * half] * kernel) for i in range(ssm.shape[0])])
    return (nov - nov.min()) / np.ptp(nov)


def boundaries(feat, prominence=0.08, min_gap_s=10):
    nov = novelty(feat["F"])
    peaks, props = ss.find_peaks(nov, distance=min_gap_s, prominence=prominence)
    keep = [(feat["t"][p], float(pr)) for p, pr in zip(peaks, props["prominences"]) if 2 < feat["t"][p] < feat["duration"] - 2]
    return nov, keep


def describe(feat, cuts):
    t = feat["t"]
    edges = [0.0] + list(cuts) + [feat["duration"]]
    rows, chromas = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        k = (t >= a) & (t < b)
        ch = feat["chroma"][:, k].mean(1)
        chromas.append(ch / np.linalg.norm(ch))
        rows.append({"start": a, "end": b, "db": float(feat["db"][k].mean()),
                     "centroid": float(feat["centroid"][k].mean()), "bass": float(feat["bass"][k].mean())})
    return rows, np.array(chromas) @ np.array(chromas).T


def main():
    seq = yaml.safe_load(SEQUENCER.read_text(encoding="utf-8"))
    music = seq["music"]
    off = music["offset_s"]
    feat = features(ROOT / music["file"])
    nov, found = boundaries(feat)

    print(f"Durée : {feat['duration']:.2f} s  →  fin de la démo à {off + feat['duration']:.1f} s")
    print("Frontières détectées (temps musique / démo, proéminence) :")
    for t, p in found:
        print(f"  {t:6.1f} s / {off + t:6.1f} s  {p:.2f}")

    beats = seq["beats"]
    cuts = [b["music_s"] for b in beats if b["music_s"] > 0]
    rows, sim = describe(feat, cuts)
    print("\nSections du séquencier :")
    for b, r in zip([b for b in beats if b["music_s"] >= 0], rows):
        near = min(found, key=lambda f: abs(f[0] - b["music_s"]))[0] if found and b["music_s"] > 0 else b["music_s"]
        print(f"  {b['id']:11s} {off + r['start']:6.1f}-{off + r['end']:6.1f} s  sonie {r['db']:5.1f} dB  "
              f"brillance {r['centroid']:5.0f} Hz  graves {r['bass'] * 100:4.1f}%  (frontière détectée la plus proche : {near:.1f} s)")

    OUT.mkdir(parents=True, exist_ok=True)
    td = feat["t"] + off
    fig, axes = plt.subplots(3, 1, figsize=(16, 7.5), sharex=True)
    axes[0].fill_between(td, -60, np.maximum(feat["db"], -60), color="#4a7fa8", lw=0)
    axes[0].set_ylim(-50, -5)
    axes[0].set_ylabel("sonie (dB)")
    axes[1].plot(td, feat["centroid"], color="#c08a2e", lw=1, label="brillance (Hz)")
    ax2 = axes[1].twinx()
    ax2.plot(td, feat["bass"] * 100, color="#5a8a4a", lw=1, label="graves (%)")
    axes[1].set_ylabel("brillance (Hz)")
    ax2.set_ylabel("graves (%)")
    axes[2].plot(td, nov, color="#555", lw=1)
    axes[2].set_ylabel("nouveauté")
    for t, p in found:
        for ax in axes:
            ax.axvline(off + t, color="#c03030", lw=0.6 + 2 * p, ls="--", alpha=0.6)
    for b in seq["beats"]:
        x = off + b["music_s"]
        for ax in axes:
            ax.axvline(x, color="#222", lw=1.5)
        axes[0].text(x + 1, -7, b["id"], fontsize=8, va="top", fontweight="bold")
    for e in seq.get("events", []):
        axes[0].annotate(e["id"], (off + e["music_s"], -48), fontsize=7, color="#7a3fa0", rotation=90, va="bottom")
        axes[0].axvline(off + e["music_s"], color="#7a3fa0", lw=0.8, ls=":")
    axes[2].set_xlabel("temps démo (s) — noir : beats du séquencier, rouge : frontières détectées, violet : événements")
    ticks = np.arange(0, off + feat["duration"] + 1, 10)
    axes[2].set_xticks(ticks, [f"{int(s // 60)}:{int(s % 60):02d}" for s in ticks], fontsize=7)
    axes[0].set_title(f"{Path(music['file']).name} — recalage du séquencier")
    fig.tight_layout()
    fig.savefig(OUT / "structure.png", dpi=110)
    print(f"\nPlanche : {(OUT / 'structure.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
