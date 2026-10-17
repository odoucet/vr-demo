"""Exécute un script Python dans Unreal en mode headless (commandlet), depuis WSL.

    python pipeline/unreal/run.py pipeline/unreal/scripts/probe.py [--rhi] [--mcp]

Le script Unreal reçoit le chemin du dépôt (format Windows) dans la variable d'environnement BARQUE_ROOT.
Journal complet : Unreal/Saved/Logs/ ; la sortie du script est relayée ici.
--rhi : rendu réel (nécessaire pour capturer des images) au lieu de -NullRHI.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import ROOT, project, to_windows, unreal  # noqa: E402


def run(script, rhi=False, mcp=False, extra=()):
    cmd = [str(unreal("editor_cmd")), to_windows(project()), "-run=pythonscript",
           f"-script={to_windows(Path(script).resolve())}", "-unattended", "-nop4", "-nosplash",
           "-stdout", "-FullStdOutLogOutput", "-NoLogTimes"]
    if not rhi:
        cmd.append("-NullRHI")
    if mcp:
        cmd.append("-ModelContextProtocolStartServer")
    cmd += list(extra)
    # WSLENV « /p » : WSL traduit le chemin en chemin Windows pour le processus Unreal.
    wslenv = ":".join(filter(None, [os.environ.get("WSLENV"), "BARQUE_ROOT/p"]))
    env = dict(os.environ, BARQUE_ROOT=str(ROOT), WSLENV=wslenv)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
    lines = proc.stdout.splitlines()
    keep = [l for l in lines if "LogPython" in l or "Error" in l or "error:" in l.lower()]
    print("\n".join(keep[-200:]))
    if proc.returncode != 0:
        raise SystemExit(f"Unreal a échoué (code {proc.returncode}). Journal : Unreal/Saved/Logs/")
    return proc


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--rhi", action="store_true")
    ap.add_argument("--mcp", action="store_true")
    args = ap.parse_args()
    run(args.script, args.rhi, args.mcp)
