"""Sonde exécutée dans Unreal : version, plugins actifs, accès au dépôt. Sert à valider la chaîne headless."""
import os

import unreal

root = os.environ.get("BARQUE_ROOT", "?")
unreal.log(f"BARQUE probe : moteur {unreal.SystemLibrary.get_engine_version()}")
unreal.log(f"BARQUE probe : projet {unreal.Paths.get_project_file_path()}")
unreal.log(f"BARQUE probe : dépôt {root} (river.json présent : {os.path.exists(os.path.join(root, 'pipeline', 'layout', 'river.json'))})")
# is_plugin_mounted ne voit que les plugins à contenu : on interroge la liste des plugins activés.
enabled = set(unreal.PluginBlueprintLibrary.get_enabled_plugin_names())
for name in ["PythonScriptPlugin", "OpenXR", "ModelContextProtocol", "MediaPlate", "PCG", "MovieRenderPipeline"]:
    unreal.log(f"BARQUE probe : plugin {name} : {'actif' if name in enabled else 'ABSENT'}")
