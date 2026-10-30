# L'article, prêt pour WordPress

| Fichier | Contenu |
|---|---|
| `la-barque-des-lucioles.md` | l'article, environ 7 800 mots. La première ligne est le titre ; le paragraphe en italique juste dessous sert de chapô (ou d'extrait). |
| `wp-content/uploads/2026/10/` | les 37 médias, rangés comme WordPress les range pour un envoi en octobre 2026 : 25 images, 6 vidéos et leurs 6 affiches, 67 Mo au total. Les noms sont numérotés dans l'ordre d'apparition. |
| `apercu.html` | l'article mis en page, images et vidéos comprises, pour relire dans un navigateur (le Markdown pointe vers `/wp-content/...`, que l'aperçu de VS Code ne sait pas résoudre). |

## Publier

1. Médias > Ajouter : envoyer les 37 fichiers du dossier `wp-content/uploads/2026/10/`, sans les renommer. En octobre,
   WordPress les range dans `/wp-content/uploads/2026/10/`, là où pointent les liens de l'article.
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
3. Remplir l'unique `[À COMPLÉTER]`, dans « Ce que je retiens » : ton temps passé, le nombre de sessions au casque, le
   coût des abonnements.

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

## Régénérer

Tout se refait par script, dans WSL, depuis le dépôt :

- les maîtres, dans `builds/article/` (hors dépôt) : `pipeline/article/schemas.py`, `graphiques.py`,
  `compositions.py`, `montage.py` (montages vidéo décrits dans `montages.yaml`) ;
- les fichiers web et l'aperçu : `pipeline/article/export_web.py` (liste des médias : `medias.yaml`).

Pas faits, en option : une vraie captation vidéo au casque (l'enregistreur du Quest), une photo de toi au casque, des
vues tournantes des modèles 3D et une vue du décor depuis l'extérieur (rendus sur la carte graphique).
