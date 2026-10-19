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
        mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
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
               "CielAppoint": (0.1, 0.12, 0.2), "CielTeinte": (1.0, 1.0, 1.0), "Barque": (0.0, 0.0, 0.0),
               "AbyssPos": (0.0, 0.0, -10000.0)}
# CielLuminosite (ancien), apparition progressive des lucioles des berges et du nuage de l'envol
MPC_SCALARS = {"CielLuminosite": 1.0, "LucioleFade": 1.0, "EnvolFade": 0.0, "AbyssFade": 1.0,
               "FinaleFade": 0.0,    # nuée de lucioles du lac (S7)
               "Fondu": 0.0,         # fondu au noir (1 = noir), sphère devant les yeux : pas de post-traitement sur Quest
               "VieJour": 1.0}       # oiseaux, papillons, libellules : présents le jour, partis la nuit (lucioles)
MPC_DIGEST = spec_digest("mpc-v8", sorted(MPC_VECTORS), sorted(MPC_SCALARS))


def ambiance_mpc():
    """Collection de paramètres partagée (ciel, look peint) ; recréée seulement si sa liste change (les
    matériaux s'y réfèrent par identifiant)."""
    mpc = eal.load_asset(MPC_PATH) if eal.does_asset_exist(MPC_PATH) else tools.create_asset(
        "MPC_Ambiance", GB, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    if up_to_date(mpc, MPC_DIGEST):
        return mpc
    scalars = []
    for name, v in MPC_SCALARS.items():
        sp = unreal.CollectionScalarParameter()
        sp.set_editor_property("parameter_name", name)
        sp.set_editor_property("default_value", v)
        scalars.append(sp)
    vps = []
    for name, v in MPC_VECTORS.items():
        vp = unreal.CollectionVectorParameter()
        vp.set_editor_property("parameter_name", name)
        vp.set_editor_property("default_value", unreal.LinearColor(*v, 1.0))
        vps.append(vp)
    mpc.set_editor_property("scalar_parameters", scalars)
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

def wire_lantern(mat, node, wp=None):
    """Entrées communes à la lumière de la lanterne : position monde, temps, pose de la barque (MPC)."""
    wp = wp or mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1100, 900)
    tn = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1100, 1000)
    cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1100, 1100)
    cp.set_editor_property("collection", MPC)
    cp.set_editor_property("parameter_name", "Barque")
    mel.connect_material_expressions(wp, "", node, "WP")
    mel.connect_material_expressions(tn, "", node, "T")
    mel.connect_material_expressions(cp, "", node, "B")
    cam = mel.create_material_expression(mat, unreal.MaterialExpressionCameraPositionWS, -1100, 1200)
    mel.connect_material_expressions(cam, "", node, "Cam")


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


# Barque (retour d'Olivier du 19/10 : « la lanterne masque tout le décor » ; nouvelle image refs/barque.png, sans
# lanterne) : modèle TRELLIS.2, longueur 100 sur +X à l'import (proue côté corde, +X), largeur ±26, fond à -15,
# plat-bord à +7 au milieu, +15 aux pointes. Mis à 3,5 × 1,56 m (la proportion d'origine ferait 1,82 m de large),
# hauteur × 3 : franc-bord ~45 cm avec 22 cm de tirant d'eau.
BOAT_SCALE, BOAT_SCALE_Y, BOAT_SCALE_Z, BOAT_YAW = 3.5, 3.0, 3.0, 0.0
BOAT_BOTTOM, BOAT_DRAFT = -15.2, 22.0
# Lanterne : modèle à part (assets/3d/lanterne, papier à nervures), haute de 32 cm, posée bas sur l'avant droit (sur
# le banc avant) : elle éclaire la nuit sans masquer le décor. Centre dans le repère de la barque (cm).
LANTERN_H = 32.0
LANTERN_LOCAL = (125.0, 36.0, 40.0 + LANTERN_H / 2)
# Lanterne qui tangue (retour d'Olivier : « trop figée ») : même balancement, calculé dans le shader, pour le modèle de
# la lanterne et son halo. Pivot au pied de la lanterne, roulis ~3° autour de l'axe de la barque, tangage ~2°.
SWAY_CODE = """float ar = 0.055 * sin(T * 1.25) + 0.025 * sin(T * 0.73 + 1.7);   // roulis (rad)
float ap = 0.035 * sin(T * 0.97 + 0.6);                                   // tangage
float3 f = normalize(float3(F.xy, 0.0) + float3(1e-4, 0.0, 0.0));         // sens de la barque
float3 sd = cross(float3(0.0, 0.0, 1.0), f);
float3 v = WP.xyz - Pv;
float3 r1 = v * cos(ar) + cross(f, v) * sin(ar) + f * dot(f, v) * (1.0 - cos(ar));
float3 r2 = r1 * cos(ap) + cross(sd, r1) * sin(ap) + sd * dot(sd, r1) * (1.0 - cos(ap));
return (r2 - v) * W;"""
# lanterne et halo (centrés sur la lanterne, axe X = sens de la barque) : pivot à son pied
SWAY_CANDLE_CODE = f"""float W = 1.0;
float3 Pv = OP.xyz - float3(0.0, 0.0, {LANTERN_H / 2:.1f});
float3 F = TF.xyz;
""" + SWAY_CODE


