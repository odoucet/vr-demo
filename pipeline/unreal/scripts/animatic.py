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
SMOOTH = unreal.MovieSceneKeyInterpolation.AUTO    # courbes : créatures et nuage de lucioles (pas de virage sec)

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


def streamed(wave):
    """Lecture en flux (chargée au fil de l'eau) : une piste de 4 min décompressée pèse ~23 Mo par canal ; avec la
    musique et dix stems, tout charger d'un coup saturerait la mémoire du Quest. Compression à l'empaquetage."""
    try:
        wave.set_editor_property("loading_behavior", unreal.SoundWaveLoadingBehavior.LOAD_ON_DEMAND)
    except Exception as e:      # propriété absente selon les versions : la valeur par défaut du projet s'applique
        unreal.log_warning(f"loading_behavior : {e}")
    return wave


def import_wav(wav, dest_dir, name):
    """Importe un WAV seulement si son contenu a changé (empreinte en métadonnée)."""
    import hashlib
    path = f"{dest_dir}/{name}"
    with open(wav, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12]
    if eal.does_asset_exist(path) and eal.get_metadata_tag(eal.load_asset(path), "source_sha1") == digest:
        return eal.load_asset(path)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = wav, dest_dir
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
    wave = streamed(eal.load_asset(path))
    eal.set_metadata_tag(wave, "source_sha1", digest)
    eal.save_loaded_asset(wave)
    return wave


# (réimportée si le WAV change : nouvelle musique d'Olivier le 18/10)
music = import_wav(os.path.join(ROOT, "Unreal", "Saved", "import", "Luminous_Wonder.wav"), "/Game/Audio/Music", "Luminous_Wonder")

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


def beat_hold(beats, i):
    """Intervalle où le beat i est tenu : entre la fin de son fondu d'entrée et le début du fondu vers le suivant.
    Fondu propre à chaque beat (fondu_s), centré sur son début avancé de avance_s (ambiance.json)."""
    b = beats[i]
    t_in = 0.0 if i == 0 else b["debut_s"] - b["avance_s"] + b["fondu_s"] / 2
    if i + 1 < len(beats):
        n = beats[i + 1]
        t_out = n["debut_s"] - n["avance_s"] - n["fondu_s"] / 2
    else:
        t_out = DURATION
    return t_in, max(t_in, t_out)


def transform_track(actor, keys, scale=None, interp=LIN):
    """keys : liste (t, (x, y, z) cm, yaw°). Interpolation linéaire (barque : vitesse constante) ou courbe
    (SMOOTH : créatures, lucioles). Pas de roulis ni de tangage."""
    binding = seq.add_possessable(actor)
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    section = track.add_section()
    section.set_range(0, end)
    ch = section.get_all_channels()  # Location XYZ, Rotation XYZ (roll, pitch, yaw), Scale XYZ
    for t, (x, y, z), yaw in keys:
        f = frame(t)
        for c, v in zip((ch[0], ch[1], ch[2], ch[5]), (x, y, z, yaw)):
            c.add_key(f, v, interpolation=interp)
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

# Musique : stéréo d'origine, ou stems spatialisés autour de la barque s'ils ont été déposés (voir plus bas).
_stems_json = os.path.join(ROOT, "Unreal", "Saved", "import", "stems.json")
STEMS = json.load(open(_stems_json, encoding="utf-8"))["stems"] if os.path.exists(_stems_json) else []
if not STEMS:
    audio_track = seq.add_track(unreal.MovieSceneAudioTrack)
    audio = audio_track.add_section()
    audio.set_sound(music)
    audio.set_range(frame(MUSIC_OFFSET).value, end)

