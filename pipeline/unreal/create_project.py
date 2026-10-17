"""Crée ou met à jour le projet Unreal (Unreal/Barque.uproject) et sa configuration, depuis zéro.

    python pipeline/unreal/create_project.py

Projet sans code C++ (pas de compilation). Le script est propriétaire des fichiers qu'il écrit : toute
modification de réglage se fait ici, pas dans l'éditeur. Idempotent : n'écrit que ce qui change.

Réglages : cible Quest 3 (OpenXR, Vulkan, rendu mobile forward, multiview, MSAA 4×, pas de HDR mobile)
et PC VR (forward shading, instanced stereo, MSAA) ; éclairage statique autorisé, Lumen / ombres virtuelles
coupés ; serveur MCP d'Unreal démarré automatiquement avec l'éditeur.
"""
import json
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import CONFIG, ROOT, project  # noqa: E402

PLUGINS = [
    "PythonScriptPlugin", "EditorScriptingUtilities",       # pilotage par script
    "ModelContextProtocol",                                  # MCP natif (exploration)
    # Jeux d'outils exposés par le MCP (sans eux, il ne propose que la gestion des AgentSkills)
    "EditorToolset", "PCGToolset", "NiagaraToolsets", "ConfigSettingsToolset",
    "OpenXR",                                                # Quest 3 et PC VR
    "MediaPlate", "ElectraPlayer",                           # sphère vidéo 360 (lointain)
    "MovieRenderPipeline",                                   # rendus offline (360, fenêtre stéréo)
    "PCG", "GeometryScripting",                              # procédural
]

ENGINE_INI = """\
[/Script/HardwareTargeting.HardwareTargetingSettings]
TargetedHardwareClass=Mobile
AppliedTargetedHardwareClass=Mobile
DefaultGraphicsPerformance=Scalable
AppliedDefaultGraphicsPerformance=Scalable

[/Script/Engine.RendererSettings]
; PC VR : forward shading + MSAA, stéréo instanciée
r.ForwardShading=True
r.AntiAliasingMethod=3
r.MSAACount=4
vr.InstancedStereo=True
; Quest : rendu mobile forward, multiview, MSAA 4x, pas de HDR mobile
r.Mobile.ShadingPath=0
r.MobileHDR=False
r.Mobile.AntiAliasing=3
vr.MobileMultiView=True
; Éclairage baked, pas de Lumen ni d'ombres virtuelles
r.AllowStaticLighting=True
r.DynamicGlobalIlluminationMethod=0
r.ReflectionMethod=0
r.Shadow.Virtual.Enable=0
r.DefaultFeature.AutoExposure=False
r.DefaultFeature.MotionBlur=False
r.DefaultFeature.LensFlare=False
; ajouté par l'éditeur pour Meta Quest
r.Mobile.UseHWsRGBEncoding=True

[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12

[/Script/AndroidRuntimeSettings.AndroidRuntimeSettings]
PackageName=com.odoucet.barque
StoreVersion=1
MinSDKVersion=32
TargetSDKVersion=32
bPackageForMetaQuest=True
bRemoveOSIG=True
bSupportsVulkan=True
bBuildForES31=False
bBuildForArm64=True
bFullScreen=True
Orientation=Landscape
bPackageDataInsideApk=True
ExtraApplicationSettings=<meta-data android:name="com.oculus.supportedDevices" android:value="quest2|questpro|quest3|quest3s" />

; Serveur de fichiers Android (ajouté par l'éditeur ; jeton figé pour que le fichier reste stable)
[/Script/AndroidFileServerEditor.AndroidFileServerRuntimeSettings]
bEnablePlugin=True
bAllowNetworkConnection=True
SecurityToken=D21AE0084B500918132937AAAB75BF0D
bIncludeInShipping=False
bAllowExternalStartInShipping=False
bCompileAFSProject=False
bUseCompression=False
bLogFiles=False
bReportStats=False
ConnectionType=USBOnly
bUseManualIPAddress=False
ManualIPAddress=
"""

GAME_INI = """\
[/Script/EngineSettings.GeneralProjectSettings]
ProjectID={project_id}
ProjectName=La barque des lucioles
CompanyName=Olivier Doucet
Description=Balade VR contemplative, 4 min, Quest 3 et PC VR
"""

EDITOR_USER_INI = """\
[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
bAutoStartServer=True
ServerPortNumber=8000
ServerUrlPath=/mcp
"""


def engine_association():
    """Identifiant du moteur tel que Windows le connaît. Un moteur installé hors Epic Launcher est enregistré
    dans HKCU\\Software\\Epic Games\\Unreal Engine\\Builds sous un GUID : écrire « 5.8 » ferait alors
    proposer une conversion du projet à chaque ouverture."""
    root = CONFIG["unreal"]["root"].replace("\\", "/").rstrip("/").lower()
    ps = ("(Get-ItemProperty 'HKCU:\\Software\\Epic Games\\Unreal Engine\\Builds' -ErrorAction SilentlyContinue)"
          ".PSObject.Properties | Where-Object { $_.Name -like '{*' } | ForEach-Object { $_.Name + '|' + $_.Value }")
    try:
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    for line in out.splitlines():
        guid, _, path = line.strip().partition("|")
        if path.replace("\\", "/").rstrip("/").lower() == root:
            return guid
    return "5.8"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8", newline="\r\n")
    return True


def main():
    uproject = project()
    base = uproject.parent
    project_id = uuid.uuid5(uuid.NAMESPACE_URL, "github.com/odoucet/vr-demo").hex.upper()
    descriptor = {
        "FileVersion": 3,
        "EngineAssociation": engine_association(),
        "Category": "",
        "Description": "La barque des lucioles",
        "Plugins": [{"Name": p, "Enabled": True} for p in PLUGINS],
        "TargetPlatforms": ["Android", "Windows"],
    }
    changed = [str(p.relative_to(ROOT)) for p, t in [
        (uproject, json.dumps(descriptor, indent="\t") + "\n"),
        (base / "Config" / "DefaultEngine.ini", ENGINE_INI),
        (base / "Config" / "DefaultGame.ini", GAME_INI.format(project_id=project_id)),
        (base / "Config" / "DefaultEditorPerProjectUserSettings.ini", EDITOR_USER_INI),
    ] if write(p, t)]
    (base / "Content").mkdir(exist_ok=True)
    print("Écrits : " + (", ".join(changed) if changed else "rien (déjà à jour)"))


if __name__ == "__main__":
    main()
