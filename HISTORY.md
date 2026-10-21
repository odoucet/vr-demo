# Historique de création — La barque des lucioles

Journal chronologique du projet : étapes, retours d'Olivier, décisions et ce qu'elles ont changé. Il sert de matière
pour un article sur le processus de création à deux, un directeur artistique humain et un agent de production
autonome. `SUIVI.md` dit où en est le projet ; ce fichier raconte comment on y est arrivé.

- **Sources** : les 53 premiers commits (relus un par un, messages et contenu), l'historique de `SUIVI.md` et les
  messages d'Olivier dans la conversation. Les heures sont à l'heure de Paris. Les hachages renvoient aux commits.
- **Tenue** : une entrée par itération à partir du 19/10, ajoutée en fin de fichier, en même temps que le commit.

---

## Le dispositif

- **Le projet** : une balade VR contemplative de ~4 min. Le spectateur est assis dans une barque qui dérive sur une
  rivière en forêt, du crépuscule à la nuit, dans un style peint inspiré de l'animation japonaise des années 80-90.
  Sept beats calés sur la musique : noir, ponton dans la brume, ombre géante sous l'eau, troupeau au gué, arche de
  racines, créature devant la lune, lac final.
- **Les rôles** : Olivier est directeur artistique et relecteur. Il génère les images de référence (Midjourney) et la
  musique (Suno), teste au casque et corrige en asynchrone. L'agent (Claude Code) construit tout le reste, seul, et
  ne demande que ce qui est bloquant.
- **Les règles** (`CLAUDE.md`) :
  - la scène est du code : tout ce qui la construit est un script Python versionné et idempotent, et
    `python pipeline/build.py` reconstruit tout depuis zéro ;
  - une itération = un commit ;
  - tester petit avant de produire en série ;
  - jamais de service payant ni d'installation sans accord écrit ;
  - toutes les créatures et tous les designs sont originaux.
- **Le poste** : Windows + WSL2, RTX 3090 24 Go, Unreal Engine 5.8 et son serveur MCP, ComfyUI local (Z-Image Turbo,
  Qwen-Image-Edit, TRELLIS.2, Pixal3D, BiRefNet), Meta Quest 3 branché en USB.
- **La boucle de revue** : `SUIVI.md` comme fichier unique de suivi (blocages, décisions attendues avec un défaut
  appliqué, vérifications au casque) ; captures de revue puis, dès le 18/10, captures réelles de la vue du casque et
  mesures de fréquence d'image par adb.

## Décisions

| Quand | Décision | Pourquoi |
|---|---|---|
| 17/10 | Musique sur Suno, générée par Olivier ; ACE-Step écarté | « très médiocre comparé à Suno » : son « MIDI », aigus saturés |
| 17/10 | Image → 3D : TRELLIS.2 et Pixal3D gardés, choix au cas par cas | comparatif sur 7 assets, chacun gagne sur des objets différents |
| 17/10 | Défauts réversibles D1-D9 appliqués sans attendre (image maîtresse, coupure S3/S4, tracé, échelles, coque, livraison sans PR, sons, caméras) | mode autonome : ne jamais rester bloqué |
| 17/10 | Outils Android dans un SDK séparé (`G:\android`), pas Docker ni le SDK de Ren'Py | UE Windows ne peut pas utiliser un SDK Linux en conteneur ; ne pas dépendre d'un autre logiciel |
| 17/10 | Scripts Unreal exécutés dans l'éditeur ouvert (Python à distance), headless sinon | l'éditeur héberge le MCP ; un headless concurrent modifierait les mêmes assets |
| 17/10 | J1b : variante de repli du lecteur 360 (calque stéréo du casque) préparée d'avance | éviter un aller-retour si la sphère à matériau échoue en stéréo |
| 17/10 | D11 : place assise reculée sur le banc arrière | la lanterne de proue masquait le centre de la vue |
| 18/10 | Look peint dans les matériaux, pas en filtre | aucun post-traitement possible sur Quest (rendu mobile sans HDR) |
| 18/10 | Éclairage calculé dans les matériaux (non éclairés), plus d'éclairage précalculé | look deux tons maîtrisé, coût fixe |
| 18/10 | MSAA 2× (D14) | bords nets ; le 1× gagnerait 2,7 ms mais scintille |
| 18/10 | Ombres du soleil coupées | 1,4 ms par image pour un décor non éclairé |
| 18/10 | Fondu au noir par une sphère noire autour des yeux | le fondu de la séquence passe par le post-traitement |
| 18/10 | D15 : nuée de lucioles finale à la place des lanternes | lanternes « trop loin, on ne voit pas leur géométrie » |
| 18/10 | D16 : arbres en images peintes (sprites) | variante B préférée au casque ; validée le 19/10 : « c'est la bonne idée à creuser » |
| 18-19/10 | Toute la végétation et la petite vie en sprites générés en local | « ça permet d'avoir des images dans le style qu'on veut et de démultiplier les polygones sur d'autres choses » |
| 19/10 | Sprites fixes, qui ne pivotent plus avec la tête (à faire) | « trop bizarre », des arbres se rentrent dedans selon l'orientation de la tête |

## Leçons transversales

- **Un fichier valide ne dit rien de sa qualité.** 30 musiques générées sans en écouter une : « C'est long et c'est
  moche ». Depuis : 2-3 essais courts, vérifiés, avant tout lot.
- **Le Quest n'est pas un petit PC.** Pas de post-traitement, brouillard calculé à part (jamais rendu jusqu'au 18/10),
  pas de lecture de profondeur dans l'eau, shaders en 16 bits par défaut (ciel pixellisé), matériaux à déclarer pour
  l'instanciation (arbres gris au casque). Chaque fois, l'éditeur affichait un rendu correct.
- **Mesurer au casque, et vérifier ce qu'on mesure.** La scène était limitée par la géométrie, pas par les pixels :
  baisser la résolution ne servait à rien. Un « 72 i/s » annoncé venait d'un casque posé qui regardait le ciel.
  Depuis : capture de la vue du casque avant toute comparaison.
- **Les essais A/B en direct** (commandes console envoyées par adb pendant que le casque tourne) ont remplacé les
  hypothèses : MSAA, maillages cachés, résolution, eau, brume, chiffrés en millisecondes.
- **Une image peinte vaut mieux qu'un maillage pauvre.** Les arbres 3D, même à 2 700 triangles, rappelaient « un jeu
  des années 90 » ; un plan peint de 2 triangles, généré dans le style du projet, rend mieux et coûte moins.
- **Le casque ne pardonne pas ce que l'écran cache.** Plans qui se croisent différemment pour chaque œil (bandes
  verticales), sprites qui pivotent avec la tête, scintillement des plans superposés : invisibles en capture, évidents en
  VR.