def wire_sway(mat, code, forward, pivot_local=None):
    """Balancement de la lanterne en décalage de position (WPO), entrées : position monde et locale, temps, origine de
    l'objet, sens de la barque (forward local → monde) et pivot (local → monde, barque seulement)."""
    def to_world(vec, x, y):
        c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, x - 200, y)
        c.set_editor_property("constant", unreal.LinearColor(*vec, 0))
        t = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, x, y)
        t.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
        t.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(c, "", t, "")
        return t
    wp = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -900, 900)
    wp.set_editor_property("world_position_shader_offset", unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    names = ["WP", "LP", "T", "OP", "TF", "TP"]
    node = custom_node(mat, code, unreal.CustomMaterialOutputType.CMOT_FLOAT3, names, -500, 900)
    srcs = {"WP": wp,
            "LP": mel.create_material_expression(mat, unreal.MaterialExpressionLocalPosition, -900, 1000),
            "T": mel.create_material_expression(mat, unreal.MaterialExpressionTime, -900, 1100),
            "OP": mel.create_material_expression(mat, unreal.MaterialExpressionObjectPositionWS, -900, 1200),
            "TF": to_world(forward, -700, 1300),
            "TP": to_world(pivot_local or (0, 0, 0), -700, 1400)}
    for n in names:
        mel.connect_material_expressions(srcs[n], "", node, n)
    mel.connect_material_property(node, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
CANDLE_RGB = (1.0, 0.55, 0.22)
SKY_DRIFT = 0.0004     # tours de panorama par seconde (vent dans les nuages)
SKY_UV_CODE = f"""float3 d = normalize(-Dir);
float u = 0.5 + atan2(d.y, d.x) / (2.0 * PI) + T * {SKY_DRIFT};
float e = asin(clamp(d.z, -1.0, 1.0));
float v = clamp(0.82 - e / (0.5 * PI) * 0.82, 0.0, 1.0);
return float2(u, v);"""
# Lune peinte dans le ciel (et non plus une sphère devant lui) : cachée par les nuages clairs, direction du repère
# « creature-lune » vue depuis la barque au sommet de S6 (la créature volante passe devant), haute de 22°.
_lm = MARKS["creature-lune"]
_pl = pose_at(_lm["t"])
_dx, _dy = _lm["x"] - _pl["x"], _lm["y"] - _pl["y"]
_dl = math.hypot(_dx, _dy)
_mv = (_dx / _dl, -_dy / _dl, math.tan(math.radians(22)))
_mn = math.sqrt(sum(c * c for c in _mv))
MOON_DIR = tuple(c / _mn for c in _mv)
MOON_RADIUS_DEG = 2.1
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
float3 col = sky + star * tw * night * clouds * saturate(d.z * 6.0) * 1.5;
// lune : disque doux et halo, masqués là où le ciel peint est un nuage (zones claires et peu bleues)
float md = dot(d, float3(%(mx).5f, %(my).5f, %(mz).5f));
float cr = cos(radians(%(mr).2f));
float disc = smoothstep(cr - 0.00004, cr + 0.00004, md);
float halo = pow(saturate((md - cr) / (1.0 - cr) * 0.5 + 0.5), 60.0) * 0.25 + pow(saturate(md), 2000.0) * 0.15;
float cloudy = saturate((Tex.r + 0.15 - Tex.b) * 3.0) * saturate(dot(Tex, float3(0.3, 0.5, 0.2)) * 2.0);
col += float3(1.0, 0.97, 0.88) * (disc * 1.1 + halo * (0.4 + night)) * (1.0 - cloudy * 0.9);
return col;""" % {"mx": MOON_DIR[0], "my": MOON_DIR[1], "mz": MOON_DIR[2], "mr": MOON_RADIUS_DEG}


with open(os.path.join(ROOT, "pipeline", "layout", "water_map.json"), encoding="utf-8") as f:
    WATER_MAP = json.load(f)
with open(os.path.join(ROOT, "assets", "textures", "stats.json"), encoding="utf-8") as _f:
    TEX_MEAN_EAU = json.load(_f).get("tex-eau", 0.25)     # luminance moyenne de l'eau peinte d'Olivier (textures.py)
WATER_CODE = """float3 v = -normalize(Dir.xyz);                       // de la caméra vers le point d'eau
float2 rp = float2(WP.x, -WP.y) / 100.0;                   // repère du tracé, mètres
float4 m = Texture2DSample(Map, MapSampler, (rp - float2(%(x0)f, %(y0)f)) / %(size)f);
float ca = (m.r - 0.5) * 0.5 * PI;                          // cap du courant (repère du tracé)
float2 fd = float2(cos(ca), -sin(ca));                      // sens du courant, repère Unreal
float lake = 1.0 - saturate((m.a - 0.5 + m.g) * 20.0);      // lac : courant presque nul
float speed = lerp(1.0, 0.25, lake);
float shore = m.b;                                          // 0 sur la rive, 1 à 8 m
// rides dans le repère monde (traits le long de la rivière, qui tourne peu) ; flowmap à deux phases : elles
// avancent avec le courant local sans s'étirer ni se casser là où il change de direction
float2 q = WP.xy / 350.0;
float ph0 = frac(T * 0.06), ph1 = frac(T * 0.06 + 0.5);
float w = abs(ph0 * 2.0 - 1.0);
float2 adv = fd * speed * 0.9;
// traits en travers de la rivière (horizontaux à l'écran pour qui regarde vers l'aval, comme dans l'eau
// peinte ; dans le sens du courant, la perspective les faisait converger en rayons)
float2 q0 = (q - adv * ph0).yx, q1 = (q - adv * ph1).yx;
float r0 = Texture2DSample(Rides, RidesSampler, q0 * float2(0.6, 2.2)).r;
float r1 = Texture2DSample(Rides, RidesSampler, q1 * float2(0.6, 2.2) + 0.5).r;
float rip = saturate(lerp(r0, r1, w) * 1.1);
float r2 = saturate(r0 * 0.7 + r1 * 0.3 + 0.25);   // variation lente sans lecture supplémentaire
// reflet du ciel peint, déformé par les rides
float3 rd = float3(v.x, v.y, abs(v.z));
float su = 0.5 + atan2(rd.y, rd.x) / (2.0 * PI) + T * %(drift)f;
float se = min(asin(clamp(rd.z, 0.0, 1.0)), 0.96);   // pas au-delà de 55° : au zénith l'équirectangulaire s'étire en rayons
float sv = clamp(0.82 - se / (0.5 * PI) * 0.82 + (rip - 0.3) * 0.025, 0.0, 1.0);
float3 sky = Texture2DSample(Sky, SkySampler, float2(su, sv)).rgb * Teinte.rgb;
float fr = 0.06 + 0.94 * pow(1.0 - abs(v.z), 4.0);
// reflet de la lisière : le rayon réfléchi part vers le haut, vers la rive qu'il rencontre (distance aux rives
// précalculée dans la carte ; dans le lac, intersection exacte avec le cercle de la rive) ; les arbres (~15 m,
// cime irrégulière) masquent le ciel sous l'angle de leur cime
float2 hd = normalize(rd.xy + float2(1e-4, 0.0));
float tanE = rd.z / max(length(rd.xy), 1e-3) + (rip - 0.3) * 0.06;
float c = dot(hd, float2(fd.y, -fd.x));                     // vers la rive gauche si > 0
float dist = c > 0.0 ? (m.a - 0.5) * 8000.0 / max(c, 0.05) : m.g * 4000.0 / max(-c, 0.05);
float2 pc = WP.xy - float2(%(lkx).1f, %(lky).1f);
float bq = dot(pc, hd);
dist = max(lerp(dist, -bq + sqrt(max(%(lkr2).1f - dot(pc, pc) + bq * bq, 0.0)), lake), 50.0);
float2 hp = WP.xy + hd * dist;
float crown = 1500.0 * (0.78 + 0.14 * sin(hp.x * 0.0031 + sin(hp.y * 0.0023) * 2.0) + 0.08 * sin(hp.y * 0.0071 - hp.x * 0.0043));
float above = crown / dist - tanE;                          // > 0 : le reflet tombe dans les arbres
float trees = max(1.0 - smoothstep(0.02, 0.15, shore), saturate(above * 3.0));
// reflet des berges peintes (retour du 19/10 : l'eau paraissait terne à côté du décor) : vert peint, plus clair vers
// la ligne des cimes éclairées, plus sombre au pied, strié par les rides ; il était presque noir
float tops = 1.0 - saturate(above * 5.0);
float3 forest = Lumiere.rgb * lerp(float3(0.07, 0.13, 0.10), float3(0.2, 0.3, 0.17), tops) * (0.8 + 0.4 * r2)
              + sky * 0.12 * tops;
float3 refl = lerp(sky, forest, trees * 0.9);
float3 deep = (Lumiere.rgb * 0.5 + 0.2) * lerp(float3(0.03, 0.095, 0.095), float3(0.012, 0.045, 0.055), shore);
float3 col = lerp(deep, refl, fr);
// crêtes des rides : traits de lumière du ciel, comme posés au pinceau
col += rip * rip * (0.3 + 0.7 * fr) * (sky * 1.1 + Lumiere.rgb * 0.05) * (1.0 - trees * 0.6);
// scintillements : la pointe des crêtes renvoie le ciel en éclats qui bougent avec le courant
col += pow(saturate(rip * 1.25 - 0.2), 6.0) * fr * (sky * 1.4 + Lumiere.rgb * 0.15) * (1.0 - trees * 0.5);
// reflets des lueurs (plantes lumineuses la nuit, lucioles des berges, nuée finale) : carte vue de dessus lue au point
// de rive dans la direction du regard ; une source basse (< 3 m) se reflète près de la ligne d'eau ; traînées brisées
// par les rides
float2 hm = (float2(hp.x, -hp.y) / 100.0 - float2(%(x0)f, %(y0)f)) / %(size)f;
float3 gl = Texture2DSample(Glow, GlowSampler, hm).rgb;
float night = 1.0 - saturate(Day);
float3 glow = gl.r * night * float3(0.45, 0.9, 1.0) + gl.g * saturate(Lf) * (0.25 + 0.75 * night) * float3(1.0, 0.9, 0.45)
            + gl.b * saturate(Ff) * float3(1.0, 0.85, 0.4);
col += glow * (1.0 - saturate(tanE * dist / 300.0)) * (0.15 + 1.2 * rip * rip) * (0.5 + 0.5 * fr) * 2.6;
// chemin de lune (la nuit) : reflet de la lune étiré à la verticale par les rides, en éclats sur les crêtes
float nsky = saturate(1.0 - dot(Teinte.rgb, float3(0.3, 0.5, 0.2)) * 3.0);
float3 rdm = normalize(rd + float3((r2 - 0.5) * 0.04, (r1 - 0.5) * 0.04, (rip - 0.45) * 0.5));
float mg = smoothstep(0.990, 0.9985, dot(rdm, float3(%(mx).5f, %(my).5f, %(mz).5f)));
col += float3(1.0, 0.95, 0.82) * mg * (0.4 + 1.6 * rip) * nsky * (1.0 - trees * 0.8) * 1.8;   // lumière vive : visible même hors incidence rasante
// eau peinte d'Olivier (refs/tex-eau.png), entraînée par le courant avec les rides : vue plongeante, on voit la
// matière peinte de l'eau ; partout, elle module la valeur (touches claires et creux sombres)
float3 we = Texture2DSample(EauTex, EauTexSampler, (q - adv * ph0) * 1.3).rgb;
float wl = dot(we, float3(0.3, 0.6, 0.1));
col = lerp(col, we * (Lumiere.rgb * 0.6 + 0.12) + sky * 0.08, (1.0 - fr) * 0.5 * (1.0 - trees * 0.4));
col *= 0.82 + 0.36 * saturate(wl / %(eaumean).4f);
// écume le long des berges
float foam = (1.0 - smoothstep(0.0, 0.05, shore)) * (0.55 + 0.45 * r2);
col = lerp(col, Lumiere.rgb * 0.5 + sky * 0.35, foam * 0.75);
// autour de la barque (B : x, y, lacet en z) : sillage en V, bourrelet d'écume le long de la coque, reflet de la
// lanterne ; pas d'eau dans la coque
float cb = cos(B.z), sb = sin(B.z);
float2 rel = WP.xy - B.xy;
float lx = dot(rel, float2(cb, sb)), ly = dot(rel, float2(-sb, cb));
float hull = (lx / 178.0) * (lx / 178.0) + (ly / 78.0) * (ly / 78.0);   // coque 3,5 × 1,56 m
float arm = abs(abs(ly) - max(-lx - 120.0, 0.0) * 0.36);
float wake = exp(-arm / 20.0) * saturate((-lx - 120.0) / 80.0) * exp(lx / 1600.0) * (0.5 + 0.5 * sin(lx * 0.07 + T * 2.6 + r2 * 3.0));
float ring = exp(-abs(sqrt(hull) - 1.1) * 8.0) * (0.55 + 0.45 * sin(atan2(ly, lx) * 11.0 + T * 3.2)) * saturate(sqrt(hull) - 0.95) * 4.0;
float boatfoam = saturate(wake * 0.8 + ring * 0.7);
col = lerp(col, Lumiere.rgb * 0.45 + sky * 0.45, boatfoam * 0.65);
float2 lp = B.xy + float2(cb, sb) * %(lantx).1f + float2(-sb, cb) * %(lanty).1f;
float dlw = length(WP.xy - lp);
float flick = 0.86 + 0.1 * sin(T * 11.0) * sin(T * 6.7 + 1.3) + 0.04 * sin(T * 23.0);
col += float3(%(cr).2f, %(cg).2f, %(cb).2f) * flick * (0.25 + 0.75 * rip) * 0.9 / (1.0 + (dlw / 140.0) * (dlw / 140.0));
// halo de la créature des abysses sur la surface (lumière vue à travers l'eau), plus faible quand elle s'enfonce
float2 da = WP.xy - Ab.xy;
float halo = exp(-dot(da, da) / (420.0 * 420.0)) * saturate(1.0 + Ab.z / 900.0) * saturate(Af);
col += float3(0.15, 1.6, 2.0) * 0.18 * halo * (0.6 + 0.4 * rip);
float op = max(lerp(0.68, 0.97, fr) * (1.0 - 0.55 * halo), max(foam, boatfoam * 0.8));   // eau plus claire au-dessus de la créature
op *= smoothstep(0.9, 1.02, hull);
return float4(col, op);""" % {"lantx": LANTERN_LOCAL[0], "lanty": LANTERN_LOCAL[1], "cr": CANDLE_RGB[0], "cg": CANDLE_RGB[1], "cb": CANDLE_RGB[2], "x0": WATER_MAP["x0"], "y0": WATER_MAP["y0"], "size": WATER_MAP["size_m"], "drift": SKY_DRIFT,
   "mx": MOON_DIR[0], "my": MOON_DIR[1], "mz": MOON_DIR[2], "eaumean": TEX_MEAN_EAU, "lkx": RIVER["lake"]["x"] * 100, "lky": -RIVER["lake"]["y"] * 100, "lkr2": (RIVER["lake"]["radius_m"] * 100) ** 2}


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


PEINT_CODE = """#define LANT_X %(lx).1f
#define LANT_Y %(ly).1f
#define LANT_Z %(lz).1f
#define CANDLE float3(%(cr).2f, %(cg).2f, %(cb).2f)
float3 n = normalize(N.xyz);
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
// lanterne de proue : lumière chaude de bougie qui vacille, sur tout ce qui l'entoure (B = barque : x, y, lacet en z)
float cb = cos(B.z), sb = sin(B.z);
float3 lp = float3(B.x + cb * LANT_X - sb * LANT_Y, B.y + sb * LANT_X + cb * LANT_Y, LANT_Z);
float dl = length(WP.xyz - lp);
float flick = 0.86 + 0.1 * sin(T * 11.0) * sin(T * 6.7 + 1.3) + 0.04 * sin(T * 23.0);
float lamp = flick * saturate(1.0 - dl / 1100.0) / (1.0 + (dl / 170.0) * (dl / 170.0));
col += albedo * CANDLE * lamp * (0.3 + 0.7 * saturate(dot(n, normalize(lp - WP.xyz)))) * 2.4;
// sous l'eau (eau plate à z = 0) : la couleur s'éteint vers celle de l'eau profonde selon la longueur du trajet
// sous la surface (exact pour une eau plate, sans lire la profondeur : impossible sur Quest sans HDR mobile)
float under = -WP.z;
if (under > 0.0)
{
    float lw = under * length(Cam.xyz - WP.xyz) / max(Cam.z - WP.z, 1.0);
    float tr = exp(-lw * 0.03);           // moitié à ~23 cm de trajet : bouts de racines et fond ne se découpent plus
    tr = tr * tr * (3.0 - 2.0 * tr);
    col = lerp((Lumiere.rgb * 0.5 + 0.2) * float3(0.02, 0.06, 0.07), col, tr);
}
// ligne d'eau : liseré clair là où l'objet traverse la surface
col += Lumiere.rgb * 0.06 * (1.0 - smoothstep(0.0, 3.5, abs(WP.z)));
return col;""" % {"lx": LANTERN_LOCAL[0], "ly": LANTERN_LOCAL[1], "lz": LANTERN_LOCAL[2], "cr": CANDLE_RGB[0], "cg": CANDLE_RGB[1], "cb": CANDLE_RGB[2]}


# Une seule lecture de texture par pixel (projection selon l'axe dominant de la normale), au lieu des trois
# d'un vrai triplanaire : mesure du 18/10, GPU saturé sur Quest ; les bords de projection se perdent dans la touche.
TRI_CODE = """float3 n = abs(N.xyz);
float3 pp = Local > 0.5 ? LP.xyz : P.xyz;      // repère de l'objet pour ce qui bouge (plancher de la barque)
float2 uv = (n.z >= n.x && n.z >= n.y) ? pp.xy : ((n.x >= n.y) ? pp.yz : pp.xz);
return Texture2DSample(Tex, TexSampler, uv / Scale).rgb;"""
TOP_CODE = """return Texture2DSample(Tex, TexSampler, P.xy / Scale).rgb;"""
DETAIL_CODE = """float3 a = pow(max(Albedo.rgb, 0.0), 2.2);
float3 lw = float3(0.2126, 0.7152, 0.0722);
// terrain : les sommets verts prennent la seconde texture (herbe), les autres la première (terre)
float g = saturate((Albedo.g - Albedo.r) * 5.0) * Blend2;
float3 dc = lerp(D.rgb, D2.rgb, g);
float mean = max(lerp(Mean, Mean2, g), 0.02);
float l = dot(dc, lw) / mean;
// variation par instance (arbres instanciés : chaque arbre a sa teinte ; 0 hors instances)
float vr = (R - 0.5) * Vary;
a *= 1.0 + vr;
a.r *= 1.0 + vr * 0.9;
a.b *= 1.0 - vr * 0.5;
float3 res = a * lerp(1.0, l, Strength);
// couleur de la texture ramenée à la valeur de la couleur du sommet (touches colorées de la peinture)
float3 tc = dc / mean * dot(a, lw);
res = lerp(res, tc, Mix);
return pow(max(res, 0.0), 1.0 / 2.2);"""
DETAIL_SCALARS = {"DetailScale": 300.0, "DetailStrength": 0.0, "ColorMix": 0.0, "Blend2": 0.0, "DetailMean": 0.25,
                  "DetailMean2": 0.25, "Vary": 0.0, "LocalSpace": 0.0}


def look_texture(tid, srgb=True, compression=None):
    """Texture peinte assets/textures/<tid>.png → /Game/Look/Textures (réimportée si le fichier change).
    srgb=False : données (carte de l'eau, rides), lues telles quelles."""
    import hashlib
    src = os.path.join(ROOT, "assets", "textures", f"{tid}.png")
    with open(src, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12]
    path = f"/Game/Look/Textures/{tid.replace('-', '_')}"
    tex = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(tex, digest) and tex.blueprint_get_size_x() > 32:
        return tex
    if tex is not None and tex.blueprint_get_size_x() <= 32:     # import raté (constaté le 19/10 : 32 × 32, tout blanc)
        eal.delete_asset(path)
    import shutil
    tmp = os.path.join(ROOT, "Unreal", "Saved", "import", f"{tid.replace('-', '_')}.png")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    shutil.copyfile(src, tmp)
    for attempt in range(3):     # le premier import d'une texture neuve donne parfois un asset de 32 × 32 (constaté le 19/10)
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = tmp, "/Game/Look/Textures"
        task.automated, task.replace_existing, task.save = True, True, True
        tools.import_asset_tasks([task])
        tex = eal.load_asset(path)
        if tex is not None and tex.blueprint_get_size_x() > 32:
            break
        unreal.log_warning(f"{tid} : import en {tex.blueprint_get_size_x() if tex else 0} px, nouvel essai")
        if tex is not None:
            eal.delete_asset(path)
    if not srgb:
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", compression or unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    mark_saved(tex, digest)
    return tex


with open(os.path.join(ROOT, "assets", "textures", "stats.json"), encoding="utf-8") as f:
    TEX_MEAN = json.load(f)
WATER_MAP_TEX = look_texture("eau_carte", srgb=False)
RIDES_TEX = look_texture("rides", srgb=False)
EAU_TEX = look_texture("tex-eau")       # eau peinte d'Olivier (refs/tex-eau.png → textures.py)
GLOW_TEX = look_texture("eau_lueurs", srgb=False, compression=unreal.TextureCompressionSettings.TC_DEFAULT)   # glow_map.py


UNDERWATER_START = "// sous l'eau (eau plate à z = 0)"


def dry_code(code):
    """PEINT_CODE sans l'absorption sous l'eau ni la ligne d'eau : pour ce qui reste hors de l'eau (arbres,
    buissons, herbe, troncs) : depuis l'ajout de ce calcul sur tous les pixels, S2-S3 sont tombés de 67 à 57-59 i/s au Quest."""
    a, b = code.index(UNDERWATER_START), code.index("return col;")
    return code[:a] + code[b:]


def peint_material(name="M_Peint", dithered=False, underwater=True):
    """M_Peint : couleur des sommets, ombrage deux tons ; voir PEINT_CODE. dithered : fondu tramé entre niveaux de
    détail (arbres instanciés : ils ne « se redessinent » plus d'un coup)."""
    path = f"/Game/Look/{name}"
    brush = brush_texture()
    default_tex = look_texture("tex-mousse")
    code = PEINT_CODE if underwater else dry_code(PEINT_CODE)
    digest = spec_digest("peint-v14", dithered, underwater, code, TRI_CODE, TOP_CODE, DETAIL_CODE, sorted(DETAIL_SCALARS.items()),
                         MPC_DIGEST, eal.get_metadata_tag(brush, "source_sha1"))
    existing = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(existing, digest):
        return existing
    mat = existing or tools.create_asset(name, "/Game/Look", unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("dithered_lod_transition", dithered)
    # forêt instanciée (HISM) : sans cet usage déclaré, le jeu empaqueté remplace le matériau par celui par défaut
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
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
    node.set_editor_property("code", code)
    node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    names = ["Albedo", "AO", "N", "L", "V", "Brush", "Lumiere", "Ombre", "Ciel", "WP", "T", "B", "Cam"]
    inputs = []
    for n in names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        inputs.append(ci)
    node.set_editor_property("inputs", inputs)
    # Détail peint : textures du type de surface (paramètres des instances MI_Peint_*), projection monde
    # triplanaire pour la première, de dessus pour la seconde (terrain : herbe), modulant la couleur des sommets.
    sp = {}
    for i, (name, v) in enumerate(DETAIL_SCALARS.items()):
        sp[name] = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -1900, -600 + 70 * i)
        sp[name].set_editor_property("parameter_name", name)
        sp[name].set_editor_property("default_value", v)
    tobj = []
    for i, name in enumerate(("Detail", "Detail2")):
        t = mel.create_material_expression(mat, unreal.MaterialExpressionTextureObjectParameter, -1900, -1000 + 150 * i)
        t.set_editor_property("parameter_name", name)
        t.set_editor_property("texture", default_tex)
        tobj.append(t)
    tri = custom_node(mat, TRI_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Tex", "P", "N", "Scale", "LP", "Local"], -1600, -900)
    mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionLocalPosition, -1900, -1100), "", tri, "LP")
    mel.connect_material_expressions(sp["LocalSpace"], "", tri, "Local")
    top = custom_node(mat, TOP_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Tex", "P", "Scale"], -1600, -750)
    for nd, t in ((tri, tobj[0]), (top, tobj[1])):
        mel.connect_material_expressions(t, "", nd, "Tex")
        mel.connect_material_expressions(wp, "", nd, "P")
        mel.connect_material_expressions(sp["DetailScale"], "", nd, "Scale")
    mel.connect_material_expressions(nrm, "", tri, "N")
    det = custom_node(mat, DETAIL_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                      ["Albedo", "D", "D2", "Strength", "Mix", "Blend2", "Mean", "Mean2", "R", "Vary"], -1300, -500)
    mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionPerInstanceRandom, -1600, -400), "", det, "R")
    mel.connect_material_expressions(sp["Vary"], "", det, "Vary")
    mel.connect_material_expressions(vc, "", det, "Albedo")
    mel.connect_material_expressions(tri, "", det, "D")
    mel.connect_material_expressions(top, "", det, "D2")
    for pin, name in (("Strength", "DetailStrength"), ("Mix", "ColorMix"), ("Blend2", "Blend2"), ("Mean", "DetailMean"),
                      ("Mean2", "DetailMean2")):
        mel.connect_material_expressions(sp[name], "", det, pin)
    mel.connect_material_expressions(det, "", node, "Albedo")     # couleur des sommets enrichie du détail peint
    wire_lantern(mat, node, wp)
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
        raise RuntimeError(f"{name} ne compile pas (voir l'éditeur de matériau)")
    mark_saved(mat, digest)
    return mat


MATS = {
    "Peint": peint_material(),
    # sans fondu tramé : il empêche le GPU du Quest de rejeter tôt les pixels cachés (houppiers superposés) ;
    # mesure du 18/10 : la forêt coûtait 6,4 ms avec lui
    "PeintArbreBase": peint_material("M_PeintArbre", dithered=False, underwater=False),
    "PeintSecBase": peint_material("M_PeintSec", underwater=False),     # feuillage, herbe, troncs : hors de l'eau
    "Terrain": material("Terrain", (0.16, 0.22, 0.08)),
    "Eau": material("Eau", (0.01, 0.025, 0.035), roughness=0.7, specular=0.08, opacity=0.55),
    "Bois": material("Bois", (0.18, 0.11, 0.06)),
    "Creature": material("Creature", (0.0, 0.6, 0.7), emissive=True),  # bioluminescente
    "Troupeau": material("Troupeau", (0.18, 0.30, 0.08)),
    "Volante": material("Volante", (0.75, 0.80, 0.85)),
    "Lune": material("Lune", (14.0, 13.5, 12.0), emissive=True),
    "Lanterne": material("Lanterne", (6.0, 2.5, 0.6), emissive=True),
    "LanternePapier": None,     # bougie qui vacille, voir candle_materials()
    "Luciole": None,      # matériau animé, voir firefly_material()
    "Roseau": material("Roseau", (0.045, 0.075, 0.025), roughness=0.95, specular=0.1),
    "Nenuphar": material("Nenuphar", (0.06, 0.20, 0.07), roughness=0.85, specular=0.1),
}


# Lucioles en particules : carré orienté face à l'œil (vecteurs droite / haut de la vue), dérive lente propre à
# chaque luciole (phase dans uv0), lueur douce dessinée dans le carré (coin dans uv1), clignotement, apparition
# progressive (paramètre de collection animé par la séquence). Additif, sans écriture de profondeur.
FIREFLY_CODE_WPO = """float ph = UV.x * 6.2832;
float3 drift = Amp * float3(sin(T * 0.61 + ph), cos(T * 0.47 + ph * 1.7), 0.6 * sin(T * 0.83 + UV.y * 6.2832));
return drift + (Right.xyz * C.x + Up.xyz * C.y) * Size;"""
FIREFLY_CODE_GLOW = """float d2 = dot(C, C);
float b = 0.5 + 0.5 * sin(T * (1.1 + UV.y) + UV.x * 40.0);
float blink = 0.2 + 0.8 * b * b;
float core = exp(-d2 * 18.0);
float halo = exp(-d2 * 3.5) * 0.35 * saturate(1.0 - d2);   // nul au bord du carré (sinon on voit le carré)
return Col.rgb * (core + halo) * blink * saturate(Fade * 2.0 - UV.y);   // s'allument une à une"""


def firefly_material(color=(4.0, 5.0, 1.2), amp_cm=30.0, name="Luciole", size_cm=14.0, fade="LucioleFade"):
    """Lucioles : particules lumineuses face à l'œil, animées entièrement dans le shader (rien sur le CPU)."""
    path = f"{GB}/M_GB_{name}"
    digest = spec_digest("luciole-v4", color, amp_cm, size_cm, fade, FIREFLY_CODE_WPO, FIREFLY_CODE_GLOW, MPC_DIGEST)
    existing = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(existing, digest):
        return existing
    mat = existing or tools.create_asset(f"M_GB_{name}", GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("two_sided", True)
    t = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1000, 0)
    uv0 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1000, 100)
    uv1 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1000, 200)
    uv1.set_editor_property("coordinate_index", 1)
    consts = {}
    for i, (n, v) in enumerate((("Amp", amp_cm), ("Size", size_cm))):
        consts[n] = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -1000, 300 + 80 * i)
        consts[n].set_editor_property("r", v)
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1000, 500)
    col.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    axes = []
    for i, v in enumerate(((1, 0, 0), (0, 1, 0))):                     # droite et haut de la vue, en monde
        c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1000, 600 + 100 * i)
        c.set_editor_property("constant", unreal.LinearColor(*v, 1.0))
        tr = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -800, 600 + 100 * i)
        tr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_VIEW)
        tr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(c, "", tr, "")
        axes.append(tr)
    fd = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1000, 800)
    fd.set_editor_property("collection", MPC)
    fd.set_editor_property("parameter_name", fade)
    wpo = custom_node(mat, FIREFLY_CODE_WPO, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                      ["T", "UV", "C", "Amp", "Size", "Right", "Up"], -500, 300)
    glow = custom_node(mat, FIREFLY_CODE_GLOW, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                       ["T", "UV", "C", "Col", "Fade"], -500, 0)
    for node in (wpo, glow):
        mel.connect_material_expressions(t, "", node, "T")
        mel.connect_material_expressions(uv0, "", node, "UV")
        mel.connect_material_expressions(uv1, "", node, "C")
    mel.connect_material_expressions(consts["Amp"], "", wpo, "Amp")
    mel.connect_material_expressions(consts["Size"], "", wpo, "Size")
    mel.connect_material_expressions(axes[0], "", wpo, "Right")
    mel.connect_material_expressions(axes[1], "", wpo, "Up")
    mel.connect_material_expressions(col, "", glow, "Col")
    mel.connect_material_expressions(fd, "", glow, "Fade")
    mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError(f"M_GB_{name} ne compile pas")
    mark_saved(mat, digest)
    return mat


