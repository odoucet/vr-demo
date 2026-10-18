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
def spec_digest(*spec):
    import hashlib
    return hashlib.sha1(repr(spec).encode()).hexdigest()[:12]


def up_to_date(asset, digest):
    return asset is not None and eal.get_metadata_tag(asset, "source_sha1") == digest


def mark_saved(asset, digest):
    """Enregistre l'empreinte de la définition et sauvegarde l'asset (reconstruit seulement s'il a changé)."""
    eal.set_metadata_tag(asset, "source_sha1", digest)
    eal.save_loaded_asset(asset)


def material(name, color, emissive=False, roughness=0.9, specular=None, opacity=None):
    path = f"{GB}/M_GB_{name}"
    digest = spec_digest(name, color, emissive, roughness, specular, opacity)
    existing = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(existing, digest):
        return existing
    mat = existing or tools.create_asset(f"M_GB_{name}", GB, unreal.Material, unreal.MaterialFactoryNew())
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
    mark_saved(mat, digest)
    return mat


# --- Look peint ---------------------------------------------------------------------------------------
# Pas de filtre de rendu : sur Quest (sans HDR mobile) aucun post-traitement n'est possible. Le dessin animé
# est dans le matériau M_Peint, non éclairé : ombrage en deux tons (lumière / ombre) à frontière douce,
# bord irrégulier par une texture de touches de pinceau, couleur et occlusion portées par les sommets,
# appoint du ciel et liseré de contre-jour. Lumières pilotées par MPC_Ambiance (animée beat par beat).
MPC_PATH = f"{GB}/MPC_Ambiance"
MPC_VECTORS = {"SoleilDir": (0.9, -0.4, 0.2), "Lumiere": (1.0, 0.95, 0.85), "Ombre": (0.3, 0.35, 0.55),
               "CielAppoint": (0.1, 0.12, 0.2), "CielTeinte": (1.0, 1.0, 1.0)}
MPC_DIGEST = spec_digest("mpc-v3", sorted(MPC_VECTORS))


def ambiance_mpc():
    """Collection de paramètres partagée (ciel, look peint) ; recréée seulement si sa liste change (les
    matériaux s'y réfèrent par identifiant)."""
    mpc = eal.load_asset(MPC_PATH) if eal.does_asset_exist(MPC_PATH) else tools.create_asset(
        "MPC_Ambiance", GB, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    if up_to_date(mpc, MPC_DIGEST):
        return mpc
    sp = unreal.CollectionScalarParameter()
    sp.set_editor_property("parameter_name", "CielLuminosite")
    sp.set_editor_property("default_value", 1.0)
    vps = []
    for name, v in MPC_VECTORS.items():
        vp = unreal.CollectionVectorParameter()
        vp.set_editor_property("parameter_name", name)
        vp.set_editor_property("default_value", unreal.LinearColor(*v, 1.0))
        vps.append(vp)
    mpc.set_editor_property("scalar_parameters", [sp])
    mpc.set_editor_property("vector_parameters", vps)
    mark_saved(mpc, MPC_DIGEST)
    return mpc


MPC = ambiance_mpc()


def mpc_rgb(mat, name, x, y):
    """Paramètre vectoriel de MPC_Ambiance réduit à RGB (multipliable par une couleur de texture)."""
    cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, x - 200, y)
    cp.set_editor_property("collection", MPC)
    cp.set_editor_property("parameter_name", name)
    mask = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, x, y)
    for c in ("r", "g", "b"):
        mask.set_editor_property(c, True)
    mel.connect_material_expressions(cp, "", mask, "")
    return mask

def custom_node(mat, code, out_type, names, x, y):
    node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, x, y)
    node.set_editor_property("code", code)
    node.set_editor_property("output_type", out_type)
    inputs = []
    for n in names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        inputs.append(ci)
    node.set_editor_property("inputs", inputs)
    return node