---

## Chronologie

### 17/10 après-midi — Préparation : musique, image → 3D, prompts

- **14 h** : création du dépôt. Première demande d'Olivier : un pipeline musique sur ACE-Step, en explorant 30 graines
  en brouillon rapide avant de rendre la composition retenue en qualité.
- **14 h 30** : premiers retours. « Y'a pas vraiment de mélodie et après 15 s on dirait des loops qui se répètent […] je
  vois pas pourquoi t'en génères 30. C'est long et c'est moche. » Puis, après un prompt réécrit : mélodie bien meilleure,
  mais « ça fait son midi, ça sature dans les aigus ». Mesures à l'appui (centroïde spectral deux fois plus haut que
  Suno, stéréo déphasée), la référence de timbre aggravant le résultat.
- **14 h 45** : **décision : la musique se fera sur Suno**, générée par Olivier ; l'agent écrit le prompt. **15 h** :
  « Luminous Wonder » est déposée. Le séquencier est recalé sur son analyse de structure (modulation à 2:17,8).
- **15 h 40** : Olivier dépose des images d'assets dans `refs/` pour tester l'image → 3D dans ComfyUI, et des essais de
  style par beat. Comparatif TRELLIS.2 / Pixal3D sur 7 assets : TRELLIS.2 gagne sur la lanterne, le ponton, le troupeau
  et la créature volante ; Pixal3D sur la créature des abysses. On garde les deux.
- **17 h 20** : Olivier reprendra les images d'assets une par une (« comme on automatise tout en Python je peux reprendre
  un élément sans tout refaire ») et demande la liste de ce qui manque à l'agent pour être autonome. Tous les prompts
  Midjourney et Suno sont regroupés dans `PROMPTS.md`.
- **17 h 34 — `3b81ec4`** : premier commit. Séquencier recalé, pipeline image → 3D, prompts, Git LFS.

### 17/10 soir — Infrastructure : Unreal par script, MCP, Android, premier APK

- **18 h 41 — `4727a32`** : **naissance du mode autonome.** `SUIVI.md` devient le suivi unique, avec la règle
  « décision attendue → défaut réversible appliqué, noté, et on continue » (D1 à D9). Unreal n'est pas encore installé :
  l'agent prépare tout ce qui ne dépend pas du moteur. Tracé de la rivière et trajectoire à vitesse constante calés sur
  le séquencier (contrôle du confort : rotation maximale 1,15 °/s), 18 caméras de revue, `build.py`, vidéo de test 360
  stéréo pour J1, sons Freesound CC0.
- **19 h 02 — `3cc310c`** : Unreal 5.8 installé par Olivier ; le projet est **créé par script** (Quest 3 : OpenXR,
  Vulkan, rendu mobile forward, multiview ; PC VR), exécution headless depuis WSL vérifiée.
- **19 h 40 — `34e3f49`, `7e4ee74`, `c26ab42`, `eb818da`** : le serveur MCP natif d'Unreal n'expose d'abord que la
  gestion de « skills » ; activation des jeux d'outils (éditeur, PCG, Niagara, configuration). Le moteur, installé hors
  du launcher, s'identifie par un GUID : écrire « 5.8 » faisait proposer une conversion du projet à chaque ouverture.
  Capture du viewport par le MCP. Les réglages Quest ajoutés par l'éditeur sont reportés dans le script (règle d'or :
  rien à la main qui ne soit rejouable).
- **20 h 18 — `2345983`, `5b0b5d0`** : outils Android. Olivier propose Docker, puis le SDK de son installation Ren'Py ;
  **décision : SDK séparé dans `G:\android`**, installé par un script rejouable. Pièges : le JDK 25 du poste est trop
  récent pour Gradle (JDK 21 portable), et le niveau d'API « latest » viserait Android 15, que le Quest 3 ne charge pas
  (fixé à android-32). Unreal valide la chaîne.
- **20 h 26 — `8c76041`** : les scripts tournent dans l'éditeur ouvert par Python à distance (le multicast de découverte
  ne traversant pas WSL, le client est lancé avec le Python Windows d'Unreal).
- **20 h 38-20 h 49 — `72e6f04`, `d3aa433`** : **J1**, la brique de l'architecture proche / lointain : sphère vidéo
  360 stéréo synchronisée sur une séquence, avec repères de distance et témoin de synchro. Premier APK Quest empaqueté
  en 7 min 30.

### 17/10 nuit — J2 : greybox, animatic et premières itérations (1 à 7)

- **23 h 07 — `50292ef`** : **itération 1**, le greybox complet construit par script : terrain (lit, gué, lac, île),
  arche des racines, forêt avec la trouée de S6, arbre colossal, arbre aux lanternes, eau translucide, lune, blocs des
  créatures. Séquence de l'animatic : barque à vitesse constante, caméra à 1,10 m, musique à 0:20. 18 captures de revue.
- **23 h 30 — `809576f`, `0fbced8`** : animatic vidéo rendu par Movie Render Queue dans un processus séparé (le
  compilateur de shaders DX11 plantait en boucle : passage en SM6, de 0,2 image/s à un rendu de 4 min en 50 s).
  Workflow Qwen-Image-Edit pour générer les vues manquantes d'un asset.
