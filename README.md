# Atlas — rig de main / hand rig

Un rig de main Blender construit **entièrement par script**, à partir d'un maillage
mesuré plutôt que réglé à l'œil. Chaque nombre publié ici est mesuré sur le
maillage déformé, pas estimé.

**On cherche de l'aide** sur deux défauts encore ouverts, décrits en bas de page.

---

## Ce qu'il y a dans ce dépôt

| fichier | contenu |
| --- | --- |
| `RIG_Hand.L.blend` | le rig complet, livré en pose neutre, seuls les contrôleurs visibles |
| `rig-main.py` | le script qui construit tout, de l'audit du maillage aux rendus |
| `images/` | 24 rendus Cycles — 6 poses × 4 plans (paume, dos, côté pouce, côté auriculaire) |
| `mesures/rapport-rig.L.json` | toutes les mesures brutes |
| `mesures/enquete.md` | le carnet d'enquête : hypothèses, réfutations, fautes de mesure |

Le maillage de base vient du **Human Base Meshes bundle** de Blender Studio (CC0).

---

## Rapport

**Main** : gauche · **Maillage** : `GEO_Hand.L` · **Armature** : `RIG_Hand.L`

**Os** : 21 `CTRL_` · 19 `MCH_` · 20 `DEF_`

Trois couches séparées : les contrôleurs portent la main de l'animateur, les
mécanismes combinent automatisme et rotation manuelle, et seuls les os `DEF_`
déforment le maillage.

**Propriétés** : `Fist`, `Index_Curl`, `Middle_Curl`, `Ring_Curl`, `Pinky_Curl`, `Thumb_Curl`, `Thumb_Opposition`, `Spread`, `Cup`, `Relax`

**Contraintes** : `COPY_TRANSFORMS`, `COPY_ROTATION`, `LIMIT_ROTATION`

**Bibliothèque de poses** : 13 poses
(Hand_Neutral, Hand_Relaxed, Hand_Open, Hand_Spread_Min, Hand_Fist, Hand_Fist_25…)

### Audit du maillage

- échelle `[1.0, 1.0, 1.0]`, rotation `[0.0, 0.0, 0.0]`
- 54019 sommets, 0 doublon soudé
- **14 à 15 boucles transversales par articulation** (le minimum utile est 3, l'idéal 5 pour un gros plan)

### Test du Bone Roll

Chaque phalange pivotée de 30° doit refermer son doigt vers la paume. L'axe de
flexion des quatre doigts doit suivre le travers de la paume ; celui du pouce ne
doit **pas** le suivre, sans quoi le pouce plierait comme un doigt ordinaire.

| doigt | axe de flexion vs travers | rapprochement |
| --- | --- | --- |
| index | -0.997 | 25.4 mm |
| middle | -1.0 | 31.0 mm |
| ring | -0.986 | 33.4 mm |
| pinky | -0.888 | 23.1 mm |
| thumb | 0.742 | 21.9 mm |


### Critères d'acceptation mesurés

- `Fist = 0` redonne la pose de repos à **0.0 mm** près — aucune double transformation
- course du poing : **123.6 mm**
- la chair de chacun des cinq doigts reste **d'un seul tenant**
- somme des poids = 1 sur **tous** les sommets déformés
- contamination entre phalanges de doigts différents : **657 sommets**, dont 655 dans les creux interdigitaux (mélange voulu) et **2 ailleurs**

### Poses de validation

| pose | course max | auriculaire → pouce | index → pouce |
| --- | --- | --- | --- |
| Hand_Neutral | 0.0 mm | 126.4 mm | 59.3 mm |
| Hand_Relaxed | 69.6 mm | 104.1 mm | 44.1 mm |
| Hand_Open | 15.2 mm | 118.0 mm | 65.6 mm |
| Hand_Spread_Min | 15.2 mm | 133.7 mm | 52.9 mm |
| Hand_Fist | 122.1 mm | 0.1 mm | 38.0 mm |
| Hand_Fist_25 | 69.3 mm | 98.6 mm | 19.4 mm |
| Hand_Fist_50 | 118.0 mm | 66.7 mm | 3.8 mm |
| Hand_Fist_75 | 133.8 mm | 45.7 mm | 16.9 mm |
| Hand_Point | 121.7 mm | 70.6 mm | 43.3 mm |
| Hand_Pinch | 107.0 mm | 57.7 mm | 29.8 mm |
| Hand_OK | 111.6 mm | 51.8 mm | 32.8 mm |
| Hand_Cupped | 50.2 mm | 114.3 mm | 57.7 mm |
| Hand_Pinky_Thumb | 112.5 mm | 2.5 mm | 77.2 mm |


### L'opposition du pouce, mesurée et non supposée

L'opposition n'est pas une rotation sur un seul axe. Les trois composantes du
métacarpien ont été **cherchées par la mesure**, en visant le contact des deux
empreintes :

| composante | supposé au départ | mesuré |
| --- | --- | --- |
| vers la paume | 40.0° | **24.1°** |
| rotation axiale | -55.0° | **53.6°** |
| troisième axe | 22.0° | **-28.1°** |


Deux des trois avaient le **signe inverse** de ce que j'avais supposé.

Pince auriculaire–pouce obtenue : **2.47 mm** entre les
deux empreintes, avec des pulpes qui se font face à **-0.702**
(−1 = parfaitement opposées).

---

## Aide recherchée

### 1. Le pouce s'écrase au poing fermé

La compression des arêtes de la phalange distale du pouce descend à
**0.106** à `Fist = 1` — la chair est
ramenée à un dixième de sa longueur au repos. L'auriculaire descend à
0.2765, l'index à
0.4154.

Le tutoriel suivi range « une articulation s'écrase complètement » dans les
défauts interdits. Un lissage correctif a été essayé puis **retiré** : mesuré, il
n'améliorait rien (thumb -0.0004, pinky -0.0059, index -0.057), il
n'aurait fait que masquer le problème.

Piste probable : les poids de `DEF_thumb_02.L`, ou l'accumulation
flexion + opposition sur le métacarpien à `Fist = 1`.

### 2. La pince auriculaire–pouce s'arrête à 2.47 mm

Les deux empreintes se touchent presque et se présentent bien
(-0.702), mais c'est un contact, pas un appui. Il manque
vraisemblablement de l'amplitude au creusement de la paume — les métacarpiens 4
et 5 tournent au maximum de 22°.

---

## Reproduire

```bash
blender --background --factory-startup --python rig-main.py -- /chemin/de/sortie homme g 110
```

Ajouter `mesure` en dernier argument pour mesurer sans rendre les images.

Le script s'arrête de lui-même si une phase échoue : moins de trois boucles sur
une articulation, un doigt qui se ferme du mauvais côté, ou `Fist = 0` qui ne
redonne pas exactement la pose de repos.

---

## Method note (English)

This hand rig is built entirely from script. Joint centres, the palm plane, the
flexion axis of every finger and the thumb's opposition angles are **measured on
the mesh**, never typed in by eye. The build aborts if a phase fails its own
test — for example if `Fist = 0` does not return the mesh to its rest pose within
0.01 mm, which would reveal a double transform in the CTRL/MCH/DEF chain.

Two defects remain open and help is welcome: the thumb's distal flesh collapses
to 0.106 of its rest edge length at full
fist, and the pinky-to-thumb pinch stops 2.47 mm
short of a true pad-on-pad press.

Base mesh: Blender Studio Human Base Meshes bundle (CC0).