# Fondus : noir au début de S1, fondu d'entrée de 10 s de 7,5 à 17,5 s (retours d'Olivier du 19/10 : 4 fois plus long,
# puis 5 s plus tôt ; l'image apparaît pendant le clapotis de S1), fondu de sortie sur l'extinction de la musique (événement
# « fondu-noir » du séquencier). Piste de fondu pour Movie Render Queue ; au casque (pas de post-traitement),
# même courbe sur la sphère noire devant les yeux (MPC Fondu, clés plus bas).
with open(os.path.join(ROOT, "pipeline", "sequencer.yaml"), encoding="utf-8") as f:
    _seqdef = f.read()                                      # pas de module yaml dans le Python d'Unreal


def _event_s(eid, default):
    import re
    m = re.search(r"id:\s*" + re.escape(eid) + r"\s*\n\s*music_s:\s*([\d.]+)", _seqdef)
    return MUSIC_OFFSET + (float(m.group(1)) if m else default)


T_FADE_OUT = _event_s("fondu-noir", 216.7)
T_REVEAL = _event_s("lanternes-reveal", 206.7)
FADE_IN_END, FADE_IN_S = MUSIC_OFFSET - 2.5, 10.0     # retour du 19/10 après-midi : 5 s plus tôt, même durée (7,5 → 17,5 s)
FADE_KEYS = [(0, 1.0), (FADE_IN_END - FADE_IN_S, 1.0), (FADE_IN_END, 0.0), (T_FADE_OUT, 0.0), (DURATION - 0.3, 1.0)]
fade = seq.add_track(unreal.MovieSceneFadeTrack).add_section()
fade.set_range(0, end)
fc = fade.get_all_channels()[0]
for t, v in FADE_KEYS:
    fc.add_key(frame(t), v, interpolation=LIN)

# Créatures : trajectoires calculées sur le tracé et le terrain (pipeline/layout/creatures.py). Clés en mètres
# dans le repère du tracé → Unreal (cm, y inversé) ; cap → lacet (+X du bloc dans le sens du mouvement).
# Avant la première clé et après la dernière, la créature est cachée sous le terrain.
with open(os.path.join(ROOT, "pipeline", "layout", "creatures.json"), encoding="utf-8") as f:
    CREA = json.load(f)


def creature_keys(keys, hide_before=True, hide_after=True):
    k = [(t, (x * 100, -y * 100, z * 100), -h) for t, x, y, z, h in keys]
    hid = lambda kk: (kk[1][0], kk[1][1], -6000.0)       # noqa: E731
    if hide_before:
        k = [(0.0, hid(k[0]), k[0][2]), (k[0][0] - 0.5, hid(k[0]), k[0][2])] + k
    if hide_after:
        k = k + [(k[-1][0] + 0.5, hid(k[-1]), k[-1][2]), (DURATION, hid(k[-1]), k[-1][2])]
    return k


def visible_between(label, t0, t1):
    """Acteur affiché seulement entre t0 et t1 : caché, il n'est plus dessiné du tout (mesure au casque : les
    créatures en attente sous le terrain coûtaient ~100 k triangles par image)."""
    actor = by_label.get(label)
    if actor is None:
        return
    visible_windows(label, [(t0, t1)])


def visible_windows(label, windows):
    """Acteur affiché seulement pendant les intervalles (t0, t1) donnés, caché le reste du temps."""
    actor = by_label.get(label)
    if actor is None:
        return
    vis = seq.add_possessable(actor).add_track(unreal.MovieSceneVisibilityTrack).add_section()
    vis.set_range(0, end)
    ch = vis.get_all_channels()[0]
    if windows[0][0] > 0.0:
        ch.add_key(frame(0), False)
    for t0, t1 in windows:
        ch.add_key(frame(max(t0, 0.0)), True)
        if t1 < DURATION:
            ch.add_key(frame(t1), False)