- **23 h 54 — `f2e0c57`** : **itération 2**, la barque 3D (TRELLIS.2 depuis la vue 3/4 peinte d'Olivier). Vue depuis la
  place assise, la lanterne de proue masque le centre de l'image : la place est reculée sur le banc arrière (D11), lune
  et créature volante décalées de 15° à gauche.
- **00 h 05 — `5a18617`** : le greybox devient **jouable au casque** (joueur assis attaché à la barque), avec un paysage
  sonore spatialisé et un APK distinct de celui de J1.
- **00 h 22-00 h 25 — `ca92457`, `8fe3550`** : **itération 3**, créatures 3D (abysses lumineuse, troupeau à mi-corps,
  créature volante), envol de 400 lucioles. Premier contact avec le budget Quest : troupeau simplifié à l'import,
  scène ramenée de ~600 k à ~165 k triangles.
- **00 h 40-00 h 47 — `6444a65`, `8ae4a7b`, `ff620cf`** : **itérations 4 et 5**, ciel peint généré en local (Z-Image
  Turbo) qui passe du crépuscule à la nuit ; eau qui reflète le ciel avec Fresnel, sans réflexion temps réel. J1b,
  variante de repli de J1, préparée pour ne pas perdre une session de test.
- **00 h 50 — `62419df`** : **J0**, palette par beat extraite des essais d'Olivier. Alerte d'originalité consignée :
  un concept provisoire montrait des créatures trop proches d'un film d'animation connu ; il ne sert qu'à la palette.
- **00 h 52-00 h 54 — `ccf03af`, `5f2b018`, `a87fa65`, `fcf6700`** : idempotence. Sons, maillages, matériaux et ciel ne
  sont réécrits que si leur source change (empreintes) : sans cela, chaque reconstruction gonflait le dépôt LFS.
- **01 h 05 — `98b2e49`** : **itération 6**, brume par beat dont la teinte est mesurée sur la bande d'horizon de chaque
  référence, dans un fichier partagé par le temps réel et le futur rendu offline du lointain (la brume sert de raccord).
  Roseaux procéduraux, dont une touffe qui frôle la barque.
- **01 h 14-01 h 22 — `31e634a`, `e84bd8e`** : ciel agrandi en 4096×2048 (il était flou) ; outil de mesure de fréquence
  d'image au casque par adb ; **itération 7**, lucioles animées entièrement dans le shader, sans coût CPU.

### 18/10 matin — Le look peint, sans post-traitement (itérations 8 à 11)

- **9 h 20, retour d'Olivier** : « Sur tes screenshots je ne vois pas le rendu dessin animé. Ça devait pas être un
  filtre de rendu UE ? Je trouve les scènes très pauvres et avec peu d'éléments. »
- **10 h 19 — `c74e0b7`** : **itération 8**. Découverte structurante : sur Quest, sans HDR mobile, **aucun filtre de
  post-traitement n'est possible**. Le look passe donc dans les matériaux : `M_Peint`, non éclairé, ombrage deux tons à
  bord peint, liseré de contre-jour. Lumière par beat dans un fichier d'ambiance. Décor dense (~1 700 arbres, lisière,
  buissons, rochers, collines). Créatures corrigées : l'abysse suit le chenal, le troupeau sort par un sentier, la
  créature volante bat des ailes (animation procédurale, sans squelette).
- **11 h 02 — `24272aa`** : **itérations 9-10**. La texture de mousse d'Olivier sert de référence : les autres
  textures (écorce, herbe, roche…) sont repeintes à partir d'elle en local (Qwen-Image-Edit). Ciel HD d'Olivier.
  ~530 k triangles de décor. Eau peinte (rides qui suivent le courant, écume des berges, sillage). Lanterne-bougie
  dont la lumière est calculée dans les matériaux. Filtre de Kuwahara réservé au PC et aux rendus offline.
- **11 h 10 — `f28c297`, `4950a88`** : animatic à exposition fixe ; la mesure au casque échoue (casque non porté :
  l'appli ne rend rien et le Quest se met en pause).

### 18/10 après-midi — La bataille des 72 Hz et les retours au casque

- **14 h 39 — `3724ee1`** : de 49-61 i/s à **72 Hz tenus**. Les essais A/B en direct au casque montrent une scène
  **limitée par la géométrie** : tout cacher fait gagner 8 ms, baisser la résolution à 60 % seulement 0,6 ms. MSAA 2×,
  faces dupliquées supprimées, créatures cachées hors de leur passage (elles étaient dessinées sous le terrain).
  Retours du casque : shaders en précision complète (le 16 bits pixellisait le ciel), plancher dans la barque, lune
  peinte, nage et marche procédurales, envol en spirale.
- **15 h 16 — `6af23c4`** : forêt instanciée à 3 niveaux de détail (2 325 arbres). **Captures réelles de la vue du
  casque** par adb : elles deviennent la référence de revue. Piège : un matériau qui ne déclare pas l'usage
  « instancié » s'affiche gris au casque.
- **15 h 30, retours d'Olivier** : ciel « vraiment bien » ; lucioles « des losanges, c'est moche », qui apparaissent
  « d'un coup » ; « on voit les arbres se redessiner » ; « surpris par le manque de polygones […] c'est vraiment une
  limite du casque ? » ; troupeau « pas mal du tout » ; nénuphars « très rectangulaires » ; l'eau passe encore dans la
  barque. Il demande une démo avec beaucoup plus de polygones, même à 25 i/s, pour juger.
- **15 h 57 — `27e7d4d`** : lucioles en particules douces qui s'allument une à une ; ponton et arche des racines en 3D
  depuis les modèles d'Olivier ; nénuphars ronds à encoche ; plancher à la forme exacte de la coque. **Démo « HD »**
  installée à côté : 44-50 i/s, pour comparer au casque ce que les polygones apportent.
- **16 h 14 — `b9834aa`** : « Je suis derrière le bateau » : l'origine VR dépendait de la zone de jeu du Quest.
  Recentrage au lancement par un Blueprint créé par script.
- **16 h 51 — `3666eea`, `0fe087e`** : nouvelle prise de « Luminous Wonder » en WAV (une autre interprétation, même
  durée) et 10 stems Suno, spatialisés en 12 sources autour de la barque (piano devant à droite, basses sous la barque,
  cordes derrière…). Le brouillard **n'avait jamais été rendu au casque** (sa passe exige le HDR mobile) : il passe dans
  le rendu de base, en brume basse. Fondu tramé des arbres retiré (il empêchait le rejet précoce des pixels cachés).

### 18/10 soir — Enquête, corrections et mesure trompeuse

- **17 h 20, retours d'Olivier** : plancher dont la texture défile ; lucioles « magnifiques » mais qui filent droit puis
  tournent net ; un tronc horizontal dans le vide ; ponton « superbe » mais qui révèle le défaut de l'eau (pieux vus
  nettement à travers) : « ça mérite une vraie recherche sur Internet » ; une voix à l'entrée du lac ; brouillard peu
  visible ; « est-ce que Blender peut aider ? ». Consigne : enquêter sans casque ni 3D locale.
- **17 h 35 — `cff4b79`** : l'enquête, consignée avant toute correction. Chaque symptôme a sa cause :
  - texture projetée en coordonnées monde sur un objet qui avance ;
  - clés de trajectoire en interpolation linéaire ;
  - tronc orienté au hasard, sol mesuré à un seul bout ;
  - parole anglaise détectée par Whisper dans un enregistrement Freesound ;
  - brouillard calculé : il ne voilait 50 % qu'à ~154 m.

  Pour l'eau, la recherche montre que le Quest ne peut pas lire la profondeur dans le matériau d'eau. On inverse donc
  le problème : ce sont les objets immergés qui s'éteignent selon la longueur de leur trajet sous l'eau. Pour Blender :
  utile pour les arbres stylisés classiques, mais les cartes de feuilles masquées sont chères sur le GPU du Quest.
- **18 h 20 — `0e7b559`** : les corrections. S2-S3 tombent à 57-59 i/s : le calcul sous l'eau tournait sur tous les
  pixels, arbres compris. Réservé aux matériaux qui touchent l'eau, il libère de quoi remonter à 72 i/s.
