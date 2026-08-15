# Chat 2 — les causes, et ce qu'elles ont en commun

Sept correctifs, chacun sur une cause et non sur un symptôme. Ce document
n'énumère pas des changements : il dit **ce qui était faux, comment on l'a su,
et pourquoi le correctif ne peut pas se contenter d'un nombre retouché**.

---

## Le motif

Cinq des sept sont la **même erreur de méthode**, prise par des bouts
différents :

> un instrument a été corrigé sans que l'espace, la doctrine ou la boucle qui
> l'entourent le soient.

- la sonde d'intersection est passée à 15 couples — mais la recherche de pose
  n'avait d'axes que sur deux doigts ;
- la doctrine « ce qui est obligatoire ne se négocie pas » était écrite en
  toutes lettres — et câblée pour l'interpénétration seulement ;
- les transitions étaient échantillonnées à onze étapes et faisaient échouer la
  construction — et rien ne les corrigeait ;
- le module d'éclairage était mesuré et prouvé — et jamais exécuté ;
- un critère de contact s'appelait « aucune interpénétration » — et ne
  regardait qu'un patch de 5 mm.

Corriger un instrument crée une dette : tout ce qu'il condamne désormais doit
recevoir de quoi s'en sortir. Cette dette n'avait pas été payée.

---

## 1 · Le sens de l'écartement était supposé

`9b07ea0`

**Annoncé :** signe inversé **sur l'annulaire**, et `Spread = 1` ferait se
traverser majeur et annulaire — 80 paires.

**Mesuré**, sur le `.blend` de `b17e548`, balayage de −1 à +1 par pas de 0,1 :

| `Spread` | index/majeur | majeur/annulaire | annulaire/auriculaire |
| ---: | ---: | ---: | ---: |
| −1,0 | 27,51 mm | 23,62 mm | 35,34 mm |
| 0,0 | 17,06 mm | 15,27 mm | 30,10 mm |
| +1,0 | **6,62 mm** | **6,84 mm** | **24,21 mm** |

Ce n'est pas l'annulaire. La suite `ECART` est monotone (+10, +1, −6, −12),
aucun doigt ne double son voisin, et les drivers l'appliquaient au dixième de
degré près. C'est le **sens global** de la rotation autour de la normale de la
paume qui était retourné — et le signe d'une normale construite est arbitraire.

Conséquence visible : `Hand_Open` (`Spread = 1`) était la main la **plus
serrée** de la bibliothèque, `Hand_Spread_Min` la plus ouverte. Deux poses
portaient le nom de leur contraire.

**Réfuté :** aucune traversée à aucun des 21 pas. À `Spread = +1`, majeur et
annulaire restent à 6,84 mm l'un de l'autre.

**Le correctif ne pouvait pas être de retourner `ECART` à la main.** La
phase C mesure déjà `SENS_FLEXION` au lieu de le supposer, pour cette raison
exacte. La phase D mesure donc `SIGNE_ECART` de la même façon : on écarte dans
un sens, on regarde si l'éventail des bouts de doigts s'ouvre, on garde le sens
qui ouvre. Un nombre retourné au jugé sur la gauche serait retombé faux sur la
droite, dont la normale de paume est inversée.

Vérifié par deux instruments séparés — la sonde sur l'ancien fichier, et la
mesure en phase D sur un rig reconstruit : `−ECART` rend 27,44 / 23,75 /
36,26 mm contre 5,78 / 7,54 / 24,68 à `+ECART`.

---

## 2 · Les doigts jugés n'avaient pas de quoi s'écarter

`0b8401e`

```
ATLAS_DEUX_TEMPS  après approche   1,08 mm — 17 traversées
                  après nettoyage  3,19 mm —  0 traversée
```

La recherche **sait** venir à 1,08 mm. Aucune pose propre n'existe à cette
distance dans les axes qu'on lui donne, alors le nettoyeur fait la seule chose
qu'il peut : il recule le pouce, et rend 3,19 mm pour un seuil à 1,00 mm.

