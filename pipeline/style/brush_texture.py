"""Texture de touches de pinceau, raccordable, pour le matériau peint (M_Peint).

    python pipeline/style/brush_texture.py      # → assets/textures/pinceau.png, rides.png (512×512, gris), rides-iso.png

Projetée en coordonnées monde par le matériau : elle décale la frontière lumière / ombre (bord irrégulier,
comme un aplat posé au pinceau) et module légèrement la valeur. Bruit filtré en fréquence (raccord parfait
par construction) + touches allongées. Déterministe.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "textures" / "pinceau.png"
N = 512


def periodic_noise(rng, falloff, aniso=(1.0, 1.0)):
    fx = np.fft.fftfreq(N)[None, :] * aniso[0]
    fy = np.fft.fftfreq(N)[:, None] * aniso[1]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    spec = (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) / f ** falloff
    spec[0, 0] = 0
    n = np.real(np.fft.ifft2(spec))
    return (n - n.mean()) / n.std()


def main():
    rng = np.random.default_rng(21)
    blotch = periodic_noise(rng, 1.6)                       # grandes taches
    strokes = periodic_noise(rng, 1.5, aniso=(1.0, 0.3))    # touches allongées (horizontales)
    grain = periodic_noise(rng, 0.6)                        # grain du papier
    v = 0.6 * blotch + 0.35 * strokes + 0.05 * grain
    v = np.tanh(v * 0.9)                                    # aplats : valeurs regroupées
    v = (v - v.min()) / (v.max() - v.min())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((v * 255).astype(np.uint8), "L").save(OUT)
    print(f"{OUT.relative_to(ROOT)} ({N}×{N})")
    ripples(rng)
    ripples_iso(np.random.default_rng(33))


def band_noise(rng, freq, width=0.5):
    """Bruit raccordable isotrope, passe-bande autour de freq (cycles par pixel), centré réduit."""
    fx = np.fft.fftfreq(N)[None, :]
    fy = np.fft.fftfreq(N)[:, None]
    f = np.sqrt(fx ** 2 + fy ** 2)
    band = np.exp(-((np.log(np.maximum(f, 1e-6)) - np.log(freq)) / width) ** 2)
    v = np.real(np.fft.ifft2((rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) * band))
    return (v - v.mean()) / v.std()


def ripples_iso(rng):
    """Rides de l'eau sans direction (20/10) : les traits allongés de rides.png, orientés en travers de la rivière,
    devenaient des rayons qui convergent dès qu'on regardait sur le côté (effet « pluie » vu au casque). Ici des
    crêtes ondulées en réseau, sans direction : la perspective seule les écrase en traits horizontaux, quel que soit
    le regard. R : crêtes (lignes de niveau zéro d'un bruit passe-bande, rompues par endroits) ; G, B : pente de la
    surface (0,5 = plat), pour onduler les reflets."""
    h = band_noise(rng, 0.022)
    lines = np.exp(-(h / 0.22) ** 2)
    patch = np.clip(band_noise(rng, 0.006) * 0.6 + 0.65, 0, 1)      # rides par plaques, eau calme entre elles
    r = np.clip(lines * patch, 0, 1)
    swell = 0.7 * band_noise(rng, 0.012) + 0.3 * h
    gy, gx = np.gradient(swell)
    g = np.stack([gx, gy], -1)
    g = g / (np.abs(g).max() + 1e-6)
    rgb = np.dstack([r, 0.5 + 0.5 * g[..., 0], 0.5 + 0.5 * g[..., 1]])
    out = ROOT / "assets" / "textures" / "rides-iso.png"
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB").save(out)
    print(f"{out.relative_to(ROOT)} ({N}×{N}, RVB)")


def ripples(rng):
    """Rides de l'eau, raccordables : traits horizontaux allongés et ondulés (le matériau les oriente dans le
    sens du courant), en niveaux de gris : clair = crête qui accroche le ciel."""
    fx = np.fft.fftfreq(N)[None, :]
    fy = np.fft.fftfreq(N)[:, None]
    f = np.sqrt((fx * 8.0) ** 2 + fy ** 2)                   # étiré en x : traits horizontaux
    band = np.exp(-((np.log(np.maximum(f, 1e-6)) - np.log(0.03)) / 0.6) ** 2)   # passe-bande : traits fins
    spec = (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) * band
    v = np.real(np.fft.ifft2(spec))
    v = (v - v.mean()) / v.std()
    v = np.clip(v - 0.4, 0, None)                             # crêtes isolées sur fond calme
    v = np.clip(v / np.percentile(v, 99.5), 0, 1)
    out = ROOT / "assets" / "textures" / "rides.png"
    Image.fromarray((v * 255).astype(np.uint8), "L").save(out)
    print(f"{out.relative_to(ROOT)} ({N}×{N})")


if __name__ == "__main__":
    main()
