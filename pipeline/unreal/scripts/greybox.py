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
               "VieJour": 1.0,       # oiseaux, papillons, libellules : présents le jour, partis la nuit (lucioles)
               "HeronFinal": 0.0,    # héron du final : 0 loin devant, 1 posé sur le rebord de la barque
               "CielNuit": 0.0}      # ciel de nuit d'Olivier (0 : ciel du crépuscule teinté, 1 : ciel de nuit)
MPC_DIGEST = spec_digest("mpc-v9", sorted(MPC_VECTORS), sorted(MPC_SCALARS))


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
# 20/10 : posée sur le plancher (14 cm), le banc avant qui la portait est retiré du modèle (bancs flottants) ; plus en
# arrière (125 → 80 cm), où la coque est large au ras du plancher, et sur le côté (30 cm du milieu) : au centre, droit
# devant la place assise, elle attirait l'œil
LANTERN_LOCAL = (80.0, 30.0, 14.0 + LANTERN_H / 2)
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
# ciel de nuit d'Olivier (20/10, refs/inbox/ciel-nuit.png, sky.py --nuit) : affiché presque tel quel (gain), pas multiplié
# par la teinte de nuit (~0,1), qui le noircirait ; fondu depuis le ciel du crépuscule par CielNuit (Nn)
NIGHT_SKY_GAIN = 0.45
SKY_STARS_CODE = """float3 d = normalize(-Dir);
float3 sky = lerp(Tex * Teinte.rgb, TexN * %(ng).2f, Nn);
float3 Tc = lerp(Tex, TexN, Nn);                             // ciel peint visible (masques des nuages)
float night = saturate(1.0 - dot(Teinte.rgb, float3(0.3, 0.5, 0.2)) * 3.0);
float2 g = float2(atan2(d.y, d.x) * 260.0, d.z * 260.0);
float2 c = floor(g);
float h = frac(sin(dot(c, float2(12.9898, 78.233))) * 43758.5453);
float2 f = frac(g) - 0.5;
float star = step(0.985, h) * saturate(1.0 - length(f) * 3.0);
float tw = 0.55 + 0.45 * sin(T * (1.5 + h * 3.0) + h * 80.0);
float clouds = saturate(1.0 - dot(Tc, float3(0.3, 0.5, 0.2)) * 1.6);
float3 col = sky + star * tw * night * clouds * saturate(d.z * 6.0) * 1.5;
// lune : disque doux et halo, masqués là où le ciel peint est un nuage (zones claires et peu bleues)
float md = dot(d, float3(%(mx).5f, %(my).5f, %(mz).5f));
float cr = cos(radians(%(mr).2f));
float disc = smoothstep(cr - 0.00004, cr + 0.00004, md);
float halo = pow(saturate((md - cr) / (1.0 - cr) * 0.5 + 0.5), 60.0) * 0.25 + pow(saturate(md), 2000.0) * 0.15;
float cloudy = lerp(saturate((Tex.r + 0.15 - Tex.b) * 3.0) * saturate(dot(Tex, float3(0.3, 0.5, 0.2)) * 2.0),
                    saturate(dot(TexN, float3(0.3, 0.5, 0.2)) * 2.5 - 0.4), Nn);   // nuages de nuit : bleutés et clairs
col += float3(1.0, 0.97, 0.88) * (disc * 1.1 + halo * (0.4 + night)) * (1.0 - cloudy * 0.9);
return col;""" % {"mx": MOON_DIR[0], "my": MOON_DIR[1], "mz": MOON_DIR[2], "mr": MOON_RADIUS_DEG, "ng": NIGHT_SKY_GAIN}


with open(os.path.join(ROOT, "pipeline", "layout", "water_map.json"), encoding="utf-8") as f:
    WATER_MAP = json.load(f)
with open(os.path.join(ROOT, "assets", "textures", "stats.json"), encoding="utf-8") as _f:
    TEX_MEAN_EAU = json.load(_f).get("tex-eau", 0.25)     # luminance moyenne de l'eau peinte d'Olivier (textures.py)
