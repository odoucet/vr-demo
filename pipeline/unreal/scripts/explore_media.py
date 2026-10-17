"""Exploration (lecture seule) : API nécessaires à la scène de test J1 (média, séquence, niveau)."""
import unreal


def props(cls, keywords=("",)):
    if cls is None:
        return "ABSENT"
    names = [n for n in dir(cls) if not n.startswith("_") and not n.startswith("get_editor") and n not in ("cast", "static_class")]
    return ", ".join(n for n in names if any(k in n.lower() for k in keywords))


unreal.log("MovieSceneMediaSection : " + props(unreal.MovieSceneMediaSection, ["media", "sound", "player", "texture", "loop", "offset", "source"]))
unreal.log("LevelSequenceActor : " + props(unreal.LevelSequenceActor, ["play", "sequence", "auto"]))
unreal.log("MovieSceneSequencePlaybackSettings : " + props(getattr(unreal, "MovieSceneSequencePlaybackSettings", None), ["auto", "loop", "play", "hide", "pause"]))
unreal.log("LevelEditorSubsystem : " + props(unreal.LevelEditorSubsystem, ["level", "save", "load", "new"]))
unreal.log("MediaSoundComponent : " + props(unreal.MediaSoundComponent, ["player", "channel", "media"]))
unreal.log("Fabriques : " + ", ".join(n for n in dir(unreal) if n.endswith("FactoryNew") and any(k in n for k in ("Media", "Material", "LevelSequence", "Blueprint"))))
unreal.log("Custom : " + props(unreal.MaterialExpressionCustom, ["code", "output", "input"]))
unreal.log("Visibilité : " + str([n for n in dir(unreal) if "VisibilityTrack" in n]))
