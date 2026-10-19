# Suivi — La barque des lucioles

**Fichier unique de suivi.** Tenu par l'agent, lu par Olivier. Classé par criticité.
Mis à jour : 2026-10-19

Légende : 🔴 bloque un jalon, aucun contournement · 🟠 j'avance avec un contournement · 🟢 mineur

---

## ▶ Chantier sans casque (19/10, ~6 h, à partir de 11 h 50)

Casque indisponible (suivi de position perdu) ; Olivier : « avançons le maximum », images et vidéos envoyées dans la
session. Revue par l'animatic rendu par Unreal (lumière de chaque beat, musique), qui fait foi hors casque pour le look.

- ✅ **Filtre peinture retiré du rendu PC** (retour d'Olivier : le Quest ne l'a pas) : animatic net, fidèle au casque.
- ✅ **« Ovale » au bas des sprites** (retour d'Olivier : l'effet de répétition) : le bas des touffes de feuillage
  était découpé en ellipse lisse, identique pour toutes ; il est maintenant festonné et propre à chaque image. Les
  arbres avaient tous une plaque d'herbe peinte sous le tronc : retirée, pied estompé.
- ✅ **Lumière cohérente** : une image retournée était éclairée du mauvais côté ; le miroir est désormais choisi au
  placement pour que le côté éclairé regarde le soleil du beat où l'on voit le sujet.
- 🔧 **Relief des sujets proches** (à juger au casque, en stéréo) : arbres à moins de 18 m du parcours, buissons et
  fourrés à moins de 10 m, faune, arbre colossal : grille creusée selon une carte de relief tirée de la silhouette
  peinte (`pipeline/comfy/relief.py`), au lieu du plan plat. Charge estimée hors casque (`pipeline/review/charge.py`,
  `review/charge.txt`) : ≤ 24 k triangles de sprites par vue (contre ~5 k sans relief, 72 k avec le premier réglage).
  **Coût à mesurer au casque.** Retour arrière : `RELIEF_M = {}` dans `sprites_layout.py`.
- ✅ **Libellules qui reculaient en vol** (retour d'Olivier) : leurs à-coups inversaient la vitesse ; à-coups gardés,
  sans marche arrière, image tournée dans le sens réel du vol.
- ✅ **Fondu d'ouverture 4 fois plus long** (retour d'Olivier) : 10 s au lieu de 2,5, même fin (22,5 s) ; l'image
  commence à poindre pendant le clapotis de S1.
