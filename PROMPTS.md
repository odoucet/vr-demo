# Prompts — La barque des lucioles

Tous les prompts de génération externe (Midjourney, Suno). Olivier génère, l'agent exploite.

## Règles

- Prompts en anglais. **Ne jamais nommer de studio, de réalisateur ni d'artiste** : ça tire vers des
  personnages et des compositions existants. On décrit le style par ses caractéristiques.
- **Une image maîtresse pour tout.** Choisir UNE image parmi les concepts `refs/S*.png` et l'utiliser en
  `--sref` sur tous les prompts ci-dessous (concepts, assets, créatures, textures), pour que l'ensemble
  reste cohérent. Proposition : `S5-RACINES` (la palette la plus complète : verts profonds, or, ciel).
  Noter l'URL ou le code `--sref` dans `assets/manifest.yaml`. Partir de `--sw 100` et descendre
  (50, puis 25) si le style écrase le sujet. Adapter les paramètres à la version de Midjourney utilisée.
- **Nom de fichier = identifiant.** Déposer chaque image retenue dans `refs/inbox/` sous l'identifiant
  donné ci-dessous (ex. `barque-dessus.png`). Les scripts du pipeline travaillent par identifiant : on peut
  remplacer une seule image et ne régénérer que ce qui en dépend.
- Les vues `-profil` et `-dessus` servent à la reconstruction multi-vues. Midjourney ne garantit pas la
  cohérence entre deux images : si les vues ne collent pas, une seule vue 3/4 suffit, l'agent génère les
  autres en local.

## Blocs communs

**[style]** — fin de prompt des concepts d'ambiance :

```
hand-painted 1980s Japanese animation background art, gouache and watercolor, soft painterly edges, flat color shapes, gentle diffuse light, lush saturated greens, towering cumulus clouds, nostalgic and serene mood
```

**[peint-3d]** — fin de prompt des assets et créatures à passer en 3D. Rendu peint (et non photoréaliste,
sinon les textures 3D le reprennent), mais éclairage plat pour que la texture ne contienne pas d'ombres :

```
hand-painted stylized look, gouache textures, simplified readable shapes, flat color areas, single isolated subject, entire subject in frame, centered, plain light grey background, flat even lighting, no cast shadows, no depth of field, clean silhouette
```

**Vues** (à insérer avant [peint-3d]) :

| Vue | Texte |
|---|---|
| 3/4 | `three-quarter view` |
| profil | `strict side view, orthographic, perfectly horizontal` |
| dessus | `top-down view from directly above, orthographic` |
| face | `strict front view, orthographic, symmetrical` |

## Concepts d'ambiance (color script) — `--ar 16:9`

Déjà générés : S2, S5, S6, S7. **Manquent : S1, S3, S4.**

- `S1-NOIR` : `near-total darkness on a still river at night, only faint ripples catching a sliver of blue light, hints of reeds, [style]`
- `S2-PONTON` : `old wooden pier in thick morning-blue mist at dusk, small rowboat moored, tall reeds, forest silhouettes fading into fog, first point of warm lantern light, [style]`
- `S3-ABYSSE` : `view from a small boat looking down into crystal-clear dark river water, a vast glowing creature shadow gliding beneath, bioluminescent cyan patterns, lily pads on the surface, [style]`
- `S4-GUE` : `shallow river ford at golden dusk, a herd of large gentle moss-covered creatures wading chest-deep across the river, mist, fireflies starting, seen from water level, [style]`
- `S5-RACINES` : `river flowing under the arched roots of a colossal ancient tree, roots forming a natural cathedral overhead, thousands of fireflies rising, warm gold light, [style]`
- `S6-LUNE` : `opening in the forest canopy at night, enormous full moon, a gigantic graceful flying creature with translucent fins crossing in front of the moon, silver light on the river, [style]`
- `S7-LAC` : `perfectly still mirror lake at night, a great tree covered in hundreds of paper lanterns on a small island, reflections, fireflies, deep blue and gold, [style]`

## Barque — le décor principal (le spectateur y est assis 4 min)

- `barque` — `--ar 1:1 --style raw` : `small weathered wooden rowboat, hand-built, curved planks, a hanging paper lantern on a bent pole at the bow, rope coils, three-quarter view, [peint-3d]`
- `barque-dessus` — `--ar 1:1 --style raw` : `small weathered wooden rowboat seen from directly above, interior fully visible: two wooden bench seats, worn floor planks, a coiled rope, oarlocks, the base of a bent lantern pole at the bow, bow pointing up, top-down view from directly above, orthographic, [peint-3d]`
- `barque-profil` — `--ar 16:9 --style raw` : `small weathered wooden rowboat, hand-built, curved planks, a hanging paper lantern on a bent pole at the bow, strict side view, orthographic, perfectly horizontal, [peint-3d]`
- `barque-interieur` — `--ar 16:9` (concept, pas pour la 3D : référence de la vue du spectateur) : `first-person view sitting at the stern of a small wooden rowboat looking toward the bow, worn plank floor and bench seat in the foreground, a coiled rope, a paper lantern hanging from a bent pole at the bow glowing warm, calm river and misty forest ahead at dusk, [style]`

## Assets — `--ar 1:1 --style raw`

- `ponton` : `short old wooden pier section on stilts, mossy posts, slightly crooked planks, three-quarter view, [peint-3d]`
- `lanterne` : `round paper lantern with wooden frame and top handle, unlit, warm off-white paper, three-quarter view, [peint-3d]`
  (éteinte : la lueur sera faite par le matériau et la lumière dans Unreal, pas cuite dans la texture)
