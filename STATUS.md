STATUS: NON-VALIDE — CHAT 3 EN COURS

Ce dépôt n'est pas dans un état livrable. Ce fichier existe pour qu'aucun
lecteur ne puisse s'y tromper.

---

## Repères

| | |
| --- | --- |
| **statut global** | **NON-VALIDE** |
| branche active | `hands/chat-2-photoreal-v2` |
| commit de départ | `e2d4b1c9e05949531d9348d68367c225b2169872` |
| dernière étape terminée | `Cup` prouvé 7/7 · poids repeints · 78 rendus Cycles · 14 planches |
| étape suivante | prouver le poing, l'anneau et la pince après quatre correctifs de cause |
| **main gauche** | rig existant, **non validé** |
| **main droite** | **inexistante** |
| `.blend` reflétant les scripts | reconstruction **en cours**, 23 ✓ / 10 ✗ à mi-parcours |
| rendus produits par ces scripts | **78 images**, 0 fautive, écrêtage 0,000 % |
| planches de contact | **14**, dont une d'ensemble des treize poses |
| playblasts de transition | 150 images, rendues depuis l'ancien `.blend` |
| épreuves hors Blender | **51 refus** + 2 nouvelles épreuves |

`main` et `wip/chat-1-honest-probe` n'ont pas bougé. Aucun force push, aucune
réécriture d'historique, aucun merge, aucun tag.

---

## Chat 3 — ce qui est acquis, et ce qui ne l'est pas

Le cahier du chat 3 est **entierement ecrit en code**. Ce qui reste n'est plus
de l'ecriture mais de la mesure : une reconstruction qui aboutisse sur tous les
criteres, puis les rendus Cycles, puis la main droite.

### Les quatre blocages du chat 2, et ou ils en sont

| blocage | avant | maintenant |
| --- | --- | --- |
| `Cup` aplatit et elargit la paume | arc −10,89 mm, largeur +14,04 | **arc +6,71, largeur −10,79** |
| le cerclage rouge de Sacha | −0,88 mm | **−4,94 mm** |
| poids sans proprietaire | 12 329 ambigus, dont pouce/auriculaire | **0 entre rayons non voisins** |
| la generation plante | code 1, aucun `.blend` | **va au bout** |

### Ce qui resiste encore

- **le poing s'arrete a 0,60 pour UN sommet.** La courbe des quatre doigts
  seuls vaut 0 partout jusqu'a 0,60 puis **1** a 0,62. La mesure s'arretait au
  premier niveau non nul : personne n'avait jamais regarde 0,64. Le « 820
  traversees a 0,7 » de ce meme fichier est vrai a 0,7 — c'est l'autre bout
  d'une courbe dont le milieu n'avait pas ete vu ;
- **`Hand_OK` A un anneau, et il est jete.** L'etape A rend 0,81 mm de contact
  et **0,0 mm** d'anneau ; l'etape B rend **8,1 mm** d'anneau, une MEILLEURE
  orientation (−0,764 contre −0,699) et MOINS de traversees (79 contre 90) —
  et perd sur trois centiemes de millimetre de contact. Le classement a raison
  de garder A ; la recherche a tort de ne pas chercher ailleurs. L'etape C part
  de toute la course avec l'anneau obligatoire ;
- **`Hand_Pinch` echoue de six centiemes a cause de DEUX sommets.**
  L'approche tient 0,83 mm avec 2 traversees, toutes deux
  `DEF_index_meta → DEF_thumb_meta` — l'eminence thenar contre la base de
  l'index, dans la commissure, sans rapport avec le pincement. Le nettoyage
  recule le pouce de 0,23 mm pour les effacer ;
- **`Hand_Pinky_Thumb` n'echoue plus que sur l'orientation** des pulpes
  (−0,287 pour −0,50). La distance est tenue a 0,9 mm. Deux causes trouvees :
  la butee verrouillait la vrille a zero sur la metacarpo-phalangienne, qui est
  condylienne et non charniere ; et le correctif de volume etait cable sur
  `PSD_PinkyThumb`, laissee a **0** dans la pose livree ;
- la main droite n'existe pas — le cahier exige une gauche validee.

### Ce que le chat 3 a ajoute aux instruments

| outil | ce qu'il repond |
| --- | --- |
| `outils/sonde-creux.py` | la paume se creuse-t-elle vraiment, et quel axe la creuse |
| `outils/sonde-poids-main.py` | quels sommets n'ont pas de proprietaire |
| `outils/anneau.py` | le diametre UTILE du trou, pas le minimum du contour |
| `outils/revue-visuelle.py` | ce qu'une image montre, avant de la noter |
| `outils/matrice-acceptation.py` | la matrice du cahier, produite et jamais recopiee |
| `atelier/mesures_paume.py` | arc, largeur, convergence — sur la pose courante |
| `atelier/correctifs.py` | masques geodesiques, transfert de poids, shape keys sparse |
| `atelier/transitions.py` | de vraies actions, pas une interpolation recalculee |
| `atelier/jacobienne.py` | convertir un deplacement voulu en delta de cle |
| `atelier/miroir.py` | la main droite se transfere, avec une table de signes mesuree |
| `outils/epreuve-classement-ok.py` | le classement des trois candidats du OK, sur ses nombres reels |
| `outils/epreuve-focus.py` | chaque mode cible s'arrete-t-il a SA section ? |

