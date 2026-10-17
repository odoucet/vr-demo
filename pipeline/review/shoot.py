"""Captures de revue (protocole CLAUDE.md) : 3 caméras fixes par beat, PNG 1920×1080, planche contact.

    python pipeline/review/shoot.py                # nouvelle itération review/iter-NNN/
    python pipeline/review/shoot.py --iter 3       # refait l'itération 3
    python pipeline/review/shoot.py --only S4-GUE-B S6-LUNE-B

Nécessite l'éditeur ouvert sur le niveau greybox (capture du viewport réel). Pour chaque caméra de
pipeline/review/cameras.json : séquence LS_Animatic placée à l'instant t, viewport placé à la pose de la
caméra (90°, vue « jeu » sans icônes), capture haute résolution. Puis planche.jpg (ID incrustés) et, si
l'itération précédente existe, diff.jpg (avant / après des caméras qui ont changé).
"""
import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "pipeline" / "unreal"))
from tools import to_windows  # noqa: E402
import run as ue_run  # noqa: E402

CAMERAS = ROOT / "pipeline" / "review" / "cameras.json"
REVIEW = ROOT / "review"
FPS = 30
W, H = 1920, 1080

SHOT_SCRIPT = """
import unreal
# Capture par SceneCapture2D vers une cible de rendu 1920x1080 : indépendante de la fenêtre de l'éditeur
# (HighResShot ne produit rien quand le viewport n'est pas affiché).
seq = unreal.load_asset("/Game/Sequences/LS_Animatic")
lseb = unreal.LevelSequenceEditorBlueprintLibrary
if lseb.get_current_level_sequence() != seq:
    lseb.open_level_sequence(seq)
lseb.set_lock_camera_cut_to_viewport(False)
params = unreal.MovieSceneSequencePlaybackParams()
params.frame = unreal.FrameTime(unreal.FrameNumber({frame}))
params.position_type = unreal.MovieScenePositionType.FRAME
params.update_method = unreal.UpdatePositionMethod.SCRUB
lseb.set_global_position(params)
eal = unreal.EditorAssetLibrary
rt_path = "/Game/Review/RT_Review"
if eal.does_asset_exist(rt_path):
    rt = eal.load_asset(rt_path)
else:
    rt = unreal.AssetToolsHelpers.get_asset_tools().create_asset("RT_Review", "/Game/Review", unreal.TextureRenderTarget2D, unreal.TextureRenderTargetFactoryNew())
rt.set_editor_property("size_x", {w})
rt.set_editor_property("size_y", {h})
rt.set_editor_property("render_target_format", unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cap = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == "ReviewCapture"), None)
if cap is None:
    cap = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
    cap.set_actor_label("ReviewCapture")
cap.set_actor_location_and_rotation(unreal.Vector({x}, {y}, {z}), unreal.Rotator({roll}, {pitch}, {yaw}), False, False)
comp = cap.capture_component2d
comp.set_editor_property("fov_angle", {fov})
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("capture_every_frame", False)
comp.set_editor_property("capture_on_movement", False)
comp.capture_scene()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.RenderingLibrary.export_render_target(world, rt, r"{out_dir}", "{out_name}")
"""


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def next_iter():
    existing = sorted(int(p.name.split("-")[1]) for p in REVIEW.glob("iter-*") if p.name.split("-")[1].isdigit())
    return (existing[-1] + 1) if existing else 1


def shoot(cam, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    script = ROOT / "Unreal" / "Saved" / "barque_shot.py"
    script.write_text(SHOT_SCRIPT.format(
        frame=int(round(cam["t"] * FPS)), x=cam["x"] * 100, y=-cam["y"] * 100, z=cam["z"] * 100,
        roll=0.0, pitch=cam["pitch_deg"], yaw=-cam["yaw_deg"], fov=cam["fov_deg"], w=W, h=H,
        out_dir=to_windows(dest.parent), out_name=dest.name), encoding="utf-8")
    proc = ue_run.run_live(script)
    if proc is None:
        raise SystemExit("Éditeur Unreal non joignable : shoot.py a besoin de l'éditeur ouvert.")
    for _ in range(60):  # la capture est faite au rendu suivant
        if dest.exists() and dest.stat().st_size > 0:
            time.sleep(0.3)
            return dest
        time.sleep(0.5)
    raise SystemExit(f"Capture absente pour {cam['id']}")


def planche(paths, dest, title):
    tw, th = 480, 270
    cols = 3
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th + 50), "#151515")
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), title, fill="white", font=font(22))
    for i, (cid, p) in enumerate(paths):
        im = Image.open(p).convert("RGB").resize((tw, th))
        x, y = (i % cols) * tw, 50 + (i // cols) * th
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 8 + 11 * len(cid), y + 26], fill="#000000")
        d.text((x + 5, y + 4), cid, fill="#ffd27a", font=font(16))
    sheet.save(dest, quality=88)


def diff(cur_dir, prev_dir, dest, threshold=2.0):
    """Avant / après des caméras dont l'image a changé (écart moyen > threshold sur 255)."""
    pairs = []
    for p in sorted(cur_dir.glob("S*.png")):
        q = prev_dir / p.name
        if q.exists():
            a, b = Image.open(q).convert("RGB").resize((480, 270)), Image.open(p).convert("RGB").resize((480, 270))
            if sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3 > threshold:
                pairs.append((p.stem, a, b))
    if not pairs:
        return False
    sheet = Image.new("RGB", (960, 270 * len(pairs) + 40), "#151515")
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), f"{prev_dir.name} (gauche) → {cur_dir.name} (droite)", fill="white", font=font(18))
    for i, (cid, a, b) in enumerate(pairs):
        sheet.paste(a, (0, 40 + i * 270))
        sheet.paste(b, (480, 40 + i * 270))
        d.text((6, 44 + i * 270), cid, fill="#ffd27a", font=font(16))
    sheet.save(dest, quality=88)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iter", type=int)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    n = args.iter or next_iter()
    out = REVIEW / f"iter-{n:03d}"
    cams = json.loads(CAMERAS.read_text(encoding="utf-8"))["cameras"]
    if args.only:
        cams = [c for c in cams if c["id"] in args.only]
    shots = []
    for cam in cams:
        p = shoot(cam, out / f"{cam['id']}.png")
        shots.append((cam["id"], p))
        print(f"  {cam['id']}")
    all_shots = sorted((p.stem, p) for p in out.glob("S*.png"))
    planche(all_shots, out / "planche.jpg", f"La barque des lucioles — iter-{n:03d}")
    prev = REVIEW / f"iter-{n - 1:03d}"
    has_diff = prev.exists() and diff(out, prev, out / "diff.jpg")
    print(f"{out.relative_to(ROOT)} : {len(shots)} captures, planche.jpg" + (", diff.jpg" if has_diff else ""))


if __name__ == "__main__":
    main()
