"""Tracé de la rivière et trajectoire de la barque, calés sur le séquencier.

    python pipeline/layout/river.py

Lit pipeline/layout/river.yaml et pipeline/sequencer.yaml, intègre la courbure le long de la trajectoire
(vitesse constante), puis écrit :
- pipeline/layout/river.json : échantillons (t, s, x, y, cap, courbure, largeur, beat) et repères placés,
  en mètres, repère monde Z-up (x vers l'avant au départ, y vers la gauche). C'est l'entrée commune
  d'Unreal (spline), de Blender (maillage de la rivière) et des caméras de revue.
- review/layout/carte.png : vue de dessus avec beats et repères, et vitesse de rotation (confort).
Échoue si une contrainte de confort est violée (rayon minimal).
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "pipeline" / "layout" / "river.yaml"
SEQUENCER = ROOT / "pipeline" / "sequencer.yaml"
OUT_JSON = ROOT / "pipeline" / "layout" / "river.json"
OUT_PNG = ROOT / "review" / "layout" / "carte.png"


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def curvature_profile(t, bends, ramp):
    """Courbure en fonction du temps : plateaux reliés par des rampes douces (pas de saut de vitesse angulaire)."""
    k = np.zeros_like(t)
    for b in bends:
        up = smoothstep((t - (b["from"] - ramp / 2)) / ramp)
        down = 1 - smoothstep((t - (b["to"] - ramp / 2)) / ramp)
        k += b["curvature"] * up * down
    return k


def build(cfg, seq):
    off = seq["music"]["offset_s"]
    duration = off + seq["music"]["duration_s"]
    v = cfg["speed_mps"]
    dt = cfg["sample_m"] / v
    t = np.arange(0, duration + dt / 2, dt)
    s = v * t
    k = curvature_profile(t, cfg["bends"], cfg["ramp_s"])
    heading = np.concatenate([[0.0], np.cumsum(0.5 * (k[1:] + k[:-1]) * np.diff(s))])
    x = np.concatenate([[0.0], np.cumsum(np.cos(heading[:-1] + 0.5 * np.diff(heading)) * np.diff(s))])
    y = np.concatenate([[0.0], np.cumsum(np.sin(heading[:-1] + 0.5 * np.diff(heading)) * np.diff(s))])
    wt = [p["t"] for p in cfg["width"]]
    width = np.interp(t, wt, [p["w"] for p in cfg["width"]])

    beats = sorted(((b["music_s"] + off, b["id"]) for b in seq["beats"]))
    beat_at = [max((bt, bid) for bt, bid in beats if bt <= ti or bt == beats[0][0])[1] for ti in t]

    yaw_rate = np.degrees(np.abs(k) * v)
    radius_ok = np.all(np.abs(k) <= 1 / cfg["min_radius_m"] + 1e-9)

    def pose(ti):
        i = int(np.clip(np.searchsorted(t, ti), 0, len(t) - 1))
        return x[i], y[i], heading[i]

    def place(item):
        px, py, h = pose(item["t"])
        return (round(float(px + item["ahead_m"] * math.cos(h) - item["side_m"] * math.sin(h)), 2),
                round(float(py + item["ahead_m"] * math.sin(h) + item["side_m"] * math.cos(h)), 2))

    landmarks = [{**lm, **dict(zip("xy", place(lm)))} for lm in cfg["landmarks"]]
    lake = {**cfg["lake"], **dict(zip("xy", place(cfg["lake"])))}

    samples = [{"t": round(float(ti), 3), "s": round(float(si), 3), "x": round(float(xi), 3), "y": round(float(yi), 3),
                "heading_deg": round(float(math.degrees(hi)), 3), "curvature": round(float(ki), 5),
                "width_m": round(float(wi), 2), "beat": bi}
               for ti, si, xi, yi, hi, ki, wi, bi in zip(t, s, x, y, heading, k, width, beat_at)]
    beat_poses = []
    for bt, bid in beats:
        px, py, h = pose(max(bt, 0))
        beat_poses.append({"id": bid, "t": bt, "x": round(float(px), 2), "y": round(float(py), 2),
                           "heading_deg": round(math.degrees(h), 2)})
    return {
        "units": "m", "axes": "x avant au départ, y gauche, z haut", "speed_mps": v,
        "eye_height_m": 1.10, "duration_s": duration, "length_m": float(s[-1]),
        "max_yaw_rate_deg_s": round(float(yaw_rate.max()), 3), "min_radius_m": cfg["min_radius_m"],
        "beats": beat_poses, "landmarks": landmarks, "lake": lake, "samples": samples,
    }, (t, x, y, heading, width, yaw_rate, radius_ok)


def draw(data, arrays):
    t, x, y, heading, width, yaw_rate, _ = arrays
    nx, ny = -np.sin(heading), np.cos(heading)
    fig = plt.figure(figsize=(16, 10))
    ax = fig.add_axes([0.04, 0.27, 0.92, 0.68])
    ax.fill(np.r_[x + nx * width / 2, (x - nx * width / 2)[::-1]], np.r_[y + ny * width / 2, (y - ny * width / 2)[::-1]],
            color="#bcd3e0", lw=0)
    lake = data["lake"]
    ax.add_patch(plt.Circle((lake["x"], lake["y"]), lake["radius_m"], color="#bcd3e0", lw=0))
    ax.plot(x, y, color="#1f4e79", lw=1.5)
    for b in data["beats"]:
        ax.plot(b["x"], b["y"], "o", color="#222")
        ax.annotate(f"{b['id']}\n{int(b['t'] // 60)}:{b['t'] % 60:04.1f}", (b["x"], b["y"]), xytext=(6, 8),
                    textcoords="offset points", fontsize=8, fontweight="bold")
    for lm in data["landmarks"]:
        if abs(lm["ahead_m"]) > 150:
            continue
        ax.plot(lm["x"], lm["y"], "*", color="#c0392b", ms=11)
        ax.annotate(lm["id"], (lm["x"], lm["y"]), xytext=(6, -12), textcoords="offset points", fontsize=8, color="#c0392b")
    for ti in range(0, int(t[-1]) + 1, 10):
        i = np.searchsorted(t, ti)
        ax.plot(x[i], y[i], "|", color="#1f4e79", ms=6)
    ax.set_aspect("equal")
    ax.set_title(f"Tracé proposé — {data['length_m']:.0f} m à {data['speed_mps']} m/s, rotation max "
                 f"{data['max_yaw_rate_deg_s']:.2f} °/s (graduations : 10 s)")
    ax.grid(alpha=0.3)
    ax2 = fig.add_axes([0.04, 0.05, 0.92, 0.16])
    ax2.plot(t, yaw_rate, color="#7a3fa0")
    ax2.axhline(math.degrees(data["speed_mps"] / data["min_radius_m"]), color="#c0392b", ls="--", lw=1)
    for b in data["beats"]:
        ax2.axvline(b["t"], color="#999", lw=0.8)
    ax2.set_ylabel("rotation (°/s)")
    ax2.set_xlabel("temps démo (s) — pointillé rouge : limite de confort")
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=110)
    plt.close(fig)


def main():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    seq = yaml.safe_load(SEQUENCER.read_text(encoding="utf-8"))
    data, arrays = build(cfg, seq)
    if not arrays[-1]:
        raise SystemExit(f"Rayon de virage inférieur à {cfg['min_radius_m']} m : revoir les courbures de river.yaml")
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    draw(data, arrays)
    print(f"{OUT_JSON.relative_to(ROOT)} : {len(data['samples'])} échantillons, {data['length_m']:.0f} m, "
          f"rotation max {data['max_yaw_rate_deg_s']:.2f} °/s")
    for b in data["beats"]:
        print(f"  {b['id']:11s} t={b['t']:6.1f}  ({b['x']:7.1f}, {b['y']:7.1f})  cap {b['heading_deg']:6.1f}°")
    print(f"Carte : {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