- **19 h 56 — `a08a91b`** : le « 72 i/s » précédent était faux : le casque posé regardait le ciel. Droit devant : 62.
  Le profileur GPU embarqué confirme le goulot géométrique (binning). Leviers retenus : ombres du soleil coupées
  (1,4 ms), herbe en 3 niveaux de détail, lisière découpée, arbres lointains éclaircis (2 325 → 1 900). Écartés après
  mesure : prépassage de profondeur (27 i/s), calculs déplacés vers les sommets (−3 i/s), résolution réduite (sans
  effet). D14 : MSAA 2× gardé. Reflet de la lisière dans l'eau calculé sans réflexion temps réel.
- **20 h 40, retours d'Olivier** : forêt, ponton, brume, plancher, voix réglés. Restent : la bête sous l'eau ne se voit
  plus (« qu'elle passe à côté du bateau ? Ou on remplace par un dauphin ? ») ; troupeau trop régulier ; racines
  « coupées » sous l'eau ; lanternes de l'arbre final trop loin, « on peut les remplacer par un autre élément visuel » ;
  pas de fondu au noir à la fin. Et surtout : « le truc le plus moche ce sont les arbres », avec une autre idée : « la
  fameuse descente en barque du Seigneur des Anneaux quand ils passent entre les deux statues géantes, mais ça ferait
  changer beaucoup d'ambiance, à débattre ensemble ».
- **21 h 06 — `d137528`, `b49ad1c`** : fondu au noir par une sphère noire autour des yeux (le fondu de la séquence ne
  passe pas sur Quest) ; nuée de ~960 lucioles finale à la place des lanternes (D15) ; abysse à 5 m à droite de la
  barque ; troupeau à vitesse, écart et couloir aléatoires ; absorption sous l'eau renforcée. Priorités posées : les
  arbres d'abord, avec trois pistes : plans peints, touffes festonnées, autre décor (D16).

### 18/10 nuit — Les arbres : de la boule texturée à l'image peinte

- **22 h 15** : « Tu peux proposer les différentes idées sur les arbres dans le même APK ? »
- **22 h 39 — `8552cfd`** : un APK où la forêt change toutes les 12 s, étiquette à la proue : **A** arbres actuels,
  **B** arbres peints (8 images générées en local avec Z-Image Turbo et détourées par BiRefNet, un plan face à l'œil
  par arbre), **C** touffes ombrées. Mêmes positions, ~72 i/s pour les trois.
- **23 h 30, verdict d'Olivier** : « les arbres peints ça rend vachement bien ! […] ça prend tellement moins de
  polygones qu'il faut creuser en ce sens ». Deux défauts : le détourage se voit, et un effet de « bandes verticales »
  quand on regarde à 90°.
- **23 h 40 — `a939a31`** : les bandes venaient de plans orientés chacun vers l'œil, qui se croisaient différemment pour
  chaque œil. Tous les plans deviennent parallèles au plan de la vue. Détourage repris : restes de fond et nuages
  retirés, couleur propagée sous la transparence, couverture alpha préservée dans les mipmaps. Le procédé a un nom
  (billboard, sprite, imposteur), c'est celui des décors d'animation.
- **Mandat d'Olivier** : « Exploiter cette idée à fond : ça permet d'avoir des images dans le style qu'on veut et de
  démultiplier les polygones sur d'autres choses. […] Tu as maintenant 8 h d'autonomie […] pour repenser la scène
  complète et ajouter plus de vie et de volumes. En ce moment ça fait "vide" ou "low poly". » Et : « la lanterne devant
  tangue un peu sur le bateau. Là elle est trop figée. »

### 19/10 nuit — Tout en images peintes

- **00 h 38 — `451df41`** : **la scène repeuplée.** Un système générique :
  - catalogue de familles d'images (`sprites.yaml`) ;
  - génération et détourage en local (`sprites.py`) ;
  - placement (`sprites_layout.py`) ;
  - un matériau unique à plusieurs modes (face à la vue, sphère, fixe, au sol).

  9 familles, 64 images, **~7 800 sprites posés** : forêt redensifiée, arbres de berge, sous-bois, voûte de lianes au-dessus de l'eau,
  lisières et collines à l'horizon, nénuphars. Vie animée dans le shader : hérons, hirondelles, papillons, libellules,
  feuilles et pétales qui tombent, qui partent à la tombée de la nuit ; faune posée sur les berges. La forêt 3D est
  retirée, et c'est ce qui paie le reste : **72 i/s, GPU ≤ 95 %**, pour une scène bien plus dense. Garde-fous trouvés en
  route : textures importées à 32 px par Unreal (réimport), nuages qui s'invitaient dans les images (style des sprites
  sans le ciel), paramètres d'animation déformés par les couleurs de sommet (passés en coordonnées UV).