# Décor caché par la brume dense de S1-S2 (densité 0,2 : rien de visible au-delà de ~40 m) : les tronçons
# lointains ne sont affichés qu'à l'approche, au plus tard quand la brume commence à se lever (36 s).
FOG_LIFT_S = 36.0
for label in list(by_label):
    if label.startswith("GB_Vegetation"):
        k = int(label[len("GB_Vegetation"):len("GB_Vegetation") + 2])
        start = 30.0 * k - 45.0                  # 45 m avant l'entrée du tronçon (barque à 1 m/s)
        if start > 0:
            visible_between(label, min(start, FOG_LIFT_S) if start < 80 else start - 60.0, DURATION + 1)
    # lisière et collines : cachées dans la brume dense de S1-S2 (invisibles de toute façon, maintenant que la brume
    # est rendue au casque) ; l'arbre colossal reste affiché dès le début (il « apparaissait d'un coup »)
    elif label.startswith(("GB_Lisiere", "GB_Collines")):
        visible_between(label, FOG_LIFT_S, DURATION + 1)

transform_track(by_label["GB_Abysses"], creature_keys(CREA["abysses"]), interp=SMOOTH)
visible_between("GB_Abysses_Modele", CREA["abysses"][0][0], CREA["abysses"][-1][0])
for i, keys in enumerate(CREA["troupeau"]):
    transform_track(by_label[f"GB_Troupeau{i}"], creature_keys(keys), interp=SMOOTH)
    visible_between(f"GB_Troupeau{i}_Modele", keys[0][0], keys[-1][0])
transform_track(by_label["GB_Volante"], creature_keys(CREA["volante"]), interp=SMOOTH)
visible_between("GB_Volante_Modele", CREA["volante"][0][0], CREA["volante"][-1][0])

# Envol des lucioles : à la modulation (sequencer.yaml, « lucioles-envol »), le nuage sort de l'eau à 10 m devant
# la barque et monte vers la trouée de la canopée en s'étalant ; caché sous le terrain avant et après.
t_env = 137.8 + MUSIC_OFFSET   # « lucioles-envol » : 137,8 s de musique
(x0, y0, _), yaw0 = rel(t_env, 10.0, 0.0, 0.0)
(x1, y1, _), _ = rel(t_env + 22, 25.0, 0.0, 0.0)
hidden = (x0, y0, -3000.0)
# Montée en spirale large et irrégulière (retour d'Olivier : trajectoire trop droite) ; chaque luciole ajoute en
# plus ses propres boucles (matériau M_GB_LucioleEnvol, WPO de 2,6 m).
swarm = [(0.0, hidden, yaw0), (t_env - 0.5, hidden, yaw0)]
for k in range(0, 51, 2):
    u = k / 50.0
    ease = u * u * (3 - 2 * u)
    cx, cy = x0 + (x1 - x0) * 1.6 * ease, y0 + (y1 - y0) * 1.6 * ease
    ang = k * 0.32 + math.sin(k * 0.17) * 0.8
    rad = 600.0 + 900.0 * ease
    z = -150.0 + 9000.0 * ease ** 1.3
    swarm.append((t_env + k, (cx + math.cos(ang) * rad, cy + math.sin(ang) * rad, z), yaw0 + k * 4.0))
swarm.append((DURATION, swarm[-1][1][:2] + (12000.0,), swarm[-1][2]))
transform_track(by_label["GB_Lucioles"], swarm, scale=(1.0, 1.0, 1.0), interp=SMOOTH)
# nuée du lac : affichée seulement pour le final, monte lentement de 4 m
if "GB_LuciolesLac" in by_label:
    transform_track(by_label["GB_LuciolesLac"], [(0.0, (0.0, 0.0, 0.0), 0.0), (T_REVEAL - 4.0, (0.0, 0.0, 0.0), 0.0),
                                                 (DURATION, (0.0, 0.0, 400.0), 0.0)], interp=SMOOTH)
    visible_between("GB_LuciolesLac", T_REVEAL - 4.5, DURATION + 1)