SKY_DRIFT = 0.0004     # tours de panorama par seconde (vent dans les nuages)
SKY_UV_CODE = f"""float3 d = normalize(-Dir);
float u = 0.5 + atan2(d.y, d.x) / (2.0 * PI) + T * {SKY_DRIFT};
float e = asin(clamp(d.z, -1.0, 1.0));
float v = clamp(0.82 - e / (0.5 * PI) * 0.82, 0.0, 1.0);
return float2(u, v);"""
SKY_STARS_CODE = """float3 d = normalize(-Dir);
float3 sky = Tex * Teinte.rgb;
float night = saturate(1.0 - dot(Teinte.rgb, float3(0.3, 0.5, 0.2)) * 3.0);
float2 g = float2(atan2(d.y, d.x) * 260.0, d.z * 260.0);
float2 c = floor(g);
float h = frac(sin(dot(c, float2(12.9898, 78.233))) * 43758.5453);
float2 f = frac(g) - 0.5;
float star = step(0.985, h) * saturate(1.0 - length(f) * 3.0);
float tw = 0.55 + 0.45 * sin(T * (1.5 + h * 3.0) + h * 80.0);
float clouds = saturate(1.0 - dot(Tex, float3(0.3, 0.5, 0.2)) * 1.6);
return sky + star * tw * night * clouds * saturate(d.z * 6.0) * 1.5;"""


BRUSH_PNG = os.path.join(ROOT, "assets", "textures", "pinceau.png")


def brush_texture():
    import hashlib
    with open(BRUSH_PNG, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12]
    path = "/Game/Look/pinceau"
    tex = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(tex, digest):
        return tex
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = BRUSH_PNG, "/Game/Look"
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
    tex = eal.load_asset(path)
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
    mark_saved(tex, digest)
    return tex


PEINT_CODE = """float3 n = normalize(N.xyz);
float3 l = normalize(L.xyz);
float3 v = normalize(V.xyz);
float3 albedo = pow(max(Albedo.rgb, 0.0), 2.2);   // couleurs des sommets stockées en sRGB
float brush = Brush.r;
float ndl = dot(n, l);
// frontière lumière / ombre douce, décalée par les touches de pinceau (bord peint, jamais net)
float t = smoothstep(-0.10, 0.12, ndl + (brush - 0.5) * 0.45);
float3 col = albedo * lerp(Ombre.rgb, Lumiere.rgb, t);
// occlusion peinte (alpha des sommets) : creux et dessous plus sombres, sans aller au noir
col *= lerp(0.35, 1.0, AO);
// appoint du ciel sur les faces tournées vers le haut
col += albedo * Ciel.rgb * saturate(n.z * 0.5 + 0.5);
// liseré de contre-jour : bords des silhouettes éclairés quand la lumière est en face
float rim = pow(1.0 - saturate(dot(n, v)), 3.0) * saturate(dot(-v, l));
col += albedo * Lumiere.rgb * rim * 0.8;
// variation de la touche
col *= 1.0 + (brush - 0.5) * 0.18;
return col;"""