MATS["Luciole"] = firefly_material()
# nuage de l'envol : grandes boucles irrégulières propres à chaque luciole (la trajectoire du nuage était trop droite)
MATS["LucioleEnvol"] = firefly_material(amp_cm=260.0, name="LucioleEnvol", size_cm=16.0, fade="EnvolFade")
MATS["LucioleFinale"] = firefly_material(amp_cm=140.0, name="LucioleFinale", size_cm=15.0, fade="FinaleFade")

FLICKER = "(0.86 + 0.1 * sin(T * 11.0) * sin(T * 6.7 + 1.3) + 0.04 * sin(T * 23.0))"


def candle_materials():
    """Lanterne : papier lumineux qui vacille comme une bougie, et halo doux autour (sphère additive dont la
    lueur décroît vers les bords). Même vacillement que la lumière portée calculée dans M_Peint et l'eau."""
    out = {}
    for name, code, blend in (
            ("LanternePapier", f"return float3({CANDLE_RGB[0]}, {CANDLE_RGB[1]}, {CANDLE_RGB[2]}) * 1.5 * {FLICKER};",
             unreal.BlendMode.BLEND_OPAQUE),
            ("HaloLanterne", f"float f = pow(saturate(dot(normalize(N.xyz), normalize(V.xyz))), 2.5);\n"
                             f"return float3({CANDLE_RGB[0]}, {CANDLE_RGB[1]}, {CANDLE_RGB[2]}) * 0.09 * f * f * {FLICKER};",
             unreal.BlendMode.BLEND_ADDITIVE)):
        path = f"{GB}/M_GB_{name}"
        digest = spec_digest("bougie-v4", code, SWAY_CANDLE_CODE)
        mat = eal.load_asset(path) if eal.does_asset_exist(path) else None
        if not up_to_date(mat, digest):
            mat = mat or tools.create_asset(f"M_GB_{name}", GB, unreal.Material, unreal.MaterialFactoryNew())
            mel.delete_all_material_expressions(mat)
            mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
            mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
            mat.set_editor_property("blend_mode", blend)
            node = custom_node(mat, code, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["T", "N", "V"], -400, 0)
            mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionTime, -700, 0), "", node, "T")
            mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -700, 100), "", node, "N")
            mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -700, 200), "", node, "V")
            mel.connect_material_property(node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            wire_sway(mat, SWAY_CANDLE_CODE, (1, 0, 0))
            mel.recompile_material(mat)
            if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
                raise RuntimeError(f"M_GB_{name} ne compile pas")
            mark_saved(mat, digest)
        out[name] = mat
    return out


MATS.update(candle_materials())

# Instances du look peint par type de surface : (texture, seconde texture, échelle cm, force, mélange couleur)
SURFACES = {
    "PeintFeuillage": ("tex-mousse", None, 260.0, 0.75, 0.45, 0.0, "PeintSecBase"),
    "PeintBois": ("tex-ecorce", None, 160.0, 0.7, 0.3),                                  # arche des racines : dans l'eau
    "PeintBoisSec": ("tex-ecorce", None, 160.0, 0.7, 0.3, 0.0, "PeintSecBase"),
    "PeintSol": ("tex-herbe", None, 120.0, 0.6, 0.35, 0.0, "PeintSecBase"),
    "PeintRoche": ("tex-roche", None, 140.0, 0.7, 0.35),
    "PeintTerrain": ("tex-terre", "tex-herbe", 350.0, 0.7, 0.4),
    "PeintPlanches": ("tex-planches", None, 90.0, 0.7, 0.5, 0.0, "Peint", True),   # plancher : suit la barque
    "PeintArbre": ("tex-mousse", None, 240.0, 0.75, 0.45, 0.45, "PeintArbreBase"),   # arbres instanciés : teinte par arbre
    "PeintTronc": ("tex-ecorce", None, 150.0, 0.7, 0.3, 0.25, "PeintArbreBase"),
}


def surface_instance(name, tex1, tex2, scale, strength, mix, vary=0.0, parent="Peint", local=False):
    path = f"/Game/Look/MI_{name}"
    t1 = look_texture(tex1)
    t2 = look_texture(tex2) if tex2 else t1
    digest = spec_digest("mi-v4", eal.get_metadata_tag(MATS[parent], "source_sha1"), parent, tex1, tex2, scale, strength, mix, vary, local,
                         eal.get_metadata_tag(t1, "source_sha1"), eal.get_metadata_tag(t2, "source_sha1"))
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(mi, digest):
        return mi
    mi = mi or tools.create_asset(f"MI_{name}", "/Game/Look", unreal.MaterialInstanceConstant,
                                  unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", MATS[parent])
    mel.set_material_instance_texture_parameter_value(mi, "Detail", t1)
    mel.set_material_instance_texture_parameter_value(mi, "Detail2", t2)
    for k, v in (("DetailScale", scale), ("DetailStrength", strength), ("ColorMix", mix), ("Blend2", 1.0 if tex2 else 0.0),
                 ("DetailMean", TEX_MEAN[tex1]), ("DetailMean2", TEX_MEAN[tex2 or tex1]), ("Vary", vary),
                 ("LocalSpace", 1.0 if local else 0.0)):
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    mel.update_material_instance(mi)
    mark_saved(mi, digest)
    return mi


for name, spec in SURFACES.items():
    MATS[name] = surface_instance(name, *spec)
MESH_MATS = {"Terrain": "PeintTerrain", "ArcheRacines": "PeintBois", "Lucioles": "LucioleEnvol", "LuciolesBerges": "Luciole",
             "LuciolesLac": "LucioleFinale",
             "Roseaux": "PeintSol", "Nenuphars": "Peint"}


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
    if "uv1" in data:                                  # second canal (coins des particules de lucioles)
        buffers.uv1 = [unreal.Vector2D(*uv) for uv in data["uv1"]]
    for ch in ("uv2", "uv3"):                          # paramètres exacts (la couleur des sommets les déforme)
        if ch in data:
            setattr(buffers, ch, [unreal.Vector2D(*uv) for uv in data[ch]])
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
# Eau en grille de 5 m (et non plus un seul carré) : sur Quest la brume est calculée aux sommets.
_n = 5.0
_nx, _ny = int((b["x1"] - b["x0"]) / _n) + 1, int((b["y1"] - b["y0"]) / _n) + 1
_wv = [[b["x0"] + i * _n, b["y0"] + j * _n, 0.0] for j in range(_ny + 1) for i in range(_nx + 1)]
_wt = []
for j in range(_ny):
    for i in range(_nx):
        a0 = j * (_nx + 1) + i
        _wt += [[a0, a0 + 1, a0 + _nx + 2], [a0, a0 + _nx + 2, a0 + _nx + 1]]
GEO["meshes"]["Eau"] = {"vertices": _wv, "triangles": _wt, "normals": [[0, 0, 1]] * len(_wv)}
MESH_MATS["Eau"] = "Eau"
with open(os.path.join(ROOT, "pipeline", "layout", "vegetation.json"), encoding="utf-8") as f:
    VEG = json.load(f)
KIND_MATS = {"feuillage": "PeintFeuillage", "bois": "PeintBoisSec", "sol": "PeintSol", "roche": "PeintRoche"}
for name, data in VEG["meshes"].items():
    GEO["meshes"][name] = data
    MESH_MATS[name] = KIND_MATS.get(name.rsplit("_", 1)[-1], "Peint")
CHUNK_LOD_SCREEN = (1.0, 0.5, 0.28)    # tronçon de 30 m : fin à moins de ~37 m de son centre, allégé jusqu'à ~66 m
_fv = [[0.0, 0.0, 0.05]] + [[1.45 * math.cos(2 * math.pi * k / 32), 0.40 * math.sin(2 * math.pi * k / 32), 0.05] for k in range(32)]
def build_lod_mesh(name, lods, screen_sizes=(1.0, 0.85, 0.42)):
    """Maillage statique à plusieurs niveaux de détail (LOD0 le plus fin) ; reconstruit si une source change."""
    import hashlib
    digest = hashlib.sha1(json.dumps([lods, screen_sizes], sort_keys=True).encode()).hexdigest()[:12]
    path = f"{GB}/SM_{name}"
    if eal.does_asset_exist(path) and eal.get_metadata_tag(eal.load_asset(path), "lods_sha1") == digest:
        return eal.load_asset(path)
    mesh = build_mesh(name, lods[0])
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for i, data in enumerate(lods[1:], start=1):
        src = build_mesh(f"{name}_LOD{i}", data)
        sms.set_lod_from_static_mesh(mesh, i, src, 0, True)
    mesh.set_editor_property("auto_compute_lod_screen_size", False) if hasattr(mesh, "auto_compute_lod_screen_size") else None
    sms.set_lod_screen_sizes(mesh, list(screen_sizes))
    eal.set_metadata_tag(mesh, "lods_sha1", digest)
    eal.save_loaded_asset(mesh)
    return mesh


TREE_KIND_MATS = {"feuillage": "PeintArbre", "bois": "PeintTronc"}
TREE_MESHES = {}
MESHES = {name: (build_lod_mesh(name, data["lods"], CHUNK_LOD_SCREEN) if "lods" in data else build_mesh(name, data))
          for name, data in GEO["meshes"].items()}
for pname, lods in VEG.get("prototypes", {}).items():
    for kind in TREE_KIND_MATS:
        if kind in lods["lod0"]:
            TREE_MESHES[(pname, kind)] = build_lod_mesh(f"Arbre_{pname}_{kind}",
                                                        [lods[f"lod{i}"].get(kind, lods["lod0"][kind]) for i in range(3)])

FLOOR_MESH = build_mesh("PlancherBarque", {"vertices": _fv, "triangles": [[0, 1 + k, 1 + (k + 1) % 32] for k in range(32)],
                                           "normals": [[0, 0, 1]] * len(_fv), "color": [0.46, 0.33, 0.21, 0.95]})
OBSOLETE = ["SM_Foret", "SM_ArbreColossal", "SM_ArbreLanternes", "M_GB_Foret"] + \
    [f"SM_{n}" for n in ("Lisiere", "ArbreColossalPeint", "ArbreLanternesPeint", "Collines")] + [f"SM_Vegetation{i:02d}" for i in range(12)] + \
    ["SM_Lisiere_feuillage", "SM_Lisiere_bois"]    # lisière découpée en 8 morceaux
for old in OBSOLETE:   # remplacés (look peint, puis découpage par type de surface)
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
    if name in ("Lucioles", "LuciolesLac"):                     # déplacés par la séquence
        a.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    if name == "Lucioles":
        a.set_actor_location(unreal.Vector(0, 0, -3000), False, False)   # sous le terrain jusqu'à l'envol (séquence)

# Forêt instanciée : un acteur par modèle et par type de surface, composant HISM (LOD et culling par instance).
_sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for (pname, kind), tmesh in TREE_MESHES.items():
    holder = tag(actors.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0)), f"GB_Foret_{pname}_{kind}")
    root = _sds.k2_gather_subobject_data_for_instance(holder)[0]
    _sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.HierarchicalInstancedStaticMeshComponent))
    hism = holder.get_component_by_class(unreal.HierarchicalInstancedStaticMeshComponent)
    hism.set_static_mesh(tmesh)
    hism.set_material(0, MATS[TREE_KIND_MATS[kind]])
    hism.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    hism.set_editor_property("cast_shadow", False)
    hism.set_editor_property("instance_end_cull_distance", 18000)    # au-delà de 180 m : brume et lisière
    xf = [unreal.Transform(ue(x, y, z), unreal.Rotator(0, 0, -yaw), unreal.Vector(sxy, sxy, sz))
          for x, y, z, yaw, sxy, sz in VEG["instances"][pname]]
    hism.add_instances(xf, False, True)

