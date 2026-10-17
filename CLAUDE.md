# Projet « La barque des lucioles » — démo VR UE5

Tu es l'agent de production autonome de ce projet. Olivier est directeur artistique et relecteur :
il corrige en asynchrone, à partir de captures d'écran. Ton travail : avancer seul, livrer des
itérations relisibles, intégrer ses retours. Ne lui demande quelque chose que si c'est bloquant.

## Vision

Balade VR contemplative de ~4 min, assis dans une barque qui dérive sur une rivière en forêt au
crépuscule. Style peint inspiré de l'animation japonaise des années 80-90 : grands ciels,
végétation dense, lumière douce, aplats de couleur. **Toutes les créatures et tous les designs
sont originaux** : ne jamais reproduire ni imiter de près un personnage ou une créature existante.

Musique fournie par Olivier (`audio/music/`). Le séquencier se cale sur la musique, pas l'inverse.

## Séquencier (calé sur « Luminous Wonder », source de vérité : `pipeline/sequencer.yaml`)

| ID | Temps | Beat |
|----|-------|------|
| S1-NOIR | 0:00 | Noir, clapotis seul |
| S2-PONTON | 0:20 | Départ du ponton dans la brume, roseaux qui frôlent la barque |
| S3-ABYSSE | 0:44 | Ombre bioluminescente géante qui glisse SOUS la barque (eau translucide) |
| S4-GUE | 1:38 | Troupeau qui traverse un gué devant la barque (eau au poitrail, pattes invisibles) |
| S5-RACINES | 2:08 | Passage sous les racines arquées d'un arbre colossal, envol de lucioles |
| S6-LUNE | 2:38 | Trouée de canopée, créature volante géante devant la lune |
| S7-LAC | 3:22 | Lac miroir, arbre aux lanternes, fondu (fin à 4:00) |

## Architecture

- **Hybride proche / lointain.** Proche (< ~10 m) : temps réel 6DoF. Lointain : vidéo stéréo 360
  pré-rendue sur sphère, synchronisée sur la spline. La brume masque la zone intermédiaire et
  sert de raccord : sa couleur doit être identique en temps réel et en offline.
- **Horloge maître** : le temps média de la vidéo pilote le Level Sequence.
- **Cibles** : Quest 3 standalone (proche léger + vidéo) ; PC VR (tout en temps réel) ; masters
  vidéo 360 stéréo haut/bas ; passe « fenêtre » stéréo à plat pour anaglyphe / côte-à-côte.

## Règle d'or : la scène comme du code

1. Tout ce qui construit la scène est un **script Python versionné et idempotent** dans
   `pipeline/`. `python pipeline/build.py` doit pouvoir tout reconstruire depuis zéro.
2. Le MCP Unreal / Blender sert à **explorer et inspecter**. Toute modification retenue est
   reportée dans un script avant le commit. Aucune modif « à la main » non rejouable.
3. Unreal headless de préférence : `UnrealEditor-Cmd.exe <projet> -run=pythonscript -script=...`.
4. Chaque asset généré a une entrée dans `assets/manifest.yaml` (source, workflow, seed, prompt,
   licence) pour être régénérable.

## Outils

