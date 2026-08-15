# Atlas Hand Rig — module d'éclairage rasant et planche-contact

Agent RENDUS ET LUMIÈRE. Aucun os, poids ou driver touché. Le `.blend` du rig a été
ouvert en lecture seule ; rien n'a été écrit dans `Atlas/` ni `atlas-hand-rig/`.

| Livrable | Chemin |
|---|---|
| Module | `/tmp/atlas-agent-lumiere/eclairage.py` |
| Script de preuve | `/tmp/atlas-agent-lumiere/rendre_preuves.py` |
| 18 rendus | `/tmp/atlas-agent-lumiere/preuves/` |
| 6 agrandissements | `/tmp/atlas-agent-lumiere/zooms/` |
| Histogrammes | `/tmp/atlas-agent-lumiere/histogrammes.json` |
| Planche-contact | `/tmp/atlas-agent-lumiere/planche.html` |
| Mesures géométriques | `/tmp/atlas-agent-lumiere/mesures_geometrie.json`, `intersections_localisees.json` |

---

## 1. La sonde d'abord

Une mesure fausse est pire que pas de mesure. Trois contre-épreuves avant de me fier
à quoi que ce soit (script `valider.py`, images dans `calib/`) :

| Contre-épreuve | Attendu | Mesuré | Verdict |
|---|---|---|---|
| Décodeur PNG maison vs lecture Blender | identiques | écart max **6,0 e-8** | la mesure lit bien les valeurs du fichier |
| Key ×10 (surexposition volontaire) | fort écrêtage | **0 % → 1,223 %**, lum. max **0,847 → 1,000**, moy. **0,563 → 0,880** | la sonde réagit |
| Key ×0,1 | image sombre | moy. **0,211**, max **0,482** | la sonde réagit dans l'autre sens |
| Source à 2× la distance | même éclairement | moy. **0,5626 → 0,5693**, soit **1,19 %** d'écart | la loi en d² tient |

`histogramme()` décode le PNG lui-même (zlib + défiltrage, code dans le module) au lieu
de passer par la gestion des couleurs de Blender : elle mesure ce que le fichier contient,
donc ce que l'œil verra.

**Une réserve à connaître.** Sous AgX, ×10 sur la key ne produit que 1,22 % d'écrêtage :
le roll-off comprime tellement les hautes lumières que le seuil 0,99 ne discrimine
presque rien. Le plafond « moins de 2 % » est donc structurellement facile à tenir avec
cette transformation de vue — ce n'est pas un exploit. J'ai ajouté `quasi_ecretage_pct`
au seuil 0,95, qui est le chiffre réellement informatif. Il vaut **0,000 % partout**, et
la luminance max plafonne à **0,846** sur les 18 images : il reste environ **1,5 diaph**
de marge avant le blanc. C'est ça, la vraie preuve de non-surexposition.

## 2. Réglages retenus

Tout est dans le dictionnaire `REGLAGES` du module — source unique, renvoyée telle
qu'appliquée par `poser_studio()` et recopiée dans `histogrammes.json`.

### Rendu et couleurs (identiques sur les 18 images)

| | |
|---|---|
| Moteur | Cycles, **96 échantillons**, débruitage actif |
| Résolution | **900 × 900**, fond transparent (RGBA 8 bits), dithering 0 |
| Transformation de vue | **AgX**, look **None**, **exposition 0,0 EV**, gamma 1,0, affichage sRGB |
| Monde | gris neutre **0,02**, intensité 1,0 |
| Clay | Principled, base **0,50** neutre, rugosité **1,00**, métallique 0, **Specular IOR Level 0,00** — lambertien pur, aucun spéculaire à écrêter |

### Cadrage

| | |
|---|---|
| Objectif | **85 mm** / capteur 36 mm (demi-champ 11,96°) |
| Champ | **23,86 cm**, marge 1,22 — verrouillé au maximum de toutes les poses/vues, donc **échelle identique partout** |
| Distance caméra | calculée, **≈ 55,4 cm** |
| Visée | centre de la boîte des sommets pondérés par les groupes `DEF_index*`, `DEF_middle*`, `DEF_ring*`, `DEF_pinky*`, `DEF_thumb*` (45 776 sommets) — **métacarpes + doigts, avant-bras exclu**. Le centre de la main est à **5,45 cm** du centre du maillage complet : viser le maillage entier aurait effectivement décalé la main. |
| Mesure du cadre | extension projetée sur les axes **du plan image**, pas sur les axes du monde |

### Éclairage (`eclairer_rasant`)

