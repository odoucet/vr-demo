# Article — plan de travail (v2, 30/10)

> **Rédigé le 30/10** (plan validé par Olivier) : `article/la-barque-des-lucioles.md`, médias web dans
> `article/wp-content/uploads/2026/10/`, mode d'emploi dans `article/LISEZMOI.md`. Ce plan reste la trace des choix.

Deuxième passe : l'axe donné par Olivier le 30/10 (§1), l'intro reformulée (§2), le plan revu en **storyboard** (§3) :
chaque partie liste sa matière et ses visuels, et les visuels qui existent déjà sont affichés ici (aperçu Markdown de
VS Code : `Ctrl+Shift+V`). Trois prototypes de visuels ont été produits pour valider la charte avant la série (§4.6).
Première passe (23/10, quatre angles) : `git show d9901bc:ARTICLE.md`.

Légende des visuels : 📐 schéma à dessiner · 📊 graphique calculé depuis le dépôt · 🖼 capture du dépôt ·
🎬 vidéo remontée depuis les animatics · 🎙 à fournir par Olivier · ✅ produit.

---

## 1. L'axe (Olivier, 30/10)

> « Avec l'énorme amélioration des IA ces derniers mois, et la multiplication des MCP (Unreal Engine, Comfy ...) j'ai
> voulu savoir à quel point une IA pouvait être autonome pour réaliser une petite démo VR assez simple. Sur ce projet,
> mon objectif a donc été de pousser son autonomie au max pour réaliser une démo VR non interactive qui tournerait sur
> mon casque Quest. Audio IA, assets IA ... Qu'est ce qu'il est possible de faire en octobre 2026 ? Et qu'est ce que
> j'ai appris sur l'Unreal Engine (que je ne maitrise pas du tout, si ce n'est côté gamer) ? Voici un tour d'horizon
> détaillé. »

Trois questions, qui deviennent la colonne vertébrale de l'article. Réponses courtes **provisoires** (à valider,
elles fixent la conclusion) :

| | Question | Réponse courte provisoire |
|---|---|---|
| **Q1** | Jusqu'où une IA peut-elle être autonome sur une démo VR ? | Très loin pour tout ce qui se voit sur un écran ou se mesure : code, scène, compilation, installation dans le casque, mesures de fluidité, de jour comme de nuit. Pas au-delà du casque : le relief, l'échelle, le confort et le goût sont restés humains, et l'agent a compensé en outillant son relecteur. |
| **Q2** | Audio IA, assets IA : que peut-on faire en octobre 2026 ? | Images 2D générées en local : excellentes et décisives (les arbres peints). 3D depuis une image : bonnes silhouettes, détail lissé. Musique : locale décevante, Suno excellente. Sons : banque CC0 vérifiée par des mesures, pas de génération. Simulation d'eau toute faite : décevante. |
| **Q3** | Qu'est-ce que j'ai appris d'Unreal, en partant de zéro ? | Un Quest n'est pas un petit PC ; un moteur se pilote en Python ; une image peinte vaut mieux qu'un maillage pauvre ; tout se mesure, à condition de vérifier ce qu'on mesure. |

**Ce que ça change par rapport au plan du 23/10**

- L'angle recommandé alors, « l'agent qui ne pouvait pas mettre le casque », devient **la limite de Q1** : un
  chapitre fort, plus l'axe entier.