Cinquante et un refus sont exerces par les autotests purs, hors Blender.

### Quatre defauts de plus, tous de la meme famille

Trouves apres les rendus, tous par lecture ou par mesure, aucun n'aurait plante :

1. **la mesure du poing s'arretait au premier echec**, donc supposait la courbe
   monotone sans l'avoir verifiee ;
2. **quatre des six modes `focus=` repondaient a cote de la question.** La
   sortie etait posee une seule fois, a la fin de `Cup`, et se declenchait pour
   tout focus autre que `all`. `focus=fist` rendait un `.blend`, un rapport et
   « 0 critere obligatoire en echec » sans avoir touche au poing ;
3. **la vrille etait verrouillee a zero sur les trois articulations** d'un
   doigt, alors que seules la PIP et la DIP sont des charnieres ;
4. **un correctif cable sur une propriete que la pose laisse a zero.** Mesure,
   retenu, cable, verifie sous les 3 mm — et jamais applique.

Le quatrieme est le defaut de signature de ce depot : un champ rempli au
contrat que rien ne lit a l'arrivee.

### La lecon de ce chat, et elle vaut au-dela du rig

Le verificateur etendu, lance sur le fichier que l'ancien jugeait
« 22 reussis / 9 echoues », rend desormais cinq echecs de plus — au chiffre
pres ce que les sondes avaient trouve a la main.

**Le rig n'etait pas moins casse avant. L'instrument ne regardait pas.**

Onze fautes du meme genre ont ete trouvees dans les modules ecrits par agents,
et au moins huit dans mon propre travail. Aucune n'aurait plante : une garde
placee apres une normalisation, une contre-epreuve qui testait IEEE 754, un
`except` qui laissait l'armature en mode edition et faisait mesurer une main
immobile. Toutes auraient rendu un verdict credible.

---

## La baseline du chat 2 — étape B du cahier

Reconstruction complète depuis le commit public, en mode `mesure` :

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend
blender --background --factory-startup --python-exit-code 1 \
  --python rig-main.py -- ./sortie homme g 110 mesure