| Source | Direction | Angle mesuré | Puissance |
|---|---|---|---|
| **Key** | latérale, ⊥ à l'axe des doigts | **75,0°** de la normale = **15,0° au-dessus du plan de la surface**, et **75,0°** de l'axe caméra | **9,25 W** à 59,7 cm, taille 12,5 cm (12° apparents) |
| **Fill** | frontale (axe caméra) | 0° | **1,39 W** = **15 % de la key** (plafond exigé : 20 %) |
| **Rim** | côté opposé, **110° de la normale** donc **20° derrière** le plan de surface | 110,0° | **2,31 W** = **25 % de la key** |

Les 75° tombent au milieu de la fourchette 70–80° exigée. Ils sont **mesurés sur les
vecteurs produits**, pas recopiés de la consigne : `eclairer_rasant()` renvoie
`key_angle_vs_normale_deg`, et c'est cette valeur qui est écrite dans le JSON.

La rim est placée **derrière** le plan de la surface : elle n'accroche que le contour et
ne peut pas remonter les ombres des zones jugées.

**Normalisation par la distance.** `énergie = éclairement × d²` et
`taille = 2·d·tan(θ/2)`. Une source deux fois plus loin éclaire pareil **et** donne la
même dureté d'ombre — vérifié à 1,19 % près.

### Deux rasances opposées

Sur la paume et sur le dos, la même vue est rendue avec `cote = +1` puis `cote = −1`.
Ce n'est pas décoratif : c'est ce qui permet de distinguer un vrai défaut d'un artefact
d'ombre. Toutes les anomalies listées ci-dessous apparaissent **sous les deux rasances**
(comparer `z2_fist_dos_doigts.png` et `z5_fist_dos_articulations.png`).

## 3. Tableau des histogrammes

Mesure bornée à la boîte projetée de la main (avant-bras exclu) et masquée par l'alpha,
donc **le fond ne compte pas**. Seuils : écrêtage ≥ 0,99, ombres bouchées ≤ 0,02.

| Image | Écrêtage % | Quasi ≥0,95 % | Ombres % | Lum. moy | Lum. max | Marge cadre % |
|---|---:|---:|---:|---:|---:|---:|
| `Hand_Neutral-paume-A` | 0,000 | 0,000 | 0,000 | 0,647 | 0,839 | 8,9 |
| `Hand_Neutral-paume-B` | 0,000 | 0,000 | 0,000 | 0,542 | 0,846 | 8,9 |
| `Hand_Neutral-dos-A` | 0,000 | 0,000 | 0,000 | 0,613 | 0,835 | 7,7 |
| `Hand_Neutral-dos-B` | 0,000 | 0,000 | 0,000 | 0,579 | 0,843 | 7,7 |
| `Hand_Neutral-pouce` | 0,000 | 0,000 | 0,000 | 0,589 | 0,835 | 7,7 |
| `Hand_Neutral-auriculaire` | 0,000 | 0,000 | 0,000 | 0,638 | 0,832 | 9,3 |
| `Hand_Fist-paume-A` | 0,000 | 0,000 | 0,000 | 0,624 | 0,831 | 19,3 |
| `Hand_Fist-paume-B` | 0,000 | 0,000 | 0,000 | 0,554 | 0,835 | 19,3 |
| `Hand_Fist-dos-A` | 0,000 | 0,000 | 0,000 | 0,602 | 0,837 | 17,9 |
| `Hand_Fist-dos-B` | 0,000 | 0,000 | 0,000 | 0,586 | 0,834 | 17,9 |
| `Hand_Fist-pouce` | 0,000 | 0,000 | 0,000 | 0,617 | 0,835 | 18,1 |
| `Hand_Fist-auriculaire` | 0,000 | 0,000 | 0,000 | 0,564 | 0,839 | 19,7 |
| `Hand_Cupped-paume-A` | 0,000 | 0,000 | 0,000 | 0,553 | 0,846 | 8,6 |
| `Hand_Cupped-paume-B` | 0,000 | 0,000 | 0,000 | 0,597 | 0,846 | 8,6 |
| `Hand_Cupped-dos-A` | 0,000 | 0,000 | 0,000 | 0,591 | 0,843 | 7,8 |
| `Hand_Cupped-dos-B` | 0,000 | 0,000 | 0,000 | 0,615 | 0,839 | 7,8 |
| `Hand_Cupped-pouce` | 0,000 | 0,000 | 0,000 | 0,609 | 0,831 | 7,6 |
| `Hand_Cupped-auriculaire` | 0,000 | 0,000 | 0,000 | 0,682 | 0,830 | 10,1 |