- 🔧 **Nouvelle barque** (retour d'Olivier : « la lanterne masque tout le décor ») : image retrouvée dans la transcription
  et écrite à la place de `refs/barque.png` (l'ancienne reste dans l'historique Git) ; TRELLIS.2 retenu (Pixal3D garde la
  perspective de l'image : barque penchée). 3,5 × 1,56 m, franc-bord ~45 cm. **Lanterne** (défaut, D11) : le modèle de
  lanterne en papier, 32 cm, posé sur l'avant droit, sous la ligne d'horizon ; son papier s'allume à la bougie et elle
  tangue. Si tu préfères : sans lanterne, ou ailleurs (`LANTERN_LOCAL` dans `greybox.py`).
- 🔧 **Reflets des lueurs dans l'eau la nuit** : plantes lumineuses, lucioles des berges et nuée finale se reflètent en
  traînées près de la ligne d'eau (`pipeline/layout/glow_map.py`, une lecture de texture de plus).
- 🔧 **Voûte au-dessus de l'eau** plus nette de près : cases de l'atlas des touffes passées de 512 à 1 024 px.
- 🔧 **Troupeau lisible** : rochers géants retirés du gué (on les confondait avec les bêtes) et bêtes remontées de
  60 cm : seuls leurs dos moussus sortaient de l'eau ; têtes et oreilles se voient maintenant, pieds au sol sur la berge.
- 🔧 **Arche des racines habillée** : lianes dispersées sous la voûte (trouée au-dessus du chenal) ; le modèle 3D,
  lisse, paraissait nu vu de dessous.
- 🔧 **Créature volante plus présente** : passe à 200 m au lieu de 300 (même direction, devant la lune, même vitesse
  apparente) : 1,5 fois plus grande à l'œil, moins voilée par la brume (D4 : envergure inchangée).
- 🔧 **Vent** : arbres, buissons, touffes et lianes se balancent doucement (pied fixe, ~1 % de la hauteur à la cime) ;
  les plans restent orientés, ils ne tournent pas avec la tête.
- 🔧 **Lac final moins vide** : nénuphars en fleurs le long du passage de la barque ; leurs fleurs s'allument la nuit.
- 🔧 **Chemin de lune** sur l'eau la nuit : reflet de la lune peinte, étiré à la verticale par les rides, en éclats.
- 🔧 **Sons de la faune** (choisis sans écoute, sans parole détectée par Whisper ; **à valider à l'écoute**, D7) :
  canards (3 groupes), chœurs de grenouilles en S3, hululements des chouettes en S6, spatialisés à leur place et
  audibles seulement en passant (portée 25 m).

## ▶ Retours du 19/10 matin : corrigés, vérifiés dans l'éditeur, pas encore au casque

Retours d'Olivier au casque sur la version « tout en images peintes » (APK installé le 19/10 à 9 h 04) :

- ✅ **Direction confirmée** : « très fourni », les sprites sont la bonne idée à creuser (D16 tranchée).
- ✅ **Oiseaux et feuilles qui tombent** : « trop bien ».
- 🔧 **[confort] Sprites qui pivotaient avec la tête** : **tous les plans sont maintenant immobiles.** Chaque plan regarde
  le point du parcours d'où on le voit à ~45° devant (de face en approchant, jamais par la tranche au passage) ; deux
  voisins regardent presque le même point, leurs plans restent presque parallèles. Le shader ne calcule plus
  d'orientation (moins de travail par sommet). Un plan vu presque par la tranche s'efface au lieu de devenir un aplat.
- 🔧 **Nénuphars qui scintillaient** : plus aucun recouvrement entre deux nénuphars (677 au lieu de 900), hauteurs
  distinctes.
- 🔧 **Plantes toutes blanches au bout de la rivière** : la lueur de nuit allumait aussi les feuilles (seuil trop bas,
  gain ×5) et les plantes entières viraient au blanc. Seules les parties claires et vives s'allument désormais (fleurs,
  chapeaux, points), avec un gain réduit et une teinte froide.
- 🔧 **Canards immobiles dans le passage du troupeau** : les canards nagent (petits cercles dans les deux sens,
  dodelinement), le groupe du gué est déplacé et toute la faune est exclue du couloir du troupeau.
- 🔧 **Arbres qui se répétaient (à gauche)** : 16 feuillus de plus générés en local (frêne, tilleul, peuplier, aulne à
  deux troncs, noisetier, charme, sorbier, saule têtard, marronnier en fleurs, orme, saule blanc, arbre au lierre, jeune
  chêne, troncs entrelacés, arbre tortueux, feuillu sombre) ; deux voisins ne tirent plus le même arbre ; chaque image
  est retournée une fois sur deux et légèrement teintée (plus chaude ou plus froide). Cause trouvée en route : la
  densification de la forêt ne tirait que parmi 4 arbres.
- 🔧 **Eau terne** : le reflet des berges était presque noir (85 %), alors que les berges sont maintenant des arbres
  peints. Il devient un vert peint, plus clair vers la ligne des cimes, strié par les rides ; scintillements sur les
  crêtes des rides ; eau profonde plus turquoise. **À juger au casque** : l'éditeur n'applique pas la lumière par beat.

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
3. Sans casque : `review/iter-011/animatic.mp4` (4 min, musique + ambiances) et `review/iter-011/planche-animatic.jpg` (images de l'animatic aux moments clés).

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
| D12 | Placement des stems autour de la barque | stems Suno déposés le 18/10, placés selon `pipeline/audio/stems.yaml` | déposer les stems dans `audio/music/stems/` (créer le dossier), puis `python pipeline/build.py stems` : placement automatique autour de la barque (`pipeline/audio/stems.yaml` : piano devant à droite, cordes larges derrière, basses sous la barque, bois devant à gauche en hauteur, cuivres au loin, celesta au-dessus) | |
| D13 | Versionner tes nouveaux fichiers audio (`audio/music/Luminous Wonder.wav` + 10 stems, ~460 Mo) | non versionnés (quota LFS GitHub) ; l'ancien MP3 supprimé de ton côté n'est pas non plus retiré du dépôt | je les ajoute au dépôt (LFS) et retire le MP3 | |
| D14 | Marge de performance au Quest (S2 à 71,5 i/s, à la limite) | MSAA 2× gardé (bords nets) ; arbres lointains éclaircis | MSAA 1× : +2,7 ms de marge, bords crénelés qui scintillent ; ou alléger encore la végétation (moins de détail) ; ou plugin Meta XR pour demander le niveau GPU maximal (+10 %, installation à autoriser) | |
| D15 | Élément visuel du final à la place des lanternes | nuée de lucioles autour de la barque et dans l'arbre de l'île | autre élément : fleurs lumineuses, lanternes flottantes près de la barque, reflet de lune… (`lake_fireflies` dans `greybox_geometry.py`) | |
| D16 | Arbres (« le plus moche ») ou autre décor (statues géantes ?) | arbres et décor en images peintes (sprites) | — | **sprites peints**, « c'est la bonne idée à creuser » (19/10) |
| D17 | Animatics vidéo déjà poussés dans l'historique Git (~925 Mo en LFS, quota GitHub limité) | désormais hors dépôt (`.gitignore`), planches seules versionnées ; l'historique n'est pas réécrit | les retirer de l'historique (réécriture, à autoriser) ou acheter du quota LFS | |
| D18 | Statues géantes (ton idée « à débattre ») : 3 pistes en image de recherche, `review/explorations/statues/planche.jpg` (gardiens, tête couchée, arche sculptée) | rien d'intégré | choisir une piste et un moment de la balade : je la peins en sprite (comme l'arbre colossal) | |

**Nettoyage LFS (dans la todo d'Olivier, à lancer sur son accord écrit)** — ~2,2 Go en LFS sur tout l'historique, dont
~1,3 Go d'animatics vidéo (`review/iter-*/animatic.mp4`), ≥ 460 Mo d'assets Unreal (versions successives), ~150 Mo de
textures. Réécrire l'historique ne libère pas le quota sur GitHub (les objets LFS restent comptés tant que le dépôt
existe) : il faut recréer le dépôt (ou passer par le support GitHub). Plan proposé :
1. `git filter-repo` en local : retirer les animatics vidéo et l'ancien MP3 (planches JPG gardées).
2. Ajouter la musique WAV et les 10 stems en LFS (D13, ~460 Mo).
3. Pousser vers le dépôt recréé ; garder la copie locale actuelle en sauvegarde jusqu'à vérification.
| D9 | M'autoriser à installer Blender portable (sans droits admin, sur G:) | j'attends ; nettoyage des maillages via les nœuds ComfyUI en attendant | — | |

## ▶ Chantier « tout en images peintes » (18/10 au soir, 8 h d'autonomie)

Retour d'Olivier : les arbres peints (variante B) « rendent vachement bien » ; il faut exploiter l'idée à fond pour donner
vie et volume au parcours (la scène paraît « vide » et « low poly »). Plan :
1. **Système générique de sprites peints** : catalogue `pipeline/comfy/sprites.yaml` (7 familles : arbres ×2, buissons,
   fourrés, lisières, feuillages, petite faune), générées en local et détourées (`pipeline/comfy/sprites.py`), placées par
   `pipeline/layout/sprites_layout.py`, matériau unique à 4 modes (face, sphère, fixe, sol) dans `greybox.py`.
2. **Scène repeuplée** : forêt peinte redensifiée, premier rang d'arbres de berge, berges et sous-bois garnis, bandes de
   lisière et de collines peintes à l'horizon, houppiers de l'arbre colossal et de l'arbre de l'île en touffes peintes,
   lotus et pétales sur l'eau. La forêt 3D et la lisière en boules sont retirées.
3. **Vie** : oiseaux, papillons, libellules, feuilles qui tombent (animés dans le shader).
4. Vérifications au casque et mesures à chaque étape ; un commit par étape.

**Étape 1 faite (19/10, nuit)** — scène repeuplée en images peintes, **72 i/s sur toute la balade au Quest, GPU ≤ 95 %**
(`review/perf/`, captures `review/iter-025/planche-casque.jpg`). Remplacer la forêt 3D par des plans peints a libéré du budget,
alors que la scène est bien plus dense :
- **9 familles de sprites** générées en local : arbres ×2 (16), buissons, fourrés, bandes de lisière et de collines, touffes
  de feuillage, nénuphars et lotus vus de dessus, petite faune volante, faune des berges. 64 images, toutes détourées.
- **~7 800 sprites posés** : forêt redensifiée, premier rang d'arbres de berge (saules, aulnes, bouleaux, cerisiers), berges
  et sous-bois garnis (buissons, fougères, iris, lys, digitales, massettes au ras de l'eau), voûte de branches et lianes
  au-dessus de l'eau, deux anneaux de lisières et de collines, houppiers des grands arbres en touffes peintes,
  nénuphars peints (les nénuphars 3D sont retirés).
- **Vie** : hérons qui tournent haut, hirondelles au ras de l'eau, papillons qui ferment les ailes, libellules, feuilles et
  pétales qui tombent (tout animé dans le shader). Oiseaux et insectes partent à la tombée de la nuit. Faune posée :
  cerfs qui boivent, renards, lapins, canards, grenouilles, martin-pêcheur sur le ponton, chouettes sur des souches (nuit),
  tortues.
- Retirés : forêt 3D, lisière et collines en boules, buissons, fougères et fleurs 3D des berges (gardés : herbe, roseaux,
  rochers, troncs couchés).

**Étape 2 (19/10)** — **nuit lumineuse et lanterne qui tangue**, toujours 72 i/s :
- Famille « nuit » : champignons bleus et orange, fleurs de lune, clochettes bleues, mousses et fougères phosphorescentes,
  lys pâles. ~700 posés sur les berges de l'arche au lac, au pied de l'arbre colossal et autour du lac. Leurs parties
  claires s'allument à la tombée de la nuit (captures `review/iter-028/planche-casque.jpg`).
- **Lanterne de proue** (ton retour : « trop figée ») : elle tangue doucement sur sa perche (roulis ~3°, tangage ~2°,
  rythmes irréguliers). Le même balancement est calculé dans le shader pour la perche et le corps de la lanterne (zone du
  maillage de la barque), le papier lumineux et le halo : ils restent solidaires (`review/iter-029/casque/`, 4 images à
  1,2 s d'écart).

**Planches de revue (sans casque)** : `review/iter-030/planche-sprites.jpg` (les 11 familles d'images peintes, ~90 images)
et `review/iter-030/tour-editeur.jpg` (tour de la balade dans l'éditeur, lumière de jour : la nuit n'y est pas rendue).

**Étape 3 (19/10)** — **arbre colossal entièrement peint** : tronc moussu en sprite (un tronc se voit pareil sous tous
les angles), houppier en touffes peintes, rideaux de lianes, fougères et mousses au pied ; l'arche 3D des racines reste.
Rochers géants moussus au bord de l'eau, souches géantes. Les bandes de lisière sont reculées à plus de 70 m (de près,
elles se voyaient comme des panneaux plats là où la forêt s'ouvre).
- **Incident casque (1 h 30)** : l'interface système du Quest plantait en boucle, plus aucune appli ne démarrait. Le journal
  indiquait « Vulkan device creation failed ». Cause non établie. Une propriété de débogage que j'avais réglée la veille
  (niveau GPU) était restée en place : je l'ai effacée, puis j'ai redémarré le casque. **Si le Quest refuse de démarrer
  une appli, un redémarrage complet suffit.**

## ▶ APK de comparaison des arbres (installé au Quest, 18/10)

La forêt change toutes les 12 s pendant toute la balade, avec une étiquette à la proue :
**A** arbres actuels → **B** arbres peints → **C** touffes ombrées → A… Mêmes positions d'arbres pour les trois ; les
trois tiennent ~72 i/s (`review/perf/`). Captures : `review/iter-022/planche-casque.jpg`.
- **B, arbres peints** : 8 arbres peints générés en local (ComfyUI), un plan tourné vers l'œil par arbre. C'est la piste des
  décors d'animation. Limites à juger au casque : les plans sont plats en relief (stéréo) et pivotent quand on tourne
  la tête ; le gros plan est le plus exposé.
- **C, touffes ombrées** : mêmes arbres 3D, chaque touffe ombrée pour elle-même (dessus clair, dessous sombre), touffes aplaties.
- L'arbre colossal, la lisière et les buissons ne changent pas.
Dis-moi laquelle garder (ou un mélange : par exemple B au loin et C près de l'eau) ; je retirerai ensuite le cycle.

## Priorités (18/10 au soir)

1. **Arbres (D16)** : ce sont des boules texturées, d'où l'aspect « jeu des années 90 ». Pistes, à tester petit avant de choisir :
   - **arbres peints en plans** : silhouettes de feuillage peintes (générées en local dans ComfyUI, dans le style du ciel), posées en croix ou face à l'œil pour le milieu et le fond de la forêt. C'est le procédé des décors d'animation, et c'est aussi moins coûteux en sommets (notre goulot au Quest) ;
   - houppiers à bord découpé en touffes (silhouette « nuage » festonnée), plus de sommets ;
   - autre décor (statues ou ruines géantes envahies de mousse, design original) : change l'ambiance, à décider ensemble.
2. **Créature des abysses** au casque : vérifier qu'elle se voit à droite vers 1:06-1:14 ; sinon la rapprocher ou la faire remonter.
3. **Marge de perf (D14)** : S2 à 71,5 i/s, et toute nouvelle géométrie se paiera.
4. **J1 (sphère vidéo 360 + synchro)** : go/no-go jamais fait au casque, alors que c'est la base de l'architecture proche / lointain.
5. Sons : repères sonores des créatures, écoute des ambiances (D7) ; caméras de revue et planche à remettre à jour pour la PR.

## 🔴 Bloquants

| # | Blocage | Bloque | Ce qu'il faut | Contournement en cours |
|---|---|---|---|---|

## 🟠 Importants (contournés)

- **Casque : suivi de position perdu (19/10, depuis 10 h)**. Le Quest posé sur le bureau, dans une pièce sombre et
  face à un carton tout proche, ne retrouve pas sa position : il affiche « Trouver la position dans la pièce » et
  l'appli ne rend rien derrière (les mesures lues, 90 i/s à GPU 30-48 %, étaient celles du menu ; jetées). Essai
  autorisé par Olivier à 11 h 30 : « Continuer sans le suivi » (atteint par adb : flèche bas puis validation) ferme la
  boîte, mais le casque refuse alors d'ouvrir l'appli (« Activez le suivi pour utiliser cette app ») ; une appli VR
  exige le suivi de position. Suivi réactivé de la même façon, casque laissé dans son état normal. **Il faut éclairer
  la pièce ou tourner le casque vers un espace dégagé et texturé**, puis me dire « go ». L'APK avec toutes les
  corrections est installé.

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
- Nuit (S6-S7) : ciel encore assez clair (ton ciel HD est plus lumineux que l'ancien) ; à juger au casque, la teinte se règle dans `pipeline/style/ambiance.yaml` (`ciel_teinte`).
- Raccord du ciel : un nuage un peu fantôme au raccord gauche/droite (derrière le spectateur au départ).
- Textures générées : l'écorce et la roche sont correctes mais moins belles que ta mousse ; des textures Midjourney (`tex-ecorce`, `tex-roche`, `tex-herbe`, `tex-terre`, `tex-feuillage` dans `PROMPTS.md`) remplaceraient directement les miennes (dépôt dans `refs/`, puis `python pipeline/comfy/textures.py`).
- Roseaux : jaunâtres à contre-jour malgré un vert très sombre (lumière du soleil rasant sur des lames double face) ; à reprendre avec le matériau peint.

- Clé Freesound collée dans la conversation : risque faible, à régénérer si tu préfères.

## À vérifier au casque

- **Prochain essai (version du 19/10 après-midi, APK installé)** — tout n'a été vu qu'en rendu PC :
  - **perf** : relief des sujets proches (≤ 24 k triangles de sprites par vue, estimés), vent (shader de sommets),
    reflets dans l'eau ; mesurer S2-S3 en premier (les plus justes) ;
  - **arbres immobiles** : plus de rotation avec la tête ? plans qui s'effacent vus par la tranche : discrets ?
  - **relief** des arbres et buissons proches en stéréo : volume perçu, ou défauts (étirements, bords) ?
  - **nouvelle barque** : échelle (3,5 × 1,56 m), hauteur des yeux, franc-bord ; lanterne sur l'avant droit : gêne-t-elle
    encore ? assez visible la nuit ?
  - eau : reflets des lueurs, chemin de lune, eau de jour moins terne ;
  - canards qui nagent, sons de faune (canards, grenouilles, chouettes) et leur portée ; libellules ;
  - fondu d'ouverture de 10 s ; arche habillée de lianes ; lac final avec nénuphars lumineux.

- **Scène en images peintes (19/10)** : les arbres et buissons peints restent-ils crédibles de près, au bord de l'eau
  (relief plat, léger pivotement quand on tourne la tête) ? Densité des berges (trop de fleurs ?), hérons et
  hirondelles (taille, vitesse), papillons, feuilles qui tombent, faune (cerfs, canards…), lueurs de nuit,
  balancement de la lanterne (assez ? trop ?), arbre colossal peint.

- **Corrections du 18/10 au soir (APK installé)** : pieux du ponton moins visibles à travers l'eau ? brume enfin perceptible, pas trop dense au départ ? plancher fixe ? lucioles de l'envol en courbes ? plus de voix à l'entrée du lac ? (volume du casque laissé à 1 par mes essais)
- **J2 (greybox)** : fréquence d'image avec ~530 k triangles de décor et les textures (mesure à faire casque porté), lisibilité de l'eau et du sillage, chaleur de la lanterne, lucioles (taille, clignotement, dérive : agréables ou agaçantes ?), brume du départ (trop dense ?), échelle de la barque (3,5 m, franc-bord ~45 cm, place assise à 1,20 m derrière le centre), gêne de la lanterne de proue (D11), hauteur des yeux 1,10 m, confort de la dérive et des virages, lisibilité du passage sous la barque (S3), distance du troupeau (14 m, S4), passage sous l'arche (8 m, S5).

- **J1 (APK `builds/android/`)** : la vidéo s'affiche ; « AVANT » devant ; la stéréo n'est pas inversée (« ŒIL GAUCHE » ne doit être lu que de l'œil gauche) ; les repères 1,5 m / 3 m / 10 m / ∞ paraissent à ces distances ; le cube rouge clignote en même temps que le flash blanc et le bip ; fluidité (72 Hz) en 4096 px. Point technique incertain : sélection de l'œil (`ResolvedView.StereoPassIndex`) avec le multiview mobile.

- J1 : vidéos `assets/spike/test360_*` (orientation, stéréo, résolution maximale fluide, synchronisation).
- Confort du tracé : rotation maximale de 1,15 °/s, vitesse de 1 m/s.
- Échelles (D4) dès le greybox.

## Fait récemment

- **19/10 matin** : casque revenu (redémarré et mis à jour par Olivier), dernier APK installé à 9 h 04 (arbre colossal
  peint, rochers) ; pas encore mesuré par adb. WSL est passé en réseau NAT : ComfyUI et le MCP Unreal sont joints sur
  `172.19.32.1` (adresses centralisées dans `pipeline/tools.yaml`). Journal de création ouvert : `HISTORY.md`.

- **Retours du 18/10 au soir (APK installé au Quest, captures `review/iter-021/planche-casque.jpg`)** :
  - **Fondu au noir** : il n'était jamais rendu au casque, car la piste de fondu de la séquence passe par le post-traitement, absent sur Quest. Le fondu est maintenant fait par une sphère noire autour des yeux, dont l'opacité est animée. **S1 est enfin noir** jusqu'à 20 s, l'image s'ouvre en 2,5 s, et la fin passe au noir sur l'extinction de la musique. Vérifié par capture : noir à 242 s, l'appli reste sur le noir final.
  - **Lanternes de l'arbre retirées** (D15) et remplacées par une **nuée de lucioles finale** : environ 800 lucioles serrées autour de la barque sur le lac, plus 160 dans l'arbre de l'île. Elles s'allument une à une sur la dernière montée de la musique et la nuée monte lentement.
  - **Créature des abysses** : elle passe à ~5 m à droite de la barque, à 2 m sous la surface, au lieu de passer dessous, où la coque la cachait. L'eau s'éclaircit au-dessus d'elle. Vérifié par une capture dans l'éditeur, **à voir au casque** : regarder à droite vers 1:06-1:14.
  - **Troupeau** : vitesse, écart et couloir propres à chaque bête.
  - **Racines coupées sous l'eau** : l'absorption est plus forte (moitié de la couleur perdue en ~23 cm de trajet sous l'eau). Les bouts de racines et leur rencontre avec le fond ne se découpent plus. Les pieux du ponton s'effacent aussi plus vite.
  - **Plancher** plus clair.
- **Performance au Quest et reflet de la lisière (18/10, 19 h 45)** — **72 i/s de S3 à S7, 71,5 en S2** (regard droit devant, `review/perf/greybox-20261018-1943.png`). Avant : 62 en S2, 63 en S3. Captures au casque : `review/iter-019/planche-casque.jpg`.
  - **Piège de mesure** : le casque posé sur le bureau ne regarde pas toujours au même endroit. Tourné vers le ciel, il donne 72 i/s ; droit devant, 62 avec la même version. Je vérifie désormais le cadrage par une capture avant de comparer deux mesures.
  - **Diagnostic** avec le profileur GPU du casque (`ovrgpuprofiler`) : la scène est limitée par la géométrie (binning 4,5-4,9 ms par image) plus que par les pixels. Baisser la résolution ne change rien ; le MSAA coûte 3 ms.
  - **Ombres du soleil coupées** : une carte d'ombres 4096 × 2048 coûtait 1,4 ms par image, pour rien, puisque le décor est non éclairé. La recapture du ciel à chaque image est coupée aussi. Gain : +4 i/s en S2, +7 en S3.
  - **Herbe, fougères et fleurs en 3 niveaux de détail** : tronçon proche complet, 45 % puis 15 % des touffes au loin. La lisière est découpée en 8 morceaux, ce qui est hors du champ n'est plus traité.
  - **Arbres lointains éclaircis** : à plus de 65 m de la rivière, 7 sur 10 sont retirés (cachés par les premiers rangs et la brume), sauf autour du lac. On passe de 2 325 à 1 900 arbres. À vérifier au casque : la forêt paraît-elle moins dense par les trouées ?
  - **Écartés après mesure** :
    - prépassage de profondeur (27 i/s) ;
    - calculs du shader peint déplacés vers les sommets (pire : −3 i/s) ;
    - résolution d'œil réduite à 0,9 (sans effet) ;
    - suppression de la couche de profondeur OpenXR (sans effet) ;
    - distance d'affichage des arbres (sans effet).
    Une variante d'APK `exp` (`package_android.py --variant exp --cvars "…"`) permet ces essais sans toucher à la version normale.
  - **Marge restante** : passer le MSAA de 2× à 1× ferait gagner 2,7 ms, mais les bords crénelés scintillent dans le casque. Je ne l'applique pas (voir D14).
  - **Reflet de la lisière dans l'eau** : la masse sombre des arbres se reflète sur les côtés, le ciel au milieu du chenal, selon l'angle de vue réel. Une seule lecture de texture : la distance aux deux rives est précalculée dans la carte de l'eau, et le lac est traité par une intersection exacte avec son cercle.
- **Corrections de l'enquête (18/10 au soir)** :
  - Plancher de la barque : texture projetée dans le repère de l'objet, elle ne défile plus.
  - Lucioles de l'envol et créatures : trajectoires en courbes (interpolation cubique), plus de virage sec à chaque clé.
  - Troncs couchés : parallèles à la berge, sol mesuré aux deux bouts, plus aucun bout en l'air ni dans l'eau (vérifié sur les 5).
  - Ambiance du lac : lue à partir de 35 s (Whisper ne détecte plus de parole).
  - **Brouillard** : densités calculées (50 % à ~32 m en S2, ~50 m en S3-S5, ~78 m en S6-S7), atténuation en hauteur 0,6 au lieu de 1,4 (les cimes restent dans la brume), début à 8 m ; la nuit, brume plus claire que les ombres.
  - **Performance** : calcul sous l'eau réservé aux matériaux qui touchent l'eau (terrain, roches, racines, ponton, créature) ; feuillage, herbe, arbres et troncs couchés ont un matériau « sec ». Le « 72 i/s » annoncé dans ce commit était faux : pendant cette mesure, le casque posé regardait le ciel. Mesures corrigées dans l'entrée suivante.
  - **Eau** : les objets immergés (pieux du ponton, racines, fond, corps de la créature) s'éteignent vers la couleur de l'eau profonde selon la longueur du trajet sous la surface, calculée exactement pour une eau plate. Liseré clair là où ils traversent la surface, halo lumineux de la créature sur l'eau, surface un peu plus opaque vers le bas (0,68 au lieu de 0,5).
- **Enquête du 18/10 au soir (sans casque ni 3D locale)** : corrigée (entrée ci-dessus), diagnostic gardé pour mémoire :
  - **Sol de la barque qui défile** : le plancher utilise le matériau peint, dont la texture de détail est projetée en coordonnées monde ; la barque avance, la texture reste fixe dans le monde. Correctif : projection dans le repère de l'objet pour ce qui bouge (plancher, et toute pièce attachée à la barque).
  - **Lucioles qui filent droit puis tournent net** : le nuage de l'envol suit des clés posées toutes les 2 s en interpolation linéaire (segments droits, changement de direction à chaque clé). Correctif : interpolation courbe (cubique) pour le nuage et les créatures ; la barque reste en linéaire (vitesse constante).
  - **Tronc horizontal dans le vide à droite (passage des abysses)** : localisé, à t ≈ 78 s à droite. Un tronc couché de 4,6 m dont un bout repose sur la berge et l'autre surplombe la rivière à 2,9 m au-dessus du fond. Le générateur ne mesure le sol qu'à un bout et oriente le tronc au hasard, rivière comprise. Un second, à 35 s à gauche, flotte à 0,7 m. Correctif : mesurer le sol aux deux bouts, rester sur la berge.
  - **Voix à l'arrivée sur le lac** : c'est l'ambiance `amb-lac-nuit` (Freesound #412941, enregistrée pendant un tournage), qui démarre à 200 s. Whisper y détecte de la parole en anglais dans ses 30 premières secondes. Les autres ambiances sont propres. Correctif : autre enregistrement (ou partir de 35 s dans celui-ci), et écouter les candidats avant de les retenir (D7).
  - **Brouillard peu visible** : calcul avec les formules du moteur et nos réglages. En S3-S4, le brouillard ne voile 50 % qu'à ~154 m (35 % à 100 m) ; en S2, 50 % à ~59 m. Le profil bas (atténuation 1,4) le dissipe vite en hauteur (les cimes restent nettes), et sa couleur de nuit est sombre (il se fond dans les ombres au lieu de se lire comme de la brume). Proposition : 50 % à ~40 m en S2, ~60 m en S3-S5, ~90 m en S6-S7 (densités ~0,44 / 0,25 / 0,15), atténuation 0,6, début à 8 m, brume plus claire que les ombres (bleu-gris éclairé par la lune la nuit).
  - **Eau (recherche web)** : sur Quest sans HDR mobile, le matériau d'eau ne peut pas lire la profondeur de la scène (Depth Fade non supporté, ticket Epic « Won't Fix ») ; reflets planaires exclus (ils re-rendent toute la scène). La technique adaptée inverse le problème : les **matériaux des objets immergés** (pieux, racines, fond, créature) s'assombrissent et se teintent selon la longueur de trajet sous l'eau, calculée exactement pour une eau plate. On peut ajouter un flou simulé (mip plus grossier, ondulation de quelques cm sous la surface) et une ligne d'eau claire là où l'objet traverse la surface. Côté surface : reflet analytique de la lisière d'arbres (masse sombre peinte, à partir de la carte des berges déjà cuite), rides en normal map dans le sens du courant, halo de la créature sur la surface. Coût : une dizaine d'instructions par pixel, sans texture.
  - **Blender pour les arbres** : utile pour la technique classique des arbres stylisés : feuillage en grappes, normales transférées d'une forme simple (mélange ~0,8), scriptable en `bpy` (D9, Blender pas encore installé). Mais les cartes de feuilles masquées sont chères sur le GPU du Quest (avec MSAA, plus de rejet précoce des pixels). Pour la performance, le levier est dans Unreal : son **Impostor Baker** (intégré) transforme les arbres lointains en imposteurs de 8 triangles. Sur mobile, l'imposteur affiche une seule vue, sans fondu : on voit un peu les sauts de vue.
- **Nouvelle musique et stems (18/10, 16 h 30)** : ta nouvelle « Luminous Wonder » en WAV est une autre prise que le MP3 (corrélation quasi nulle), de même durée (219,44 s). Séquencier recalé sur l'analyse de structure (`review/music/structure.png`) : S3 +2 s (frontière nette à 26 s), S4 −1 s, S5 −2 s, S6 inchangé, S7 +2 s ; révélation des lanternes sur la dernière montée de l'outro (206,7 s). Les repères du parcours restent dans leurs beats.
  - **Stems spatialisés** : tes 10 stems Suno deviennent 12 sources attachées à la barque (`pipeline/audio/stems.yaml`). Piano devant à droite, cordes larges derrière, basses sous la barque, bois devant à gauche en hauteur, cuivres au loin, guitare à gauche, nappe de synthé au-dessus, percussions derrière ; « Other » reste en stéréo. La musique stéréo n'est plus jouée quand les stems sont là.
  - **Mémoire et APK** : les WAV restent les sources ; Unreal les recompresse à l'empaquetage (pas besoin d'Opus). Toutes les pistes sont lues en flux : décompressées d'un coup, elles prendraient plus de 200 Mo.
- **Brouillard** : il n'était **jamais rendu au casque** (le Quest le calcule dans une passe séparée qui exige le HDR mobile, désactivé). Il est maintenant calculé dans le rendu de base, en **brouillard bas** : épais au ras de l'eau, il s'éclaircit avec la hauteur et le ciel reste dégagé. Densités relevées, eau en grille de 5 m (le brouillard est calculé aux sommets).
- **Recentrage VR** : au lancement, origine au sol sous le joueur, puis après 1 s recentrage position et cap. Le spectateur est sur le banc, face à la proue, quels que soient la zone de jeu et le dernier recentrage du Quest.
- **Créatures et ambiance** :
  - Abysses : la créature file devant puis s'enfonce et s'éteint dans le chenal profond, au lieu de disparaître dans le sol.
  - Créature volante : passage devant la lune 40 % plus lent.
  - Nuit : le passage à S6 commence 8 s plus tôt et dure 26 s au lieu de 12.
  - Arbre colossal : affiché dès le début, il n'apparaît plus d'un coup.
  - Eau : le reflet ne monte plus au-delà de 55° (au zénith, le ciel équirectangulaire s'étirait en rayons sur l'eau).
- **Arbres** : fondu tramé entre niveaux de détail retiré. Il empêchait le GPU de rejeter tôt les pixels cachés : la forêt coûtait 6,4 ms. La brume, maintenant visible, adoucit les changements de niveau au loin.
- **Retours du 18/10 après-midi** :
  - **Lucioles en particules** : lueurs douces face à l'œil, qui s'allument une à une (berges à la fin du noir, nuage de l'envol en sortant de l'eau). Elles ne s'affichaient plus du tout dans les deux dernières versions : les carrés de taille nulle étaient supprimés à la construction du maillage. Corrigé et vérifié sur PC, **pas encore vu au casque** (pause demandée).
  - **Ponton et arche des racines** : tes modèles 3D (TRELLIS.2 depuis `refs/ponton.png` et `refs/racine.png`) remplacent les cubes et le tube du greybox, avec le look peint et une teinte raccordée au décor.
  - **Nénuphars** ronds, au bord irrégulier, avec l'encoche et le bord relevé, une teinte par feuille.
  - **Eau dans la barque** : le cap de la barque n'arrivait sans doute pas au shader de l'eau (stocké dans la composante alpha d'un paramètre animé) ; il est maintenant dans une autre composante. Le plancher suit le contour réel de la coque à la ligne de flottaison (298 × 141 cm, calculé sur le maillage).
  - **Arbres** : les niveaux de détail gardent toutes les touffes principales (seule la finesse change) et passent de l'un à l'autre par un fondu tramé au lieu d'un saut.
  - Plus de fleurs sur les berges.
- **Démo « HD » pour comparer** (`builds/android_hd/`, paquet `com.odoucet.barque.hd`, installée à côté de la normale) : arbres fins gardés bien plus loin, pas de culling, MSAA 4x. Mesure : 44-50 i/s en S2-S5, 58-68 en S6-S7 (`review/perf/hd-20261018-1543.png`). La version normale : 72 i/s, sauf S3 à 69,5 (`review/perf/greybox-20261018-1538.png`).
- **Casque en pause à ta demande** (18/10 ~15:50) : plus aucune commande adb jusqu'à nouvel ordre. Le dernier APK normal (lucioles corrigées, ponton et racine) est construit mais **n'est pas installé**.
- **Forêt instanciée à niveaux de détail** : 6 feuillus et 3 résineux en 3 niveaux (≈2 700 / 560 / 90 triangles pour un feuillu), 2 325 arbres avec taille, rotation et teinte propres. Le niveau fin est réservé aux arbres tout proches de la barque ; au-delà de 180 m, plus d'arbres (brume et lisière). Mesures A/B au casque : la forêt coûtait 6,8 ms par image avant réglage des niveaux. **72 Hz tenus sur toute la balade** (`review/perf/greybox-20261018-1507.png`), S2-S3 à la limite (GPU 96-97 %).
- **Captures réelles au casque** : `pipeline/unreal/quest_shots.py` lance l'APK et capture la vue du casque aux moments clés (`review/iter-013/planche-casque.jpg`). C'est désormais la référence de revue ; à chaque run, la courbe FPS / GPU / CPU est dans `review/perf/`.
- **Piège réglé** : un matériau doit déclarer son usage « maillages instanciés », sinon le jeu empaqueté affiche le matériau par défaut (arbres gris au casque, alors que le rendu PC était correct).
- **72 Hz tenus sur toute la balade au Quest** (mesure du 18/10 à 14:34, GPU ≤ 92 %, `review/perf/greybox-20261018-1434.png`). Avant : 49-61 i/s de S2 à S5, GPU saturé.
  - Les essais A/B en direct au casque (`pipeline/unreal/quest_ab.py`, commandes console par adb) ont montré une scène limitée par la géométrie, pas par les pixels. Mesures en S2 : MSAA 4x → 1x : -3,2 ms ; tous les maillages cachés : -8 ms ; résolution à 60 % : -0,6 ms ; eau : -0,5 ms ; brume : -0,7 ms.
  - Correctifs : MSAA 2x ; faces dupliquées supprimées (herbe, fougères, roseaux) ; créatures cachées hors de leur passage (elles étaient dessinées sous le terrain) ; décor lointain caché pendant la brume dense de S1-S2 ; une seule lecture de texture de détail ; rendu fovéal activé.
- **Retours du casque (14 h) corrigés** :
  - Précision complète des shaders sur Quest. Le calcul en 16 bits pixellisait le ciel, le faisait bouger par à-coups et faussait le masque de l'eau dans la barque.
  - Plancher opaque dans la barque, en plus du masque de l'eau.
  - Lune peinte dans le ciel, derrière les nuages.
  - Animations sans squelette : nage ondulante et lumineuse des abysses, marche du troupeau (pattes en diagonale, corps qui ondule).
  - Envol des lucioles en spirale, avec des boucles propres à chaque luciole.
  - Houppiers des arbres moyens plus ronds (touffes à 80 triangles au lieu de 20).
- **Captures au casque** possibles par adb (outil de capture du Quest) : je peux relire ce que montre réellement le casque.
- **APK de l'itération 10 installé sur le Quest** (586 Mo). La mesure de fréquence d'image n'a pas pu se faire : casque non porté, l'application ne rend rien et le Quest se met en pause. **À faire casque porté** (`python pipeline/unreal/quest_perf.py --variant greybox`, ou dis-moi « go »). C'est la mesure qui décide si j'ajoute encore du détail ou si j'allège (le décor est passé de ~250 k à ~530 k triangles, avec 5 lectures de texture par pixel sur le feuillage).
- **Revue** : `planche-animatic.jpg` est produite automatiquement à chaque animatic (moments clés, rendu Movie Render Queue fidèle à la lumière par beat). Les captures de l'éditeur (`planche.jpg`) restent utiles pour les cadrages, pas pour la lumière.
- **Itération 9-10 (rendu HD, polygones, eau, lanterne ; retours du 18/10 matin)** :
  - **Textures peintes** : ta mousse (`refs/tex-mousse.png`) sert de référence de style. Les autres textures (écorce, herbe, terre, roche, feuillage, planches) sont repeintes à partir d'elle en local (Qwen-Image-Edit, `pipeline/comfy/textures.py`, prompts dans `PROMPTS.md`). Elles sont projetées en coordonnées monde (triplanaire) par type de surface : feuillage = ta mousse, bois = écorce, sol = herbe, roche = roche, terrain = terre/herbe selon la couleur. Elles modulent la valeur des aplats et y mêlent leurs touches de couleur.
  - **Ciel HD** : ton `refs/ciel.png`, raccordé gauche/droite et agrandi en 4096×2048. Le raccord laisse un nuage un peu fantôme, derrière le spectateur au départ.
  - **Polygones** : ~530 k triangles de décor (contre ~250 k), 2 373 arbres. Houppiers proches en chou-fleur (touffes de surface) avec branches visibles, fougères, massifs de fleurs, galets, bois mort, fleurs de nénuphar, roseaux du lac, contreforts et côtes d'écorce de l'arbre colossal, houppier de l'arbre aux lanternes trois fois plus détaillé. Chaque tronçon est découpé par type de surface (un matériau chacun).
  - **Eau peinte** : rides qui suivent le courant (carte de l'eau calculée sur le terrain), reflet du ciel déformé par les rides, traits de lumière sur les crêtes, bande sombre du reflet des arbres près des berges, écume le long des rives, chenal plus sombre.
  - **Autour de la barque** : sillage en V, bourrelet d'écume le long de la coque, reflet de la lanterne. **Plus d'eau dans la barque** (masque à l'intérieur de la coque).
  - **Lanterne** : papier qui vacille comme une bougie, halo doux, et lumière chaude portée sur le décor, la barque et l'eau (calculée dans les matériaux peints, qui ne reçoivent pas les lumières du moteur).
  - **Lucioles** : le nuage de l'envol ne « retombe » plus sous l'eau à la fin (il était renvoyé sous le terrain en 0,5 s) ; il continue de monter et disparaît dans le ciel.
  - **Filtre peinture** (filtre de Kuwahara, aplats à bords nets) : PC VR et rendus offline seulement. **Sur Quest, aucun filtre de post-traitement n'est possible** (rendu mobile sans HDR) : le look y vient des matériaux et des textures.
- **Itération 8 (look peint, retours au casque du 18/10)** :
  - **Look dessin animé** dans le matériau `M_Peint` (non éclairé, ombrage deux tons à bord peint, liseré de contre-jour, couleurs par sommet). Ce n'est pas un filtre de rendu : sur Quest sans HDR mobile, aucun post-traitement n'est possible.
  - **Lumière par beat** dans `pipeline/style/ambiance.yaml` (lumière, ombre, ciel, soleil, teinte du ciel) : brume bleue au départ, jour vert, crépuscule doré sous les racines, nuit bleue étoilée pour la lune et le lac.
  - **Décor peint** (`pipeline/layout/vegetation.py`, couleurs dans `pipeline/style/look.yaml`) : environ 1 700 arbres (feuillus en houppiers à normales sphériques, résineux), lisière, buissons fleuris, herbe, rochers, pierres du gué, collines lointaines, arbre colossal à contreforts, arbre aux lanternes en ombrelle. La barque et les créatures prennent le même look (texture conservée).
  - **Ciel vivant** : nuages qui dérivent lentement (y compris dans le reflet de l'eau), étoiles qui scintillent la nuit.
  - **Retours corrigés** : plus de « Lighting needs to be rebuilt » (aucun éclairage précalculé). Abysses : suit le chenal, rattrape et dépasse la barque, puis plonge dans une fosse. Troupeau : sort de la forêt par un sentier creusé dans la berge, traverse le gué et remonte sur la berge gauche en suivant le terrain. Créature volante : continue son vol jusqu'à sortir du champ, avec un battement d'ailes procédural.
  - **Captures de revue** : les captures de l'éditeur (SceneCapture) n'appliquent pas la lumière par beat (paramètres de collection non transmis hors lecture) ; elles montrent toutes la même lumière. En attendant une revue rendue par Movie Render Queue, la référence est l'animatic (`planche-animatic.jpg`).
- **Mesure au casque (APK de l'itération 7, ancien look)** : 72 Hz tenus en S2-S3, GPU à ~89 % (10,9 ms sur 13,9) ; le casque, non porté, s'est mis en pause au bout d'une minute. À refaire casque porté sur l'APK de l'itération 8.
- **Itération 7 (J2)** : lucioles vivantes. Elles dérivent lentement et clignotent, avec une phase propre à chacune ; tout est animé dans le shader (WPO), sans coût CPU sur le Quest. Environ 440 lucioles éparses le long des berges de 0:20 à la fin, en plus du nuage de l'envol. Nénuphars et roseaux moins brillants : ils renvoyaient le ciel en blanc à contre-jour. Les captures de revue figent le temps des shaders (images comparables d'une itération à l'autre) ; le clignotement a été vérifié sur les images de l'animatic.
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
| J2 Greybox + animatic | greybox construit par script (terrain, eau translucide, arche, forêt, lac, lune, blocs des créatures) ; séquence LS_Animatic calée sur la musique ; 18 captures et animatic vidéo avec musique ; **itérations 9-10 : textures peintes, ciel HD, ~530 k triangles de décor, eau peinte avec sillage, lanterne-bougie** ; look peint, lumière par beat, créatures corrigées (itération 8) ; lucioles animées (itération 7) ; brume par beat, roseaux, nénuphars (itération 6) ; eau qui reflète le ciel peint (itération 5), ciel peint (itération 4) (crépuscule → nuit) après les créatures 3D (itération 3) (abysses lumineuse, troupeau, créature volante) après la barque 3D en itération 2 (modèle TRELLIS.2 de ta vue 3/4, lanterne lumineuse, place assise sur le banc arrière) — `review/iter-011/planche-animatic.jpg` et `review/iter-011/animatic.mp4` ; à valider : timing et confort au casque |
| J3 à J6 | non commencés |