# Grille d'eau fine attachée à la barque (repère barque, cm) : 13 m derrière, 7 m devant, 6 m de chaque côté
PATCH_RECT = {"px0": 1300.0, "px1": 700.0, "py": 600.0}
PATCH_CELL = 12.5
# Relief de l'eau et sillage (20/10) : bloc commun au shader de l'eau (reflets) et au déplacement de la grille fine qui
# suit la barque (WAVE_WPO_CODE). Entrées : WP (position monde, cm), T, B (barque : x, y, lacet).
WAVE_CORE = """// lac : courant presque nul ; fondu sur ~25 m autour de son rivage (20/10 : la bascule par la carte faisait une ligne)
float lake = 1.0 - smoothstep(%(lkr).1f - 1500.0, %(lkr).1f + 1000.0, length(WP.xy - float2(%(lkx).1f, %(lky).1f)));
// autour de la barque (B : x, y, lacet en z) — reprise du 20/10 (« le bateau ne fait aucun effet sur l'eau ») :
// sillage de Kelvin né à l'étrave (deux bras à ~19,5° qui longent les flancs à ~50 cm de la coque puis s'ouvrent
// derrière, crêtes en biais fixes par rapport à la barque, vagues transversales entre les bras), vague d'étrave,
// bourrelet le long des flancs ; il fait onduler les reflets (hw) et pose de l'écume (plus bas)
float cb = cos(B.z), sb = sin(B.z);
float2 rel = WP.xy - B.xy;
float lx = dot(rel, float2(cb, sb)), ly = dot(rel, float2(-sb, cb));
// coque à la flottaison, mesurée sur le maillage (20/10) : 3,10 × 1,14 m, pointue aux deux bouts (demi-largeur
// 57 cm au milieu, 45 à ±80 cm, 24 à ±120). L'ancienne ellipse (3,56 × 1,56 m) débordait : entre elle et la coque, l'eau
// devenait transparente (« on voit l'eau un petit peu sous la barque »). d : distance au bord de la coque (cm, < 0 dedans)
float wx = 57.0 * pow(max(1.0 - (lx / 158.0) * (lx / 158.0), 0.0), 0.8);
float d = abs(lx) < 158.0 ? abs(ly) - wx : length(float2(abs(lx) - 158.0, ly));
float back = 158.0 - lx;                                             // distance derrière l'étrave (cm)
float aly = abs(ly);
float edge = back * 0.36 + 25.0;                                     // bras du sillage
float band = exp(-pow((aly - edge) / (32.0 + back * 0.06), 2.0)) * step(0.0, back);
// crêtes divergentes, en biais : lignes fines (pointe d'une sinusoïde) plutôt que des taches
float div = pow(saturate(sin((back * 0.94 + aly * 0.34) * 0.075) * 0.5 + 0.5), 5.0) * 2.2 - 0.35;
float inside = saturate(1.0 - aly / max(edge, 1.0)) * step(0.0, back);
float trv = sin(back * 0.06) * inside * exp(-max(back, 0.0) / 450.0);   // vagues transversales (courtes : au loin, des barres régulières)
float wfade = exp(-max(back, 0.0) / 1300.0) * saturate(back / 40.0);
float outside = smoothstep(-3.0, 4.0, d);
float bowh = exp(-pow((d - 10.0) / 12.0, 2.0)) * saturate((lx - 40.0) / 90.0);          // vague d'étrave
float sideh = exp(-pow((d - 9.0) / 10.0, 2.0)) * (0.55 + 0.45 * sin(lx * 0.06 + T * 3.0));   // bourrelet des flancs
// --- Relief de l'eau (20/10, Olivier : « ton souci c'est que l'eau reste une surface plane ») : hauteur wh (cm) et pente
// wg, partagées par la grille fine qui suit la barque (déplacée en hauteur) et par les reflets de toute l'eau.
// Houle de rivière : cinq ondes de gravité (vitesse c = racine(g λ / 2π)), 2 à 4 cm de creux, plus calme sur le lac.
float wh = 0.0;
float2 wg = float2(0.0, 0.0);
const float4 WV[5] = { float4(0.94, 0.34, 220.0, 1.8), float4(0.73, -0.68, 140.0, 1.2), float4(0.27, 0.96, 90.0, 0.8),
                       float4(-0.32, -0.95, 55.0, 0.45), float4(-0.86, 0.52, 34.0, 0.3) };
float calm = lerp(1.0, 0.35, lake);
for (int i = 0; i < 5; i++)
{
    float k = 6.2832 / WV[i].z;
    float ph = k * dot(WV[i].xy, WP.xy) - sqrt(981.0 * k) * T;
    wh += WV[i].w * calm * sin(ph);
    wg += WV[i].w * calm * k * cos(ph) * WV[i].xy;
}
// sillage en relief : crêtes de Kelvin (4 cm), vagues transversales, vague d'étrave (6 cm), creux le long des flancs
float wph = (back * 0.94 + aly * 0.34) * 0.075;
float wk = band * wfade * outside;
float sly = ly >= 0.0 ? 1.0 : -1.0;
wh += (wk * 4.0 * sin(wph) + trv * wfade * 1.5 + (bowh * 6.0 - sideh * 1.5) * outside);
float2 gbt = wk * 4.0 * cos(wph) * float2(-0.0705, 0.0255 * sly);                    // pente des crêtes (repère barque)
float2 nd = abs(lx) < 158.0 ? float2(0.0, sly) : normalize(float2(abs(lx) - 158.0, ly) + 1e-3) * float2(sign(lx), 1.0);
gbt += (bowh * 6.0 * (-2.0 * (d - 10.0) / 144.0) + sideh * 1.5 * 2.0 * (d - 9.0) / 100.0) * outside * nd;
wg += gbt.x * float2(cb, sb) + gbt.y * float2(-sb, cb);
// grille fine : rectangle autour de la barque (repère barque, cm), fondu sur 1,5 m au bord (raccord avec la grille de 5 m)
float pf = smoothstep(0.0, 150.0, min(min(lx + %(px0).1f, %(px1).1f - lx), %(py).1f - aly));
"""
WATER_CODE = ("""float3 v = -normalize(Dir.xyz);                       // de la caméra vers le point d'eau
""" + WAVE_CORE + """#if !PATCH
if (pf > 0.995) return float4(0.0, 0.0, 0.0, 0.0);         // la grille fine prend le relais : pas de calcul inutile
#endif
float2 rp = float2(WP.x, -WP.y) / 100.0;                   // repère du tracé, mètres
float4 m = Texture2DSample(Map, MapSampler, (rp - float2(%(x0)f, %(y0)f)) / %(size)f);
float ca = (m.r - 0.5) * 0.5 * PI;                          // cap du courant (repère du tracé)
float2 fd = float2(cos(ca), -sin(ca));                      // sens du courant, repère Unreal
float speed = lerp(1.0, 0.25, lake);
float shore = m.b;                                          // 0 sur la rive, 1 à 8 m
// rides (20/10) : réseau de crêtes sans direction (rides-iso.png) ; la perspective seule les écrase en traits
// horizontaux, quel que soit le regard (les traits orientés en travers de la rivière devenaient des rayons qui
// convergent dès qu'on regardait sur le côté : effet « pluie »). Flowmap à deux phases : elles avancent avec le
// courant local sans s'étirer ni revenir en arrière. G, B : pente de la surface, qui fait onduler les reflets.
float2 q = WP.xy / 300.0;
float ph0 = frac(T * 0.08), ph1 = frac(T * 0.08 + 0.5);
float w = abs(ph0 * 2.0 - 1.0);
float2 adv = fd * speed * 1.5;     // 19/10 : « zéro animation » à 0,9 (rides quasi immobiles) → courant lisible
float4 t0 = Texture2DSample(Rides, RidesSampler, q - adv * ph0);
float4 t1 = Texture2DSample(Rides, RidesSampler, (q - adv * ph1) * 1.27 + 0.5);
float rip = saturate(lerp(t0.r, t1.r, w) * 1.1);
float2 nr = (lerp(t0.gb, t1.gb, w) - 0.5) * 2.0;
float r2 = saturate(0.5 + nr.x * 0.5 + nr.y * 0.3);   // variation lente (découpe de l'écume, reflets des berges)
// 20/10 (« je ne vois pas vraiment de traînée autour du bateau, c'est très très léger ») : sillage renforcé
float hw = ((band * div * 1.6 * (0.45 + r2) + trv * 0.15) * wfade + bowh * 1.0 + sideh * 0.6) * outside;   // crêtes inégales
// reflet du ciel peint selon la pente réelle des vagues (atténuée au loin : les petites ondes y scintilleraient), plus
// les rides peintes et le sillage
float cdist = length(WP.xyz - Cam.xyz);
float2 wgv = wg * saturate(1.6 - cdist / 2500.0);
float3 wn = normalize(float3(-wgv.x, -wgv.y, 1.0));
float3 rd = reflect(v, wn);
rd.z = max(abs(rd.z), 0.02);
// houle lente : les reflets ondoient (19/10 : « zéro animation ») — deux trains d'ondes croisés, quelques mètres
float sw = sin(dot(WP.xy, float2(0.0021, 0.0013)) + T * 0.9) * 0.6 + sin(dot(WP.xy, float2(-0.0017, 0.0026)) - T * 0.7) * 0.4;
float su = 0.5 + atan2(rd.y, rd.x) / (2.0 * PI) + T * %(drift)f + sw * 0.004 + nr.x * 0.004;
float se = min(asin(clamp(rd.z, 0.0, 1.0)), 0.96);   // pas au-delà de 55° : au zénith l'équirectangulaire s'étire en rayons
float sv = clamp(0.82 - se / (0.5 * PI) * 0.82 + nr.y * 0.03 + sw * 0.012 + hw * 0.05, 0.0, 1.0);
// ciel du crépuscule ou de nuit (CielNuit) : une seule lecture hors du fondu (mesure du 20/10 : GPU saturé au Quest)
float2 suv = float2(su, sv), sdx = ddx(suv), sdy = ddy(suv);
float3 sky;
[branch] if (Nn < 0.001) sky = Texture2DSampleGrad(Sky, SkySampler, suv, sdx, sdy).rgb * Teinte.rgb;
else if (Nn > 0.999) sky = Texture2DSampleGrad(SkyN, SkyNSampler, suv, sdx, sdy).rgb * %(ng).2f;
else sky = lerp(Texture2DSampleGrad(Sky, SkySampler, suv, sdx, sdy).rgb * Teinte.rgb,
                Texture2DSampleGrad(SkyN, SkyNSampler, suv, sdx, sdy).rgb * %(ng).2f, Nn);
float fr = 0.06 + 0.94 * pow(1.0 - saturate(dot(wn, -v)), 4.0);
// reflet de la lisière : le rayon réfléchi part vers le haut, vers la rive qu'il rencontre (distance aux rives
// précalculée dans la carte ; dans le lac, intersection exacte avec le cercle de la rive) ; les arbres (~15 m,
// cime irrégulière) masquent le ciel sous l'angle de leur cime
float2 hd = normalize(rd.xy + float2(1e-4, 0.0));
float tanE = rd.z / max(length(rd.xy), 1e-3) + nr.y * 0.08 + hw * 0.12;
float c = dot(hd, float2(fd.y, -fd.x));                     // vers la rive gauche si > 0
// rive gauche ou droite selon le regard, fondues autour de l'axe (20/10 : la bascule nette dessinait une ligne en V dans
// le reflet, visible à l'entrée du lac)
float dist = lerp(m.g * 4000.0 / max(-c, 0.05), (m.a - 0.5) * 8000.0 / max(c, 0.05), smoothstep(-0.12, 0.12, c));
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
// crêtes des rides : traits de lumière du ciel, comme posés au pinceau (plus fins et plus doux que les traits de
// rides.png, qui faisaient des rayures blanches)
// ; discrètes en vue plongeante (de près, le réseau de crêtes faisait « reflets de piscine »)
col += rip * rip * (0.08 + 0.75 * fr) * (sky * 0.8 + Lumiere.rgb * 0.05) * (1.0 - trees * 0.6);
// scintillements : la pointe des crêtes renvoie le ciel en éclats qui bougent avec le courant
col += pow(saturate(rip * 1.25 - 0.2), 6.0) * fr * (sky * 1.1 + Lumiere.rgb * 0.15) * (1.0 - trees * 0.5);
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
float3 rdm = normalize(rd + float3(nr.x * 0.04, nr.y * 0.04, (rip - 0.45) * 0.5 + hw * 0.3));
float mg = smoothstep(0.990, 0.9985, dot(rdm, float3(%(mx).5f, %(my).5f, %(mz).5f)));
col += float3(1.0, 0.95, 0.82) * mg * (0.4 + 1.6 * rip) * nsky * (1.0 - trees * 0.8) * 1.8;   // lumière vive : visible même hors incidence rasante
// eau peinte d'Olivier (refs/tex-eau.png), entraînée par le courant avec les rides : vue plongeante, on voit la
// matière peinte de l'eau ; partout, elle module la valeur (touches claires et creux sombres)
// deux phases fondues comme les rides (19/10 : avec une seule phase, la texture revenait en arrière d'un coup à
// chaque cycle, « la texture saute ») ; la couche lente en travers est retirée le 20/10 (coût : GPU saturé au Quest,
// la houle et les reflets ondulés font maintenant vivre la surface)
float3 we0 = Texture2DSample(EauTex, EauTexSampler, (q - adv * ph0 * 1.6) * 1.3).rgb;
float3 we1 = Texture2DSample(EauTex, EauTexSampler, (q - adv * ph1 * 1.6) * 1.3 + 0.37).rgb;
float3 we = lerp(we0, we1, w);
float wl = dot(we, float3(0.3, 0.6, 0.1));
col = lerp(col, we * (Lumiere.rgb * 0.6 + 0.12) + sky * 0.08, (1.0 - fr) * 0.5 * (1.0 - trees * 0.4));
col *= 0.82 + 0.36 * saturate(wl / %(eaumean).4f);
// écume le long des berges
float lap = 0.05 + 0.025 * sin(T * 1.1 + dot(WP.xy, float2(0.003, 0.002)));      // écume qui lèche la berge
float foam = (1.0 - smoothstep(0.0, lap, shore)) * (0.55 + 0.45 * r2);
col = lerp(col, Lumiere.rgb * 0.5 + sky * 0.35, foam * 0.75);
// sillage : crêtes éclairées, creux plus sombres ; écume à l'étrave, le long des flancs et sur les crêtes des bras
float brk = saturate(rip * 0.9 + r2 * 0.8 - 0.45);                   // découpe irrégulière de l'écume
col += saturate(hw) * (sky * 0.7 + Lumiere.rgb * 0.12) * (0.45 + 0.25 * fr);   // tempéré en rasant (traits blancs)
col *= 1.0 - saturate(-hw) * 0.3;
// écume dessinée (20/10 au casque : « je ne vois pas l'écume autour du bateau, ou alors elle n'est pas très jolie » ; c'était
// un voile clair découpé par du bruit, noyé dans le reflet du ciel) : formes blanches à bord franc, comme dans l'animation
// — liseré au contact de la coque, crête de la vague d'étrave, dentelle qui se détache le long des flancs puis s'effiloche
// dans le sillage ; motif fixé à l'eau (il suit le courant) : la barque avance, la dentelle file le long des flancs
float2 fuv = (q - adv * ph0) * 2.0 + 0.23, fdx = ddx(fuv), fdy = ddy(fuv);
float4 f4 = float4(0.0, 0.5, 0.5, 0.0);
[branch] if (d < 500.0 && back > -60.0) f4 = Texture2DSampleGrad(Rides, RidesSampler, fuv, fdx, fdy);   // près de la coque seulement
float fl = f4.r;                                                    // crêtes (lignes fines)
// taches de découpe : bruit lisse calculé (la pente compressée de la texture donnait des bords en escalier)
float bn = sin(fuv.x * 7.1 + sin(fuv.y * 5.3) * 1.7) * sin(fuv.y * 6.3 + sin(fuv.x * 4.1) * 1.9);
float blob = saturate(0.5 + 0.45 * bn + 0.15 * (fl - 0.3));
// écume en V autour de la coque : depuis la place assise (yeux à 1,10 m au centre), le plat-bord masque l'eau à moins de
// ~1,1 m de l'axe et l'étrave cache l'eau devant sur plusieurs mètres (mesuré le 20/10 : un col collé à la coque restait
// invisible, même peint en rouge). Le col part fin de l'étrave (35 cm) et s'élargit vers l'arrière (~1,5 m au milieu,
// ~2,6 m à la poupe : exagéré pour une barque à 1 m/s, mais c'est ce qui se voit depuis la place assise),
// plein près de la coque, déchiré vers l'extérieur, bord irrégulier qui ondule.
float foamW = 35.0 + 0.7 * max(back, 0.0) + 25.0 * (r2 - 0.5) + 12.0 * sin(lx * 0.045 + T * 0.8);
float foamT = saturate(d / max(foamW, 1.0));                                                      // 0 coque → 1 bord du col
// bande pleine au ras de la coque (un quart du col, bord ondulé), puis réseau de filets (crêtes de rides) qui s'éclaircit
float coreW = 0.18 * foamW + (blob - 0.5) * 0.14 * foamW;
float core = (1.0 - smoothstep(coreW - 6.0, coreW + 6.0, d)) * smoothstep(-4.0, 0.0, d);
float net = smoothstep(0.3, 0.45, fl) * smoothstep(0.25, 0.45, blob) * (1.0 - smoothstep(0.55, 1.0, foamT));
float foamRim = max(core, net * 0.9) * step(-60.0, back) * exp(-max(back - 330.0, 0.0) / 250.0);
float crest = smoothstep(0.35, 0.5, bowh * (0.6 + 0.8 * fl));                                     // crête d'étrave
float reach = 30.0 + 0.1 * max(back, 0.0);                                                         // la dentelle s'élargit vers l'arrière
float lace = smoothstep(0.8, 0.86, blob) * exp(-pow(max(d - foamW, 0.0) / reach, 1.5)) * saturate(back / 40.0)
           * exp(-max(back - 200.0, 0.0) / 450.0);
float arms = smoothstep(0.55, 0.6, fl) * band * wfade * saturate(div + 0.3) * 0.8;                 // filets sur les bras du sillage
float boatfoam = saturate(max(max(foamRim, crest), max(lace, arms))) * outside;
float3 foamcol = Lumiere.rgb * 0.9 + sky * 0.25 + 0.06;                                            // blanc franc
col = lerp(col, foamcol, boatfoam * 0.85);
float2 lp = B.xy + float2(cb, sb) * %(lantx).1f + float2(-sb, cb) * %(lanty).1f;
float dlw = length(WP.xy - lp);
float flick = 0.86 + 0.1 * sin(T * 11.0) * sin(T * 6.7 + 1.3) + 0.04 * sin(T * 23.0);
col += float3(%(cr).2f, %(cg).2f, %(cb).2f) * flick * (0.25 + 0.75 * rip) * 0.9 / (1.0 + (dlw / 140.0) * (dlw / 140.0));
// halo de la créature des abysses sur la surface (lumière vue à travers l'eau), plus faible quand elle s'enfonce
float2 da = WP.xy - Ab.xy;
float halo = exp(-dot(da, da) / (420.0 * 420.0)) * saturate(1.0 + Ab.z / 900.0) * saturate(Af);
col += float3(0.15, 1.6, 2.0) * 0.18 * halo * (0.6 + 0.4 * rip);
float op = max(lerp(0.68, 0.97, fr) * (1.0 - 0.55 * halo), max(foam, boatfoam * 0.85));   // eau plus claire au-dessus de la créature
op *= smoothstep(-10.0, -2.0, d);                                  // pas d'eau dans la coque
#if PATCH
op *= pf;
#else
op *= 1.0 - pf;
#endif
return float4(col, op);""") % (WATER_FMT := {"lantx": LANTERN_LOCAL[0], "lanty": LANTERN_LOCAL[1], "cr": CANDLE_RGB[0], "cg": CANDLE_RGB[1], "cb": CANDLE_RGB[2], "x0": WATER_MAP["x0"], "y0": WATER_MAP["y0"], "size": WATER_MAP["size_m"], "drift": SKY_DRIFT,
   "mx": MOON_DIR[0], "my": MOON_DIR[1], "mz": MOON_DIR[2], "eaumean": TEX_MEAN_EAU, "lkx": RIVER["lake"]["x"] * 100, "lky": -RIVER["lake"]["y"] * 100, "lkr2": (RIVER["lake"]["radius_m"] * 100) ** 2, "lkr": RIVER["lake"]["radius_m"] * 100, "ng": NIGHT_SKY_GAIN, **PATCH_RECT})
