"""J2 : séquence de l'animatic (LS_Animatic) sur le niveau greybox, calée sur le séquencier et la musique.

Exécuté dans Unreal (run.py) après greybox.py. Idempotent : la séquence est recréée à chaque fois.
- Barque : trajectoire de river.json, une clé par seconde, interpolation linéaire (vitesse constante,
  aucun roulis) ; la caméra du spectateur lui est attachée (yeux à 1,10 m).
- Musique : « Luminous Wonder » à partir de offset_s (0:20). S1 en noir, fondu d'entrée, fondu de sortie.
- Créatures (blocs du greybox) : passage de l'ombre des abysses sous la barque, traversée du troupeau
  devant, créature volante devant la lune au sommet de S6 ; temps tirés de river.json / sequencer.yaml.
"""
import json
import math
import os

import unreal

ROOT = os.environ["BARQUE_ROOT"]
MAP, SEQ_DIR, SEQ_NAME = "/Game/Maps/Barque_Greybox", "/Game/Sequences", "LS_Animatic"
FPS = 30

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
LIN = unreal.MovieSceneKeyInterpolation.LINEAR

with open(os.path.join(ROOT, "pipeline", "layout", "river.json"), encoding="utf-8") as f:
    RIVER = json.load(f)
MARKS = {m["id"]: m for m in RIVER["landmarks"]}
SAMPLES = RIVER["samples"]
DURATION = RIVER["duration_s"]
MUSIC_OFFSET = 20.0


def pose_at(t):
    i = min(range(len(SAMPLES)), key=lambda k: abs(SAMPLES[k]["t"] - t))
    return SAMPLES[i]


def rel(t, ahead, side, z=0.0):
    """Point relatif à la pose de la barque à l'instant t (m, side + = gauche) → Unreal (cm)."""
    p = pose_at(t)
    h = math.radians(p["heading_deg"])
    x = p["x"] + ahead * math.cos(h) - side * math.sin(h)
    y = p["y"] + ahead * math.sin(h) + side * math.cos(h)
    return (x * 100, -y * 100, z * 100), -p["heading_deg"]


levels.load_level(MAP)
by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}

# --- Musique (WAV dérivé du MP3 d'Olivier, importé une fois) ------------------------------------------------
music_path = "/Game/Audio/Music/Luminous_Wonder"
if not eal.does_asset_exist(music_path):
    task = unreal.AssetImportTask()
    task.filename = os.path.join(ROOT, "Unreal", "Saved", "import", "Luminous_Wonder.wav")
    task.destination_path = "/Game/Audio/Music"
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
music = eal.load_asset(music_path)

# --- Séquence ------------------------------------------------------------------------------------------
path = f"{SEQ_DIR}/{SEQ_NAME}"
if eal.does_asset_exist(path):
    eal.delete_asset(path)
seq = tools.create_asset(SEQ_NAME, SEQ_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(FPS, 1))
seq.set_tick_resolution(unreal.FrameRate(FPS, 1))
end = int(round(DURATION * FPS))
seq.set_playback_start(0)
seq.set_playback_end(end)


def frame(t):
    return unreal.FrameNumber(int(round(t * FPS)))


def transform_track(actor, keys, scale=None):
    """keys : liste (t, (x, y, z) cm, yaw°). Interpolation linéaire, pas de roulis ni de tangage."""
    binding = seq.add_possessable(actor)
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    section = track.add_section()
    section.set_range(0, end)
    ch = section.get_all_channels()  # Location XYZ, Rotation XYZ (roll, pitch, yaw), Scale XYZ
    for t, (x, y, z), yaw in keys:
        f = frame(t)
        for c, v in zip((ch[0], ch[1], ch[2], ch[5]), (x, y, z, yaw)):
            c.add_key(f, v, interpolation=LIN)
    s = scale or tuple(actor.get_actor_scale3d().to_tuple())
    for c, v in zip(ch[6:9], s):
        c.set_default(v)
    ch[3].set_default(0.0)
    ch[4].set_default(0.0)
    return binding


# Barque : une clé par seconde le long de la trajectoire.
boat = by_label["Barque"]
boat_keys = []
for t in range(0, int(DURATION) + 1):
    p = pose_at(t)
    boat_keys.append((t, (p["x"] * 100, -p["y"] * 100, 0.0), -p["heading_deg"]))
transform_track(boat, boat_keys)

# Caméra du spectateur.
cam_binding = seq.add_possessable(by_label["CameraBarque"])
cut_track = seq.add_track(unreal.MovieSceneCameraCutTrack)
cut = cut_track.add_section()
cut.set_range(0, end)
cut.set_camera_binding_id(seq.get_binding_id(cam_binding))

