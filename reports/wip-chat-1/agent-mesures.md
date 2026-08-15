# Atlas Hand Rig — audit des auto-intersections

Fichier mesuré : `/Users/orphicagency/Projet de développement/Atlas/objets/humain/rig/RIG_Hand.L-NON-VALIDE.blend`
Sonde : `/tmp/atlas-agent-mesures/audit-collisions.py` — Blender 5.1.2, `--background --factory-startup`, 124 s.
Données brutes : `/tmp/atlas-agent-mesures/collisions.json`.

Aucun fichier du dépôt n'a été modifié. Aucune correction anatomique n'est proposée ici : ce document ne contient que des mesures.

---

## 0. Contrôle de la sonde avant tout verdict

| Contrôle | Attendu | Mesuré | Verdict |
|---|---|---|---|
| main tout à zéro (rotations nulles, propriétés nulles) | 0 | **0** | la sonde ne compte pas la continuité du maillage |
| `Hand_Neutral` (action jouée) | 0 | **0** | idem |
| `Hand_Fist` réagit différemment du repos | ≠ 0 | **3** (permissif) | la sonde lit bien son entrée |
| étape 1,0 de chaque transition = pose jouée par l'action | écart 0 | **+0 sur les 6 transitions** | l'interpolation atteint réellement la pose cible |
| reproduction des chiffres du rapport de référence | identiques | voir ci-dessous | la sonde est calibrée sur l'existante |

Reproduction exacte des nombres de `rapport-rig.L.json`, dans le sens et sur les couples que le vérificateur regarde :
`Hand_Fist_75` thumb→index 6 / index→middle 43 / middle→ring 4 ; `Hand_Point` somme des 4 couples = **543** contre 543 au rapport (126+25+75+317) ; `Hand_Cupped` middle→ring 36 ; `Hand_Pinky_Thumb` thumb→index 26, thumb→middle 14, thumb→hand 5.
La sonde n'invente pas de chiffres : elle en voit davantage parce qu'elle regarde davantage.

**Une seule sonde produit deux jeux de chiffres**, et il faut savoir lequel on lit :

- **classement permissif** — celui de `verifier-rig.py` : le groupe de sommets dominant peut être n'importe quel groupe, y compris `ZONES_ARTICULAIRES`, qui ne correspond à **aucun os**.
- **classement strict** — seuls les 20 groupes qui portent le nom d'un os `DEF_` concourent.

203 sommets changent de famille entre les deux. Voir l'incohérence n° 5.

---

## 1. Les 13 poses

`vu` = ce que `verifier-rig.py` compterait (5 couples, un seul sens). `aveugle` = ce qui lui échappe.

| Pose | Total strict | Total permissif | Couples en intersection (strict, sommets) | vu | aveugle |
|---|---:|---:|---|---:|---:|
| Hand_Neutral | **0** | 0 | — | 0 | 0 |
| Hand_Relaxed | **0** | 0 | — | 0 | 0 |
| Hand_Open | **0** | 0 | — | 0 | 0 |
| Hand_Spread_Min | **0** | 0 | — | 0 | 0 |
| Hand_Fist_25 | **0** | 0 | — | 0 | 0 |
| Hand_Fist_50 | **0** | 0 | — | 0 | 0 |
| Hand_Fist_75 | **118** | 118 | index/middle 72 · thumb/index 42 · middle/ring 4 | 53 | 65 |
| Hand_Fist | **0** | 3 | — (permissif : middle/hand 2 · ring/hand 1, tous vers `ZONES_ARTICULAIRES`) | 0 | 0 |
| Hand_Point | **1540** | 1745 | index/middle 482 · thumb/middle 450 · ring/pinky 336 · middle/ring 214 · thumb/ring 58 | 543 | 997 |
| Hand_Pinch | **0** | 53 | — (permissif : thumb/hand 53, tous vers `ZONES_ARTICULAIRES`) | 0 | 0 |
| Hand_OK | **0** | 53 | — (permissif : thumb/hand 53, tous vers `ZONES_ARTICULAIRES`) | 0 | 0 |
| Hand_Cupped | **80** | 80 | middle/ring 80 | 36 | 44 |
| Hand_Pinky_Thumb | **1271** | 1384 | thumb/pinky 556 · ring/pinky 403 · index/middle 146 · thumb/index 136 · thumb/middle 25 · thumb/hand 5 | 40 | 1231 |