**Écrêtage max 0,000 %** (limite 2 %). **Ombres bouchées max 0,000 %.** Aucune image
n'a eu à être refaite. Luminance moyenne comprise entre 0,542 et 0,682 : la série est
homogène, sans dérive d'exposition.

La colonne « marge cadre » est la marge minimale entre la main projetée et le bord de
l'image, en % du cadre. Elle est **positive partout** (min 7,6 %) : aucune main n'est
coupée. Les 17,9–19,7 % du poing viennent de l'échelle commune — le poing est plus
compact que la main ouverte, il occupe donc moins de cadre, ce qui est voulu pour
comparer les poses entre elles.

### Preuve que les poses ont bien été évaluées

En mode fond, un rig immobile donnerait 18 images identiques. Contrôle avant rendu, sur
la boîte des sommets de la main :

| Pose | Propriétés actives | Taille de la main (m) |
|---|---|---|
| `Hand_Neutral` | aucune | 0,0972 × 0,1607 × 0,2255 |
| `Hand_Fist` | `Fist 0,55` · `Thumb_Curl 0,219` · `Thumb_Opposition 0,163` | 0,1018 × 0,1359 × **0,1817** |
| `Hand_Cupped` | `Cup 1,00` | 0,0841 × 0,1601 × 0,2353 |

Trois géométries distinctes : les drivers se sont bien évalués. Le script échoue
volontairement (`SystemExit`) si les trois tailles sont identiques.

---

## 4. Zones suspectes

Ce que la rasance a fait sortir. Je juge la déformation, pas le shader, et je donne le
chiffre quand je l'ai. Chaque anomalie visuelle a été **recoupée par une mesure
géométrique** (auto-intersections détectées par BVH sur le maillage évalué, paires de
faces non adjacentes) afin de ne pas livrer une impression.

### 4.1 Auto-intersections — le défaut principal

| Pose | Propriété | Paires de faces qui se traversent | Volume vs Neutral |
|---|---|---:|---:|
| `Hand_Neutral` | — | **0** | 0,000 % |
| `Hand_Fist_25` | `Fist 0,25` | **0** | +0,819 % |
| `Hand_Cupped` | `Cup 1,00` | **29** | +0,682 % |
| `Hand_Fist_50` | `Fist 0,50` | **32** | +2,114 % |
| `Hand_Open` | `Spread 1,00` | **80** | +0,326 % |
| `Hand_Fist` | `Fist 0,55` | **141** | +2,027 % |
| `Hand_Fist_75` | `Fist 0,75` | **856** | +3,833 % |

Le seuil de rupture est **entre `Fist 0,25` et `Fist 0,50`** : en dessous le rig est
propre, au-dessus il se traverse, et ça explose ensuite (×6 entre 0,55 et 0,75).

Où, exactement (groupes de sommets dominants des faces fautives) :

- **`Hand_Fist` (0,55) — 101 paires sur 141, soit 72 %, en `DEF_middle_01.L × DEF_ring_01.L`** :
  les phalanges proximales du majeur et de l'annulaire se traversent l'une l'autre.
  Visible comme des **encoches dures dans la silhouette** aux plis interdigitaux —
  `z1_fist_paume_doigts.png`, `z2_fist_dos_doigts.png`, et confirmé sous la rasance
  opposée dans `z5_fist_dos_articulations.png`. 28 paires supplémentaires en
  `middle_01 × middle_meta`.
- **`Hand_Fist_75` — effondrement généralisé des métacarpo-phalangiennes** :
  `index_01 × index_meta` (70), `middle_01 × middle_meta` (67), `ring_01 × ring_meta`
  (110 au total), `pinky_01 × pinky_meta` (46). Chaque phalange proximale rentre dans
  **sa propre tête métacarpienne**. S'y ajoute `pinky_01 × pinky_02` (37) : l'inter-
  phalangienne proximale de l'auriculaire se replie dans elle-même, et
  **`index_03 × thumb_meta` (112)** : le bout de l'index traverse le métacarpe du pouce,
  c'est-à-dire rentre dans l'éminence thénar.
- **`Hand_Cupped` — 29 paires, toutes en `index_01 × middle_01`** : index et majeur se
  croisent au lieu de se rapprocher (`z6_cupped_index_majeur.png`).
- **`Hand_Open` (`Spread 1,00`) — 80 paires, toutes en `middle_01 × ring_01`.**
  C'est le plus anormal du lot : `Spread` est censé **écarter** les doigts, et il les
  fait se traverser. Un signe inversé ou un mauvais axe sur l'annulaire est le suspect
  naturel. Cette pose n'était pas dans ma commande de rendus ; elle est apparue en
  balayant les autres actions, je la signale telle quelle.