# Musique.
audio_track = seq.add_track(unreal.MovieSceneAudioTrack)
audio = audio_track.add_section()
audio.set_sound(music)
audio.set_range(frame(MUSIC_OFFSET).value, end)

# Fondus : noir pendant S1, fondu d'entrée en 2 s, fondu de sortie sur l'extinction de la musique.
fade = seq.add_track(unreal.MovieSceneFadeTrack).add_section()
fade.set_range(0, end)
fc = fade.get_all_channels()[0]
for t, v in [(0, 1.0), (MUSIC_OFFSET, 1.0), (MUSIC_OFFSET + 2.5, 0.0), (DURATION - 3.0, 0.0), (DURATION, 1.0)]:
    fc.add_key(frame(t), v, interpolation=LIN)

# Ombre des abysses : traverse sous la barque à t = 70 s, de gauche à droite, à 3,2 m sous l'eau.
t0 = MARKS["abysses-passage"]["t"]
k = []
for t, side in [(t0 - 12, 26.0), (t0, 0.0), (t0 + 12, -26.0)]:
    (x, y, z), yaw = rel(t0, 0.0, side, -3.2)
    k.append((t, (x, y, z), yaw + 90))
k = [(t0 - 30, k[0][1], k[0][2])] + k + [(DURATION, k[-1][1], k[-1][2])]
transform_track(by_label["GB_Abysses"], k)

# Troupeau : traverse 14 m devant la barque, de droite à gauche, centré sur t = 112 s ; décalé par animal.
tm = MARKS["troupeau-gue"]
for i in range(5):
    lag, lane = i * 1.6, (i % 2) * 3.0
    keys = []
    for t, side in [(tm["t"] - 9 + lag, -22.0), (tm["t"] + 9 + lag, 22.0)]:
        (x, y, z), yaw = rel(tm["t"], tm["ahead_m"] + lane, side, 0.6)
        keys.append((t, (x, y, z), yaw - 90))
    keys = [(0.0, keys[0][1], keys[0][2])] + keys + [(DURATION, keys[-1][1], keys[-1][2])]
    transform_track(by_label[f"GB_Troupeau{i}"], keys)

# Créature volante : passe devant la lune au sommet de S6 (t = 180,8 s), à 300 m, à la hauteur de la lune.
cl = MARKS["creature-lune"]
alt = cl["ahead_m"] * math.tan(math.radians(22))
keys = []
for t, side in [(cl["t"] - 12, cl["side_m"] + 160.0), (cl["t"], cl["side_m"]), (cl["t"] + 12, cl["side_m"] - 160.0)]:
    (x, y, z), yaw = rel(cl["t"], cl["ahead_m"], side, alt)
    keys.append((t, (x, y, z), yaw + 90))   # +X dans le sens du mouvement (de gauche à droite)
keys = [(0.0, keys[0][1], keys[0][2])] + keys + [(DURATION, keys[-1][1], keys[-1][2])]
transform_track(by_label["GB_Volante"], keys)

# Envol des lucioles : à la modulation (sequencer.yaml, « lucioles-envol »), le nuage sort de l'eau à 10 m devant
# la barque et monte vers la trouée de la canopée en s'étalant ; caché sous le terrain avant et après.
t_env = 137.8 + MUSIC_OFFSET   # « lucioles-envol » : 137,8 s de musique
(x0, y0, _), yaw0 = rel(t_env, 10.0, 0.0, 0.0)
(x1, y1, _), _ = rel(t_env + 22, 25.0, 0.0, 0.0)
hidden = (x0, y0, -3000.0)
transform_track(by_label["GB_Lucioles"], [
    (0.0, hidden, yaw0), (t_env - 0.5, hidden, yaw0),
    (t_env, (x0, y0, -150.0), yaw0),
    (t_env + 8, ((x0 + x1) / 2, (y0 + y1) / 2, 600.0), yaw0),
    (t_env + 22, (x1, y1, 2600.0), yaw0),
    (t_env + 22.5, hidden, yaw0), (DURATION, hidden, yaw0)], scale=(1.0, 1.0, 1.0))

# Crépuscule → nuit : luminosité du ciel peint (MPC_Ambiance.CielLuminosite), pleine en S2-S4, baisse sous les
# racines et pendant la trouée, nuit pour la lune (S6) et le lac (S7).
mpc = eal.load_asset("/Game/Greybox/MPC_Ambiance")
if mpc is not None:
    mtrack = seq.add_track(unreal.MovieSceneMaterialParameterCollectionTrack)
    mtrack.set_editor_property("mpc", mpc)
    msec = mtrack.add_section()
    msec.set_range(0, end)
    msec.add_scalar_parameter_key("CielLuminosite", frame(0), 1.0)
    for t, v in [(97.9, 1.0), (127.8, 0.8), (157.8, 0.45), (180.0, 0.28), (DURATION, 0.25)]:
        msec.add_scalar_parameter_key("CielLuminosite", frame(t), v)

