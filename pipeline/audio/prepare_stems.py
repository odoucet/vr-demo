"""Stems de la musique → sources sonores spatialisées autour de la barque (Unreal).

    python pipeline/audio/prepare_stems.py      # audio/music/stems/* → Unreal/Saved/import/stems/*.wav + stems.json

Chaque fichier d'audio/music/stems/ (wav, mp3, flac, ogg) est reconnu par pipeline/audio/stems.yaml, converti en WAV
48 kHz mono (source ponctuelle) ou en deux sources mono gauche / droite pour les stems « larges ». Sans stems, le
JSON est vide et la séquence garde la musique stéréo d'origine. Les fichiers d'Olivier ne sont jamais modifiés.
"""
import json
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(os.environ.get("BARQUE_STEMS_DIR", ROOT / "audio" / "music" / "stems"))   # variable : tests
OUT = ROOT / "Unreal" / "Saved" / "import" / "stems"


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


SILENCE_DB = -45.0      # pic sous ce niveau : stem vide (ex. batterie d'un morceau orchestral), ignoré


def peak_db(path):
    out = subprocess.run(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    import re
    m = re.search(r"max_volume: (-?[\d.]+) dB", out)
    return float(m.group(1)) if m else -99.0


def main():
    cfg = yaml.safe_load((ROOT / "pipeline" / "audio" / "stems.yaml").read_text(encoding="utf-8"))["stems"]
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    files = sorted(p for p in SRC.glob("*") if p.suffix.lower() in (".wav", ".mp3", ".flac", ".ogg")) if SRC.exists() else []
    for f in files:
        pk = peak_db(f)
        if pk < SILENCE_DB:
            print(f"  {f.name} : vide (pic {pk:.0f} dB), ignoré")
            continue
        low = f.stem.lower()
        rule = next((r for r in cfg if any(m in low for m in r["motif"])), None)
        base = rule["nom"] if rule else "autre"
        sid = f"Stem_{base}_{len([e for e in entries if e['base'] == base])}"
        if rule and rule.get("large"):
            for ch, side in ((0, 1.0), (1, -1.0)):                      # canal gauche → à gauche
                wav = OUT / f"{sid}_{'G' if side > 0 else 'D'}.wav"
                ffmpeg("-i", str(f), "-af", f"pan=mono|c0=c{ch}", "-ar", "48000", str(wav))
                fwd, left, up = rule["position"]
                entries.append({"id": wav.stem, "base": base, "wav": str(wav.relative_to(ROOT)),
                                "position": [fwd, left + side * rule["large"], up], "volume_db": rule.get("volume", 0.0)})
        else:
            wav = OUT / f"{sid}.wav"
            ffmpeg("-i", str(f), "-ac", "1" if rule else "2", "-ar", "48000", str(wav))
            entries.append({"id": wav.stem, "base": base, "wav": str(wav.relative_to(ROOT)),
                            "position": rule["position"] if rule else None, "volume_db": rule.get("volume", 0.0) if rule else 0.0})
        print(f"  {f.name} → {base} (pic {pk:.0f} dB)")
    (ROOT / "Unreal" / "Saved" / "import" / "stems.json").write_text(json.dumps({"stems": entries}, indent=2), encoding="utf-8")
    print(f"{len(entries)} sources de stems" + ("" if entries else " (aucun stem déposé : musique stéréo d'origine)"))


if __name__ == "__main__":
    main()