Les axes de `PINCH` ne portaient rien sur le majeur, l'annulaire ni
l'auriculaire. Depuis que la sonde compte les 15 couples, ces trois doigts sont
**jugés sans pouvoir bouger**.

La phase de nettoyage reçoit donc des axes de dégagement : **une** liberté par
doigt libre, l'écartement. Dans une vraie main, un doigt évite son voisin
latéralement ; lui donner aussi la flexion serait lui permettre de changer de
geste, et l'optimiseur ouvrirait le poing pour le rendre propre.

---

## 3 · Ce qui est obligatoire s'échangeait quand même

`ee6bd38`

```
Hand_OK   après approche   0,53 mm — 0 traversée
          après nettoyage  1,04 mm — 0 traversée   →  ÉCHEC
```

Le nettoyage **dégrade un contact déjà propre**. Sous 1,00 mm la distance ne
coûtait plus rien, et l'exigence d'anneau — 400 points par millimètre manquant
— est **antagoniste** du contact : écarter le pouce de l'index ouvre l'anneau
et éloigne les pulpes. L'optimiseur a dépensé toute la marge, puis franchi le
seuil de 0,04 mm parce que le millimètre d'anneau gagné valait plus que le
dépassement.

Le score compte désormais les critères **obligatoires violés**, et cette somme
entre dans la barrière : aucune pose qui en viole un ne peut battre une pose
qui les respecte tous. Les termes continus ne servent plus qu'à guider vers eux.

Au passage, les deux seuils étaient écrits en clair à **deux endroits** — dans
le score et dans les `exiger` qui prononcent le verdict. Une recherche qui vise
autre chose que son juge ne peut réussir que par chance. Ils sont nommés une
fois.

---

## 4 · Les transitions étaient mesurées et jamais corrigées

`4601d97`

Quatre des neuf critères en échec sont des transitions. Le croisement des deux
listes le montre :

| | pose | transition |
| --- | :---: | :---: |
| `Hand_Point` | ✗ | ✗ |
| `Hand_Cupped` | ✗ | ✗ |
| `Hand_Pinky_Thumb` | ✗ | ✗ |
| `Hand_Fist_75` | ✗ | — |
| **`Hand_Fist`** | **propre** | **✗** |

Trois sont en aval d'une pose fautive et suivront sa correction. La quatrième a
ses **deux extrémités propres** : le pouce traverse l'index à t = 0,8 et 0,9
puis en ressort. Nettoyer la pose d'arrivée ne pouvait pas l'atteindre.

`nettoyer_transition()` corrige le chemin. L'échantillonnage est adaptatif — on
ne retient que les étapes réellement fautives plus l'arrivée, et on relit le
trajet entier entre deux rondes, parce que corriger une étape peut en salir une
autre. Et **toutes les poses sont remesurées après** : les corrections de
transition s'appliquent aussi à l'arrivée, puisqu'elle est l'étape t = 1,0 du
même trajet.

---

## 5 · Une pulpe qui ne peut pas s'orienter se pose de travers

`b412890`

Le diagnostic générique ajouté en `0b8401e` a **réfuté l'hypothèse posée dans ce
même commit** :

```
ATLAS_OU_CA_TRAVERSE_APPROCHE index/thumb
    DEF_index_03.L → DEF_thumb_02.L : 12
    DEF_thumb_02.L → DEF_index_03.L :  5
```

Les 17 traversées sont entre les **deux phalanges distales du contact** — les
deux pulpes qui se pincent. Aucun doigt libre n'y est pour quoi que ce soit.

La cause se lit en comparant les deux recherches : `ANNEAU` porte
`CTRL_index_02`, `PINCH` n'a que `CTRL_index_01`, aucune n'a `CTRL_index_03`.
Et `Hand_OK`, qui a une articulation de plus, approche **propre** à 0,53 mm là
où `Hand_Pinch` approche à 1,08 mm avec 17 traversées.

