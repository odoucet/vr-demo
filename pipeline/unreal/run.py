"""Exécute un script Python dans Unreal, depuis WSL.

    python pipeline/unreal/run.py pipeline/unreal/scripts/probe.py            # éditeur ouvert si possible
    python pipeline/unreal/run.py pipeline/unreal/scripts/probe.py --headless # forcer le headless

Si l'éditeur est ouvert sur le projet (exécution Python à distance activée par create_project.py), le script
y est exécuté : pas d'instance concurrente qui modifierait les mêmes assets, et le MCP reste disponible.
Sinon, commandlet headless (UnrealEditor-Cmd -run=pythonscript). Le script reçoit le chemin du dépôt dans la
variable d'environnement BARQUE_ROOT. Journal headless complet : Unreal/Saved/Logs/.
--rhi : headless avec rendu réel (captures) au lieu de -NullRHI.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import ROOT, from_windows, project, to_windows, unreal, CONFIG  # noqa: E402

UE_ROOT = from_windows(CONFIG["unreal"]["root"])
UE_PYTHON = UE_ROOT / "Engine/Binaries/ThirdParty/Python3/Win64/python.exe"
PLUGIN_PY = UE_ROOT / "Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python"
CLIENT = Path(__file__).with_name("remote_client.py")


def run_live(script, timeout=5.0):
    """Exécution dans l'éditeur ouvert. Renvoie None si aucun éditeur n'est joignable."""
    wrapper = ROOT / "Unreal" / "Saved" / "barque_remote.py"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    extra = "".join(f"os.environ[{k!r}] = {v!r}\n" for k, v in os.environ.items() if k.startswith("BARQUE_") and k != "BARQUE_ROOT")
    wrapper.write_text(
        "import os, runpy\n"
        f"os.environ['BARQUE_ROOT'] = r'{to_windows(ROOT)}'\n" + extra +
        f"runpy.run_path(r'{to_windows(Path(script).resolve())}', run_name='__main__')\n", encoding="utf-8")
    proc = subprocess.run([str(UE_PYTHON), "-X", "utf8", to_windows(CLIENT), to_windows(PLUGIN_PY), to_windows(wrapper), str(timeout)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", cwd="/mnt/c")
    if proc.returncode == 2:
        return None
    lines = [l for l in proc.stdout.splitlines() if not l.startswith("BARQUE_REMOTE_STATUS")]
    print("\n".join(lines))
    if proc.returncode != 0:
        raise SystemExit(f"Le script a échoué dans l'éditeur.\n{proc.stderr[-2000:]}")
    return proc


def run_headless(script, rhi=False, mcp=False, extra=()):
    cmd = [str(unreal("editor_cmd")), to_windows(project()), "-run=pythonscript",
           f"-script={to_windows(Path(script).resolve())}", "-unattended", "-nop4", "-nosplash",
           "-stdout", "-FullStdOutLogOutput", "-NoLogTimes"]
    if not rhi:
        cmd.append("-NullRHI")
    if mcp:
        cmd.append("-ModelContextProtocolStartServer")
    cmd += list(extra)
    # WSLENV « /p » : WSL traduit le chemin en chemin Windows pour le processus Unreal.
    # Variables Android : positionnées côté Windows par setup_android.py, mais invisibles d'une session WSL
    # ouverte avant leur création ; on les transmet explicitement (WSLENV sans drapeau = valeur telle quelle).
    from unreal.setup_android import ENV as ANDROID_ENV
    wslenv = ":".join(filter(None, [os.environ.get("WSLENV"), "BARQUE_ROOT/p", *ANDROID_ENV]))
    env = dict(os.environ, BARQUE_ROOT=str(ROOT), WSLENV=wslenv, **ANDROID_ENV)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
    keep = [l for l in proc.stdout.splitlines() if "LogPython" in l or "Error" in l or "error:" in l.lower()]
    print("\n".join(keep[-200:]))
    if proc.returncode != 0:
        raise SystemExit(f"Unreal a échoué (code {proc.returncode}). Journal : Unreal/Saved/Logs/")
    return proc


def run(script, headless=False, rhi=False, mcp=False, extra=()):
    if not headless and not rhi:
        proc = run_live(script)
        if proc is not None:
            print("(exécuté dans l'éditeur ouvert)")
            return proc
    print("(exécution headless)")
    return run_headless(script, rhi, mcp, extra)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--rhi", action="store_true")
    ap.add_argument("--mcp", action="store_true")
    args = ap.parse_args()
    run(args.script, args.headless, args.rhi, args.mcp)