# déplacement de la grille fine : hauteur de l'eau, fondue au bord (raccord avec la grille plate de 5 m)
WAVE_WPO_CODE = (WAVE_CORE + "return float3(0.0, 0.0, wh * pf);") % WATER_FMT


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
// de jour, la bougie compte peu (20/10 : la barque paraissait rose pâle en plein jour, délavée par la lanterne)
lamp *= lerp(1.0, 0.35, saturate((dot(Lumiere.rgb, float3(0.3, 0.5, 0.2)) - 0.25) / 0.6));
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
float2 uv = (n.z >= n.x && n.z >= n.y) ? (Local > 0.5 ? pp.yx : pp.xy) : ((n.x >= n.y) ? pp.yz : pp.xz);   // plancher : planches dans la longueur
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
RIDES_TEX = look_texture("rides-iso", srgb=False, compression=unreal.TextureCompressionSettings.TC_DEFAULT)   # crêtes + pente (brush_texture.py)
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
return Col.rgb * (core + halo) * blink * saturate((Fade * 1.05 - UV.y) * 12.0);   // une à une, chacune en ~1/12 du fondu"""


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
# Vent : balancement lent, pied fixe, amplitude croissante vers la cime (~2 % de la hauteur), phase selon le lieu.
# Le plan ne tourne pas avec la tête (retour d'Olivier du 19/10) : il oscille autour de sa position fixe.
SPRITE_WIND_CODE = """float hs = length(U) * 100.0;                          // hauteur du sujet (cm) : plan de 100 unités × échelle
// (19/10 : sans le × 100, le balancement faisait ~5 mm à la cime, invisible au casque)
float z = saturate(LP.z / 100.0 + 0.5 * C);                 // pied (0) à cime (1) (plan de 100 unités ; touffes centrées)
// phase quasi uniforme (une rafale traverse la forêt en ~40 s) : avec une phase propre à chaque arbre, deux voisins se
// balançaient à contretemps et s'entrechoquaient (19/10)
float s = sin(T * 0.8 + dot(WP.xy, float2(0.00008, 0.00005))) + 0.3 * sin(T * 1.7 + dot(WP.xy, float2(0.00011, -0.00007)));
return float3(0.8, 0.6, 0.0) * s * 0.018 * hs * z * z * E;   // ~2 % de la hauteur à la cime (30 cm pour 15 m)"""
SPRITE_TINT_CODE = """return Tex * (1.0 + Tint * float3(0.08, 0.015, -0.1));"""
SPRITE_EDGE_CODE = """return A * lerp(1.0, smoothstep(0.12, 0.3, abs(dot(normalize(N), normalize(V)))), E);"""