# sphère de fondu : affichée seulement pendant les fondus (une surface translucide plein écran coûte même transparente)
visible_windows("GB_Fondu", [(0.0, FADE_IN_END + 0.1), (T_FADE_OUT - 0.1, DURATION + 1)])
visible_between("GB_Lucioles", t_env - 0.5, DURATION + 1)

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
    # Look peint : lumière, ombre, appoint du ciel et direction du soleil par beat (pipeline/style/ambiance.json),
    # tenus pendant le beat avec le même fondu que la brume. Direction : repère du tracé → Unreal (y inversé).
    with open(os.path.join(ROOT, "pipeline", "style", "ambiance.json"), encoding="utf-8") as f:
        amb = json.load(f)
    for i, b in enumerate(amb["beats"]):
        t_in, t_out = beat_hold(amb["beats"], i)
        sx_, sy_, sz_ = b["soleil_dir"]
        values = {"Lumiere": b["lumiere"], "Ombre": b["ombre"], "CielAppoint": b["ciel"], "SoleilDir": [sx_, -sy_, sz_],
                  "CielTeinte": b["ciel_teinte"]}
        for t in (t_in, max(t_in, t_out)):
            for name, v in values.items():
                msec.add_color_parameter_key(name, frame(t), unreal.LinearColor(*v, 1.0))
    # Apparition progressive des lucioles (retour d'Olivier : « elles apparaissent d'un coup ») : celles des berges
    # s'allument une à une pendant 10 s à la fin du noir, le nuage de l'envol en 6 s quand il sort de l'eau.
    t_env_fade = 137.8 + MUSIC_OFFSET
    for t, v in ((0.0, 0.0), (MUSIC_OFFSET - 2.0, 0.0), (MUSIC_OFFSET + 8.0, 1.0)):
        msec.add_scalar_parameter_key("LucioleFade", frame(t), v)
    for t, v in ((0.0, 0.0), (t_env_fade - 0.5, 0.0), (t_env_fade + 6.0, 1.0)):
        msec.add_scalar_parameter_key("EnvolFade", frame(t), v)
    # final : la nuée du lac s'allume en 10 s sur la dernière montée de la musique (événement lanternes-reveal)
    for t, v in ((0.0, 0.0), (T_REVEAL - 4.0, 0.0), (T_REVEAL + 6.0, 1.0)):
        msec.add_scalar_parameter_key("FinaleFade", frame(t), v)
    for t, v in FADE_KEYS:
        msec.add_scalar_parameter_key("Fondu", frame(t), v)
    # oiseaux, papillons, libellules : partent pendant la tombée de la nuit (S6), les lucioles prennent le relais
    t_nuit = _event_s("lucioles-envol", 137.8)
    for t, v in ((0.0, 1.0), (t_nuit - 8.0, 1.0), (t_nuit + 12.0, 0.0), (DURATION, 0.0)):
        msec.add_scalar_parameter_key("VieJour", frame(t), v)
    # créature des abysses : s'éteint en filant devant la barque, avant de quitter le chenal profond
    t_ab = MARKS["abysses-passage"]["t"]
    for t, v in ((0.0, 1.0), (t_ab + 4.0, 1.0), (t_ab + 11.0, 0.0), (DURATION, 0.0)):
        msec.add_scalar_parameter_key("AbyssFade", frame(t), v)
    # Barque (x, y cm, z = 0, lacet en radians) pour les shaders : lumière de la lanterne sur le décor et l'eau,
    # sillage et masque de l'eau dans la coque.
    # position de la créature des abysses pour son halo sur l'eau (shader de l'eau)
    for t, x, y, z, _h in CREA["abysses"]:
        msec.add_color_parameter_key("AbyssPos", frame(t), unreal.LinearColor(x * 100, -y * 100, z * 100, 1.0))
    for t, (bx, by, _), yaw in boat_keys:
        msec.add_color_parameter_key("Barque", frame(t), unreal.LinearColor(bx, by, math.radians(yaw), 1.0))   # lacet en z : l'alpha n'était pas transmis

# Brume par beat (pipeline/style/ambiance.json, partagé avec le rendu offline du lointain) : couleur et densité
# tenues pendant le beat, fondu de fondu_s centré sur le début de chaque beat.
with open(os.path.join(ROOT, "pipeline", "style", "ambiance.json"), encoding="utf-8") as f:
    AMBIANCE = json.load(f)
