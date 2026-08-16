# CHANGELOG

## chat 3 — les instruments d'abord, et ce qu'ils ont revele

**Toujours NON-VALIDE.** Des criteres obligatoires restent faux, nommes dans
[`STATUS.md`](STATUS.md).

### Le fait central

Le verificateur de ce depot jugeait `RIG_Hand.L-NON-VALIDE.blend` « 22 reussis,
9 echoues ». Le verificateur ETENDU rend cinq echecs de plus sur le MEME
fichier : la paume s'aplatit de 10,83 mm au lieu de se creuser, elle s'elargit
de 14,04, le poing ne ferme qu'a 0,55.

**Le rig n'etait pas moins casse avant. L'instrument ne regardait pas.**

### Ce qui est repare, et mesure

| | avant | apres |
| --- | --- | --- |
| `Cup` voute la paume | arc −10,89 mm | **+6,71 mm** |
| `Cup` resserre la paume | largeur +14,04 mm | **−10,79 mm** |
| le cerclage rouge de Sacha | −0,88 mm | **−4,94 mm** |
| poids sans proprietaire | 12 329 ambigus | **0 entre rayons non voisins** |
| os correctifs | inexistants | crees, repos deplace de **0,00013 mm** |
| rendus de preuve | relief local 0,009–0,015 | **0,041–0,049**, 0 image fautive sur 78 |
| la generation | plantait en code 1 | **va au bout** |

`Cup` passe ses **sept criteres**, dont deux qui n'existaient pas : le
resserrement ne repart jamais en arriere, et la voute ne s'effondre jamais en
chemin. Ce sont eux qui auraient attrape le pouce-auriculaire qui se rapprochait
jusqu'a `Cup = 0,5` puis reculait.

### Les deux axes du creusement, elus par la mesure

    voute        axe 0, signe −1     ← CUP employait le sens OPPOSE
    convergence  axe 2, signe −1     ← n'etait pilote par RIEN

Puis l'amplitude cherchee sous contrainte de proprete, et la descente est
monotone : 16 119 → 14 006 → 9 258 → 3 016 → 319 → 4 → **0** traversees.

### Les instruments ajoutes

Onze outils et modules, **51 refus** exerces par les autotests hors Blender.
Trois modules ont ete ecrits par agents PUIS REFUTES par un second agent : onze
defauts reels trouves, dont une garde placee APRES une normalisation donc
aveugle par construction, et une contre-epreuve qui testait IEEE 754 au lieu du
module.

### Ce qui resiste, sans arrondi

