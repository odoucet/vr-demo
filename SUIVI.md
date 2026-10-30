# Suivi — La barque des lucioles

**Fichier unique de suivi.** Tenu par l'agent, lu par Olivier. Classé par criticité.
Mis à jour : 2026-10-30 — **article rédigé, médias prêts pour WordPress.** Démo : version finale livrée au casque
le 23/10.

Légende : 🔴 bloque, aucun contournement · 🟠 contourné · 🟢 mineur

Le suivi détaillé des séances du 17 au 23/10 (retours au casque un par un, mesures, essais abandonnés) a été condensé
ici à l'état final ; il reste lisible dans l'historique git (`git show 3c4edf0:SUIVI.md`) et raconté dans `HISTORY.md`.

---

## ▶ Article (30/10)

Axe d'Olivier : jusqu'où une IA peut-elle être autonome sur une petite démo VR, en tour d'horizon. Plan validé (« le
plan de l'article me va très bien »), article rédigé à sa voix, dans le style demandé (skill avoid-ai-writing).

- **Livré** : `article/la-barque-des-lucioles.md` (~7 800 mots) et `article/wp-content/uploads/2026/10/`, 35 médias
  prêts à envoyer dans la médiathèque WordPress (23 images, 6 vidéos et leurs affiches, 67 Mo), plus deux diaporamas
  MetaSlider dans `article/diaporamas/` (A/B/C des arbres, 3 diapositives ; le pont en sept versions, 7), légende
  incrustée ; `article/apercu.html` pour relire ; mode d'emploi dans `article/LISEZMOI.md`. Tout se régénère :
  `pipeline/article/` (maîtres dans `builds/article/`, puis `export_web.py`).
- **Vidéo 4K pour YouTube** : `review/iter-070/animatic-hd-5.1.mp4` (1,6 Go), la version finale rendue le 30/10 à
  priorité basse (33 min), avec une piste stéréo puis une piste 5.1, comme le recommande YouTube. Son 5.1 seul :
  `review/iter-070/animatic-5.1.flac`, spatialisé comme au casque (`pipeline/review/mix51.py`), vérifié par la mesure
  seulement. Les médias de l'article sont refaits à partir de ce rendu.
- **Attendu d'Olivier** : écouter le 5.1 (l'arrière est aussi présent que l'avant, comme au casque : un réglage s'il
  le veut plus discret) ; assembler les deux diaporamas dans MetaSlider et remplacer les deux
  `[metaslider id="REMPLACER-…"]` ; remplir l'unique `[À COMPLÉTER]` (temps passé, sessions au casque, coût) ;
  trancher le paragraphe sur le style (A4) ; vérifier les droits (Suno, Midjourney, modèles locaux) ; plateforme :
  WordPress (A7, tranché par sa demande).
- **Défauts appliqués** (réversibles) : vidéos H.264 plafonnées à 3 Mb/s (≤ 17,4 Mo chacune ; `export_web.py`) ;
  images ≤ 2000 px (JPEG 82-88, PNG en palette) ; noms numérotés dans l'ordre d'apparition ; espaces insécables à la
  française ; shortcodes `[video]` plutôt que des blocs Vidéo.