- **01 h 05 — `68277c1`** : nuit lumineuse (champignons, fleurs, mousses phosphorescents dont les parties claires
  s'allument à la tombée de la nuit) ; **la lanterne tangue** (roulis ~3°, tangage ~2°), calculée dans le shader de façon
  identique pour la perche, le papier lumineux et le halo, qui restent solidaires.
- **01 h 30, incident** : l'interface du Quest plante en boucle, plus aucune appli ne démarre. Une propriété de débogage
  du niveau GPU, réglée la veille, est effacée et le casque redémarré ; il ne réapparaît plus en USB. Cause non établie.
- **01 h 38-01 h 47 — `6aebfaa`, `ddf1342`, `1a9b468`** : arbre colossal entièrement peint (tronc en sprite, lianes,
  mousses ; l'arche 3D des racines reste parce qu'on passe dessous), rochers géants et souches. Lisières reculées à
  plus de 70 m : de près, on les voyait comme des panneaux plats. Aulne régénéré : sa plaque de sol peinte devenait un
  rectangle sur les berges. `build.py` complet vérifié. Planches de revue sans casque.

### 19/10 matin — Réseau, casque revenu, premiers retours sur les sprites

- **9 h** : WSL est passé en réseau NAT : `127.0.0.1` n'atteint plus Windows. Olivier lance ComfyUI en écoute sur
  toutes les interfaces et expose le MCP Unreal sur `172.19.32.1` (le réglage d'écoute du MCP n'est pas dans ses
  paramètres mais dans la configuration du serveur HTTP d'Unreal, `[HTTPServer.Listeners]`). Casque redémarré et mis à
  jour par Olivier ; le dernier APK est installé à 9 h 04, sans rien lancer d'autre (consigne : « ne fais rien de plus »).
- **9 h 14 — `6dc3952`** : adresses passées à `172.19.32.1` partout, centralisées dans `pipeline/tools.yaml`.
  L'exécution Python dans l'éditeur, qui passe par le Python Windows d'Unreal, reste en `127.0.0.1`.
- **9 h 20, retours d'Olivier au casque** :
  - « c'est très fourni et je confirme que les sprites c'est la bonne idée à creuser » ;
  - « les oiseaux et les feuilles qui tombent trop bien ! » ;
  - mais « les sprites qui bougent/tournent quand on bouge ou tourne la tête, c'est trop bizarre. Il faut que les
    sprites soient fixes » : des arbres se rentrent dedans ou non selon l'orientation de la tête ;
  - nénuphars qui scintillent ; plantes toutes blanches au bout de la rivière ; canards immobiles, dont certains dans le
    passage du troupeau, qui les traverse ;
  - « là c'est presque l'eau qui paraît terne ».

  Consigne : tout noter sans corriger, et ouvrir ce journal pour un article sur le processus.
- **Commit « Journal de création »** : retours consignés dans `SUIVI.md` (section « Retours du 19/10 matin », avec une première piste
  par point), D16 tranchée (sprites peints), création de `HISTORY.md` à partir de la relecture des 53 commits.

### 19/10 fin de matinée — Les corrections des sprites

- **Push et reprise** : Olivier demande de pousser le journal (sans ses fichiers audio WAV) et de passer aux corrections.
  Pendant le travail, un retour de plus : « la texture des arbres sur la gauche se répétait beaucoup trop souvent ».
- **Sprites immobiles** : chaque plan est orienté une fois pour toutes, au placement, vers le point du parcours d'où on le
  voit à ~45° devant. Idée clé : deux voisins regardent presque le même point, donc leurs plans restent presque
  parallèles et ne se croisent pas, sans dépendre de la tête. Premier essai dans l'éditeur : une touffe vue par la
  tranche devenait un grand aplat (mipmap grossière) ; un fondu selon l'angle de vue l'efface. Ce fondu effaçait aussi
  les nénuphars, toujours vus en rasant depuis la barque : ils en sont exclus. Un « aplat » restant s'est révélé être une
  feuille animée qui tombait devant la caméra (identifiée en masquant les familles une à une).
- **Nénuphars** : sans recouvrement ; **plantes blanches** : la lueur de nuit allumait les feuilles vertes (seuil sur la
  luminance trop bas) ; **canards** : animés comme les oiseaux, hors du couloir du troupeau.
- **Répétition des arbres** : 16 nouveaux feuillus générés (deux ont dû être régénérés : le décor « au bord de l'eau » du
  prompt faisait peindre une plaque de sol). Tirage sans répétition entre voisins, image retournée et teinte propre à
  chaque arbre. En relisant le placement, une cause directe : la densification de la forêt ne tirait que parmi les 4
  premiers feuillus de la liste.
- **Eau terne** : le reflet des berges était presque noir, hérité de l'époque où les berges étaient des boules sombres ;
  il devient un vert peint dégradé vers les cimes, avec des scintillements sur les rides.
- **Casque** : depuis sa mise à jour, posé sur le bureau, il perd le suivi de position et affiche une boîte de dialogue
  système qui bloque l'appli. La mesure obtenue (90 i/s, GPU 48 %) était celle du menu : jetée, et le point remonté à
  Olivier plutôt que de cliquer dans l'interface système par adb.
- **11 h 30** : Olivier autorise à cliquer « Continuer sans le suivi ». La boîte système ne se pilote pas par l'arbre
  d'interface Android, mais au clavier par adb (flèche bas pour sélectionner le bouton, puis validation), en contrôlant
  chaque pas par une capture du casque. Résultat : sans suivi de position, le Quest refuse d'ouvrir une appli VR. Suivi
  réactivé ; il faut de la lumière ou un autre point de vue pour le casque.

### 19/10 après-midi — Six heures sans casque

- **La question d'Olivier** : que peut-on avancer sans casque, un rendu avec Unreal seul est-il possible ? Réponse : oui,
  l'animatic rendu par Movie Render Queue (lumière de chaque beat, musique) fait foi pour le look ; le casque reste
  nécessaire pour la perf, le relief, l'échelle, le confort. L'animatic n'avait plus été rendu depuis l'itération 11 :
  relancé, envoyé dans la session en 720p.
- **Retours sur l'animatic** : « enlève le filtre peinture du PC vu qu'on l'a pas dans le Quest » ; « on retrouve sur
  toutes les images cet "ovale" sur le bas du sprite, c'est ça l'effet répétition ». L'ovale : la découpe en ellipse lisse
  des touffes de feuillage, vue d'en dessous ; remplacée par un bord festonné propre à chaque image. Au passage, la
  plaque d'herbe peinte sous chaque tronc est retirée.
- **Une erreur rattrapée** : en retournant une image sur deux contre la répétition, la moitié des arbres étaient
  éclairés du mauvais côté (images peintes éclairées par la gauche). Le miroir est maintenant choisi au placement selon
  la direction du soleil du beat où l'on voit l'arbre.
- **Relief en stéréo** : Depth Anything V3 est installé dans ComfyUI mais son nœud échoue (module manquant dans son
  environnement isolé) ; plutôt que de toucher à l'installation, le relief est tiré de la silhouette peinte (profil de
  dôme selon la distance au bord, modulé par les touches claires). Premier profil sphérique : flancs verticaux qui
  étirent la texture vue de biais ; passé en parabolique. Grille creusée dans le shader de sommets, un seul maillage
  instancié de plus par famille.
- **Reflets des lueurs de nuit** : le shader de l'eau calculait déjà le point de rive touché par le rayon réfléchi (pour
  le reflet de la lisière) ; une carte vue de dessus des sources lumineuses, lue en ce point, donne les reflets des
  plantes lumineuses et des lucioles pour une seule lecture de texture.
- **Débogage du reflet des lueurs** : invisible sur le premier rendu. Diagnostic en affichant les termes du shader un à
  un sur l'eau (carte alignée, terme lu au point de rive fort, fenêtre de hauteur ouverte) : le reflet était multiplié par
  le Fresnel, faible près de la barque. Une lumière vive se reflète aussi hors incidence rasante : pondération revue,
  traînées brisées par les rides.
