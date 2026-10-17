"""Accès aux outils du poste (pipeline/tools.yaml) et conversion de chemins WSL ↔ Windows."""
import subprocess
from pathlib import Path, PureWindowsPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "pipeline" / "tools.yaml").read_text(encoding="utf-8"))


def to_windows(path):
    """Chemin WSL (/mnt/g/...) → chemin Windows (G:\\...), pour les exécutables Windows."""
    return subprocess.run(["wslpath", "-w", str(path)], capture_output=True, text=True, check=True).stdout.strip()


def from_windows(path):
    return Path(subprocess.run(["wslpath", "-u", str(PureWindowsPath(path))], capture_output=True, text=True, check=True).stdout.strip())


def unreal(key):
    """Chemin WSL d'un binaire Unreal (editor, editor_cmd)."""
    return from_windows(CONFIG["unreal"]["root"]) / CONFIG["unreal"][key]


def project():
    return ROOT / CONFIG["unreal"]["project"]
