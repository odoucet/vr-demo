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

# Barque (bloc 3,5 × 1,3 m) et caméra du spectateur, assis à l'arrière, yeux à 1,10 m de l'eau.
start = pose_at(0)
boat = place_mesh(CUBE, "Barque", "Bois", ue(start["x"], start["y"], 0.0), unreal.Rotator(0, 0, ue_yaw(start["heading_deg"])), (3.5, 1.3, 0.5))
cam = tag(actors.spawn_actor_from_class(unreal.CineCameraActor, ue(start["x"], start["y"], 0) + unreal.Vector(-80, 0, EYE_CM)), "CameraBarque")
cam.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
cine = cam.get_cine_camera_component()
cine.set_editor_property("current_focal_length", 12.0)    # ~ 90° horizontal sur capteur 16:9
focus = cine.get_editor_property("focus_settings")
focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
cine.set_editor_property("focus_settings", focus)

# Lune, droit devant au sommet de S6, haute de ~22° ; à 900 m (lointain, pas de stéréo).
lm = MARKS["creature-lune"]
p = pose_at(lm["t"])
h = math.radians(p["heading_deg"])
moon_xy = (p["x"] + 900 * math.cos(h), p["y"] + 900 * math.sin(h))
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
