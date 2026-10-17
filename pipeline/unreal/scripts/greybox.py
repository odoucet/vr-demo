"""J2 : niveau greybox construit depuis pipeline/layout/greybox.json et river.json (exécuté dans Unreal, run.py).

Idempotent : les maillages /Game/Greybox/SM_* sont mis à jour en place, les acteurs marqués « barque_gb »
sont supprimés puis recréés. Conversion : mètres → centimètres, repère du tracé (y à gauche) → Unreal
(Y à droite), donc y inversé et sens des triangles retourné.
Contenu : terrain, eau, arche des racines, forêt, arbre colossal, île et arbre aux lanternes, ponton, barque
avec caméra à 1,10 m, lune, blocs des créatures (animés par animatic.py), lumière de crépuscule et brume.
Tout est provisoire (placeholder) : formes et couleurs servent au timing, à l'échelle et au confort.
"""
import json
import math
import os

import unreal

ROOT = os.environ["BARQUE_ROOT"]
GB, MAP = "/Game/Greybox", "/Game/Maps/Barque_Greybox"
TAG = "barque_gb"
EYE_CM = 110.0

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

with open(os.path.join(ROOT, "pipeline", "layout", "greybox.json"), encoding="utf-8") as f:
    GEO = json.load(f)
with open(os.path.join(ROOT, "pipeline", "layout", "river.json"), encoding="utf-8") as f:
    RIVER = json.load(f)
MARKS = {m["id"]: m for m in RIVER["landmarks"]}


def ue(x, y, z=0.0):
    """Point du tracé (m) → Unreal (cm)."""
    return unreal.Vector(x * 100.0, -y * 100.0, z * 100.0)


def ue_yaw(heading_deg):
    return -heading_deg


def pose_at(t):
    s = RIVER["samples"]
    i = min(range(len(s)), key=lambda k: abs(s[k]["t"] - t))
    return s[i]


# --- Matériaux -----------------------------------------------------------------------------------------
def material(name, color, emissive=False, roughness=0.9, specular=None, opacity=None):
    path = f"{GB}/M_GB_{name}"
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(f"M_GB_{name}", GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    c.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    if emissive:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        mel.connect_material_property(c, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    else:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
        mel.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
        r = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 200)
        r.set_editor_property("r", roughness)
        mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
        if specular is not None:
            sp = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 300)
            sp.set_editor_property("r", specular)
            mel.connect_material_property(sp, "", unreal.MaterialProperty.MP_SPECULAR)
        if opacity is not None:  # eau translucide (S3 : la créature doit se voir sous la barque)
            mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
            op = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 400)
            op.set_editor_property("r", opacity)
            mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mat.set_editor_property("two_sided", True)
    mel.recompile_material(mat)
    return mat


MATS = {
    "Terrain": material("Terrain", (0.16, 0.22, 0.08)),
    "Eau": material("Eau", (0.01, 0.025, 0.035), roughness=0.7, specular=0.08, opacity=0.55),
    "Bois": material("Bois", (0.18, 0.11, 0.06)),
    "Foret": material("Foret", (0.04, 0.12, 0.05)),
    "Creature": material("Creature", (0.0, 0.6, 0.7), emissive=True),  # bioluminescente
    "Troupeau": material("Troupeau", (0.18, 0.30, 0.08)),
    "Volante": material("Volante", (0.75, 0.80, 0.85)),
    "Lune": material("Lune", (3.0, 2.9, 2.6), emissive=True),
    "Lanterne": material("Lanterne", (6.0, 2.5, 0.6), emissive=True),
    "LanternePapier": material("LanternePapier", (1.1, 0.55, 0.22), emissive=True),
}
MESH_MATS = {"Terrain": "Terrain", "ArcheRacines": "Bois", "Foret": "Foret", "ArbreColossal": "Bois", "ArbreLanternes": "Foret"}


