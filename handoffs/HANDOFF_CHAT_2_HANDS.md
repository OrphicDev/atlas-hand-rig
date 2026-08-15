# HANDOFF — chat 1 → chat 2 (mains)

## Ce que tu reprends

| | |
| --- | --- |
| dépôt | `OrphicDev/atlas-hand-rig` |
| **branche à reprendre** | `wip/chat-1-honest-probe` |
| **SHA du checkpoint** | `3454e5c61fb6f80acd5cec7a6286220c229cc03e` |
| base auditée, intacte | `b17e54806f942736e47c4dcfd477a91b7fd6f262` (`main`) |
| Blender | **5.1.2**, aucun add-on |

`main` n'a pas bougé. Ce checkpoint ne prétend rien livrer.

---

## Le seul fait qui compte avant de commencer

**L'ancienne sonde d'auto-intersection ne voyait que 22 % des traversées** —
672 sur 3 009. Tout ce que le chat 1 a déclaré « validé » avant cette
découverte reposait dessus. Ne fais confiance à aucun chiffre du commit
`b17e548` sans le remesurer.

Trois causes, toutes corrigées dans cette branche :

1. **5 couples de familles testés sur 15.** `thumb/pinky` n'était jamais
   examiné — il vaut **556 sommets** dans `Hand_Pinky_Thumb`, la pose qui met
   justement le pouce contre l'auriculaire.
2. **Comptage dans un seul sens.** `ring/pinky` rend **0** dans le sens qui
   était testé et **403** dans l'autre. « A dans B » et « B dans A » ne sont pas
   la même question.
3. **9 poses sur 13 jamais contrôlées.**

Plus une pollution : le groupe `ZONES_ARTICULAIRES` — qui n'est l'os de
personne — dominait 203 sommets et brouillait le classement par famille.

---

## Architecture modifiée dans cette branche

### Fichiers faisant autorité

| fichier | rôle |
| --- | --- |
| `rig-main.py` | construit tout ; c'est la seule source du rig |
| `verifier-rig.py` | juge un `.blend` **sans le reconstruire** — 13 poses + 6 transitions |
| `atelier/eclairage.py` | lumière rasante et cadrage, **jamais encore intégré** |
| `atelier/{humain,articulations,mains,portillon}.py` | mesures et portillon |
| `audit/wip-chat-1/audit-collisions.py` | audit indépendant, second regard |

### Nouvelle logique de mesure

- **auto-intersection** = plus proche voisin à moins de 8 mm, profondeur
  > 0,5 mm, **et distance de repos entre les deux sommets > 14 mm**. Cette
  dernière condition est indispensable : le maillage est continu, sans elle on
  compte la continuité du maillage comme une traversée. Le seuil de 0,5 mm a
  été contre-éprouvé — une fermeture pleine sans écartement rend 780 sommets,
  donc il voit bien les vraies fautes.
- **contact** mesuré **localement** : on cherche le point le plus proche, puis
  on ne mesure que le patch de 5 mm autour — distance, normales locales,
  étendue, pénétration. La moyenne globale d'une pulpe pouvait annoncer une
  belle orientation pendant que la zone réellement en regard se présentait de
  travers.
- **anneau du OK** : écart entre les segments proximaux du pouce et de l'index.
  Un anneau se reconnaît à son trou.
- **creux palmaire** : flèche de la paume sous le plan poignet–jointures.

### Deux pièges de Blender, mesurés et non supposés

1. **Les drivers ne s'évaluent pas en mode fond** sans changement d'image.
   Après toute modification de pose : `rig.update_tag()`, puis
   `bpy.context.scene.frame_set(...)`, puis `bpy.context.view_layer.update()`.
   Sans ça tu mesures une main immobile — et une main immobile revient toujours
   exactement à sa pose de repos, donc elle passe le contrôle.
2. **L'évaluateur d'expressions n'accepte que des droites.** `min`, `max` et le
   produit de deux variables échouent **en silence** (`is_valid = false`, la
   rotation reste à 0,00°). La cascade de fermeture est donc construite en
   surpilotant des droites que les butées écrêtent.

---

## Commandes exactes

Vérifier un `.blend` — aucun téléchargement :

```bash
blender --background --factory-startup --python-exit-code 1 --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

Reconstruire — demande le maillage de base :

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend
blender --background --factory-startup --python-exit-code 1 --python rig-main.py -- ./sortie homme g 110 mesure
```

`--python-exit-code 1` **n'est pas décoratif** : sans lui, les scripts sortent
en code 0 après un plantage, et un échec se lit comme un succès.

L'argument `mesure` évite les 60 rendus. **Compte plus de 30 minutes** pour la
reconstruction ; la sortie est déstamponnée, donc tu verras les phases défiler.

---

## Résultats

### Reproductible — smoke test exécuté sur ce checkpoint

`verifier-rig.py` sur `RIG_Hand.L-NON-VALIDE.blend` : **code de sortie 2**,
**22 critères passent, 9 échouent**.

