# Rapport final — chat 3, main gauche

> **STATUT : NON-VALIDE.** Des critères obligatoires restent faux. Ils sont
> nommés ici sans arrondi, avec leur cause quand elle est trouvée et avec ce
> qui manque quand elle ne l'est pas.

Ce rapport est écrit au fil du travail et daté par les commits qu'il cite. Il
ne contient aucun nombre recopié : chacun vient d'un journal de run, et le run
est nommé.

---

## 1 · Ce qu'il faut savoir avant de lire le reste

Le vérificateur de ce dépôt jugeait `RIG_Hand.L-NON-VALIDE.blend` **« 22
critères réussis, 9 échoués »**. Le vérificateur **étendu**, lancé sur le
**même fichier**, rend **cinq échecs de plus** : la paume s'aplatit de 10,83 mm
au lieu de se creuser, elle s'élargit de 14,04, le poing ne ferme qu'à 0,55.

**Le rig n'était pas moins cassé avant. L'instrument ne regardait pas.**

Tout ce qui suit découle de cette phrase, y compris les défauts que j'ai
moi-même introduits et rattrapés.

---

## 2 · Repères techniques

| | |
| --- | --- |
| dépôt | `OrphicDev/atlas-hand-rig` |
| branche | `hands/chat-2-photoreal-v2` |
| commit de départ (chat 2) | `e2d4b1c9e05949531d9348d68367c225b2169872` |
| HEAD audité (chat 3) | `96d017755504499545c340fa404922a631c48826` |
| commits sur la branche | 77 |
| Blender | 5.1.2 (`ec6e62d40fa9`, 2026-05-19) |
| machine | macOS 26.5, Apple Silicon, 10 cœurs |
| maillage de base | `human-base-meshes-bundle-v1.4.1`, 49 420 489 octets |
| SHA-256 du maillage | `3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137` |
| licence du maillage | CC0 — Blender Studio |

### Les commandes, et ce qu'elles rendent

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend
```

Juger le `.blend` livré — ne demande **aucun** téléchargement :

```bash
blender --background --factory-startup --python-exit-code 1 --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

Reconstruire entièrement :

```bash
blender --background --factory-startup --python-exit-code 1 --python rig-main.py -- sortie homme g 110 mesure
```

Apprendre vite, sur une seule question :

```bash
blender --background --factory-startup --python-exit-code 1 --python rig-main.py -- work homme g 110 mesure focus=cup
```

Les épreuves qui ne demandent pas Blender :

```bash
python3 outils/epreuve-focus.py && python3 outils/epreuve-classement-ok.py
```

`--python-exit-code 1` n'est pas décoratif : sans lui, les scripts sortent en
**code 0 après un plantage**, et un échec se lit comme un succès.

---

## 3 · Ce qui est réparé, et prouvé par la mesure

| | avant | après |
| --- | ---: | ---: |
| `Cup` voûte la paume | arc **−10,89 mm** | **+6,71 mm** |
| `Cup` resserre la paume | largeur **+14,04 mm** | **−10,79 mm** |
| le cerclage rouge de Sacha (pouce↔auriculaire) | **−0,88 mm** | **−4,94 mm** |
| poids sans propriétaire | **12 329** ambigus | **0** entre rayons non voisins |
| os correctifs | inexistants | créés, repos déplacé de **0,00014 mm** |
| relief local des rendus | 0,009–0,015 | **0,041–0,049** |
| images fautives | 8 gros plans sur 8 | **0 sur 78** |
| la génération | plantait en code 1 | **va au bout** |

`Cup` passe ses **sept** critères, sur **trois runs indépendants**. Deux de ces
sept n'existaient pas : le resserrement ne repart jamais en arrière, et la
voûte ne s'effondre jamais en chemin. Ce sont eux qui auraient attrapé le
pouce-auriculaire qui se rapprochait jusqu'à `Cup = 0,5` puis reculait.

### Les deux axes du creusement, élus par la mesure et non décrétés

    voûte         axe 0, signe −1     ← CUP employait le sens OPPOSÉ
    convergence   axe 2, signe −1     ← n'était pilotée par RIEN

Puis l'amplitude cherchée **sous contrainte de propreté**, et la descente est
monotone : 16 119 → 14 006 → 9 258 → 3 016 → 319 → 4 → **0** traversées.

---

## 4 · Ce qui résiste, avec sa cause

### 4.1 · Le poing s'arrête à 0,60 — pour **un** sommet

La courbe des quatre doigts seuls, pas à 0,02 :

    0,00 → 0,60   0 traversée
    0,62          1 traversée
    …             jamais mesuré

