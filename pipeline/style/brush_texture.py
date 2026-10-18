"""Texture de touches de pinceau, raccordable, pour le matériau peint (M_Peint).

    python pipeline/style/brush_texture.py      # → assets/textures/pinceau.png (512×512, niveaux de gris)

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


if __name__ == "__main__":
    main()
