# Une IA peut-elle faire une démo VR toute seule ?

*Six jours, Claude Code, Unreal Engine et un casque Quest 3. J'ai demandé à une IA de construire une balade en réalité virtuelle, de la première ligne de code à l'application installée dans mon casque. Ce qu'elle a su faire seule, et ce que j'ai appris d'Unreal en la regardant travailler.*

![Le lac du final, la nuit : un héron blanc posé à l'avant d'une barque en bois, des lucioles, un arbre sur une île et la lune.](/wp-content/uploads/2026/10/barque-01-heros.jpg)

*Le lac, à 3 min 52 : le héron vient de se poser sur la barque. Image de la version finale, rendue sur PC.*

Ces derniers mois, les IA ont fait un bond, et les MCP se sont multipliés. Un MCP, c'est un connecteur qui laisse une IA piloter un logiciel : Unreal Engine a maintenant le sien, Blender aussi, et on en trouve pour ComfyUI, l'outil de génération d'images que j'utilise. Sur le papier, une IA peut donc faire tourner seule les outils d'un studio de jeu vidéo. J'ai voulu voir ce que ça donne en vrai.

Le terrain d'essai est volontairement modeste : une démo VR de quatre minutes, sans interaction, qui tourne sur mon Quest 3. On est assis dans une barque qui dérive sur une rivière en forêt, du crépuscule à la nuit, dans le style des dessins animés japonais des années 80 et 90. La règle du jeu : pousser l'autonomie de l'IA au maximum. Elle écrit le code, génère les images et la 3D, choisit les sons, construit la scène dans Unreal, compile l'application, l'installe dans le casque et mesure sa fluidité. Moi, je fournis quelques images de référence et la musique, je mets le casque et je dis ce qui ne va pas.

L'IA, ici, c'est Claude Code, l'agent de programmation d'Anthropic, avec le modèle Claude Opus 5.5. Je l'appellerai simplement l'agent. Il a travaillé du samedi 17 octobre, 14 heures, au vendredi 23, midi.

Au bout de ces six jours, la balade tournait à 72 images par seconde dans le casque, et j'avais mes réponses aux trois questions de départ. Jusqu'où une IA peut-elle aller seule sur un projet comme celui-là ? Audio IA, assets IA : qu'est-ce qu'on sait faire en octobre 2026 ? Et qu'est-ce que j'allais apprendre d'Unreal Engine, que je ne connaissais que côté joueur ?

Tout ce qui illustre cet article sort du dépôt du projet : captures du casque, vidéos de contrôle, mesures, journaux. L'agent a tout gardé.

[video mp4="/wp-content/uploads/2026/10/barque-02-bande-annonce.mp4" poster="/wp-content/uploads/2026/10/barque-02-bande-annonce-poster.jpg" width="1920" height="1080" preload="metadata"][/video]

*La bande-annonce : huit plans de la version finale, rendue sur PC en 4K. Dans le casque, l'image est moins fine.*

## Le terrain d'essai

### La balade

La rivière fait 239 mètres. La barque la descend à un mètre par seconde, sans jamais accélérer, et la caméra ne penche jamais sur le côté : ce sont les deux règles de base pour ne rendre personne malade en VR assise. Les yeux sont à 1,10 m au-dessus de l'eau, et le parcours ne tourne jamais de plus de 1,15 degré par seconde.

Sept moments ponctuent les quatre minutes : le noir et le clapotis du départ, le ponton dans la brume, une bête lumineuse qui passe sous l'eau tout près de la barque, un troupeau qui traverse un gué, le passage sous un pont de statues, une créature géante devant la lune, puis le lac du final, où un héron vient se poser sur la barque.

