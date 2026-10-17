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
    "Lune": material("Lune", (14.0, 13.5, 12.0), emissive=True),
    "Lanterne": material("Lanterne", (6.0, 2.5, 0.6), emissive=True),
    "LanternePapier": material("LanternePapier", (1.1, 0.55, 0.22), emissive=True),
    "Luciole": material("Luciole", (4.0, 5.0, 1.2), emissive=True),
}
MESH_MATS = {"Terrain": "Terrain", "ArcheRacines": "Bois", "Foret": "Foret", "ArbreColossal": "Bois", "ArbreLanternes": "Foret",
             "Lucioles": "Luciole"}


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
    a = place_mesh(mesh, f"GB_{name}", MESH_MATS[name])
    if name == "Lucioles":
        a.set_actor_location(unreal.Vector(0, 0, -3000), False, False)   # sous le terrain jusqu'à l'envol (séquence)

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


def import_glb(rel_glb, dest_dir, max_tris=None):
    """Importe assets/3d/<rel_glb>/model.glb dans dest_dir (une fois par empreinte du fichier et par budget de
    triangles) ; None si absent. max_tris : simplification à l'import (budget Quest : ≤ 500 k triangles visibles)."""
    import hashlib
    glb = os.path.join(ROOT, "assets", "3d", rel_glb, "model.glb")
    if not os.path.exists(glb):
        return None
    mesh_path = f"{dest_dir}/model/StaticMeshes/model"
    with open(glb, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12] + (f"-{max_tris}" if max_tris else "")
    if eal.does_asset_exist(mesh_path) and eal.get_metadata_tag(eal.load_asset(mesh_path), "source_sha1") == digest:
        return eal.load_asset(mesh_path)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = glb, dest_dir
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
    mesh = eal.load_asset(mesh_path)
    if max_tris and mesh.get_num_triangles(0) > max_tris:
        dm = unreal.DynamicMesh()
        unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        dm.apply_editor_simplify_to_triangle_count(max_tris)
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, mesh, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD())
        unreal.log(f"{rel_glb} : simplifié à {mesh.get_num_triangles(0)} triangles")
    eal.set_metadata_tag(mesh, "source_sha1", digest)
    eal.save_loaded_asset(mesh)
    return mesh


def boat_mesh():
    return import_glb("barque/trellis2-s42", BOAT_DIR, 30000)


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
# Joueur VR : pion attaché à la barque sur la place assise, au niveau de l'eau. En suivi « au sol » (Quest),
# le casque ajoute la hauteur réelle de la tête assise (~1,10 m). Caméra verrouillée sur le casque, ni collision
# ni déplacement ; la séquence ignore ses coupes caméra en jeu (animatic.py).
vr = tag(actors.spawn_actor_from_class(unreal.DefaultPawn, ue(start["x"] + SEAT_X_CM / 100 * math.cos(h0), start["y"] + SEAT_X_CM / 100 * math.sin(h0), 0.0),
                                       unreal.Rotator(0, 0, ue_yaw(start["heading_deg"]))), "JoueurVR")
vr.set_editor_property("auto_possess_player", unreal.AutoReceiveInput.PLAYER0)
vr.set_editor_property("base_eye_height", 0.0)
vr.collision_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
vr.mesh_component.set_visibility(False)
vr.mesh_component.set_hidden_in_game(True)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
root_handle = sds.k2_gather_subobject_data_for_instance(vr)[0]
sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root_handle, new_class=unreal.CameraComponent))
vr_cam = vr.get_component_by_class(unreal.CameraComponent)
vr_cam.set_editor_property("lock_to_hmd", True)
# Sans casque (rendu MRQ, jeu à l'écran), la caméra reste à sa position relative : yeux à 1,10 m. Avec le casque,
# la pose de la tête (origine STAGE, au sol) remplace cette position relative.
vr_cam.set_editor_property("relative_location", unreal.Vector(0, 0, EYE_CM))
vr.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
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