La chaîne distale des **deux** doigts en contact est désormais cherchable, dès
l'approche — un contact formé de travers ne se redresse pas au nettoyage. Pas
d'écartement : au-delà de la métacarpo-phalangienne, une interphalangienne est
une charnière, et la phase E y verrouille le Z.

Le **poing en est explicitement exclu** : sa proximité pouce/index n'est jugée
par aucun `exiger` — c'est un sous-produit de l'enroulement — alors que sa
silhouette est un critère. Ouvrir l'index de 30° pour améliorer un non-critère
troquerait le poing contre rien.

---

## 6 · Un critère vert qui mentait

`fa92143`

```
ATLAS_DEUX_TEMPS  Hand_Pinky_Thumb  traversees_apres_nettoyage: 213
ATLAS_CRITERE OK  Hand_Pinky_Thumb · aucune interpénétration · mesuré 0
```

Le critère ne lisait que `penetration` : les sommets traversants **dans le
patch des deux pulpes**. 213 sommets se traversent ailleurs dans la main, et le
critère est vert. C'est la cécité que tout le chat 1 a corrigée, survivante à un
endroit qu'on n'avait pas regardé. Les deux comptes sont désormais exigés, et
tous deux affichés.

---

## 7 · « Sans le pouce » ne l'était pas — et le poing en payait le prix

`fa92143`

`regler(Fist=f)` ne bouge que les quatre doigts : le pouce a ses commandes
propres depuis la correction de l'écrasement. Il reste donc **au repos, en
travers du chemin**, et les quatre doigts se referment dessus. La mesure
comptait ces chocs et les attribuait à la fermeture — à 0,7 elle rendait
2 429 traversées dont **1 272 sur le couple `thumb/index`**, dans un relevé
intitulé « mesuré sans le pouce ».

La conséquence n'est pas cosmétique : `FERMETURE` retombait à **0,6**. Le poing
livré n'était fermé qu'à 60 %, alors que le cahier exige « une silhouette de
vrai poing, pas une boucle de cylindres ». Un poing bridé par un pouce qu'on
n'avait pas posé.

`intersections()` accepte désormais une restriction de familles, et la question
posée aux quatre doigts ne porte plus que sur eux — ce qu'elle a toujours
prétendu être.

---

## Deux fautes que j'ai commises et corrigées avant de livrer

Elles appartiennent au même motif, et les taire serait pire que les avoir
faites.

**Un zéro qui se serait lu comme une mesure.** Mon intégration de l'éclairage
lisait `_h.get("ecretage", 0.0)` là où la clé s'appelle `ecretage_pct`. Chaque
image aurait rendu **0 % d'écrêtage et 0° de rasance**, et les trois nouveaux
critères seraient passés **en ne mesurant rien**. Les clés sont maintenant
indexées directement : une clé absente lève au lieu de valoir zéro.

**Un outil qui m'a rassuré à tort.** Mon tableau de régression annonçait
« RÉGRESSIONS : 0 » pendant que `Hand_OK` passait de 1,04 à 2,29 mm sous
l'effet du correctif d'écartement. Sa définition était celle du cahier au mot
près — « une pose *précédemment propre* » — donc un critère déjà en échec
pouvait doubler sans rien déclencher. Il liste désormais à part les
**aggravations chiffrées**, et il lit la direction dans le seuil imprimé
(« ≤ 1,00 mm » dit que descendre est un progrès) au lieu de la supposer.

---

## Une erreur de recopie dans le checkpoint

`STATUS.md` et `audit/AUDIT_PACKET_HANDS.md` chiffrent `Hand_Point` à
**978 sommets** et `Hand_Pinky_Thumb` à **717**. Le vérificateur, relancé sur le
même fichier depuis le commit public, rend **1 528** et **1 271** en additionnant
les couples. Mêmes poses, mêmes couples, verdict inchangé — seuls les totaux
publiés étaient faux.
