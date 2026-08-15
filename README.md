# Atlas — rig de main / hand rig

Un rig de main Blender construit **entièrement par script**, sur un maillage
mesuré plutôt que réglé à l'œil. Chaque nombre publié ici est mesuré sur le
maillage déformé.

> ## ⚠️ Ce rig n'est PAS validé
>
> **1 critère obligatoire reste faux** et il est décrit en détail plus bas.
> Le fichier livré s'appelle `RIG_Hand.L-NON-VALIDE.blend` pour que son état soit
> lisible sans ouvrir quoi que ce soit. **De l'aide est recherchée sur ce point.**

---

## Ce qu'il y a dans ce dépôt

| fichier | contenu |
| --- | --- |
| `RIG_Hand.L-NON-VALIDE.blend` | le rig, en pose neutre, seuls les contrôleurs visibles |
| `rig-main.py` | construit tout : audit, squelette, drivers, poses, rendus |
| `verifier-rig.py` | **vérifie un `.blend` sans reconstruire le maillage** |
| `atelier/` | les quatre modules dont dépend la construction |
| `images/` | 52 rendus — 13 poses × 4 plans |
| `images/gros-plans/` | 8 gros plans des contacts critiques |
| `mesures/` | rapport complet, rapport d'échec, carnets d'enquête |

---

## Reproduire

**Blender 5.1.2.** Aucun add-on.

Vérifier le rig livré — ne demande **aucun** téléchargement :

```bash
blender --background --factory-startup --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

Exécuté dans un clone propre : **code de sortie 2**, 12 critères passent, 1
échoue (celui décrit plus bas). Le script sort en erreur dès qu'un critère
obligatoire est faux — c'est voulu.

Reconstruire depuis zéro — demande le maillage de base :

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend
blender --background --factory-startup --python rig-main.py -- ./sortie homme g 110
```

### Résultat des deux commandes, exécutées dans un dossier temporaire propre

| commande | code de sortie | résultat |
| --- | --- | --- |
| `verifier-rig.py` | **2** | 12 critères passent, 1 échoue — aucun téléchargement requis |
| `rig-main.py` (reconstruction complète) | **2** | 25 critères passent, 1 échoue — résultat identique au dépôt de travail |

Le code 2 est le comportement voulu : un critère obligatoire faux fait échouer
le pipeline. Il vaudra 0 quand le défaut décrit plus bas sera corrigé.