**Total strict sur les 13 poses : 3 009 sommets traversants, dont 672 vus par le vérificateur et 2 337 aveugles (78 %).**
En classement permissif : 3 436 au total, 668 vus, 2 768 aveugles (81 %).

### Détail par groupe de sommets — les 3 pires de chaque pose fautive (strict)

| Pose | 1er | 2e | 3e |
|---|---|---|---|
| Hand_Fist_75 | `DEF_index_01.L → DEF_middle_01.L` (43) | `DEF_index_03.L → DEF_thumb_meta.L` (36) | `DEF_middle_01.L → DEF_index_01.L` (29) |
| Hand_Point | `DEF_ring_03.L → DEF_pinky_meta.L` (232) | `DEF_middle_03.L → DEF_thumb_meta.L` (178) | `DEF_middle_03.L → DEF_index_meta.L` (163) |
| Hand_Cupped | `DEF_ring_01.L → DEF_middle_01.L` (44) | `DEF_middle_01.L → DEF_ring_01.L` (36) | — |
| Hand_Pinky_Thumb | `DEF_pinky_03.L → DEF_ring_meta.L` (403) | `DEF_thumb_02.L → DEF_pinky_02.L` (291) | `DEF_middle_03.L → DEF_index_meta.L` (146) |

Lecture : les pulpes distales (`_03`) entrent dans les **métacarpiens voisins** (`_meta`). Ce n'est pas un frottement latéral entre doigts, c'est un doigt qui s'enfonce dans la paume ou dans la base du doigt d'à côté.

---

## 2. Les transitions Neutral → X, 11 étapes

Nombres de sommets traversants, classement **strict**, à chaque dixième.

| Transition | 0,0 | 0,1 | 0,2 | 0,3 | 0,4 | 0,5 | 0,6 | 0,7 | 0,8 | 0,9 | 1,0 | pic | 1re fautive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| → Hand_Fist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **137** | **355** | 0 | 0,9 | 0,8 |
| → Hand_Point | 0 | 0 | 0 | 1 | 19 | 128 | 187 | 199 | 1726 | **1942** | 1540 | 0,9 | 0,3 |
| → Hand_Pinch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | aucune |
| → Hand_OK | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | aucune |
| → Hand_Cupped | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 34 | 61 | **80** | 1,0 | 0,7 |
| → Hand_Pinky_Thumb | 0 | 0 | 0 | 0 | 22 | 68 | 102 | 1003 | 1984 | **2238** | 1271 | 0,9 | 0,4 |

**4 transitions fautives sur 6** : Fist, Point, Cupped, Pinky_Thumb. Pinch et OK sont propres de bout en bout.

### Quels couples, à quelles étapes (strict)

| Transition | Étape | Couples |
|---|---|---|
| → Hand_Fist | 0,8 | thumb/index 137 |
| | 0,9 | thumb/index 355 |
| → Hand_Point | 0,3 → 0,7 | index/middle seul (1 → 19 → 128 → 187 → 199) |
| | 0,8 | thumb/middle 876 · index/middle 644 · ring/pinky 169 · middle/ring 33 · thumb/ring 4 |
| | 0,9 | thumb/middle 707 · index/middle 515 · ring/pinky 326 · middle/ring 287 · thumb/ring 107 |
| | 1,0 | index/middle 482 · thumb/middle 450 · ring/pinky 336 · middle/ring 214 · thumb/ring 58 |
| → Hand_Cupped | 0,7 → 1,0 | middle/ring seul (6 → 34 → 61 → 80) |
| → Hand_Pinky_Thumb | 0,4 → 0,7 | thumb/index seul (22 → 68 → 102 → 1003) |
| | 0,8 | thumb/index 897 · thumb/pinky 844 · thumb/middle 243 |
| | 0,9 | thumb/pinky 904 · thumb/middle 740 · ring/pinky 432 · thumb/index 160 · thumb/hand 2 |
| | 1,0 | thumb/pinky 556 · ring/pinky 403 · index/middle 146 · thumb/index 136 · thumb/middle 25 · thumb/hand 5 |