```

| | |
| --- | --- |
| durée | **53 min** |
| critères réussis | **16** |
| critères échoués | **15** |
| code de sortie | **1 — plantage**, et non le code 2 attendu |
| `.blend` produit | **aucun** |
| rapport JSON | `reports/chat-2/baseline/rapport-rig.L.json` |
| journal complet | `reports/chat-2/baseline/journal-generation.txt` |

**Ces chiffres ne se comparent pas au « 22 réussis / 9 échoués » du
vérificateur.** Ce sont deux jeux de critères différents mesurés sur deux
objets différents : `verifier-rig.py` juge le `.blend` de `b17e548`,
`rig-main.py` juge sa propre construction et pose des questions que l'autre ne
pose pas — creux palmaire, ouverture de l'anneau, distinction `Pinch`/`OK`,
compression au poing.

### Pourquoi aucune génération n'avait jamais abouti

```
File "rig-main.py", line 2401, in <module>
KeyError: ''
```

`_gnom.get(g.group, "")` rend la chaîne **vide** pour un groupe de sommets dont
l'index n'est plus dans la table. Ce nom vide traverse ensuite tous les filtres
— il ne finit pas par `_meta`, il n'est pas `DEF_hand` — jusqu'à `_gr[""]`, qui
n'existe pas. Le plantage arrive **après** les rendus et **avant** la
sauvegarde : d'où l'absence de tout `.blend` à jour dans ce dépôt.

Corrigé (`8727990`) aux sept sites de `rig-main.py` et aux trois autres
scripts, où le même défaut était **latent et plus sournois** : là il ne
plantait pas, il pouvait faire élire la chaîne vide comme groupe *dominant*
d'un sommet — lequel sortait alors de toute famille, donc de toute mesure
d'intersection, sans un mot.

---

## Défauts ouverts, mesurés sur la baseline

### Les trois contacts

| pose | distance | orientation | interpénétration |
| --- | ---: | ---: | --- |
| `Hand_Pinch` | **3,19 mm** ✗ | −0,536 ✓ | aucune ✓ |
| `Hand_OK` | **1,04 mm** ✗ | **−0,46** ✗ | aucune ✓ |
| `Hand_Pinky_Thumb` | **2,46 mm** ✗ | **−0,079** ✗ | **213 sommets non comptés** |

Seuils : ≤ 1,00 mm et ≤ −0,50.

### Les poses

`Hand_Fist_75` (779 sommets sur `thumb/index`), `Hand_Point` (440 + 445 + …),
`Hand_Cupped` (1), `Hand_Pinky_Thumb` (127 + …).

### Les transitions — **cinq sur six**

`Neutral→` `Hand_Fist`, `Hand_Point`, **`Hand_OK`**, `Hand_Cupped`,
`Hand_Pinky_Thumb`. Seule `Neutral→Hand_Pinch` est propre.
`Neutral→Hand_OK` ne figurait pas dans la liste transmise par le chat 1.

### Les volumes

- **la paume ne se creuse pas** : gain **1,0 mm** pour **6 mm** exigés ;
- **le poing n'est fermé qu'à 0,6**, et cette valeur vient d'une mesure
  faussée (voir ci-dessous).

### Ce qui passe déjà

Retour exact au repos, `Hand_Neutral`, `Hand_Relaxed`, `Hand_Open`,
`Hand_Spread_Min`, `Hand_Fist`, `Hand_Fist_25`, `Hand_Fist_50`, `Hand_Pinch`,
`Hand_OK` sans auto-intersection ; `Pinch` et `OK` distincts (47,8 mm) ;
anneau du `OK` lisible (20,6 mm) ; transition `Neutral→Hand_Pinch`.

---

## Sept causes corrigées — et le motif qu'elles partagent

Détail complet, avec les chiffres : [`reports/chat-2/01-les-causes.md`](reports/chat-2/01-les-causes.md).

Cinq des sept sont **la même erreur de méthode** :

> un instrument a été corrigé sans que l'espace, la doctrine ou la boucle qui
> l'entourent le soient.

Corriger un instrument crée une dette : tout ce qu'il condamne désormais doit
recevoir de quoi s'en sortir.

| | commit |
| --- | --- |
| le sens de l'écartement est **mesuré**, plus décrété | `9b07ea0` |
| les doigts étrangers au contact peuvent sortir du chemin | `0b8401e` |
| ce qui est obligatoire ne se négocie plus, pour aucun critère | `ee6bd38` |
| les transitions sont **corrigées**, plus seulement mesurées | `4601d97` |
| la chaîne distale des deux pulpes en contact est cherchable | `b412890` |
| l'éclairage rasant entre dans le pipeline | `4a68afc` |
| deux mesures qui ne mesuraient pas ce qu'elles annonçaient | `fa92143` |

**Aucun de ces sept correctifs n'est encore prouvé par la mesure.** Ils sont
argumentés, versés et poussés ; il leur manque une reconstruction qui aboutisse.

---

## Trois affirmations du checkpoint corrigées

1. **Le défaut d'écartement n'était pas sur l'annulaire.** C'est `Spread`
   entier qui était retourné, sur les trois couples voisins. `Hand_Open`
   (`Spread = 1`) était la main la **plus serrée** de la bibliothèque, et
   `Hand_Spread_Min` la plus ouverte : deux poses portaient le nom de leur
   contraire.
2. **Les « 80 paires majeur/annulaire » n'existent pas** sur ce fichier :
   0 traversée aux 21 pas du balayage, 6,84 mm d'écart à `Spread = +1`.
3. **Les totaux publiés étaient faux.** `Hand_Point` vaut **1 528** sommets et
   `Hand_Pinky_Thumb` **1 271**, non 978 et 717. Mêmes poses, mêmes couples,
   verdict inchangé — seuls les totaux étaient recopiés d'une autre addition.

## Deux fautes commises pendant ce chat, corrigées avant livraison

- `_h.get("ecretage", 0.0)` sur une clé nommée `ecretage_pct` : chaque image
  aurait rendu 0 % d'écrêtage et 0° de rasance, et trois critères d'éclairage
  seraient passés **en ne mesurant rien** ;
- le tableau de régression annonçait « 0 » pendant qu'une mesure doublait,
  parce qu'il suivait la lettre du cahier (« une pose *précédemment propre* »).

---

## Outils ajoutés

| outil | ce qu'il répond |
| --- | --- |
| `outils/sonde-ecartement.py` | l'écartement écarte-t-il ? Balayage −1 → +1, éventail **et** traversées, se contre-éprouve avant de conclure |
| `outils/comparer-rapports.py` | tableau de régression ; distingue régression, aggravation chiffrée, correction et absence |
| `outils/playblast-transitions.py` | les six playblasts, rejoués exactement comme le vérificateur les mesure |

Les trois sortent en code non nul quand leur verdict est négatif. Le dernier a
livré **trois bugs** à son premier lancement, dont un qui n'est pas de lui :
**cette build de Blender est compilée sans FFmpeg** et la machine n'a pas de
binaire `ffmpeg`, donc aucun MP4 n'est possible. La sortie est une séquence
PNG plus un lecteur HTML sans codec — 150 images, écrêtage **0,000 %**, et
c'est la première exécution réelle de `atelier/eclairage.py`.

---

## Ce qui reste

1. **une reconstruction qui aboutisse** — c'est le préalable à tout le reste ;
2. volumes : paume creuse, silhouette du poing, effet « saucisse », dômes de
   jointures ;
3. les rendus — l'éclairage est intégré mais **jamais exécuté** ;
4. la main droite — le cahier exige qu'elle dérive d'une gauche *validée* ;
5. les playblasts du rig CORRIGÉ — ceux qui existent viennent de `b17e548` ;
6. revue visuelle argumentée, clone propre.

Reprise : [`handoffs/HANDOFF_CHAT_2_NEXT.md`](handoffs/HANDOFF_CHAT_2_NEXT.md).
