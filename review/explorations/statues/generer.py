"""Images de recherche (19/10) : statues géantes au bord de la rivière, idée d'Olivier « à débattre ensemble ».
Designs originaux, génération locale Z-Image Turbo, même style que le ciel. Pas des assets de la scène.

    python review/explorations/statues/generer.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
from comfy import client  # noqa: E402
from comfy.sky import STYLE  # noqa: E402
from gpu import gpu_lock  # noqa: E402

OUT = Path(__file__).parent
STYLE_NC = STYLE.replace(", towering cumulus clouds", "")
VARIANTS = {
    "gardiens": "view from a small wooden rowboat on a calm forest river at dusk, two colossal ancient stone guardians "
                "with simple rounded faces and closed eyes stand on either side of the river, half swallowed by moss, "
                "ferns and hanging roots, their stone hands resting on the riverbanks, fireflies, mist on the water",
    "tete": "view from a small wooden rowboat on a calm forest river at dusk, an enormous ancient stone head lying on "
            "its side in the river, covered in thick moss and small trees, the water flowing around it, glowing "
            "mushrooms in its carved features, soft golden light through the canopy",
    "arche-sculptee": "view from a small wooden rowboat drifting toward a giant ancient carved stone arch shaped like "
                      "two kneeling figures whose raised arms meet above a forest river, overgrown with moss, vines "
                      "and flowers, birds circling, warm dusk light",
}


def main():
    with gpu_lock("explorations-statues"):
        for i, (name, scene) in enumerate(VARIANTS.items()):
            dest = OUT / f"{name}.png"
            if dest.exists():
                continue
            wf = client.load_workflow("z_image_turbo_t2i.json")
            wf["27"]["inputs"]["text"] = f"{scene}, {STYLE_NC}"
            wf["3"]["inputs"]["seed"] = 300 + i
            wf["13"]["inputs"]["width"], wf["13"]["inputs"]["height"] = 1344, 768
            wf["9"]["inputs"]["filename_prefix"] = f"barque/explorations/{name}"
            entry = client.wait(client.submit(wf), timeout=900)
            client.download(client.output_files(entry, "9", "images")[0], dest)
            print(dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