def sprite_material(relief=False):
    """Matériau des sprites ; relief=True : variante dont la grille se creuse selon la carte de relief (sujets proches)."""
    name = "M_GB_SpriteRelief" if relief else "M_GB_Sprite"
    path = f"{GB}/{name}"
    digest = spec_digest("sprite-v7", SPRITE_UV_CODE, SPRITE_COLOR_CODE, SPRITE_EDGE_CODE, SPRITE_TINT_CODE, MPC_DIGEST,
                         SPRITE_RELIEF_CODE if relief else "", SPRITE_WIND_CODE, WAVE_WPO_CODE)
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
    # nénuphars (« Flotte », interrupteur statique : seule leur variante calcule les vagues) : ils suivent le relief de l'eau
    # de la grille fine (même hauteur que M_GB_EauProche), sinon les crêtes les recouvraient
    fb = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1300, 2000)
    fb.set_editor_property("collection", MPC)
    fb.set_editor_property("parameter_name", "Barque")
    flo = custom_node(mat, WAVE_WPO_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["WP", "T", "B"], -1000, 2000)
    for pin, src in (("WP", wwp), ("T", mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1300, 2100)), ("B", fb)):
        mel.connect_material_expressions(src, "", flo, pin)
    fadd = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -500, 1900)
    mel.connect_material_expressions(wpo_out, "", fadd, "A")
    mel.connect_material_expressions(flo, "", fadd, "B")
    fsw = mel.create_material_expression(mat, unreal.MaterialExpressionStaticSwitchParameter, -350, 1900)
    fsw.set_editor_property("parameter_name", "Flotte")
    fsw.set_editor_property("default_value", False)
    mel.connect_material_expressions(fadd, "", fsw, "True")
    mel.connect_material_expressions(wpo_out, "", fsw, "False")
    mel.connect_material_property(fsw, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
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
    flotte = name == "eau" and mode == "sol"
    mi_digest = spec_digest("mi-sprite-v2", flotte, parent.get_path_name(), eal.get_metadata_tag(parent, "source_sha1"),
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
        mel.set_material_instance_static_switch_parameter_value(mi, "Flotte", flotte)
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
else if (type > 7.5)                                 // feuille ou pétale qui flotte : dérive avec le courant, à plat
{
    float f = frac(T * spd * 0.01 + P2.y);            // une dérive de 12 m en ~100 s, puis elle renaît plus haut
    float2 dir = float2(cos(P2.x), sin(P2.x));        // cap du courant (rad, repère Unreal)
    o = float3(dir * (f - 0.5) * 1200.0, 0.8 * sin(T * 1.5 + ph * 4.0));
    size = 13.0 * saturate(min(f * 10.0, (1.0 - f) * 10.0));
    float r = ph + T * 0.05;                          // tourne lentement sur elle-même
    float2 cc = float2(c.x * cos(r) - c.y * sin(r), c.x * sin(r) + c.y * cos(r));
    return o + float3(cc.x, cc.y, 0.0) * size * 0.5;  // à plat sur l'eau
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
float cells[9] = {0, 1, 2, 3, 4, 5, 7, 6, 4};
float cell = cells[(int)min(type, 8.0)];
return float2((fmod(cell, 4.0) + UV.x) / 4.0, (floor(cell / 4.0) + UV.y) / 2.0);"""


def vie_material():
    path = f"{GB}/M_GB_Vie"
    atlas = look_texture("sprite_vie")
    digest = spec_digest("vie-v8", VIE_WPO_CODE, VIE_UV_CODE, SPRITE_COLOR_CODE, MPC_DIGEST, eal.get_metadata_tag(atlas, "source_sha1"))
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


def model_dir(mid, source="trellis2-s42"):
    """Dossier du modèle 3D <mid> : la version reprise dans Blender (pipeline/blender/nettoyage_3d.py) si elle existe,
    sinon la reconstruction brute."""
    return f"{mid}/blender" if os.path.exists(os.path.join(ROOT, "assets", "3d", mid, "blender", "model.glb")) else f"{mid}/{source}"


def import_glb(rel_glb, dest_dir, max_tris=None, smooth=False, cut=(), lods=(), max_tex=2048):
    """Importe assets/3d/<rel_glb>/model.glb dans dest_dir (une fois par empreinte du fichier et par budget de
    triangles) ; None si absent. max_tris : simplification à l'import (budget Quest : ≤ 500 k triangles visibles).
    max_tex : taille maximale des textures dans le jeu (modèles régénérés en 4096 le 19/10 : 4096 seulement pour ce qui
    se voit de près, la mémoire du Quest ne tiendrait pas tout en 4096)."""
    import hashlib
    glb = os.path.join(ROOT, "assets", "3d", rel_glb, "model.glb")
    if not os.path.exists(glb):
        return None
    mesh_path = f"{dest_dir}/model/StaticMeshes/model"
    with open(glb, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12] + (f"-{max_tris}" if max_tris else "") + ("-lisse" if smooth else "") + "-sans-nanite-v2" \
            + (f"-coupe{hash(tuple(cut)) & 0xffff:04x}" if cut else "") + (f"-lod{'_'.join(f'{a}x{b}' for a, b in lods)}" if lods else "") + f"-tex{max_tex}"
    if eal.does_asset_exist(mesh_path) and eal.get_metadata_tag(eal.load_asset(mesh_path), "source_sha1") == digest:
        return eal.load_asset(mesh_path)
    # dossier vidé avant réimport (19/10) : sinon l'import remplace le maillage mais garde les textures du modèle précédent
    # (pont, tête, barque : nouveau maillage, ancienne texture plaquée sur de nouvelles coordonnées → bruit de couleur)
    if eal.does_directory_exist(dest_dir):
        eal.delete_directory(dest_dir)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = glb, dest_dir
    task.automated, task.replace_existing, task.save = True, True, True
    tools.import_asset_tasks([task])
    mesh = eal.load_asset(mesh_path)
    # Nanite coupé (19/10) : l'import glTF l'active ; le Quest ne le gère pas et affichait un maillage de repli généré par
    # Nanite (pont : 67 k triangles sur 594 k, barque : 16 k sur 198 k), coordonnées de texture et détail perdus — d'où
    # des modèles pâles et à facettes, loin de leur vue tournante.
    ns = mesh.get_editor_property("nanite_settings")
    if ns.get_editor_property("enabled"):
        ns.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", ns)
        eal.save_loaded_asset(mesh)
        mesh = eal.load_asset(mesh_path)
    unreal.log(f"{rel_glb} : {mesh.get_num_triangles(0)} triangles importés (sans Nanite)")
    if cut or (max_tris and mesh.get_num_triangles(0) > max_tris):
        dm = unreal.DynamicMesh()
        unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        if max_tris and dm.get_triangle_count() > max_tris:
            dm.apply_editor_simplify_to_triangle_count(max_tris)
        for lo, hi in cut:         # morceaux à retirer (boîtes dans le repère d'import), ex. lattes de la barque qui flottent
            box = unreal.Box(unreal.Vector(*lo), unreal.Vector(*hi))
            dm, sel = unreal.GeometryScript_MeshSelection.select_mesh_elements_in_box(dm, box, unreal.GeometryScriptMeshSelectionType.TRIANGLES, False, 3)
            dm, n = unreal.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(dm, sel)
            unreal.log(f"{rel_glb} : {n} triangles retirés dans {lo} – {hi}")
        if smooth:                 # normales lissées par sommet : sculptures (le visage disparaissait dans les facettes)
            unreal.GeometryScript_Normals.set_per_vertex_normals(dm)
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, mesh, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD())
        unreal.log(f"{rel_glb} : simplifié à {mesh.get_num_triangles(0)} triangles")
    if lods:   # niveaux de détail (le Quest n'a pas Nanite) : [(part des triangles, taille à l'écran), ...] après le LOD0
        opts = unreal.StaticMeshReductionOptions()
        opts.set_editor_property("auto_compute_lod_screen_size", False)
        opts.set_editor_property("reduction_settings", [unreal.StaticMeshReductionSettings(1.0, 1.0)]
                                 + [unreal.StaticMeshReductionSettings(f, sc) for f, sc in lods])
        n = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_lods(mesh, opts)
        unreal.log(f"{rel_glb} : {n} niveaux de détail")
    for tpath in eal.list_assets(dest_dir, recursive=True, include_folder=False):
        tex = eal.load_asset(tpath)
        if isinstance(tex, unreal.Texture2D) and tex.blueprint_get_size_x() > max_tex:
            tex.set_editor_property("max_texture_size", max_tex)
            eal.save_loaded_asset(tex)
    eal.set_metadata_tag(mesh, "source_sha1", digest)
    eal.save_loaded_asset(mesh)
    return mesh


FLOOR_Z = 0.14


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
        if FLOOR_Z * 100 - 12.0 <= z <= FLOOR_Z * 100 + 12.0:
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
    # plancher à 14 cm (3 cm avant le 19/10) : il recouvre les lisses intérieures du modèle de la nouvelle barque, qui
    # flottaient au-dessus de lui vues depuis la place assise
    ring = [[(cx + (x - cx) * 0.96) / 100.0, -(cy + (y - cy) * 0.96) / 100.0, FLOOR_Z] for x, y in hull]
    verts = [[cx / 100.0, -cy / 100.0, FLOOR_Z]] + ring
    n = len(ring)
    data = {"vertices": verts, "triangles": [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)],
            "normals": [[0, 0, 1]] * len(verts), "color": [0.46, 0.33, 0.21, 0.95]}
    unreal.log(f"Plancher de la coque : {n} points, {max(p_[0] for p_ in hull) - min(p_[0] for p_ in hull):.0f} × "
               f"{max(p_[1] for p_ in hull) - min(p_[1] for p_ in hull):.0f} cm")
    return build_mesh("PlancherCoque", data)


def boat_mesh():
    # 80 k triangles (30 k avant le 20/10) : on l'a sous les yeux tout le trajet ; bancs flottants retirés dans Blender
    return import_glb(model_dir("barque"), BOAT_DIR, 80000, max_tex=4096)


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
    lantern_model = import_glb(model_dir("lanterne"), "/Game/Assets/Lanterne", 6000, max_tex=1024)
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

# Héron du final (idée d'Olivier du 19/10 : la fin était un peu morne) : il arrive de loin devant à gauche, plane en
# descendant et se pose sur le rebord gauche de la barque, ailes levées (image « atterrissage »), puis reste posé
# (image « pose »). Deux plans attachés à la barque, face à l'œil comme la petite vie ; progression HeronFinal (MPC).
# Héron v3 (20/10, retour d'Olivier : « presque pas mal mais il va falloir revoir l'animation » ; avant : une image figée
# qui glissait 16 s puis basculait d'un coup sur l'image « posé »). Le plan « en vol » est une grille : les ailes (haut de
# l'image, hors tête) pivotent autour de la ligne des épaules, battent au départ, planent pendant l'approche, battent pour
# freiner ; le corps monte quand elles s'abaissent, pique en descendant, se cabre au freinage. Au contact, ailes repliées
# et fondu en 0,5 s vers l'image « posé », qui se tasse puis respire.
HERON_WPO_CODE = """float p = saturate(P);
float pa = saturate(p / 0.95);                            // 0.95 : contact avec le plat-bord
float k = 1.0 - pow(1.0 - pa, 1.8);                       // ralentit en arrivant
float3 a = float3(3200.0, -1600.0, 900.0);               // départ, repère de la barque (cm) : loin devant à gauche, haut
// 20/10 au casque : « il se prend un peu le bateau en pleine pomme » → fin d'approche par la gauche, en descente, sans
// passer devant le visage ; « il se pose à 10 cm au-dessus de la barque » → pattes sur le rebord (mesuré : 45 cm)
float3 m = float3(150.0, -750.0, 420.0);
float3 b = float3(90.0, -58.0, 45.0);                    // sur le plat-bord gauche, à 90 cm devant le centre de la barque
float3 pl = lerp(lerp(a, m, k), lerp(m, b, k), k);        // courbe de Bézier : plane en descendant
float3 dl = lerp(m - a, b - m, k);
float fold = smoothstep(0.95, 0.97, p);                   // ailes repliées, passage à l'image « posé »
float env = max(saturate(1.0 - pa * 2.5), smoothstep(0.6, 0.85, pa)) * (1.0 - fold);   // battements : envol, freinage
float fl = sin(T * 8.5);                                  // ~1,35 battement par seconde
pl.z -= fl * env * 9.0;                                   // le corps monte quand les ailes s'abaissent
pl.z -= fold * (1.0 - fold) * 16.0;                       // se tasse en se posant (4 cm)
float3 pw = AX.xyz * pl.x + AY.xyz * pl.y + AZ.xyz * pl.z;
float3 dw = AX.xyz * dl.x + AY.xyz * dl.y;
float flip = dot(dw, VR.xyz) > 0.0 ? -1.0 : 1.0;         // les images regardent vers la gauche
float u = UV0.x, v = UV0.y;                               // v = 0 en haut de l'image
float qx, qy, show;
if (UV1.x < 0.5)
{
    // ailes : bande du haut (au-dessus de la tête) et haut de l'image derrière le cou ; tête et pattes ne bougent pas
    float wing = max((1.0 - smoothstep(0.26, 0.36, v)), smoothstep(0.36, 0.46, u) * (1.0 - smoothstep(0.46, 0.56, v)));
    float s = lerp(0.3, lerp(-0.1, 1.0, 0.5 + 0.5 * fl), env);    // 1 : levées (l'image), 0,3 : plané, < 0 : abaissées
    s = lerp(s, 0.1, fold);
    float vv = v + (0.48 - v) * (1.0 - s) * wing;
    // envergure ~1 m ; pattes (bas de l'image, v ≈ 0,93) sur la trajectoire : au contact, elles touchent le rebord
    float x0 = (u - 0.5) * 120.0, y0 = (0.93 - vv) * 120.0;
    float desc = saturate(-dl.z / max(length(dl), 1.0));
    float ang = desc * 0.5 - 0.25 * smoothstep(0.8, 0.95, pa) * (1.0 - fold);   // pique en descendant, se cabre en freinant
    float ca = cos(ang), sa = sin(ang);
    qx = (x0 * ca - y0 * sa) * flip;
    qy = x0 * sa + y0 * ca;
    show = step(0.002, p) * step(fold, 0.999);
}
else
{
    // ~90 cm debout (20/10 : posé, il paraissait plus petit qu'en vol) ; pattes (v ≈ 0,94) sur le rebord ; respiration
    qx = (u - 0.5) * 95.0 * flip;
    qy = (0.94 - v) * 95.0 * (1.0 + 0.012 * sin(T * 1.7));
    show = step(0.001, fold);
}
return pw + (VR.xyz * qx + VU.xyz * qy) * show;"""
# fondu de l'image « en vol » vers l'image « posé » : dissolution par cellules (matériau masqué, pas de transparence)
HERON_MASK_CODE = """float fold = smoothstep(0.95, 0.97, saturate(P));
float h = frac(sin(dot(floor(UV0 * 160.0), float2(12.9898, 78.233))) * 43758.5453);   // cellules fines (48 : gros carrés)
return A * (UV1.x < 0.5 ? step(h, 1.0 - fold) : step(h, fold));"""
HERON_UV_CODE = """return float2((UV1.x + UV0.x) * 0.5, UV0.y);"""


def heron_material():
    path = f"{GB}/M_GB_Heron"
    atlas = look_texture("sprite_heron")
    digest = spec_digest("heron-v4", HERON_WPO_CODE, HERON_UV_CODE, HERON_MASK_CODE, SPRITE_COLOR_CODE, MPC_DIGEST, eal.get_metadata_tag(atlas, "source_sha1"))
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if up_to_date(mat, digest):
        return mat
    mat = mat or tools.create_asset("M_GB_Heron", GB, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("two_sided", True)
    def vec(src, v, y):
        c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1700, y)
        c.set_editor_property("constant", unreal.LinearColor(*v, 0))
        t = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -1500, y)
        t.set_editor_property("transform_source_type", src)
        t.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(c, "", t, "")
        return t
    LOCAL = unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL
    VIEW = unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_VIEW
    uv0 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1700, -400)
    uv1 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1700, -300)
    uv1.set_editor_property("coordinate_index", 1)
    pp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1700, 0)
    pp.set_editor_property("collection", MPC)
    pp.set_editor_property("parameter_name", "HeronFinal")
    wpo = custom_node(mat, HERON_WPO_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["P", "T", "UV0", "UV1", "AX", "AY", "AZ", "VR", "VU"], -1000, 200)
    srcs = {"P": pp, "T": mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1700, 100), "UV0": uv0, "UV1": uv1,
            "AX": vec(LOCAL, (1, 0, 0), 300), "AY": vec(LOCAL, (0, 1, 0), 400), "AZ": vec(LOCAL, (0, 0, 1), 500),
            "VR": vec(VIEW, (1, 0, 0), 600), "VU": vec(VIEW, (0, 1, 0), 700)}
    for k, v in srcs.items():
        mel.connect_material_expressions(v, "", wpo, k)
    mel.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    uvn = custom_node(mat, HERON_UV_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT2, ["UV0", "UV1"], -1100, -350)
    mel.connect_material_expressions(uv0, "", uvn, "UV0")
    mel.connect_material_expressions(uv1, "", uvn, "UV1")
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -800, -350)
    tex.set_editor_property("texture", atlas)
    mel.connect_material_expressions(uvn, "", tex, "UVs")
    one = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -800, -150)
    one.set_editor_property("r", 1.2)
    col = custom_node(mat, SPRITE_COLOR_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Tex", "Lumiere", "Ombre", "Ciel", "Bright", "Day"], -400, -350)
    mel.connect_material_expressions(tex, "RGB", col, "Tex")
    mel.connect_material_expressions(one, "", col, "Bright")
    for i, nm in enumerate(("Lumiere", "Ombre", "Ciel", "Day")):
        cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -800, -50 + 80 * i)
        cp.set_editor_property("collection", MPC)
        cp.set_editor_property("parameter_name", {"Ciel": "CielAppoint", "Day": "VieJour"}.get(nm, nm))
        mel.connect_material_expressions(cp, "", col, nm)
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mk = custom_node(mat, HERON_MASK_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT1, ["A", "UV0", "UV1", "P"], -400, -150)
    mel.connect_material_expressions(tex, "A", mk, "A")
    mel.connect_material_expressions(uv0, "", mk, "UV0")
    mel.connect_material_expressions(uv1, "", mk, "UV1")
    mel.connect_material_expressions(pp, "", mk, "P")
    mel.connect_material_property(mk, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    mel.recompile_material(mat)
    if mel.get_statistics(mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError("M_GB_Heron ne compile pas")
    mark_saved(mat, digest)
    return mat


if os.path.exists(os.path.join(ROOT, "assets", "textures", "sprite_heron.png")):
    MATS["Heron"] = heron_material()
    hv, ht, huv, huv1 = [], [], [], []
    # deux plans, sommets à l'origine (écartés de 5 mm : triangles non dégénérés) ; « en vol » en grille 12 × 12 (les ailes
    # se plient), « posé » en un seul quad
    for which, n in ((0, 12), (1, 1)):
        base = len(hv)
        for j in range(n + 1):
            for i in range(n + 1):
                u, v = i / n, j / n
                hv.append([(u - 0.5) * 0.005, 0.0, (1 - v) * 0.005])
                huv.append([u, v])
                huv1.append([which, 0])
        for j in range(n):
            for i in range(n):
                a_, b_ = base + j * (n + 1) + i, base + (j + 1) * (n + 1) + i
                ht += [[a_, a_ + 1, b_ + 1], [a_, b_ + 1, b_]]
    heron_mesh = build_mesh("HeronFinal", {"vertices": hv, "triangles": ht, "normals": [[0, -1, 0]] * len(hv), "uv": huv, "uv1": huv1,
                                           "color": [1, 1, 1, 1]})
    heron = place_mesh(heron_mesh, "GB_HeronFinal", "Heron", boat.get_actor_location())
    heron.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    heron.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    heron.root_component.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    heron.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
    heron.static_mesh_component.set_editor_property("bounds_scale", 4000.0)   # il vient de 36 m : jamais exclu du rendu
    # émetteur de ses sons (cri, battements d'ailes), déplacé par la séquence le long de la même courbe (animatic.py)
    hs_ = tag(actors.spawn_actor_from_class(unreal.TargetPoint, boat.get_actor_location()), "GB_Son_Heron")
    hs_.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    hs_.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
# Caméra du spectateur, sur le banc arrière (-1,20 m du centre), yeux à 1,10 m de l'eau. Reculée de 0,80 m
# à 1,20 m pour réduire la place de la lanterne de proue dans le champ (SUIVI.md, D11).
# place assise à l'arrière (avancer sur le banc ne cachait pas les lisses qui flottaient : le plancher les recouvre, FLOOR_Z)
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
    SKY_NIGHT_PNG = os.path.join(ROOT, "assets", "sky", "ciel-nuit.png")
    sky_night_src = SKY_NIGHT_PNG if os.path.exists(SKY_NIGHT_PNG) else SKY_PNG     # repli : ciel du crépuscule
    with open(sky_night_src, "rb") as f:
        sky_night_digest = hashlib.sha1(f.read()).hexdigest()[:12]
    sky_night_tex = eal.load_asset(f"{GB}/ciel-nuit") if eal.does_asset_exist(f"{GB}/ciel-nuit") else None
    if sky_night_tex is None or eal.get_metadata_tag(sky_night_tex, "source_sha1") != sky_night_digest:
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = sky_night_src, GB, "ciel-nuit"
        task.automated, task.replace_existing, task.save = True, True, True
        tools.import_asset_tasks([task])
        sky_night_tex = eal.load_asset(f"{GB}/ciel-nuit")
        eal.set_metadata_tag(sky_night_tex, "source_sha1", sky_night_digest)
        eal.save_loaded_asset(sky_night_tex)
    sky_digest = sky_digest + "-" + sky_night_digest
    SKY_WATER_VERSION = "ciel-eau-v43"   # à incrémenter si le code des matériaux du ciel ou de l'eau change
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
    stn = mel.create_material_expression(sky_mat, unreal.MaterialExpressionTextureSample, -200, 120)
    stn.set_editor_property("texture", sky_night_tex)
    mel.connect_material_expressions(cu, "", stn, "UVs")
    nn = mel.create_material_expression(sky_mat, unreal.MaterialExpressionCollectionParameter, -200, 350)
    nn.set_editor_property("collection", MPC)
    nn.set_editor_property("parameter_name", "CielNuit")
    mul = custom_node(sky_mat, SKY_STARS_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Dir", "T", "Tex", "Teinte", "TexN", "Nn"], 0, 100)
    mel.connect_material_expressions(camv, "", mul, "Dir")
    mel.connect_material_expressions(tnode, "", mul, "T")
    mel.connect_material_expressions(st, "RGB", mul, "Tex")
    mel.connect_material_expressions(cp, "", mul, "Teinte")
    mel.connect_material_expressions(stn, "RGB", mul, "TexN")
    mel.connect_material_expressions(nn, "", mul, "Nn")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(sky_mat)
    mark_saved(sky_mat, spec_digest(SKY_WATER_VERSION, sky_digest, MPC_DIGEST, WATER_CODE,
                                    eal.get_metadata_tag(WATER_MAP_TEX, "source_sha1"),
                                    eal.get_metadata_tag(RIDES_TEX, "source_sha1"), eal.get_metadata_tag(GLOW_TEX, "source_sha1"), eal.get_metadata_tag(EAU_TEX, "source_sha1")))
    # Eau peinte (voir WATER_CODE) : rides qui suivent le courant, reflet du ciel déformé, reflets de crêtes,
    # bande sombre du reflet des arbres près des berges, écume le long des rives, fond profond ; translucide
    # pour voir la créature des abysses. Sans réflexions temps réel (coût Quest faible).
    def build_water(name, patch):
        """Eau de la grande grille (plate, patch=False) ou de la grille fine qui suit la barque (patch=True : relief des
        vagues en déplacement de sommets). Même code (WATER_CODE), PATCH choisit le fondu de raccord."""
        path = f"{GB}/{name}"
        water = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(name, GB, unreal.Material, unreal.MaterialFactoryNew())
        mel.delete_all_material_expressions(water)
        water.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        water.set_editor_property("float_precision_mode", unreal.MaterialFloatPrecisionMode.MFPM_FULL)   # Quest : pas de calcul en 16 bits
        water.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        water.set_editor_property("two_sided", True)
        # brouillard par pixel (20/10) : calculé aux sommets de la grille de 5 m, son départ dessinait une ligne droite
        # dans l'eau à l'entrée du lac (rendu PC ; à vérifier au casque)
        water.set_editor_property("compute_fog_per_pixel", True)
        wcam = mel.create_material_expression(water, unreal.MaterialExpressionCameraVectorWS, -1000, 0)
        wpos = mel.create_material_expression(water, unreal.MaterialExpressionWorldPosition, -1000, 100)
        wt = mel.create_material_expression(water, unreal.MaterialExpressionTime, -1000, 200)
        wcp = mel.create_material_expression(water, unreal.MaterialExpressionCameraPositionWS, -1000, 250)
        wnode = custom_node(water, f"#define PATCH {int(patch)}\n" + WATER_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                            ["Dir", "WP", "T", "Map", "Rides", "Sky", "Teinte", "Lumiere", "B", "Ab", "Af", "Glow", "Day", "Lf", "Ff", "EauTex", "Cam",
                             "SkyN", "Nn"], -600, 0)
        mel.connect_material_expressions(wcam, "", wnode, "Dir")
        mel.connect_material_expressions(wpos, "", wnode, "WP")
        mel.connect_material_expressions(wt, "", wnode, "T")
        mel.connect_material_expressions(wcp, "", wnode, "Cam")
        for i, (pin, tex) in enumerate((("Map", WATER_MAP_TEX), ("Rides", RIDES_TEX), ("Sky", sky_tex), ("Glow", GLOW_TEX), ("EauTex", EAU_TEX),
                                        ("SkyN", sky_night_tex))):
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
                                          ("Ff", "FinaleFade"), ("Nn", "CielNuit"))):
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
        if patch:      # relief : hauteur des vagues et du sillage en déplacement de sommets (grille de 12,5 cm)
            vpos = mel.create_material_expression(water, unreal.MaterialExpressionWorldPosition, -1000, 1500)
            vt = mel.create_material_expression(water, unreal.MaterialExpressionTime, -1000, 1600)
            vb = mel.create_material_expression(water, unreal.MaterialExpressionCollectionParameter, -1000, 1700)
            vb.set_editor_property("collection", MPC)
            vb.set_editor_property("parameter_name", "Barque")
            wpo = custom_node(water, WAVE_WPO_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["WP", "T", "B"], -600, 1500)
            for src, pin in ((vpos, "WP"), (vt, "T"), (vb, "B")):
                mel.connect_material_expressions(src, "", wpo, pin)
            mel.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        mel.recompile_material(water)
        if mel.get_statistics(water).num_pixel_shader_instructions <= 0:
            raise RuntimeError(f"{name} : échec de compilation")
        eal.save_loaded_asset(water)
        return water
    water = build_water("M_GB_Eau", False)
    build_water("M_GB_EauProche", True)
    if mel.get_statistics(sky_mat).num_pixel_shader_instructions <= 0:
        raise RuntimeError("Matériau du ciel : échec de compilation")
if os.path.exists(SKY_PNG):
    MATS["CielPeint"] = sky_mat
    sky_sphere = place_mesh(SPHERE, "GB_CielPeint", "CielPeint", unreal.Vector(10000, 0, 0), scale=(10000, 10000, 10000))
    sky_sphere.static_mesh_component.set_editor_property("cast_shadow", False)
# Grille d'eau fine (20/10) : attachée à la barque, mailles de 12,5 cm, déplacée en hauteur par M_GB_EauProche (vagues et
# sillage en relief, visibles en stéréo) ; la grande grille de 5 m s'efface dessous (fondu sur 1,5 m au bord).
if eal.does_asset_exist(f"{GB}/M_GB_EauProche"):
    MATS["EauProche"] = eal.load_asset(f"{GB}/M_GB_EauProche")
    _nx_ = int((PATCH_RECT["px0"] + PATCH_RECT["px1"]) / PATCH_CELL)
    _ny_ = int(2 * PATCH_RECT["py"] / PATCH_CELL)
    _pv = [[(-PATCH_RECT["px0"] + i * PATCH_CELL) / 100.0, (-PATCH_RECT["py"] + j * PATCH_CELL) / 100.0, 0.0]
           for j in range(_ny_ + 1) for i in range(_nx_ + 1)]
    _pt = []
    for j in range(_ny_):
        for i in range(_nx_):
            a0 = j * (_nx_ + 1) + i
            _pt += [[a0, a0 + 1, a0 + _nx_ + 2], [a0, a0 + _nx_ + 2, a0 + _nx_ + 1]]
    _patch = place_mesh(build_mesh("EauProche", {"vertices": _pv, "triangles": _pt, "normals": [[0, 0, 1]] * len(_pv)}),
                        "GB_EauProche", "EauProche", boat.get_actor_location(), boat.get_actor_rotation())
    _patch.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    _patch.attach_to_actor(boat, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    _patch.root_component.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    _patch.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
    _patch.static_mesh_component.set_editor_property("bounds_scale", 1.5)

# Lanternes de l'arbre de S7 retirées (retour d'Olivier : trop loin, on ne voyait pas leur forme) : remplacées
# par la nuée de lucioles du lac (LuciolesLac, greybox_geometry.py), qui monte autour de la barque et dans l'arbre.

# Créatures : bloc animé par la séquence (repère : +X = sens du mouvement) + modèle 3D attaché s'il existe.
# Modèles TRELLIS.2 : longueur sur +Y à l'import (1 unité = 100 cm), comme la barque → rotation -90°.
# Échelles D4 : abysses 15 m de long (épaisseur ramenée à 2,5 m), troupeau 2,5 m au garrot, volante 40 m d'envergure.
CREATURES = {
    # bloc : (modèle, matériau du bloc, échelle du bloc de repli, échelle du modèle (x, y, z), décalage z cm, triangles max)
    "GB_Abysses": (model_dir("abysses"), "Creature", (15, 7, 1.2), (15, 15, 4.5), 0.0, 20000),
    # eau au poitrail (séquencier) : à -60 cm, seuls les dos moussus sortaient de l'eau, lus comme des rochers (19/10)
    "GB_Troupeau": (model_dir("troupeau"), "Troupeau", (3.0, 2.2, 2.5), (4.1, 4.1, 4.1), 0.0, 12000),   # pieds au sol sur la berge
    "GB_Volante": (model_dir("fly"), "Volante", (40, 12, 4), (56, 56, 56), 0.0, 20000),
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
float cad = T * (4.6 + 0.5 * sin(Ph * 2.3)) + Ph;          // cadence propre à chaque animal (±10 %)
float ph = cad + (side * fore > 0.0 ? 0.0 : 3.1416);
float stride = sin(ph) * h * 0.13 * legs;
float lift = max(0.0, cos(ph)) * h * 0.06 * legs;
float bob = sin(cad * 2.0) * h * 0.015;
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
# Ombrage « sculpté » des statues (retour d'Olivier du 19/10 : la vue tournante sur fond gris est belle, pas le rendu
# en jeu) : éclairage continu comme la vue tournante (appoint + diffus enveloppant + carte de normales), sans la frontière
# deux tons ni les touches du look peint, qui aplatissaient le modelé.
SCULPT_CODE = """float3 n = normalize(N);
float3 l = normalize(L);
float3 albedo = pow(max(Albedo, 0.0), 2.2);
float d = saturate(dot(n, l) * 0.6 + 0.4);
float sky = saturate(n.z * 0.5 + 0.5);
return albedo * (lerp(Ombre.rgb, Lumiere.rgb, d) + Ciel.rgb * sky * 0.3);   // même exposition que le look peint"""
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


def peint_tex_material(name, texture, anim=None, box=None, glow=None, tint=None, moss=False, proj=None, normal=None, sculpt=False, model_tag=None):
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
                         (PROJ_CODE, proj[0].get_path_name(), eal.get_metadata_tag(proj[0], "source_sha1"), sorted(proj[1].items())) if proj else None,
                         ("normale-v1", normal.get_path_name()) if normal else None, SCULPT_CODE if sculpt else None, model_tag)
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
    if normal is not None:   # carte de normales cuite par TRELLIS depuis la forme haute définition : le relief fin revient
        ntex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -1500, 0)
        ntex.set_editor_property("texture", normal)
        ntex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        ntr = mel.create_material_expression(mat, unreal.MaterialExpressionTransform, -1300, 0)
        ntr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT)
        ntr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        mel.connect_material_expressions(ntex, "RGB", ntr, "")
        nrm = ntr
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
    if sculpt:
        sc = custom_node(mat, SCULPT_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Albedo", "N", "L", "Lumiere", "Ombre", "Ciel"], -350, 100)
        mel.connect_material_expressions(enc, "", sc, "Albedo")
        mel.connect_material_expressions(nrm, "", sc, "N")
        for i, (pin, name_) in enumerate((("L", "SoleilDir"), ("Lumiere", "Lumiere"), ("Ombre", "Ombre"), ("Ciel", "CielAppoint"))):
            cp = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -600, 500 + 60 * i)
            cp.set_editor_property("collection", MPC)
            cp.set_editor_property("parameter_name", name_)
            mel.connect_material_expressions(cp, "", sc, pin)
        out = sc
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


