"""Résout les caméras de revue (pipeline/review/cameras.yaml) en poses monde à partir du tracé.

    python pipeline/review/cameras.py     # → pipeline/review/cameras.json

Chaque caméra : id (ex. S4-GUE-B), instant t, position (x, y, z) en mètres (z = yeux à 1,10 m au-dessus de
l'eau), yaw/pitch absolus en degrés (yaw 0 = axe x monde), champ de vision. Consommé par shoot.py (Unreal).
"""
import bisect
import json
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RIVER = ROOT / "pipeline" / "layout" / "river.json"
CONFIG = ROOT / "pipeline" / "review" / "cameras.yaml"
OUT = ROOT / "pipeline" / "review" / "cameras.json"


def boat_pose(samples, t):
    ts = [s["t"] for s in samples]
    i = min(max(bisect.bisect_left(ts, t), 1), len(ts) - 1)
    a, b = samples[i - 1], samples[i]
    u = 0 if b["t"] == a["t"] else (t - a["t"]) / (b["t"] - a["t"])
    lerp = lambda k: a[k] + u * (b[k] - a[k])  # noqa: E731
    return lerp("x"), lerp("y"), lerp("heading_deg")


def main():
    river = json.loads(RIVER.read_text(encoding="utf-8"))
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    marks = {lm["id"]: lm for lm in river["landmarks"]}
    cams = []
    for beat, views in cfg["cameras"].items():
        for letter, v in views.items():
            x, y, heading = boat_pose(river["samples"], v["t"])
            if "look_at" in v:
                lm = marks[v["look_at"]]
                yaw = math.degrees(math.atan2(lm["y"] - y, lm["x"] - x))
            else:
                yaw = heading + v["yaw"]
            cams.append({"id": f"{beat}-{letter}", "t": v["t"], "x": round(x, 3), "y": round(y, 3),
                         "z": river["eye_height_m"], "yaw_deg": round((yaw + 180) % 360 - 180, 2),
                         "pitch_deg": v["pitch"], "fov_deg": cfg["fov_deg"], "note": v.get("note", "")})
    OUT.write_text(json.dumps({"cameras": cams}, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in cams:
        print(f"  {c['id']:13s} t={c['t']:6.1f}  ({c['x']:6.1f}, {c['y']:6.1f}, {c['z']})  "
              f"yaw {c['yaw_deg']:7.1f}  pitch {c['pitch_deg']:4}  {c['note']}")
    print(f"{len(cams)} caméras → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
