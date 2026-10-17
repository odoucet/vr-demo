"""J1b : variante de repli de J1, vidéo 360 stéréo affichée par un calque stéréo équirectangulaire (StereoLayer)
composé directement par le casque, au lieu d'une sphère à matériau. Exécuté dans Unreal (run.py), après j1_spike.py
(réutilise ses assets média : /Game/Spike).

Calque : forme Equirect, moitié haute de l'image pour l'œil gauche, moitié basse pour l'œil droit, texture média en
direct. Le calque est dessiné par-dessus la scène : le cube témoin de J1 est probablement masqué ; la synchronisation
se juge entre le flash blanc et le bip de la vidéo. Même séquence de 60 s (piste média).
"""
import unreal

SPIKE, LEVEL, TAG = "/Game/Spike", "/Game/Maps/J1b_StereoLayer", "barque_j1b"
FPS, DURATION_S = 30, 60

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

source = eal.load_asset(f"{SPIKE}/FMS_Test360")
player = eal.load_asset(f"{SPIKE}/MP_Test360")
texture = eal.load_asset(f"{SPIKE}/MT_Test360")

if eal.does_asset_exist(LEVEL):
    levels.load_level(LEVEL)
else:
    levels.new_level(LEVEL)
for a in actors.get_all_level_actors():
    if TAG in [str(t) for t in a.tags]:
        actors.destroy_actor(a)


def tagged(a, label):
    a.set_actor_label(label)
    a.tags = [TAG]
    return a


# Porteur du calque : petit maillage invisible, auquel on ajoute un StereoLayerComponent et le son de la vidéo.
holder = tagged(actors.spawn_actor_from_object(eal.load_asset("/Engine/BasicShapes/Cube"), unreal.Vector(0, 0, 110)), "CalqueVideo360")
holder.static_mesh_component.set_visibility(False)
holder.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
root = sds.k2_gather_subobject_data_for_instance(holder)[0]
sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.StereoLayerComponent))
sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.MediaSoundComponent))
layer = holder.get_component_by_class(unreal.StereoLayerComponent)
shape = unreal.new_object(unreal.StereoLayerShapeEquirect, outer=layer)
left, right = unreal.Box2D(), unreal.Box2D()
left.set_editor_property("min", unreal.Vector2D(0.0, 0.0))
left.set_editor_property("max", unreal.Vector2D(1.0, 0.5))
right.set_editor_property("min", unreal.Vector2D(0.0, 0.5))
right.set_editor_property("max", unreal.Vector2D(1.0, 1.0))
shape.set_editor_property("left_uv_rect", left)
shape.set_editor_property("right_uv_rect", right)
shape.set_editor_property("radius", 0.0)        # 0 : à l'infini
layer.set_editor_property("shape", shape)
layer.set_editor_property("texture", texture)
layer.set_editor_property("live_texture", True)
layer.set_editor_property("stereo_layer_type", unreal.StereoLayerType.SLT_WORLD_LOCKED)
holder.get_component_by_class(unreal.MediaSoundComponent).set_media_player(player)

cube = tagged(actors.spawn_actor_from_object(eal.load_asset("/Engine/BasicShapes/Cube"), unreal.Vector(300, 0, 80)), "TemoinSynchro")
cube.set_actor_scale3d(unreal.Vector(0.2, 0.2, 0.2))
cube.static_mesh_component.set_material(0, eal.load_asset(f"{SPIKE}/M_FlashRouge"))
start = tagged(actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 0)), "Depart")

seq_path = f"{SPIKE}/LS_J1b"
if eal.does_asset_exist(seq_path):
    eal.delete_asset(seq_path)
seq = tools.create_asset("LS_J1b", SPIKE, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(FPS, 1))
seq.set_tick_resolution(unreal.FrameRate(FPS, 1))
seq.set_playback_start(0)
seq.set_playback_end(FPS * DURATION_S)
media = seq.add_track(unreal.MovieSceneMediaTrack).add_section()
media.set_range(0, FPS * DURATION_S)
media.set_editor_property("media_source", source)
media.set_editor_property("use_external_media_player", True)
media.set_editor_property("external_media_player", player)
media.set_editor_property("media_texture", texture)
vis = seq.add_possessable(cube).add_track(unreal.MovieSceneVisibilityTrack).add_section()
vis.set_range(0, FPS * DURATION_S)
ch = vis.get_all_channels()[0]
for s in range(DURATION_S):
    ch.add_key(unreal.FrameNumber(s * FPS), True)
    ch.add_key(unreal.FrameNumber(s * FPS + 1), False)
seq_actor = tagged(actors.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0, 0, 0)), "SequenceJ1b")
seq_actor.set_sequence(seq)
settings = seq_actor.get_editor_property("playback_settings")
settings.set_editor_property("auto_play", True)
seq_actor.set_editor_property("playback_settings", settings)

eal.save_directory(SPIKE)
levels.save_current_level()
unreal.log(f"J1b : niveau {LEVEL} construit (calque stéréo équirectangulaire)")