def painted_model(model, name, anim=None, glow=None, tint=None, moss=False, proj=None, normal_map=False, sculpt=False, fallback_tex=None):
    """Remplace les matériaux glTF du modèle par le look peint (texture de couleur conservée)."""
    b = model.get_bounding_box()
    box = (b.min.x, b.max.x, b.min.y, b.max.y, b.min.z, b.max.z)
    model_tag = eal.get_metadata_tag(model, "source_sha1")    # matériaux reconstruits quand le modèle importé change
    mats = []
    for i in range(model.get_num_sections(0) if hasattr(model, "get_num_sections") else 1):
        mi = model.get_material(i)
        if mi is None:
            break
        tex = mel.get_material_instance_texture_parameter_value(mi, "BaseColorTexture") if isinstance(mi, unreal.MaterialInstance) else None
        tex = tex or fallback_tex          # modèle sans texture (Hunyuan3D : forme seule)
        if tex is None:
            mats.append(None)
            continue
        ntex = mel.get_material_instance_texture_parameter_value(mi, "NormalTexture") if normal_map and isinstance(mi, unreal.MaterialInstance) else None
        mats.append(peint_tex_material(f"M_Peint_{name}{i}", tex, anim, box, glow, tint, moss, proj, ntex, sculpt, model_tag))
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
    # valeur par défaut (sauvegardée avec le niveau) ; set_custom_primitive_data_float ne vit qu'à l'exécution : en jeu,
    # tous les animaux repartaient à la phase 0, d'où le troupeau au pas synchronisé (Olivier, 20/10)
    m.static_mesh_component.set_default_custom_primitive_data_float(0, _phase[0])
    return blk