| en échec | sommets | couples |
| --- | ---: | --- |
| `Hand_Point` | 978 | thumb/middle, thumb/ring, index/middle, middle/ring |
| `Hand_Pinky_Thumb` | 717 | thumb/index, thumb/middle, thumb/pinky, thumb/hand |
| `Hand_Fist_75` | 118 | thumb/index, index/middle, middle/ring |
| `Hand_Cupped` | 80 | middle/ring |
| 4 transitions sur 6 | — | `Neutral→` Fist, Point, Cupped, Pinky_Thumb |

Le `.blend` mesuré **date de `b17e548`** et ne contient pas les corrections de
scripts de cette branche. Ces chiffres décrivent l'état audité vu par un
instrument honnête — **ce n'est pas une régression**.

### Observé localement seulement — à reproduire

Mesures prises dans le chat 1 sur une exécution **interrompue avant la fin**,
jamais reproduites depuis le commit public :

| pose | mesure locale | seuil |
| --- | --- | --- |
| `Hand_Pinch` | 3,19 mm | ≤ 1,00 mm |
| `Hand_OK` | 1,04 mm, orientation −0,46 | ≤ 1,00 mm, ≤ −0,50 |
| `Hand_Pinky_Thumb` | 2,46 mm, orientation −0,08 | ≤ 1,00 mm, ≤ −0,50 |

### Observation visuelle, non confirmée par le pipeline

Détection BVH indépendante de l'agent lumière : `Spread = 1` ferait se
traverser **majeur et annulaire, 80 paires**. L'écartement rapprocherait au
lieu de séparer — signe ou axe probablement inversé sur l'annulaire.

### Réfuté par la mesure

Le gros plan paume de `Hand_OK` était signalé vide : **82,5 % de sujet**,
contraste normal, mesuré deux fois. Sur les 60 images, **aucune n'est vide ni
surexposée** (pixel maximal 229/255 = 0,898). Une seule image mérite d'être
refaite : `gros-plan-Hand_Pinky_Thumb-pouce.png`, écart-type de luminance
14,94 contre 41,76 minimum ailleurs.

---

## Tentatives abandonnées — ne les refais pas

1. **Piloter la divergence des doigts par un driver.** Trois essais : produit de
   deux variables, expression linéaire, renommage de la variable. Le driver
   restait `is_valid = false` pendant que ses voisins du même os
   fonctionnaient, sans le moindre message. La divergence est passée en axe de
   recherche sur les contrôleurs, et **ça marche**.
2. **Le lissage correctif (phase G) sur le pincement du pouce.** Mesuré : gains
   **négatifs** sur les trois doigts testés. Il a été retiré plutôt que gardé
   pour masquer un mauvais poids.
3. **La barrière lexicographique seule** pour les contacts. À 10⁶ par sommet,
   un unique sommet marginal valait plus que tout le contact : la recherche
   abandonnait un appui à 0,86 mm pour aller à 16 mm. La barrière de nettoyage
   est désormais **haute mais finie** (20 000), et la distance cesse de coûter
   sous 1 mm.

---

## Ta première tâche, atomique

**Reprendre les trois contacts contre la sonde honnête.** `Hand_Pinch`,
`Hand_OK` et `Hand_Pinky_Thumb` doivent satisfaire les **15 couples** de
familles, dans les deux sens — la recherche actuelle n'en satisfaisait que 5.
C'est la seule tâche à faire avant toute autre : tant qu'elle n'est pas faite,
aucune mesure de contact n'est comparable.

**Deuxième tâche : le signe d'écartement de l'annulaire.** `ECART` vaut
`{index: +10, middle: +1, ring: −6, pinky: −12}` dans `rig-main.py`. Vérifie le
signe ET l'axe local — la phase C a montré que `align_roll` met la normale sur
**X** et non sur Z, contrairement à ce qu'on croit en lisant la documentation.

### Ensuite

3. volumes articulaires : effet « saucisse », dômes de jointures absents au dos
   du poing ;
4. **main droite** — le brief exige qu'elle dérive d'une gauche *validée* ;
5. playblasts des 6 transitions ;
6. revue visuelle argumentée, cible 8/10 ;
7. **intégrer `atelier/eclairage.py`** dans `rig-main.py` : prouvé isolément
   (0 % d'écrêtage sur 18 images, key à 75° de la normale), jamais exécuté dans
   le pipeline.

---

## Où est quoi

```
atelier/eclairage.py              le module de lumière rasante
reports/wip-chat-1/               les trois rapports d'agents + smoke test
audit/wip-chat-1/                 l'audit indépendant de collisions
renders/wip-chat-1/preuves-lumiere/   18 rendus, preuve du module
renders/wip-chat-1/planche-lumiere.html
images/, images/gros-plans/       les rendus de b17e548, inchangés
```

Rien d'important ne vit plus dans `/tmp`.