# Ciel peint provisoire (assets/sky/ciel.png, pipeline/comfy/sky.py) : panorama « paysage » dont l'horizon est à
# ~82 % de la hauteur ; projeté sur la voûte (horizon → zénith) par la direction de vue, sur une sphère de 5 km
# en matériau « ciel » (dessiné derrière tout, hors brume).
SKY_PNG = os.path.join(ROOT, "assets", "sky", "ciel.png")
if os.path.exists(SKY_PNG):
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = SKY_PNG, GB
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
    sky_tex = eal.load_asset(f"{GB}/ciel")
    sky_mat_path = f"{GB}/M_GB_CielPeint"
    sky_mat = eal.load_asset(sky_mat_path) if eal.does_asset_exist(sky_mat_path) else tools.create_asset("M_GB_CielPeint", GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(sky_mat)
    sky_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    sky_mat.set_editor_property("is_sky", True)
    sky_mat.set_editor_property("two_sided", True)
    camv = mel.create_material_expression(sky_mat, unreal.MaterialExpressionCameraVectorWS, -700, 0)
    cu = mel.create_material_expression(sky_mat, unreal.MaterialExpressionCustom, -450, 0)
    cu.set_editor_property("code", "float3 d = normalize(-Dir);\n"
                                   "float u = 0.5 + atan2(d.y, d.x) / (2.0 * PI);\n"
                                   "float e = asin(clamp(d.z, -1.0, 1.0));\n"
                                   "float v = clamp(0.82 - e / (0.5 * PI) * 0.82, 0.0, 1.0);\n"
                                   "return float2(u, v);")
    cu.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", "Dir")
    cu.set_editor_property("inputs", [ci])
    st = mel.create_material_expression(sky_mat, unreal.MaterialExpressionTextureSample, -200, 0)
    st.set_editor_property("texture", sky_tex)
    mel.connect_material_expressions(camv, "", cu, "Dir")
    mel.connect_material_expressions(cu, "", st, "UVs")
    # Luminosité du ciel pilotée par la séquence (crépuscule → nuit) via une collection de paramètres.
    mpc_path = f"{GB}/MPC_Ambiance"
    mpc = eal.load_asset(mpc_path) if eal.does_asset_exist(mpc_path) else tools.create_asset("MPC_Ambiance", GB, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    sp = unreal.CollectionScalarParameter()
    sp.set_editor_property("parameter_name", "CielLuminosite")
    sp.set_editor_property("default_value", 1.0)
    mpc.set_editor_property("scalar_parameters", [sp])
    eal.save_loaded_asset(mpc)
    cp = mel.create_material_expression(sky_mat, unreal.MaterialExpressionCollectionParameter, -200, 250)
    cp.set_editor_property("collection", mpc)
    cp.set_editor_property("parameter_name", "CielLuminosite")
    mul = mel.create_material_expression(sky_mat, unreal.MaterialExpressionMultiply, 0, 100)
    mel.connect_material_expressions(st, "RGB", mul, "A")
    mel.connect_material_expressions(cp, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(sky_mat)
    MATS["CielPeint"] = sky_mat
    sky_sphere = place_mesh(SPHERE, "GB_CielPeint", "CielPeint", unreal.Vector(10000, 0, 0), scale=(10000, 10000, 10000))
    sky_sphere.static_mesh_component.set_editor_property("cast_shadow", False)

# Lanternes de l'arbre de S7 : 40 petites sources sur le houppier.
lt = MARKS["ile-lanternes"]
for i in range(40):
    a = 2 * math.pi * i / 40 * 2.618
    r = 4 + 7 * ((i * 37) % 11) / 11
    place_mesh(SPHERE, f"GB_Lanterne{i:02d}", "Lanterne", ue(lt["x"] + r * math.cos(a), lt["y"] + r * math.sin(a), 8 + 9 * ((i * 17) % 13) / 13), scale=(0.5, 0.5, 0.6))

# Créatures : bloc animé par la séquence (repère : +X = sens du mouvement) + modèle 3D attaché s'il existe.
# Modèles TRELLIS.2 : longueur sur +Y à l'import (1 unité = 100 cm), comme la barque → rotation -90°.
# Échelles D4 : abysses 15 m de long (épaisseur ramenée à 2,5 m), troupeau 2,5 m au garrot, volante 40 m d'envergure.
CREATURES = {
    # bloc : (modèle, matériau du bloc, échelle du bloc de repli, échelle du modèle (x, y, z), décalage z cm, triangles max)
    "GB_Abysses": ("abysses/trellis2-s42", "Creature", (15, 7, 1.2), (15, 15, 4.5), 0.0, 20000),
    "GB_Troupeau": ("troupeau/trellis2-s42", "Troupeau", (3.0, 2.2, 2.5), (4.1, 4.1, 4.1), -60.0, 12000),   # à mi-corps, ×5
    "GB_Volante": ("fly/trellis2-s42", "Volante", (40, 12, 4), (56, 56, 56), 0.0, 20000),
}


GLOW = {"GB_Abysses": (0.15, 1.6, 2.0)}   # bioluminescence : texture de couleur réutilisée en émissif, teintée


def glow(dest_dir, tint):
    """Rend le modèle lumineux : sa texture de couleur sert aussi d'émissif, multipliée par une teinte."""
    mel = unreal.MaterialEditingLibrary
    for path in eal.list_assets(f"{dest_dir}/model/Materials", recursive=True):
        mi = eal.load_asset(path)
        if not isinstance(mi, unreal.MaterialInstanceConstant):
            continue
        base = mel.get_material_instance_texture_parameter_value(mi, "BaseColorTexture")
        mel.set_material_instance_texture_parameter_value(mi, "EmissiveTexture", base)
        mel.set_material_instance_static_switch_parameter_value(mi, "bHasEmissiveTexture", True)
        mel.set_material_instance_vector_parameter_value(mi, "EmissiveFactor", unreal.LinearColor(*tint, 1.0))
        mel.update_material_instance(mi)
        eal.save_loaded_asset(mi)


def creature(label, kind, loc):
    rel_glb, mat, fallback, mscale, dz, max_tris = CREATURES[kind]
    model = import_glb(rel_glb, f"/Game/Assets/{kind[3:]}", max_tris)
    if model is not None and kind in GLOW:
        glow(f"/Game/Assets/{kind[3:]}", GLOW[kind])
    blk = place_mesh(SPHERE, label, mat, loc, scale=(1, 1, 1) if model else fallback)
    if model is None:
        return blk
    blk.set_actor_hidden_in_game(True)
    blk.static_mesh_component.set_visibility(False)
    m = actors.spawn_actor_from_object(model, loc)
    tag(m, label + "_Modele")
    m.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    m.attach_to_actor(blk, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    m.root_component.set_editor_property("relative_location", unreal.Vector(0, 0, dz))
    m.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, -90.0))
    m.root_component.set_editor_property("relative_scale3d", unreal.Vector(*mscale))
    return blk


creature("GB_Abysses", "GB_Abysses", ue(0, -60, -3.2))
for i in range(5):
    creature(f"GB_Troupeau{i}", "GB_Troupeau", ue(0, -60 - i * 4, 0.6))
creature("GB_Volante", "GB_Volante", ue(*moon_xy, 150))

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
