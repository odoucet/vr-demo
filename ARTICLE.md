# Article — plan de travail

Première passe : inventaire de la matière, angles possibles, plan détaillé recommandé, visuels disponibles et à
produire, décisions à prendre. Sources balayées : `HISTORY.md`, `SUIVI.md`, `CLAUDE.md`, `PROMPTS.md`, les 132 commits,
`review/` (67 itérations), `refs/`, `assets/`, `pipeline/`.

---

## 1. Ce que tu dois trancher

| # | Question | Options | Ma recommandation |
|---|---|---|---|
| A1 | **L'angle** (détail en §3) | ① « L'agent qui ne pouvait pas mettre le casque » · ② « Directeur artistique d'une IA » · ③ « Le Quest n'est pas un petit PC » · ④ « La scène comme du code » | **①**, qui absorbe ② et ④ et garde ③ comme matière technique |
| A2 | **Format** | un grand article (~6 000 mots) · une série de 3 épisodes · article + annexe technique | **article principal + annexe technique** (ou billet séparé) pour les développeurs UE / Quest |
| A3 | **Public et support** | grand public curieux d'IA · développeurs (UE, VR) · créatifs / directeurs artistiques | grand public tech ; l'annexe sert les développeurs |
| A4 | **La référence de style** | nommer l'inspiration (film, studio) · rester sur « animation japonaise des années 80-90 » | voir §7 : le projet s'interdit les noms dans ses prompts ; l'article peut en parler, mais c'est un choix à faire en conscience |
| A5 | **Ce que tu veux dire de toi** | temps passé, compétences préalables (UE ? VR ?), coût (abonnement, électricité, tokens) | à fournir : c'est la première question des lecteurs (§8) |
| A6 | **La démo est-elle diffusée ?** | APK / vidéo publique · captures seulement | conditionne l'appel à l'action de la fin |

---

## 2. Le projet en chiffres (relevés le 23/10)

- **6 jours** de production, du 17/10 14 h (création du dépôt) au 23/10.
- **132 commits**, rédigés par l'agent en français ; 16 / 31 / 38 / 30 / 9 / 8 par jour : la courbe raconte elle-même
  l'emballement puis le polish.
- **58 scripts Python, ~10 200 lignes** dans `pipeline/` (layout, unreal, blender, comfy, audio, review, style) ;
  `python pipeline/build.py` reconstruit la scène depuis zéro.
- **67 itérations de revue** dans `review/iter-NNN/` : 337 PNG, 276 JPG, **19 animatics vidéo** (720p puis 4K,
  3 min 59 s chacun).
- **378 images peintes** (sprites) générées en local dans `assets/textures/sprites/`, ~7 800 posées dans la scène.
- **57 assets** tracés dans `assets/manifest.yaml` (34 encore marqués `placeholder`).
- **24 sons** (Freesound CC0) + la musique Suno et ses 10 stems spatialisés en 12 sources.
- **Matériel** : un PC Windows + WSL2, une RTX 3090, un Quest 3 branché en USB. Aucun service payant utilisé.
- **Performance** : de ~600 k triangles et 49-61 i/s à **72 i/s tenus** au Quest 3, mesurés par adb.
- **Durées d'autonomie demandées par Olivier** : 8 h (« repenser la scène complète »), 6 h sans casque, puis
  « je te rends la 3D, le casque et tout, tu as 20 h devant toi ».

À compléter par toi : heures réellement passées, nombre de sessions au casque, coût.

---

## 3. Les angles possibles

### ① « L'agent qui ne pouvait pas mettre le casque » — recommandé

**Thèse** : l'agent construit seul une expérience VR qu'il ne peut ni voir en stéréo, ni entendre, ni ressentir.
Tout le projet est l'histoire de la façon dont on comble ces sens manquants : par des instruments (captures adb,
mesures de fréquence, Whisper, spectres audio, estimateur de triangles, rendus par dichotomie) et par un humain qui
porte le casque et rapporte ce qu'il voit.

**Pourquoi c'est le plus fort** :
- c'est **inédit** : les récits « j'ai fait X avec une IA » parlent de ce que l'IA produit ; celui-ci parle de ce
  qu'elle ne perçoit pas, et de la division du travail qui en découle ;
- il est **riche en anecdotes concrètes** (§4) et chaque anecdote illustre la thèse ;
- il **englobe les autres** : la collaboration (②) devient « les yeux d'Olivier », la technique Quest (③) devient
  « ce que l'écran cache et que le casque révèle », la méthode (④) devient « les instruments de l'agent » ;