# --- Sprites peints (retour d'Olivier du 18/10 : les arbres peints tournés vers l'œil « rendent vachement bien ») ----
# Images peintes générées en local (pipeline/comfy/sprites.py), posées par pipeline/layout/sprites_layout.py. Un plan de
# 2 triangles par sujet, une famille = un atlas = un maillage instancié (HISM). Données d'instance : 0 = case de l'atlas,
# 1 = teinte (-1 plus froid, +1 plus chaud), 2 = éclat. Retour d'Olivier du 19/10 : les plans tournés vers l'œil à chaque image « c'est trop
# bizarre » (des arbres se rentrent dedans selon l'orientation de la tête). Tous les plans sont immobiles : orientation
# et échelle sont dans la transformée de l'instance, calculées par sprites_layout.py (vers le passage de la barque).
SPRITE_LAYOUT = os.path.join(ROOT, "pipeline", "layout", "sprites.json")
SPRITE_DIR = os.path.join(ROOT, "assets", "textures", "sprites")
SPRITE_UV_CODE = """float c = round(C);
return float2((fmod(c, Cols) + UV.x) / Cols, (floor(c / Cols) + UV.y) / Rows);"""
# Éclat > 1,5 : sujet lumineux (famille « nuit ») ; ses parties claires et vives (chapeaux, fleurs, points) s'allument la
# nuit. Les feuilles restent éteintes : allumées aussi, les plantes entières viraient au blanc (retour du 19/10).
SPRITE_COLOR_CODE = """float3 c = Tex.rgb * (lerp(Ombre.rgb, Lumiere.rgb, 0.75) + Ciel.rgb * 0.35) * min(Bright, 1.3);
float glow = max(Bright - 1.5, 0.0) * (1.0 - saturate(Day));
float lum = dot(Tex.rgb, float3(0.3, 0.6, 0.1));
float mx = max(Tex.r, max(Tex.g, Tex.b));
float m = smoothstep(0.6, 0.88, mx) * smoothstep(0.4, 0.65, lum);
return c + lerp(Tex.rgb, float3(0.6, 0.9, 1.0) * mx, 0.3) * m * glow * 2.2;"""
# Plan immobile vu presque par la tranche : il s'efface au lieu de devenir un aplat (mipmap grossière, bords droits).
# Pas pour les plans posés sur l'eau (Tranche = 0) : vus depuis la barque, ils sont toujours rasants.
# Relief des sujets proches : la grille avance vers l'œil (D = -Y local, à l'échelle de l'instance) selon la carte de
# relief de la case (pipeline/comfy/relief.py), lue dans le shader de sommets.
SPRITE_RELIEF_CODE = """return D * (Texture2DSampleLevel(R, RSampler, UV, 0).r * A);"""
# Vent : balancement lent, pied fixe, amplitude croissante vers la cime (~1,2 % de la hauteur), phase selon le lieu.
# Le plan ne tourne pas avec la tête (retour d'Olivier du 19/10) : il oscille autour de sa position fixe.
SPRITE_WIND_CODE = """float hs = length(U);                                  // hauteur du sujet (cm) : échelle de l'instance
float z = saturate(LP.z / 100.0 + 0.5 * C);                 // pied (0) à cime (1) (plan de 100 unités ; touffes centrées)
float s = sin(T * 0.8 + dot(WP.xy, float2(0.0011, 0.0017))) + 0.35 * sin(T * 2.1 + dot(WP.xy, float2(0.003, -0.002)));
return float3(0.8, 0.6, 0.0) * s * 0.012 * hs * z * z * E;"""
SPRITE_TINT_CODE = """return Tex * (1.0 + Tint * float3(0.08, 0.015, -0.1));"""
SPRITE_EDGE_CODE = """return A * lerp(1.0, smoothstep(0.12, 0.3, abs(dot(normalize(N), normalize(V)))), E);"""


def sprite_material(relief=False):
    """Matériau des sprites ; relief=True : variante dont la grille se creuse selon la carte de relief (sujets proches)."""
    name = "M_GB_SpriteRelief" if relief else "M_GB_Sprite"
    path = f"{GB}/{name}"
    digest = spec_digest("sprite-v7", SPRITE_UV_CODE, SPRITE_COLOR_CODE, SPRITE_EDGE_CODE, SPRITE_TINT_CODE, MPC_DIGEST,
                         SPRITE_RELIEF_CODE if relief else "", SPRITE_WIND_CODE)
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(mat, digest):
        return mat
    mat = mat or tools.create_asset(name, GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.5)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("used_with_instanced_static_meshes", True)

    def scalar(name, default, x, y):
        sp = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
        sp.set_editor_property("parameter_name", name)
        sp.set_editor_property("default_value", default)
        return sp

    def custom_data(i, y):
        cd = mel.create_material_expression(mat, unreal.MaterialExpressionPerInstanceCustomData, -1600, y)
        cd.set_editor_property("data_index", i)
        return cd

    cell, tint, bright = custom_data(0, 0), custom_data(1, 100), custom_data(2, 200)
    cols, rows = scalar("Cols", 4.0, -1600, 400), scalar("Rows", 2.0, -1600, 500)
    uv0 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1600, -300)
    uvn = custom_node(mat, SPRITE_UV_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT2, ["C", "UV", "Cols", "Rows"], -1100, -300)
    for pin, src in (("C", cell), ("UV", uv0), ("Cols", cols), ("Rows", rows)):
        mel.connect_material_expressions(src, "", uvn, pin)
    uvi = mel.create_material_expression(mat, unreal.MaterialExpressionVertexInterpolator, -900, -300)   # calcul par sommet
    mel.connect_material_expressions(uvn, "", uvi, "VS")
    # vent (tous les sprites ; Vent = 0 pour les plans fixes : lisières, eau)
    ucon = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1500, 1300)
    ucon.set_editor_property("constant", unreal.LinearColor(0, 0, 1, 0))
    utr = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -1300, 1300)
    utr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
    utr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    mel.connect_material_expressions(ucon, "", utr, "")
    wwp = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1300, 1400)
    wwp.set_editor_property("world_position_shader_offset", unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    wind = custom_node(mat, SPRITE_WIND_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["U", "LP", "T", "WP", "E", "C"], -1000, 1300)
    for pin, src in (("U", utr), ("LP", mel.create_material_expression(mat, unreal.MaterialExpressionLocalPosition, -1300, 1500)),
                     ("T", mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1300, 1600)), ("WP", wwp),
                     ("E", scalar("Vent", 1.0, -1300, 1700)), ("C", scalar("Centre", 0.0, -1300, 1800))):
        mel.connect_material_expressions(src, "", wind, pin)
    wpo_out = wind
    if relief:
        rtex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureObjectParameter, -1100, 700)
        rtex.set_editor_property("parameter_name", "Relief")
        rtex.set_editor_property("texture", relief_texture("arbres"))
        rtex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        dcon = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1300, 800)
        dcon.set_editor_property("constant", unreal.LinearColor(0, -1, 0, 0))
        dtr = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -1100, 800)
        dtr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
        dtr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(dcon, "", dtr, "")
        wpo = custom_node(mat, SPRITE_RELIEF_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["R", "UV", "D", "A"], -800, 700)
        for pin, src in (("R", rtex), ("UV", uvn), ("D", dtr), ("A", scalar("Creux", 0.16, -1100, 900))):
            mel.connect_material_expressions(src, "", wpo, pin)
        add_ = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -600, 900)
        mel.connect_material_expressions(wpo, "", add_, "A")
        mel.connect_material_expressions(wind, "", add_, "B")
        wpo_out = add_
    mel.connect_material_property(wpo_out, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, -300)
    tex.set_editor_property("parameter_name", "Atlas")
    tex.set_editor_property("texture", look_texture("sprite_arbres"))
    mel.connect_material_expressions(uvi, "", tex, "UVs")
    col = custom_node(mat, SPRITE_COLOR_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Tex", "Lumiere", "Ombre", "Ciel", "Bright", "Day"], -400, -300)
    tinted = custom_node(mat, SPRITE_TINT_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Tex", "Tint"], -550, -450)
    mel.connect_material_expressions(tex, "RGB", tinted, "Tex")
    mel.connect_material_expressions(tint, "", tinted, "Tint")
    mel.connect_material_expressions(tinted, "", col, "Tex")
    mel.connect_material_expressions(bright, "", col, "Bright")
    dayp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -700, 300)
    dayp.set_editor_property("collection", MPC)
    dayp.set_editor_property("parameter_name", "VieJour")
    mel.connect_material_expressions(dayp, "", col, "Day")
    for i, nm in enumerate(("Lumiere", "Ombre", "Ciel")):
        cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -700, -100 + 100 * i)
        cp.set_editor_property("collection", MPC)
        cp.set_editor_property("parameter_name", "CielAppoint" if nm == "Ciel" else nm)
        mel.connect_material_expressions(cp, "", col, nm)
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    edge = custom_node(mat, SPRITE_EDGE_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT1, ["A", "N", "V", "E"], -400, 0)
    mel.connect_material_expressions(scalar("Tranche", 1.0, -700, 300), "", edge, "E")
    mel.connect_material_expressions(tex, "A", edge, "A")
    mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -700, 100), "", edge, "N")
    mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -700, 200), "", edge, "V")
    mel.connect_material_property(edge, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError(f"{name} ne compile pas")
    mark_saved(mat, digest)
    return mat


def relief_texture(name):
    return look_texture(f"relief_{name}", srgb=False, compression=unreal.TextureCompressionSettings.TC_GRAYSCALE)


RELIEF_CREUX = {"buissons": 0.2, "fourres": 0.2, "heros": 0.1, "faune": 0.1}   # avancée max (hauteur de case = 1)


def sprite_set(key, mode, instances, cull_cm):
    """Une famille de sprites : atlas, instance de matériau, plan à la proportion d'une case, maillage instancié.
    « famille@mode » : même atlas posé dans un autre mode (ex. lianes debout, touffes de feuillage)."""
    name = key.split("@")[0]
    tag_ = key.replace("@", "_")
    with open(os.path.join(SPRITE_DIR, f"{name}.json"), encoding="utf-8") as f:
        meta = json.load(f)
    cols, rows = meta["grid"]
    aspect = meta["cell"][0] / meta["cell"][1]
    items = meta["items"]
    atlas = look_texture(f"sprite_{name}")
    if not atlas.get_editor_property("do_scale_mips_for_alpha_coverage"):   # pas d'amincissement au loin
        atlas.set_editor_property("do_scale_mips_for_alpha_coverage", True)
        atlas.set_editor_property("alpha_coverage_thresholds", unreal.Vector4(0, 0, 0, 0.5))
        eal.save_loaded_asset(atlas)
    mi_path = f"{GB}/MI_GB_Sprite_{tag_}"
    parent = MATS["SpriteRelief" if mode == "relief" else "Sprite"]
    rtex = relief_texture(name) if mode == "relief" else None
    params = (("Cols", float(cols)), ("Rows", float(rows)), ("Tranche", 0.0 if mode == "sol" else 1.0),
              ("Vent", 0.0 if mode in ("sol", "fixe") else 1.0), ("Centre", 1.0 if mode == "touffe" else 0.0),
              ("Creux", RELIEF_CREUX.get(name, 0.12) if mode == "relief" else 0.0))
    mi_digest = spec_digest("mi-sprite-v1", parent.get_path_name(), eal.get_metadata_tag(parent, "source_sha1"),
                            atlas.get_path_name(), eal.get_metadata_tag(atlas, "source_sha1"),
                            rtex.get_path_name() if rtex else "", eal.get_metadata_tag(rtex, "source_sha1") if rtex else "", params)
    mi = eal.load_asset(mi_path) if eal.does_asset_exist(mi_path) else None
    if not up_to_date(mi, mi_digest):    # réécrite seulement si elle change (sinon chaque build regonfle le dépôt LFS)
        mi = mi or tools.create_asset(f"MI_GB_Sprite_{tag_}", GB, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", parent)
        mel.set_material_instance_texture_parameter_value(mi, "Atlas", atlas)
        if rtex is not None:
            mel.set_material_instance_texture_parameter_value(mi, "Relief", rtex)
        for k, v in params:
            if k != "Creux" or mode == "relief":
                mel.set_material_instance_scalar_parameter_value(mi, k, v)
        mel.update_material_instance(mi)
        mark_saved(mi, mi_digest)
    hw = aspect / 2
    if mode == "sol":          # à plat, centré
        verts = [[-hw, -0.5, 0], [hw, -0.5, 0], [hw, 0.5, 0], [-hw, 0.5, 0]]
        nrm = [[0, 0, 1]] * 4
    elif mode == "touffe":     # vertical, centré
        verts = [[-hw, 0, -0.5], [hw, 0, -0.5], [hw, 0, 0.5], [-hw, 0, 0.5]]
        nrm = [[0, -1, 0]] * 4
    elif mode == "relief":     # vertical, pied au sol, grille creusée par le matériau (arbres 6 × 12, petits sujets 6 × 6)
        rows = 6 if name in ("buissons", "fourres", "faune") else 12
        nz = rows + 1
        nx = max(5, round(rows * aspect) + 1)
        verts = [[-hw + 2 * hw * i / (nx - 1), 0, j / (nz - 1)] for j in range(nz) for i in range(nx)]
        uvs = [[i / (nx - 1), 1 - j / (nz - 1)] for j in range(nz) for i in range(nx)]
        tris = []
        for j in range(nz - 1):
            for i in range(nx - 1):
                a_, b_ = j * nx + i, (j + 1) * nx + i
                tris += [[a_, a_ + 1, b_ + 1], [a_, b_ + 1, b_]]
        nrm = [[0, -1, 0]] * len(verts)
    else:                      # vertical, pied au sol
        verts = [[-hw, 0, 0], [hw, 0, 0], [hw, 0, 1], [-hw, 0, 1]]
        nrm = [[0, -1, 0]] * 4
    if mode != "relief":
        tris, uvs = [[0, 1, 2], [0, 2, 3]], [[0, 1], [1, 1], [1, 0], [0, 0]]
    quad = build_mesh(f"Sprite_{tag_}", {"vertices": verts, "triangles": tris, "normals": nrm, "uv": uvs,
                                         "color": [1, 1, 1, 1]})
    holder = tag(actors.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0)), f"GB_Sprites_{tag_}")
    root = _sds.k2_gather_subobject_data_for_instance(holder)[0]
    _sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.HierarchicalInstancedStaticMeshComponent))
    hism = holder.get_component_by_class(unreal.HierarchicalInstancedStaticMeshComponent)
    hism.set_static_mesh(quad)
    hism.set_material(0, mi)
    hism.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    hism.set_editor_property("cast_shadow", False)
    hism.set_editor_property("instance_end_cull_distance", cull_cm)
    hism.set_editor_property("num_custom_data_floats", 3)
    hism.set_editor_property("bounds_scale", 1.4 if mode == "relief" else 1.1)   # relief : la grille avance ; vent
    xf, data = [], []
    up = unreal.Vector(0, 0, 1)
    for x, y, z, h, cell, yaw, bright, pitch, mirror in instances:
        it = items[int(cell)]
        fh, fw = it["v1"] - it["v0"], (it["u1"] - it["u0"]) * aspect
        k = 1.0 / max(fh, 1e-3) if mode in ("debout", "fixe", "relief") else 1.0 / max(fh, fw, 1e-3)   # le sujet prend la hauteur h
        if mode == "sol":
            rot = unreal.Rotator(0, 0, -yaw)
        else:                      # la face du plan (-Y local) regarde dans la direction (cap, inclinaison) du tracé
            cy, sy_, cp, sp = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
            rot = unreal.MathLibrary.make_rot_from_yz(unreal.Vector(-cy * cp, sy_ * cp, -sp), up)
        # sujets debout : miroir choisi au placement (côté éclairé vers le soleil), teinte propre tirée de la position
        hsh = (math.sin(x * 12.9898 + y * 78.233) * 43758.5453) % 1.0
        flip = -1.0 if mirror > 0.5 else 1.0
        tint = ((hsh * 7.0) % 1.0) * 1.6 - 0.8 if mode in ("debout", "relief") else 0.0
        xf.append(unreal.Transform(ue(x, y, z), rot, unreal.Vector(h * k * flip, h * k, h * k)))
        data.append((cell, tint, bright))
    hism.add_instances(xf, False, True)
    for i, d in enumerate(data):
        for j, v in enumerate(d):
            hism.set_custom_data_value(i, j, float(v), False)
    return holder