`_profondeur_propre` s'arrêtait au **premier** niveau non nul. Elle supposait
la courbe monotone sans l'avoir jamais vérifié. Le dépôt écrivait « 820
traversées à 0,7 » **et** « fermeture retenue 0,6 » comme si c'était la même
mesure : ce sont deux points d'une courbe dont personne n'avait vu le milieu.

Le balayage va désormais jusqu'à 1,0 quoi qu'il arrive, rend la courbe entière,
dit si c'est un **accident** ou un **mur**, et appelle `ou_ca_traverse` au
premier niveau sale pendant que la pose existe encore.

**Le verdict ne change pas** : on rend toujours le dernier niveau tel que TOUT
ce qui précède est propre. Un poing qui se traverse en chemin ne se rattrape
pas d'avoir l'air propre plus loin.

### 4.2 · `Hand_OK` A un anneau, et il est jeté

| étape | contact | orientation | traversées | anneau |
| --- | ---: | ---: | ---: | ---: |
| A — l'anneau ignoré | **0,81 mm** | −0,699 | 90 | **0,0 mm** |
| B — ±30 % autour de A | 1,03 mm | **−0,764** | **79** | **8,1 mm** |

B est meilleur sur l'orientation **et** sur les traversées, et c'est le seul à
avoir un anneau. Il perd sur **trois centièmes de millimètre** de contact.

Le classement a raison de garder A : B viole un critère obligatoire de plus.
**La faute est dans la recherche.** L'étape A ignore l'anneau, donc
l'optimiseur plaque les deux pulpes l'une contre l'autre et referme le trou ; B
ancrée à ±30 % de cet état ne peut qu'améliorer un anneau que A a écrasé — elle
ne peut pas changer de bassin.

L'étape **C** repart de toute la course avec l'anneau obligatoire dès le début.

### 4.3 · `Hand_Pinch` échoue de six centièmes à cause de **deux** sommets

| | distance | traversées |
| --- | ---: | ---: |
| après l'approche | **0,83 mm** | 2 |
| après le nettoyage | **1,06 mm** | 0 |

Les deux sommets sont `DEF_index_meta.L → DEF_thumb_meta.L` : l'éminence thénar
contre la base de l'index, **dans la commissure**, sans aucun rapport avec le
pincement. N'ayant aucun moyen de faire céder de la chair, le nettoyeur recule
le pouce entier de 0,23 mm.

C'est très exactement ce que les os correctifs de volume savent faire, et ils
ne sont cherchés que pour `Hand_Pinky_Thumb`.

### 4.4 · `Hand_Pinky_Thumb` — deux causes trouvées

**Deux critères sur trois passent désormais**, et la vrille en est la cause
prouvée :

| critère | mesuré | exigé | |
| --- | ---: | ---: | --- |
| les pulpes se touchent | **0,94 mm** | ≤ 1,00 | réussi |
| les pulpes se font face | **−0,732** | ≤ −0,50 | réussi |
| aucune interpénétration | **1 326** | 0 | échec |

L'orientation échouait de 0,213 ; elle passe de 0,232. Avant la vrille, elle
valait **−0,287**.

**Cause 1 — la vrille était verrouillée sur une articulation qui n'est pas une
charnière.** La butée posait `min_y = max_y = 0` sur les trois articulations de
chaque doigt. C'est exact pour la PIP et la DIP. C'est **faux** pour la
métacarpo-phalangienne, qui est condylienne et autorise une rotation axiale
passive — celle, précisément, qui permet à une pulpe de se présenter à plat
contre une autre. Le côté auriculaire n'avait **aucun** canal capable de
tourner une pulpe.

Ouverte à ±10°, la borne basse de ce que la littérature accorde, parce qu'une
vrille généreuse fabrique des poses que la recherche adorerait et qu'un
animateur trouverait fausses.

Et **mesurée avant d'être crue** — un garde tord chaque os de 10° et refuse de
continuer si aucune chair ne bouge :

    CTRL_pinky_01.L   1,876 mm
    CTRL_thumb_01.L   2,427 mm
    CTRL_index_01.L   2,724 mm

**Cause 2 — le correctif était câblé sur une propriété que la pose laisse à
zéro.** L'amplitude est cherchée avec `PSD_PinkyThumb = 1` dans une copie
**locale**. Le driver est câblé sur cette propriété. Mais la pose livrée est
construite depuis `CONTACTS[…]["props"]`, où `PSD_PinkyThumb` n'a jamais été
touché et vaut **0**.

La correction était mesurée, retenue, câblée, vérifiée sous les 3 mm — et
**jamais appliquée à la pose pour laquelle elle existe**.

**Ce qui reste, et le diagnostic le sépare en trois causes au lieu d'un total :**