- il est **honnête** : il montre les ratés (le « 72 i/s » mesuré sur un casque posé qui regardait le ciel) sans en
  faire un réquisitoire.

**Phrase d'accroche possible** : « Pendant six jours, une IA a construit une balade en réalité virtuelle qu'elle n'a
jamais vue. »

**Risque** : survendre le côté « aveugle ». L'agent voit les captures et les rendus PC ; ce qui lui manque, c'est
la stéréo, l'échelle, le confort, le mouvement de la tête, le son. À formuler précisément.

### ② « Directeur artistique d'une IA »

**Thèse** : le rôle d'Olivier ressemble à celui d'un directeur artistique face à un studio : il ne touche à rien,
il regarde, il réagit en une phrase, et ses phrases réorientent le projet (« le truc le plus moche ce sont les
arbres », « l'eau, c'est clairement ce qui fait pas fini »).

**Atouts** : citations nombreuses et savoureuses, rapport humain / machine lisible par tous, réflexion sur le métier.
**Limite** : plus attendu ; sans les « sens manquants », ça devient un récit de gestion de projet.

### ③ « Le Quest n'est pas un petit PC »

**Thèse** : récit technique des contraintes du rendu mobile en VR et des parades trouvées (look peint dans les
matériaux faute de post-traitement, arbres en images peintes, eau sans lecture de profondeur, brume jamais rendue,
profil de textures hérité d'un Android moyen…).

**Atouts** : très utile aux développeurs UE / Quest, chiffres à l'appui (`review/perf/`).
**Limite** : public étroit ; l'IA passe au second plan. → **idéal comme annexe ou billet séparé.**

### ④ « La scène comme du code »

**Thèse** : la méthode transposable : tout est script idempotent, un fichier de suivi unique, des « défauts
réversibles » pour ne jamais attendre, tester petit avant de produire, captures datées. Ce sont les règles qui
rendent l'autonomie possible, plus que le modèle.

**Atouts** : utile à quiconque veut piloter un agent sur un projet long, au-delà du jeu vidéo.
**Limite** : abstrait sans les anecdotes. → **à distiller en encadrés** dans l'angle ①.

---

## 4. Points d'intérêt relevés (la matière)

Classés par thème, avec la source et la force narrative (★ à ★★★).

### Les sens manquants de l'agent (fil rouge de l'angle ①)

- ★★★ **Des sons choisis sans les entendre** : une voix anglaise détectée par Whisper dans l'ambiance du lac ;
  le « bruit de voiture » de la fin repéré à la part de basses fréquences de chaque demi-seconde ; les cris du héron
  validés par enveloppe et spectre, « validation à l'oreille laissée à Olivier ». (`HISTORY.md` 18/10 soir, 19/10,
  20/10)
- ★★★ **La mesure trompeuse** : le « 72 i/s » annoncé venait d'un casque posé qui regardait le ciel ; droit devant,
  62. Depuis : capture de la vue du casque avant toute mesure. (18/10 soir)
- ★★★ **Ce que l'écran cache** : sprites qui tournent avec la tête (« trop bizarre »), bandes verticales parce que les
  plans se croisent différemment pour chaque œil, ellipse de l'ancienne barque sous la nouvelle coque, eau qui passe
  dans la barque — invisibles en capture, flagrants au casque.
- ★★ **Piloter un casque à distance** : boîte système contournée au clavier par adb (« flèche bas puis validation »),
  chaque pas contrôlé par une capture ; casque qui perd son suivi dans la pièce sombre ; mesures relancées toutes les
  30 min en ne gardant que celles où le GPU travaille.
- ★★ **Le bouton A** : Olivier peine à montrer un défaut (« j'ai essayé de faire des screenshots mais pas très
  pratique ») ; l'agent lui fabrique un raccourci de capture daté par l'instant de la balade. Premier usage : trois
  captures qui mènent au bug de la bande de lisière de 160 m, trouvé en sept rendus par dichotomie. Leçon : « une
  capture datée vaut mieux qu'une description ».
- ★★ **Chiffrer sans casque** : estimateur de triangles par caméra de revue, animatic MRQ comme référence du look,
  extraits courts pour juger le mouvement.
