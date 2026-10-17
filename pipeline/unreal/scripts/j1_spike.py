"""J1 : scène de test « sphère vidéo 360 stéréo + synchronisation », exécutée dans Unreal (run.py).

Construit (idempotent) :
- /Game/Spike : source vidéo (Content/Movies/test360_j1.mp4), lecteur, texture média ;
- M_Sphere360Stereo : matériau non éclairé qui calcule les coordonnées équirectangulaires à partir de la
  direction de vue et choisit la moitié haute (œil gauche) ou basse (œil droit) selon l'œil rendu.
  La sphère est donc à l'infini optique : seule la vidéo porte la stéréo, comme prévu pour le lointain ;
- /Game/Maps/J1_Spike : sphère de 1 km de diamètre centrée sur le joueur, témoin de synchronisation
  (cube rouge à 3 m devant, visible une image par seconde, piloté par la séquence), départ du joueur ;
- LS_J1 : séquence de 60 s à 30 i/s avec une piste média qui pilote le lecteur (même horloge que la
  séquence) et le son de la vidéo (bips), lancée automatiquement.
Au casque : le flash blanc de la vidéo et le cube rouge doivent apparaître ensemble, en même temps que le bip.
"""
import unreal

SPIKE, MAPS = "/Game/Spike", "/Game/Maps"
LEVEL = f"{MAPS}/J1_Spike"
TAG = "barque_j1"
FPS, DURATION_S = 30, 60

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def asset(name, folder, cls, factory):
    path = f"{folder}/{name}"
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    return tools.create_asset(name, folder, cls, factory)


# --- Média -----------------------------------------------------------------------------------------
source = asset("FMS_Test360", SPIKE, unreal.FileMediaSource, unreal.FileMediaSourceFactoryNew())
source.set_file_path("./Movies/test360_j1.mp4")
player = asset("MP_Test360", SPIKE, unreal.MediaPlayer, unreal.MediaPlayerFactoryNew())
player.set_editor_property("play_on_open", True)
texture = asset("MT_Test360", SPIKE, unreal.MediaTexture, unreal.MediaTextureFactoryNew())
texture.set_editor_property("media_player", player)

# --- Matériau sphère 360 stéréo -------------------------------------------------------------------------
CODE = """float3 d = normalize(-Dir);
float u = 0.5 + atan2(d.y, d.x) / (2.0 * PI);
float v = acos(clamp(d.z, -1.0, 1.0)) / PI;
float eye = ResolvedView.StereoPassIndex;
return float2(u, v * 0.5 + eye * 0.5);"""

mat = asset("M_Sphere360Stereo", SPIKE, unreal.Material, unreal.MaterialFactoryNew())
mel.delete_all_material_expressions(mat)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("two_sided", True)
camvec = mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -700, 0)
custom = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -450, 0)
custom.set_editor_property("code", CODE)
custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
custom.set_editor_property("description", "Equirect TB stéréo")
dir_input = unreal.CustomInput()
dir_input.set_editor_property("input_name", "Dir")
custom.set_editor_property("inputs", [dir_input])
sample = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -200, 0)
sample.set_editor_property("texture", texture)
sample.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
mel.connect_material_expressions(camvec, "", custom, "Dir")
mel.connect_material_expressions(custom, "", sample, "UVs")
mel.connect_material_property(sample, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.recompile_material(mat)

flash_mat = asset("M_FlashRouge", SPIKE, unreal.Material, unreal.MaterialFactoryNew())
mel.delete_all_material_expressions(flash_mat)
flash_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
red = mel.create_material_expression(flash_mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
red.set_editor_property("constant", unreal.LinearColor(1, 0, 0, 1))
mel.connect_material_property(red, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.recompile_material(flash_mat)

# --- Niveau --------------------------------------------------------------------------------------------
if eal.does_asset_exist(LEVEL):
    levels.load_level(LEVEL)
else:
    levels.new_level(LEVEL)
for a in actors.get_all_level_actors():
    if TAG in [str(t) for t in a.tags]:
        actors.destroy_actor(a)


def spawn(obj, loc, label, rot=unreal.Rotator(0, 0, 0)):
    a = actors.spawn_actor_from_object(obj, loc, rot)
    a.set_actor_label(label)
    a.tags = [TAG]
    return a


sphere = spawn(eal.load_asset("/Engine/BasicShapes/Sphere"), unreal.Vector(0, 0, 110), "Sphere360")
sphere.set_actor_scale3d(unreal.Vector(1000, 1000, 1000))  # 1 km de diamètre
smc = sphere.static_mesh_component
smc.set_material(0, mat)
smc.set_editor_property("cast_shadow", False)
smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)

cube = spawn(eal.load_asset("/Engine/BasicShapes/Cube"), unreal.Vector(300, 0, 80), "TemoinSynchro")
cube.set_actor_scale3d(unreal.Vector(0.2, 0.2, 0.2))
cube.static_mesh_component.set_material(0, flash_mat)
cube.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)

start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 0))
start.set_actor_label("Depart")
start.tags = [TAG]

# Son de la vidéo : composant MediaSound ajouté à la sphère.
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
root = sds.k2_gather_subobject_data_for_instance(sphere)[0]
params = unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.MediaSoundComponent)
handle, fail = sds.add_new_subobject(params)
sound = sphere.get_component_by_class(unreal.MediaSoundComponent)
sound.set_media_player(player)

# --- Séquence ------------------------------------------------------------------------------------------
seq_path = f"{SPIKE}/LS_J1"
if eal.does_asset_exist(seq_path):
    eal.delete_asset(seq_path)
seq = tools.create_asset("LS_J1", SPIKE, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(FPS, 1))
seq.set_tick_resolution(unreal.FrameRate(FPS, 1))
seq.set_playback_start(0)
seq.set_playback_end(FPS * DURATION_S)

media_track = seq.add_track(unreal.MovieSceneMediaTrack)
media = media_track.add_section()
media.set_range(0, FPS * DURATION_S)
media.set_editor_property("media_source", source)
media.set_editor_property("use_external_media_player", True)
media.set_editor_property("external_media_player", player)
media.set_editor_property("media_texture", texture)

binding = seq.add_possessable(cube)
vis = binding.add_track(unreal.MovieSceneVisibilityTrack)
vis_section = vis.add_section()
vis_section.set_range(0, FPS * DURATION_S)
channel = vis_section.get_all_channels()[0]
for s in range(DURATION_S):
    channel.add_key(unreal.FrameNumber(s * FPS), True)       # visible pendant la 1re image de chaque seconde
    channel.add_key(unreal.FrameNumber(s * FPS + 1), False)

seq_actor = actors.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0, 0, 0))
seq_actor.set_actor_label("SequenceJ1")
seq_actor.tags = [TAG]
seq_actor.set_sequence(seq)
settings = seq_actor.get_editor_property("playback_settings")
settings.set_editor_property("auto_play", True)
seq_actor.set_editor_property("playback_settings", settings)

eal.save_directory(SPIKE)
levels.save_current_level()
unreal.log(f"J1 : niveau {LEVEL} construit ({DURATION_S} s à {FPS} i/s)")