- **À ne jamais publier** : `review/iter-063/casque/008s.jpg` et `review/iter-049/casque/030s.jpg` (la pièce d'Olivier).

## ▶ État final (23/10)

Balade de 4 min, entièrement en temps réel au Quest 3, calée sur « Luminous Wonder ». Olivier, 23/10 : « c'est pas loin
d'être parfait ! les vagues nickel, le tangage nickel ». Tous les retours au casque sont traités.

### Deux applis dans le casque

| Appli (bibliothèque du Quest) | Paquet | Usage | Construire |
|---|---|---|---|
| **La barque des lucioles** | `com.odoucet.barque` | **version finale** (Shipping) : sans console ni journal, 369 Mo | `python pipeline/unreal/package_android.py --variant finale` |
| Barque (travail) | `com.odoucet.barque.greybox` | version de relecture (Development) : **capture au bouton A**, console pour les mesures adb, 414 Mo | `python pipeline/unreal/package_android.py` |

Les deux ont le même contenu. Installation : `adb install -r builds/android_finale/Barque-Android-Shipping-arm64.apk`.

### Fluidité de la version finale

Mesure au casque du 23/10, 11 h 12, toute la balade (`review/perf/finale-20261023-1112.txt`) : **72,1 à 72,6 i/s de
moyenne sur chaque beat** (cible 72), temps GPU de l'appli 9,4 à 11,4 ms, CPU ≤ 33 % (52 % pour la version de travail :
le Shipping allège le processeur). Quelques images perdues aux pics (S5 sous l'arche : 30 sur 30 s) ; S1-NOIR = le
chargement, pendant le noir du début (non significatif). Casque posé : regard fixe, à confirmer casque porté.

### Outils de relecture

- **Captures au bouton A** (manette droite, version de travail) : `python pipeline/unreal/quest_captures.py` →
  `review/casque-A/<date>/A-<instant>s.jpg` (instant de la balade lu dans le journal de l'appli).
- Captures automatiques au casque : `python pipeline/unreal/quest_shots.py --iter N [--package com.odoucet.barque]`.
- Fluidité : `python pipeline/unreal/quest_perf.py --variant finale|greybox` ; essais A/B de réglages en direct :
  `quest_ab.py` (version de travail).
- Vidéo 4K à plat : `python pipeline/review/animatic.py --hd` (dernière : `review/iter-070/animatic-hd.mp4`, version
  finale, 30/10) ; son 5.1 et version YouTube : `python pipeline/review/mix51.py --iter 70`.

### Corrigé en dernier (23/10)

- **Flaque sur l'avant du plancher** au passage de la bête (vue sur la version finale, 1:12-1:16) : avec le roulis à 18°
  et le tangage à 6°, l'avant du plancher — plus large que la coque à la flottaison, que suit le masque « pas d'eau dans la
  coque » — plongeait sous la surface. L'eau reste maintenant 30 cm plus bas sous l'emprise du plancher (invisible, sous
  la coque). Vérifié dans l'éditeur (1:12-1:13,5) et au casque (1:11-1:16).
- **Bug de texture à droite avant le gué** (bouton A, 1:27 et 1:58) : une bande de lisière de la couronne du lac (160 m
  de large) venait jusqu'à la berge, vue par la tranche. Toute la largeur des bandes est maintenant vérifiée.
- Bête des abysses sous l'eau près de la surface (dos ~30 cm sous l'eau, lueur bleue visible à droite), houle et
  tangage doublés à son passage ; fleurs de nénuphar 3D fixes retirées ; capture au bouton A.
- **Lointain pré-rendu en vidéo 360 retiré** (accord d'Olivier, 23/10 : « on peut virer ce pré-rendu lointain 360
  inutile ») : scènes de test J1/J1b, sphère vidéo, vidéos de test (3,4 Go hors dépôt), plugins MediaPlate et
  ElectraPlayer. L'APK de travail passe de 719 à 414 Mo (très probablement la vidéo de test, que le moteur embarquait d'office).

---

## 🔴 Bloquants

Aucun.

## 🟠 Contournés

| # | Manque | Contournement | Ce qui le lèverait |
|---|---|---|---|
| I1 | Images d'assets définitives en style peint | 34 assets `placeholder: true` dans `assets/manifest.yaml` (générations locales, essais 3D), tous en place dans la démo | dépôt dans `refs/inbox/` sous l'identifiant de `PROMPTS.md`, puis relancer le script concerné |
| I4 | Pas de PR (connecteur GitHub sans accès, `gh` non connecté) | un commit par itération sur `main` (D6) | `gh auth login` |
| I6 | Freesound : seuls les aperçus OGG sans OAuth | aperçus utilisés | connexion OAuth pour les originaux |

## 🟢 Mineurs (à juger au casque, rien de signalé)

- Roseaux du départ un peu jaunâtres à contre-jour.
- Un nuage fantôme au raccord gauche/droite du ciel (derrière le spectateur au départ).
- Ciel de nuit (S6-S7) peut-être encore un peu clair (`pipeline/style/ambiance.yaml`, `ciel_teinte`).
- Textures générées (écorce, roche) moins belles que la mousse d'Olivier : les prompts `tex-*` de `PROMPTS.md` les
  remplaceraient directement (`python pipeline/comfy/textures.py`).
- Clé Freesound passée dans une conversation : à régénérer si besoin.

## À vérifier au casque (version finale)