# Vie animée : un seul maillage, un plan par animal ou feuille (sommets au centre de sa trajectoire), mouvement et
# battement d'ailes calculés dans le shader (rien sur le processeur), images de la famille « vie ».
VIE_WPO_CODE = """float type = round(P1.x);                         // P1 = (type, vitesse), P2 = (rayon en m, phase 0-1)
float spd = P1.y;
float rad = P2.x * 100.0;                            // rayon de trajectoire (cm)
float ph = P2.y * 6.2832;
float t = T * spd + ph;
float3 o = float3(0, 0, 0);
float3 v = float3(-sin(t), cos(t), 0);               // sens du déplacement (retourne l'image)
float size = 10.0;
float2 c = UV1.xy;                                   // coin du plan (-1..1 ; colonne centrale en 0 pour les ailes)
float day = saturate(Day);
if (type < 0.5)                                      // héron : grand cercle lent, battements amples
{
    o = float3(cos(t) * rad, sin(t) * rad, 250.0 * sin(t * 0.7));
    size = 190.0 * day;
    c.y += sin(T * 2.4 + ph * 5.0) * 0.55 * abs(c.x);
}
else if (type < 1.5)                                 // hirondelle : boucles rapides au ras de l'eau
{
    o = float3(cos(t) * rad, sin(t * 1.3) * rad * 0.6, 70.0 * sin(t * 2.1));
    v = float3(-sin(t), 1.3 * 0.6 * cos(t * 1.3), 0);
    size = 38.0 * day;
    c.y += sin(T * 16.0 + ph * 7.0) * 0.5 * abs(c.x);
}
else if (type < 2.5)                                 // papillon : vol erratique, ailes qui se referment
{
    o = float3(sin(t) * rad + 30.0 * sin(t * 3.7), cos(t * 0.8) * rad, 35.0 * sin(t * 2.3));
    v = float3(cos(t), -0.8 * sin(t * 0.8), 0);
    size = 13.0 * day;
    c.x *= 0.2 + 0.8 * abs(sin(T * 13.0 + ph * 9.0));
}
else if (type < 3.5)                                 // libellule : file, ralentit presque à l'arrêt, repart
{
    // à-coups sans marche arrière (retour d'Olivier du 19/10 : avec 0,6, la vitesse s'inversait) : dérivée 1 + 0,9 cos > 0
    float tt = t + 0.3 * sin(t * 3.0);
    o = float3(cos(tt) * rad, sin(tt) * rad, 15.0 * sin(t * 7.0));
    v = float3(-sin(tt), cos(tt), 0);
    size = 14.0 * day;
}
else if (type > 6.5)                                 // canard : nage en petit cercle, dodeline (reste la nuit)
{
    o = float3(cos(t) * rad, sin(t) * rad, 1.5 * sin(T * 1.9 + ph * 5.0));
    v = float3(-sin(t), cos(t), 0) * sign(spd);
    size = 52.0;
    o.z += size * 0.32;                              // ligne de flottaison sous le milieu de l'image
    c.y += 0.04 * sin(T * 1.3 + ph * 3.0) * c.x;
}
else                                                 // feuilles, pétales : tombent en se balançant, en boucle
{
    float f = frac(T * spd * 0.08 + P2.y * 7.0);
    o = float3(70.0 * sin(t * 1.7 + f * 9.0), 70.0 * cos(t * 1.3 + f * 7.0), -f * 900.0);
    size = 11.0 * saturate(min(f * 12.0, (1.0 - f) * 12.0));
    c = float2(c.x * cos(t * 3.0) - c.y * sin(t * 3.0), c.x * sin(t * 3.0) + c.y * cos(t * 3.0));
    v = float3(1, 0, 0);
}
float flip = dot(v, VR.xyz) < 0.0 ? -1.0 : 1.0;      // les images regardent vers la droite
return o + (VR.xyz * c.x * flip + VU.xyz * c.y) * size * 0.5;"""
VIE_UV_CODE = """float type = round(P1.x);
float cells[8] = {0, 1, 2, 3, 4, 5, 7, 6};
float cell = cells[(int)min(type, 7.0)];
return float2((fmod(cell, 4.0) + UV.x) / 4.0, (floor(cell / 4.0) + UV.y) / 2.0);"""


def vie_material():
    path = f"{GB}/M_GB_Vie"
    atlas = look_texture("sprite_vie")
    digest = spec_digest("vie-v7", VIE_WPO_CODE, VIE_UV_CODE, SPRITE_COLOR_CODE, MPC_DIGEST, eal.get_metadata_tag(atlas, "source_sha1"))
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(mat, digest):
        return mat
    mat = mat or tools.create_asset("M_GB_Vie", GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.5)
    mat.set_editor_property("two_sided", True)
    t = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1600, 100)
    uv1 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1600, 200)
    uv1.set_editor_property("coordinate_index", 1)
    day = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1600, 300)
    day.set_editor_property("collection", MPC)
    day.set_editor_property("parameter_name", "VieJour")
    vecs = []
    for i, vec in enumerate(((1, 0, 0), (0, 1, 0))):
        c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1600, 400 + 100 * i)
        c.set_editor_property("constant", unreal.LinearColor(*vec, 0))
        tr = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -1400, 400 + 100 * i)
        tr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_VIEW)
        tr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(c, "", tr, "")
        vecs.append(tr)
    p1 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1600, -100)
    p1.set_editor_property("coordinate_index", 2)
    p2 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1600, -200)
    p2.set_editor_property("coordinate_index", 3)
    wpo = custom_node(mat, VIE_WPO_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["P1", "P2", "T", "UV1", "Day", "VR", "VU"], -900, 200)
    for pin, src in (("P1", p1), ("P2", p2), ("T", t), ("UV1", uv1), ("Day", day), ("VR", vecs[0]), ("VU", vecs[1])):
        mel.connect_material_expressions(src, "", wpo, pin)
    mel.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    uv0 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1600, -300)
    uvn = custom_node(mat, VIE_UV_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT2, ["P1", "UV"], -1100, -300)
    mel.connect_material_expressions(p1, "", uvn, "P1")
    mel.connect_material_expressions(uv0, "", uvn, "UV")
    uvi = mel.create_material_expression(mat, unreal.MaterialExpressionVertexInterpolator, -900, -300)
    mel.connect_material_expressions(uvn, "", uvi, "VS")
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -700, -300)
    tex.set_editor_property("texture", atlas)
    mel.connect_material_expressions(uvi, "", tex, "UVs")
    one = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -700, -100)
    one.set_editor_property("r", 1.0)
    col = custom_node(mat, SPRITE_COLOR_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Tex", "Lumiere", "Ombre", "Ciel", "Bright", "Day"], -400, -300)
    mel.connect_material_expressions(tex, "RGB", col, "Tex")
    mel.connect_material_expressions(one, "", col, "Bright")
    mel.connect_material_expressions(day, "", col, "Day")
    for i, nm in enumerate(("Lumiere", "Ombre", "Ciel")):
        cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -700, 0 + 100 * i)
        cp.set_editor_property("collection", MPC)
        cp.set_editor_property("parameter_name", "CielAppoint" if nm == "Ciel" else nm)
        mel.connect_material_expressions(cp, "", col, nm)
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(tex, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError("M_GB_Vie ne compile pas")
    mark_saved(mat, digest)
    return mat


def vie_mesh(items):
    """Un plan par animal : 6 sommets (colonne centrale pour le battement d'ailes), tous au centre de la trajectoire
    (écartés de 5 mm : un triangle d'aire nulle serait supprimé), paramètres dans les canaux UV 2 et 3."""
    verts, tris, uv, uv1, uv2, uv3 = [], [], [], [], [], []
    for x, y, z, typ, spd, rad, ph in items:
        base = len(verts)
        for cx in (-1, 0, 1):
            for cy in (-1, 1):
                verts.append([x + cx * 0.005, y + cy * 0.005, z + cy * 0.005])
                uv.append([(cx + 1) / 2, (1 - cy) / 2])
                uv1.append([cx, cy])
                uv2.append([typ, spd])
                uv3.append([rad, ph])
        for a, b_ in ((0, 2), (2, 4)):        # deux colonnes de deux triangles
            tris += [[base + a, base + b_, base + b_ + 1], [base + a, base + b_ + 1, base + a + 1]]
    return build_mesh("VieAnimee", {"vertices": verts, "triangles": tris, "normals": [[0, 0, 1]] * len(verts),
                                    "uv": uv, "uv1": uv1, "uv2": uv2, "uv3": uv3, "color": [1, 1, 1, 1]})


SPRITE_CULL = {"arbres": 18000, "arbres2": 18000, "arbres3": 18000, "arbres4": 18000, "buissons": 7000, "fourres": 8000, "lisieres": 0, "feuillages": 0, "eau": 6000, "faune": 6000, "nuit": 6000, "heros": 0}
if os.path.exists(SPRITE_LAYOUT):
    MATS["Sprite"] = sprite_material()
    MATS["SpriteRelief"] = sprite_material(relief=True)
    with open(SPRITE_LAYOUT, encoding="utf-8") as f:
        for _name, _spec in json.load(f)["sets"].items():
            sprite_set(_name, _spec["mode"], _spec["instances"], SPRITE_CULL.get(_name.split("@")[0], 10000))
        f.seek(0)
        _layout = json.load(f)
        _vie = _layout.get("vie_animee", [])
    # points d'émission des sons de faune (canards, grenouilles, chouettes) : le paysage sonore y attache ses sons
    for _sname, _spos in _layout.get("sons", {}).items():
        tag(actors.spawn_actor_from_class(unreal.TargetPoint, ue(*_spos)), f"GB_Son_{_sname}")
    if _vie and os.path.exists(os.path.join(ROOT, "assets", "textures", "sprite_vie.png")):
        MATS["Vie"] = vie_material()
        _va = place_mesh(vie_mesh(_vie), "GB_VieAnimee", "Vie")
        _va.static_mesh_component.set_editor_property("bounds_scale", 4.0)   # trajectoires jusqu'à 40 m autour des sommets

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


# Ponton et arche des racines : modèles 3D (images d'Olivier refs/ponton.png, refs/racine.png → TRELLIS.2),
# placés plus bas, après l'import des modèles (place_props).

# Barque : racine invisible (animée par la séquence, porte la caméra) + modèle 3D attaché (assets/3d/barque/
# trellis2-s42, image refs/barque.png ; mesures et échelles avec BOAT_SCALE plus haut). Bloc en repli s'il manque.
BOAT_GLB = os.path.join(ROOT, "assets", "3d", "barque", "trellis2-s42", "model.glb")
BOAT_DIR, BOAT_MESH = "/Game/Assets/Barque", "/Game/Assets/Barque/model/StaticMeshes/model"
BOAT_Z = -BOAT_BOTTOM * BOAT_SCALE_Z - BOAT_DRAFT


def import_glb(rel_glb, dest_dir, max_tris=None, smooth=False):
    """Importe assets/3d/<rel_glb>/model.glb dans dest_dir (une fois par empreinte du fichier et par budget de
    triangles) ; None si absent. max_tris : simplification à l'import (budget Quest : ≤ 500 k triangles visibles)."""
    import hashlib
    glb = os.path.join(ROOT, "assets", "3d", rel_glb, "model.glb")
    if not os.path.exists(glb):
        return None
    mesh_path = f"{dest_dir}/model/StaticMeshes/model"
    with open(glb, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12] + (f"-{max_tris}" if max_tris else "") + ("-lisse" if smooth else "")
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
        if smooth:                 # normales lissées par sommet : sculptures (le visage disparaissait dans les facettes)
            unreal.GeometryScript_Normals.set_per_vertex_normals(dm)
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, mesh, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD())
        unreal.log(f"{rel_glb} : simplifié à {mesh.get_num_triangles(0)} triangles")
    eal.set_metadata_tag(mesh, "source_sha1", digest)
    eal.save_loaded_asset(mesh)
    return mesh


