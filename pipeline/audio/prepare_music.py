"""Prépare la musique pour Unreal : WAV 48 kHz 16 bits dérivé du fichier d'Olivier (non modifié).

    python pipeline/audio/prepare_music.py     # → Unreal/Saved/import/Luminous_Wonder.wav

Unreal importe le WAV de façon sûre ; le MP3 d'origine (audio/music/) reste la référence. Idempotent.
"""
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
seq = yaml.safe_load((ROOT / "pipeline" / "sequencer.yaml").read_text(encoding="utf-8"))
src = ROOT / seq["music"]["file"]
dst = ROOT / "Unreal" / "Saved" / "import" / "Luminous_Wonder.wav"
if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
    print(f"{dst.relative_to(ROOT)} déjà à jour")
else:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-ar", "48000",
                    "-c:a", "pcm_s16le", str(dst)], check=True)
    print(f"{dst.relative_to(ROOT)} ({dst.stat().st_size / 1e6:.0f} Mo)")