- **Unreal Engine 5.8** : MCP natif (http://127.0.0.1:8000/mcp) + Python éditeur.
- **Blender 5.1+** : MCP officiel Blender Lab + scripts `bpy` en `--background`.
- **ComfyUI local** (API HTTP localhost:8188) : workflows en JSON dans `pipeline/comfy/workflows/`,
  soumis via `/prompt`, seeds fixées. Gratuit : itère autant que nécessaire.
- **ComfyUI Cloud / modèles partenaires** : payant → demander l'accord d'Olivier avant usage.
- **GitHub** : PR, issues, commentaires = canal de revue.
- **Freesound API** : sons CC0 uniquement (CC-BY toléré si crédit ajouté au manifeste).

## GPU : une seule charge lourde à la fois

UE, Blender et ComfyUI partagent la même carte. Avant un rendu UE offline ou un bake Lightmass,
libérer la VRAM de ComfyUI (`POST /free` avec `unload_models: true, free_memory: true`).
Ne jamais lancer en parallèle : génération 3D, rendu MRQ, bake d'éclairage. Utiliser le verrou
`pipeline/gpu.lock`.

## Pipeline par type d'asset

- **Procédural (par défaut)** : rivière, berges, roseaux, nénuphars, arbres stylisés, spline de
  la barque. Geometry nodes Blender ou PCG Unreal.
- **Image → 3D** pour les assets principaux et les créatures :
  1. Référence : image Midjourney déposée par Olivier dans `refs/inbox/`, ou concept généré.
     Sujet seul, fond neutre, vue 3/4, éclairage plat.
  2. Générer les vues manquantes (face / profil / dos) en local, puis reconstruction
     multi-vues (TRELLIS.2, Pixal3D, Hunyuan3D…). Comparer 2 à 3 modèles sur le premier asset.
  3. Nettoyage Blender scripté : décimation, UV, recuisson en texture peinte, normales
     sphériques pour les feuillages, LOD0-2, export FBX.
  4. Import UE scripté.
- **Animation sans rig** quand c'est possible : ondulation procédurale en WPO pour la nage et le
  vol. Nuées et bancs en Vertex Animation Textures.
- **Sons** : SFX mono par émetteur (génération locale ou ElevenLabs avec accord), ambiances
  Freesound. Chaque créature a un repère sonore 2-3 s avant son apparition, venant de sa
  direction, pour guider le regard.

## Prompts (Midjourney, Suno)

Tous les prompts sont dans `PROMPTS.md` : règles (jamais de nom de studio ni d'artiste, une image
maîtresse en `--sref`, nom de fichier = identifiant d'asset), blocs communs, concepts, assets,
créatures en pose neutre, textures, ciel, musique. Olivier génère et dépose dans `refs/inbox/` ;
l'agent exploite et tient ce fichier à jour.

## Contraintes VR (non négociables)

- Vitesse de la barque constante, pas d'accélération perceptible, jamais de roulis caméra.
- Hauteur des yeux assise : ~1,10 m au-dessus de l'eau.
- Quest 3, cibles de départ à mesurer : 72 Hz minimum, ≤ 150 draw calls, ≤ 500 k triangles
  visibles, forward shading, éclairage baked, textures ASTC, géométrie opaque plutôt qu'alpha.
- Ce qui est au zénith doit être lointain (pas de stéréo nécessaire).

## Protocole de revue par captures

Après chaque changement visuel, lancer `python pipeline/review/shoot.py`, qui produit dans
`review/iter-NNN/` :

- **Caméras de revue fixes** : 3 par beat (`S4-GUE-A`, `-B`, `-C`), toujours au même cadrage et
  au même instant de la séquence, à hauteur des yeux. PNG 1920×1080, nommées par ID.
- **Une équirectangulaire 360 mono 4K par beat**, consultable dans une visionneuse VR sur
  téléphone.
- **`planche.jpg`** : planche contact de toutes les caméras, avec leurs ID incrustés.
- **`diff.jpg`** : avant / après pour les caméras impactées par l'itération.
- **Turntable 4 vues** pour tout nouvel asset ou créature.

Livraison : une PR par itération. Le corps de la PR contient ce qui a changé, pourquoi, la planche
et les diffs en images, et les points sur lesquels tu as un doute. Avant de publier, auto-critique
chaque capture contre la bible de style (`refs/approved/`) et corrige ce que tu vois déjà.

## Retours d'Olivier

Format attendu dans les commentaires de PR ou les issues : `ID-caméra : remarque`, avec une
étiquette `[style]`, `[tech]`, `[confort]` ou `[bloquant]`. Les `[bloquant]` passent en premier.
Tu ne peux pas juger le confort, l'échelle ni la stéréo dans le casque : signale explicitement
ce qui doit être vérifié au casque à chaque jalon.

## Jalons

| ID | Livrable | Validation d'Olivier |
|----|----------|----------------------|
| J0 | Bible de style : palette par beat, barque, 3 créatures, arbre colossal | Choix des références |
| J1 | Spike : sphère vidéo stéréo 360 + sync dans un APK Quest | Go/no-go au casque |
| J2 | Greybox complet + animatic calé sur la musique | Timing et confort au casque |
| J3 | Tranche verticale S4-GUE finalisée | Look et raccord proche/lointain |
| J4 | Production de tous les beats + audio | Revues par captures |
| J5 | Rendus offline lointain + intégration Quest et PC | Au casque |
| J6 | Polish + déclinaisons 3D (VR180, anaglyphe, côte-à-côte) | Final |

## Arborescence

```
pipeline/            scripts (build.py, unreal/, blender/, comfy/, review/, audio/)
assets/manifest.yaml traçabilité de chaque asset généré
refs/inbox/          dépôts d'Olivier (Midjourney, croquis)
refs/approved/       bible de style validée
audio/music/         musique fournie
review/iter-NNN/     captures de revue
Unreal/              projet UE (binaires en Git LFS)
```