def hull_floor(model):
    """Plancher à la forme exacte de la coque à la ligne de flottaison : sommets du maillage de la barque entre
    -10 et +15 cm autour de l'eau, ramenés dans le repère de la barque, enveloppe convexe réduite de 4 %, posée
    à +3 cm. Opaque, il cache l'eau à l'intérieur de la coque (retour d'Olivier : l'eau passait sous le plancher
    elliptique, trop petit)."""
    dm = unreal.DynamicMesh()
    unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(model, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    vl = unreal.GeometryScript_MeshQueries.get_all_vertex_positions(dm, True)
    vl = next(x for x in (vl if isinstance(vl, tuple) else (vl,)) if type(x).__name__ == "GeometryScriptVectorList")
    pts = []
    for v in unreal.GeometryScript_List.convert_vector_list_to_array(vl):
        x, y, z = v.x * BOAT_SCALE, v.y * BOAT_SCALE_Y, v.z * BOAT_SCALE_Z + BOAT_Z
        ca, sa = math.cos(math.radians(BOAT_YAW)), math.sin(math.radians(BOAT_YAW))
        bx, by = x * ca - y * sa, x * sa + y * ca        # rotation du modèle (relative_rotation)
        if -10.0 <= z <= 15.0:
            pts.append((round(bx, 1), round(by, 1)))
    pts = sorted(set(pts))
    if len(pts) < 3:
        return FLOOR_MESH

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p_ in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p_) <= 0:
            lower.pop()
        lower.append(p_)
    for p_ in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p_) <= 0:
            upper.pop()
        upper.append(p_)
    hull = lower[:-1] + upper[:-1]
    cx, cy = sum(p_[0] for p_ in hull) / len(hull), sum(p_[1] for p_ in hull) / len(hull)
    ring = [[(cx + (x - cx) * 0.96) / 100.0, -(cy + (y - cy) * 0.96) / 100.0, 0.03] for x, y in hull]
    verts = [[cx / 100.0, -cy / 100.0, 0.03]] + ring
    n = len(ring)
    data = {"vertices": verts, "triangles": [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)],
            "normals": [[0, 0, 1]] * len(verts), "color": [0.46, 0.33, 0.21, 0.95]}
    unreal.log(f"Plancher de la coque : {n} points, {max(p_[0] for p_ in hull) - min(p_[0] for p_ in hull):.0f} × "
               f"{max(p_[1] for p_ in hull) - min(p_[1] for p_ in hull):.0f} cm")
    return build_mesh("PlancherCoque", data)


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
    hull.root_component.set_editor_property("relative_scale3d", unreal.Vector(BOAT_SCALE, BOAT_SCALE_Y, BOAT_SCALE_Z))
    # Lanterne : modèle à part (papier à nervures), centré sur LANTERN, papier allumé par la bougie (matériau
    # « bougie », qui la fait aussi tanguer) ; lumière et halo au centre. Repli : cylindre lumineux.
    LANTERN = unreal.Vector(*LANTERN_LOCAL)
    lantern_model = import_glb("lanterne/trellis2-s42", "/Game/Assets/Lanterne", 6000)
    if lantern_model is not None:
        lb = lantern_model.get_bounding_box()
        ls_ = LANTERN_H / max(lb.max.z - lb.min.z, 1e-3)
        paper = actors.spawn_actor_from_object(lantern_model, boat.get_actor_location())
        tag(paper, "Lanterne")
        paper.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        lc_ = unreal.Vector(LANTERN.x, LANTERN.y, LANTERN.z - (lb.min.z + lb.max.z) / 2 * ls_)
        scale_ = unreal.Vector(ls_, ls_, ls_)
    else:
        paper = place_mesh(CYL, "LanternePapier", "LanternePapier", boat.get_actor_location())
        lc_, scale_ = LANTERN, unreal.Vector(0.22, 0.22, LANTERN_H / 100.0)
    paper.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    paper.root_component.set_editor_property("relative_location", lc_)
    paper.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
    paper.root_component.set_editor_property("relative_scale3d", scale_)
    paper.static_mesh_component.set_editor_property("cast_shadow", False)
    # Plancher de la barque : planches opaques juste au-dessus de la ligne de flottaison, dans la coque ; l'eau
    # ne se voit plus à l'intérieur même si le masque du shader de l'eau échoue (retour d'Olivier).
    fl = place_mesh(hull_floor(model), "PlancherBarque", "PeintPlanches", boat.get_actor_location())
    fl.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    fl.root_component.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    fl.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
    halo = place_mesh(SPHERE, "HaloLanterne", "HaloLanterne", boat.get_actor_location())
    halo.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    halo.root_component.set_editor_property("relative_location", LANTERN)
    halo.root_component.set_editor_property("relative_scale3d", unreal.Vector(0.7, 0.7, 0.7))
    halo.static_mesh_component.set_editor_property("cast_shadow", False)
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
# la pose de la tête (origine LocalFloor, au sol sous le joueur, voir BP_Recentrage) remplace cette position.
vr_cam.set_editor_property("relative_location", unreal.Vector(0, 0, EYE_CM))
vr.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)


def fade_material():
    """Fondu au noir sans post-traitement (impossible sur Quest sans HDR mobile) : sphère noire translucide autour
    des yeux, dessinée par-dessus tout (sans test de profondeur), opacité = MPC Fondu (animée par la séquence)."""
    path = f"{GB}/M_GB_Fondu"
    digest = spec_digest("fondu-v1", MPC_DIGEST)
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(mat, digest):
        return mat
    mat = mat or tools.create_asset("M_GB_Fondu", GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("disable_depth_test", True)
    black = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    black.set_editor_property("constant", unreal.LinearColor(0, 0, 0, 1))
    mel.connect_material_property(black, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -400, 200)
    op.set_editor_property("collection", MPC)
    op.set_editor_property("parameter_name", "Fondu")
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError("M_GB_Fondu ne compile pas")
    mark_saved(mat, digest)
    return mat


MATS["Fondu"] = fade_material()
fondu = place_mesh(SPHERE, "GB_Fondu", "Fondu", vr_cam.get_world_location(), scale=(0.4, 0.4, 0.4))   # 20 cm de rayon
fondu.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)   # sinon elle ne suit pas la caméra
fondu.static_mesh_component.set_editor_property("translucency_sort_priority", 100)
fondu.static_mesh_component.set_editor_property("cast_shadow", False)
fondu.attach_to_component(vr_cam, "", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                          unreal.AttachmentRule.KEEP_RELATIVE, False)

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
# (la lune elle-même est peinte dans le ciel : SKY_STARS_CODE)

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
    SKY_WATER_VERSION = "ciel-eau-v17"   # à incrémenter si le code des matériaux du ciel ou de l'eau change
    sky_mat_path = f"{GB}/M_GB_CielPeint"
    sky_mat = eal.load_asset(sky_mat_path) if eal.does_asset_exist(sky_mat_path) else None
    rebuild_sky_water = not up_to_date(sky_mat, spec_digest(SKY_WATER_VERSION, sky_digest, MPC_DIGEST, WATER_CODE,
                                                            eal.get_metadata_tag(WATER_MAP_TEX, "source_sha1"),
                                                            eal.get_metadata_tag(RIDES_TEX, "source_sha1"), eal.get_metadata_tag(GLOW_TEX, "source_sha1"), eal.get_metadata_tag(EAU_TEX, "source_sha1")))
    sky_mat = sky_mat or tools.create_asset("M_GB_CielPeint", GB, unreal.Material, unreal.MaterialFactoryNew())
