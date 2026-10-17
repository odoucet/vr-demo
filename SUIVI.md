# Suivi — La barque des lucioles

**Fichier unique de suivi.** Tenu par l'agent, lu par Olivier. Classé par criticité.
Mis à jour : 2026-10-18

Légende : 🔴 bloque un jalon, aucun contournement · 🟠 j'avance avec un contournement · 🟢 mineur

---

## ▶ Pour ton test au casque

Trois APK, installables côte à côte (noms de paquet distincts). Installation : glisser l'APK dans Meta Quest
Developer Hub, ou `Install_Barque-arm64.bat` dans le même dossier (Quest branché, débogage USB accepté).
Dans le casque : Bibliothèque → Sources inconnues.

1. **J1 — sphère vidéo 360 + synchro** : `builds/android/Barque-arm64.apk` (paquet `com.odoucet.barque`, 60 s).
   « AVANT » devant ; stéréo non inversée (« ŒIL GAUCHE » lisible de l'œil gauche seulement) ; repères à
   1,5 m / 3 m / 10 m / ∞ à ces distances ; cube rouge, flash blanc et bip simultanés ; fluidité. → **go / no-go J1**.
   **J1b — variante de repli** : `builds/android_j1b/Barque-arm64.apk` (paquet `com.odoucet.barque.j1b`). Même vidéo,
   affichée par un calque stéréo équirectangulaire composé par le casque (plus net, mais dessiné par-dessus la scène :
   le cube rouge est sans doute masqué ; synchro = flash blanc + bip). À tester surtout si J1 a un défaut de stéréo,
   et pour comparer la netteté des deux méthodes.
2. **J2 — greybox jouable** : `builds/android_greybox/Barque-arm64.apk` (paquet `com.odoucet.barque.greybox`, 4 min).
   Assis, regarde devant : la barque dérive seule, musique et ambiances. Juge : confort (vitesse, virages),
   échelle (barque, troupeau, arche, lune), hauteur des yeux, gêne de la lanterne (D11), timing sur la musique.
   Utilise la zone **stationnaire** du Quest et recentre la vue (appui long sur le bouton Meta) avant de lancer.
   Hauteur : le joueur est posé au niveau de l'eau, ta tête assise doit tomber vers 1,10 m (origine OpenXR « STAGE », au sol).
   Si tu es trop haut ou trop bas, dis-le-moi : c'est un réglage.
   Alternative sans APK : Quest Link + éditeur, niveau `Barque_Greybox`, Play → VR Preview.
3. Sans casque : `review/iter-006/animatic.mp4` (4 min, musique + ambiances) et `review/iter-006/planche.jpg`.

**Mesure de fréquence d'image (facultatif, 5 min)** : Quest branché en USB et casque porté, lance
`python pipeline/unreal/quest_perf.py --variant greybox` (ou dis-moi « Quest branché » et je la lance). L'APK
démarre, la télémétrie du casque est relevée pendant toute la balade, puis résumée par beat dans `review/perf/`
(FPS minimum, images perdues, charge GPU/CPU) : c'est la mesure des budgets Quest qui manque au jalon J2.
Sans câble, l'overlay de l'application OVR Metrics Tool (Store Meta, gratuite) donne la même information à l'œil.

Retours : dans ce fichier, en issue GitHub, ou en conversation (`ID-caméra : remarque [étiquette]`).

---

## Décisions attendues d'Olivier

Chaque décision a un **défaut réversible déjà appliqué** : je n'attends pas. Réponds dans ce fichier
(colonne « Ta décision »), en issue GitHub, ou en conversation.

| # | Décision | Défaut appliqué en attendant | Si tu changes | Ta décision |
|---|---|---|---|---|
| D1 | Image maîtresse `--sref` pour tout Midjourney | `S5-RACINES` | relancer les prompts concernés | |
| D2 | Coupure S3 / S4 | 1:38 (S3 54 s, S4 30 s) ; alternative 1:11 | modifier `pipeline/sequencer.yaml`, tout se recale | |
| D3 | Tracé de la rivière (`review/layout/carte.png`) | proposition actuelle, 240 m à 1 m/s | modifier `pipeline/layout/river.yaml` | |
| D4 | Échelles réelles | barque 3,5 m · abysses 15 m · troupeau 2,5 m au garrot · volante 40 m d'envergure · arche des racines 8 m au-dessus de l'eau | modifier les échelles, réimport | |
| D5 | Coque de la barque | tes nouvelles images (`refs/barque.png`, `refs/barque-top.png`, style peint) donnent de bons modèles : la vue 3/4 (Pixal3D) restitue perche, lanterne et corde ; la vue de dessus (TRELLIS.2) une coque complète avec ses bancs (`review/3d/comparaison.jpg`). Intégré au greybox : modèle TRELLIS.2 de la vue 3/4 (rend bien en scène). Multi-vues en attente : les vues générées en local (Qwen-Image-Edit, `pipeline/comfy/views.py`, 26 s/vue) sont des 3/4 tournés, pas les profils stricts qu'exige Pixal3D multi-vues | choisir l'une des variantes de `assets/3d/barque*` | |
| D6 | Livraison sans accès aux PR | un commit par itération sur `main`, captures dans `review/iter-NNN/`, résumé ici | passage aux PR dès que `gh` est connecté | |
| D7 | Sons Freesound (9 ambiances et bruitages, tous CC0) | un candidat retenu par besoin d'après titre et fiabilité, sans écoute : `audio/sfx/*.ogg` ; alternatives dans `audio/sfx/candidates/README.md` | `freesound.py pick <besoin> <id>` | |
| D8 | Cadrages des caméras de revue | `pipeline/review/cameras.yaml` actuel | éditer le YAML | |
| D11 | Lanterne de proue dans le champ de vision : vue depuis la place assise, elle est au centre, juste au-dessus des yeux, pendant toute la balade (`review/iter-002/`) | place assise reculée sur le banc arrière (-1,20 m) et lanterne en papier lumineux ; alternatives : perche déportée sur le côté, lanterne plus haute, ou spectateur assis de biais | régénérer l'asset barque ou déplacer la caméra (`greybox.py`) | |
| D9 | M'autoriser à installer Blender portable (sans droits admin, sur G:) | j'attends ; nettoyage des maillages via les nœuds ComfyUI en attendant | — | |

## 🔴 Bloquants

| # | Blocage | Bloque | Ce qu'il faut | Contournement en cours |
|---|---|---|---|---|

## 🟠 Importants (contournés)

| # | Manque | Contournement | Ce qui le lèverait |
|---|---|---|---|
| I1 | Images d'assets en style peint (en cours chez Olivier) | visuels provisoires générés en local, essais 3D actuels marqués `placeholder` | dépôt dans `refs/inbox/` sous l'identifiant de `PROMPTS.md` |
| I2 | Concepts S1, S3, S4 manquants | concepts provisoires générés en local (`assets/concepts/`, `pipeline/comfy/concepts.py`, prompts de PROMPTS.md) | génération Midjourney |
| I3 | Blender absent | nœuds de maillage ComfyUI (décimation, UV), import GLB dans UE | D9, ou installation par Olivier |
| I4 | Pas de création de PR (connecteur GitHub sans accès, `gh` non connecté) | D6 | `gh auth login`, ou installer l'application GitHub de Claude sur le dépôt |
| I5 | Musique en MP3 185 kb/s | MP3 utilisé tel quel | export WAV depuis Suno |
| I6 | Freesound : seuls les aperçus OGG sont accessibles sans OAuth | aperçus utilisés pour le prototype | connexion OAuth pour les originaux (au master) |

## 🟢 Mineurs

- **Originalité** : le concept provisoire S4 (`assets/concepts/S4-GUE.png`) montre des créatures façon sangliers moussus à défenses, trop proches d'un film d'animation connu ; il ne sert qu'à la palette, pas au design (ton troupeau aux oreilles tombantes reste la référence).

- Ciel provisoire : ce n'est pas un vrai équirectangulaire (horizon à 82 % de l'image, projeté sur la voûte) ; le ciel définitif viendra du rendu du lointain.

