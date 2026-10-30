"""Mixage 5.1 de l'animatique : la musique en stems et les sons attachés placés comme dans la démo, autour de la
caméra (demande d'Olivier, 30/10 : un son 5.1 pour la vidéo YouTube).

    python pipeline/review/mix51.py --iter 70           # review/iter-070/animatic-5.1.flac (+ la vidéo, si rendue)
    python pipeline/review/mix51.py --iter 70 --carte   # et la carte des niveaux par enceinte (vérification)

La piste stéréo de l'animatique (animatic.py) mélange la musique d'origine et le paysage sonore, repères centrés.
Celle-ci reprend ce que joue la démo : les dix stems sont des sources fixes autour du spectateur assis
(pipeline/audio/stems.yaml, préparés par prepare_stems.py) ; les repères des créatures, la faune et le héron suivent
leurs émetteurs (pipeline/layout/creatures.json, sprites.json, courbe du héron de pipeline/unreal/scripts/animatic.py),
avec les atténuations du jeu (ATT_Reperes, ATT_Proche) ; les ambiances, en 2D au casque, entourent la barque, à
l'avant et à l'arrière. La caméra regarde droit devant, dans l'axe de la barque.

Panoramique par paires d'enceintes (VBAP 2D) sur les cinq enceintes ITU-R BS.775 : centre 0°, avant ±30°, arrière
±110° ; une part diffuse, répartie sur les cinq, pour ce qui est au-dessus ou au-dessous ; le LFE reçoit les graves de
l'ensemble sous 120 Hz, à -12 dB. Niveau : même intensité perçue (EBU R128) que la piste stéréo de l'animatique.

Sorties : review/iter-NNN/animatic-5.1.flac (5.1, 48 kHz, 24 bits) et, si la vidéo 4K de l'itération existe,
review/iter-NNN/animatic-hd-5.1.mp4 : vidéo copiée, piste stéréo d'origine puis piste 5.1 (AAC 512 kb/s), sans liste
d'édition, comme le recommande YouTube. Processeur seul : pas de verrou GPU. L'agent ne peut pas écouter ce mixage : il
se vérifie par la mesure (--carte : niveau de chaque enceinte au fil du temps), puis à l'oreille.
"""
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[2]
SR = 48000
CTRL = 20                       # pas de calcul des positions des sources mobiles (Hz)
SEAT_X, EYE_Z = -1.2, 1.1       # place assise : 1,20 m derrière le centre de la barque, yeux à 1,10 m (cameras.yaml)
# Enceintes ITU-R BS.775 : azimut en degrés (positif vers la gauche) → canal, ordre ffmpeg « 5.1 » (FL FR FC LFE BL BR).
ENCEINTES = [(-110.0, 5), (-30.0, 1), (0.0, 2), (30.0, 0), (110.0, 4)]
DIFFUS = np.array([1, 1, 1, 0, 1, 1]) / math.sqrt(5)
# Atténuations du jeu (pipeline/unreal/scripts/animatic.py) : rayon à plein volume, puis décroissance linéaire (m).
ATTENUATIONS = {None: (20.0, 600.0), "proche": (4.0, 25.0)}
AMBIANCE = {0: ((0, 0.85), (4, 0.53)), 1: ((1, 0.85), (5, 0.53))}   # canal stéréo → (enceinte, gain), avant et arrière
LFE_GAIN = 10 ** (-12 / 20)
NOMS = ["FL", "FR", "FC", "LFE", "BL", "BR"]


def lire(path, canaux):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", str(canaux), "-ar", str(SR),
                          "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, canaux).T.copy()