- `racine` : `single massive arched tree root, smooth stylized bark, moss patches, three-quarter view, [peint-3d]`
- `arbre-colossal` — `--ar 16:9` (concept de référence, l'arbre sera construit dans le pipeline) : `a colossal ancient tree on a riverbank, its enormous arched roots spanning over the river like a gateway a small boat can pass under, moss and ferns, fireflies, [style]`

## Créatures (originales) — `--ar 1:1 --style raw`

Silhouettes simples et lisibles : elles passent en image → 3D puis sont animées par ondulation procédurale.
**Pose neutre obligatoire** pour les vues profil et dessus : corps droit, membres et nageoires étalés,
symétrique. Une pose enroulée ou en mouvement ne peut pas être animée proprement.

**Créature des abysses**
- `abysses` : `giant elongated river creature, half manta ray half eel, smooth dark body with glowing cyan bioluminescent spots and stripes, long flowing fins, gentle and ancient, three-quarter view, [peint-3d]`
- `abysses-dessus` : `giant elongated river creature, half manta ray half eel, smooth dark body with glowing cyan bioluminescent spots and stripes, body perfectly straight and fully extended from head to tail, both wing-fins spread flat and symmetrical, top-down view from directly above, orthographic, [peint-3d]`
- `abysses-profil` : `giant elongated river creature, half manta ray half eel, smooth dark body with glowing cyan bioluminescent spots and stripes, body straight and horizontal, fins relaxed, strict side view, orthographic, perfectly horizontal, [peint-3d]`

**Troupeau du gué**
- `troupeau` : `large gentle round herbivore creature, body covered in thick moss and small ferns, short sturdy legs, long drooping ears, small glowing seed-pods on its back, calm eyes, three-quarter view, [peint-3d]`
- `troupeau-profil` : `large gentle round herbivore creature, body covered in thick moss and small ferns, short sturdy legs, long drooping ears, small glowing seed-pods on its back, calm eyes, standing still, legs straight, strict side view, orthographic, perfectly horizontal, [peint-3d]`

**Créature volante** (fichier actuel : `fly`)
- `fly` : `enormous sky creature shaped like a slow-flying whale with wide translucent wing-fins, pale body with faint luminous markings, long trailing tail filaments, majestic and peaceful, three-quarter view, [peint-3d]`
- `fly-profil` : `enormous sky creature shaped like a slow-flying whale, pale body with faint luminous markings, body straight and horizontal, wide wing-fins fully spread, long tail filaments trailing straight back, strict side view, orthographic, perfectly horizontal, [peint-3d]`
- `fly-dessus` : `enormous sky creature shaped like a slow-flying whale, pale body with faint luminous markings, body straight, wide wing-fins fully spread and symmetrical, tail filaments trailing straight back, top-down view from directly above, orthographic, [peint-3d]`

**Petits esprits**
- `esprit` : `tiny round forest spirit made of soft glowing light and leaves, simple shape, two dot eyes, three-quarter view, [peint-3d]`

**Planche de vues** (optionnelle, à tenter pour chaque créature) :
`character turnaround sheet of [créature], front view, side view, back view, top view, same scale, neutral straight pose, plain light grey background, flat lighting`

## Textures — `--tile --ar 1:1`

- `tex-mousse` : `seamless stylized painted moss texture, soft gouache strokes, flat color shapes`
- `tex-ecorce` : `seamless stylized painted tree bark texture, simple shapes, warm brown and green`
- `tex-eau` : `seamless stylized river water texture, painted ripples, flat blue-green tones`
- `tex-planches` : `seamless stylized wooden planks texture, weathered, hand-painted`

## Ciel et lointain — `--ar 2:1`

- `ciel` : `wide panoramic dusk sky, towering cumulus clouds lit pink and gold from below, deep blue zenith, hand-painted, [style]`

Référence de couleur et de forme pour le skydome, pas un équirectangulaire utilisable tel quel : le
skydome final est produit dans le pipeline.

## Musique — Suno

Morceau retenu : `audio/music/Luminous Wonder.mp3`, généré avec ce prompt en mode Custom.
Le séquencier est recalé dessus (`pipeline/sequencer.yaml`). À 72 BPM en 4/4, une mesure dure 3,33 s.

**Style of Music**

```
Instrumental cinematic orchestral film score, 72 BPM, D major, 4/4. Hand-painted 1980s Japanese animated film soundtrack feel: nostalgic, tender, full of wonder. Live chamber orchestra recorded in a warm concert hall. A memorable, singable main theme, first on solo felt piano, then solo flute, then soaring legato strings. Harp arpeggios, oboe countermelodies, soft French horns, delicate celesta. Expressive rubato, rich chord progressions, gentle modulations. Slow build to a luminous orchestral climax, then a quiet piano reprise and fade out. Warm, smooth, intimate mix.
```

**Exclude Styles**

```
vocals, choir, singing, drums, percussion, synthesizer, electronic, EDM, pop beat, trap, bass drop
```

**Lyrics** (structure uniquement ; `Instrumental` désactivé pour que Suno la lise)

```
[Intro]
[Solo felt piano, misty and sparse, very soft string pad]

[Interlude]
[Deep low strings and contrabass, shimmering celesta, mysterious, a vast presence gliding beneath]

[Verse]
[Main theme on solo flute, warm pizzicato strings in a gentle walking rhythm, golden and tender]

[Build]
[Flowing harp arpeggios, strings swelling, oboe countermelody, rising wonder]

[Chorus]
[Full orchestra, main theme soaring on strings and French horns, majestic and luminous]

[Outro]
[Main theme returns on solo piano, slowing down, peaceful]

[Fade Out]
[End]
```