- 17/10 au soir : j'ai fait planter l'éditeur une fois (maillage sans UV, corrigé) ; la fenêtre du rapport de plantage Unreal peut être restée ouverte.
- L'animatic (exposition de la caméra) est plus clair que les captures de revue (exposition fixe) : à harmoniser avec l'éclairage définitif.
- Greybox très sombre (crépuscule sans exposition automatique) : lisible pour le timing, l'éclairage définitif viendra avec le look (J3).
- Roseaux : jaunâtres à contre-jour malgré un vert très sombre (lumière du soleil rasant sur des lames double face) ; à reprendre avec le matériau peint.

- Clé Freesound collée dans la conversation : risque faible, à régénérer si tu préfères.

## À vérifier au casque

- **J2 (greybox)** : échelle de la barque (3,5 m, franc-bord ~45 cm, place assise à 1,20 m derrière le centre), gêne de la lanterne de proue (D11), hauteur des yeux 1,10 m, confort de la dérive et des virages, lisibilité du passage sous la barque (S3), distance du troupeau (14 m, S4), passage sous l'arche (8 m, S5).

- **J1 (APK `builds/android/`)** : la vidéo s'affiche ; « AVANT » devant ; la stéréo n'est pas inversée (« ŒIL GAUCHE » ne doit être lu que de l'œil gauche) ; les repères 1,5 m / 3 m / 10 m / ∞ paraissent à ces distances ; le cube rouge clignote en même temps que le flash blanc et le bip ; fluidité (72 Hz) en 4096 px. Point technique incertain : sélection de l'œil (`ResolvedView.StereoPassIndex`) avec le multiview mobile.

- J1 : vidéos `assets/spike/test360_*` (orientation, stéréo, résolution maximale fluide, synchronisation).
- Confort du tracé : rotation maximale de 1,15 °/s, vitesse de 1 m/s.
- Échelles (D4) dès le greybox.

## Fait récemment

- **Mesure au casque prête** : `pipeline/unreal/quest_perf.py` lance l'APK par adb, relève la télémétrie VrApi (FPS, images perdues, GPU %, CPU %) et la résume par beat avec une courbe. Testé sur un journal simulé, en attente d'un Quest branché.
- **Ciel en 4096×2048** : le panorama retenu est agrandi par un modèle 4x (Remacri), puis réduit, avec le raccord gauche/droite préservé (`sky.py --upscale`). Les nuages sont nets et les aplats propres ; le ciel était flou en 2048 px.
- **Itération 6 (J2)** : brume par beat. La teinte est mesurée sur la bande d'horizon de chaque référence ; luminance et densité sont réglées par beat. Source unique : `pipeline/style/ambiance.json`, lue par Unreal et à reprendre telle quelle par le rendu offline du lointain (raccord). La séquence fond la brume sur 12 s à chaque beat : vraie brume au départ du ponton (S2), plans étagés ensuite. Roseaux procéduraux le long des berges en S2, avec une touffe qui frôle la barque à gauche (0:32-0:40) ; nénuphars en S3. Nuancier : `review/bible/brume.png`.
- **Captures de revue** : la capture attend deux images après le placement de la séquence. Avant, la brume animée affichée était celle de la caméra précédente.
- **Reconstruction idempotente** : `build.py` ne réécrit plus les sons, maillages, matériaux ni le ciel quand leur source n'a pas changé (empreintes en métadonnées). Seuls le niveau et la séquence sont régénérés, ce qui évite de gonfler le dépôt LFS. Les scènes de test J1/J1b ne sont relancées que si leur script ou leur vidéo change (`--force` pour les forcer).
- **Python à distance dans l'éditeur ouvert** : tous les scripts Unreal passent par l'éditeur s'il est ouvert, sinon en headless ; l'ancien blocage I7 est levé.
- **Bible de style (J0)** : palette par beat (7 beats) ; concepts provisoires S1/S3/S4 générés en local avec les prompts de PROMPTS.md.
- **Itération 5 (J2)** : eau à reflet du ciel peint + Fresnel (miroir à l'horizon, transparente vers le bas), sans réflexions temps réel (coût Quest faible) ; les berges ne s'y reflètent pas.
- **J1b** : variante de repli de J1 (calque stéréo équirectangulaire natif du Quest), APK prêt, pour éviter un aller-retour si la sphère à matériau échoue.
- **Itération 4 (J2)** : ciel peint provisoire généré en local (Z-Image Turbo, prompt « Ciel et lointain »), projeté sur la voûte, luminosité animée du crépuscule à la nuit ; lune plus brillante (la créature passe devant en silhouette).
- **Budget Quest** : scène greybox ramenée à ~165 k triangles (troupeau simplifié à 12 k triangles par animal à l'import, terrain en grille de 2 m) ; mesure réelle de la fréquence d'image à faire sur le casque.
- **Itération 3 (J2)** : envol des lucioles à la modulation (2:37,8 : nuage de 400 lucioles qui monte vers la trouée, substitut d'un futur Niagara) ; modèles 3D des créatures attachés aux blocs animés (abysses en émissif cyan, troupeau à mi-corps, créature volante dans le sens de son vol) ; caméra du joueur VR à 1,10 m sans casque.
- **APK greybox jouable** (`builds/android_greybox/`) : joueur VR assis dans la barque, séquence en lecture automatique.
- **Paysage sonore** : 12 sons Freesound CC0 (9 ambiances, 3 repères de créatures spatialisés) placés selon `pipeline/audio/soundscape.yaml`, normalisés ; mixés aussi dans l'animatic.
- **Itération 2 (J2)** : barque 3D intégrée (3,5 m, franc-bord ~45 cm), lumière de lanterne, lune et créature volante décalées de 15° à gauche pour ne pas être masquées par la lanterne, caméras de revue à la place assise.
- **Animatic J2** : `review/iter-001/animatic.mp4` (rendu Movie Render Queue en 50 s depuis le passage aux shaders SM6).
- **Itération 1 du greybox (J2)** : `review/iter-001/planche.jpg` — 18 caméras de revue (`pipeline/review/shoot.py`), niveau `Barque_Greybox`, séquence `LS_Animatic`.
- Barque régénérée en 3D depuis tes nouvelles images peintes (`review/3d/comparaison.jpg`).
- Premier APK Quest empaqueté sans erreur (`python pipeline/unreal/package_android.py`, 7 min 30).
- Scène de test J1 et script d'empaquetage Android (`pipeline/unreal/scripts/j1_spike.py`, `package_android.py`) ; scripts exécutés dans l'éditeur ouvert (Python à distance).
- Outils Android installés dans `G:\android\` (SDK, NDK r27c, JDK 21), validés par Unreal : `pipeline/unreal/setup_android.py`.
- MCP Unreal opérationnel : ~20 jeux d'outils (scène, acteurs, assets, matériaux, PCG, Niagara, journaux), capture du viewport (`pipeline/unreal/mcp.py capture`).
- Projet Unreal créé par script (Quest 3 + PC VR, MCP), exécution headless depuis WSL.
- 9 sons Freesound CC0 retenus provisoirement, tracés dans le manifeste.
- Vidéos de test J1 (4096/30, 5760/30, 4096/60), synchronisation par flash et bip.
- Tracé de la rivière et trajectoire de la barque, 18 caméras de revue, `pipeline/build.py`.
- Comparatif image → 3D TRELLIS.2 / Pixal3D sur 7 assets (`review/3d/`).
- Séquencier recalé sur « Luminous Wonder » ; prompts regroupés dans `PROMPTS.md`.

## État des jalons

| Jalon | État |
|---|---|
| J0 Bible de style | prompts prêts ; **palette par beat** (`review/bible/palettes.png`, `pipeline/style/palettes.yaml`) à partir de tes essais S2/S5/S6/S7 et de concepts provisoires S1/S3/S4 ; ciel peint provisoire ; attend tes images d'assets (I1) et le choix de l'image maîtresse (D1) |
| J1 Spike vidéo 360 + Quest | scène J1_Spike construite par script (sphère 360 stéréo + séquence + témoin de synchro), matériau validé dans l'éditeur ; **APK prêt : `builds/android/Barque-arm64.apk`** (485 Mo) ; attend le test au casque (go / no-go) |
| J2 Greybox + animatic | greybox construit par script (terrain, eau translucide, arche, forêt, lac, lune, blocs des créatures) ; séquence LS_Animatic calée sur la musique ; 18 captures et animatic vidéo avec musique ; **itération 6 : brume par beat, roseaux, nénuphars** ; eau qui reflète le ciel peint (itération 5), ciel peint (itération 4) (crépuscule → nuit) après les créatures 3D (itération 3) (abysses lumineuse, troupeau, créature volante) après la barque 3D en itération 2 (modèle TRELLIS.2 de ta vue 3/4, lanterne lumineuse, place assise sur le banc arrière) — `review/iter-006/planche.jpg` et `review/iter-006/animatic.mp4` ; à valider : timing et confort au casque |
| J3 à J6 | non commencés |
