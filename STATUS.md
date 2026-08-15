STATUS: NON-VALIDE — CHECKPOINT WIP DE TRANSMISSION

Ce dépôt n'est pas dans un état livrable. Ce fichier existe pour qu'aucun
lecteur ne puisse s'y tromper.

---

## Repères

| | |
| --- | --- |
| base publique auditée | `b17e54806f942736e47c4dcfd477a91b7fd6f262` (branche `main`) |
| branche de ce checkpoint | `wip/chat-1-honest-probe` |
| commit de ce checkpoint | `3454e5c61fb6f80acd5cec7a6286220c229cc03e` |
| `.blend` reflétant ces corrections | **aucun** |
| processus encore actifs | **aucun** |


> **Sur les deux SHA.** Le commit de contenu est `3454e5c61fb6f80acd5cec7a6286220c229cc03e`. Le
> commit qui porte l'étiquette de tête ajoute uniquement l'inscription
> de ce SHA dans les documents — un fichier ne peut pas contenir sa
> propre empreinte. Clone la **tête de branche** : elle contient tout.

**`main` n'est pas touchée.** Aucun `force push`, aucune réécriture d'historique,
aucun merge, aucun tag.

## Il n'existe aucun `.blend` à jour

Le `RIG_Hand.L-NON-VALIDE.blend` présent dans ce dépôt **date de `b17e548`**. Il
a été construit **avant** les corrections de sonde décrites ci-dessous, et ne
les contient donc pas. La reconstruction qui l'aurait remplacé a été **arrêtée
avant la fin** : aucun fichier fiable n'en est sorti, et rien n'a été republié
sous un nom laissant croire le contraire.

---

## Ce que ce checkpoint apporte

La correction principale ne porte pas sur le rig : **elle porte sur
l'instrument qui le juge.**

### Mesure confirmée — l'ancienne sonde était aveugle à 78 % des traversées

Établi par un agent d'audit indépendant, sur le `.blend` de `b17e548` :
**672 traversées détectées sur 3 009 réellement présentes.** Trois causes
cumulées :

| cause | conséquence mesurée |
| --- | --- |
| **5 couples de familles testés sur 15** | `thumb/pinky` jamais examiné : **556 sommets** dans la pose qui met justement le pouce contre l'auriculaire |
| **comptage dans un seul sens** | `ring/pinky` : **0** dans le sens testé, **403** dans l'autre |
| **9 poses sur 13 jamais contrôlées** | `Hand_Point` **1 540**, `Hand_Fist_75` **118**, `Hand_Cupped` **80** |

S'y ajoutait une pollution : le groupe de sommets `ZONES_ARTICULAIRES`, qui
n'est l'os de personne, dominait **203 sommets** — il fabriquait des
intersections fantômes sur `Pinch` et `OK`, et en cachait de vraies sur `Point`.

### Mesure confirmée — deux poses n'en faisaient qu'une

`Hand_Pinch` et `Hand_OK` étaient **la même action** : **0,0 mm** d'écart
maximal sur 54 019 sommets, empreinte identique sur 73 courbes, et rendus
identiques au pixel près. La bibliothèque annonçait 13 poses ; elle en
contenait **12**.

### Mesure confirmée — les scripts mentaient sur leur propre échec

Les deux scripts sortaient en **code 0 après un plantage** (fichier
introuvable, maillage absent) : un échec se lisait comme un succès. Et Blender
tamponnant en amont de Python, **trois exécutions de 11, 16 et 34 minutes
n'avaient écrit aucun octet** — impossible de distinguer un calcul long d'un
blocage, ni de lire l'erreur qui avait tout arrêté.

---

## Ce qui a été corrigé dans les scripts de cette branche

- sonde d'intersection portée à **15 couples**, comptés **dans les deux sens** ;
- **groupes non-os exclus** des familles (`ZONES_ARTICULAIRES` et assimilés) ;
- contrôle des **13 poses**, plus l'échantillonnage des **6 transitions** à
  11 étapes (0,0 → 1,0) ;
