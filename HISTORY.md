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