fog_comp = by_label["Brume"].component
fog_binding = seq.add_possessable(fog_comp)
color_sec = fog_binding.add_track(unreal.MovieSceneColorTrack)
color_sec.set_property_name_and_path("FogInscatteringLuminance", "FogInscatteringLuminance")
color_sec = color_sec.add_section()
color_sec.set_range(0, end)
dens_sec = fog_binding.add_track(unreal.MovieSceneFloatTrack)
dens_sec.set_property_name_and_path("FogDensity", "FogDensity")
dens_sec = dens_sec.add_section()
dens_sec.set_range(0, end)
rgba = color_sec.get_all_channels()[:4]
beats = AMBIANCE["beats"]
for i, b in enumerate(beats):
    for t in beat_hold(beats, i):
        for ch, v in zip(rgba, b["brume_lineaire"] + [1.0]):
            ch.add_key(frame(t), v)
        dens_sec.get_all_channels()[0].add_key(frame(t), b["densite"])

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
# sons de faune (portee: proche) : on les entend en passant à côté, plus du tout à 30 m
near_path = "/Game/Audio/ATT_Proche"
near_att = eal.load_asset(near_path) if eal.does_asset_exist(near_path) else tools.create_asset(
    "ATT_Proche", "/Game/Audio", unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
natt = near_att.get_editor_property("attenuation")
natt.set_editor_property("spatialize", True)
natt.set_editor_property("falloff_distance", 2500.0)
natt.set_editor_property("attenuation_shape_extents", unreal.Vector(400.0, 0, 0))
near_att.set_editor_property("attenuation", natt)
eal.save_loaded_asset(near_att, only_if_is_dirty=True)


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
    want_att = (near_att if snd.get("portee") == "proche" else attenuation) if "attach" in snd else None
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

# Stems spatialisés : chaque piste joue sur sa source attachée à la barque (atténuation douce : volume quasi
# constant, seule la direction compte) ; les pistes sans position restent en 2D.
if STEMS:
    stem_att_path = "/Game/Audio/ATT_Stems"
    stem_att = eal.load_asset(stem_att_path) if eal.does_asset_exist(stem_att_path) else tools.create_asset(
        "ATT_Stems", "/Game/Audio", unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    sa = stem_att.get_editor_property("attenuation")
    sa.set_editor_property("spatialize", True)
    sa.set_editor_property("attenuation_shape_extents", unreal.Vector(1500.0, 0, 0))
    sa.set_editor_property("falloff_distance", 3000.0)
    stem_att.set_editor_property("attenuation", sa)
    eal.save_loaded_asset(stem_att, only_if_is_dirty=True)
    for st in STEMS:
        wave = import_wav(os.path.join(ROOT, st["wav"]), "/Game/Audio/Stems", st["id"])
        want = stem_att if st["position"] else None
        if wave.get_editor_property("attenuation_settings") != want:
            wave.set_editor_property("attenuation_settings", want)
            eal.save_loaded_asset(wave)
        if st["position"] and st["id"] in by_label:
            track = seq.add_possessable(by_label[st["id"]]).add_track(unreal.MovieSceneAudioTrack)
        else:
            track = seq.add_track(unreal.MovieSceneAudioTrack)
            track.set_display_name(st["id"])
        sec = track.add_section()
        sec.set_sound(wave)
        sec.set_range(frame(MUSIC_OFFSET).value, end)
        sec.get_all_channels()[0].set_default(10 ** (st["volume_db"] / 20.0))

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
settings.set_editor_property("pause_at_end", True)           # reste au noir final (sinon l'état initial revient)
player.set_editor_property("playback_settings", settings)

eal.save_loaded_asset(seq)
levels.save_current_level()
unreal.log(f"Animatic : {path} ({DURATION:.1f} s, {FPS} i/s)")