if os.path.exists(SKY_PNG) and rebuild_sky_water:
    mel.delete_all_material_expressions(sky_mat)
    sky_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    sky_mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
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
    mark_saved(sky_mat, spec_digest(SKY_WATER_VERSION, sky_digest, MPC_DIGEST, WATER_CODE,
                                    eal.get_metadata_tag(WATER_MAP_TEX, "source_sha1"),
                                    eal.get_metadata_tag(RIDES_TEX, "source_sha1"), eal.get_metadata_tag(GLOW_TEX, "source_sha1"), eal.get_metadata_tag(EAU_TEX, "source_sha1")))
    # Eau peinte (voir WATER_CODE) : rides qui suivent le courant, reflet du ciel déformé, reflets de crêtes,
    # bande sombre du reflet des arbres près des berges, écume le long des rives, fond profond ; translucide
    # pour voir la créature des abysses. Sans réflexions temps réel (coût Quest faible).
    water = eal.load_asset(f"{GB}/M_GB_Eau")
    mel.delete_all_material_expressions(water)
    water.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    water.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
    water.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    water.set_editor_property("two_sided", True)
    wcam = mel.create_material_expression(water, unreal.MaterialExpressionCameraVectorWS, -1000, 0)
    wpos = mel.create_material_expression(water, unreal.MaterialExpressionWorldPosition, -1000, 100)
    wt = mel.create_material_expression(water, unreal.MaterialExpressionTime, -1000, 200)
    wnode = custom_node(water, WATER_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                        ["Dir", "WP", "T", "Map", "Rides", "Sky", "Teinte", "Lumiere", "B", "Ab", "Af", "Glow", "Day", "Lf", "Ff", "EauTex"], -600, 0)
    mel.connect_material_expressions(wcam, "", wnode, "Dir")
    mel.connect_material_expressions(wpos, "", wnode, "WP")
    mel.connect_material_expressions(wt, "", wnode, "T")
    for i, (pin, tex) in enumerate((("Map", WATER_MAP_TEX), ("Rides", RIDES_TEX), ("Sky", sky_tex), ("Glow", GLOW_TEX), ("EauTex", EAU_TEX))):
        to = mel.create_material_expression(water, unreal.MaterialExpressionTextureObject, -1000, 300 + 100 * i)
        to.set_editor_property("texture", tex)
        mel.connect_material_expressions(to, "", wnode, pin)
    mel.connect_material_expressions(mpc_rgb(water, "CielTeinte", -1000, 650), "", wnode, "Teinte")
    mel.connect_material_expressions(mpc_rgb(water, "Lumiere", -1000, 750), "", wnode, "Lumiere")
    wb = mel.create_material_expression(water, unreal.MaterialExpressionCollectionParameter, -1000, 850)
    wb.set_editor_property("collection", MPC)
    wb.set_editor_property("parameter_name", "Barque")
    mel.connect_material_expressions(wb, "", wnode, "B")
    for i, (pin, pname) in enumerate((("Ab", "AbyssPos"), ("Af", "AbyssFade"), ("Day", "VieJour"), ("Lf", "LucioleFade"),
                                      ("Ff", "FinaleFade"))):
        cpw = mel.create_material_expression(water, unreal.MaterialExpressionCollectionParameter, -1000, 950 + 100 * i)
        cpw.set_editor_property("collection", MPC)
        cpw.set_editor_property("parameter_name", pname)
        mel.connect_material_expressions(cpw, "", wnode, pin)
    rgb = mel.create_material_expression(water, unreal.MaterialExpressionComponentMask, -300, 0)
    for c in ("r", "g", "b"):
        rgb.set_editor_property(c, True)
    alpha = mel.create_material_expression(water, unreal.MaterialExpressionComponentMask, -300, 150)
    alpha.set_editor_property("a", True)
    mel.connect_material_expressions(wnode, "", rgb, "")
    mel.connect_material_expressions(wnode, "", alpha, "")
    mel.connect_material_property(rgb, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(alpha, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(water)
    if mel.get_statistics(water).num_pixel_shader_instructions <= 0 or mel.get_statistics(sky_mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError("Matériau du ciel ou de l'eau : échec de compilation")
    eal.save_loaded_asset(water)
if os.path.exists(SKY_PNG):
    MATS["CielPeint"] = sky_mat
    sky_sphere = place_mesh(SPHERE, "GB_CielPeint", "CielPeint", unreal.Vector(10000, 0, 0), scale=(10000, 10000, 10000))
    sky_sphere.static_mesh_component.set_editor_property("cast_shadow", False)

# Lanternes de l'arbre de S7 retirées (retour d'Olivier : trop loin, on ne voyait pas leur forme) : remplacées
# par la nuée de lucioles du lac (LuciolesLac, greybox_geometry.py), qui monte autour de la barque et dans l'arbre.

# Créatures : bloc animé par la séquence (repère : +X = sens du mouvement) + modèle 3D attaché s'il existe.
# Modèles TRELLIS.2 : longueur sur +Y à l'import (1 unité = 100 cm), comme la barque → rotation -90°.
# Échelles D4 : abysses 15 m de long (épaisseur ramenée à 2,5 m), troupeau 2,5 m au garrot, volante 40 m d'envergure.
CREATURES = {
    # bloc : (modèle, matériau du bloc, échelle du bloc de repli, échelle du modèle (x, y, z), décalage z cm, triangles max)
    "GB_Abysses": ("abysses/trellis2-s42", "Creature", (15, 7, 1.2), (15, 15, 4.5), 0.0, 20000),
    # eau au poitrail (séquencier) : à -60 cm, seuls les dos moussus sortaient de l'eau, lus comme des rochers (19/10)
    "GB_Troupeau": ("troupeau/trellis2-s42", "Troupeau", (3.0, 2.2, 2.5), (4.1, 4.1, 4.1), 0.0, 12000),   # pieds au sol sur la berge
    "GB_Volante": ("fly/trellis2-s42", "Volante", (40, 12, 4), (56, 56, 56), 0.0, 20000),
}


GLOW = {"GB_Abysses": (0.15, 1.6, 2.0)}   # bioluminescence : texture de couleur réutilisée en émissif, teintée


# Animations sans squelette, en WPO dans le repère local du modèle (longueur sur +Y à l'import, travers X,
# haut Z ; boîte englobante du modèle en constantes). Ph : phase propre à chaque acteur (donnée primitive 0).
ANIM_CODES = {
    # battement d'ailes : bouts d'ailes (loin de l'axe du corps) qui montent et descendent
    "vol": """float hs = max(BXX - BXN, BYX - BYN) * 0.5;
float n = saturate(abs((BXX - BXN) >= (BYX - BYN) ? LP.x - (BXX + BXN) * 0.5 : LP.y - (BYX + BYN) * 0.5) / hs);
return float3(0, 0, hs * 0.22 * n * n * sin(T * 1.8 + Ph));""",
    # marche : pattes en paires diagonales qui avancent et se lèvent, corps qui ondule légèrement
    "marche": """float h = BZX - BZN;
float legs = saturate((BZN + h * 0.45 - LP.z) / (h * 0.45));
float side = LP.x > (BXX + BXN) * 0.5 ? 1.0 : -1.0;
float fore = LP.y > (BYX + BYN) * 0.5 ? 1.0 : -1.0;
float ph = T * 4.6 + Ph + (side * fore > 0.0 ? 0.0 : 3.1416);
float stride = sin(ph) * h * 0.13 * legs;
float lift = max(0.0, cos(ph)) * h * 0.06 * legs;
float bob = sin((T * 4.6 + Ph) * 2.0) * h * 0.015;
return float3(0, stride, lift + bob);""",
    # nage : onde qui parcourt le corps, ailes larges qui ondulent (raie géante), lente
    "nage": """float L = BYX - BYN, W = BXX - BXN;
float a = (LP.y - BYN) / L;
float lat = saturate(abs(LP.x - (BXX + BXN) * 0.5) / (W * 0.5));
float wave = sin(a * 7.5 - T * 1.7 + Ph);
return float3(wave * W * 0.04 * (1.0 - a), 0, wave * W * 0.09 * lat + sin(T * 0.8 + Ph) * W * 0.012);""",
}


# Mousse sur les statues de pierre (D18, modèles 3D sans végétation) : les faces tournées vers le haut verdissent,
# en taches irrégulières ; la teinte suit l'ombrage déjà calculé (C).
# Roche d'Olivier (refs/tex-roche.png) en détail fin sur les statues (côtés et dos, là où la projection ne porte pas) :
# projection selon l'axe dominant de la normale, 3 m, module la couleur autour de sa moyenne.
ROCK_DETAIL_CODE = """float3 an = abs(normalize(N));
float2 uv = an.z > max(an.x, an.y) ? WP.xy : (an.x > an.y ? WP.yz : WP.xz);
float3 d = Texture2DSample(Tex, TexSampler, uv / 300.0).rgb;
return C * lerp(1.0, dot(d, float3(0.3, 0.6, 0.1)) / MEAN, 0.6);"""
MOSS_CODE = """// contraste rendu à la pierre (les fissures et les blocs peints de la texture se perdaient dans l'ombrage peint)
float l0 = dot(C, float3(0.3, 0.6, 0.1));
C = max(lerp(float3(l0, l0, l0), C, 1.15) * pow(saturate(l0 * 2.2), 0.35) / max(pow(saturate(l0 * 2.2), 0.35), 1e-3) * 1.0, 0.0);
C = C * (0.55 + 0.9 * smoothstep(0.02, 0.5, l0));
float n = 0.5 + 0.25 * sin(WP.x * 0.011 + sin(WP.y * 0.017) * 2.0) + 0.25 * sin(WP.y * 0.023 - WP.x * 0.007 + WP.z * 0.013);
float m = smoothstep(0.25, 0.7, normalize(N).z) * smoothstep(0.35, 0.65, n);
float l = dot(C, float3(0.3, 0.6, 0.1));
return lerp(C, l * float3(0.62, 1.05, 0.42) * 1.15, m * 0.85);"""
# Image d'Olivier projetée sur la face avant de sa statue (pipeline/style/projection.py) : la 3D d'une seule vue perd
# le détail peint (blocs, fissures, visages) ; la barque voit le pont sous le même angle que l'image. Projection le
# long de l'axe Y du modèle (son épaisseur), cadre de la silhouette calé sur la boîte du modèle ; faces de côté : la
# texture reconstruite. Éclairée par la lumière du moment (l'image a déjà son modelé).
PROJ_CODE = """float u = lerp(PU0, PU1, saturate((LP.x - BXN) / (BXX - BXN)));
if (PFLIP > 0.5) u = PU0 + PU1 - u;
float v = lerp(PV1, PV0, saturate((LP.z - BZN) / (BZX - BZN)));
float3 P = pow(max(Texture2DSample(Tex, TexSampler, float2(u, v)).rgb, 0.0), 1.0);
float w = smoothstep(0.25, 0.65, abs(normalize(NL).y));
float3 lit = P * (lerp(Ombre.rgb, Lumiere.rgb, 0.7) * 1.1 + Ciel.rgb * 0.3);
return lerp(C, lit, w * PSTR);"""
LAMP_CODE = (f"float lum = dot(Tex, float3(0.3, 0.6, 0.1));\n"
             f"return C * 0.4 + Tex * float3({CANDLE_RGB[0]}, {CANDLE_RGB[1]}, {CANDLE_RGB[2]}) * smoothstep(0.25, 0.6, lum) * 2.6 * {FLICKER};")


def peint_tex_material(name, texture, anim=None, box=None, glow=None, tint=None, moss=False, proj=None):
    """Look peint pour un modèle texturé (créatures, barque) : couleur de la texture, même ombrage deux tons
    que M_Peint. anim : animation procédurale (ANIM_CODES) ; glow : teinte de bioluminescence (abysses)."""
    path = f"/Game/Look/{name}"
    box_def = ""
    if box is not None:
        box_def = "".join(f"#define {k} {v:.3f}\n" for k, v in zip(("BXN", "BXX", "BYN", "BYX", "BZN", "BZX"), box))
    anim_code = box_def + ANIM_CODES[anim] if anim and anim != "bougie" else None
    digest = spec_digest("peint-tex-v9", PEINT_CODE, SWAY_CANDLE_CODE if anim == "bougie" else None, LAMP_CODE if anim == "bougie" else None,
                         MPC_DIGEST, texture.get_path_name(), anim_code, glow, tint,
                         (MOSS_CODE, ROCK_DETAIL_CODE, eal.get_metadata_tag(look_texture("tex-roche"), "source_sha1")) if moss else None,
                         (PROJ_CODE, proj[0].get_path_name(), eal.get_metadata_tag(proj[0], "source_sha1"), sorted(proj[1].items())) if proj else None)
    existing = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(existing, digest):
        return existing
    mat = existing or tools.create_asset(name, "/Game/Look", unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
    mat.set_editor_property("two_sided", True)
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -1300, -200)
    tex.set_editor_property("texture", texture)
    # la texture est déjà décodée (linéaire) : on la réencode pour le code commun, qui décode les couleurs sRGB
    tn = tint or (1.0, 1.0, 1.0)                     # teinte (raccord avec la palette du décor)
    enc = custom_node(mat, f"return pow(max(C * float3({tn[0]}, {tn[1]}, {tn[2]}), 0.0), 1.0 / 2.2);",
                      unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["C"], -1100, -200)
    mel.connect_material_expressions(tex, "RGB", enc, "C")
    one = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -1100, -100)
    one.set_editor_property("r", 1.0)
    nrm = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -1100, 0)
    cam = mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -1100, 100)
    half = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -1100, 200)
    half.set_editor_property("r", 0.5)
    node = custom_node(mat, PEINT_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                       ["Albedo", "AO", "N", "L", "V", "Brush", "Lumiere", "Ombre", "Ciel", "WP", "T", "B", "Cam"], -500, 0)
    mel.connect_material_expressions(enc, "", node, "Albedo")
    mel.connect_material_expressions(one, "", node, "AO")
    mel.connect_material_expressions(nrm, "", node, "N")
    mel.connect_material_expressions(cam, "", node, "V")
    mel.connect_material_expressions(half, "", node, "Brush")
    wire_lantern(mat, node)
    for i, (pin, name_) in enumerate((("L", "SoleilDir"), ("Lumiere", "Lumiere"), ("Ombre", "Ombre"), ("Ciel", "CielAppoint"))):
        cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1100, 300 + 100 * i)
        cp.set_editor_property("collection", MPC)
        cp.set_editor_property("parameter_name", name_)
        mel.connect_material_expressions(cp, "", node, pin)
    out = node
    if glow is not None:          # bioluminescence : la texture éclaire aussi par elle-même
        # s'éteint en s'éloignant (AbyssFade, animé par la séquence)
        gl = custom_node(mat, f"return (C + Tex * float3({glow[0]}, {glow[1]}, {glow[2]})) * saturate(F);",
                         unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["C", "Tex", "F"], -250, 0)
        mel.connect_material_expressions(node, "", gl, "C")
        mel.connect_material_expressions(tex, "RGB", gl, "Tex")
        fd = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -500, 200)
        fd.set_editor_property("collection", MPC)
        fd.set_editor_property("parameter_name", "AbyssFade")
        mel.connect_material_expressions(fd, "", gl, "F")
        out = gl
    if moss:
        rk = custom_node(mat, f"#define MEAN {TEX_MEAN['tex-roche']:.4f}\n" + ROCK_DETAIL_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                         ["C", "N", "WP", "Tex"], -300, -250)
        mel.connect_material_expressions(out, "", rk, "C")
        mel.connect_material_expressions(nrm, "", rk, "N")
        mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -550, -300), "", rk, "WP")
        rto = mel.create_material_expression(mat, unreal.MaterialExpressionTextureObject, -550, -350)
        rto.set_editor_property("texture", look_texture("tex-roche"))
        mel.connect_material_expressions(rto, "", rk, "Tex")
        out = rk
        mo = custom_node(mat, MOSS_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["C", "N", "WP"], -250, -150)
        mel.connect_material_expressions(out, "", mo, "C")
        mel.connect_material_expressions(nrm, "", mo, "N")
        mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -500, -250), "", mo, "WP")
        out = mo
    if proj is not None:
        ptex, pbox = proj
        defs = box_def + "".join(f"#define {k} {v:.4f}\n" for k, v in (("PU0", pbox["u0"]), ("PU1", pbox["u1"]), ("PV0", pbox["v0"]),
                                                                      ("PV1", pbox["v1"]), ("PFLIP", pbox.get("flip", 0.0)), ("PSTR", pbox.get("force", 0.9))))
        pj = custom_node(mat, defs + PROJ_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["C", "LP", "NL", "Tex", "Lumiere", "Ombre", "Ciel"], -150, -150)
        mel.connect_material_expressions(out, "", pj, "C")
        mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionLocalPosition, -500, -400), "", pj, "LP")
        nl = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -500, -350)
        nl.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
        nl.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
        mel.connect_material_expressions(nrm, "", nl, "")
        mel.connect_material_expressions(nl, "", pj, "NL")
        to = mel.create_material_expression(mat, unreal.MaterialExpressionTextureObject, -500, -300)
        to.set_editor_property("texture", ptex)
        mel.connect_material_expressions(to, "", pj, "Tex")
        for i, nm in enumerate(("Lumiere", "Ombre")):
            cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -500, -250 + 50 * i)
            cp.set_editor_property("collection", MPC)
            cp.set_editor_property("parameter_name", nm)
            mel.connect_material_expressions(cp, "", pj, nm)
        cpc = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -500, -150)
        cpc.set_editor_property("collection", MPC)
        cpc.set_editor_property("parameter_name", "CielAppoint")
        mel.connect_material_expressions(cpc, "", pj, "Ciel")
        out = pj
    if anim == "bougie":          # lanterne : le papier (clair) s'allume à la bougie, les nervures restent sombres
        lmp = custom_node(mat, LAMP_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["C", "Tex", "T"], -250, 0)
        mel.connect_material_expressions(out, "", lmp, "C")
        mel.connect_material_expressions(tex, "RGB", lmp, "Tex")
        mel.connect_material_expressions(mel.create_material_expression(mat, unreal.MaterialExpressionTime, -500, 300), "", lmp, "T")
        out = lmp
    mel.connect_material_property(out, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if anim == "bougie":
        wire_sway(mat, SWAY_CANDLE_CODE, (1, 0, 0))
    if anim_code is not None:
        lp = mel.create_material_expression(mat, unreal.MaterialExpressionLocalPosition, -900, 500)
        tt = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -900, 600)
        ph = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -900, 700)
        ph.set_editor_property("parameter_name", "Phase")
        ph.set_editor_property("use_custom_primitive_data", True)
        ph.set_editor_property("primitive_data_index", 0)
        an = custom_node(mat, anim_code, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["LP", "T", "Ph"], -650, 600)
        for src, pin in ((lp, "LP"), (tt, "T"), (ph, "Ph")):
            mel.connect_material_expressions(src, "", an, pin)
        tr = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -400, 600)
        tr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
        tr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(an, "", tr, "")
        mel.connect_material_property(tr, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError(f"{name} ne compile pas")
    mark_saved(mat, digest)
    return mat


def painted_model(model, name, anim=None, glow=None, tint=None, moss=False, proj=None):
    """Remplace les matériaux glTF du modèle par le look peint (texture de couleur conservée)."""
    b = model.get_bounding_box()
    box = (b.min.x, b.max.x, b.min.y, b.max.y, b.min.z, b.max.z)
    mats = []
    for i in range(model.get_num_sections(0) if hasattr(model, "get_num_sections") else 1):
        mi = model.get_material(i)
        if mi is None:
            break
        tex = mel.get_material_instance_texture_parameter_value(mi, "BaseColorTexture") if isinstance(mi, unreal.MaterialInstance) else None
        if tex is None:
            mats.append(None)
            continue
        mats.append(peint_tex_material(f"M_Peint_{name}{i}", tex, anim, box, glow, tint, moss, proj))
    return mats


CREATURE_ANIM = {"GB_Volante": "vol", "GB_Troupeau": "marche", "GB_Abysses": "nage"}
_phase = [0.0]


def creature(label, kind, loc):
    rel_glb, mat, fallback, mscale, dz, max_tris = CREATURES[kind]
    model = import_glb(rel_glb, f"/Game/Assets/{kind[3:]}", max_tris)
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
    # look peint et animation procédurale ; les abysses gardent leur bioluminescence (teinte GLOW)
    for i, pm in enumerate(painted_model(model, kind[3:], CREATURE_ANIM.get(kind), GLOW.get(kind))):
        if pm is not None:
            m.static_mesh_component.set_material(i, pm)
    _phase[0] += 1.7                                   # chaque animal à son pas
    m.static_mesh_component.set_custom_primitive_data_float(0, _phase[0])
    return blk


creature("GB_Abysses", "GB_Abysses", ue(0, -60, -3.2))
for i in range(5):
    creature(f"GB_Troupeau{i}", "GB_Troupeau", ue(0, -60 - i * 4, 0.6))
creature("GB_Volante", "GB_Volante", ue(*moon_xy, 150))
if model is not None:      # la barque et la lanterne prennent aussi le look peint
    for i, pm in enumerate(painted_model(model, "Barque", tint=(0.78, 0.66, 0.54))):   # bois brun patiné (image d'Olivier)
        if pm is not None:
            hull.static_mesh_component.set_material(i, pm)
    if lantern_model is not None:
        for i, pm in enumerate(painted_model(lantern_model, "Lanterne", "bougie")):
            if pm is not None:
                paper.static_mesh_component.set_material(i, pm)

# --- Ponton et arche des racines (modèles 3D, look peint) -------------------------------------------------------
def place_model(model, label, loc, yaw, size_cm, z_base_cm, painted_name, tint=None, moss=False, proj=None):
    """Pose un modèle importé : mis à l'échelle sur sa boîte (size_cm = (x, y, z), None = proportionnel),
    base posée à z_base_cm, tourné de yaw ; look peint (texture conservée)."""
    b = model.get_bounding_box()
    ext = (b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z)
    sc = [size_cm[i] / ext[i] if size_cm[i] else None for i in range(3)]
    ref = next(v for v in sc if v)
    sc = [v or ref for v in sc]
    a = actors.spawn_actor_from_object(model, unreal.Vector(loc.x, loc.y, z_base_cm - b.min.z * sc[2]), unreal.Rotator(0, 0, yaw))
    tag(a, label)
    a.set_actor_scale3d(unreal.Vector(*sc))
    a.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    for i, pm_ in enumerate(painted_model(model, painted_name, tint=tint, moss=moss, proj=proj)):
        if pm_ is not None:
            a.static_mesh_component.set_material(i, pm_)
    return a


pm = MARKS["ponton"]
pose_p = pose_at(pm["t"])
across_yaw = -pose_p["heading_deg"] - 90.0               # axe X du modèle en travers de la rivière
ponton = import_glb("ponton/trellis2-s42", "/Game/Assets/Ponton", 15000)
if ponton is not None:
    # trois travées de 2,2 m depuis la berge droite vers la trajectoire, tablier à 0,9 m, pieds dans l'eau
    for i, side in enumerate((-7.7, -5.5, -3.3)):
        loc, _ = oriented(pm["t"], pm["ahead_m"], side, 0.0)
        place_model(ponton, f"GB_Ponton{i}", loc, across_yaw + (180.0 if i % 2 else 0.0), (225.0, 200.0, 200.0), -110.0, "Ponton",
                    tint=(0.85, 0.72, 0.58))
else:                                                   # repli : pilotis et tablier
    for i, side in enumerate((-8.5, -6.0, -3.5)):
        loc, rot = oriented(pm["t"], pm["ahead_m"], side, 0.0)
        place_mesh(CYL, f"GB_PontonPieu{i}", "Bois", unreal.Vector(loc.x, loc.y, -50), rot, (0.25, 0.25, 2.2))
    loc, rot = oriented(pm["t"], pm["ahead_m"], -6.0, 0.75)
    place_mesh(CUBE, "GB_PontonTablier", "Bois", loc, unreal.Rotator(0, 0, rot.yaw + 90), (6.5, 2.0, 0.15))

am = MARKS["arche-racines"]
pose_a = pose_at(am["t"])
# Arche de statues (une seule vue : la 3D a deviné des socles très épais, 16 m dans le sens du courant, qui se rejoignent
# au ras de l'eau) : largeur de la rivière + 28 m, hauteur proportionnelle, épaisseur ramenée à 7 m, enfoncée de 5,5 m
# pour que la rivière passe dans la partie large de l'ouverture.
ARCH_EXTRA_M, ARCH_DEPTH_CM, ARCH_SINK_CM = 28.0, 700.0, -550.0
def projection(pid, flip=0.0):
    """Image projetée (PROJ_CODE) : texture et cadre écrits par pipeline/style/projection.py ; None s'ils manquent."""
    png = os.path.join(ROOT, "assets", "textures", f"proj-{pid}.png")
    if not os.path.exists(png):
        return None
    with open(os.path.join(ROOT, "assets", "textures", f"proj-{pid}.json"), encoding="utf-8") as f:
        box = json.load(f)
    box["flip"] = flip
    return look_texture(f"proj-{pid}"), box


# D18 (19/10) : l'arche de pierre aux deux figures agenouillées remplace l'arche des racines (redondante avec l'arbre
# colossal, selon Olivier). Modèle sans végétation (assets/3d/arche-statues : image d'Olivier refs/inbox/arche-statues.png,
# substitut local en attendant), habillé de mousse (matériau) et de lianes peintes (sprites_layout.py).
statues = import_glb("arche-statues/trellis2-s42", "/Game/Assets/ArcheStatues", 80000, smooth=True)   # 150 k et 400 k essayés (19/10) : pas plus de détail, la limite est la reconstruction 3D d'une seule vue   # vu de près : détail (retour du 19/10)
racine = None if statues is not None else import_glb("racine/trellis2-s42", "/Game/Assets/Racine", 30000)
if statues is not None:
    loc, _ = oriented(am["t"], 0.0, 0.0, 0.0)
    place_model(statues, "GB_ArcheStatues", loc, -pose_a["heading_deg"] - 90.0,
                ((pose_a["width_m"] + ARCH_EXTRA_M) * 100.0, ARCH_DEPTH_CM, None), ARCH_SINK_CM, "ArcheStatues", moss=True,
                proj=projection("arche-statues"))
    for a_ in actors.get_all_level_actors():
        if a_.get_actor_label() == "GB_ArcheRacines":      # l'ancien tube du greybox
            actors.destroy_actor(a_)
if racine is not None:
    # l'anneau de racines (le modèle est fermé en bas) enjambe la rivière : base enfouie à -4,8 m, le bas de l'anneau
    # devient des racines immergées vues à travers l'eau ; ~11 m de passage au-dessus de la barque
    loc, _ = oriented(am["t"], 0.0, 0.0, 0.0)
    place_model(racine, "GB_ArcheRacinesModele", loc, -pose_a["heading_deg"] - 90.0,
                ((pose_a["width_m"] + 18.0) * 100.0, None, 1700.0), -480.0, "Racine", tint=(0.42, 0.34, 0.24))   # écorce sombre moussue (S5)
    for a in actors.get_all_level_actors():
        if a.get_actor_label() == "GB_ArcheRacines":       # l'ancien tube
            actors.destroy_actor(a)

# Tête de pierre couchée (D18) : sur la berge gauche au début de S6 (tombée de la nuit : champignons lumineux dans ses
# traits, sprites_layout.py), couchée sur le côté, le visage vers la rivière, l'arrière (creux) dans la berge ; à moitié
# enfoncée dans la berge et dans l'eau. Modèle : assets/3d/tete-couchee (image d'Olivier, substitut local en attendant).
HEAD_T, HEAD_SIDE_M, HEAD_H_CM = 165.0, 1.0, 1000.0
HEAD_TOWARD_DEG = 35.0       # visage tourné vers l'amont : il regarde la barque qui arrive (on le découvre en approchant)
tete = import_glb("tete-couchee/trellis2-s42", "/Game/Assets/TeteCouchee", 50000, smooth=True)
if tete is not None:
    ph_ = pose_at(HEAD_T)
    loc, _ = oriented(HEAD_T, 0.0, ph_["width_m"] / 2 + HEAD_SIDE_M, 0.8)
    hb = tete.get_bounding_box()
    hs = HEAD_H_CM / max(hb.max.x - hb.min.x, hb.max.y - hb.min.y, hb.max.z - hb.min.z)
    # le modèle importé a le visage vers le haut (+Z) : roulis 90° → visage vers +Y (la rivière, vue de la rive gauche),
    # tangage 90° → axe menton-front horizontal (tête couchée sur la joue) ; puis le cap de la rivière. Trouvé en
    # comparant les orientations depuis la barque (19/10).
    hrot = unreal.Rotator(90.0, -90.0, ue_yaw(ph_["heading_deg"]) + HEAD_TOWARD_DEG)   # crâne vers l'amont, cou (creux) vers l'aval
    hc = unreal.Vector((hb.min.x + hb.max.x) / 2 * hs, (hb.min.y + hb.max.y) / 2 * hs, (hb.min.z + hb.max.z) / 2 * hs)
    head = actors.spawn_actor_from_object(tete, loc - unreal.MathLibrary.greater_greater_vector_rotator(hc, hrot), hrot)
    tag(head, "GB_TeteCouchee")
    head.set_actor_scale3d(unreal.Vector(hs, hs, hs))
    head.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    for i, pm_ in enumerate(painted_model(tete, "TeteCouchee", tint=(0.78, 0.78, 0.74), moss=True)):
        if pm_ is not None:
            head.static_mesh_component.set_material(i, pm_)

# Stems de la musique (pipeline/audio/prepare_stems.py) : une source par stem, attachée à la barque autour du
# spectateur ; la séquence y joue la piste (animatic.py). Sans stems déposés : rien.
_stems_json = os.path.join(ROOT, "Unreal", "Saved", "import", "stems.json")
STEMS = json.load(open(_stems_json, encoding="utf-8"))["stems"] if os.path.exists(_stems_json) else []
for st in STEMS:
    if st["position"] is None:
        continue
    fwd, left, up = st["position"]
    em = tag(actors.spawn_actor_from_class(unreal.TargetPoint, boat.get_actor_location()), st["id"])
    em.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    em.root_component.set_editor_property("relative_location", unreal.Vector(SEAT_X_CM + fwd * 100.0, -left * 100.0, EYE_CM + up * 100.0))

# Lumière de crépuscule, ciel, brume.
sun = tag(actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000), unreal.Rotator(0, -8, ue_yaw(start["heading_deg"]) + 150)), "Soleil")
sun.light_component.set_editor_property("intensity", 14.0)
sun.light_component.set_editor_property("light_color", unreal.Color(255, 170, 120, 255))
sun.light_component.set_editor_property("atmosphere_sun_light", True)
# pas d'ombres : tout le décor est non éclairé (M_Peint) ; trace GPU au Quest du 18/10 : la carte d'ombres
# (4096 × 2048) coûtait 1,4 ms par image pour rien
sun.light_component.set_editor_property("cast_shadows", False)
tag(actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)), "Ciel")
sky = tag(actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 500)), "LumiereCiel")
sky.light_component.set_editor_property("real_time_capture", False)   # capture unique : rien d'éclairé ne bouge le ciel
sky.light_component.set_editor_property("intensity", 4.0)
fog = tag(actors.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0)), "Brume")
fc = fog.component
# Valeurs de S2 (pipeline/style/ambiance.json) ; la séquence les anime ensuite beat par beat (animatic.py).
with open(os.path.join(ROOT, "pipeline", "style", "ambiance.json"), encoding="utf-8") as f:
    fog_s2 = next(b for b in json.load(f)["beats"] if b["id"] == "S2-PONTON")
