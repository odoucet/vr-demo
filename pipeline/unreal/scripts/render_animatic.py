"""Lance le rendu Movie Render Queue de LS_Animatic (exécuté dans l'éditeur, voir pipeline/review/animatic.py).

Images JPEG 1280×720 dans le dossier donné par la variable BARQUE_FRAMES (chemin Windows). Rendu dans un
processus séparé (MoviePipelineNewProcessExecutor) : la session de jeu dans l'éditeur est fortement
ralentie quand sa fenêtre n'est pas au premier plan (~0,1 image/s mesuré). Ce script lance et rend la main.
"""
import builtins
import os

import unreal

frames_dir = os.environ.get("BARQUE_FRAMES") or os.path.join(os.environ["BARQUE_ROOT"], "builds", "animatic", "frames")
# BARQUE_HD=1 (21/10, demande d'Olivier : « une vidéo HD, tous les paramètres à fond, pour voir ce qui change du Quest ») :
# 3840×2160, 4 échantillons temporels × 2 spatiaux par image, qualité maximale (sg.* à 4), filtrage anisotrope 16, PNG
HD = os.environ.get("BARQUE_HD") == "1"
res = unreal.IntPoint(3840, 2160) if HD else unreal.IntPoint(1280, 720)

subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
queue = subsystem.get_queue()
queue.delete_all_jobs()
job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
job.job_name = "animatic"
job.sequence = unreal.SoftObjectPath("/Game/Sequences/LS_Animatic.LS_Animatic")
job.map = unreal.SoftObjectPath("/Game/Maps/Barque_Greybox.Barque_Greybox")
cfg = job.get_configuration()
out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_directory = unreal.DirectoryPath(frames_dir)
out.output_resolution = res
out.file_name_format = "{frame_number}"
out.zero_pad_frame_numbers = 5
if os.environ.get("BARQUE_RANGE"):         # extrait : "début,fin" en images (animatic.py --extrait)
    a, b = (int(x) for x in os.environ["BARQUE_RANGE"].split(","))
    out.use_custom_playback_range = True
    out.custom_start_frame, out.custom_end_frame = a, b
cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
if HD:
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.temporal_sample_count, aa.spatial_sample_count = 4, 2
    aa.override_anti_aliasing = True
    aa.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE        # le suréchantillonnage fait l'anticrénelage
    cv = cfg.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    for k, v in {"sg.TextureQuality": 4, "sg.ViewDistanceQuality": 4, "sg.EffectsQuality": 4, "sg.FoliageQuality": 4,
                 "r.MaxAnisotropy": 16, "r.Streaming.MipBias": 0, "r.Streaming.FullyLoadUsedTextures": 1,
                 "r.ViewDistanceScale": 3, "r.StaticMeshLODDistanceScale": 0.25}.items():
        cv.add_or_update_console_variable(k, float(v))
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
else:
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
executor = unreal.MoviePipelineNewProcessExecutor()
builtins.barque_mrq_executor = executor  # garde une référence pendant le rendu asynchrone
subsystem.render_queue_with_executor_instance(executor)
unreal.log(f"Rendu animatic lancé → {frames_dir}")