Le maillage de base est le **Human Base Meshes bundle** de Blender Studio,
publié en **CC0** ([source](https://studio.blender.org/tools/assets/human-base-meshes),
version 1.4.1, 47 Mo). Il n'est pas versionné ici : trop lourd, et inutile pour
vérifier le rig.

---

## Journal avant / après

L'état de départ est le commit `4bfab88`, audité et jugé incorrect.

| mesure | avant | après | exigé |
| --- | --- | --- | --- |
| compression min. du pouce au poing | 0,106 | 0.7494 | ≥ 0,25 |
| pouce–index dans `Hand_Pinch` | 29,8 mm | 0.8 mm | ≤ 1,0 mm |
| pouce–index dans `Hand_OK` | 32,8 mm | 0.8 mm | ≤ 1,0 mm |
| pouce–auriculaire | 2,47 mm | 0.9 mm | ≤ 1,0 mm |
| auto-intersections (poing) | non mesurées | aucune | aucune |
| auto-intersections (pince auriculaire) | non mesurées | **26 sommets** | aucune |
| contamination hors commissures | 2 sommets | 0 | 0 |
| écart au retour au repos | 0,0 mm | 0,0000 mm | < 0,01 mm |
| reproductible depuis un clone | non | oui | oui |


---

## Le défaut qui reste

**La pose `Hand_Pinky_Thumb` fait se traverser 26 sommets.**

Les deux pulpes se touchent bien — 0,90 mm, orientées face à face à −0,73 — mais
la chair se traverse ailleurs. J'ai cherché *où*, au lieu de retenter au hasard,
et la réponse est nette :

```
DEF_thumb_meta.L → DEF_index_meta.L : 26 sommets
```

**Ce n'est pas un doigt qui en traverse un autre.** C'est l'**éminence thénar**
contre la **base de l'index** — deux masses de la paume qui se replient l'une
sur l'autre quand le pouce traverse pour rejoindre l'auriculaire.

Ce que j'ai essayé, et pourquoi ça n'a pas suffi :

1. **Élargir la recherche de pose** (index et majeur libres de se replier
   complètement, amplitudes du métacarpien portées à ±45°). Le nettoyage passe
   de 65 à 45 sommets puis plafonne : aucune pose accessible n'est propre.
2. **Chercher en deux temps** — approcher sans contrainte, puis nettoyer. C'est
   ce qui a débloqué les trois autres contacts. Ici, l'approche atteint 0,09 mm
   et le nettoyage ne descend pas sous ~26.
3. **Un lissage correctif** (phase G du cahier des charges). Mesuré, il
   n'améliorait rien — gains négatifs sur les trois doigts testés — donc il a
   été **retiré** plutôt que conservé pour masquer le défaut.

**Ma lecture :** c'est un problème de **volume**, pas de pose ni d'architecture.
La paume n'a pas de quoi absorber la traversée du pouce. La piste que je n'ai
pas menée à bout est celle des **correctifs dépendants de la pose** sur le
thénar et sur le creux entre pouce et index — précisément ce que la phase G
prévoit pour ce cas. C'est là que de l'aide serait la plus utile.

---

## Ce qui a été corrigé

### Le pouce s'écrasait au poing

Sa chair distale tombait à **0,106** de sa longueur de repos. La cause n'était
pas les poids : `Fist` s'additionnait à `Thumb_Curl` sur les mêmes phalanges,
*et* une part de `Fist` s'ajoutait encore à l'opposition. Les trois
articulations finissaient plaquées contre leurs butées. `Fist` ne pilote plus
que les quatre doigts ; le pouce a ses commandes propres.

Compression au poing après correction — minimum, puis percentile 1 % :

| doigt | minimum | p1 | médiane |
| --- | --- | --- | --- |
| index | 0.6457 | 0.8576 | 1.0 |
| middle | 0.5908 | 0.8385 | 1.0 |
| ring | 0.5295 | 0.7996 | 1.0 |
| pinky | 0.5516 | 0.7725 | 1.0 |
| thumb | 0.7494 | 0.8368 | 1.0 |


### Les quatre métacarpiens partaient du même point

Ils pivotaient autour d'un centre unique : une paume ne peut alors pas se
creuser, elle ne peut que s'ouvrir en corolle. Leurs bases forment maintenant un
**arc carpo-métacarpien** mesuré sur la largeur réelle de la paume à hauteur du
carpe.

### Les doigts se traversaient en se fermant

Mesuré **sans le pouce** : 8 sommets dès une fermeture de 0,7, 444 à 0,8. Ce
n'était donc ni le pouce ni la pose — c'était la fermeture. Les doigts divergent
maintenant en se refermant, et l'amplitude de cette divergence est cherchée par
la mesure.

### Le pipeline concluait malgré ses propres échecs

L'ancienne version écrivait `"reussi": false` puis sauvegardait et affichait
« terminé ». Un seul critère faux interdit désormais d'écraser un `.blend`
validé, écrit `mesures/rapport-echec.json`, et sort en **code non nul**.

---

## Method note (English)

This hand rig is built entirely from script: joint centres, the palm plane, each
finger's flexion axis and the thumb's opposition angles are **measured on the
mesh**, never typed in by eye. Every mandatory check can fail the build.

**One criterion still fails.** In the `Hand_Pinky_Thumb` pose the pads meet
correctly (0.90 mm apart, normals opposed at −0.73), but 26 vertices
interpenetrate — all of them between `DEF_thumb_meta` and `DEF_index_meta`, that
is, **thenar eminence against the base of the index**. It is palm flesh folding
into itself, not one finger passing through another. Pose search and a two-stage
approach-then-clean strategy both plateau around 26 vertices; a corrective smooth
was measured, found not to help, and removed rather than kept as a cover-up. The
untried lead is pose-space corrective shapes on the thenar. Help welcome.

Base mesh: Blender Studio Human Base Meshes bundle (CC0). Blender 5.1.2.