# Paysage sonore (pipeline/audio/soundscape.yaml) : ambiances 2D en boucle avec fondus ; repères des créatures
# attachés à leur bloc et spatialisés (atténuation à très longue portée pour la créature volante, à 300 m).
# (soundscape.yaml exporté en JSON par pipeline/audio/prepare_sounds.py : pas de yaml dans le Python d'Unreal)
with open(os.path.join(ROOT, "Unreal", "Saved", "import", "soundscape.json"), encoding="utf-8") as f:
    SOUNDSCAPE = json.load(f)["sounds"]
att_path = "/Game/Audio/ATT_Reperes"
if eal.does_asset_exist(att_path):
    attenuation = eal.load_asset(att_path)
else:
    attenuation = tools.create_asset("ATT_Reperes", "/Game/Audio", unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
att = attenuation.get_editor_property("attenuation")
att.set_editor_property("spatialize", True)
att.set_editor_property("falloff_distance", 60000.0)    # 600 m : la créature volante passe à 300 m
att.set_editor_property("attenuation_shape_extents", unreal.Vector(2000.0, 0, 0))
attenuation.set_editor_property("attenuation", att)
eal.save_loaded_asset(attenuation, only_if_is_dirty=True)


def sound_asset(sid):
    """Importe le WAV préparé, seulement s'il a changé (empreinte en métadonnée) : pas de réécriture inutile."""
    import hashlib
    path = f"/Game/Audio/SFX/{sid}"
    wav = os.path.join(ROOT, "Unreal", "Saved", "import", "sfx", f"{sid}.wav")
    with open(wav, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12]
    if eal.does_asset_exist(path) and eal.get_metadata_tag(eal.load_asset(path), "source_sha1") == digest:
        return eal.load_asset(path)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = wav, "/Game/Audio/SFX"
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
    asset = eal.load_asset(path)
    eal.set_metadata_tag(asset, "source_sha1", digest)
    eal.save_loaded_asset(asset)
    return asset


bindings = {}
for snd in SOUNDSCAPE:
    wave = sound_asset(snd["id"])
    want_att = attenuation if "attach" in snd else None
    if wave.get_editor_property("looping") != ("attach" not in snd) or wave.get_editor_property("attenuation_settings") != want_att:
        wave.set_editor_property("looping", "attach" not in snd)
        wave.set_editor_property("attenuation_settings", want_att)
        eal.save_loaded_asset(wave)
    if "attach" in snd:
        label = snd["attach"]
        if label not in bindings:
            bindings[label] = next((b for b in seq.get_bindings() if b.get_display_name() == label), None) or seq.add_possessable(by_label[label])
        track = bindings[label].add_track(unreal.MovieSceneAudioTrack)
    else:
        track = seq.add_track(unreal.MovieSceneAudioTrack)
        track.set_display_name(snd["id"])
    section = track.add_section()
    section.set_sound(wave)
    section.set_range(frame(snd["start"]).value, frame(snd["end"]).value)
    section.set_editor_property("looping", "attach" not in snd)
    vol = section.get_all_channels()[0]   # Volume
    vol.add_key(frame(snd["start"]), 0.0, interpolation=LIN)
    vol.add_key(frame(snd["start"] + snd["fade_in"]), snd["volume"], interpolation=LIN)
    vol.add_key(frame(snd["end"] - snd["fade_out"]), snd["volume"], interpolation=LIN)
    vol.add_key(frame(snd["end"]), 0.0, interpolation=LIN)

# Lecture automatique en jeu (PIE / casque).
for a in actors.get_all_level_actors():
    if a.get_actor_label() == "SequenceAnimatic":
        actors.destroy_actor(a)
player = actors.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0, 0, 0))
player.set_actor_label("SequenceAnimatic")
player.tags = ["barque_gb"]
player.set_sequence(seq)
settings = player.get_editor_property("playback_settings")
settings.set_editor_property("auto_play", True)
settings.set_editor_property("disable_camera_cuts", True)    # en jeu : la vue est celle du casque (JoueurVR)
settings.set_editor_property("disable_movement_input", True)
player.set_editor_property("playback_settings", settings)

eal.save_loaded_asset(seq)
levels.save_current_level()
unreal.log(f"Animatic : {path} ({DURATION:.1f} s, {FPS} i/s)")