# --- Maillages depuis greybox.json -------------------------------------------------------------------------
def build_mesh(name, data, uv_scale_cm=400.0):
    dm = unreal.DynamicMesh()
    buffers = unreal.GeometryScriptSimpleMeshBuffers()
    buffers.vertices = [ue(*v) for v in data["vertices"]]
    buffers.triangles = [unreal.IntVector(a, c, b) for a, b, c in data["triangles"]]  # miroir en y → sens inversé
    # UV fournis avec les sommets (projection plane, 1 répétition par uv_scale_cm) : un maillage statique
    # sans canal UV fait planter l'éditeur à la construction (assertion NumUVs > 0).
    k = 100.0 / uv_scale_cm
    buffers.uv0 = [unreal.Vector2D(v[0] * k, -v[1] * k) for v in data["vertices"]]
    dm.append_buffers_to_mesh(buffers)
    dm.recompute_normals(unreal.GeometryScriptCalculateNormalsOptions())
    path = f"{GB}/SM_{name}"
    if eal.does_asset_exist(path):
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, eal.load_asset(path), unreal.GeometryScriptCopyMeshToAssetOptions(),
                                                                  unreal.GeometryScriptMeshWriteLOD())
        return eal.load_asset(path)
    options = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    options.set_editor_property("enable_collision", False)
    mesh, _ = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, path, options)
    return mesh


b = GEO["bounds"]
GEO["meshes"]["Eau"] = {"vertices": [[b["x0"], b["y0"], 0], [b["x1"], b["y0"], 0], [b["x1"], b["y1"], 0], [b["x0"], b["y1"], 0]],
                        "triangles": [[0, 1, 2], [0, 2, 3]]}
MESH_MATS["Eau"] = "Eau"
MESHES = {name: build_mesh(name, data) for name, data in GEO["meshes"].items()}

# --- Niveau --------------------------------------------------------------------------------------------
if eal.does_asset_exist(MAP):
    levels.load_level(MAP)
else:
    levels.new_level(MAP)
for a in actors.get_all_level_actors():
    if TAG in [str(t) for t in a.tags]:
        actors.destroy_actor(a)


def tag(a, label):
    a.set_actor_label(label)
    a.tags = [TAG]
    return a


def place_mesh(mesh, label, mat, loc=unreal.Vector(0, 0, 0), rot=unreal.Rotator(0, 0, 0), scale=(1, 1, 1)):
    a = actors.spawn_actor_from_object(mesh, loc, rot)
    a.set_actor_scale3d(unreal.Vector(*scale))
    smc = a.static_mesh_component
    smc.set_material(0, MATS[mat])
    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return tag(a, label)


for name, mesh in MESHES.items():
    place_mesh(mesh, f"GB_{name}", MESH_MATS[name])

CUBE = eal.load_asset("/Engine/BasicShapes/Cube")      # 100 cm
SPHERE = eal.load_asset("/Engine/BasicShapes/Sphere")  # 100 cm de diamètre
CYL = eal.load_asset("/Engine/BasicShapes/Cylinder")


def oriented(t, ahead_m, side_m, z_m=0.0):
    """Position relative à la barque à l'instant t (side + = gauche), en Unreal."""
    p = pose_at(t)
    h = math.radians(p["heading_deg"])
    x = p["x"] + ahead_m * math.cos(h) - side_m * math.sin(h)
    y = p["y"] + ahead_m * math.sin(h) + side_m * math.cos(h)
    return ue(x, y, z_m), unreal.Rotator(0, 0, ue_yaw(p["heading_deg"]))


# Ponton : tablier de 6,5 m × 2 m depuis la berge droite (à 7 m de l'axe) vers la trajectoire, sur pilotis.
pm = MARKS["ponton"]
for i, side in enumerate((-8.5, -6.0, -3.5)):
    loc, rot = oriented(pm["t"], pm["ahead_m"], side, 0.0)
    place_mesh(CYL, f"GB_PontonPieu{i}", "Bois", unreal.Vector(loc.x, loc.y, -50), rot, (0.25, 0.25, 2.2))
loc, rot = oriented(pm["t"], pm["ahead_m"], -6.0, 0.75)
deck = place_mesh(CUBE, "GB_PontonTablier", "Bois", loc, unreal.Rotator(0, 0, rot.yaw + 90), (6.5, 2.0, 0.15))