def vbap(az):
    """Gains des cinq enceintes pour un azimut en degrés : la paire qui encadre la source, à puissance constante."""
    angs = [a for a, _ in ENCEINTES] + [ENCEINTES[0][0] + 360.0]
    chans = [c for _, c in ENCEINTES] + [ENCEINTES[0][1]]
    a = (az - angs[0]) % 360.0 + angs[0]
    for i in range(len(ENCEINTES)):
        if angs[i] <= a <= angs[i + 1]:
            r1, r2, ra = math.radians(angs[i]), math.radians(angs[i + 1]), math.radians(a)
            g = np.linalg.solve([[math.cos(r1), math.cos(r2)], [math.sin(r1), math.sin(r2)]], [math.cos(ra), math.sin(ra)])
            g = np.clip(g, 0.0, None)
            g /= np.linalg.norm(g)
            out = np.zeros(6)
            out[chans[i]] += g[0]
            out[chans[i + 1]] += g[1]
            return out
    raise ValueError(az)


def gains(devant, gauche, haut):
    """Gains des six canaux pour une source (mètres, repère de l'auditeur : devant, gauche, haut)."""
    horiz = math.hypot(devant, gauche)
    az = math.degrees(math.atan2(gauche, devant))
    elev = math.atan2(abs(haut), horiz) if horiz > 1e-6 else math.pi / 2
    e = min(0.6, math.sin(elev) ** 2)            # au-dessus ou au-dessous : une part diffuse, sur les cinq enceintes
    g = math.sqrt(1.0 - e) * vbap(az) + math.sqrt(e) * DIFFUS
    return g / np.linalg.norm(g)


def attenuation(distance, portee):
    rayon, chute = ATTENUATIONS[portee]
    return float(np.clip(1.0 - (distance - rayon) / chute, 0.0, 1.0)) if distance > rayon else 1.0


class Balade:
    """Pose de l'auditeur (place assise) le long du tracé, et passage du repère monde à son repère."""

    def __init__(self):
        s = json.loads((ROOT / "pipeline/layout/river.json").read_text(encoding="utf-8"))["samples"]
        self.t = np.array([p["t"] for p in s])
        self.x, self.y = np.array([p["x"] for p in s]), np.array([p["y"] for p in s])
        self.h = np.radians(np.array([p["heading_deg"] for p in s]))

    def relatif(self, monde, t):
        h = np.interp(t, self.t, self.h)
        ax = np.interp(t, self.t, self.x) + SEAT_X * math.cos(h)
        ay = np.interp(t, self.t, self.y) + SEAT_X * math.sin(h)
        vx, vy, vz = monde[0] - ax, monde[1] - ay, monde[2] - EYE_Z
        return vx * math.cos(h) + vy * math.sin(h), -vx * math.sin(h) + vy * math.cos(h), vz


def emetteurs(balade, offset):
    """Position de chaque émetteur dans le repère de l'auditeur : fonction du temps de balade."""
    crea = json.loads((ROOT / "pipeline/layout/creatures.json").read_text(encoding="utf-8"))
    sons = json.loads((ROOT / "pipeline/layout/sprites.json").read_text(encoding="utf-8"))["sons"]

    def piste(keys):
        k = np.array(keys, float)
        return lambda t: balade.relatif([np.interp(t, k[:, 0], k[:, i]) for i in (1, 2, 3)], t)

    # Héron : courbe de l'émetteur dans le repère de la barque (cm, axes Unreal : x devant, y à droite, z en haut),
    # avancement en smoothstep entre T_FADE_OUT - 24 et - 8 s (pipeline/unreal/scripts/animatic.py).
    seq = (ROOT / "pipeline/sequencer.yaml").read_text(encoding="utf-8")
    fondu = offset + float(re.search(r"id:\s*fondu-noir\s*\n\s*music_s:\s*([\d.]+)", seq).group(1))
    ha, hm, hb = (3200.0, -1600.0, 900.0), (150.0, -750.0, 420.0), (90.0, -58.0, 45.0)
    t0, t1 = fondu - 24.0, fondu - 8.0

    def heron(t):
        u = min(max((t - t0) / (t1 - t0), 0.0), 1.0)
        k = 1.0 - (1.0 - min(u * u * (3.0 - 2.0 * u) / 0.95, 1.0)) ** 1.8
        x, y, z = ((1 - k) ** 2 * ha[i] + 2 * (1 - k) * k * hm[i] + k * k * hb[i] for i in range(3))
        return x / 100.0 - SEAT_X, -y / 100.0, z / 100.0 - EYE_Z

    table = {"GB_Abysses": piste(crea["abysses"]), "GB_Volante": piste(crea["volante"]), "GB_Son_Heron": heron}
    for i, bete in enumerate(crea["troupeau"]):
        table[f"GB_Troupeau{i}"] = piste(bete)
    for nom, pos in sons.items():
        table[f"GB_Son_{nom}"] = (lambda p: lambda t: balade.relatif(p, t))(pos)
    return table