creature("GB_Abysses", "GB_Abysses", ue(0, -60, -3.2))
for i in range(5):
    creature(f"GB_Troupeau{i}", "GB_Troupeau", ue(0, -60 - i * 4, 0.6))
creature("GB_Volante", "GB_Volante", ue(*moon_xy, 150))
if model is not None:      # la barque et la lanterne prennent aussi le look peint
    for i, pm in enumerate(painted_model(model, "Barque", tint=(0.70, 0.58, 0.46))):   # bois brun patiné (image d'Olivier ; un peu plus sombre le 20/10)
        if pm is not None:
            hull.static_mesh_component.set_material(i, pm)
    if lantern_model is not None:
        for i, pm in enumerate(painted_model(lantern_model, "Lanterne", "bougie")):
            if pm is not None:
                paper.static_mesh_component.set_material(i, pm)

# --- Ponton et arche des racines (modèles 3D, look peint) -------------------------------------------------------
def place_model(model, label, loc, yaw, size_cm, z_base_cm, painted_name, tint=None, moss=False, proj=None, sculpt=False, fallback_tex=None):
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
    for i, pm_ in enumerate(painted_model(model, painted_name, tint=tint, moss=moss, proj=proj, normal_map=moss or sculpt, sculpt=sculpt,
                                          fallback_tex=fallback_tex)):
        if pm_ is not None:
            a.static_mesh_component.set_material(i, pm_)
    return a


