"""Lance un script bpy dans Blender en arrière-plan (exécutable Windows déclaré dans pipeline/tools.yaml).

    python pipeline/blender/run.py pipeline/blender/nettoyage_3d.py [arguments du script...]

Les chemins passés au script sont convertis en chemins Windows s'ils existent côté WSL. Code retour : celui de Blender
(le script appelle sys.exit(1) en cas d'échec).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
import tools  # noqa: E402


def exe():
    path = tools.CONFIG.get("blender", {}).get("exe")
    return tools.from_windows(path) if path else None


def run(script, *args):
    win = lambda a: tools.to_windows(Path(a).resolve()) if Path(a).exists() else str(a)  # noqa: E731
    cmd = [str(exe()), "--background", "--factory-startup", "--python-exit-code", "1", "--python", win(script), "--",
           "--root", tools.to_windows(ROOT)] + [win(a) for a in args]
    return subprocess.run(cmd, cwd="/mnt/c").returncode


if __name__ == "__main__":
    sys.exit(run(*sys.argv[1:]))