# Barque : racine invisible (animée par la séquence, porte la caméra) + modèle 3D attaché.
# Modèle : assets/3d/barque/trellis2-s42 (image refs/barque.png, repère standard). Mesures à l'import :
# longueur 100 cm sur +Y (proue côté perche), fond à -35 cm, bordé à -9 cm. Mis à 3,5 m (D4), tourné de -90°
# pour que la proue regarde +X, posé avec 25 cm de tirant d'eau. Bloc en repli si le modèle manque.
BOAT_GLB = os.path.join(ROOT, "assets", "3d", "barque", "trellis2-s42", "model.glb")
BOAT_DIR, BOAT_MESH = "/Game/Assets/Barque", "/Game/Assets/Barque/model/StaticMeshes/model"
# Hauteur réduite (2,6 au lieu de 3,5) : franc-bord de ~45 cm au lieu de 68, pour voir l'eau par-dessus le bord.
BOAT_SCALE, BOAT_SCALE_Z, BOAT_YAW = 3.5, 2.6, -90.0
BOAT_Z = 35.1 * BOAT_SCALE_Z - 25.0


def boat_mesh():
    if not os.path.exists(BOAT_GLB):
        return None
    import hashlib
    with open(BOAT_GLB, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12]
    if eal.does_asset_exist(BOAT_MESH) and eal.get_metadata_tag(eal.load_asset(BOAT_MESH), "source_sha1") == digest:
        return eal.load_asset(BOAT_MESH)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = BOAT_GLB, BOAT_DIR
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
    mesh = eal.load_asset(BOAT_MESH)
    eal.set_metadata_tag(mesh, "source_sha1", digest)
    eal.save_loaded_asset(mesh)
    return mesh


start = pose_at(0)
boat = place_mesh(CUBE, "Barque", "Bois", ue(start["x"], start["y"], 0.0), unreal.Rotator(0, 0, ue_yaw(start["heading_deg"])))  # échelle 1 : le modèle attaché en hérite
model = boat_mesh()
if model is not None:
    boat.set_actor_hidden_in_game(True)
    boat.static_mesh_component.set_visibility(False)
    hull = actors.spawn_actor_from_object(model, boat.get_actor_location(), boat.get_actor_rotation())
    tag(hull, "BarqueModele")
    hull.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    hull.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    hull.root_component.set_editor_property("relative_location", unreal.Vector(0, 0, BOAT_Z))
    hull.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, BOAT_YAW))
    hull.root_component.set_editor_property("relative_scale3d", unreal.Vector(BOAT_SCALE, BOAT_SCALE, BOAT_SCALE_Z))
    # Lanterne de proue : corps mesuré dans le maillage (x ±4, y 22-30, z 8-24 cm à l'échelle d'import), soit
    # ~30 × 55 cm centré à (+91, 0, 154) cm dans le repère de la barque. Papier lumineux posé par-dessus
    # (le maillage n'a pas de matériau séparé pour la lanterne) et lumière au centre.
    LANTERN = unreal.Vector(26 * BOAT_SCALE, 0, BOAT_Z + 16 * BOAT_SCALE_Z)
    paper = place_mesh(CYL, "LanternePapier", "LanternePapier", boat.get_actor_location(), scale=(0.34, 0.34, 0.56))
    paper.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    paper.root_component.set_editor_property("relative_location", LANTERN)
    paper.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
    paper.root_component.set_editor_property("relative_scale3d", unreal.Vector(0.34, 0.34, 0.56 * BOAT_SCALE_Z / BOAT_SCALE))
    paper.static_mesh_component.set_editor_property("cast_shadow", False)
    lantern = tag(actors.spawn_actor_from_class(unreal.PointLight, boat.get_actor_location()), "LumiereLanterne")
    lantern.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    lantern.root_component.set_editor_property("relative_location", LANTERN)
    lc = lantern.point_light_component
    lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_editor_property("intensity", 25.0)
    lc.set_editor_property("light_color", unreal.Color(90, 170, 255, 255))  # BGRA : orangé chaud
    lc.set_editor_property("attenuation_radius", 900.0)
    lc.set_editor_property("source_radius", 12.0)
    lc.set_editor_property("cast_shadows", False)   # la lumière est dans le maillage de la lanterne