| sommets | où | ce que c'est |
| ---: | --- | --- |
| **400** | `middle_03 → thumb_meta` | le majeur enroulé à 0,95 s'enfonce dans le thénar |
| **200** | `pinky_meta ↔ thumb_meta` | les deux éminences de la paume l'une sur l'autre |
| **171** | `thumb_02 ↔ pinky_02` | les deux segments en contact, **hors** des pulpes |

**La première est le problème du poing.** Pour laisser passer le pouce vers
l'auriculaire, l'index et le majeur doivent s'enrouler à 0,95 — très au-delà de
la fermeture propre mesurée à 0,60. Les deux blocages du cahier n'en font
qu'un : tant que les quatre doigts ne se ferment pas proprement, aucune pose
qui les enroule ne peut être propre.

### 4.5 · Les transitions ne peuvent pas être plus propres que leur arrivée

L'étape t = 1,0 **est** la pose finale. `Hand_Fist` passe de 218 traversées à
t = 0,6 à 1812 à t = 0,7, et sa pose d'arrivée en compte **1596** à elle seule.
Trois rondes de six tours ont tourné là-dessus pendant près de deux heures sans
pouvoir aboutir, et l'échec se lisait ensuite comme un échec de **transition**
alors que c'est un échec de **pose**.

Le critère échoue toujours, mais il nomme sa vraie cause et n'y passe plus
d'heures.

### 4.6 · La main droite n'existe pas

Le cahier exige qu'elle dérive d'une gauche **validée**. `atelier/miroir.py`
est écrit et éprouvé (5 refus exercés), avec une table de signes **mesurée** et
non supposée. Il attend.

---

## 5 · Les rendus

| grandeur | résultat |
| --- | --- |
| images | **78** — treize poses, six vues |
| écrêtées | **aucune** |
| écrêtage | **0,000 %** sur les 78 |
| rasance de la key | **75,0°** exactement |
| relief local | **0,041 à 0,049** pour 0,020 exigé |
| images fautives | **0 sur 78** |
| planches de contact | **14** |

Le relief local est **trois fois meilleur** que sur la série du chat 1
(0,009–0,015), qui n'atteignait le seuil sur **aucun** de ses huit gros plans.
La cause était physique : le module dimensionnait la source proportionnellement
à la distance, donc son angle apparent restait 12° à toutes les échelles — sur
un gros plan à 55 mm, les plis sont eux-mêmes à l'échelle de ce flou. Les gros
plans passent à 4°.

Les deux directions rasantes ne sont pas un luxe : `paume-A` et `paume-B` ne
montrent pas les mêmes plis, parce qu'une rasante ne révèle que ceux qui lui
sont perpendiculaires.

### Ce que les planches rendent visible

- **`Fist` n'est pas un poing.** Les doigts sont à peine repliés. « Fermeture
  retenue 0,6 » ne se corrige pas ; une main qui ne ferme pas, si.
- **`OK` n'a pas d'anneau.** `outils/anneau.py` refusait de rendre un nombre —
  « le contour projeté n'enferme aucun vide » — et la planche donne raison à
  son refus.
- **`Open` et `Spread_Min` sont enfin dans le bon sens.** Avant le correctif de
  signe, les deux poses portaient le nom de leur contraire.
- **`Point` est juste** : index tendu, les trois autres repliés.

---

## 6 · Les instruments, et les refus qu'ils exercent

Onze outils et modules, **51 refus** exercés par les autotests **hors Blender**
à chaque exécution, plus deux épreuves ajoutées :

| épreuve | ce qu'elle empêche |
| --- | --- |
| `outils/epreuve-focus.py` | qu'un mode ciblé réponde à côté de la question |
| `outils/epreuve-classement-ok.py` | qu'un critère obligatoire s'achète avec de la marge sur un autre |

Trois modules ont été écrits par agents **puis réfutés** par un second agent :
onze défauts réels trouvés, dont une garde placée **après** une normalisation —
donc aveugle par construction — et une contre-épreuve qui testait IEEE 754 au
lieu du module.

> **Une sonde doit pouvoir échouer.** Un instrument qui rend zéro parce qu'il
> ne mesure rien est indiscernable d'un instrument qui rend zéro parce que tout
> va bien — sauf si on l'a construit pour pouvoir tomber.

---

## 7 · Ce que j'ai cassé moi-même, et rattrapé

Ces lignes ne sont pas de l'humilité décorative : chacune est un défaut que
j'ai introduit, qui n'aurait pas planté, et qui aurait rendu un verdict
crédible.

1. **`max(_propres)` sur une courbe complète.** En faisant aller le balayage du
   poing jusqu'au bout, j'ai rendu fausse la règle qui lisait son résultat :
   elle aurait enjambé la traversée de 0,62 et déclaré le poing **fermé à
   1,0**. Contre-épreuve hors Blender sur la courbe réellement mesurée :
   nouvelle règle 0,6, ancienne règle **1,0**.