- **Nouveaux retours d'Olivier** : « des libellules faire de la marche arrière en vol, c'est perturbant 😃 » (leurs
  à-coups, une sinusoïde trop forte sur l'angle, inversaient la vitesse) ; le fondu d'ouverture « 4 fois plus long
  (commencer plus tôt pour finir au même timing) » ; et la barque : « la lanterne masque tout le décor, c'est dommage »,
  avec une nouvelle image de barque à passer en 3D.
- **Les sons de la faune** : le paysage s'était peuplé (canards, grenouilles, chouettes) mais restait muet. Trois sons
  CC0 de Freesound, choisis sans pouvoir les écouter : les candidats sont passés dans Whisper (aucune parole, la leçon de
  l'ambiance du lac) et mesurés (niveau, part de basses fréquences pour écarter circulation et vent). Le placement des
  sprites écrit maintenant des points d'émission ; les sons y sont attachés avec une portée courte, pour qu'on les
  entende en passant. Un deux-points mal échappé dans le manifeste bloquait l'outil Freesound depuis deux jours.
- **Le chemin de lune** : la lune, peinte dans le ciel, ne se reflétait pas (le reflet de l'eau lit la texture du ciel,
  pas la lune). Sa direction étant connue, l'eau calcule un reflet de la lune étiré à la verticale par les rides.
- **Le poids des vidéos** : un push a envoyé 432 Mo en LFS, dont trois animatics. Les vidéos sortent du dépôt (seules
  les planches restent) ; nettoyer l'historique demanderait une réécriture, laissée à la décision d'Olivier (D17).
- **Profondeur estimée** : Olivier confirme que Depth Anything ne convient pas (« tes images sont cartoonisées et le
  moteur ne sait pas traiter ce genre de choses »). Le gonflement de silhouette reste la méthode du relief.
- **Nouvelle barque** : l'image envoyée dans la conversation n'existait pas sur le disque ; elle a été retrouvée en base64
  dans la transcription de la session, écrite à la place de refs/barque.png à la demande d'Olivier, puis passée en 3D
  (TRELLIS.2 et Pixal3D).
- **Chiffrer sans casque** : un estimateur compte, pour chaque caméra de revue, les sprites dans le champ et en deçà de
  leur distance de culling, et leurs triangles. Le premier réglage du relief ajoutait jusqu'à 67 000 triangles par vue
  en S2-S3, là où le Quest était le plus juste. Le relief comptant surtout de près, il est resserré (arbres < 18 m,
  grilles plus légères) : 24 000 triangles au pire.
- **Passe de contrôle** sur l'animatic, une image toutes les 6 s : le troupeau semblait avoir disparu du gué. Il était
  là : ses bêtes couvertes de mousse, dans l'eau jusqu'au poitrail, se lisaient comme des rochers, d'autant que deux
  rochers géants moussus posés la nuit précédente se trouvaient au gué. Rochers déplacés. Le lac final paraissait vide
  jusqu'à la nuée : nénuphars en fleurs le long du passage, fleurs lumineuses la nuit. Voûte au-dessus de l'eau en
  résolution double (floue de près).
- **Arche des racines** : nue vu de dessous ; habillée de lianes et de mousse peintes. Premier essai : quatorze rideaux
  alignés en travers de la rivière, une haie suspendue ; dispersés sur l'épaisseur de l'arche, longueurs variées,
  trouée au-dessus du chenal.
- **Le vent** : depuis qu'ils sont immobiles, les arbres peints étaient figés. Un balancement lent dans le shader de
  sommets (pied fixe, amplitude croissante vers la cime, phase selon le lieu) leur rend du mouvement sans les faire
  tourner avec la tête. Les touffes de mousse ajoutées sur l'arche faisaient un chapelet de boules vu de loin : retirées.
- **Prévisualisation mobile dans l'éditeur** : la plateforme de prévisualisation n'est pas exposée à Python ; l'animatic
  rendu reste la référence hors casque.
- **Statues géantes, en recherche** : l'idée d'Olivier du 18/10 (« à débattre ensemble ») est reprise en trois images
  générées en local, avec des designs originaux : deux gardiens moussus, une tête couchée dans la rivière, une arche
  sculptée en deux figures agenouillées. Envoyées pour décision (D18), rien d'intégré.
- **La créature devant la lune** : à 300 m, elle ne couvrait qu'une fois et demie la lune et la brume la bleuissait ;
  « géante » ne se lisait pas. Rapprochée à 200 m dans la même direction, avec des déplacements réduits d'autant pour
  garder la même lenteur apparente.
- **Reconstruction complète** (`python pipeline/build.py`, toutes les étapes) : passe. Elle a montré que les instances de
  matériau des sprites étaient réécrites à chaque build ; elles ont maintenant une empreinte, comme le reste.
- **Le troupeau se lit enfin** : même sans les rochers, ses bêtes ne montraient que leur dos moussu, plus enfoncées que
  « l'eau au poitrail » du séquencier. Remontées de 60 cm : têtes claires et oreilles tombantes visibles.
- **Les statues** : Olivier « adore le pont » (l'arche sculptée) et veut qu'il remplace l'arche des racines, redondante
  avec l'arbre colossal ; la tête couchée « est trop belle » et ira sur une berge. Sa méthode : un objet 3D sans
  végétation, habillé ensuite. Prompts Midjourney écrits (pierre nue, pas de mousse : l'image → 3D en ferait des blocs) ;
  premiers substituts locaux à figures dévêtues, d'où des robes ajoutées au prompt. Olivier livre ses deux images,
  une seule vue du pont. Intégration : mousse calculée dans le matériau sur les faces tournées vers le haut ; tête
  orientée par essais successifs depuis la barque (le modèle sortait couché sur le dos), maillage simplifié à facettes
  qui effaçait le visage (normales lissées, plus de triangles), buissons et cerf écartés de devant. La tête reste peu
  lisible à distance : point remonté à Olivier.
- **« Quel élément de la chaîne fixe le nombre de polygones ? »** Trois étages : la reconstruction TRELLIS.2 (maillage
  décimé à 200 000 faces dans ComfyUI, texture 2048), puis la simplification à l'import dans Unreal (60 000 triangles
  pour le pont). Essais : 400 000 faces et texture 4096 côté ComfyUI, puis 150 000 et sans simplification côté Unreal :
  rendu identique. Le manque de détail vient de la reconstruction d'une seule image, qui lisse les formes. Le fondu
  d'ouverture est avancé de 5 s ; la tête, validée sur l'aperçu, est gelée jusqu'au casque.
- **La projection, ou « l'aplat »** : la barque voit le pont sous le même angle que l'image d'Olivier ; l'image est donc
  projetée telle quelle sur sa face avant, le volume deviné par la 3D ne servant plus que de support. Silhouette
  détourée (BiRefNet ; un premier masque « ciel bleu » échouait sur le bas lavande de l'image), cadre calé sur la boîte
  du modèle. Résultat immédiat : les visages des deux figures se lisent quand on passe dessous. Olivier livre au passage
  deux textures peintes, roche et eau : la roche habille les rochers et le détail des statues, l'eau entre dans le
  shader de la rivière.
- **Enquête sur le détail 3D** (Olivier : « est-ce le Quest qui impose la limite, ou nous qui nous mettons des limites
  absurdes ? ») : un peu des deux. Meta recommande < 1,5 M triangles par image au Quest 3 ; nos 500 k étaient prudents,
  mais la scène mesurée est limitée par la géométrie. Surtout, le détail se perdait avant le Quest : le workflow
  d'exemple de ComfyUI remaillait la forme TRELLIS à 768 avec 20 passes de lissage. Rendu réglable ; à 1536 et 5 passes,
  la vue tournante du pont gagne nettement. La carte de normales déjà cuite par TRELLIS, jusque-là ignorée par le
  matériau peint, est branchée. Le fondu d'ouverture commence 3 s plus tôt (13 s, de 4,5 à 17,5 s).
- **« Ta vue 3D sur fond gris est très belle, c'est pas du tout ce que je vois dans le jeu »** : une planche de comparaison
  par itération (vue tournante + trois vues depuis la barque) a mené à deux défauts d'import, présents depuis le début.
  Nanite, activé par défaut, faisait afficher au Quest un maillage de repli au dixième ; et les réimports gardaient
  l'ancienne texture : le pont d'Olivier portait celle du substitut gris, la nouvelle barque celle de l'ancienne. Corrigé,
  le pont se lit comme sa vue tournante. La projection, astucieuse, compensait un bug qu'on n'avait pas vu.
- **Trois pistes pour le pont, comparées sur la même planche** : TRELLIS forme complète (retenue), deux figures
  reconstruites séparément (plus de détail, mais TRELLIS redresse chaque moitié de face et l'arche ne se referme plus),
  Hunyuan3D 2.1 (téléchargé avec l'accord d'Olivier : géométrie plus sculptée mais sans texture). Les petits triangles
  noirs repérés par Olivier sont des texels jamais cuits : bouchés automatiquement. Les reconstructions à 30 minutes
  venaient de la mémoire du GPU partagée avec l'éditeur Unreal ; le nœud de nettoyage d'Olivier est branché.
- **Fin de journée** : APK complet empaqueté et installé, liste de 22 points de validation au casque rédigée dans SUIVI.md
  (tout ce qui n'a été vu qu'en rendu PC depuis le matin).
- **Test au casque du soir** (Olivier, enregistrement audio commenté en direct) : fondu, arbres fixes, lanterne basse,
  canards, feuilles volantes, arbre géant validés ; le pont aux statues est le moment fort (« waouh »). À reprendre : la
  lanterne traverse la coque en tanguant, les canards se croisent, une fougère traverse un rocher 3D, les nénuphars
  manquent de résolution (saut de mipmap visible), des planches de la barque flottent, les lucioles finales montent trop
  vite et devraient s'allumer une à une. Et une remarque de mise en scène : le troupeau détourne l'attention de l'arche.
- **Corrections du soir** : lanterne recentrée, canards en cercles concentriques, rochers 3D évités par les sprites,
  nénuphars en résolution double, lucioles finales qui s'allument vraiment une à une et montent moins. Nouvel APK
  installé (19 h 07).
- **Deuxième essai du soir** : planches flottantes de la barque (la place assise passe sur le banc, plutôt que d'amputer
  le maillage qui abîmait la coque), rochers à droite retirés, vent accentué, nénuphars régénérés en grand, plus de vie
  au début, troupeau 15 s plus tôt pour laisser l'arche seule, arche à 300 k triangles, tête couchée déplacée sur la
  berge que regarde la barque. Le « bruit de voiture » de la fin : un grondement dans l'enregistrement de l'ambiance du
  lac, repéré à la part de basses fréquences de chaque demi-seconde.
- **Troisième essai du soir** : les lisses de la barque restaient visibles depuis l'arrière ; plutôt que de découper un
  maillage soudé (sans Blender), le plancher est remonté pour les couvrir. Le vent, « toujours invisible », cachait une
  erreur d'unité (la hauteur du sujet lue en échelle, pas en centimètres : 5 mm de balancement). Et une idée d'Olivier
  pour une fin « un peu morne » : un héron qui vient se poser sur le rebord de la barque, en deux images peintes
  (atterrissage, posé) animées dans le shader le long d'une courbe, attaché à la barque.
- **Reprise de la 3D et de l'eau** (Olivier : « l'eau, c'est clairement ce qui fait pas fini » ; « reprends tous les
  imports ») : Blender installé avec son accord (D9) ; tous les modèles TRELLIS régénérés avec les réglages trouvés sur
  le pont — avec le nœud de nettoyage mémoire d'Olivier, ~3 min par modèle au lieu de 27. L'eau est réécrite autour de la
  barque (sillage, étrave, écume) et en surface ; l'arche recevra des niveaux de détail plutôt que d'être allégée
  (« ou alors une version adaptative ? UE gère ça non ? » — oui, hors Nanite). Pause demandée en fin de traitement.


## 20/10 — Session autonome de nuit (Olivier : « je te rends la 3D, le casque et tout, tu as 20 h devant toi »)

- **Blender autonome** : lancé sans interface depuis WSL (2 s par démarrage). Les « deux planches » qu'Olivier voyait
  depuis la place arrière étaient les bancs : deux morceaux séparés du maillage, larges de 26 cm dans une coque de 52,
  donc suspendus dans le vide. Plutôt qu'une découpe par boîte (qui trouait la coque la veille), le script ne garde que
  le plus gros morceau du maillage ; le même nettoyage retire les débris des autres modèles. La lanterne, posée sur le
  banc avant, descend sur le plancher.
- **Tous les modèles réimportés** dans leur version fine, avec un plafond de texture par usage (4096 de près, 2048 pour
  les créatures, 1024 pour la lanterne) : la mémoire du Quest ne tiendrait pas tout en 4096. Barque à 80 k triangles.
  L'arche reçoit ses niveaux de détail (300 k / 100 k / 30 k), réponse à « UE gère ça non ? ».
- **L'eau, enfin comprise** : les rides étaient des traits allongés, orientés en travers de la rivière. Vus vers
  l'aval, ils faisaient l'eau peinte voulue ; mais dès qu'on tournait la tête, la perspective les changeait en rayons
  qui convergent — l'effet « pluie » des captures casque, et une bonne part du « pas fini ». Remplacés par un réseau de
  crêtes sans direction : c'est la perspective seule qui les écrase en traits horizontaux, quel que soit le regard. La
  pente de ces rides fait onduler les reflets. Le sillage de la veille partait de la poupe et ne se voyait pas : un vrai
  sillage de Kelvin naît à l'étrave et longe les flancs, ce qui le met sous les yeux du passager assis à l'arrière.
- **Vérifier le mouvement sans casque** : un rendu d'extrait de quelques secondes (Movie Render Queue sur une plage
  d'images) remplace l'animatic complet pour juger l'eau et le héron.
- **Héron** : l'image figée qui glissait est devenue une grille dont les ailes battent dans le shader ; les deux
  premiers rendus ont montré qu'il passait en travers de la proue, ailes immenses, et que le fondu se faisait par gros
  carrés : trajectoire par la gauche, taille réduite, fondu fin. Vu de la place assise, il semble debout dans l'eau ;
  une vue de dessus montre qu'il est bien sur le plat-bord — la perspective d'un sprite plat trompe, la stéréo tranchera.
- **Troupeau** régénéré (remaillage à 1024 : la mémoire ne suffit pas à 1536 pour ce modèle).
- **Sons du héron** : la règle du projet veut un repère sonore avant chaque créature. Cri d'aigrette (Freesound, CC0) au
  loin 2,5 s avant qu'il n'apparaisse, battements d'ailes quand il freine ; l'émetteur suit la même courbe que le shader,
  le son vient donc de l'oiseau. Choisis sans pouvoir les écouter : enveloppe et spectre analysés (cris bien au-dessus du
  fond, pas de grave parasite — la leçon du « bruit de voiture »), validation à l'oreille laissée à Olivier.
- **Animatic complet** relu (iter-054) : l'eau tient sur tout le parcours, de jour comme de nuit. APK installé ; le
  casque, posé, attend d'être porté pour la mesure de fluidité.

## 20/10 matin — essai au casque d'Olivier, puis corrections

- **Mesure casque porté** : malgré la barque à 80 k triangles et l'eau plus riche, la balade est plus fluide que la veille
  (les niveaux de détail de l'arche ont payé) ; seul creux sous l'arche (65 i/s), qu'Olivier n'a pas senti.
- **Retour** : « la barque est super propre », lanterne et pont validés. Mais le sillage reste « très très léger » et
  « on voit l'eau un petit peu sous la barque » : la zone sans eau du shader était encore l'ellipse de l'ancienne barque,
  plus large que la nouvelle coque pointue — un reste de la barque précédente, invisible en captures, flagrant au casque.
  Forme de coque mesurée dans Blender à la flottaison.
- « J'ai enfin compris ce qui me choquait : leurs animations sont synchronisées » : le troupeau avait bien un décalage de
  pas par animal… réglé par une fonction d'exécution, non sauvegardée avec le niveau. Toutes les bêtes repartaient à zéro.
- Le casque posé : un essai réussi juste après qu'Olivier l'a reposé, puis perte de suivi dans la pièce sombre.

## 20/10 matin — eau en relief, particules, assets d'Olivier

- « Ton souci c'est que l'eau reste une surface plane » : l'article d'Epic sur Still Wakes the Deep (simulation d'eau peu
  profonde dans Niagara, le corps du joueur comme « pompe », particules) sert de piste. Version Quest retenue pour la
  journée : hauteur d'eau calculée (houle, sillage), grille fine déplacée autour de la barque, reflets sur la pente des
  vagues, nénuphars qui flottent, flocons d'écume et feuilles qui dérivent. La vraie simulation attend un redémarrage de
  l'éditeur (plugin Niagara Fluids), que seul Olivier peut faire.
- La ligne droite qui traversait le lac venait du brouillard calculé aux sommets d'une grille de 5 m : trois fausses
  pistes (reflet, carte de l'eau, fond) avant de la trouver, par élimination.
- Olivier demande un « top 3 » d'images à fournir : ciel de nuit, arbre de l'île, plancher de la barque — ce qui restait
  généré en local et se voit le plus. Livrés dans l'heure ; son idée de retourner le ciel de nuit pour caler ses nuages
  sur ceux du jour donne un fondu presque sur place.
- Le casque posé ne tient pas son suivi dans la pénombre ; l'appli se fige faute de suivi. Mesure relancée toutes les
  30 min, ne gardant que les mesures où le GPU travaille vraiment.

## 20/10 soir — écume, essai Niagara

- Au casque : « j'aime beaucoup », « l'eau c'est très chouette », fluide. Mais l'écume reste invisible. Trois causes
  empilées, trouvées par diagnostics en couleur vive dans le rendu : le plat-bord cache toute l'eau à ~1,1 m de l'axe
  depuis la place assise ; un smoothstep écrit à l'envers vaut zéro à la compilation (il effaçait aussi une partie des
  ailes du héron) ; le motif de découpe était fait de lignes fines. Écume refaite en V qui dépasse du plat-bord, bande
  pleine puis dentelle.
- Essai de la simulation d'eau Niagara Fluids (piste de l'article Still Wakes the Deep), après un redémarrage de
  l'éditeur : un premier APK vide (système posé après l'enregistrement du niveau), puis un second où Olivier la voit —
  « c'est très moche ». Le modèle brut n'est pas exploitable ; mis en pause au profit de l'eau calculée.

## 21/10 nuit — textures, buissons, tangage

- « La barque c'est bien là dans le casque ! Globalement c'est très abouti. » La netteté venait d'un réglage caché : le
  profil Quest 3 d'Unreal hérite d'un profil Android moyen, qui affiche toutes les textures un niveau en dessous et coupe
  le filtrage anisotrope. Trouvé dans le journal du casque, corrigé par un profil propre au projet.
- Une vidéo 4K « tout à fond » pour comparer au casque : même contenu, plus net. La version PC VR « plus riche » sort du
  périmètre (Olivier : avec les sprites, pas de contrainte de polygones).
- Répétitions de buissons : avec 16 images et ~8 buissons dans 5 m, le hasard seul mettait des jumeaux côte à côte.
  Répartition gloutonne (aucun voisin identique, entre images de même rôle et de même taille) et 16 images de plus ;
  prompts complets pour qu'Olivier les refasse dans son style.
- Bête volante qui « tombe » au fondu : sa trajectoire dépassait la fin de la séquence de 0,4 s, et la clé qui cache les
  créatures après leur passage s'insérait avant ses dernières positions. Invisible au rendu PC, qui s'arrête juste avant.
- Tangage de la barque (idée d'Olivier, puis « la barque est vraiment trop fixe ») : un pivot porte la coque, la lanterne
  et le héron, pas la caméra — la règle « jamais de roulis caméra » tient, la barque bouge sous le spectateur. Premier
  essai : la coque disparue, restée à l'origine du monde (un parent « mobile » refuse des enfants « statiques »).
- Nettoyage du dépôt (demandé par Olivier) : les vidéos de rendu poussées en LFS au fil des jours — dont 2,4 Go de vidéos 4K
  commitées par erreur, la règle d'exclusion ne couvrant pas leur nom — pesaient près de la moitié du stockage. Historique
  réécrit en local (après sauvegarde complète), dépôt GitHub supprimé et recréé, puis repoussé : 3,9 Go au lieu de ~7,3.
  Réécrire seul n'aurait rien libéré côté GitHub, qui garde les objets LFS tant que le dépôt existe.
