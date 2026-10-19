"""Convertit les sons retenus (audio/sfx/*.ogg) en WAV 48 kHz pour l'import Unreal.

    python pipeline/audio/prepare_sounds.py      # → Unreal/Saved/import/sfx/<id>.wav

Repères des créatures (cue-*) en mono : Unreal ne spatialise que les sons mono. Ambiances en stéréo.
Sonie normalisée (aperçus Freesound très inégaux) : -24 LUFS pour les ambiances, -18 LUFS pour les repères ;
les volumes de soundscape.yaml sont donc relatifs. Idempotent (date de modification, version de traitement).
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "audio" / "sfx"
DST = ROOT / "Unreal" / "Saved" / "import" / "sfx"

import yaml  # noqa: E402

# Début d'écoute par son (sounds.yaml, debut_s) : saute un passage indésirable de l'enregistrement.
SKIP = {s_["id"]: s_.get("debut_s", 0)
        for s_ in yaml.safe_load((ROOT / "pipeline" / "audio" / "sounds.yaml").read_text(encoding="utf-8"))["sounds"]}

DST.mkdir(parents=True, exist_ok=True)
for ogg in sorted(SRC.glob("*.ogg")):
    wav = DST / f"{ogg.stem}.wav"
    skip = SKIP.get(ogg.stem, 0)
    stamp = wav.with_suffix(f".v2s{skip}" if skip else ".v2")
    if wav.exists() and stamp.exists() and wav.stat().st_mtime >= ogg.stat().st_mtime:
        continue
    cue = ogg.stem.startswith(("cue-", "sfx-gue", "sfx-heron"))
    loud = "loudnorm=I=-18:TP=-2:LRA=11" if cue else "loudnorm=I=-24:TP=-2:LRA=11"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(skip), "-i", str(ogg), "-af", loud, "-ar", "48000",
                    "-ac", "1" if cue else "2", "-c:a", "pcm_s16le", str(wav)], check=True)
    stamp.touch()
    print(f"  {wav.relative_to(ROOT)}")
print(f"{len(list(DST.glob('*.wav')))} sons prêts dans {DST.relative_to(ROOT)}")

# Plan de mixage exporté en JSON pour Unreal (son Python embarqué n'a pas le module yaml).
import json  # noqa: E402

import yaml  # noqa: E402

plan = yaml.safe_load((ROOT / "pipeline" / "audio" / "soundscape.yaml").read_text(encoding="utf-8"))
(DST.parent / "soundscape.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Plan de mixage : {(DST.parent / 'soundscape.json').relative_to(ROOT)}")