def peint_material():
    """M_Peint : couleur des sommets, ombrage deux tons ; voir PEINT_CODE."""
    path = "/Game/Look/M_Peint"
    brush = brush_texture()
    digest = spec_digest("peint-v6", PEINT_CODE, MPC_DIGEST, eal.get_metadata_tag(brush, "source_sha1"))
    existing = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(existing, digest):
        return existing
    mat = existing or tools.create_asset("M_Peint", "/Game/Look", unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -1100, -200)
    nrm = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -1100, 0)
    cam = mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -1100, 100)
    wp = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1400, 300)
    # projection monde de la texture de touches (5 m), légèrement inclinée pour couvrir aussi les verticales
    uvc = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -1150, 300)
    uvc.set_editor_property("code", "return float2(P.x + P.z * 0.6, P.y - P.z * 0.45) / 500.0;")
    uvc.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", "P")
    uvc.set_editor_property("inputs", [ci])
    mel.connect_material_expressions(wp, "", uvc, "P")
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -900, 300)
    tex.set_editor_property("texture", brush)
    tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)   # texture non sRGB
    mel.connect_material_expressions(uvc, "", tex, "UVs")
    params = {}
    for i, name in enumerate(("SoleilDir", "Lumiere", "Ombre", "CielAppoint")):
        cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1100, 450 + 100 * i)
        cp.set_editor_property("collection", MPC)
        cp.set_editor_property("parameter_name", name)
        params[name] = cp
    node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -500, 0)
    node.set_editor_property("code", PEINT_CODE)
    node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    names = ["Albedo", "AO", "N", "L", "V", "Brush", "Lumiere", "Ombre", "Ciel"]
    inputs = []
    for n in names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        inputs.append(ci)
    node.set_editor_property("inputs", inputs)
    mel.connect_material_expressions(vc, "", node, "Albedo")      # sortie couleur (float3 ; pas de broche « RGB »)
    mel.connect_material_expressions(vc, "A", node, "AO")         # alpha des sommets = occlusion peinte
    mel.connect_material_expressions(nrm, "", node, "N")
    mel.connect_material_expressions(params["SoleilDir"], "", node, "L")
    mel.connect_material_expressions(cam, "", node, "V")
    mel.connect_material_expressions(tex, "R", node, "Brush")
    mel.connect_material_expressions(params["Lumiere"], "", node, "Lumiere")
    mel.connect_material_expressions(params["Ombre"], "", node, "Ombre")
    mel.connect_material_expressions(params["CielAppoint"], "", node, "Ciel")
    mel.connect_material_property(node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError("M_Peint ne compile pas (voir l'éditeur de matériau)")
    mark_saved(mat, digest)
    return mat


MATS = {
    "Peint": peint_material(),
    "Terrain": material("Terrain", (0.16, 0.22, 0.08)),
    "Eau": material("Eau", (0.01, 0.025, 0.035), roughness=0.7, specular=0.08, opacity=0.55),
    "Bois": material("Bois", (0.18, 0.11, 0.06)),
    "Creature": material("Creature", (0.0, 0.6, 0.7), emissive=True),  # bioluminescente
    "Troupeau": material("Troupeau", (0.18, 0.30, 0.08)),
    "Volante": material("Volante", (0.75, 0.80, 0.85)),
    "Lune": material("Lune", (14.0, 13.5, 12.0), emissive=True),
    "Lanterne": material("Lanterne", (6.0, 2.5, 0.6), emissive=True),
    "LanternePapier": material("LanternePapier", (1.1, 0.55, 0.22), emissive=True),
    "Luciole": None,      # matériau animé, voir firefly_material()
    "Roseau": material("Roseau", (0.045, 0.075, 0.025), roughness=0.95, specular=0.1),
    "Nenuphar": material("Nenuphar", (0.06, 0.20, 0.07), roughness=0.85, specular=0.1),
}


FIREFLY_CODE_WPO = """float ph = UV.x * 6.2832;
return Amp * float3(sin(T * 0.61 + ph), cos(T * 0.47 + ph * 1.7), 0.6 * sin(T * 0.83 + UV.y * 6.2832));"""
FIREFLY_CODE_BLINK = """float b = 0.5 + 0.5 * sin(T * (1.1 + UV.y) + UV.x * 40.0);
return 0.25 + 0.75 * b * b;"""


def firefly_material(color=(4.0, 5.0, 1.2), amp_cm=30.0):
    """Lucioles : émissif non éclairé qui clignote, sommets déplacés en WPO (dérive lente, phase par luciole
    lue dans l'UV). Animation entièrement dans le shader : rien à évaluer sur le CPU du Quest."""
    path = f"{GB}/M_GB_Luciole"
    digest = spec_digest("luciole-v2", color, amp_cm, FIREFLY_CODE_WPO, FIREFLY_CODE_BLINK)
    existing = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(existing, digest):
        return existing
    mat = existing or tools.create_asset("M_GB_Luciole", GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    t = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -900, 0)
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -900, 150)
    amp = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -900, 300)
    amp.set_editor_property("r", amp_cm)

    def custom(code, out_type, names, x, y):
        node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, x, y)
        node.set_editor_property("code", code)
        node.set_editor_property("output_type", out_type)
        inputs = []
        for n in names:
            ci = unreal.CustomInput()
            ci.set_editor_property("input_name", n)
            inputs.append(ci)
        node.set_editor_property("inputs", inputs)
        return node

    wpo = custom(FIREFLY_CODE_WPO, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["T", "UV", "Amp"], -600, 200)
    blink = custom(FIREFLY_CODE_BLINK, unreal.CustomMaterialOutputType.CMOT_FLOAT1, ["T", "UV"], -600, 0)
    for node in (wpo, blink):
        mel.connect_material_expressions(t, "", node, "T")
        mel.connect_material_expressions(uv, "", node, "UV")
    mel.connect_material_expressions(amp, "", wpo, "Amp")
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -600, -150)
    col.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, -50)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(blink, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(mat)
    mark_saved(mat, digest)
    return mat


MATS["Luciole"] = firefly_material()
MESH_MATS = {"Terrain": "Peint", "ArcheRacines": "Peint", "Lucioles": "Luciole", "LuciolesBerges": "Luciole",
             "Roseaux": "Peint", "Nenuphars": "Peint"}


# --- Maillages depuis greybox.json -------------------------------------------------------------------------
def build_mesh(name, data, uv_scale_cm=400.0):
    """Maillage statique depuis les données du tracé ; réécrit seulement si la géométrie a changé (empreinte)."""
    import hashlib
    digest = hashlib.sha1(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
    path = f"{GB}/SM_{name}"
    if eal.does_asset_exist(path) and eal.get_metadata_tag(eal.load_asset(path), "source_sha1") == digest:
        return eal.load_asset(path)
    dm = unreal.DynamicMesh()
    buffers = unreal.GeometryScriptSimpleMeshBuffers()
    buffers.vertices = [ue(*v) for v in data["vertices"]]
    buffers.triangles = [unreal.IntVector(a, c, b) for a, b, c in data["triangles"]]  # miroir en y → sens inversé
    # UV fournis avec les sommets (projection plane, 1 répétition par uv_scale_cm) : un maillage statique
    # sans canal UV fait planter l'éditeur à la construction (assertion NumUVs > 0).
    k = 100.0 / uv_scale_cm
    buffers.uv0 = ([unreal.Vector2D(*uv) for uv in data["uv"]] if "uv" in data else
                   [unreal.Vector2D(v[0] * k, -v[1] * k) for v in data["vertices"]])
    # Look peint : couleur par sommet (sRGB → linéaire), alpha = occlusion ; normales choisies si fournies
    # (feuillages sphériques), sinon recalculées.
    srgb = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92     # noqa: E731
    colors = data.get("colors") or ([data["color"]] * len(data["vertices"]) if "color" in data else None)
    if colors:
        buffers.vertex_colors = [unreal.LinearColor(srgb(c[0]), srgb(c[1]), srgb(c[2]), c[3]) for c in colors]
    if "normals" in data:
        buffers.normals = [unreal.Vector(n[0], -n[1], n[2]) for n in data["normals"]]
    dm.append_buffers_to_mesh(buffers)
    if "normals" not in data:
        dm.recompute_normals(unreal.GeometryScriptCalculateNormalsOptions())
    if eal.does_asset_exist(path):
        mesh = eal.load_asset(path)
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, mesh, unreal.GeometryScriptCopyMeshToAssetOptions(),
                                                                  unreal.GeometryScriptMeshWriteLOD())
    else:
        options = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
        options.set_editor_property("enable_collision", False)
        mesh, _ = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, path, options)
    eal.set_metadata_tag(mesh, "source_sha1", digest)
    eal.save_loaded_asset(mesh)
    return mesh