- fermeture en **cascade MCP → PIP → DIP**, obtenue par écrêtage des butées
  anatomiques — l'évaluateur de drivers de Blender n'accepte que des
  expressions linéaires, ce qui a été mesuré et non supposé ;
- **`Hand_Pinch` et `Hand_OK` séparés** : plages d'index disjointes, doigts
  libres relâchés d'un côté et ouverts de l'autre ;
- **mesure de l'anneau** du signe OK (l'écart entre les segments proximaux du
  pouce et de l'index) — un anneau se reconnaît à son trou, et un trou se
  mesure ;
- **nettoyeur générique de pose** : corrections FK minimales supprimant les
  traversées sans réécrire l'intention de la pose ;
- **mesure du creux palmaire** (flèche de la paume sous le plan
  poignet–jointures) ;
- sorties **déstamponnées** et `--python-exit-code 1` documenté ;
- **module d'éclairage rasant** sauvé de `/tmp` vers `atelier/eclairage.py`.

---

## Résultats locaux WIP — à reproduire avant d'y croire

Ces chiffres viennent de l'**état local du chat 1** et n'ont **pas** été
reproduits depuis le commit public. Le chat 2 doit les remesurer.

| pose | mesure locale | seuil |
| --- | --- | --- |
| `Hand_Pinch` | **3,19 mm** | ≤ 1,00 mm |
| `Hand_OK` | **1,04 mm**, orientation **−0,46** | ≤ 1,00 mm, ≤ −0,50 |
| `Hand_Pinky_Thumb` | **2,46 mm**, orientation **−0,08** | ≤ 1,00 mm, ≤ −0,50 |

**Ces contacts échouaient déjà avant** : ils passaient sous l'ancienne sonde
parce qu'elle ne voyait pas ce qui les empêchait. Ce n'est pas une régression
du rig, c'est la fin d'une illusion de mesure. La recherche de pose doit
maintenant satisfaire 15 couples au lieu de 5, ce qui n'a pas encore été fait.

### Observation visuelle, non confirmée par la mesure du pipeline

Relevé par l'agent lumière via une détection BVH indépendante :
`Spread = 1` ferait se traverser **majeur et annulaire, 80 paires** —
l'écartement rapprocherait au lieu de séparer. Signe ou axe probablement
inversé sur l'annulaire. **À reproduire** : ce chiffre ne vient pas du
pipeline principal.

### Signalement client réfuté par la mesure

Le gros plan paume de `Hand_OK` était signalé comme vide. Mesuré deux fois :
**82,5 % de sujet**, contraste normal. Sur les 60 images, **aucune n'est vide
ni surexposée** — valeur de pixel maximale **229/255 = 0,898**. Une seule image
mérite d'être refaite : `gros-plan-Hand_Pinky_Thumb-pouce.png`, écart-type de
luminance **14,94 contre 41,76 minimum ailleurs**.

---

## Ce qui reste à faire

1. reprendre les trois contacts **contre la sonde honnête** ;
2. corriger le **signe d'écartement de l'annulaire** ;
3. volumes articulaires : effet « saucisse », dômes de jointures absents au dos
   du poing ;
4. **main droite** — le brief exige qu'elle dérive d'une gauche *validée*, qui
   ne l'est pas ;
5. playblasts des transitions, revue visuelle 8/10 ;
6. refaire `gros-plan-Hand_Pinky_Thumb-pouce.png` ;
7. **intégrer `atelier/eclairage.py` dans le pipeline** — le module est prouvé
   isolément, jamais exécuté dans `rig-main.py`.

## Dernier processus

Dernière exécution : `rig-main.py … mesure`, **arrêtée manuellement** avant la
fin de la recherche `Hand_Pinky_Thumb`. Journal partiel conservé. **Aucun
processus Blender, Python ou commande d'attente ne tourne.**