- L'« annexe technique » devient **le chapitre Q3**, écrit à ta voix et construit sur tes propres questions de joueur,
  citées dans le journal (« Ça devait pas être un filtre de rendu UE ? », « c'est vraiment une limite du casque ? »).
- **Narrateur : toi, à la première personne.** L'agent est cité (commits, journal), il ne signe pas.
- **Format : un grand article** (~7 500 mots, ~40 visuels). Les trois questions donnent un découpage naturel en trois
  épisodes si la plateforme s'y prête (A7).
- **Graphique d'abord** : chaque partie s'ouvre sur un visuel ; une vidéo ou une animation tous les ~1 000 mots.

---

## 2. L'intro, reformulée

**Version proposée** (~210 mots, à ta voix) :

> Ces derniers mois, les IA ont fait un bond, et les MCP se sont multipliés : Unreal Engine a désormais le sien,
> ComfyUI et Blender aussi. Sur le papier, une IA peut donc piloter seule les outils d'un studio de jeu vidéo. J'ai
> voulu savoir ce que ça donne en vrai : à quel point une IA peut-elle être autonome pour réaliser une petite démo VR ?
>
> Le terrain d'essai est volontairement simple : une balade de quatre minutes, sans interaction, assis dans une barque
> qui dérive sur une rivière au crépuscule, dans un style de dessin animé, sur mon casque Quest 3. La règle : pousser
> l'autonomie au maximum. L'IA (Claude Code) écrit le code, génère les images et la 3D, choisit les sons, construit la
> scène dans Unreal, compile l'application, l'installe dans le casque et mesure sa fluidité. Moi, je fournis quelques
> images de référence et la musique, je mets le casque, et je dis ce qui ne va pas.
>
> Six jours plus tard, la balade tourne à 72 images par seconde dans le casque. Entre-temps : audio IA, assets IA,
> agents… qu'est-ce qu'il est possible de faire en octobre 2026 ? Et qu'est-ce que j'ai appris d'Unreal Engine, que je
> ne connaissais que côté joueur ? Voici un tour d'horizon détaillé, images et vidéos à l'appui.

**Chapô court** (~50 mots, pour les réseaux ou l'en-tête) :

> Six jours, une IA, un casque Quest 3 : j'ai demandé à Claude Code de construire seule une balade VR peinte, de la
> première ligne de code à l'application installée dans le casque. Ce qu'elle a su faire, ce qu'elle n'a pas pu faire,
> et ce que j'ai appris d'Unreal en la regardant travailler.

**Titres** (recommandé en premier) :

1. **« Une IA peut-elle faire une démo VR toute seule ? »** — *Six jours avec Claude Code, Unreal Engine et un Quest 3*
2. « Jusqu'où une IA peut-elle aller seule ? Une démo VR en six jours »
3. « J'ai confié ma démo VR à une IA : ce qui marche en octobre 2026 »
4. « La barque des lucioles : une démo VR construite par une IA, regardée par un humain »

Points à vérifier dans l'intro : « les MCP se sont multipliés » reste ton constat de départ ; dans les faits, le MCP
d'Unreal a servi à **explorer**, et tout le reste est passé par des scripts (§3.3, partie 3). C'est un des
enseignements de l'article, l'intro peut le laisser venir.

---

## 3. Le plan, partie par partie

### Chemin de fer

| # | Partie | Mots | Visuel d'ouverture | Autres visuels |
|---|---|---|---|---|
| 0 | Ouverture | 400 | 🎬 V01 bande-annonce | 🖼 C01 image héros |
| 1 | Le terrain d'essai | 800 | 📐 S01 l'atelier ✅ | 📐 S02 la partition, S03 la carte |
| 2 | Six jours en accéléré | 500 | 📊 G01 les commits ✅ | 🎬 V02 le pont en sept versions ✅, V04 time-lapse casque |
| 3 | Q1 — L'autonomie, jusqu'où ? | 1 800 | 📐 S04 une itération | 📐 S05, S06 · 🖼 C06, C10 · 🎙 V09 |
| 4 | Q2 — Assets et audio IA | 1 800 | 🖼 C05 les arbres A/B/C | 📐 S07, S08, S09 · 🖼 C07, C11-C16 · 📊 G04 · 🎬 V06, V07 |
| 5 | Q3 — Unreal vu par un joueur | 1 500 | 🎬 V08 le décor vu de dehors | 📐 S10, S11 · 📊 G02, G03 · 🖼 C08, C17, C18 · 🎬 V05 |
| 6 | Bilan | 800 | 🖼 C02 → C09 le grand avant/après | 🎬 V03 volet · 📊 G05 les chiffres |

★ = force narrative de l'anecdote (★ à ★★★), reprise du relevé du 23/10. Les dates renvoient à `HISTORY.md`.

### 0. Ouverture (~400 mots)

- **Message** : le résultat d'abord, puis la question (intro du §2), puis le contrat : l'agent fait, tu regardes.
- **Matière** : la démo en deux phrases ; « Claude Code, avec Claude Opus 5.5 » (les 134 commits sont co-signés) ; le
  poste (un PC, une RTX 3090, un Quest 3 en USB).

| ID | Visuel | Source | État |
|---|---|---|---|
| 🎬 V01 | Bande-annonce 45-60 s, 4K → 1080p, musique : brume du départ, roseaux, lueur de la bête sous l'eau, pont, passage sous les statues, envol des lucioles, créature devant la lune, héron | `review/iter-064/animatic-hd.mp4` : 0:08-0:14, 0:28-0:34, 1:06-1:12, 1:44-1:50, 2:08-2:16, 2:40-2:46, 3:02-3:08, 3:40-3:52 | à monter (`montage.py`) |
| 🖼 C01 | Image héros : le héron posé sur la barque, les lucioles, l'arbre de l'île | image 4K de `iter-064` à 3:45, ou capture casque `iter-067/casque/232s.jpg` | à extraire |

<img src="review/iter-064/planche-animatic-hd.jpg" width="49%"> <img src="review/iter-067/planche-casque.jpg" width="37%">

*Le rendu 4K du 23/10 (à gauche) et la vue réelle du casque (à droite) aux mêmes instants : réservoirs pour C01 et V01.*

### 1. Le terrain d'essai (~800 mots)

- **Message** : ce qu'on a demandé à l'IA, avec quels outils, sous quelles règles.
- **Matière**
  - La démo : 4 min assis dans une barque, sept beats calés sur « Luminous Wonder » (Suno), fin à 4:00.
  - Les règles de `CLAUDE.md`, la « fiche de poste » de l'agent (encadré) : mode autonome et défauts réversibles,
    la scène comme du code, tester petit avant de produire en série, jamais de service payant ni d'installation sans
    accord écrit, créatures originales. Le mode autonome a été ajouté le premier soir (17/10, 18 h 41).
  - Les outils et les MCP : le MCP natif d'Unreal 5.8 n'exposait d'abord que la gestion de « skills » ; il a fallu
    activer ses jeux d'outils (17/10). Il a servi à regarder (inspecter, capturer la vue) ; tout ce qui modifie la
    scène passe par un script (Python à distance dans l'éditeur, ou sans fenêtre). ComfyUI est piloté par son API
    HTTP (workflows JSON), Blender sans interface, le casque par adb.
  - Le poste : Windows + WSL2, RTX 3090 partagée par Unreal, ComfyUI et Blender (une charge lourde à la fois, verrou).
- **🎙 À toi** : pourquoi ce projet-là ; le `CLAUDE.md` initial (143 lignes) : écrit seul ou avec une IA ?

| ID | Visuel | Source | État |
|---|---|---|---|
| 📐 S01 | **L'atelier : qui pilote quoi** — la conversation pour les demandes et les retours, les fichiers pour la mémoire écrite ; un canal par outil (MCP pour explorer, Python pour construire) ; les deux rejoignent le casque par des chemins différents | `pipeline/article/schemas/atelier.html` | ✅ prototype |
| 📐 S02 | **La partition** : les sept beats sur la forme d'onde de la musique, une vignette par beat, les repères sonores des créatures | `pipeline/sequencer.yaml`, `audio/music/Luminous Wonder.flac`, images de `iter-064` ; base : `review/music/structure.png` | à dessiner |
| 📐 S03 | **La carte de la balade** : la rivière vue de dessus, 239 m à 1 m/s, les beats, les créatures, une vignette par lieu | `pipeline/layout/`, base : `review/layout/carte.png` | à redessiner |
| 🖼 C02b | Extrait de `CLAUDE.md` (les règles d'or), composé proprement plutôt qu'en capture d'écran | `CLAUDE.md` | à composer |

<img src="article/wp-content/uploads/2026/10/barque-03-atelier.png" width="80%">

<img src="review/music/structure.png" width="49%"> <img src="review/layout/carte.png" width="44%">

*S01 tel que produit ; en dessous, les bases techniques de S02 et S03 (lisibles par l'agent, pas encore par un lecteur).*

### 2. Six jours en accéléré (~500 mots)

- **Message** : l'arc complet avant les zooms thématiques ; le lecteur voit la démo se construire.
- **Matière** (les pivots, dans l'ordre) : « C'est long et c'est moche » (17/10, 30 musiques ACE-Step) → greybox
  jouable au casque le premier soir → « Je ne vois pas le rendu dessin animé » (18/10) → la bataille des 72 Hz →
  « le truc le plus moche ce sont les arbres » → l'APK A/B/C → la forêt peinte (19/10, 0 h 38) → le pont, « waouh » →
  l'eau refaite → Niagara, « c'est très moche » → tangage, bête sous l'eau, bouton A → version finale (23/10, 11 h 45).
  Les mandats d'autonomie : 8 h (« repenser la scène complète »), 6 h sans casque, « tu as 20 h devant toi ».

| ID | Visuel | Source | État |
|---|---|---|---|
| 📊 G01 | **Six jours, 134 commits** : commits par heure, la nuit en bandes, les moments-clés au-dessus | `git log` + `HISTORY.md` → `pipeline/article/graphiques.py` | ✅ prototype |
| 🎬 V02 | **Le même passage, sept versions** : la barque avance sans coupure de 1:38 à 2:20 pendant que le décor change de version toutes les 6 s (19/10 11 h 50 → 23/10), date et changement incrustés, frise des six jours | 7 animatics, `pipeline/article/montages.yaml` | ✅ prototype (42 s) |
| 🖼 C20 | Les 19 animatics au même instant (1:45), en planche | les 19 `animatic*.mp4` | à produire (`montage.py`) |
| 🎬 V04 | Time-lapse des captures casque aux onze mêmes instants, iter-012 → iter-069, fondu enchaîné | `review/iter-0NN/casque/{030s…232s}.jpg` | à monter |

<img src="article/wp-content/uploads/2026/10/barque-05-commits.png" width="80%">

<img src="article/wp-content/uploads/2026/10/barque-20-pont-versions.jpg" width="80%">

*G01 et la planche fixe de V02. La vidéo : `article/wp-content/uploads/2026/10/barque-06-pont-versions.mp4` (hors
dépôt, régénérable).*

### 3. Q1 — L'autonomie, jusqu'où ? (~1 800 mots)

**3.1 Ce qui rend l'autonomie possible** — les règles comptent autant que le modèle.

- ★★★ « C'est long et c'est moche » : 30 musiques générées sans en écouter une, le premier jour. Naissance de la règle
  « tester petit avant de produire en série » (17/10).
- ★★ Le défaut réversible : D1 à D20, chaque décision attendue reçoit un défaut appliqué et noté ; l'agent n'attend
  jamais. Le tableau des décisions de `SUIVI.md` se montre tel quel.
- ★★ La scène comme du code : 58 scripts, `build.py` reconstruit tout ; empreintes pour ne rien réécrire inutilement
  (sinon le dépôt LFS gonflait à chaque construction, 18/10).
- ★★ L'enquête avant la correction (18/10 soir) : cinq symptômes, cinq causes, consignées avant de toucher au code.
- ★ Le journal pour l'article : `HISTORY.md` ouvert le 19/10 à ta demande, « pour un article sur le processus ».

**3.2 Ce qu'elle a fait seule** — les chiffres (§5), les nuits (G01), les mandats (8 h, 6 h, 20 h) ; ce que tu as fait
pendant ce temps.

**3.3 Les MCP en vrai** — le MCP regarde, le script construit. Le MCP d'Unreal a servi à explorer et capturer la vue ;
les modifications passent par du Python versionné, rejouable par `build.py`. ComfyUI : API HTTP et workflows JSON ;
Blender : `bpy` sans fenêtre ; le casque : adb. Raison : un geste fait par MCP ne se rejoue pas, un script si
(règle d'or n° 2). C'est une réponse nuancée à ton point de départ « la multiplication des MCP ».

**3.4 L'IA qui ne pouvait pas mettre le casque** — cœur de la limite. L'agent voit les captures et les rendus PC ; il
lui manque le relief, l'échelle, le mouvement de la tête, le confort, le son.

- ★★★ La mesure trompeuse : le « 72 i/s » annoncé venait d'un casque posé qui regardait le ciel ; droit devant, 62.
  Depuis : capture de la vue du casque avant toute mesure (18/10 soir).
- ★★★ Ce que l'écran cache : sprites qui tournent avec la tête (« trop bizarre »), bandes verticales parce que les
  plans se croisent différemment pour chaque œil, ellipse de l'ancienne barque sous la nouvelle coque, eau qui passe
  dans la barque — invisibles en capture, flagrants au casque.
- ★★ Piloter un casque à distance : boîte système passée au clavier par adb (« flèche bas puis validation »), chaque
  pas contrôlé par une capture ; casque qui perd son suivi dans la pièce sombre ; mesures relancées toutes les 30 min.
- ★★ Chiffrer sans casque : estimateur de triangles par caméra de revue, animatic comme référence du look, extraits
  courts pour juger un mouvement.
- ★★ Le bouton A : « j'ai essayé de faire des screenshots mais pas très pratique » → un raccourci de capture daté par
  l'instant de la balade ; première capture → la bande de lisière de 160 m, trouvée en sept rendus par dichotomie
  après plusieurs fausses pistes. Leçon : « une capture datée vaut mieux qu'une description ». L'agent outille son
  relecteur, pas seulement lui-même.

**3.5 Ce qui reste humain** — le goût (« le truc le plus moche ce sont les arbres », « l'eau, c'est clairement ce qui
fait pas fini »), les idées de mise en scène (le pont venu du Seigneur des Anneaux, le héron, le tangage), le
périmètre (« ne fais rien de plus », « tout noter sans corriger »), les accords (installations, téléchargements), le
corps (redémarrer le casque, lui rendre la lumière). ★★ « J'ai enfin compris ce qui me choquait : leurs animations
sont synchronisées » (troupeau, 20/10) : un défaut que seul un œil humain a nommé.

| ID | Visuel | Source | État |
|---|---|---|---|
| 📐 S04 | **Une itération** : script → construction → captures → auto-critique → commit ; les retours d'Olivier entrent par `SUIVI.md` ; la branche « décision attendue → défaut réversible » | `CLAUDE.md`, `SUIVI.md` | à dessiner |
| 📐 S05 | **Les sens de l'agent** : ce qu'il perçoit, par quel instrument (captures adb, compteur d'images, Whisper, spectres, estimateur de triangles, rendus par dichotomie), ce qui reste à Olivier (relief, échelle, confort, oreille) | `HISTORY.md` | à dessiner |
| 📐 S06 | **Qui a fait quoi** : tâches × agent / Olivier / outils IA | `HISTORY.md`, `assets/manifest.yaml` | à dessiner |
| 🖼 C06 | Ce que « voit » un casque posé sur le bureau : horizon de travers, intérieur de la barque | `review/iter-026/planche-casque.jpg` | existe |
| 🖼 C10 | La capture au bouton A d'Olivier (aplat vert vu par la tranche, à droite) | `review/casque-A/20261023/A-0118.2s.jpg` | existe |
| 🖼 C04b | Tableau des décisions de `SUIVI.md` (D1-D20), composé | `SUIVI.md` | à composer |
| 🎬 V09 | La vraie vue du casque, tête qui bouge (scrcpy ou enregistreur du Quest) | 🎙 | à fournir |
| 🎬 V10 | L'agent au travail, en accéléré : une itération filmée (terminal + éditeur) | 🎙 à enregistrer ensemble | à faire |

<img src="review/iter-026/planche-casque.jpg" width="49%"> <img src="review/casque-A/20261023/A-0118.2s.jpg" width="29%">

*Gauche : le casque posé sur le bureau, vu par l'agent. Droite : la capture au bouton A qui a mené au bug de la bande
de lisière.*

### 4. Q2 — Assets et audio IA : ce qui marche en octobre 2026 (~1 800 mots)

**4.1 Les images peintes, la grande réussite** — ★★★ le pivot du projet, en une nuit : « le truc le plus moche ce sont
les arbres » (18/10, 20 h 40) → un APK où la forêt change toutes les 12 s (A arbres 3D, B arbres peints, C touffes) →
« les arbres peints ça rend vachement bien ! » → mandat de 8 h → ~7 800 images peintes posées, 72 i/s (19/10, 0 h 38).
Une image peinte de 2 triangles, générée dans le style, rend mieux qu'un arbre 3D de 2 700 triangles : c'est aussi la
technique des décors d'animation. Les ratés : détourage visible, plaques de sol peintes, nuages dans les images,
répétitions (« la texture des arbres sur la gauche se répétait beaucoup trop souvent »), la moitié des arbres éclairés
du mauvais côté après un retournement d'images.

**4.2 Ce que l'humain apporte encore** — les images de référence (Midjourney) et la cohérence de style ; la mousse
d'Olivier comme référence de toutes les textures ; `PROMPTS.md` : jamais de nom de studio ni d'artiste.

**4.3 De l'image à la 3D** — TRELLIS.2 et Pixal3D comparés sur 7 assets (17/10), chacun gagne sur des objets
différents ; Hunyuan3D 2.1 plus sculpté mais sans texture. ★★★ Le pont : ton idée (« la fameuse descente en barque du
Seigneur des Anneaux […] à débattre ensemble »), trois concepts originaux générés en local, ton image Midjourney, la
3D, la projection, puis ★★ « Ta vue 3D sur fond gris est très belle, c'est pas du tout ce que je vois dans le jeu » :
deux bugs d'import présents depuis le début (§5). ★★ « est-ce le Quest qui impose la limite, ou nous qui nous mettons
des limites absurdes ? » — un peu des deux : le workflow d'exemple remaillait à 768 avec 20 passes de lissage.
Reconstructions de 27 min tant que la mémoire du GPU était partagée avec l'éditeur, ~3 min ensuite.

**4.4 La musique** — ACE-Step en local : « Y'a pas vraiment de mélodie et après 15 s on dirait des loops qui se
répètent », puis, après un prompt réécrit, « ça fait son midi, ça sature dans les aigus » (17/10) ; Suno :
« Luminous Wonder » et ses 10 stems, spatialisés en 12 sources autour de la barque (piano devant à droite, basses sous
la barque, cordes derrière).

**4.5 Les sons, choisis sans oreilles** — ★★★ Freesound CC0, choisis par mesures : une voix anglaise détectée par
Whisper dans l'ambiance du lac ; ton « on croit entendre une voiture qui démarre », localisée par l'agent à la part de
basses fréquences de chaque demi-seconde (33 s après le début de l'enregistrement : l'ambiance est coupée avant) ; les
cris du héron validés par enveloppe et spectre, « validation à l'oreille laissée à Olivier ». Un repère sonore 2-3 s
avant chaque créature, venu de sa direction.

**4.6 Le verdict** (tableau de l'article)

| Domaine | Outil | Où | Verdict |
|---|---|---|---|
| Décors peints (sprites) | Z-Image Turbo + BiRefNet | local | ★★★ cohérent, rapide, décisif |
| Images de référence | Midjourney | Olivier, abonnement | ★★★ |
| Textures, vues manquantes | Qwen-Image-Edit | local | ★★ (moins belles que Midjourney) |
| 3D depuis une image | TRELLIS.2, Pixal3D, Hunyuan3D 2.1 | local | ★★ silhouettes justes, détail lissé |
| Musique | ACE-Step / Suno | local / Olivier, abonnement | ★ / ★★★ |
| Sons | Freesound CC0 + Whisper, spectres | API gratuite + local | ★★ par mesures, pas de génération |
| Relief estimé | Depth Anything | local | ✗ sur des images « cartoon » |
| Simulation d'eau | Niagara Fluids | Unreal | ✗ « c'est très moche » |
| Code, scène, build | Claude Code (Claude Opus 5.5) | Anthropic (cloud) | ★★★ |

| ID | Visuel | Source | État |
|---|---|---|---|
| 🖼 C05 | **L'APK A/B/C au casque** : la même forêt en arbres 3D, arbres peints, touffes (étiquette à la proue) | `review/iter-022/planche-casque.jpg` | existe |
| 🖼 C07 | Les familles d'images peintes | `review/iter-030/planche-sprites.jpg` | existe |
| 📐 S07 | **La chaîne des images peintes**, avec les vraies étapes d'un arbre : prompt → image brute → masque → image détourée → posée dans la scène (orientation, vent, relief) | `assets/textures/sprites/arbres/arbres_0_brut.png`, `_masque.png`, `.png` (intermédiaires hors dépôt, présents en local) | à dessiner |
| 🖼 C11 | Les trois concepts de statues générés en local ⚠ style (§7) | `review/explorations/statues/planche.jpg` | existe |
| 🖼 C12 | Ton image Midjourney du pont | `refs/inbox/arche-statues.png` | existe |
| 🖼 C13 | TRELLIS.2 contre Hunyuan3D 2.1 sur le pont ⚠ licence (§7) | `review/explorations/pont/trellis_vs_hunyuan.jpg` | existe |
| 🖼 C14 | Le pont, de la 3D à la vue de la barque | `review/explorations/pont/v01_v08.jpg` | existe |
| 🖼 C15 | La barque : ton image, Pixal3D, TRELLIS.2 | `review/3d/comparaison.jpg` | existe |
| 🖼 C16 | Référence contre résultat : tes images de concept (S2, S7) à côté du rendu au même endroit | `refs/S2-PONTON.png`, `refs/S7-LAC.png` + images de `iter-064` | à composer |
| 📐 S08 | **La chaîne image → 3D** et l'endroit où se perd le détail (remaillage 768/20 passes → 1536/5, Nanite, plafond de texture) | `HISTORY.md` 19/10 | à dessiner |
| 📐 S09 | **Le son autour de la barque** : les 12 sources des stems vues de dessus, les repères sonores des créatures | `pipeline/audio/stems.yaml`, `soundscape.yaml` | à dessiner |
| 📊 G04 | **Écouter sans oreilles** : spectrogramme de l'ambiance du lac, part des basses par demi-seconde, le grondement à 33 s, la coupe | `audio/sfx/amb-lac-nuit.ogg`, `soundscape.yaml` | à calculer |
| 🎬 V06 | **Le héron et son cri** : 3:33-3:52, forme d'onde incrustée, le cri qui précède l'oiseau | `iter-064` | à monter |
| 🎬 V07 | Les modèles 3D en vue tournante (barque, pont, troupeau, créatures) | 28 modèles dans `assets/3d/` (hors dépôt), Blender | à rendre (GPU) |

<img src="review/iter-022/planche-casque.jpg" width="40%"> <img src="review/iter-030/planche-sprites.jpg" width="21%"> <img src="review/3d/comparaison.jpg" width="34%">

<img src="refs/inbox/arche-statues.png" width="31%"> <img src="review/explorations/pont/trellis_vs_hunyuan.jpg" width="31%"> <img src="review/explorations/pont/v01_v08.jpg" width="35%">

*La forêt A/B/C au casque, les familles d'images peintes, la barque en 3D ; puis le pont : ton image, deux
reconstructions, la 3D vue depuis la barque.*

### 5. Q3 — Unreal Engine vu par un joueur (~1 500 mots)

Construit sur **tes questions** du journal, chacune suivie de ce qu'elle t'a appris. Ton regard de joueur est le fil
(🎙 à toi : ce qui t'a surpris, ce que tu croyais avant).

1. ★★★ **« Ça devait pas être un filtre de rendu UE ? »** (18/10) — pas de post-traitement possible sur Quest (rendu
   mobile sans HDR) : le look peint passe dans les matériaux (deux tons, liseré de contre-jour).
2. ★★★ **« surpris par le manque de polygones […] c'est vraiment une limite du casque ? »** (18/10) — le budget du
   Quest, les essais A/B en direct : cacher les maillages fait gagner 8 ms, baisser la résolution à 60 % seulement
   0,34 ms (`review/perf/ab-20261018-1422.txt`). La scène était limitée par la géométrie, pas par les pixels.
3. ★★ **« une version adaptative ? UE gère ça non ? »** (19/10) — oui : les niveaux de détail (l'arche à 300 k /
   100 k / 30 k triangles), mais pas Nanite, qui faisait afficher au Quest un maillage de repli au dixième.
4. ★★★ **« les sprites qui bougent/tournent quand on bouge ou tourne la tête, c'est trop bizarre »** (19/10) — imposteurs,
   billboards : un plan par œil, et pourquoi les plans sont désormais orientés une fois pour toutes, au placement.
5. ★★ **« Ton souci c'est que l'eau reste une surface plane »** (20/10) — pas de lecture de profondeur dans l'eau au
   Quest : ce sont les objets immergés qui s'éteignent ; les rides orientées devenaient des rayons quand on tournait
   la tête (« effet pluie ») ; sillage de Kelvin né à l'étrave ; Niagara Fluids essayé : « c'est très moche ».
6. ★ **« Je suis derrière le bateau »** (18/10) — l'origine VR dépend de la zone de jeu du casque : recentrage au
   lancement.
7. ★★ **« je n'ai pas vu de fort tangage quand la bête remonte »** (23/10) — la caméra ne roule jamais (règle de
   confort) : c'est la barque qui bouge sous le spectateur, 4° imperceptibles, puis 9°, puis 18°.
8. ★ **Ce que l'éditeur ne montre pas** — brume jamais rendue au casque avant le 18/10 au soir, shaders en 16 bits qui
   pixellisaient le ciel, matériaux gris faute de déclarer l'instanciation, profil de textures du Quest 3 hérité d'un
   Android moyen, scène qui « se construit petit à petit » au premier lancement (shaders).
9. ★ **Un moteur se pilote en Python** — projet créé par script, réglages reportés dans le code, Movie Render Queue
   pour les vidéos, deux APK : l'appli de travail passe de 719 à 414 Mo une fois retirée la vidéo de test du spike 360,
   que le moteur embarquait d'office ; la finale pèse 369 Mo.
10. **Encadré glossaire** : draw call, triangle, LOD, Nanite, rendu forward, post-traitement, MSAA, billboard,
    World Position Offset, shader, APK Development / Shipping.

| ID | Visuel | Source | État |
|---|---|---|---|
| 🎬 V08 | **Le décor vu de dehors** : une caméra qui s'élève au-dessus de la rivière et révèle que les arbres sont des plans peints | rendu Unreal (Movie Render Queue, caméra ajoutée par script) | à rendre (GPU, éditeur) |
| 🖼 C08 | Le décor vu de l'extérieur, depuis l'éditeur | `review/iter-030/tour-editeur.jpg` | existe |
| 🖼 C17 | Rendu PC (filtre peinture) contre vue du casque, même jour | image de `iter-031` à 0:30 + `review/iter-049/casque/030s.jpg` | à composer |
| 🖼 C03 | Le look peint arrive dans les matériaux (18/10) | `review/iter-008/planche.jpg` | existe |
| 🖼 C04 | Arbres 3D « boules » au casque (18/10) | `review/iter-012/planche-casque.jpg` | existe |
| 📊 G02 | **De 49 à 72 i/s** : ce que chaque levier a fait gagner, mesuré au casque | `review/perf/ab-*.txt`, `greybox-*.txt` | à calculer |
| 📊 G03 | Fluidité de la version finale, beat par beat | `review/perf/finale-20261023-1112.txt` | à calculer |
| 📐 S10 | **Plans face à l'œil contre plans fixes** (vue de dessus, deux yeux) : d'où viennent les bandes verticales | `HISTORY.md` 18/10 nuit, 19/10 | à dessiner |
| 📐 S11 | **L'eau sans profondeur** : la lecture qu'on ne peut pas faire, et l'inversion | `HISTORY.md` 18/10 soir | à dessiner |
| 🎬 V05 | **L'eau, avant / après** : écran partagé au même instant, rides orientées contre réseau sans direction | `iter-051` et `iter-054`, 1:00-1:12 | à monter |
| 🖼 C18 | Le tangage à 18° vu du casque | `review/iter-068/casque/071s.jpg` | existe |

<img src="review/iter-008/planche.jpg" width="33%"> <img src="review/iter-012/planche-casque.jpg" width="25%"> <img src="review/iter-030/tour-editeur.jpg" width="38%">

*Le look peint du 18/10 (rendu PC), les arbres « boules » vus au casque le même jour, le décor vu de l'extérieur.*

### 6. Bilan (~800 mots)

- **Les trois réponses** (§1), en une phrase chacune, validées par toi.
- **Ce que l'agent a bien fait** : endurance, rigueur, outillage (de lui-même et de son relecteur), mémoire écrite.
  **Mal fait** : conclure trop vite sur une mesure, corriger un symptôme sans vérifier son étendue (la bande de lisière
  « corrigée » sur un seul anneau, les fleurs 3D restées du premier décor), raisonner sur l'aspect plutôt que sur une
  capture datée.
- **Le plan contre la réalité** : l'architecture prévue (proche en temps réel, lointain en vidéo 360 stéréo) n'a jamais
  servi ; les images peintes l'ont rendue inutile (D19, retirée le 23/10).
- **Les incidents**, en une ligne chacun : interface du Quest en boucle, éditeur planté, 2,4 Go de vidéos 4K poussées
  par erreur, historique réécrit et dépôt recréé (3,9 Go au lieu de ~7,3).
- **🎙 À toi** : temps passé, coût (abonnements, électricité), ce que ça change pour un créatif seul, ce qui manque
  encore (un agent qui « voit » en relief ?).

| ID | Visuel | Source | État |
|---|---|---|---|
| 🖼 C02 → C09 | **Le grand avant / après** : le greybox du premier soir contre la vue du casque du dernier jour | `review/iter-001/planche.jpg`, `review/iter-067/planche-casque.jpg` (ou `iter-069`) | existe, à mettre en regard |
| 🎬 V03 | **Volet avant / après** : un rideau qui balaie l'image, 19/10 matin d'un côté, 23/10 de l'autre, même instant | `iter-031` et `iter-064`, 0:20-0:40 | à monter |
| 📊 G05 | Les chiffres en tuiles (6 jours, 134 commits, 58 scripts, 186 captures casque, 72 i/s…) | §5 | à composer |

<img src="review/iter-001/planche.jpg" width="40%"> <img src="review/iter-067/planche-casque.jpg" width="38%">

*Premier soir (17/10, greybox) et dernier jour (23/10, vue du casque).*

---

## 4. Visuels : inventaire, charte, prototypes

### 4.1 Récapitulatif

| Type | Nombre | Produits | Méthode |
|---|---|---|---|
| 📐 Schémas | 11 (S01-S11) + 2 compositions | 1 | HTML/SVG versionnés, rendus en PNG (`pipeline/article/schemas.py`) |
| 📊 Graphiques | 5 (G01-G05) | 1 | calculés depuis le dépôt (`pipeline/article/graphiques.py`) |
| 🖼 Captures | ~20 | ~14 existent | `review/`, `refs/` ; compositions par script |
| 🎬 Vidéos | 10 (V01-V10) | 1 | remontées depuis les 19 animatics (`pipeline/article/montage.py`, définitions dans `montages.yaml`) ; V07-V08 à rendre ; V09-V10 avec toi |

Tout visuel est régénérable par un script du dépôt, comme la scène : déposer une meilleure source et relancer suffit.

### 4.2 Réserves de matière

- **19 animatics de 3 min 59** (16 en 720p du 19 au 20/10, 3 en 4K des 21 et 23/10) : même trajectoire de caméra,
  donc tout instant se compare d'une version à l'autre, au cadrage près. Hors dépôt, sur le disque.
- **186 captures du casque** (iter-012 → iter-069) dont onze instants fixes repris aux passes complètes (30, 62, 76,
  100, 112, 140, 165, 181, 196, 214, 232 s : iter-012, iter-019, iter-067), et 3 captures au bouton A.
- **Planches de revue** iter-001 → iter-058 (18 caméras), explorations du pont (11 versions), statues, comparatifs 3D.
- **Images d'Olivier** : `refs/` (concepts de beats, assets, textures, ciels), `refs/inbox/` (pont, tête, arbre de l'île).
- **Intermédiaires des images peintes** (brut, masque, final) et **28 modèles 3D**, hors dépôt mais présents en local.
- **Mesures** : `review/perf/` (essais A/B, mesures par beat), `review/charge.txt` (triangles par caméra).

### 4.3 À fournir par toi (🎙)

- **Une captation au casque** (V09) : enregistreur du Quest ou scrcpy ; c'est la seule vraie vue VR de l'article.
- **Une photo de toi au casque**, ou du poste (humanise le récit).
- **L'enregistrement audio du test du 19/10 au soir**, s'il existe encore (citations de première main, « waouh »).
- **Ton regard de joueur** pour Q3, et les chiffres de A5 (temps, coût).
- **L'enregistrement d'une itération** (V10), à faire ensemble : je lance une itération, tu filmes l'écran.

### 4.4 Charte graphique (à valider sur les prototypes)

- **Fond papier** `#f6f1e7`, encre `#1d2b3a`, texte secondaire `#5b6670`, filets `#dcd4c4` : clair pour s'insérer dans
  une page web, chaud pour rappeler la peinture.
- **Couleurs de données** : bleu eau `#2a79a5` et orange lanterne `#c8742b`, tirés de la palette du projet ; validés
  (contraste ≥ 3:1 sur le papier, séparation correcte pour les trois daltonismes). Dans les schémas : l'agent en
  bleu nuit `#133e66`, Olivier en orange lanterne.
- **Police** : Segoe UI partout (schémas, graphiques, incrustations vidéo).
- **Formats** : schémas 1600×900 rendus ×2 ; graphiques 2600 px de large ; texte ≥ 19 px à pleine taille, pour rester
  lisible réduit à 800 px. Vidéos maîtres 1920×1080, 30 i/s ; versions web à encoder selon la plateforme (A7).
- **Légendes** : une phrase par visuel qui dit ce qu'il montre, en français courant.

### 4.5 Ce qui ne sera pas montré

- `review/iter-063/casque/008s.jpg` : la vue du casque en transparence montre la pièce d'Olivier et des photos
  personnelles. **Jamais publiée.**
- Les captures portant un **rectangle noir** (plusieurs dans iter-061, iter-063 et iter-068, à vérifier une à une) :
  écartées ou recadrées.
- `review/iter-067/casque/076s.jpg` : la flaque sur le plancher (corrigée le 23/10) ; lui préférer `iter-068/071s`.
- `review/bible/palettes.png` tel quel : il contient le concept provisoire S4 signalé pour originalité (§7).

### 4.6 Les prototypes de cette passe

| | Visuel | Fichier | Régénérer |
|---|---|---|---|
| 📐 S01 | L'atelier : qui pilote quoi | maître `builds/article/schemas/atelier.png` | `python pipeline/article/schemas.py atelier` |
| 📊 G01 | Six jours, 134 commits | maître `builds/article/graphiques/commits.png` | `python pipeline/article/graphiques.py commits` |
| 🎬 V02 | Le même passage, sept versions (42 s, avec la musique) + planche fixe | maître `builds/article/montages/pont-versions.mp4` | `python pipeline/article/montage.py pont-versions` |

Le 30/10, l'article a retenu 31 visuels (25 images, 6 vidéos ; liste : `pipeline/article/medias.yaml`). S02 et S03 sont
fusionnés dans le graphique « balade ». Écartés : C02b et C04b (les règles et les décisions sont dans le texte), C13
(licence de Hunyuan3D), C03, C04, C08 et C20 (redondants), G03, S11 (expliqué dans le texte). Non faits : V07, V08
(rendus GPU), V09, V10 et les photos (à fournir). Versions web : `python pipeline/article/export_web.py`.

Ce qu'ils testent : la charte (S01, G01), la lisibilité une fois réduits, et l'idée de montage propre à ce projet —
toutes les animatics partagent la même caméra, donc **la barque avance sans coupure pendant que le décor se construit**.
Le même procédé donnera V03 (volet), V05 (eau) et C20 (19 versions).

---

## 5. Le projet en chiffres (relevés le 30/10)

- **Six jours** de production : du 17/10 14 h (création du dépôt) au 23/10 11 h 45 (version finale), dont une pause de
  37 h sans commit (21-22/10).
- **134 commits**, tous co-signés Claude Opus 5.5 : 16 / 31 / 38 / 30 / 9 / 10 par jour.
- **58 scripts Python, 10 199 lignes** dans `pipeline/`, 12 fichiers de données YAML, 6 workflows ComfyUI.
- **69 itérations de revue** (66 dossiers), **186 captures du casque** + 3 au bouton A, **19 animatics** de 3 min 59
  (16 en 720p, 3 en 4K).
- **114 images peintes** finales (378 fichiers avec les intermédiaires), **~7 800** posées dans la scène (19/10, à
  recompter) ; **28 modèles 3D** générés pour 12 sujets.
- **57 assets** au manifeste, dont 34 encore marqués `placeholder` (substituts générés en local, tous en place).
- **17 sons** Freesound CC0 (6 ambiances, 4 repères de créatures, 7 effets) + la musique et ses 10 stems, en 12 sources.
- **Fluidité** : 49-61 i/s le 18/10 au matin → 72 i/s tenus ; version finale : 72,1 à 72,6 i/s de moyenne sur chaque
  beat (mesure casque posé, à confirmer casque porté).
- **Applis** : finale 369 Mo (Shipping), travail 414 Mo (719 avant le retrait de la vidéo de test du spike 360).
- **Matériel** : un PC Windows + WSL2, une RTX 3090 24 Go, un Quest 3 en USB. Côté agent, aucun service payant
  (hors Claude lui-même) ; côté Olivier : Midjourney et Suno.
- **Mandats d'autonomie** : 8 h (18/10, nuit), 6 h sans casque (19/10), « tu as 20 h devant toi » (19-20/10).
- **À compléter par toi** : heures réellement passées, nombre de sessions au casque, coût.

---

## 6. Ce qu'il te reste à trancher

| # | Question | État / recommandation |
|---|---|---|
| A1 | L'angle | ✅ **tranché le 30/10** : jusqu'où une IA peut-elle être autonome, en tour d'horizon (Q1-Q3) |
| A2 | Le format | ✅ **un grand article** ; en réserve, trois épisodes = trois questions |
| A3 | Le public | déduit de l'intro : public tech curieux d'IA, pas forcément développeur ; Q3 sert aussi les débutants en Unreal. À confirmer |
| A4 | La référence de style | ouvert. Le projet s'interdit les noms dans ses prompts, et deux images évoquent fortement un studio (§7). Reco : en parler franchement |
| A5 | Ce que tu dis de toi | partiel : Unreal « côté joueur » ✓ ; manquent le temps passé et le coût |
| A6 | La démo est-elle diffusée ? | ouvert : APK, vidéo publique, ou captures seulement ; conditionne la fin |
| A7 | **La plateforme** (nouveau) | blog, Medium, LinkedIn, site d'entreprise ? Décide vidéos intégrées (MP4, YouTube) ou animations courtes, largeur des images, découpage en épisodes |
| A8 | **Qui écrit le premier jet** (nouveau) | reco : moi, à ta voix, en marquant `[à toi]` ce que je ne peux pas écrire (le ressenti au casque, le regard de joueur) ; puis tu réécris |
| A9 | **La charte des visuels** (nouveau) | valider fond papier, couleurs, police et principe de montage sur les trois prototypes avant la série |

---

## 7. Points de vigilance

- **Style et originalité** : les créatures et designs sont originaux et les prompts n'ont jamais nommé de studio ni
  d'artiste. Mais une alerte a été consignée le 18/10 (concept provisoire S4 trop proche d'un film d'animation connu,
  gardé pour la palette : il figure dans `review/bible/palettes.png`), et la planche des statues évoque fortement un
  studio. Le Seigneur des Anneaux, lui, est une référence de mise en scène, à garder telle quelle.
- **Données à ne pas publier** : la pièce d'Olivier (§4.5), les adresses internes (`172.19.32.1`), les chemins du
  poste, la clé Freesound passée en conversation, le nom du compte Suno présent dans `assets/manifest.yaml`.
- **Licences, avant toute image publiée** : sons CC0 ; musique Suno (offre payante au moment de la génération selon le
  manifeste : droits d'usage commercial, à confirmer) ; images Midjourney (ton abonnement) ; modèles locaux à vérifier
  un par un (TRELLIS.2, Pixal3D, Z-Image, Qwen-Image-Edit, BiRefNet). **Hunyuan3D 2.1** : sa licence communautaire
  exclut certains territoires (l'Union européenne, si ma mémoire est bonne) ; à vérifier avant de montrer C13. Le
  modèle retenu dans la démo est TRELLIS.2.
- **Hachages de commit** : ceux que cite `HISTORY.md` avant le 21/10 sont ceux d'avant la réécriture de l'historique
  (l'itération 1 est `50292ef` dans le journal, `2e88607` aujourd'hui). Citer les hachages actuels.
- **Chiffres** : distinguer mesuré au casque / estimé / rendu PC ; la mesure finale a été prise casque posé. Le journal
  arrondit parfois : partir des fichiers bruts (résolution à 60 % : 0,34 ms dans `review/perf/ab-20261018-1422.txt`,
  0,6 ms dans `HISTORY.md`).
- **Ton** : « je » = toi ; les phrases de l'agent viennent de ses commits et du journal, citées comme telles.

## 8. Questions que les lecteurs poseront

- Combien de temps humain, combien de temps machine, combien ça a coûté ?
- Quelle part vient de toi ? (S06 y répond.) Avais-tu déjà fait de l'Unreal ou de la VR ? (Non : c'est l'axe.)
- Quel modèle ? (Claude Opus 5.5 dans Claude Code.) Les MCP, ça sert vraiment ? (3.3)
- L'IA a-t-elle triché ou inventé des résultats ? (La mesure du casque posé, rattrapée par la règle « vérifier ce
  qu'on mesure ».)
- Que se serait-il passé sans toi au casque ?
- Est-ce reproductible ? Le dépôt et le `CLAUDE.md` seront-ils publics ?
- Les créations générées sont-elles originales ? À qui appartiennent-elles ?

## 9. Prochaines étapes

1. **Toi** : valider l'axe et le chemin de fer (§3), les réponses provisoires (§1), A3-A9, la charte sur les
   prototypes (§4.6) ; fournir ce qui est marqué 🎙.
2. **Moi** : produire les visuels par lots, tous par script, après validation de la charte — d'abord ceux qui ne
   demandent que le disque (S02-S11, G02-G05, V01, V03-V06, C16, C17, C20), puis les rendus GPU (V07 turntables, V08
   vue de dehors).
3. **Moi** : premier jet de l'article à ta voix (A8), citations vérifiées contre `HISTORY.md` et les commits.
4. **Toi** : relecture, et ce que l'agent ne peut pas écrire : le ressenti au casque.