![La rivière vue de dessus avec ses sept moments, une vignette par moment, et la forme d'onde de la musique avec le début de chaque moment.](/wp-content/uploads/2026/10/barque-04-balade.jpg)

*La balade vue de dessus, une image par moment (rendu PC de la version finale), et la musique sur laquelle tout est calé.*

La musique commande tout. « Luminous Wonder » est un morceau que j'ai généré sur Suno. L'agent en a analysé la structure et repéré les frontières : la plus forte, une modulation, tombe à 2 min 38 dans la démo et ouvre la scène de la lune. Après le noir du début, chaque moment démarre sur une de ces frontières. Le séquencier suit la musique, jamais l'inverse.

### L'atelier

Côté matériel, rien d'exotique : un PC sous Windows avec WSL2, une RTX 3090 de 24 Go et le Quest 3 branché en USB. La carte graphique est partagée entre Unreal, ComfyUI et Blender, et l'agent ne lance jamais deux calculs lourds à la fois : un fichier verrou fait office de feu rouge.

L'agent tourne dans WSL2 et pilote tout le reste : Unreal Engine 5.8 avec son serveur MCP, ComfyUI en local avec ses modèles d'image et de 3D (Z-Image Turbo, Qwen-Image-Edit, TRELLIS.2, Pixal3D, BiRefNet), Blender sans interface, Freesound pour des sons du domaine public, GitHub pour le code. Le casque se pilote par adb, l'outil de débogage d'Android : installer l'application, la lancer, capturer la vue du casque, lire la fréquence d'images. De mon côté, deux abonnements, Midjourney pour les images de référence et Suno pour la musique. L'agent n'a utilisé aucun service payant en dehors de Claude lui-même.

![Schéma de l'atelier : Olivier, les fichiers du projet, l'agent au centre, et un canal par outil (Unreal, ComfyUI, Blender, Freesound, GitHub), puis le Quest 3.](/wp-content/uploads/2026/10/barque-03-atelier.png)

*L'atelier. Mes demandes et mes retours passent par la conversation, et la mémoire du projet tient dans quelques fichiers. Chaque outil a son canal ; l'agent et moi rejoignons le casque par deux chemins différents.*

### Les règles

Le projet tient dans un fichier de consignes, CLAUDE.md, que l'agent relit au début de chaque session. On y trouve la vision, le séquencier, les contraintes du Quest, et surtout une méthode. Cinq règles font l'essentiel du travail :

1. La scène est du code. Tout ce qui la construit est un script Python versionné et rejouable, et une seule commande, `python pipeline/build.py`, reconstruit le projet depuis zéro.
2. Le MCP sert à explorer. Toute modification retenue passe dans un script avant le commit.
3. Tester petit avant de produire en série : deux ou trois essais courts, vérifiés, avant tout lot.
4. Une décision attendue reçoit un défaut réversible. L'agent l'applique, la note avec ce qui changerait si je tranchais autrement, et continue.
5. Pas de service payant, d'installation de logiciel ni d'envoi de données vers un service imprévu sans mon accord écrit.

Deux fichiers tenus par l'agent complètent le dispositif. SUIVI.md donne l'état du projet : blocages, décisions en attente, points à vérifier au casque. HISTORY.md est le journal, une entrée par itération, et chaque itération donne un commit. Quand je reviens après une nuit, c'est le suivi que je lis.

Mon rôle tient en une ligne du fichier : directeur artistique et relecteur. Je ne touche ni au code ni à la scène.

## Six jours en accéléré

![Graphique des commits heure par heure sur six jours, nuits grisées, avec au-dessus les moments-clés du projet.](/wp-content/uploads/2026/10/barque-05-commits.png)

*134 commits en six jours, heure par heure. La nuit est grisée.*

L'agent a fait 134 commits : 16 le premier après-midi et le premier soir, puis 31, 38 et 30 les trois jours suivants, et encore 19 sur la fin, de part et d'autre d'une pause de 37 heures. Le graphique montre aussi ses nuits. Je lui ai laissé les clés trois fois pour longtemps : huit heures le 18 au soir « pour repenser la scène complète », six heures sans casque le 19 après-midi, puis vingt heures d'un coup : « je te rends la 3D, le casque et tout, tu as 20 h devant toi ».

Le premier jour a donné le ton. À 14 h 30, trente musiques générées en local, aucune écoutée, et ma réponse : « C'est long et c'est moche. » Unreal était installé à 19 h, la première application pour le Quest compilée à 20 h 49. Peu après minuit, je pouvais m'asseoir dans le casque, au milieu d'un premier décor de formes grises.

Le deuxième jour, j'ai appris qu'un casque autonome ne sait pas appliquer de filtre « dessin animé », et l'agent a passé l'après-midi à gagner des millisecondes. Le soir, une phrase a tout changé : « le truc le plus moche ce sont les arbres ». Dans la nuit, la forêt entière était refaite en images peintes.

La suite tient en 69 itérations de revue au total, et en quelques chantiers qui reviennent : les statues, l'eau, le tangage, une bête sous l'eau, un héron. Le 23 octobre à 11 h 45, l'agent a installé une version finale dans le casque, à côté de la version de travail.

Toutes les vidéos de contrôle rendues pendant ces six jours suivent exactement la même trajectoire de caméra. Un même instant de la balade se retrouve donc, au même cadrage, d'une version à l'autre. Dans le montage qui suit, la barque avance sans coupure et le décor change de version toutes les six secondes.

[video mp4="/wp-content/uploads/2026/10/barque-06-pont-versions.mp4" poster="/wp-content/uploads/2026/10/barque-06-pont-versions-poster.jpg" width="1920" height="1080" preload="metadata"][/video]

*Le passage du pont, de 1 min 38 à 2 min 20, en sept versions du 19 au 23/10 (rendus PC). La date et le changement sont incrustés.*

Les captures du casque racontent la même histoire avec l'image du Quest lui-même : celle qu'affiche le casque, capturée par l'agent.

[video mp4="/wp-content/uploads/2026/10/barque-07-casque-timelapse.mp4" poster="/wp-content/uploads/2026/10/barque-07-casque-timelapse-poster.jpg" width="1080" height="1080" preload="metadata" loop="on"][/video]

*Trois instants de la balade (0 min 30, 1 min 52, 3 min 52), vus dans le casque du 18 au 23/10.*

## Jusqu'où l'agent est allé seul

### Ce qui le fait avancer

La première leçon date du premier après-midi, et elle vaut autant pour moi que pour lui. Ma toute première demande : une chaîne de production musicale sur ACE-Step, un modèle qui tourne en local, en explorant trente graines en brouillon avant de rendre la meilleure en qualité. L'agent l'a fait à la lettre, sans pouvoir écouter une seule note. Une demi-heure plus tard, je lui écrivais : « Y'a pas vraiment de mélodie et après 15 s on dirait des loops qui se répètent […] je vois pas pourquoi t'en génères 30. C'est long et c'est moche. » La règle « tester petit » est née là. Le fichier de consignes le dit maintenant en une phrase : « Un fichier techniquement valide ne dit rien de sa qualité. »

La deuxième règle, c'est le défaut réversible. Le premier soir, avant même qu'Unreal soit installé, l'agent avait neuf décisions en attente : quelle image sert de référence de style, où couper entre deux moments, à quelle échelle faire les créatures, quelle forme donner à la coque. Plutôt que de m'attendre, il applique un défaut, le note dans le suivi, et continue. Il y en a eu vingt sur le projet. J'en ai tranché certaines au casque. D'autres jamais : le défaut tenait.

![Schéma d'une itération : lire l'état, changer un script, reconstruire, vérifier, commiter, puis recommencer ; au-dessus, Olivier teste l'application et renvoie ses retours.](/wp-content/uploads/2026/10/barque-08-iteration.png)

*Une itération. L'agent boucle seul ; mes retours entrent dans la boucle quand j'ai le temps.*

Troisième règle, la scène comme du code : 58 scripts Python, un peu plus de 10 000 lignes, et une commande qui reconstruit tout. J'en ai vu l'intérêt dès le premier jour : « comme on automatise tout en Python je peux reprendre un élément sans tout refaire ». Une meilleure image, une autre musique : on dépose le fichier, on relance le script concerné. Il y a un revers. Chaque reconstruction réécrivait des fichiers binaires et faisait gonfler le dépôt, jusqu'à ce que l'agent ne réécrive plus que ce qui a changé.

Le soir du deuxième jour, je lui ai envoyé une liste de défauts vus au casque, avec une consigne : enquêter sans toucher au casque. Il a consigné cinq symptômes et cinq causes avant de corriger quoi que ce soit. Le plancher dont la texture défilait : une texture projetée en coordonnées du monde, sur un objet qui avance. La voix entendue à l'entrée du lac : de la parole anglaise dans un enregistrement de Freesound, détectée par Whisper. Le brouillard « peu visible » : à 154 mètres, il ne voilait encore que la moitié de l'image.

### Ce qu'il a fait pendant que je n'étais pas là

La nuit du 18 au 19 en donne la mesure. Vers 23 h 30, je valide l'idée des arbres peints et je lui laisse huit heures « pour repenser la scène complète et ajouter plus de vie et de volumes ». À 0 h 38, il commite une forêt entièrement repeuplée : un catalogue de familles d'images, leur génération en local, leur placement, un seul matériau pour toutes. Suivent des plantes qui luisent la nuit, une lanterne qui tangue, un arbre colossal repeint, et une reconstruction complète du projet vérifiée vers 1 h 45. Seul accroc : à 1 h 30, l'interface du Quest s'est mise à planter en boucle, et le casque a disparu du câble USB.

Pendant les vingt heures du 19 au 20, il a appris à piloter Blender sans interface (deux secondes par lancement), retiré deux bancs qui flottaient dans la barque, régénéré et réimporté tous les modèles 3D, compris pourquoi l'eau faisait « pas fini », puis animé le héron du final et lui a donné un cri.

Le casque aussi, il le pilote à distance. Il installe l'application, la lance, capture la vue et mesure la fluidité, tout par adb. Le 19 au matin, le Quest posé sur le bureau perdait son suivi de position et affichait une boîte de dialogue système qui bloquait l'application. Je l'ai autorisé à cliquer « Continuer sans le suivi ». L'arbre d'interface d'Android ne permettait pas d'atteindre le bouton ; il est passé par le clavier, flèche bas puis validation, en vérifiant chaque pas par une capture. Verdict : sans suivi de position, le Quest refuse d'ouvrir une application VR. Le casque a besoin de lumière pour se repérer. Le lendemain, dans la pénombre, l'agent relançait sa mesure toutes les trente minutes et ne gardait que celles où la carte graphique calculait bien la scène.

### Les MCP, en vrai

J'étais parti avec l'idée que les MCP feraient le gros du travail. Celui d'Unreal n'exposait d'abord que la gestion de ses « skills » ; il a fallu activer ses jeux d'outils (éditeur, PCG, Niagara, configuration) pour qu'il serve à quelque chose. Ensuite, il a servi à regarder : inspecter la scène, interroger des objets, capturer la vue de l'éditeur.

Pour construire, l'agent est passé par des scripts Python, exécutés dans l'éditeur ouvert ou par Unreal en ligne de commande. ComfyUI, il le pilote par son API, avec des workflows enregistrés et des graines fixées. Blender, par un script, sans fenêtre. La raison tient dans la deuxième règle : un geste fait par MCP ne se rejoue pas, un script si. Quand tout le projet se reconstruit d'une commande, on peut tout casser sans crainte.

Mon point de départ était donc à moitié juste. Les MCP donnent à l'IA des yeux dans les outils, mais sur six jours, ce sont les scripts qui ont tenu le projet debout.

### Le casque, l'angle mort de l'agent

L'agent voit des images : les captures de revue, les vidéos rendues sur PC, la vue du casque capturée par adb. Il lit des mesures. Ce qui lui échappe, c'est tout ce qui passe par le corps : le relief que donnent deux yeux, l'échelle, le mouvement de la tête, le confort, le son.

![Tableau : ce que l'agent pouvait juger seul (l'image, la fluidité), en partie (le son, le confort) ou pas du tout (le relief, la tête qui bouge), avec à côté ce qu'Olivier a vu au casque.](/wp-content/uploads/2026/10/barque-09-sens.png)

*Ce que l'agent pouvait juger seul, et ce qui me revenait.*

L'épisode le plus parlant date du deuxième soir. L'agent m'annonce 72 images par seconde. Le chiffre était juste, mais le casque, posé sur le bureau, regardait le ciel. Droit devant, au niveau de la rivière, on était à 62. Depuis, il capture la vue du casque avant toute mesure, pour savoir ce qu'il mesure.

![Capture du casque posé sur un bureau : l'intérieur de la barque vu de travers, un coin noir hors de l'image.](/wp-content/uploads/2026/10/barque-10-casque-pose.jpg)

*Ce que voit le casque posé sur le bureau : l'intérieur de la barque, de travers. Une mesure de fluidité prise dans ces conditions ne vaut rien.*

Ce que l'écran cache, le casque le montre tout de suite : des arbres peints qui pivotent avec la tête, des bandes verticales qui scintillent parce que des plans se croisent différemment pour chaque œil, ou encore le masque qui empêche l'eau d'entrer dans la barque, resté à la forme de l'ancienne coque, une ellipse, alors que la nouvelle est pointue. Aucun de ces défauts ne se voyait sur les captures.

Le troupeau, lui, m'a gêné pendant deux jours avant que je trouve les mots : « J'ai enfin compris ce qui me choquait : leurs animations sont synchronisées. » Chaque bête avait bien son propre décalage de pas, mais réglé par une fonction qui n'était pas sauvegardée avec le niveau. Au lancement, toutes repartaient de zéro, ensemble.

Le dernier matin, je n'arrivais toujours pas à montrer un défaut : « j'ai essayé de faire des screenshots mais pas très pratique ». J'ai demandé un raccourci sur le bouton A de la manette. L'agent a dû apprendre deux choses en route : la commande de capture du moteur n'avait jamais été essayée sur un Quest (elle marche, et donne l'image de l'œil gauche en pleine définition), et OpenXR ne remonte une touche que si elle est liée à une action déclarée dans la configuration. Chaque capture est datée par l'instant de la balade, lu dans le journal de l'application.

Le premier usage a été le bon. Mes trois captures pointaient un « bug de texture » sur la droite, avant le gué. C'était une bande de forêt peinte, un plan de 160 mètres de large vu par la tranche, dont l'agent n'avait vérifié que le centre. Le défaut avait déjà été signalé et « corrigé » la veille, mais sur un seul des deux anneaux de bandes qui ferment l'horizon. Tant qu'il raisonnait sur l'aspect, l'agent a cherché du côté du troupeau, du bois mort, d'une statue, des feuillages. Il l'a trouvé en rendant l'éditeur au même instant que ma capture et en masquant les objets par moitiés : sept rendus. La leçon est dans son journal : un objet plat se vérifie sur toute son étendue, et une capture datée vaut mieux qu'une description.

![Capture au casque sur la berge droite : de grands aplats verts au milieu des arbres peints.](/wp-content/uploads/2026/10/barque-11-bouton-a.jpg)

*Une de mes captures au bouton A, à 1 min 58 : les aplats verts sont une bande de forêt peinte vue par la tranche.*

### Ce qui reste à l'humain

Le goût, d'abord. Les deux phrases qui ont le plus changé la démo sont des jugements : « le truc le plus moche ce sont les arbres », et le lendemain soir, « l'eau, c'est clairement ce qui fait pas fini ». Dans les deux cas, l'agent a trouvé la solution. Il n'avait pas désigné le problème.

Les idées de mise en scène, ensuite. Le pont de statues vient d'un souvenir de cinéma, la descente en barque du Seigneur des Anneaux entre deux statues géantes. Le héron du final vient d'une fin que je trouvais « un peu morne », le tangage d'une barque « vraiment trop fixe ». L'agent les a mises en œuvre ; aucune de ces trois idées ne venait de lui.

Restent le périmètre (« ne fais rien de plus », « tout noter sans corriger »), les accords pour installer Blender ou télécharger un modèle 3D, et le corps : redémarrer le casque, redémarrer l'éditeur pour activer un plugin, poser le Quest à la lumière, le mettre sur la tête.

![Tableau des tâches avec, pour chacune, la part d'Olivier, celle de l'agent et les outils utilisés.](/wp-content/uploads/2026/10/barque-12-roles.png)

*Qui a fait quoi, tâche par tâche, d'après le journal et le manifeste des assets.*

## Images, 3D, son : ce qui marche en octobre 2026

### Les images peintes ont sauvé la forêt

Le soir du deuxième jour, après une journée passée à gagner des millisecondes, la forêt restait le point faible : des arbres en 3D aux feuillages en boules texturées, qui faisaient jeu des années 90. L'agent a proposé trois pistes : des plans peints, des touffes festonnées, un autre décor. J'ai voulu les voir toutes : « Tu peux proposer les différentes idées sur les arbres dans le même APK ? » Vingt-quatre minutes plus tard, j'avais une application où la forêt changeait toutes les douze secondes, avec une lettre à la proue : A pour les arbres 3D, B pour des arbres peints, C pour des touffes ombrées. Mêmes positions, même fluidité.

[metaslider id="REMPLACER-barque-13-arbres-abc"]

*L'application de comparaison vue au casque : la même forêt en arbres 3D (A), en arbres peints (B) et en touffes ombrées (C).*

Le verdict est tombé à 23 h 30 : « les arbres peints ça rend vachement bien ! […] ça prend tellement moins de polygones qu'il faut creuser en ce sens ». Un arbre peint, c'est une image posée sur un plan de deux triangles ; l'arbre 3D qu'il remplaçait en comptait 2 700, pour un résultat bien pire. Les décors de dessin animé sont faits comme ça, et le jeu vidéo a un nom pour ce procédé : le billboard, ou imposteur.

Cette nuit-là, l'agent a construit un système complet : un catalogue de familles d'images, leur génération et leur détourage en local, leur placement par script, un matériau unique. La démo compte aujourd'hui 114 images peintes. Elles sont posées 7 837 fois dans le décor, et 749 fois en mouvement : oiseaux, papillons, libellules, feuilles et pétales qui tombent. La forêt 3D a disparu, et c'est ce qui paie le reste : sur une scène bien plus dense, la démo tenait toujours 72 images par seconde.

![Seize images peintes détourées : arbres, saule, sapin, arbuste en fleurs, hortensia, iris, tronc mort, nénuphar, faon, renard, martin-pêcheur, canard, hirondelle, papillon, chouette, champignons lumineux.](/wp-content/uploads/2026/10/barque-14-images-peintes.jpg)

*Seize des 114 images peintes, générées en local et détourées.*

La chaîne tient en quatre étapes. Z-Image Turbo, un modèle d'image qui tourne sur la carte graphique du PC, peint un sujet seul, sur fond gris uni, éclairé par la gauche. BiRefNet le détoure. Un script nettoie le résultat, puis l'agent pose l'image dans la scène. Les ratés ont été nombreux : des restes de fond autour des feuillages, des nuages qui s'invitaient dans les images, une plaque d'herbe peinte sous chaque tronc, des textures importées en 32 pixels par Unreal, une forêt où le même arbre revenait sans cesse (« la texture des arbres sur la gauche se répétait beaucoup trop souvent »), et la moitié des arbres éclairés du mauvais côté le jour où l'agent en a retourné une sur deux pour casser la répétition.

![Quatre étapes : l'image générée sur fond gris, son masque de détourage, l'image détourée, puis la forêt vue au casque.](/wp-content/uploads/2026/10/barque-15-chaine-images.jpg)

*D'une image générée à la forêt du casque : l'image brute, le masque, l'image nettoyée, puis la scène.*

### Ce que j'apporte encore

Les images de référence viennent de moi, sur Midjourney : des ambiances pour plusieurs moments, la barque, le ponton, la lanterne, les créatures, des textures, deux ciels. L'agent écrit les prompts dans un fichier dédié, avec une consigne : jamais de nom de studio ni d'artiste. Ma texture de mousse a servi de modèle pour repeindre les autres textures en local, avec Qwen-Image-Edit. Elles restent moins belles que l'originale.

![Deux images de référence d'Olivier, le départ et le lac, à côté des mêmes lieux dans la démo.](/wp-content/uploads/2026/10/barque-16-reference-resultat.jpg)

*Mes images de référence, à gauche, et les mêmes lieux dans la démo, à droite (rendu PC).*

Un mot sur le style. Le projet le décrit comme « inspiré de l'animation japonaise des années 80-90 », sans plus. Aucun prompt ne nomme de studio ni d'artiste, et les créatures sont des designs originaux. Le premier soir, l'agent a quand même consigné une alerte : un concept provisoire montrait des créatures trop proches de celles d'un film d'animation connu. Il n'a servi qu'à extraire une palette de couleurs.

### De l'image à la 3D

Pour les objets principaux, l'agent reconstruit un modèle 3D à partir d'une seule image, en local. Le premier jour, il a comparé deux modèles, TRELLIS.2 et Pixal3D, sur sept de mes images. Chacun gagne sur des objets différents : TRELLIS.2 sur la lanterne, le ponton, le troupeau et la créature volante, Pixal3D sur la bête des abysses. On a gardé les deux. Les silhouettes sont justes ; le détail est lissé, et l'arrière de l'objet, que l'image ne montre pas, est deviné.

![La barque : l'image de départ d'Olivier, puis deux reconstructions 3D, Pixal3D et TRELLIS.2, chacune sous quatre angles.](/wp-content/uploads/2026/10/barque-17-barque-3d.jpg)

*La barque : mon image de départ, puis deux reconstructions 3D faites en local, Pixal3D et TRELLIS.2, chacune sous quatre angles.*

Le pont est l'histoire la plus complète du projet. Le deuxième soir, je lance une idée en passant : « la fameuse descente en barque du Seigneur des Anneaux quand ils passent entre les deux statues géantes, mais ça ferait changer beaucoup d'ambiance, à débattre ensemble ». Le lendemain, l'agent revient avec trois concepts aux designs originaux, générés en local : deux gardiens moussus, une tête couchée dans la rivière, une arche faite de deux figures agenouillées. J'ai adoré le pont. La tête était « trop belle » pour ne pas finir sur une berge.

![Trois concepts peints vus depuis une barque : deux gardiens de pierre moussus, une tête couchée dans l'eau, une arche formée de deux figures agenouillées.](/wp-content/uploads/2026/10/barque-18-statues.jpg)

*Les trois concepts proposés par l'agent à partir de mon idée.*

J'ai fait l'image du pont sur Midjourney, en pierre nue : passée en 3D, la mousse se transforme en blocs. L'idée était d'obtenir un objet sans végétation, à habiller ensuite. L'agent l'a reconstruit avec TRELLIS.2, a calculé la mousse dans le matériau, sur les faces tournées vers le haut, et l'a posé sur la rivière. Au casque, le soir même : « waouh ».

![Le pont en quatre étapes : l'image Midjourney d'Olivier, le modèle 3D, le pont dans la scène, puis vu au casque.](/wp-content/uploads/2026/10/barque-19-chaine-3d.jpg)

*Le pont, de mon image Midjourney au casque.*

Deux questions m'ont occupé entre-temps : « Quel élément de la chaîne fixe le nombre de polygones ? », puis « est-ce le Quest qui impose la limite, ou nous qui nous mettons des limites absurdes ? ». Réponse : un peu des deux. Meta recommande de rester sous 1,5 million de triangles par image sur le Quest 3, et nos 500 000 étaient prudents. Mais le détail se perdait avant le casque : le workflow d'exemple de ComfyUI remaillait la forme sortie de TRELLIS à une résolution de 768, avec vingt passes de lissage. À 1 536 et cinq passes, le pont gagne nettement.

Puis une de mes remarques a débusqué deux bugs : « Ta vue 3D sur fond gris est très belle, c'est pas du tout ce que je vois dans le jeu. » L'agent a monté une planche de comparaison, la vue tournante du modèle à côté de trois vues depuis la barque, et trouvé deux défauts d'import présents depuis le début. Nanite, la géométrie virtualisée d'Unreal, activée par défaut, faisait afficher au Quest un maillage de secours dix fois plus pauvre. Et les réimports gardaient l'ancienne texture : mon pont portait celle de son substitut gris, la nouvelle barque celle de l'ancienne. L'agent venait de projeter mon image sur la face avant du pont pour rattraper le détail. Son journal le résume : « La projection, astucieuse, compensait un bug qu'on n'avait pas vu. »

[metaslider id="REMPLACER-barque-20-pont-versions"]

*Le pont et son passage en sept versions, au même instant de la balade (1 min 52).*

Dernier essai, Hunyuan3D 2.1, téléchargé avec mon accord : une géométrie plus sculptée, mais sans texture. On est resté sur TRELLIS.2. Les reconstructions prenaient 27 minutes, jusqu'à ce qu'on comprenne que la mémoire de la carte graphique était partagée avec l'éditeur d'Unreal ; avec un nœud de nettoyage de la mémoire branché dans ComfyUI, on est tombé à trois minutes par modèle.

### La musique vient de Suno

L'échec d'ACE-Step ne s'est pas arrêté aux trente brouillons. Après un prompt réécrit, la mélodie était meilleure, mais « ça fait son midi, ça sature dans les aigus ». L'agent l'a confirmé par la mesure : un son deux fois plus brillant que celui d'un morceau de Suno (le centroïde spectral, le centre de gravité du spectre), et une stéréo déphasée. À 14 h 45 le premier jour, on a tranché : la musique viendrait de Suno, générée par moi sur un prompt écrit par l'agent. À 15 h, « Luminous Wonder » était dans le dépôt.

Suno fournit aussi les pistes séparées d'un morceau, les stems. J'ai déposé les dix, et l'agent les a placées autour de la barque, en douze sources sonores : le clavier devant à droite, à hauteur de la proue, les basses sous la barque, là où passera la bête, les cordes en nappe derrière, les cuivres à douze mètres devant. Dans le casque, la musique vient de quelque part.

![Vue de dessus de la barque et du spectateur, avec les pistes de la musique placées autour : clavier, guitare, bois, cuivres au loin, cordes et nappe de synthé en sources larges, basses sous la barque, percussions derrière.](/wp-content/uploads/2026/10/barque-21-son.png)

*Les pistes de la musique, placées autour du spectateur assis.*

### Les sons, choisis sans oreilles

L'agent ne peut rien écouter. Il a pourtant choisi les dix-sept sons de la démo dans la banque Freesound, uniquement parmi ceux qui sont dans le domaine public. Pour compenser, il mesure. Whisper, un modèle de transcription, lui dit s'il y a de la parole : c'est comme ça qu'il a trouvé la voix anglaise que j'avais entendue à l'entrée du lac, au début d'un enregistrement d'ambiance. Le niveau sonore et la part de basses fréquences lui signalent la circulation ou le vent.

Le 19 au soir, je lui signale qu'à la fin, « on croit entendre une voiture qui démarre ». Il découpe l'ambiance du lac en demi-secondes, mesure la part de graves de chacune, et trouve un grondement 33 secondes après le début du passage joué. L'ambiance s'arrête maintenant deux secondes avant.

![Spectrogramme de l'ambiance du lac et courbe du niveau des graves, avec la zone de voix au début, le passage gardé dans la démo et le grondement juste après.](/wp-content/uploads/2026/10/barque-22-lac.jpg)

*L'ambiance du lac lue sans l'écouter : la voix du début, le passage gardé, puis le grondement.*

Même méthode pour le héron, dont le cri précède l'arrivée de deux secondes et demie et vient de sa direction : l'agent a vérifié l'enveloppe et le spectre des enregistrements, et m'a laissé, je cite, « la validation à l'oreille ».

[video mp4="/wp-content/uploads/2026/10/barque-23-heron.mp4" poster="/wp-content/uploads/2026/10/barque-23-heron-poster.jpg" width="1920" height="1080" preload="metadata"][/video]

*Le héron du final, précédé de son cri. Dans le casque, le son vient de sa direction ; dans cette vidéo, il est centré.*

### Le bilan, outil par outil

| Ce qu'on a demandé | Outil | Où | Verdict |
|---|---|---|---|
| Décors peints | Z-Image Turbo, BiRefNet | en local | excellent, c'est ce qui a sauvé la forêt |
| Images de référence | Midjourney | mon abonnement | excellent |
| Textures repeintes, vues manquantes | Qwen-Image-Edit | en local | correct, moins beau que Midjourney |
| 3D depuis une image | TRELLIS.2, Pixal3D | en local | bonnes silhouettes, détail lissé |
| 3D, autre essai | Hunyuan3D 2.1 | en local | plus sculpté, sans texture : écarté |
| Musique | ACE-Step | en local | décevant |
| Musique | Suno | mon abonnement | excellent, pistes séparées comprises |
| Sons | Freesound, Whisper | en ligne (gratuit), en local | bon, par la mesure ; rien de généré |
| Relief tiré des images | Depth Anything | en local | ne tournait pas, et pas fait pour des images « cartoonisées » |
| Simulation d'eau | Niagara Fluids | dans Unreal | « c'est très moche » |
| Code, scène, compilation, mesures | Claude Code, Claude Opus 5.5 | en ligne | a tout fait tourner |

## Unreal Engine vu par un joueur

Unreal Engine, je le connaissais par les jeux qui l'utilisent. Ce chapitre suit les questions que j'ai posées à l'agent pendant ces six jours, et ce que chacune m'a appris.

### « Ça devait pas être un filtre de rendu UE ? »

Le deuxième matin, j'ai regardé les captures et écrit : « Sur tes screenshots je ne vois pas le rendu dessin animé. Ça devait pas être un filtre de rendu UE ? » Dans ma tête de joueur, un style graphique, c'est un filtre posé sur l'image. Sur un Quest, c'est impossible : le rendu mobile du casque n'a pas le HDR dont le post-traitement a besoin. Le look peint est donc passé dans les matériaux. Un matériau maison, qui ne dépend pas de l'éclairage du moteur, ombre chaque objet en deux tons, avec un bord peint, un liseré de contre-jour et une lumière propre à chaque moment de la balade.

Sur PC, pour les vidéos de contrôle, l'agent avait gardé un filtre de peinture. Je lui ai demandé de l'enlever, « vu qu'on l'a pas dans le Quest » : une vidéo plus jolie que le casque ne m'aide pas à juger.

![Le même instant en rendu PC : à gauche avec un filtre de peinture qui empâte l'image, à droite sans filtre.](/wp-content/uploads/2026/10/barque-24-filtre-pc.jpg)

*Le même instant en rendu PC, avec le filtre de peinture et sans. Le Quest ne sait pas appliquer ce filtre.*

C'est devenu un fil rouge : l'éditeur d'Unreal affiche une image correcte, et le casque en montre une autre. Le brouillard n'a pas été rendu au casque avant le deuxième après-midi, parce que sa passe exige elle aussi le HDR mobile. Les shaders calculés en 16 bits pixellisaient le ciel. Un matériau qui ne déclare pas qu'il sert à des objets instanciés s'affiche en gris. Et le profil Quest 3 d'Unreal hérite d'un profil Android moyen, qui affiche toutes les textures un niveau en dessous et coupe le filtrage anisotrope ; l'agent l'a découvert dans le journal du casque, le 21.

### « C'est vraiment une limite du casque ? »

Le même jour, au casque, j'étais « surpris par le manque de polygones […] c'est vraiment une limite du casque ? ». J'ai demandé une version bien plus détaillée, quitte à tomber à 25 images par seconde, pour comparer. L'agent l'a installée à côté de l'autre : elle tournait entre 44 et 50.

Pour savoir où partait le temps de calcul, il a mesuré en direct. Pendant que la démo tourne dans le casque, il envoie une commande à la console du jeu par adb, et compare le temps de calcul d'une image avant et après. Pour tenir 72 images par seconde, chaque image doit être calculée en moins de 13,9 millisecondes. Cacher les maillages du décor faisait gagner 8 millisecondes ; baisser la résolution à 60 %, un tiers de milliseconde. La scène était limitée par la géométrie. Baisser la résolution, le premier réflexe d'un joueur sur PC, ne servait à rien.

![Graphique en barres : temps gagné par image en coupant chaque élément, de 8 ms pour les maillages du décor à 0,34 ms pour la résolution à 60 %.](/wp-content/uploads/2026/10/barque-25-leviers.png)

*Ce que chaque réglage faisait gagner par image, mesuré au casque le 18/10.*

Les mesures ont tranché à ma place. Couper l'anticrénelage faisait gagner 3 millisecondes, mais les bords scintillaient : on l'a gardé à 2×. Les ombres du soleil coûtaient 1,4 milliseconde pour un décor qui ne dépend pas de l'éclairage du moteur : coupées. Un prépassage de profondeur faisait tomber la démo à 27 images par seconde : écarté.

Les niveaux de détail, ensuite. Quand j'ai demandé si Unreal savait faire « une version adaptative », la réponse était oui, sans Nanite, que le Quest ne gère pas : l'arche a reçu trois versions de 300 000, 100 000 et 30 000 triangles, choisies selon la distance. Une régression de fluidité, plus tard, m'a appris quelque chose sur la VR elle-même : le pont restait dans sa version la plus fine bien trop loin, parce qu'en VR un objet de 42 mètres paraît « grand à l'écran » beaucoup plus longtemps qu'on ne croit.

### « C'est trop bizarre »

Le matin du troisième jour, après la première nuit en images peintes, j'ai écrit : « c'est très fourni et je confirme que les sprites c'est la bonne idée à creuser », et « les oiseaux et les feuilles qui tombent trop bien ! ». Puis : « les sprites qui bougent/tournent quand on bouge ou tourne la tête, c'est trop bizarre. Il faut que les sprites soient fixes. » Selon l'orientation de ma tête, des arbres se rentraient dedans ou non.

![Schéma vu de dessus en trois cases : plans tournés vers chaque œil qui se croisent, plans parallèles à la vue qui tournent avec la tête, plans fixés au placement vers un point de la rivière.](/wp-content/uploads/2026/10/barque-26-plans.png)

*Trois façons d'orienter les arbres peints, vues de dessus, et pourquoi seule la troisième tient en VR.*

Le schéma résume trois versions successives. Au départ, chaque plan se tournait vers l'œil. Chaque œil ayant sa position, un même plan avait deux orientations, et deux arbres voisins se croisaient pour un œil et pas pour l'autre : d'où les bandes verticales. L'agent a ensuite rendu tous les plans parallèles à la vue. Plus de croisement, mais les arbres pivotaient quand je tournais la tête. La version finale oriente chaque plan une fois pour toutes, au placement, vers le point de la rivière d'où on le voit à 45° devant. Deux voisins visent presque le même point : leurs plans restent presque parallèles, et rien ne bouge plus avec la tête.

Chaque correction en a amené une autre. Une touffe vue par la tranche devenait un grand aplat : un fondu selon l'angle de vue l'efface. Ce fondu effaçait aussi les nénuphars, toujours vus en rasant depuis la barque : ils en sont exclus. Immobiles, les arbres étaient devenus figés : un balancement lent, calculé dans le shader, leur rend du vent, le pied fixe et la cime qui bouge. Ce vent est resté invisible un moment, à cause d'une erreur d'unité : cinq millimètres de balancement.

Il fallait aussi du relief, parce qu'une image plate reste plate pour deux yeux. Depth Anything, un modèle qui estime la profondeur d'une image, refusait de tourner dans ComfyUI, et je lui ai confirmé que ça ne marcherait pas : « tes images sont cartoonisées et le moteur ne sait pas traiter ce genre de choses ». L'agent a tiré le relief de la silhouette peinte : chaque image se bombe en dôme, plus épaisse au centre qu'aux bords.

### « L'eau reste une surface plane »

L'eau a été le chantier le plus long. Premier obstacle : sur le Quest, le matériau de l'eau ne peut pas lire la profondeur de ce qu'il y a dessous. Les pieux du ponton se voyaient nettement à travers l'eau ; j'avais trouvé le ponton « superbe », mais ce défaut-là, « ça mérite une vraie recherche sur Internet ». L'agent a retourné le problème : ce sont les objets immergés qui s'éteignent, selon la longueur de leur trajet sous l'eau.

Deuxième obstacle, plus sournois. Les rides de l'eau étaient des traits allongés, orientés en travers de la rivière. Vers l'aval, ça donnait une eau peinte. Mais dès qu'on tournait la tête, la perspective les changeait en rayons qui convergent : l'effet « pluie » des captures du casque, et une bonne part de ce qui faisait « pas fini ». L'agent les a remplacées par un réseau de crêtes sans direction, que la perspective écrase en traits horizontaux, où que l'on regarde. Le sillage, qui partait de la poupe et ne se voyait pas, naît maintenant à l'étrave, comme celui d'un vrai bateau, et longe les flancs, sous les yeux du passager assis à l'arrière.

[video mp4="/wp-content/uploads/2026/10/barque-27-eau.mp4" poster="/wp-content/uploads/2026/10/barque-27-eau-poster.jpg" width="1920" height="1080" preload="metadata"][/video]

*Le même instant, avant et après la nuit du 19 au 20/10 : les rides orientées à gauche, les crêtes sans direction à droite.*

Puis j'ai écrit : « Ton souci c'est que l'eau reste une surface plane ». Un article d'Epic sur l'eau de Still Wakes the Deep, un jeu où elle est simulée, a servi de piste. La version Quest est plus modeste : une hauteur d'eau calculée pour la houle et le sillage, une grille fine qui se déforme autour de la barque, des reflets sur la pente des vagues, des nénuphars qui flottent. La simulation complète, Niagara Fluids, a été essayée au casque le 20 au soir. Mon verdict : « c'est très moche ». Elle est restée de côté.

L'écume, enfin, restait invisible, pour trois raisons empilées : depuis la place assise, le plat-bord cache toute l'eau à moins de 1,10 m de l'axe de la barque ; une fonction de transition écrite à l'envers valait zéro à la compilation, et effaçait au passage une partie des ailes du héron ; le motif de découpe était fait de lignes trop fines. Refaite, elle sautait par taches. Elle a fini par disparaître : l'eau ondulée suffisait.

### « Je n'ai pas vu de fort tangage »

Une règle de confort interdit de faire pencher la caméra. Pour que la barque bouge quand même, l'agent l'a montée sur un pivot qui porte la coque, la lanterne et le héron, mais pas la caméra : c'est la barque qui bouge sous le spectateur. Au premier essai, la coque a disparu, restée à l'origine du monde : dans Unreal, un parent « mobile » refuse des enfants « statiques ».

Il a commencé prudemment, avec quelques degrés. Je ne voyais rien. Puis 9° au passage de la bête, et ma remarque : « je n'ai pas vu de fort tangage quand la bête remonte ». Avec la caméra droite, seul le bord de la barque bouge, et l'œil le remarque à peine. Je lui ai dit de doubler « pour voir » : 18° de roulis, une houle de 50 centimètres. C'est resté, avec mon verdict du dernier jour : « les vagues nickel, le tangage nickel ».

![Capture du casque au passage de la bête : la barque penche fortement, le paysage au loin reste droit.](/wp-content/uploads/2026/10/barque-28-tangage.jpg)

*Au casque, au passage de la bête : la barque penche de 18°, la caméra reste droite.*

Ce réglage a laissé un dernier défaut, trouvé dans la version finale : à 18° de roulis, l'avant du plancher, plus large que la coque à la flottaison, plongeait sous la surface, et une flaque apparaissait dans la barque. Le premier rendu de contrôle, une seconde trop tard, ne montrait rien. Une série toutes les demi-secondes l'a trouvée. Sous le plancher, l'eau reste maintenant 30 centimètres plus bas.

### Un moteur qui se pilote en Python

Ce qui m'a le plus surpris, c'est qu'Unreal se pilote entièrement par script. Le projet lui-même a été créé par un script Python, avec les réglages du Quest 3 : OpenXR, Vulkan, rendu mobile en forward, multiview. Les réglages que l'éditeur ajoute de lui-même sont reportés dans le script, pour que tout reste rejouable. Les vidéos sortent de Movie Render Queue, l'outil de rendu d'Unreal, lancé lui aussi par script.

Les pièges étaient souvent en dehors du moteur. Le JDK installé sur mon PC était trop récent pour Gradle, l'outil qui assemble l'application Android ; le niveau d'API « latest » visait Android 15, que le Quest 3 ne charge pas. Installé hors du launcher d'Epic, le moteur s'identifie par un identifiant unique : écrire « 5.8 » dans le projet faisait proposer une conversion à chaque ouverture. Pendant les rendus vidéo, le compilateur de shaders DirectX 11 plantait en boucle ; en passant au Shader Model 6, on est passé de 0,2 image par seconde à une vidéo de quatre minutes rendue en 50 secondes.

D'autres pièges ne se voient qu'au casque. Un jour, je me suis retrouvé assis derrière la barque (« Je suis derrière le bateau ») : l'origine de la VR dépendait de la zone de jeu du Quest, et l'agent a écrit, par script, un Blueprint qui recentre le joueur au démarrage. Plus tard, j'ai vu la scène se construire « petit à petit » avant le noir du début. L'explication de l'agent : au premier lancement, chaque objet attend que ses shaders soient compilés. Tout ce qui se dessine est maintenant caché pendant quatre secondes.

Il y a enfin deux applications dans mon casque : la version de travail, avec la console et la capture au bouton A, et la version finale, compilée en mode Shipping, qui charge moins le processeur (33 % au plus, contre 52 %). L'application de travail est passée de 719 à 414 Mo le dernier jour, quand l'agent a retiré les vidéos d'un essai abandonné : le moteur embarquait très probablement l'une d'elles dans chaque APK. La version finale pèse 369 Mo.

### Les mots que j'ai appris

- Draw call : une commande envoyée à la carte graphique pour dessiner un objet. Notre budget de départ : 150 par image.
- Triangle : l'unité de la géométrie 3D. Budget de départ : 500 000 visibles à la fois.
- Niveau de détail (LOD) : plusieurs versions d'un même objet, de plus en plus simples avec la distance.
- Nanite : la géométrie virtualisée d'Unreal 5, activée par défaut, inutilisable sur le Quest.
- Rendu forward : la méthode de rendu des casques autonomes, plus légère que le rendu différé des PC.
- Post-traitement : les filtres appliqués à l'image terminée. Absent ici.
- MSAA : un anticrénelage qui lisse les bords des objets.
- Billboard, ou imposteur : une image peinte posée sur un plan, à la place d'un objet 3D.
- Shader : le petit programme qui calcule la couleur de chaque pixel, ou la position de chaque sommet.
- World Position Offset : déplacer les sommets d'un objet dans le shader, sans squelette. C'est ce qui fait nager la bête, voler la créature et balancer les arbres.
- Level Sequence : la ligne de temps d'Unreal. Ici, l'horloge de toute la balade, calée sur la musique.
- Development et Shipping : la version de travail d'une application, avec ses outils, et la version finale, allégée.

## Ce que je retiens

![Le même instant de la balade le premier soir, un décor de formes sombres, et le dernier jour, le pont de statues et la forêt peinte.](/wp-content/uploads/2026/10/barque-29-avant-apres.jpg)

*Le premier soir et le dernier jour, à la même place, au même instant de la balade.*

Ma première question a une réponse nette. Pour tout ce qui se voit sur un écran ou se mesure, l'agent est allé très loin seul. Il a écrit 10 000 lignes de code, généré plus d'une centaine d'images et vingt-huit modèles 3D, choisi les sons, construit la scène, compilé, installé et mesuré, la nuit comme le jour, sans que je touche une ligne. Il s'est arrêté au casque : le relief, l'échelle, le confort et le goût sont restés de mon côté. Et quand il ne pouvait pas voir, il m'a fabriqué des outils pour mieux lui montrer ; le bouton A en est le meilleur exemple.

Côté outils, octobre 2026 a un grand gagnant : l'image générée en local. Les 114 images peintes sont cohérentes, dans le style voulu, et c'est grâce à elles que la démo tient au casque. La 3D depuis une seule image donne de bonnes silhouettes et un détail lissé. Pour la musique, Suno ; pour les sons, une banque libre et des mesures. Les solutions toutes faites, Depth Anything ou la simulation d'eau d'Unreal, n'ont rien donné ici.

Côté Unreal, j'ai appris qu'un casque autonome n'est pas un petit PC : pas de filtre, un budget de géométrie serré, et un éditeur qui montre autre chose que le casque. J'ai aussi découvert qu'Unreal se pilote entièrement en Python, et qu'une image peinte vaut souvent mieux qu'un maillage pauvre.

L'agent n'a pas tout réussi, et son journal le dit. Il a conclu trop vite sur une mesure, avec le casque qui regardait le ciel. Il a corrigé des symptômes sans en vérifier l'étendue : la bande de forêt « corrigée » sur un seul anneau, des fleurs en 3D oubliées depuis le tout premier décor. Et il a longtemps raisonné sur l'aspect d'un défaut plutôt que sur une capture datée.

Le plan de départ n'a pas survécu non plus. CLAUDE.md prévoyait une architecture hybride : le décor proche en temps réel, le lointain en vidéo 360 stéréo pré-rendue, la brume pour faire le raccord. Dès que la forêt est passée en images peintes, toute la balade a tenu 72 images par seconde en temps réel. Le lointain en vidéo n'a jamais servi ; l'agent l'a retiré le dernier jour, avec 3,4 Go de vidéos de test.

Il y a eu des incidents, aucun grave : l'interface du Quest qui plante en boucle une nuit, 2,4 Go de vidéos 4K envoyées par erreur sur GitHub, un historique git réécrit et un dépôt recréé pour repasser de 7,3 à 3,9 Go.

![Tuiles de chiffres : 134 commits, 58 scripts, 69 itérations, 186 captures du casque, 19 animatics, 114 images peintes, 28 modèles 3D, 17 sons, 72 images par seconde, 34 substituts, une RTX 3090, 37 heures de pause.](/wp-content/uploads/2026/10/barque-31-chiffres.png)

*Le projet en chiffres.*

[À COMPLÉTER : le temps que j'y ai passé, le nombre de sessions au casque, le coût des abonnements.]

[video mp4="/wp-content/uploads/2026/10/barque-30-volet-lac.mp4" poster="/wp-content/uploads/2026/10/barque-30-volet-lac-poster.jpg" width="1920" height="1080" preload="metadata"][/video]

*Le lac, le 19 et le 23/10. La lanterne qui masquait le centre de l'image est descendue au fond de la barque, et le héron s'est posé.*

Le 23 octobre, j'ai écrit à l'agent : « bah là on a fini en vrai… Tu vois des choses à améliorer ? » Dans son suivi, il en note trois : un audit automatique des plans vus par la tranche, la famille de défauts revenue deux fois ; une vidéo partageable sans casque ; et le premier jet de cet article. Il reste aussi 34 éléments générés en local en attendant mieux, tous en place dans la démo. Pour remplacer l'un d'eux, il suffit de déposer une image et de relancer le script concerné. C'était écrit dans le fichier de consignes dès le premier jour.

## Le casque, c'était moi

En lançant ce projet, je me demandais ce qu'une IA saurait faire seule. Au bout de six jours, la question qui m'intéresse est l'inverse : ce qu'il m'est resté à faire. Rien de technique. J'ai regardé au casque ce que l'agent ne pouvait pas voir, dit en une phrase ce qui n'allait pas, lancé quelques idées de mise en scène, et répondu oui ou non quand il demandait une installation. C'est un travail de directeur artistique.

Pour quelqu'un qui crée seul, ce partage des rôles change l'échelle de ce qu'on peut tenter. Je ne maîtrise pas Unreal, et la démo existe quand même, avec un journal qui explique chacune de ses décisions. La limite est physique : tant que l'agent ne voit pas en relief et n'entend pas une voiture au fond d'une ambiance de lac, il faut quelqu'un dans le casque.

La leçon de méthode vaut bien au-delà du jeu vidéo. Sans le fichier de suivi, les défauts réversibles et une scène qui se reconstruit d'une commande, je n'aurais pas laissé l'agent seul une nuit entière, encore moins vingt heures. Le modèle fait le travail ; ces quelques règles m'ont permis de lui faire confiance.

La barque dérive toujours dans mon casque. Le héron s'y pose à 3 min 47, annoncé par un cri d'aigrette que l'agent n'a jamais entendu.