2. **Une contre-épreuve qui ne mordait pas.** Mon test « l'ordre des critères
   agit » utilisait un cas qui rend le même verdict qu'on classe ou qu'on
   somme. Il ne prouvait rien. Remplacé par un couple où celui qui viole trois
   critères bas bat celui qui n'en viole qu'un haut placé.
3. **Une attente fausse dans mon propre test.** J'attendais qu'un candidat
   propre mais ratant le contact de 1,5 mm perde contre un candidat qui se
   traverse 90 fois. Il gagne, et il a raison : l'interpénétration est le
   premier critère du cahier.
4. **`_h.get("ecretage", 0.0)`** sur une clé nommée `ecretage_pct` : chaque
   image aurait rendu 0 % d'écrêtage et 0° de rasance, et trois critères
   d'éclairage seraient passés **en ne mesurant rien**.
5. **Un `except` qui laissait l'armature en mode édition** : tout ce qui
   suivait mesurait une main immobile — compression 1,0, zéro traversée sur un
   poing qui ne se fermait jamais.
6. **Une origine relevée avant que l'origine soit décidée** : 0,0401 mm de
   dérive.
7. **Un critère qui punissait exactement ce que l'anatomie exige** — le mélange
   entre rayons voisins, que la règle 7 déclare légitime.
8. **Une tranche à un seul bord** : 844 sommets d'index, 0 de pouce, un disque
   de 19,1 mm inscrit dans un **pincement**.

---

## 8 · Réfuté

- Les « **80 paires majeur/annulaire** à `Spread = 1` » : **0 traversée** aux 21
  pas du balayage, et 6,84 mm d'écart au pas incriminé.
- Le « gros plan paume de `Hand_OK` vide » : mesuré deux fois, **82,5 % de
  sujet**, contraste normal. Aucune des 60 images n'était vide ni surexposée.
- Mon hypothèse « les traversées métacarpien↔métacarpien sont un artefact de
  sonde, puisque ces os ne bougent pas les uns par rapport aux autres » :
  **réfutée par la lecture du code**. Le garde `ECART_REPOS_MINIMAL` de 14 mm
  exclut déjà les surfaces voisines au repos ; ce qui reste est l'éminence
  thénar qui se replie réellement contre la base de l'index.
- Mon hypothèse « il suffit d'ajouter l'axe de vrille aux axes de recherche » :
  **réfutée avant d'être écrite**. La butée verrouillait cet axe à zéro ;
  l'ajouter aurait été un canal mort que l'optimiseur aurait exploré en rendant
  le même score à toutes ses valeurs.

---

## 9 · Corrigé dans la documentation

`Hand_Point` vaut **1 528** sommets et `Hand_Pinky_Thumb` **1 271** — non 978
et 717. Mêmes poses, mêmes couples, verdict inchangé ; seuls les totaux étaient
recopiés d'une autre addition.

---

## 10 · Les pièges déjà payés

Ils sont en tête du [`README`](../../../README.md), au nombre de quinze. Aucun
n'aurait planté bruyamment, et c'est pour cela qu'ils ont coûté des heures. Les
trois derniers viennent de ce chat :

13. **Une mesure qui s'arrête au premier échec suppose la courbe monotone.**
14. **Un mode ciblé qui répond à côté de la question est pire qu'un mode
    absent** — il rend « 0 critère obligatoire en échec » pour une section
    qu'il n'a pas atteinte.
15. **Un axe verrouillé par une butée reste cherchable par l'optimiseur.**

---

## 11 · Ce qu'il reste, dans l'ordre

1. une reconstruction complète portant les quatre correctifs de cause ;
2. le poing à `Fist = 1,0`, ou la démonstration que c'est un mur ;
3. l'étape C du OK, ou la démonstration qu'aucun bassin ne tient les deux ;
4. les gros plans à lumière dure et les overlays rouges avant/après ;
5. les six séquences jouant les **vraies** actions ;
6. la main droite, et l'écart de symétrie mesuré.

---

## 12 · Ma note sur le rig, argumentée

**5 sur 10.**

- **+3** pour la chaîne de rendu : irréprochable et prouvée sur 78 images ;
- **+1** pour l'écartement, visible et corrigé ;
- **+1** pour `Point`, `Neutral`, `Relaxed` et les trois `Fist_25/50/75` ;
- **−3** parce que le poing, la pose la plus attendue d'une main, n'en est pas
  un ;
- **−2** parce qu'un signe OK sans trou n'est pas un signe OK.

Un 5 et pas moins parce que la moitié de ce qui manquait au chat 1 est
désormais mesurable **et** mesurée. Un 5 et pas plus parce que **deux des
treize poses ne font pas ce que leur nom annonce** — exactement le reproche que
ce dépôt s'était déjà fait avec `Hand_Open`.
