# L'article, prêt pour WordPress

| Fichier | Contenu |
|---|---|
| `la-barque-des-lucioles.md` | l'article, environ 7 800 mots. La première ligne est le titre ; le paragraphe en italique juste dessous sert de chapô (ou d'extrait). |
| `wp-content/uploads/2026/10/` | les 35 médias cités par l'article, rangés comme WordPress les range pour un envoi en octobre 2026 : 23 images, 6 vidéos et leurs 6 affiches, 67 Mo au total. Les noms sont numérotés dans l'ordre d'apparition. |
| `diaporamas/` | les diapositives des deux diaporamas MetaSlider, une image par diapositive (1600×900, légende incrustée) : `barque-13-arbres-abc/` (3) et `barque-20-pont-versions/` (7). |
| `apercu.html` | l'article mis en page, images, vidéos et diaporamas compris, pour relire dans un navigateur (le Markdown pointe vers `/wp-content/...`, que l'aperçu de VS Code ne sait pas résoudre). |

## Publier

1. Médias > Ajouter : envoyer les 35 fichiers du dossier `wp-content/uploads/2026/10/`, sans les renommer, et les 10
   diapositives de `diaporamas/`. En octobre, WordPress les range dans `/wp-content/uploads/2026/10/`, là où pointent
   les liens de l'article.
   - Envoi en novembre : `python pipeline/article/export_web.py --mois 2026/11` (dans WSL, depuis le dépôt) refait le
     dossier et les liens.
   - La plus grosse vidéo fait 17,4 Mo. La limite de l'hébergement s'affiche sur Médias > Ajouter (« Taille de
     fichier maximale »).
   - Si WordPress renomme un fichier (doublon, suffixe `-1`), corriger son lien dans l'article.
2. Articles > Ajouter : coller le Markdown dans l'éditeur de blocs, qui convertit titres, images, citations, listes et
   tableau. Le titre (première ligne, `#`) va dans le champ du titre.
   - Les vidéos sont des codes courts `[video]` : ils deviennent des blocs « Code court » et fonctionnent tels quels.
     On peut aussi les remplacer par des blocs Vidéo pris dans la médiathèque, avec leur affiche.
   - Les légendes sont les paragraphes en italique sous chaque image.
   - Le texte contient des espaces insécables (typographie française devant `: ; ! ?` et dans « »).
3. Les deux diaporamas, dans MetaSlider : un diaporama par dossier de `diaporamas/`, les diapositives dans l'ordre de
   leur numéro, aux dimensions 1600 × 900 (toutes les images font exactement cette taille : rien n'est recadré). La
   légende est déjà dans l'image ; inutile de remplir celle de MetaSlider. Dans l'article, remplacer chaque
   `[metaslider id="REMPLACER-…"]` par le code court que donne MetaSlider (ou par son bloc).
4. Remplir l'unique `[À COMPLÉTER]`, dans « Ce que je retiens » : ton temps passé, le nombre de sessions au casque, le
   coût des abonnements.

### Textes alternatifs des diapositives

À coller dans le champ « Texte alternatif » de chaque image de la médiathèque :

| Diapositive | Texte alternatif |
|---|---|
| `barque-13-arbres-abc-1` | Vue du casque : la forêt en arbres 3D, aux feuillages en boules texturées, derrière la lanterne de la proue. |
| `barque-13-arbres-abc-2` | Vue du casque : la même forêt en arbres peints. |
| `barque-13-arbres-abc-3` | Vue du casque : la même forêt en touffes ombrées. |
| `barque-20-pont-versions-1` | Le passage du 19 octobre, 11 h 50 : l'ancienne arche de racines, rendu PC avec un filtre de peinture. |
| `barque-20-pont-versions-2` | 19 octobre, 13 h 08 : la nouvelle barque en 3D et sa lanterne basse. |
| `barque-20-pont-versions-3` | 19 octobre, 14 h 56 : le pont aux statues apparaît, encore gris. |
| `barque-20-pont-versions-4` | 19 octobre, 15 h 37 : l'image du pont projetée sur le modèle 3D. |
| `barque-20-pont-versions-5` | 19 octobre, 20 h 48 : le pont avec sa vraie texture. |
| `barque-20-pont-versions-6` | 20 octobre, 0 h 43 : l'eau refaite et le sillage de la barque. |
| `barque-20-pont-versions-7` | 23 octobre : la version finale, rendue en 4K. |

## À vérifier avant de publier

- Le paragraphe « Un mot sur le style » (partie Images, 3D, son) : il dit franchement d'où vient le style, sans nommer
  ni studio ni film. C'est à toi de décider de le garder.
- Les droits : musique Suno (offre payante au moment de la génération : droits commerciaux à confirmer), images
  Midjourney (ton abonnement), sons CC0, modèles locaux (TRELLIS.2, Pixal3D, Z-Image Turbo, Qwen-Image-Edit, BiRefNet)
  pour un usage public. Hunyuan3D 2.1 est cité mais aucune de ses images n'est publiée : sa licence communautaire
  exclut certains territoires, dont l'Union européenne si je me souviens bien.
- Deux captures à ne jamais publier, ta pièce y est visible : `review/iter-063/casque/008s.jpg` et
  `review/iter-049/casque/030s.jpg`. Aucune n'est dans l'article.
- Les rendus PC sont légendés comme tels ; seules les captures du casque montrent la vraie image du Quest.

## La vidéo complète, pour YouTube

`review/iter-070/animatic-hd-5.1.mp4` (1,6 Go, hors dépôt) : la balade entière en 4K, version finale rendue sur PC,
avec une piste stéréo puis une piste 5.1 spatialisée comme au casque. Le son 5.1 seul : `review/iter-070/animatic-5.1.flac`.
Pour les refaire : `python pipeline/review/animatic.py --iter N --hd` (éditeur ouvert), puis
`python pipeline/review/mix51.py --iter N`.

## Régénérer

Tout se refait par script, dans WSL, depuis le dépôt :

- les maîtres, dans `builds/article/` (hors dépôt) : `pipeline/article/schemas.py`, `graphiques.py`,
  `compositions.py` (diaporamas compris), `montage.py` (montages vidéo décrits dans `montages.yaml`) ;
- les fichiers web et l'aperçu : `pipeline/article/export_web.py` (liste des médias : `medias.yaml`).

Pas faits, en option : une vraie captation vidéo au casque (l'enregistreur du Quest), une photo de toi au casque, des
vues tournantes des modèles 3D et une vue du décor depuis l'extérieur (rendus sur la carte graphique).