def enveloppe(n, d_in, d_out, volume):
    env = np.full(n, volume, np.float32)
    a, b = min(n, int(d_in * SR)), min(n, int(d_out * SR))
    if a:
        env[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    if b:
        env[n - b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)
    return env


def mixer(offset, duree):
    n_total = int(round(duree * SR))
    out = np.zeros((6, n_total), np.float32)
    balade = Balade()
    table = emetteurs(balade, offset)

    # Musique : les stems, sources fixes autour du spectateur (dans le rayon à plein volume d'ATT_Stems : seule la
    # direction compte) ; la piste « autre », sans position, à l'avant gauche et droite comme un son 2D.
    stems = json.loads((ROOT / "Unreal/Saved/import/stems.json").read_text(encoding="utf-8"))["stems"]
    s0 = int(round(offset * SR))
    for st in stems:
        vol = 10 ** (st["volume_db"] / 20.0)
        if st["position"]:
            x = lire(ROOT / st["wav"], 1)[0]
            n = min(len(x), n_total - s0)
            g = gains(*st["position"]).astype(np.float32)
            for ch in np.nonzero(g)[0]:
                out[ch, s0:s0 + n] += g[ch] * vol * x[:n]
        else:
            x = lire(ROOT / st["wav"], 2)
            n = min(x.shape[1], n_total - s0)
            out[0, s0:s0 + n] += x[0, :n] * vol
            out[1, s0:s0 + n] += x[1, :n] * vol

    # Paysage sonore : mêmes temps, volumes et fondus que l'animatique stéréo ; les sons 2D en boucle.
    plan = yaml.safe_load((ROOT / "pipeline/audio/soundscape.yaml").read_text(encoding="utf-8"))["sounds"]
    for snd in plan:
        wav = ROOT / "Unreal/Saved/import/sfx" / f"{snd['id']}.wav"
        s, e = int(round(snd["start"] * SR)), min(int(round(snd["end"] * SR)), n_total)
        n = e - s
        env = enveloppe(n, snd["fade_in"], snd["fade_out"], snd["volume"])
        if "attach" not in snd:
            x = lire(wav, 2)
            x = np.tile(x, (1, -(-n // x.shape[1])))[:, :n] * env
            for c in (0, 1):
                for ch, g in AMBIANCE[c]:
                    out[ch, s:e] += g * x[c]
            continue
        x = lire(wav, 1)[0][:n]
        n = len(x)
        pos = table[snd["attach"]]
        tc = np.arange(snd["start"], snd["start"] + n / SR + 1.0 / CTRL, 1.0 / CTRL)
        g = np.array([gains(*p) * attenuation(math.dist(p, (0, 0, 0)), snd.get("portee"))
                      for p in (pos(t) for t in tc)])
        ts = snd["start"] + np.arange(n) / SR
        for ch in (0, 1, 2, 4, 5):
            out[ch, s:s + n] += np.interp(ts, tc, g[:, ch]).astype(np.float32) * x * env[:n]

    principal = out[[0, 1, 2, 4, 5]].sum(axis=0)
    out[3] = sosfilt(butter(4, 120.0, "low", fs=SR, output="sos"), principal).astype(np.float32) * LFE_GAIN
    return out


def intensite(args_entree):
    """Intensité intégrée EBU R128 (LUFS) d'une entrée ffmpeg."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args_entree, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def carte(out, offset, png):
    """Niveau de chaque enceinte (dB) par demi-seconde, avec les repères des créatures : le mixage vu sans l'écouter."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pas = SR // 2
    m = out.shape[1] // pas
    rms = np.sqrt((out[:, :m * pas].reshape(6, m, pas) ** 2).mean(axis=2))
    db = 20 * np.log10(rms + 1e-6)
    fig, ax = plt.subplots(figsize=(14, 4.2), dpi=120)
    ax.imshow(db[[2, 0, 1, 4, 5, 3]], aspect="auto", cmap="magma", vmin=-60, vmax=-10, extent=[0, m / 2, 5.5, -0.5])
    ax.set_yticks(range(6))
    ax.set_yticklabels(["C", "FL", "FR", "BL", "BR", "LFE"])
    plan = yaml.safe_load((ROOT / "pipeline/audio/soundscape.yaml").read_text(encoding="utf-8"))["sounds"]
    for snd in plan:
        if "attach" in snd:
            ax.axvspan(snd["start"], snd["end"], ymin=0.97, ymax=1.0, color="cyan")
            ax.text(snd["start"], -0.7, snd["id"].replace("sfx-", "").replace("cue-", "▶"), fontsize=7, color="black")
    ax.set_xlabel("secondes de balade")
    fig.tight_layout()
    fig.savefig(png)
    print(f"carte : {png}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iter", type=int, required=True)
    ap.add_argument("--carte", action="store_true")
    args = ap.parse_args()
    seq = yaml.safe_load((ROOT / "pipeline/sequencer.yaml").read_text(encoding="utf-8"))
    offset = seq["music"]["offset_s"]
    duree = offset + seq["music"]["duration_s"]
    dossier = ROOT / "review" / f"iter-{args.iter:03d}"
    dossier.mkdir(parents=True, exist_ok=True)
    video = dossier / "animatic-hd.mp4"
    reference = video if video.exists() else max(ROOT.glob("review/iter-*/animatic-hd.mp4"))

    out = mixer(offset, duree)
    tmp = Path(tempfile.gettempdir()) / "barque-mix51.f32"      # 276 Mo de flottants : sur le disque local de WSL
    tmp.write_bytes(np.ascontiguousarray(out.T).tobytes())
    brut = ["-f", "f32le", "-ar", str(SR), "-ch_layout", "5.1", "-i", str(tmp)]
    cible, mesure = intensite(["-i", str(reference), "-vn"]), intensite(brut)
    gain = cible - mesure
    print(f"intensité : stéréo {cible:.1f} LUFS ({reference.relative_to(ROOT)}), 5.1 {mesure:.1f} LUFS → {gain:+.1f} dB")

    flac = dossier / "animatic-5.1.flac"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *brut, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.95:level=disabled",
                    "-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24", str(flac)], check=True)
    pic = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(flac), "-af", "astats=measure_perchannel=none",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    crete = re.findall(r"Peak level dB:\s*(-?[\d.]+)", pic)
    print(f"{flac.relative_to(ROOT)} ({flac.stat().st_size / 1e6:.0f} Mo, crête {crete[-1] if crete else '?'} dBFS)")
    if args.carte:
        carte(out * 10 ** (gain / 20.0), offset, ROOT / "builds" / "animatic" / f"carte-5.1-iter-{args.iter:03d}.png")
    tmp.unlink()

    if not video.exists():
        print(f"pas encore de vidéo {video.relative_to(ROOT)} : relancer après le rendu pour la version YouTube")
        return
    mp4 = dossier / "animatic-hd-5.1.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(flac),
                    "-map", "0:v", "-map", "0:a", "-map", "1:a", "-c:v", "copy", "-c:a:0", "copy",
                    "-c:a:1", "aac", "-b:a:1", "512k", "-disposition:a:0", "default", "-disposition:a:1", "0",
                    "-metadata:s:a:0", "title=Stéréo", "-metadata:s:a:1", "title=5.1", "-metadata:s:a:1", "language=fra",
                    "-metadata:s:a:0", "language=fra", "-movflags", "+faststart", "-use_editlist", "0", str(mp4)],
                   check=True)
    print(f"{mp4.relative_to(ROOT)} ({mp4.stat().st_size / 1e9:.2f} Go) : vidéo, piste stéréo puis piste 5.1")


if __name__ == "__main__":
    sys.exit(main())