- Berge droite avant le gué (1:20-2:00) : plus d'aplat vert ni de pointes en tournant la tête à droite.
- Passage de la bête (1:05-1:20) : plus d'eau sur le plancher ; tangage toujours aussi « nickel ».
- Autour du lac (3:20-4:00), en se retournant : la forêt ferme l'horizon (deux bandes de lisière retirées).

## Pistes d'amélioration (non demandées)

1. **Audit automatique des plans vus par la tranche** : caméra qui tourne sur 360° toutes les 5 s le long du parcours
   (éditeur), zones anormalement uniformes repérées. Cette famille de défauts est revenue deux fois.
2. **Vidéo partageable sans casque** : 360 stéréo ou côte-à-côte 3D (la vidéo 4K à plat existe).
3. **Visuels de l'article encore possibles** : vues tournantes des modèles 3D, décor vu de l'extérieur (rendus GPU),
   captation vidéo au casque (à faire avec Olivier).

---

## Décisions

Chaque décision a un défaut réversible appliqué. Celles qui restent ouvertes n'ont plus d'effet sur la démo livrée.

| # | Décision | État |
|---|---|---|
| D1 | Image maîtresse `--sref` pour Midjourney | défaut `S5-RACINES` |
| D2 | Coupure S3 / S4 | 1:38 (`pipeline/sequencer.yaml`) — validé de fait au casque |
| D3 | Tracé de la rivière | 240 m à 1 m/s — validé de fait |
| D4 | Échelles | barque 3,5 m, abysses 15 m, troupeau 2,5 m au garrot, volante 40 m — validé de fait |
| D5 | Coque de la barque | modèle TRELLIS.2 de la vue 3/4, bancs flottants retirés (Blender) — « la barque c'est bien là » |
| D6 | Livraison sans PR | commits sur `main` |
| D7 | Sons Freesound | un candidat CC0 par besoin (`audio/sfx/`), alternatives dans `audio/sfx/candidates/README.md` |
| D9 | Blender portable | ✅ accordé (19/10), `G:\blender` |
| D11 | Lanterne de proue | place assise reculée, lanterne en papier sur l'avant droit — « lanterne OK » |
| D12 | Stems autour de la barque | ✅ placés selon `pipeline/audio/stems.yaml` |
| D13 | Musique dans le dépôt | ✅ FLAC sans perte (musique + 10 stems) |
| D14 | Marge de performance | MSAA 2× gardé ; fluidité validée (« très fluide ») |
| D15 | Final du lac | nuée de lucioles et héron |
| D16 | Arbres et décor | ✅ images peintes (sprites) |
| D17 | Nettoyage LFS | ✅ dépôt recréé le 21/10 (3,9 Go) ; sauvegarde `G:\barque-sauvegarde-git-20261021` à supprimer quand Olivier le souhaite |
| D18 | Statues géantes | ✅ arche sculptée + tête couchée, en 3D |
| D19 | Architecture proche / lointain | ✅ **tranché le 23/10 : tout en temps réel**, lointain vidéo 360 retiré |
| D20 | Article | ✅ **rédigé le 30/10** sur l'axe d'Olivier (autonomie d'une IA, Q1-Q3) : `article/`, pour WordPress ; plan dans `ARTICLE.md` ; restent A4 (style) et le `[À COMPLÉTER]` |

## État des jalons

| Jalon | État |
|---|---|
| J0 Bible de style | ✅ palettes par beat, prompts, images d'Olivier intégrées ; image maîtresse au défaut (D1) |
| J1 Spike vidéo 360 | ❌ **abandonné** (D19) : le temps réel tient tout seul ; scènes et vidéos de test retirées le 23/10 |
| J2 Greybox + animatic | ✅ jouable au Quest, timing et confort validés au casque (17-23/10) |
| J3 Tranche verticale S4-GUE | ✅ de fait : tous les beats sont au même niveau de finition |
| J4 Production des beats + audio | ✅ sons spatialisés, stems, repères sonores, faune ; assets définitifs : voir I1 |
| J5 Rendus offline + intégration | ✅ redéfini : pas de lointain pré-rendu ; version finale Quest livrée ; vidéo 4K à plat. PC VR hors périmètre (Olivier, 22/10) |
| J6 Polish + déclinaisons 3D | ✅ polish au casque fait ; déclinaisons (VR180, anaglyphe, côte-à-côte) non faites, voir pistes |