### 4.2 Pertes de volume

- **Aucune dôme métacarpo-phalangienne sur le poing.** Sur `Hand_Fist-dos-A` et `-dos-B`
  (`z2`, `z5`), le dos de la main à 55 % de fermeture est une **rampe lisse continue** :
  on ne voit que les lignes des tendons extenseurs, pas les quatre dômes des jointures.
  Sur une main réelle à ce niveau de fermeture, les jointures sont l'élément le plus
  saillant du dos. Les deux rasances opposées donnent le même verdict, donc ce n'est pas
  une ombre qui masque le relief : le volume n'y est pas. C'est la contrepartie visuelle
  des paires `XX_01 × XX_meta` mesurées ci-dessus — la phalange rentre dans le métacarpe
  au lieu de rouler dessus.
- **Le `Cup` ne creuse quasiment pas la paume.** `Hand_Cupped-paume-A/B` est très proche
  de `Hand_Neutral-paume-A/B` : l'arche métacarpienne transverse ne se creuse pas, seuls
  les doigts convergent. La taille sur l'axe transverse passe de 0,0972 à 0,0841 m
  (−13,5 %), mais la concavité de la paume elle-même ne se lit pas sous la rasance.
- **Sur le volume chiffré, prudence.** Le volume est calculé par le théorème de la
  divergence : dès qu'il y a auto-intersection, les zones superposées sont comptées deux
  fois, et l'écart devient un **indicateur d'anomalie**, pas une mesure de gonflement.
  Le seul point propre est `Hand_Fist_25` : **0 auto-intersection et +0,819 %** de
  volume. Celui-là est un vrai gonflement de skinning linéaire, modeste et acceptable.

### 4.3 Défauts de maillage, indépendants de la déformation

- **Bruit de surface sur la paume au repos** (`z3_neutral_paume_centre.png`). Sur
  `Hand_Neutral`, donc sans aucune déformation, la rasance révèle un moutonnement
  irrégulier sur toute la paume : ce n'est pas le dessin des trois plis palmaires, c'est
  du bruit de surface. À traiter côté maillage, pas côté rig. Je le signale parce que ce
  bruit va parasiter la lecture de toutes les futures évaluations de déformation.
- **Repli des phalanges distales dans les moyennes** sur le profil pouce du poing
  (`z4_fist_pouce.png`) : arête dure à la jonction, sans le roulement de la pulpe.

### 4.4 Cadrages

Rien à signaler : marge minimale **+7,6 %**, aucune main coupée, aucune vue ne rate la
zone à juger. Deux remarques d'usage tout de même :

- L'avant-bras occupe le tiers bas de chaque image. Il est hors de la zone mesurée
  (l'histogramme est borné à la main) mais il mange du cadre. Un `largeur_de_champ` plus
  serré ou un masque de l'avant-bras gagnerait de la définition sur les jointures.
- L'échelle commune est un choix : elle rend les poses comparables entre elles, au prix
  d'un poing qui n'occupe que 64 % du cadre. Appeler `cadre_optimal()` par pose au lieu
  de verrouiller la largeur donnerait l'inverse.

---

## 5. Utiliser le module

```python
import sys; sys.path.insert(0, "/tmp/atlas-agent-lumiere")
import eclairage as E

reglages = E.poser_studio(scene, materiau_clay=True, objets_clay=[geo])

pts   = E.sommets_evalues(geo, groupes=['DEF_index*', 'DEF_thumb*'], poids_min=0.2)
cadre = E.cadre_optimal(pts, direction, haut=axe_doigts)
cam   = E.cadrer(geo, direction, cadre['cible'], cadre['largeur'], haut=axe_doigts)

info  = E.eclairer_rasant(cadre['cible'], direction, normale, cote=+1,
                          largeur_sujet=cadre['largeur'], axe_vertical=axe_doigts)

cad   = E.verifier_cadrage(cam, pts, scene)          # marge en % du cadre
h     = E.rendre("/chemin/img.png", scene, zone=cad['boite_ndc'])
print(h['ecretage_pct'], h['quasi_ecretage_pct'], h['ombres_pct'])
```

Aucun chemin en dur, aucune dépendance au dépôt. `poser_studio()` **purge les lumières
existantes de la scène** (3 supprimées dans ce `.blend`) : le module possède l'éclairage,
une lampe résiduelle fausserait toute la série.

`histogramme()` fonctionne aussi hors Blender : elle n'utilise que `zlib`, `struct` et,
si présent, `numpy`.