b = GEO["bounds"]
GEO["meshes"]["Eau"] = {"vertices": [[b["x0"], b["y0"], 0], [b["x1"], b["y0"], 0], [b["x1"], b["y1"], 0], [b["x0"], b["y1"], 0]],
                        "triangles": [[0, 1, 2], [0, 2, 3]]}
MESH_MATS["Eau"] = "Eau"
with open(os.path.join(ROOT, "pipeline", "layout", "vegetation.json"), encoding="utf-8") as f:
    VEG = json.load(f)
for name, data in VEG["meshes"].items():
    GEO["meshes"][name] = data
    MESH_MATS[name] = "Peint"
MESHES = {name: build_mesh(name, data) for name, data in GEO["meshes"].items()}
for old in ("SM_Foret", "SM_ArbreColossal", "SM_ArbreLanternes", "M_GB_Foret"):   # remplacés par le look peint
    if eal.does_asset_exist(f"{GB}/{old}"):
        eal.delete_asset(f"{GB}/{old}")

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
    import hashlib
    with open(SKY_PNG, "rb") as f:
        sky_digest = hashlib.sha1(f.read()).hexdigest()[:12]
    sky_tex = eal.load_asset(f"{GB}/ciel") if eal.does_asset_exist(f"{GB}/ciel") else None
    if sky_tex is None or eal.get_metadata_tag(sky_tex, "source_sha1") != sky_digest:
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = SKY_PNG, GB
        task.automated, task.replace_existing, task.save = True, True, True
        tools.import_asset_tasks([task])
        sky_tex = eal.load_asset(f"{GB}/ciel")
        eal.set_metadata_tag(sky_tex, "source_sha1", sky_digest)
        eal.save_loaded_asset(sky_tex)
    SKY_WATER_VERSION = "ciel-eau-v3"   # à incrémenter si le code des matériaux du ciel ou de l'eau change
    sky_mat_path = f"{GB}/M_GB_CielPeint"
    sky_mat = eal.load_asset(sky_mat_path) if eal.does_asset_exist(sky_mat_path) else None
    rebuild_sky_water = not up_to_date(sky_mat, spec_digest(SKY_WATER_VERSION, sky_digest, MPC_DIGEST))
    sky_mat = sky_mat or tools.create_asset("M_GB_CielPeint", GB, unreal.Material, unreal.MaterialFactoryNew())