pm = MARKS["ponton"]
pose_p = pose_at(pm["t"])
across_yaw = -pose_p["heading_deg"] - 90.0               # axe X du modèle en travers de la rivière
ponton = import_glb(model_dir("ponton"), "/Game/Assets/Ponton", 15000, max_tex=4096)
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
# Arche de statues, forme complète (retour d'Olivier du 19/10 : garder le modèle entier, ne régler que la hauteur) :
# même échelle sur les trois axes, 42 m de large ; le trou du modèle va de 20 à 80 % de sa hauteur et fait au moins 13 %
# de sa largeur au-dessus de 25 % (mesuré sur le maillage) : ligne d'eau à 25 % → 5,5 m de passage au ras de l'eau,
# ~9 m à 1 m au-dessus ; fondations en briques en partie hors de l'eau. Centre du trou décalé de -1 % (modèle).
ARCH_WIDTH_CM, ARCH_WATERLINE, ARCH_HOLE_SHIFT = 4200.0, 0.25, -0.010
ARCH_PROJECTION, ARCH_SCULPT, ARCH_MOSS = False, True, False     # essais du 19/10 (review/explorations/pont/)
# variante du modèle : "trellis2" (TRELLIS.2, texturé) ou "hunyuan21" (Hunyuan3D 2.1, forme seule : projection de l'image
# d'Olivier + roche en détail) ; variable d'environnement BARQUE_ARCHE pour les essais
ARCH_VARIANT = os.environ.get("BARQUE_ARCHE", "trellis2")
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
# variante « deux » : les deux figures reconstruites séparément (image coupée aux mains, chacune sur toute la grille de
# TRELLIS) puis assemblées ; décalage en travers et rotation propre à chaque figure (TRELLIS les a remises de face)
ARCH_FIGURES = {"gauche": (0.24, float(os.environ.get("BARQUE_ROT_G", "180"))), "droite": (-0.26, float(os.environ.get("BARQUE_ROT_D", "270")))}   # trouvés par essais (19/10)
statues = None if ARCH_VARIANT == "deux" else import_glb(f"arche-statues/{ARCH_VARIANT}-s42", f"/Game/Assets/ArcheStatues_{ARCH_VARIANT}", 300000, smooth=True,
                     lods=((0.33, 0.6), (0.1, 0.25)), max_tex=4096)
