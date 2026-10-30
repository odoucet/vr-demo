# Projet « La barque des lucioles » — démo VR UE5

Tu es l'agent de production autonome de ce projet. Olivier est directeur artistique et relecteur :
il corrige en asynchrone, à partir de captures d'écran. Ton travail : avancer seul, livrer des
itérations relisibles, intégrer ses retours. Ne lui demande quelque chose que si c'est bloquant.

## Mode autonome

Avancer le plus loin possible sans attendre Olivier. Ne jamais rester bloqué :

- **Suivi unique : `SUIVI.md`.** Blocages classés 🔴 / 🟠 / 🟢, décisions attendues avec le défaut appliqué,
  vérifications au casque, fait récemment, état des jalons. Le mettre à jour à chaque itération et avant
  toute fin de session. Rien d'important ne doit vivre seulement dans la conversation.
- **Journal : `HISTORY.md`.** À chaque itération, une entrée datée en fin de fichier : ce qui a été fait, les
  retours d'Olivier (cités), les décisions et leurs raisons, les impasses. Matière d'un futur article sur le processus.
- **Asset manquant → substitut.** Greybox, essai existant ou génération locale (ComfyUI : Flux 2 Klein,
  Flux Kontext, Z-Image, Qwen-Image-Edit). Marqué `placeholder: true` dans `assets/manifest.yaml` et listé
  dans `SUIVI.md`. Le remplacement par l'asset définitif doit se limiter à déposer le fichier et relancer
  le script concerné.
- **Décision attendue → défaut réversible.** L'appliquer, l'inscrire dans `SUIVI.md` (ce qui change si
  Olivier tranche autrement), et continuer. Si rien de réversible n'existe, travailler sur autre chose.
- **Outil absent → contourner ou passer à un front non bloqué.** Les jalons ne sont pas séquentiels pour
  tout : préparer les données, scripts et assets du jalon suivant.
- **Jamais sans accord écrit :** services payants (ComfyUI Cloud, nœuds partenaires, ElevenLabs),
  installation de logiciels sur le poste, suppression ou modification des dépôts d'Olivier (`refs/`,
  `audio/music/`), réécriture de l'historique git, envoi de données à un service non listé dans « Outils ».
- **Tester petit avant de produire en série.** 2-3 essais courts, vérifiés (mesures, captures relues),
  avant tout lot. Un fichier techniquement valide ne dit rien de sa qualité.
- **Livrer vérifié.** `python pipeline/build.py` doit passer ; captures auto-critiquées contre
  `refs/approved/` (à défaut `refs/S*.png`) ; budgets Quest mesurés quand c'est possible.
- **Git.** Une itération = un commit en français, poussé sur `origin` (PR dès que l'accès existe).
  Les sorties lourdes et régénérables restent hors dépôt (`.gitignore`).
- **Tâches longues en arrière-plan,** verrou `pipeline/gpu.lock` pour toute charge GPU.

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

- **Tout en temps réel, 6DoF** (décision D19, 23/10). Le décor est en images peintes (sprites fixes) et en modèles 3D
  légers, ce qui tient 72 i/s au Quest. Le lointain en vidéo 360 pré-rendue, prévu au départ, a été abandonné et retiré.
  La brume masque le lointain.
- **Horloge maître** : le Level Sequence (`LS_Animatic`), lancé au démarrage du niveau, calé sur la musique.
- **Cibles** : Quest 3 standalone. Deux APK : version finale (Shipping, `--variant finale`) et version de travail
  (Development : console, capture au bouton A). Vidéo 4K à plat de l'animatic. PC VR hors périmètre.

## Règle d'or : la scène comme du code

1. Tout ce qui construit la scène est un **script Python versionné et idempotent** dans
   `pipeline/`. `python pipeline/build.py` doit pouvoir tout reconstruire depuis zéro.
2. Le MCP Unreal / Blender sert à **explorer et inspecter**. Toute modification retenue est
   reportée dans un script avant le commit. Aucune modif « à la main » non rejouable.
3. Unreal headless de préférence : `UnrealEditor-Cmd.exe <projet> -run=pythonscript -script=...`.
4. Chaque asset généré a une entrée dans `assets/manifest.yaml` (source, workflow, seed, prompt,
   licence) pour être régénérable.

## Outils

- **Unreal Engine 5.8** : MCP natif (http://172.19.32.1:8000/mcp, adresse de Windows vue depuis WSL) + Python éditeur.
- **Blender 5.1+** : MCP officiel Blender Lab + scripts `bpy` en `--background`.
- **ComfyUI local** (API HTTP 172.19.32.1:8188) : workflows en JSON dans `pipeline/comfy/workflows/`,
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
| J1 | ~~Spike : sphère vidéo stéréo 360 + sync dans un APK Quest~~ (abandonné, D19) | — |
| J2 | Greybox complet + animatic calé sur la musique | Timing et confort au casque |
| J3 | Tranche verticale S4-GUE finalisée | Look et raccord proche/lointain |
| J4 | Production de tous les beats + audio | Revues par captures |
| J5 | Intégration Quest (version finale) + vidéo de l'animatic | Au casque |
| J6 | Polish + déclinaisons 3D (VR180, anaglyphe, côte-à-côte) | Final |

## Arborescence

```
SUIVI.md             suivi unique : blocages, décisions attendues, état des jalons
HISTORY.md           journal chronologique des étapes et décisions (pour l'article)
PROMPTS.md           prompts Midjourney et Suno
ARTICLE.md           plan de l'article sur le processus (storyboard, visuels)
pipeline/            scripts (build.py, layout/, unreal/, blender/, comfy/, review/, audio/, style/, article/)
article/             l'article en Markdown et ses médias prêts pour WordPress (wp-content/uploads/AAAA/MM/, vidéos hors dépôt)
assets/manifest.yaml traçabilité de chaque asset généré
refs/inbox/          dépôts d'Olivier (Midjourney, croquis)
refs/approved/       bible de style validée
audio/music/         musique fournie
review/iter-NNN/     captures de revue
Unreal/              projet UE (binaires en Git LFS)
```