fc.set_editor_property("fog_density", fog_s2["densite"])
fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(*fog_s2["brume_lineaire"], 1.0))
fc.set_editor_property("start_distance", 800.0)
# brume basse (retour d'Olivier) : épaisse au ras de l'eau, sa densité diminue de moitié tous les ~17 m de hauteur ;
# le ciel peint (matériau « ciel ») n'est pas embrumé
fc.set_editor_property("fog_height_falloff", 0.6)   # mesures du 18/10 : à 1,4 les cimes sortaient de la brume
tag(actors.spawn_actor_from_class(unreal.PlayerStart, ue(start["x"], start["y"], 0.2)), "Depart")

# Pas de réglage d'exposition : l'exposition auto est coupée dans le projet (VR) et le moteur ignore alors
# toute compensation. La lisibilité du greybox se règle par l'intensité des lumières.

# Filtre « peinture » (PC VR et rendus offline seulement : sur Quest, sans HDR mobile, aucun post-traitement
# n'est appliqué) : filtre de Kuwahara (aplats et bords nets, comme des touches de gouache) + légère saturation.
KUWAHARA_CODE = """float2 px = View.ViewSizeAndInvSize.zw;
const int R = 3;
float3 m0 = 0, m1 = 0, m2 = 0, m3 = 0, s0 = 0, s1 = 0, s2 = 0, s3 = 0;
for (int x = -R; x <= R; x++) {
  for (int y = -R; y <= R; y++) {
    float3 c = SceneTextureLookup(UV + float2(x, y) * px, 14, false).rgb;
    if (x <= 0 && y <= 0) { m0 += c; s0 += c * c; }
    if (x >= 0 && y <= 0) { m1 += c; s1 += c * c; }
    if (x <= 0 && y >= 0) { m2 += c; s2 += c * c; }
    if (x >= 0 && y >= 0) { m3 += c; s3 += c * c; }
  }
}
float n = (R + 1) * (R + 1);
m0 /= n; m1 /= n; m2 /= n; m3 /= n;
float v0 = dot(s0 / n - m0 * m0, 1), v1 = dot(s1 / n - m1 * m1, 1);
float v2 = dot(s2 / n - m2 * m2, 1), v3 = dot(s3 / n - m3 * m3, 1);
float3 c = m0; float v = v0;
if (v1 < v) { c = m1; v = v1; }
if (v2 < v) { c = m2; v = v2; }
if (v3 < v) { c = m3; v = v3; }
float l = dot(c, float3(0.2126, 0.7152, 0.0722));
return lerp(float3(l, l, l), c, 1.08);"""


def painted_filter():
    path = "/Game/Look/M_FiltrePeinture"
    digest = spec_digest("filtre-v2", KUWAHARA_CODE)
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(mat, digest):
        return mat
    mat = mat or tools.create_asset("M_FiltrePeinture", "/Game/Look", unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property("blendable_location", unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -700, 0)
    st = mel.create_material_expression(mat, unreal.MaterialExpressionSceneTexture, -700, 150)
    st.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    node = custom_node(mat, KUWAHARA_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["UV", "Unused"], -400, 0)
    mel.connect_material_expressions(uv, "", node, "UV")
    mel.connect_material_expressions(st, "Color", node, "Unused")   # rend SceneTextureLookup disponible
    mel.connect_material_property(node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        unreal.log_warning("M_FiltrePeinture ne compile pas : filtre ignoré")
        return None
    mark_saved(mat, digest)
    return mat


# Retour d'Olivier (19/10) : pas de filtre peinture sur PC, puisque le Quest ne l'a pas ; les rendus offline montrent
# ce que montre le casque. Le volume reste pour l'exposition fixe et l'absence de flou de mouvement.
PAINT_FILTER = False
FILTER = painted_filter() if PAINT_FILTER else None
ppv = tag(actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0)), "PostTraitement")
ppv.set_editor_property("unbound", True)
settings = ppv.get_editor_property("settings")
if FILTER is not None:
    settings.set_editor_property("weighted_blendables",
                                 unreal.WeightedBlendables([unreal.WeightedBlendable(1.0, FILTER)]))
# pas de flou de mouvement dans les rendus offline (il n'y en a pas au casque ; il étirait l'eau en rayons)
settings.set_editor_property("override_motion_blur_amount", True)
settings.set_editor_property("motion_blur_amount", 0.0)
# exposition fixe (pas d'exposition automatique au casque) : l'animatic montre la nuit comme le Quest
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
settings.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
ppv.set_editor_property("settings", settings)

# Recentrage VR : au lancement, origine de suivi « LocalFloor » (centrée sur la position du joueur au démarrage,
# au niveau du sol) au lieu de « Stage » (centre de la zone du Quest) : le spectateur est toujours sur le banc,
# quelle que soit la zone de jeu (retour d'Olivier : on se retrouvait derrière la barque). Blueprint écrit par
# script avec les outils Blueprint du plugin EditorToolset (catégories localisées de l'éditeur).
def recentering_blueprint():
    """BP_Recentrage : BeginPlay → origine LocalFloor → attente 1 s (pose de tête valide) → recentrage position et
    cap (la hauteur reste celle du sol : hauteur assise réelle). Le spectateur est sur le banc, face à la proue,
    quelle que soit la zone de jeu ou le dernier recentrage du Quest."""
    from editor_toolset.toolsets.blueprint import BlueprintTools as BT
    path, version = "/Game/Look/BP_Recentrage", "recentrage-v2"
    bp = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if bp is not None and eal.get_metadata_tag(bp, "source_sha1") == version:
        return bp
    if bp is not None:
        eal.delete_asset(path)
    bp = BT.create("/Game/Look", "BP_Recentrage", unreal.Actor.static_class())
    g = next(g for g in BT.list_graphs(bp) if "EventGraph" in g.get_name())

    def node(suffix, x):
        tid = next(t for t in BT.find_node_types(g, suffix) if t.endswith("|" + suffix))
        return BT._get_node_info(BT.create_node(g, tid, unreal.IntPoint(x, 0)))

    def pin(info, name, out=False):
        return next(p_.pin_id for p_ in (info.output_pins if out else info.input_pins) if str(p_.name) == name)

    begin = BT._get_node_info(next(n for n in BT.find_nodes(g) if "BeginPlay" in str(BT._get_node_info(n).type_id)))
    origin = node("SetTrackingOrigin", 300)
    delay = node("Delay", 600)
    reset = node("ResetOrientationandPosition", 900)
    BT.connect_pins(pin(begin, "then", True), pin(origin, "execute"))
    BT.set_pin_value(pin(origin, "Origin"), "LocalFloor")
    BT.connect_pins(pin(origin, "then", True), pin(delay, "execute"))
    BT.set_pin_value(pin(delay, "Duration"), "1.0")
    BT.connect_pins(pin(delay, "then", True), pin(reset, "execute"))      # sortie « Completed » nommée « then »
    BT.compile_blueprint(bp)
    eal.set_metadata_tag(bp, "source_sha1", version)
    eal.save_loaded_asset(bp)
    return bp


_rbp = recentering_blueprint()
tag(actors.spawn_actor_from_class(_rbp.generated_class(), unreal.Vector(0, 0, 0)), "RecentrageVR")
if eal.does_directory_exist("/Game/Probe"):
    eal.delete_directory("/Game/Probe")

# Pas d'éclairage précalculé : le look peint est non éclairé (M_Peint) ; seuls la barque et les créatures
# utilisent encore les lumières, toutes dynamiques. Supprime « Lighting needs to be rebuilt » en jeu.
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property("force_no_precomputed_lighting", True)
for a in actors.get_all_level_actors():
    for comp in a.get_components_by_class(unreal.LightComponentBase):
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)

levels.save_current_level()
# La séquence (animatic.py) référence les acteurs du niveau, qui viennent d'être recréés : la régénérer aussitôt,
# sinon ses pistes pointent vers des acteurs disparus (barque immobile, créatures figées).
import runpy  # noqa: E402
runpy.run_path(os.path.join(ROOT, "pipeline", "unreal", "scripts", "animatic.py"), run_name="__main__")
unreal.log(f"Greybox : {MAP} construit ({len(MESHES)} maillages)")