else:
    boat.set_actor_scale3d(unreal.Vector(3.5, 1.3, 0.5))
# Caméra du spectateur, sur le banc arrière (-1,20 m du centre), yeux à 1,10 m de l'eau. Reculée de 0,80 m
# à 1,20 m pour réduire la place de la lanterne de proue dans le champ (SUIVI.md, D11).
SEAT_X_CM = -120.0
h0 = math.radians(start["heading_deg"])
cam_loc = ue(start["x"] + SEAT_X_CM / 100 * math.cos(h0), start["y"] + SEAT_X_CM / 100 * math.sin(h0), EYE_CM / 100)
cam = tag(actors.spawn_actor_from_class(unreal.CineCameraActor, cam_loc), "CameraBarque")
cam.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
cine = cam.get_cine_camera_component()
cine.set_editor_property("current_focal_length", 12.0)    # ~ 90° horizontal sur capteur 16:9
focus = cine.get_editor_property("focus_settings")
focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
cine.set_editor_property("focus_settings", focus)

# Lune : dans la direction du repère « creature-lune » (sommet de S6), prolongée à 900 m, haute de ~22°.
lm = MARKS["creature-lune"]
p = pose_at(lm["t"])
dx, dy = lm["x"] - p["x"], lm["y"] - p["y"]
dist = math.hypot(dx, dy)
moon_xy = (p["x"] + dx / dist * 900, p["y"] + dy / dist * 900)
place_mesh(SPHERE, "GB_Lune", "Lune", ue(*moon_xy, 900 * math.tan(math.radians(22))), scale=(70, 70, 70))

# Lanternes de l'arbre de S7 : 40 petites sources sur le houppier.
lt = MARKS["ile-lanternes"]
for i in range(40):
    a = 2 * math.pi * i / 40 * 2.618
    r = 4 + 7 * ((i * 37) % 11) / 11
    place_mesh(SPHERE, f"GB_Lanterne{i:02d}", "Lanterne", ue(lt["x"] + r * math.cos(a), lt["y"] + r * math.sin(a), 8 + 9 * ((i * 17) % 13) / 13), scale=(0.5, 0.5, 0.6))

# Blocs des créatures (positions de départ ; animés par la séquence de l'animatic).
place_mesh(SPHERE, "GB_Abysses", "Creature", ue(0, -60, -3.2), scale=(15, 7, 1.2))          # 15 m (D4)
for i in range(5):
    place_mesh(SPHERE, f"GB_Troupeau{i}", "Troupeau", ue(0, -60 - i * 4, 0.6), scale=(3.0, 2.2, 2.5))  # 2,5 m (D4)
place_mesh(SPHERE, "GB_Volante", "Volante", ue(*moon_xy, 150), scale=(40, 12, 4))              # 40 m (D4)

# Lumière de crépuscule, ciel, brume.
sun = tag(actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000), unreal.Rotator(0, -8, ue_yaw(start["heading_deg"]) + 150)), "Soleil")
sun.light_component.set_editor_property("intensity", 14.0)
sun.light_component.set_editor_property("light_color", unreal.Color(255, 170, 120, 255))
sun.light_component.set_editor_property("atmosphere_sun_light", True)
tag(actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)), "Ciel")
sky = tag(actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 500)), "LumiereCiel")
sky.light_component.set_editor_property("real_time_capture", True)
sky.light_component.set_editor_property("intensity", 4.0)
fog = tag(actors.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0)), "Brume")
fc = fog.component
fc.set_editor_property("fog_density", 0.006)
fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.10, 0.13, 0.20, 1.0))
fc.set_editor_property("start_distance", 1500.0)
tag(actors.spawn_actor_from_class(unreal.PlayerStart, ue(start["x"], start["y"], 0.2)), "Depart")

# Pas de réglage d'exposition : l'exposition auto est coupée dans le projet (VR) et le moteur ignore alors
# toute compensation. La lisibilité du greybox se règle par l'intensité des lumières.

eal.save_directory(GB)
levels.save_current_level()
unreal.log(f"Greybox : {MAP} construit ({len(MESHES)} maillages)")