- ★ **Le relief stéréo** : Depth Anything ne sait pas lire des images « cartoonisées » ; le relief est tiré de la
  silhouette peinte (profil de dôme puis parabolique).

### La collaboration et ses phrases-pivots

- ★★★ **« Le truc le plus moche ce sont les arbres »** → APK où la forêt change toutes les 12 s (A / B / C) → « les
  arbres peints ça rend vachement bien ! » → mandat de 8 h → scène repeuplée de ~7 800 sprites à 72 i/s. **Le pivot
  du projet**, en 24 h. (18/10 soir → 19/10 nuit)
- ★★★ **Le pont aux statues** : une idée d'Olivier venue du Seigneur des Anneaux (« à débattre ensemble »), reprise
  en trois concepts originaux par l'agent, choisie par Olivier, passée en 3D → « waouh » au casque. Du souvenir de
  cinéma au moment fort de la démo. (18/10 → 19/10 soir)
- ★★ **« Ta vue 3D sur fond gris est très belle, c'est pas du tout ce que je vois dans le jeu »** → deux bugs d'import
  présents depuis le début (Nanite, réimports qui gardaient l'ancienne texture). « La projection, astucieuse,
  compensait un bug qu'on n'avait pas vu. »
- ★★ **« J'ai enfin compris ce qui me choquait : leurs animations sont synchronisées »** : le troupeau, réglé par une
  fonction non sauvegardée avec le niveau.
- ★★ **« Ton souci c'est que l'eau reste une surface plane »** → piste Still Wakes the Deep → Niagara Fluids essayé :
  « c'est très moche » → retour à l'eau calculée. Une piste prometteuse abandonnée, mesurée au casque.
- ★ **Le héron de la fin**, idée d'Olivier pour un final « un peu morne ».
- ★ **Les consignes de retenue** : « ne fais rien de plus », « tout noter sans corriger », casque « hors limites » :
  l'humain règle aussi le périmètre de l'autonomie.

### La méthode qui rend l'autonomie possible (encadrés)

- ★★★ **« C'est long et c'est moche »** : 30 musiques ACE-Step générées sans en écouter une, le premier jour. Naissance
  de la règle « tester petit avant de produire en série ». Excellent ouverture ou premier échec.
- ★★ **Défaut réversible** : D1 à D19, chaque décision attendue a un défaut appliqué et noté ; l'agent n'attend jamais.
  Tableau de `SUIVI.md` montrable tel quel.
- ★★ **La scène comme du code** : 58 scripts, reconstruction complète, empreintes pour ne rien réécrire inutilement
  (sinon le dépôt LFS gonflait à chaque build).
- ★★ **L'enquête avant la correction** (18/10 soir) : cinq symptômes, cinq causes, consignées avant de toucher au code.
- ★ **Le journal pour l'article** : `HISTORY.md` a été ouvert à la demande d'Olivier « pour un article sur le
  processus » dès le 19/10 — l'article est prévu depuis le jour 3.

### Les découvertes techniques (annexe ou angle ③)

- ★★★ **Pas de post-traitement sur Quest** : « Sur tes screenshots je ne vois pas le rendu dessin animé. Ça devait pas
  être un filtre de rendu UE ? » → le look peint passe dans les matériaux (`M_Peint`, deux tons, liseré).
- ★★★ **Une image peinte vaut mieux qu'un maillage pauvre** : arbres 3D « jeu des années 90 » vs plan peint de
  2 triangles généré dans le style. C'est aussi la technique des décors d'animation.
- ★★ **Limité par la géométrie, pas par les pixels** : tout cacher = −8 ms, résolution à 60 % = −0,3 ms
  (`review/perf/ab-20261018-1422.txt`). Les essais A/B en direct par adb.
- ★★ **L'eau, enfin comprise** : les rides orientées devenaient des rayons convergents quand on tournait la tête
  (effet « pluie ») ; un réseau sans direction laisse la perspective faire le travail. Sillage de Kelvin né à
  l'étrave.
- ★★ **Le détail perdu avant le Quest** : le workflow d'exemple ComfyUI remaillait TRELLIS à 768 avec 20 passes de
  lissage ; « est-ce le Quest qui impose la limite, ou nous qui nous mettons des limites absurdes ? » — un peu des
  deux.
- ★ **Le profil Quest 3 d'Unreal** hérite d'un Android moyen : textures un niveau en dessous, pas d'anisotrope.
- ★ **Brume jamais rendue au casque** pendant les premières 24 h ; fondu de séquence inopérant (sphère noire autour
  des yeux) ; scène qui « se construit petit à petit » au premier lancement (shaders).
- ★ **Tangage sans roulis caméra** : la barque bouge sous le spectateur ; 4° imperceptibles, 9°, puis 18°.

### Ce qui n'a pas marché (à assumer)

- ★★ **L'architecture initiale abandonnée** : le plan hybride (proche temps réel + lointain en vidéo 360 stéréo) est
  devenu inutile grâce aux sprites ; J1 n'a jamais été validé au casque (D19). Un bon passage sur « le plan vs la
  réalité ».
- ★★ **Bugs « corrigés » qui revenaient** : la bande de lisière corrigée sur un seul des deux anneaux ; les fleurs 3D
  fixes, restes du tout premier décor ; le vent à 5 mm de balancement (erreur d'unité).
- ★ **Incidents** : interface du Quest en boucle après un réglage de débogage, éditeur planté, 2,4 Go de vidéos 4K
  poussées par erreur, historique réécrit et dépôt recréé (3,9 Go au lieu de 7,3).
- ★ **Image → 3D** : bonne silhouette, détail lissé ; Hunyuan3D plus sculpté mais sans texture ; reconstructions à
  30 min tant que la VRAM était partagée avec l'éditeur.

---

## 5. Plan détaillé recommandé (angle ①)

Titre de travail : **« L'IA qui ne pouvait pas mettre le casque »** — sous-titre : *six jours, un agent, un directeur
artistique et un Quest 3 pour une balade VR peinte.*

Alternatives : « Six jours dans une barque avec Claude » · « Une IA a construit ma démo VR. Je n'ai fait que
regarder. » · « Je portais le casque, elle portait tout le reste ».

### 0. Chapeau (150 mots)
Le résultat d'abord : une image du lac final (`review/iter-067/casque/232s.jpg`, après vérification §7) et la phrase
d'accroche. Ce qu'est la démo, en deux lignes. Le contrat : l'agent fait tout, Olivier regarde et dit ce qui ne va
pas.

### 1. Le dispositif (500 mots)
- La vision : 4 min assis dans une barque, sept beats calés sur une musique Suno.
- Les rôles et les règles de `CLAUDE.md` (encadré : les 5 règles d'or).
- Le poste : un PC, une 3090, un Quest 3 en USB, tout en local, aucun service payant.
- Visuels : carte de la rivière (`review/layout/carte.png`), structure musicale (`review/music/structure.png`),
  palettes par beat (`review/bible/palettes.png`).

### 2. Premier jour : « c'est long et c'est moche » (500 mots)
- ACE-Step, 30 musiques, aucun écoutée ; le passage à Suno.
- Naissance du mode autonome : `SUIVI.md`, les défauts réversibles D1-D9.
- Unreal créé par script, le MCP, le premier APK en 7 min 30.
- Le greybox d'iter-001 (`review/iter-001/planche.jpg`) — l'image « avant » du grand avant / après.
- Encadré méthode : *tester petit avant de produire en série*.

### 3. Ce que l'écran ne montre pas (900 mots) — cœur de la thèse
- « Sur tes screenshots je ne vois pas le rendu dessin animé » : pas de post-traitement sur Quest.
- La bataille des 72 Hz, les essais A/B par adb, et la mesure faite sur un casque qui regardait le ciel.
- La brume jamais rendue, les shaders en 16 bits, les matériaux gris : « chaque fois, l'éditeur affichait un rendu
  correct ».
- Visuels : `review/iter-008/planche.jpg` (look peint), un fichier `review/perf/ab-*.txt` mis en graphique.
- Encadré : *ce que l'agent voit / ce qu'il ne voit pas* (tableau à deux colonnes).

### 4. Le pivot des arbres (900 mots)
- « Le truc le plus moche ce sont les arbres ».
- L'APK A / B / C où la forêt change toutes les 12 s : laisser l'humain choisir au casque plutôt que débattre.
- Les sprites, les bandes verticales, puis « les sprites qui tournent quand on tourne la tête, c'est trop bizarre ».
- Le mandat de 8 h et la scène repeuplée : ~7 800 sprites, 72 i/s.
- Visuels : planche casque iter-012 (arbres 3D) vs iter-019/029 ; planche des familles de sprites (à produire) ;
  `review/iter-030/planche-sprites.jpg`.

### 5. Les oreilles de l'agent (600 mots)
- Les sons Freesound choisis sans écoute : Whisper, spectres, le « bruit de voiture ».
- Les stems Suno spatialisés autour de la barque, le repère sonore avant chaque créature.
- Ce passage est court mais très parlant pour la thèse.

### 6. Du Seigneur des Anneaux au pont de pierre (800 mots)
- L'idée d'Olivier, les trois concepts (`review/explorations/statues/planche.jpg`), le choix.
- Image → 3D, la projection, puis « ta vue 3D sur fond gris est très belle, c'est pas du tout ce que je vois dans le
  jeu » : la comparaison systématique qui révèle deux bugs d'import.
- « Waouh » au casque.
- Visuels : `refs/inbox/arche-statues.png` → `review/explorations/pont/v01_v08.jpg`,
  `trellis_vs_hunyuan.jpg`, puis la capture casque à 100-140 s.

### 7. L'eau, ou le « pas fini » (600 mots)
- « L'eau, c'est clairement ce qui fait pas fini », « l'eau reste une surface plane ».
- Les rides devenues rayons, le réseau sans direction, le sillage de Kelvin, l'écume invisible (trois causes
  empilées), Niagara « très moche ».
- Visuels : extraits vidéo de l'eau (avant / après, à produire depuis les animatics iter-043 et iter-064).

### 8. Rendre les yeux de l'humain plus efficaces (500 mots)
- Le casque piloté par adb, le suivi perdu dans le noir, les captures casque devenues la référence.
- Le bouton A et la bande de lisière trouvée par dichotomie.
- Conclusion de section : l'agent outille son relecteur, pas seulement lui-même.

### 9. Bilan (700 mots)
- Le grand avant / après : `review/iter-001/planche.jpg` → `review/iter-067/planche-casque.jpg`, et le time-lapse des
  10 instants fixes de iter-012 à iter-067.
- Les chiffres (§2).
- Ce que l'agent a bien fait (endurance, rigueur, outillage, mémoire écrite) / ce qu'il a mal fait (conclure trop vite
  sur une mesure, corriger un symptôme sans vérifier l'étendue, raisonner sur l'aspect plutôt que sur une capture
  datée).
- Ce qui reste humain : le goût, le casque, le périmètre, les idées de mise en scène (statues, héron, tangage).
- Le plan initial vs la réalité (architecture vidéo 360 abandonnée).
- Ouverture : ce que ça change pour un créatif seul ; ce qui manque encore (un agent qui « voit » en stéréo ?).

### Annexe technique (angle ③, 1 500-2 500 mots, ou billet séparé)
Quest 3 et UE 5.8 : look sans post-traitement, sprites fixes orientés au placement, relief par gonflement de
silhouette, eau sans profondeur, profil de textures, MSAA, ombres, LOD, estimateur de triangles, chaîne image → 3D
(TRELLIS.2, Pixal3D, Hunyuan3D, remaillage), MCP Unreal et Python à distance depuis WSL.

---

## 6. Visuels et vidéos

### Disponibles

| Visuel | Chemin | Usage |
|---|---|---|
| Greybox du premier soir | `review/iter-001/planche.jpg` | « avant » du grand avant / après |
| Look peint (18/10) | `review/iter-008/planche.jpg`, `diff.jpg` | §3 |
| Captures casque, 10 instants fixes, iter-012 → iter-067 | `review/iter-0NN/casque/{030s…232s}.jpg`, `planche-casque.jpg` | time-lapse, avant / après |
| Captures au bouton A | `review/casque-A/20261023/` | §8 |
| Comparatif image → 3D | `review/3d/comparaison*.jpg` | §6, annexe |
| Concepts de statues | `review/explorations/statues/planche.jpg` | §6 |
| Versions du pont | `review/explorations/pont/v01…v11.jpg`, `v01_v08.jpg`, `trellis_vs_hunyuan.jpg`, `comparatif.jpg` | §6 |
| Images d'Olivier | `refs/*.png`, `refs/inbox/*.png` | référence vs résultat |
| Palettes, brume | `review/bible/` | §1 |
| Carte, terrain | `review/layout/` | §1 |
| Structure musicale | `review/music/structure.png` | §1, §5 |
| Mesures A/B | `review/perf/ab-*.txt` (15 fichiers) | graphique §3 |
| Sprites | `assets/textures/sprites/` (378 images) | planche §4 |
| Animatics vidéo | 19 × ~4 min : `review/iter-031…057/animatic.mp4` (720p), `iter-059/060/064/animatic-hd.mp4` (4K) | extraits, évolution |

### À produire (je peux le faire en itération suivante)

1. **Time-lapse** des captures casque aux 10 instants fixes, iter-012 → iter-067 (GIF ou vidéo courte) : le visuel
   le plus partageable.
2. **Avant / après en curseur** iter-001 vs iter-067 (images appariées, même instant quand possible).
3. **Graphique de performance** (i/s par levier, depuis `review/perf/`) et **courbe des commits par jour**.
4. **Planche des sprites** par famille (arbres, buissons, faune, lueurs).
5. **Frise chronologique** des six jours avec les phrases-pivots d'Olivier.
6. **Schéma de la boucle** agent ↔ fichiers de suivi ↔ Olivier ↔ casque.
7. **Extraits vidéo** de 10-20 s : eau (avant / après), passage sous le pont, héron final, nuée de lucioles.
8. **Comparaison du plan des arbres A / B / C** : capture à refaire si aucune n'existe de l'APK de comparaison.

### À fournir par toi
- Une **vraie vidéo au casque** (capture Quest ou scrcpy) : les animatics sont des rendus PC, pas la vue VR.
- Une **photo de toi au casque** ou du poste (humanise le récit).
- L'**enregistrement audio** de ton test du 19/10 au soir, s'il existe encore : citations de première main.
- Les **transcriptions des sessions** : seule la session en cours est dans `~/.claude/projects/` ; les précédentes
  donneraient des échanges verbatim (le journal ne garde que des extraits).

---

## 7. Points de vigilance

- **Style et originalité** : la règle du projet interdit noms de studio et d'artiste dans les prompts, et les
  créatures sont originales. Mais certains concepts (statues) évoquent très fortement un studio précis, et une alerte
  d'originalité a été consignée le 18/10 (concept S4 trop proche d'un film connu, gardé pour la palette). L'article
  doit décider s'il en parle ; je recommande d'en parler franchement (la règle, l'alerte, le choix de ne jamais
  nommer) plutôt que de laisser le lecteur le relever.
- **Le Seigneur des Anneaux** est cité comme source d'idée : à garder tel quel, c'est une référence de mise en scène,
  pas une reproduction.
- **Données à ne pas publier** : adresses internes (`172.19.32.1`), noms de clés SSH, la clé Freesound collée en
  conversation, chemins de sauvegarde ; à purger des captures de fichiers si on en montre.
- **Licences** : sons CC0, musique Suno (vérifier les droits de ton abonnement pour la diffusion), images Midjourney
  (idem), modèles locaux (licences de TRELLIS.2, Pixal3D, Hunyuan3D, Z-Image pour un usage public).
- **Captures à vérifier avant usage** : sur `review/iter-067/casque/076s.jpg`, une nappe d'eau translucide apparaît
  sur le plancher de la barque (houle de la bête doublée le 23/10 ?) — à contrôler avant d'en faire une image de
  l'article.
- **Chiffres** : les relever à nouveau au moment de publier (le projet continue) ; distinguer mesuré au casque /
  estimé / rendu PC.
- **Ton** : l'agent rédige ses commits et son journal à la première personne par endroits ; l'article doit trancher
  qui parle (toi, avec citations de l'agent ? un texte co-écrit ?).

## 8. Questions que les lecteurs poseront (à préparer)

- Combien de temps humain, combien de temps machine, combien ça a coûté ?
- Quelle part du code / des choix vient de toi ? Avais-tu déjà fait de l'Unreal ou de la VR ?
- L'agent a-t-il « triché » ou inventé des résultats ? (réponse honnête : la mesure du casque posé, rattrapée par la
  règle « vérifier ce qu'on mesure »)
- Que se serait-il passé sans toi au casque ?
- Est-ce reproductible par quelqu'un d'autre ? (le dépôt est-il public ?)
- Les créations générées sont-elles originales, à qui appartiennent-elles ?

## 9. Prochaines étapes proposées

1. Toi : trancher A1-A6.
2. Moi : produire les visuels de §6 « À produire » (time-lapse et avant / après en premier).
3. Moi : premier jet de l'article sur l'angle retenu, citations vérifiées contre `HISTORY.md` et les commits.
4. Toi : relecture, ajout de ta voix (ressenti au casque, que l'agent ne peut pas écrire).