- `Hand_Pinky_Thumb` : la pose EXISTE (0,10 mm a l'approche), le nettoyage ne la
  tient pas ;
- `Hand_OK` : l'anneau et le contact sont ANTAGONISTES. L'etape A rend 0,81 mm
  et −0,699 — un excellent contact — avec **aucun anneau** ;
- le poing : les quatre doigts SEULS se traversent 820 fois a `Fist = 0,7` ;
- la main droite n'existe pas : le cahier exige une gauche validee.

### Douze pieges payes

Ils sont en tete du [`README`](README.md). Aucun n'aurait plante bruyamment, et
c'est pour cela qu'ils ont coute des heures.

---

## hands/chat-2-photoreal-v2 — sept causes, et le plantage qui cachait tout

Base : `e2d4b1c9e05949531d9348d68367c225b2169872`

**Toujours NON-VALIDE.** Aucun `.blend` ne reflète encore ces correctifs : la
reconstruction qui devait les prouver est le travail suivant.

### Le fait qui explique les trois tentatives avortées du chat 1

`rig-main.py` **plantait** en fin de course, après les rendus et avant la
sauvegarde : `KeyError: ''`. `_gnom.get(g.group, "")` rendait la chaîne vide
pour un groupe de sommets inconnu, et ce nom vide traversait tous les filtres.
D'où l'absence de tout `.blend` à jour dans ce dépôt, et la ligne « le code de
sortie d'une génération complète n'a jamais été relevé ».

Le même défaut était **latent** dans `verifier-rig.py` et les deux sondes, où
il ne plantait pas : il pouvait faire élire la chaîne vide comme groupe
*dominant* d'un sommet, qui sortait alors de toute famille et de toute mesure
d'intersection, sans un mot.

### Les sept causes

- **le sens de l'écartement est mesuré, plus décrété.** `Spread` entier était
  retourné — monter `Spread` REFERMAIT l'éventail sur les trois couples
  voisins, et `Hand_Open` était la main la plus serrée de la bibliothèque. Ce
  n'était pas l'annulaire : `ECART` est monotone et les drivers l'appliquaient
  au dixième de degré. La phase D mesure désormais `SIGNE_ECART` comme la
  phase C mesure `SENS_FLEXION` ;
- **les doigts étrangers au contact peuvent sortir du chemin.** La sonde jugeait
  15 couples ; la recherche n'avait d'axes que sur deux doigts, et le nettoyeur
  n'avait d'autre issue que de reculer le pouce — 1,08 mm devenait 3,19 mm ;
- **ce qui est obligatoire ne se négocie plus, pour aucun critère.** La doctrine
  n'était câblée que pour l'interpénétration ; distance, orientation et anneau
  s'échangeaient. `Hand_OK` passait de 0,53 mm propre à 1,04 mm après
  « nettoyage » ;
- **les transitions sont corrigées, plus seulement mesurées.** Elles faisaient
  échouer la construction depuis le chat 1 sans que rien ne les touche ;
- **la chaîne distale des deux pulpes en contact est cherchable.** Les 17
  traversées de `Hand_Pinch` étaient entre les deux phalanges distales
  elles-mêmes : l'index ne pouvait pas présenter sa pulpe à plat ;
- **l'éclairage rasant entre dans le pipeline.** Prouvé isolément depuis le
  chat 1, jamais exécuté. Six vues par pose, et trois critères mesurés image
  par image ;
- **deux mesures ne mesuraient pas ce qu'elles annonçaient** : le critère
  « aucune interpénétration » ne regardait qu'un patch de 5 mm — vert avec
  213 sommets traversants — et la fermeture du poing dite « sans le pouce »
  était mesurée avec un pouce au repos en travers du chemin, ce qui bridait le
  poing à 60 %.

### Réfuté

Les « 80 paires majeur/annulaire à `Spread = 1` » : **0 traversée aux 21 pas**
du balayage, et 6,84 mm d'écart au pas incriminé.

### Corrigé dans la documentation

`Hand_Point` vaut **1 528** sommets et `Hand_Pinky_Thumb` **1 271** — non 978
et 717. Mêmes poses, mêmes couples, verdict inchangé.

### Trois outils

`outils/sonde-ecartement.py`, `outils/comparer-rapports.py`,
`outils/playblast-transitions.py`. Tous trois sortent en code non nul sur
verdict négatif ; le dernier n'a jamais été exécuté.


## wip/chat-1-honest-probe — checkpoint de transmission (NON VALIDE)

Base : `b17e54806f942736e47c4dcfd477a91b7fd6f262`
SHA de ce checkpoint : `3454e5c61fb6f80acd5cec7a6286220c229cc03e`

**Aucun `.blend` de cette branche ne reflète ces corrections.** Le
`RIG_Hand.L-NON-VALIDE.blend` présent date de la base et n'a pas été remplacé.

### L'instrument, d'abord

- sonde d'auto-intersection portée de **5 à 15 couples** de familles, comptés
  **dans les deux sens** — l'ancienne ne voyait que **22 %** des traversées
  (672 sur 3 009) ;
- groupes non-os (`ZONES_ARTICULAIRES`) exclus du classement par famille :
  203 sommets étaient mal attribués ;
- `verifier-rig.py` contrôle désormais les **13 poses** et les **6 transitions**
  à 11 étapes, au lieu de 4 poses et aucune transition ;
- une pose absente du fichier est un **échec**, plus un silence ;
- le vérificateur ne force plus le mode de rotation des os : il ne modifie plus
  l'objet qu'il juge.

### Ce que les scripts ne peuvent plus cacher

- `--python-exit-code 1` documenté : les scripts sortaient en **code 0 après un
  plantage** ;
- sorties déstamponnées : trois exécutions de 11, 16 et 34 minutes n'avaient
  écrit **aucun octet**, rendant un blocage indiscernable d'un calcul long.

### Anatomie — écrit, pas encore validé

- fermeture en **cascade MCP → PIP → DIP**, par écrêtage des butées ;
- `Hand_Pinch` et `Hand_OK` séparés — ils étaient **la même action** (0,0 mm
  d'écart, empreinte identique) ;
- **mesure de l'anneau** du signe OK et du **creux palmaire** ;
- nettoyeur générique de pose appliqué aux 13 poses ;
- bases métacarpiennes distribuées en arc, divergence des doigts cherchée par
  la mesure.

### Sauvé de `/tmp`

- `atelier/eclairage.py` — lumière rasante, key à 75° de la normale,
  **0 % d'écrêtage sur 18 images**. Prouvé isolément, **jamais intégré** au
  pipeline ;
- les trois rapports d'agents, l'audit de collisions et 18 rendus de preuve.

### Réfuté

Le signalement « gros plan paume de `Hand_OK` vide » : mesuré deux fois,
**82,5 % de sujet**, contraste normal. Aucune des 60 images n'est vide ni
surexposée.