if os.path.exists(SKY_PNG) and rebuild_sky_water:
    mel.delete_all_material_expressions(sky_mat)
    sky_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    sky_mat.set_editor_property("is_sky", True)
    sky_mat.set_editor_property("two_sided", True)
    camv = mel.create_material_expression(sky_mat, unreal.MaterialExpressionCameraVectorWS, -700, 0)
    # Ciel vivant : le panorama dérive lentement (nuages poussés par le vent, ~0,15°/s), étoiles procédurales
    # qui scintillent la nuit (révélées quand la teinte du ciel s'assombrit, masquées par les nuages clairs).
    tnode = mel.create_material_expression(sky_mat, unreal.MaterialExpressionTime, -700, 150)
    cu = custom_node(sky_mat, SKY_UV_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT2, ["Dir", "T"], -450, 0)
    mel.connect_material_expressions(camv, "", cu, "Dir")
    mel.connect_material_expressions(tnode, "", cu, "T")
    st = mel.create_material_expression(sky_mat, unreal.MaterialExpressionTextureSample, -200, 0)
    st.set_editor_property("texture", sky_tex)
    mel.connect_material_expressions(cu, "", st, "UVs")
    mpc = MPC
    cp = mpc_rgb(sky_mat, "CielTeinte", -200, 250)
    mul = custom_node(sky_mat, SKY_STARS_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Dir", "T", "Tex", "Teinte"], 0, 100)
    mel.connect_material_expressions(camv, "", mul, "Dir")
    mel.connect_material_expressions(tnode, "", mul, "T")
    mel.connect_material_expressions(st, "RGB", mul, "Tex")
    mel.connect_material_expressions(cp, "", mul, "Teinte")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(sky_mat)
    mark_saved(sky_mat, spec_digest(SKY_WATER_VERSION, sky_digest, MPC_DIGEST))
    # Eau : reflet du ciel peint (texture lue dans la direction réfléchie, sans réflexions temps réel, peu coûteux
    # sur Quest) + Fresnel : miroir vers l'horizon, transparente en regardant vers le bas (S3 : la créature dessous).
    water = eal.load_asset(f"{GB}/M_GB_Eau")
    mel.delete_all_material_expressions(water)
    water.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    water.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    water.set_editor_property("two_sided", True)
    wcam = mel.create_material_expression(water, unreal.MaterialExpressionCameraVectorWS, -900, 0)
    wuv = mel.create_material_expression(water, unreal.MaterialExpressionCustom, -650, -100)
    wuv.set_editor_property("code", "float3 d = normalize(-Dir); d.z = abs(d.z);\n"
                                    "float u = 0.5 + atan2(d.y, d.x) / (2.0 * PI) + T * " + str(SKY_DRIFT) + ";\n"
                                    "float e = asin(clamp(d.z, 0.0, 1.0));\n"
                                    "return float2(u, clamp(0.82 - e / (0.5 * PI) * 0.82, 0.0, 1.0));")
    wuv.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    wfr = mel.create_material_expression(water, unreal.MaterialExpressionCustom, -650, 200)
    wfr.set_editor_property("code", "float3 d = normalize(-Dir); return 0.08 + 0.92 * pow(1.0 - abs(d.z), 4.0);")
    wfr.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    wt = mel.create_material_expression(water, unreal.MaterialExpressionTime, -900, 150)
    for node in (wuv, wfr):
        inps = []
        for n in (("Dir", "T") if node is wuv else ("Dir",)):
            inp = unreal.CustomInput()
            inp.set_editor_property("input_name", n)
            inps.append(inp)
        node.set_editor_property("inputs", inps)
        mel.connect_material_expressions(wcam, "", node, "Dir")
    mel.connect_material_expressions(wt, "", wuv, "T")
    wsky = mel.create_material_expression(water, unreal.MaterialExpressionTextureSample, -400, -100)
    wsky.set_editor_property("texture", sky_tex)
    mel.connect_material_expressions(wuv, "", wsky, "UVs")
    wmpc = mpc_rgb(water, "CielTeinte", -400, 100)
    refl = mel.create_material_expression(water, unreal.MaterialExpressionMultiply, -200, -50)
    mel.connect_material_expressions(wsky, "RGB", refl, "A")
    mel.connect_material_expressions(wmpc, "", refl, "B")
    deep = mel.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -200, 150)
    deep.set_editor_property("constant", unreal.LinearColor(0.01, 0.03, 0.05, 1.0))
    mix = mel.create_material_expression(water, unreal.MaterialExpressionLinearInterpolate, 0, 0)
    mel.connect_material_expressions(deep, "", mix, "A")
    mel.connect_material_expressions(refl, "", mix, "B")
    mel.connect_material_expressions(wfr, "", mix, "Alpha")
    mel.connect_material_property(mix, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    wop = mel.create_material_expression(water, unreal.MaterialExpressionLinearInterpolate, 0, 250)
    c0 = mel.create_material_expression(water, unreal.MaterialExpressionConstant, -200, 300)
    c0.set_editor_property("r", 0.35)
    c1 = mel.create_material_expression(water, unreal.MaterialExpressionConstant, -200, 380)
    c1.set_editor_property("r", 0.95)
    mel.connect_material_expressions(c0, "", wop, "A")
    mel.connect_material_expressions(c1, "", wop, "B")
    mel.connect_material_expressions(wfr, "", wop, "Alpha")
    mel.connect_material_property(wop, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(water)
    if mel.get_statistics(water).num_pixel_shader_instructions <= 0 or mel.get_statistics(sky_mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError("Matériau du ciel ou de l'eau : échec de compilation")
    eal.save_loaded_asset(water)
if os.path.exists(SKY_PNG):
    MATS["CielPeint"] = sky_mat
    sky_sphere = place_mesh(SPHERE, "GB_CielPeint", "CielPeint", unreal.Vector(10000, 0, 0), scale=(10000, 10000, 10000))
    sky_sphere.static_mesh_component.set_editor_property("cast_shadow", False)

# Lanternes de l'arbre de S7 : suspendues sous le houppier (positions dans vegetation.json).
for i, (x, y, z) in enumerate(VEG["lanternes"]):
    place_mesh(SPHERE, f"GB_Lanterne{i:02d}", "Lanterne", ue(x, y, z), scale=(0.45, 0.45, 0.6))

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
        if mel.get_material_instance_texture_parameter_value(mi, "EmissiveTexture") == base and \
                mel.get_material_instance_vector_parameter_value(mi, "EmissiveFactor") == unreal.LinearColor(*tint, 1.0):
            continue   # déjà lumineux : ne pas réécrire l'asset
        mel.set_material_instance_texture_parameter_value(mi, "EmissiveTexture", base)
        mel.set_material_instance_static_switch_parameter_value(mi, "bHasEmissiveTexture", True)
        mel.set_material_instance_vector_parameter_value(mi, "EmissiveFactor", unreal.LinearColor(*tint, 1.0))
        mel.update_material_instance(mi)
        eal.save_loaded_asset(mi)


FLAP_CODE = """float n = saturate(abs(dot(LP.xyz, Axis.xyz)) / Half);
return float3(0, 0, Half * 0.22 * n * n * sin(T * 1.8));"""


def peint_tex_material(name, texture, flap_axis=None, half_span=1.0):
    """Look peint pour un modèle texturé (créatures, barque) : couleur de la texture, même ombrage deux tons
    que M_Peint. flap_axis : battement d'ailes procédural (WPO, axe d'envergure local, sans squelette)."""
    path = f"/Game/Look/{name}"
    digest = spec_digest("peint-tex-v1", PEINT_CODE, MPC_DIGEST, texture.get_path_name(), flap_axis, round(half_span, 2), FLAP_CODE)
    existing = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(existing, digest):
        return existing
    mat = existing or tools.create_asset(name, "/Game/Look", unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -1300, -200)
    tex.set_editor_property("texture", texture)
    # la texture est déjà décodée (linéaire) : on la réencode pour le code commun, qui décode les couleurs sRGB
    enc = custom_node(mat, "return pow(max(C, 0.0), 1.0 / 2.2);", unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["C"], -1100, -200)
    mel.connect_material_expressions(tex, "RGB", enc, "C")
    one = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -1100, -100)
    one.set_editor_property("r", 1.0)
    nrm = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -1100, 0)
    cam = mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -1100, 100)
    half = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -1100, 200)
    half.set_editor_property("r", 0.5)
    node = custom_node(mat, PEINT_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                       ["Albedo", "AO", "N", "L", "V", "Brush", "Lumiere", "Ombre", "Ciel"], -500, 0)
    mel.connect_material_expressions(enc, "", node, "Albedo")
    mel.connect_material_expressions(one, "", node, "AO")
    mel.connect_material_expressions(nrm, "", node, "N")
    mel.connect_material_expressions(cam, "", node, "V")
    mel.connect_material_expressions(half, "", node, "Brush")
    for i, (pin, name_) in enumerate((("L", "SoleilDir"), ("Lumiere", "Lumiere"), ("Ombre", "Ombre"), ("Ciel", "CielAppoint"))):
        cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1100, 300 + 100 * i)
        cp.set_editor_property("collection", MPC)
        cp.set_editor_property("parameter_name", name_)
        mel.connect_material_expressions(cp, "", node, pin)
    mel.connect_material_property(node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if flap_axis is not None:
        lp = mel.create_material_expression(mat, unreal.MaterialExpressionLocalPosition, -900, 500)
        tt = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -900, 600)
        ax = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -900, 700)
        ax.set_editor_property("constant", unreal.LinearColor(*flap_axis, 1.0))
        hs = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -900, 800)
        hs.set_editor_property("r", half_span)
        fl = custom_node(mat, FLAP_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["LP", "T", "Axis", "Half"], -650, 600)
        for src, pin in ((lp, "LP"), (tt, "T"), (ax, "Axis"), (hs, "Half")):
            mel.connect_material_expressions(src, "", fl, pin)
        tr = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -400, 600)
        tr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
        tr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(fl, "", tr, "")
        mel.connect_material_property(tr, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError(f"{name} ne compile pas")
    mark_saved(mat, digest)
    return mat


def painted_model(model, name, flap=False):
    """Remplace les matériaux glTF du modèle par le look peint (texture de couleur conservée)."""
    mats = []
    for i in range(model.get_num_sections(0) if hasattr(model, "get_num_sections") else 1):
        mi = model.get_material(i)
        if mi is None:
            break
        tex = mel.get_material_instance_texture_parameter_value(mi, "BaseColorTexture") if isinstance(mi, unreal.MaterialInstance) else None
        if tex is None:
            mats.append(None)
            continue
        axis, half_span = None, 1.0
        if flap:
            box = model.get_bounding_box()
            ext = (box.max.x - box.min.x, box.max.y - box.min.y)
            axis = (1.0, 0.0, 0.0) if ext[0] >= ext[1] else (0.0, 1.0, 0.0)
            half_span = max(ext) / 2
        mats.append(peint_tex_material(f"M_Peint_{name}{i}", tex, axis, half_span))
    return mats


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
    if kind not in GLOW:      # les abysses gardent leur bioluminescence ; les autres prennent le look peint
        for i, pm in enumerate(painted_model(model, kind[3:], flap=(kind == "GB_Volante"))):
            if pm is not None:
                m.static_mesh_component.set_material(i, pm)
    return blk


creature("GB_Abysses", "GB_Abysses", ue(0, -60, -3.2))
for i in range(5):
    creature(f"GB_Troupeau{i}", "GB_Troupeau", ue(0, -60 - i * 4, 0.6))
creature("GB_Volante", "GB_Volante", ue(*moon_xy, 150))
if model is not None:      # la barque prend aussi le look peint
    for i, pm in enumerate(painted_model(model, "Barque")):
        if pm is not None:
            hull.static_mesh_component.set_material(i, pm)

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
# Valeurs de S2 (pipeline/style/ambiance.json) ; la séquence les anime ensuite beat par beat (animatic.py).
with open(os.path.join(ROOT, "pipeline", "style", "ambiance.json"), encoding="utf-8") as f:
    fog_s2 = next(b for b in json.load(f)["beats"] if b["id"] == "S2-PONTON")
fc.set_editor_property("fog_density", fog_s2["densite"])
fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(*fog_s2["brume_lineaire"], 1.0))
fc.set_editor_property("start_distance", 1500.0)
tag(actors.spawn_actor_from_class(unreal.PlayerStart, ue(start["x"], start["y"], 0.2)), "Depart")

# Pas de réglage d'exposition : l'exposition auto est coupée dans le projet (VR) et le moteur ignore alors
# toute compensation. La lisibilité du greybox se règle par l'intensité des lumières.

# Pas d'éclairage précalculé : le look peint est non éclairé (M_Peint) ; seuls la barque et les créatures
# utilisent encore les lumières, toutes dynamiques. Supprime « Lighting needs to be rebuilt » en jeu.
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property("force_no_precomputed_lighting", True)
for a in actors.get_all_level_actors():
    for comp in a.get_components_by_class(unreal.LightComponentBase):
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)

levels.save_current_level()
unreal.log(f"Greybox : {MAP} construit ({len(MESHES)} maillages)")