### Le fait le plus important de ce rapport

**`Neutral → Hand_Fist` a ses deux extrémités propres (0 et 0) et traverse à 355 sommets au milieu du chemin.**
Au pic (t = 0,9), le détail des groupes est `DEF_index_03.L → DEF_thumb_02.L` (285) et `DEF_thumb_02.L → DEF_index_03.L` (70) : la pulpe de l'index et celle du pouce se traversent l'une l'autre avant de se ranger côte à côte à t = 1,0.
Aucun contrôle du dépôt ne mesure une valeur intermédiaire. Une pose validée n'entraîne donc pas une animation valide : sur une interpolation de 12 images, la main s'auto-traverse aux images 10 et 11 et se répare à la 12e.

Même figure, atténuée, sur `Neutral → Hand_Point` (1 942 au pic contre 1 540 à l'arrivée) et `Neutral → Hand_Pinky_Thumb` (2 238 contre 1 271). Dans les deux cas, **le pire moment de la transition est plus mauvais que la pose finale**, de +26 % et +76 %.

---

## 3. Incohérences constatées dans `verifier-rig.py`

Je signale, je ne corrige pas. Chaque point est chiffré sur le fichier livré.

**1. Neuf poses sur treize ne sont jamais contrôlées en auto-intersection.**
`traversees()` n'est appelée que sur `Hand_Pinch`, `Hand_OK`, `Hand_Pinky_Thumb` et `Hand_Fist` (lignes 194-214). Échappent au contrôle : `Hand_Neutral`, `Hand_Relaxed`, `Hand_Open`, `Hand_Spread_Min`, `Hand_Fist_25`, `Hand_Fist_50`, `Hand_Fist_75`, `Hand_Point`, `Hand_Cupped`.
Coût mesuré : **1 738 sommets traversants** (strict) dans `Hand_Fist_75` (118), `Hand_Point` (1 540) et `Hand_Cupped` (80) ne sont jamais regardés. `Hand_Point` est la pose la plus fautive du fichier après `Hand_Pinky_Thumb`, et elle n'est pas testée.

**2. Cinq couples de familles examinés sur quinze.**
`traversees()` ne parcourt que `thumb/index`, `thumb/middle`, `index/middle`, `middle/ring`, `ring/pinky` (ligne 145-146). Jamais examinés : `thumb/ring`, `thumb/pinky`, `index/ring`, `index/pinky`, `middle/pinky`, et les cinq couples `X/hand`.
Coût mesuré : `thumb/pinky` vaut **556 sommets** dans `Hand_Pinky_Thumb` — c'est le plus gros défaut de la pose, et c'est justement la pose dont le nom dit qu'elle met le pouce contre l'auriculaire. `thumb/ring` vaut 58 dans `Hand_Point`.

**3. Un seul sens de comptage, alors que le critère n'est pas symétrique.**
Pour un couple `(A, B)`, la boucle ne teste que « un sommet de A est-il dans B ». Un doigt entièrement enfoncé dans son voisin peut donc rendre 0.
Coût mesuré, cas exemplaire : `Hand_Pinky_Thumb`, couple `ring/pinky` → `ring_dans_pinky = 0`, `pinky_dans_ring = **403**`. Le vérificateur écrit « aucune auto-intersection » sur un couple qui en compte 403.
Autre cas : `Hand_Point`, `index/middle` → 25 dans le sens testé, **457** dans l'autre (strict ; 25 contre 453 en permissif).
Total sur les 13 poses : le vérificateur voit 672 sommets sur 3 009, soit **22 %**.

**4. Aucun contrôle des valeurs intermédiaires.**
Le vérificateur ne teste que des poses clés. Aucune propriété n'est balayée, aucune interpolation n'est échantillonnée.
Coût mesuré : `Neutral → Hand_Fist` passe par 355 sommets traversants alors que ses deux extrémités valent 0. Ce défaut est structurellement invisible pour le vérificateur actuel, quelles que soient ses tolérances.

**5. Le classement en familles s'appuie sur un groupe de sommets qui n'est l'os de personne.**
`famille()` (lignes 88-92) range dans `hand` tout groupe qui ne commence pas par `DEF_<doigt>_`. Or `GEO_Hand.L` porte 21 groupes pour 20 os `DEF` : `ZONES_ARTICULAIRES`, créé par `rig-main.py` ligne 2291, ne correspond à aucun os et ne déforme rien. Il est pourtant le groupe **dominant** de **203 sommets**, qui sont donc comptés comme « paume ».
Deux conséquences mesurées, en sens opposés :
- des intersections fantômes : `Hand_Pinch` et `Hand_OK` rendent **53** `thumb/hand` en permissif et **0** en strict — les 53 sont `DEF_thumb_02.L → ZONES_ARTICULAIRES`. Idem `Hand_Fist` : 3 fantômes.
- des intersections perdues : `Hand_Point` `index/middle` vaut 478 en permissif contre 482 en strict — 4 sommets réels sortis de leur famille.

**6. Le rapport de référence a été mesuré avant l'existence de ce groupe.**
`dire("poses_de_validation", …)` est ligne 2071 de `rig-main.py` ; `ZONES_ARTICULAIRES` est créé ligne 2291. Les chiffres de `rapport-rig.L.json` sont donc en classement strict, alors que toute mesure refaite sur le `.blend` livré est en classement permissif. C'est vérifié : `Hand_Pinky_Thumb` `thumb/hand` vaut **5** au rapport et **5** dans mon classement strict, contre **23** en permissif. Deux outils du dépôt mesurent la même chose et ne peuvent pas s'accorder.

**7. Une pose absente est silencieusement acceptée.**
`if pose not in ACTIONS: continue` (lignes 197 et 210) : un `.blend` livré sans `Hand_Pinch`, sans `Hand_OK`, sans `Hand_Pinky_Thumb` et sans `Hand_Fist` passe tous les critères de contact et d'intersection et sort en code 0. Le nombre de poses n'est jamais exigé — `resultat["poses"]` les liste sans rien en conclure.

**8. Les critères de contact ne sont exigés que sur trois couples nommés.**
`contact()` n'est mesuré que pour `Hand_Pinch` (index/thumb), `Hand_OK` (index/thumb) et `Hand_Pinky_Thumb` (pinky/thumb). Aucun écart n'est exigé sur `Hand_Fist`, `Hand_Cupped`, `Hand_Point`, ni sur les paliers `Fist_25/50/75`.
**8 bis. `Hand_Pinch` et `Hand_OK` sont la même pose, et rien ne le détecte.**
Mesuré, pas déduit : l'écart maximal entre les deux maillages déformés est de **0,0 mm** sur les 54 019 sommets, et les deux actions n'ont **aucune** valeur de courbe différente à l'image 1. Témoin de la sonde : `Hand_Fist` contre `Hand_Fist_75` donne 67,2 mm, la comparaison n'est donc pas aveugle.
La bibliothèque annonce 13 poses ; elle en contient **12 distinctes**. `rapport-rig.L.json` le montrait déjà — `contact_Hand_Pinch` et `contact_Hand_OK` y sont identiques champ pour champ (0,8 mm, −0,655, 96 sommets, 15 sommets à moins de 1,5 mm) — sans qu'aucun critère ne s'en émeuve. Le vérificateur exige deux fois le même contact et compte deux réussites.

**9. `neutre()` force `rotation_mode = "XYZ"` sur tous les os de pose.**
Sans conséquence sur ce rig (tous les `CTRL` sont en euler), mais le vérificateur modifie l'objet qu'il contrôle : si un os était en quaternion, la vérification le casserait au lieu de le mesurer.

---

## 4. Tableau de régression — valeurs « avant » pour la prochaine itération

Mesures à refaire à l'identique avec `audit-collisions.py`. Le classement **strict** fait foi ; le permissif est donné pour la comparaison avec les outils du dépôt tant qu'ils n'ont pas changé.

| # | Mesure | Valeur actuelle (strict) | Valeur actuelle (permissif) | Cible |
|---|---|---:|---:|---|
| R01 | Sommets traversants — repos tout à zéro | 0 | 0 | rester 0 |
| R02 | Sommets traversants — `Hand_Neutral` | 0 | 0 | rester 0 |
| R03 | `Hand_Relaxed` | 0 | 0 | rester 0 |
| R04 | `Hand_Open` | 0 | 0 | rester 0 |
| R05 | `Hand_Spread_Min` | 0 | 0 | rester 0 |
| R06 | `Hand_Fist_25` | 0 | 0 | rester 0 |
| R07 | `Hand_Fist_50` | 0 | 0 | rester 0 |
| R08 | `Hand_Fist_75` | **118** | 118 | 0 |
| R09 | `Hand_Fist` | 0 | 3 | rester 0 / 0 |
| R10 | `Hand_Point` | **1540** | 1745 | 0 |
| R11 | `Hand_Pinch` | 0 | 53 | rester 0 / 0 |
| R12 | `Hand_OK` | 0 | 53 | rester 0 / 0 |
| R13 | `Hand_Cupped` | **80** | 80 | 0 |
| R14 | `Hand_Pinky_Thumb` | **1271** | 1384 | 0 |
| R15 | **Somme des 13 poses** | **3009** | 3436 | 0 |
| R16 | Pic de `Neutral → Hand_Fist` (t = 0,9) | **355** | 355 | 0 |
| R17 | Pic de `Neutral → Hand_Point` (t = 0,9) | **1942** | 2016 | 0 |
| R18 | Pic de `Neutral → Hand_Pinch` | 0 | 53 | rester 0 |
| R19 | Pic de `Neutral → Hand_OK` | 0 | 53 | rester 0 |
| R20 | Pic de `Neutral → Hand_Cupped` (t = 1,0) | **80** | 80 | 0 |
| R21 | Pic de `Neutral → Hand_Pinky_Thumb` (t = 0,9) | **2238** | 2564 | 0 |
| R22 | Nombre de transitions fautives sur 6 | **4** | 4 | 0 |
| R23 | Première étape fautive — `→ Hand_Point` | **0,3** | 0,3 | aucune |
| R24 | Première étape fautive — `→ Hand_Pinky_Thumb` | **0,4** | 0,4 | aucune |
| R25 | Première étape fautive — `→ Hand_Cupped` | **0,7** | 0,7 | aucune |
| R26 | Première étape fautive — `→ Hand_Fist` | **0,8** | 0,8 | aucune |
| R27 | Pire couple : `thumb/pinky` dans `Hand_Pinky_Thumb` | **556** | 556 | 0 |
| R28 | Pire couple : `pinky_dans_ring` dans `Hand_Pinky_Thumb` | **403** | 403 | 0 |
| R29 | Pire couple : `index/middle` dans `Hand_Point` | **482** | 478 | 0 |
| R30 | Pire couple : `thumb/middle` dans `Hand_Point` | **450** | 442 | 0 |
| R31 | Pire groupe : `DEF_pinky_03.L → DEF_ring_meta.L` (`Hand_Pinky_Thumb`) | **403** | 403 | 0 |
| R32 | Pire groupe : `DEF_ring_03.L → DEF_pinky_meta.L` (`Hand_Point`) | **232** | 232 | 0 |
| R33 | Pire groupe : `DEF_index_03.L → DEF_thumb_02.L` (pic `→ Fist`) | **285** | 285 | 0 |
| R34 | Sommets dominés par un groupe sans os (`ZONES_ARTICULAIRES`) | — | **203** | 0 |
| R35 | Part des intersections vue par `verifier-rig.py` | **22 %** (672/3009) | 19 % (668/3436) | 100 % |
| R36 | Écart maximal des maillages `Hand_Pinch` / `Hand_OK`, mm | **0,0** | 0,0 | ≠ 0 |
| R37 | Écart contre-épreuve étape 1,0 − action jouée, 6 transitions | **0** | 0 | rester 0 |
| R38 | Poses réellement distinctes dans la bibliothèque | **12 / 13** | 12 / 13 | 13 / 13 |

Sont **déjà bons** et doivent le rester : R01 à R07, R37. Toute itération qui les fait bouger a cassé quelque chose d'acquis.