# TRELLIS : forme remaillée à 1536 (image_to_3d --remesh 1536 --smooth 5) ; vu de près, le détail compte (retour du 19/10) ;
# niveaux de détail : 300 k dessous, 100 k à l'approche, 30 k de loin (gué : 63 i/s avec 300 k partout)
racine = None if (statues is not None or ARCH_VARIANT == "deux") else import_glb("racine/trellis2-s42", "/Game/Assets/Racine", 30000)
if ARCH_VARIANT == "deux":
    loc, _ = oriented(am["t"], 0.0, 0.0, 0.0)
    base_yaw = -pose_a["heading_deg"] - 90.0
    across = unreal.MathLibrary.get_forward_vector(unreal.Rotator(0, 0, base_yaw))
    arch_h = ARCH_WIDTH_CM * 0.485
    for side, (off, rot) in ARCH_FIGURES.items():
        fig = import_glb(f"arche-statues-{side}/trellis2-s42", f"/Game/Assets/ArcheStatues_{side}", 120000, smooth=True)
        if fig is None:
            continue
        a_ = place_model(fig, f"GB_ArcheStatues_{side}", loc + across * (off * ARCH_WIDTH_CM), base_yaw + rot, (None, None, arch_h),
                         -ARCH_WATERLINE * arch_h, f"ArcheStatues_{side}", sculpt=ARCH_SCULPT)
        fb = a_.get_actor_bounds(False)
        a_.add_actor_world_offset(unreal.Vector(loc.x + across.x * off * ARCH_WIDTH_CM - fb[0].x, loc.y + across.y * off * ARCH_WIDTH_CM - fb[0].y, 0.0), False, False)
    for a_ in actors.get_all_level_actors():
        if a_.get_actor_label() == "GB_ArcheRacines":
            actors.destroy_actor(a_)
if statues is not None:
    loc, _ = oriented(am["t"], 0.0, 0.0, 0.0)
    sb = statues.get_bounding_box()
    arch_h = ARCH_WIDTH_CM * (sb.max.z - sb.min.z) / (sb.max.x - sb.min.x)
    arch = place_model(statues, "GB_ArcheStatues", loc, -pose_a["heading_deg"] - 90.0, (ARCH_WIDTH_CM, None, None),
                       -ARCH_WATERLINE * arch_h, f"ArcheStatues_{ARCH_VARIANT}", moss=ARCH_MOSS or ARCH_VARIANT == "hunyuan21",
                       proj=projection("arche-statues") if (ARCH_PROJECTION or ARCH_VARIANT == "hunyuan21") else None, sculpt=ARCH_SCULPT,
                       fallback_tex=look_texture("tex-roche"))
    arch.add_actor_world_offset(arch.get_actor_forward_vector() * (-ARCH_HOLE_SHIFT * ARCH_WIDTH_CM), False, False)
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
# berge droite depuis le 19/10 au soir (à gauche, la barque regardait de l'autre côté et on ne la reconnaissait pas) ;
# HEAD_SIDE : 1 = gauche, -1 = droite
HEAD_T, HEAD_SIDE, HEAD_SIDE_M, HEAD_H_CM = 165.0, -1, 1.0, 1250.0
HEAD_TOWARD_DEG = 35.0       # visage tourné vers l'amont : il regarde la barque qui arrive (on le découvre en approchant)
tete = import_glb(model_dir("tete-couchee"), "/Game/Assets/TeteCouchee", 50000, smooth=True, max_tex=4096)
if tete is not None:
    ph_ = pose_at(HEAD_T)
    loc, _ = oriented(HEAD_T, 0.0, HEAD_SIDE * (ph_["width_m"] / 2 + HEAD_SIDE_M), 0.8)
    hb = tete.get_bounding_box()
    hs = HEAD_H_CM / max(hb.max.x - hb.min.x, hb.max.y - hb.min.y, hb.max.z - hb.min.z)
    # le modèle importé a le visage vers le haut (+Z) : roulis 90° → visage vers +Y (la rivière, vue de la rive gauche),
    # tangage 90° → axe menton-front horizontal (tête couchée sur la joue) ; puis le cap de la rivière. Trouvé en
    # comparant les orientations depuis la barque (19/10).
    # cap trouvé par essais depuis la barque (19/10) : berge gauche +35°, berge droite +185° (visage de profil vers l'amont)
    hrot = unreal.Rotator(90.0, -90.0, ue_yaw(ph_["heading_deg"]) + (HEAD_TOWARD_DEG if HEAD_SIDE > 0 else 185.0))   # crâne vers l'amont, cou (creux) vers l'aval
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
# Essai de simulation d'eau (20/10, Niagara Fluids « Shallow Water ») : seulement pour l'APK d'essai (BARQUE_ESSAI_EAU=1,
# package_android.py --variant exp). Modèle tel quel (sphères qui tournent et poussent l'eau), 8 m devant la barque au
# départ : savoir s'il tourne au Quest et ce qu'il coûte, avant de l'attacher à la barque.
if os.environ.get("BARQUE_ESSAI_EAU") == "1":
    _sw = eal.load_asset("/NiagaraFluids/Templates/Liquid/2D/Systems/ShallowWater/Grid2D_SW_ParticleCollisions")
    if _sw is not None:
        _h0 = math.radians(start["heading_deg"])
        _swa = actors.spawn_actor_from_object(_sw, ue(start["x"] + 8 * math.cos(_h0), start["y"] + 8 * math.sin(_h0), 0.0))
        tag(_swa, "GB_EssaiEauSim")
        unreal.log("Essai Niagara Fluids : système Shallow Water placé devant la barque")
# La séquence (animatic.py) référence les acteurs du niveau, qui viennent d'être recréés : la régénérer aussitôt,
# sinon ses pistes pointent vers des acteurs disparus (barque immobile, créatures figées).
import runpy  # noqa: E402
runpy.run_path(os.path.join(ROOT, "pipeline", "unreal", "scripts", "animatic.py"), run_name="__main__")
unreal.log(f"Greybox : {MAP} construit ({len(MESHES)} maillages)")
