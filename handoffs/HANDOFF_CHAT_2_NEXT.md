# HANDOFF — chat 2 → suite (mains)

## Ce que tu reprends

| | |
| --- | --- |
| dépôt | `OrphicDev/atlas-hand-rig` |
| **branche** | `hands/chat-2-photoreal-v2` (publique) |
| commit de départ du chat 2 | `e2d4b1c9e05949531d9348d68367c225b2169872` |
| base auditée, intacte | `b17e54806f942736e47c4dcfd477a91b7fd6f262` (`main`) |
| Blender | **5.1.2** (`ec6e62d40fa9`, 2026-05-19), aucun add-on |
| système | macOS 26.5, Apple Silicon, 10 cœurs, 16 Go |
| maillage source | `human-base-meshes-bundle-v1.4.1`, 49 420 489 octets, SHA-256 `3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137` |

`main` et `wip/chat-1-honest-probe` n'ont pas bougé. Aucun force push, aucun
commit audité réécrit, aucun tag.

---

## Ce que le chat 2 a établi, et qui ne se remesure pas

Sept causes, chacune corrigée à sa racine. Le détail, avec les chiffres et la
façon dont ils ont été obtenus, est dans
[`reports/chat-2/01-les-causes.md`](../reports/chat-2/01-les-causes.md).

**Le motif, parce qu'il vaut plus que la liste :** cinq des sept sont la même
erreur de méthode. *Un instrument a été corrigé sans que l'espace, la doctrine
ou la boucle qui l'entourent le soient.* Corriger un instrument crée une dette :
tout ce qu'il condamne désormais doit recevoir de quoi s'en sortir. Si tu
corriges une sonde, cherche immédiatement ce qu'elle vient de rendre
impossible.

### Trois affirmations du checkpoint corrigées

1. **Le défaut d'écartement n'était pas sur l'annulaire.** C'est `Spread`
   entier qui était retourné, sur les trois couples voisins. `Hand_Open`
   (`Spread = 1`) était la main la plus SERRÉE de la bibliothèque.
2. **Les « 80 paires majeur/annulaire » n'existent pas** sur ce fichier :
   0 traversée aux 21 pas du balayage, et 6,84 mm d'écart à `Spread = +1`.
3. **Les totaux de `STATUS.md` étaient faux** : `Hand_Point` vaut 1 528 sommets
   et `Hand_Pinky_Thumb` 1 271, non 978 et 717. Mêmes couples, mêmes poses,
   verdict inchangé.

### Deux critères qui mentaient, et qu'il ne faut jamais laisser revenir

- `{pose} · aucune interpénétration` ne lisait que le patch des deux pulpes :
  `Hand_Pinky_Thumb` était vert avec **213 sommets traversants** dans la main ;
- la fermeture du poing était mesurée « sans le pouce » alors que le pouce
  restait **au repos en travers du chemin** — 1 272 traversées `thumb/index`
  comptées comme une faute des quatre doigts. `FERMETURE` retombait à **0,6** :
  le poing livré n'était fermé qu'à 60 %.

### Deux fautes que j'ai commises, corrigées avant livraison

- `_h.get("ecretage", 0.0)` sur une clé nommée `ecretage_pct` : chaque image
  aurait rendu 0 % d'écrêtage et 0° de rasance, et trois critères seraient
  passés **en ne mesurant rien** ;
- mon tableau de régression annonçait « 0 » pendant qu'une mesure doublait,
  parce qu'il suivait la lettre du cahier (« une pose *précédemment propre* »).

---

## Les outils ajoutés

| outil | ce qu'il répond |
| --- | --- |
| `outils/sonde-ecartement.py` | l'écartement écarte-t-il ? Balayage −1 → +1, éventail ET traversées, se contre-éprouve avant de conclure |
| `outils/comparer-rapports.py` | tableau de régression ; distingue régression, aggravation chiffrée, correction et absence |
| `outils/playblast-transitions.py` | les six playblasts, rejoués **exactement** comme le vérificateur les mesure |

Les trois sortent en code non nul quand leur verdict est négatif.

---

## Commandes exactes

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend
blender --background --factory-startup --python-exit-code 1 \
  --python rig-main.py -- ./sortie homme g 110 mesure
```

`mesure` évite les rendus. **Compter 1 h 30 à 2 h** par reconstruction ; les
recherches de contact et le nettoyage des transitions dominent. `--python-exit-code 1`
n'est pas décoratif : sans lui les scripts sortent en code 0 après un plantage.

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
blender --background --factory-startup --python-exit-code 1 \
  --python outils/sonde-ecartement.py -- FICHIER.blend sortie.json
python3 outils/comparer-rapports.py base=journal1.txt apres=journal2.txt
```

Le portillon (`atelier/portillon.py`) refuse de construire sans une enquête
complète dans `enquetes/humain-rig-main.md` — sections obligatoires, deux
vérifications, deux réfutations dont un **invariant**.

---

## Ce qui reste

### 0. LA PAUME NE SE CREUSE PAS — elle fait l'inverse, et c'est diagnostiqué

C'est le chantier le plus important qui reste, et il n'était dans aucune liste.
Tout est mesuré ; il ne reste qu'à corriger. **Ne recommence pas l'enquête.**

Mesuré par `outils/sonde-creux.py` sur le rig de `b17e548`, `Cup` de 0 à 1 :

```
grandeur du dépôt   21,00 → 21,98 mm   (+0,98)   ← annonce un progrès
flèche de l'arc     29,99 → 19,10 mm   (−10,89)  ← l'arc S'APLATIT
largeur de paume    71,99 → 86,03 mm   (+14,04)  ← la paume S'ÉLARGIT
pouce ↔ auriculaire 102,27 → 99,13 → 101,39      ← 3 mm, puis ça repart
```

**Creuser la paume l'élargit.** Et `creux_palmaire()` lit un progrès parce
qu'il prend le maximum de profondeur sous un plan **figé à la pose de repos** :
un splay l'augmente aussi. Il ne se trompe pas d'amplitude, il se trompe de
**sens sur le phénomène**. Le cerclage rouge de Sacha — les deux têtes
métacarpiennes qui se rapprochent — n'est donc pas obtenu.

Puis, **drivers tus** (indispensable, voir piège 6), ring et pinky tournés de
±20° sur chaque axe local :

```
axe  angle   Δlargeur   Δarc   Δpouce-auriculaire
  0    +20     +6,20   −8,88        −8,36     ← LE SENS ACTUEL DE CUP
  0    −20     +1,42   +8,00        +5,02
  1    ±20      0,00     ∓2          0,00     ← CUP_AXIAL ne sert à RIEN
  2    +20    +12,94   +0,32       +10,03
  2    −20    −13,19   −0,19       −10,35
```

**Deux causes, aucune connue avant :**

1. `CUP` pilote l'axe 0 **dans le sens qui aplatit l'arc**. C'est la faute de
   `Spread` à l'identique — un sens de rotation déduit d'une convention d'axes
   au lieu d'être mesuré ;
2. **l'axe qui fait converger les métacarpiens n'est piloté par rien.** L'axe 2
   est le seul qui resserre la paume, et `CUP` ne le touche jamais.

**Le correctif, et sa forme est imposée :** mesurer à la construction, comme la
phase D mesure déjà `SIGNE_ECART`, quel couple (axe, signe) creuse l'arc et
quel couple fait converger les têtes — puis piloter **les deux**. Ne retouche
ni `CUP` ni `CUP_AXIAL` au jugé : un signe corrigé à la main sur la gauche
retomberait faux sur la droite.

**Un obstacle t'attend et il est réel :** la phase E borne l'axe Z des
métacarpiens à **±8°**, ce qui écrêterait la convergence à moins de 6 mm des
13 mesurés. Cette butée est aussi arbitraire que le reste — les articulations
carpo-métacarpiennes des 4ᵉ et 5ᵉ rayons ont une mobilité réelle. Elle doit
être **mesurée**, pas relevée d'un cran jusqu'à ce que le chiffre passe.

### 1. Le reste de P1 — volumes et réalisme

Effet « saucisse », dômes de jointures absents au dos du poing,
thénar/hypothénar. Poids d'abord, correctifs pilotés ensuite — jamais
l'inverse.
2. **P1 — les rendus.** L'éclairage rasant est intégré (`4a68afc`) mais **jamais
   exécuté** : toutes les reconstructions du chat 2 ont tourné en mode `mesure`.
   Six vues par pose désormais (paume-A/B, dos-A/B, pouce, auriculaire) et trois
   critères nouveaux : écrêtage ≤ 2 %, key à 75° ± 5, amplitude de luminance
   ≥ 0,10. Sacha a tranché : **tout en Cycles**.
3. **P1 — main droite.** `rig-main.py` la construit déjà (`… homme d 110`) par
   la même chaîne mesurée : pas de miroir à échelle négative, donc pas d'échelle
   résiduelle à nettoyer. **Mais** les poses de contact sont trouvées par
   recherche : deux recherches indépendantes rendraient deux mains différentes
   et la tolérance de symétrie de 1 mm serait perdue d'avance. Il faut
   **transférer** les poses de la gauche, pas les rechercher — et déterminer par
   la mesure, non par supposition, quels axes locaux changent de signe.
4. **Playblasts** — l'outil existe, il n'a jamais été exécuté.
5. **Revue visuelle argumentée ≥ 8/10.** Sacha a tranché : **c'est moi qui note
   et j'argumente**.
6. **Clone propre** reproduisant `.blend`, rapports, images et vidéos.

## Décisions de Sacha à ne pas redemander (16 août 2026)

- pousser `hands/chat-2-photoreal-v2` au fil de l'eau — fait ;
- aller jusqu'au bout, quel que soit le temps ;
- c'est moi qui note la revue visuelle, et je l'argumente ;
- tous les rendus en Cycles ;
- **ne plus poser de questions jusqu'au mardi 18 août.**

## Pièges déjà payés — ne pas les repayer

1. **Les drivers ne s'évaluent pas en mode fond** sans changement d'image.
   Après toute pose : `rig.update_tag()`, `scene.frame_set(...)`,
   `view_layer.update()`. Sans ça on mesure une main immobile — et une main
   immobile revient toujours exactement à sa pose de repos, donc elle passe.
2. **L'évaluateur d'expressions n'accepte que des droites.** `min`, `max` et le
   produit de deux variables échouent **en silence** (`is_valid = false`).
3. **Une pose finale propre ne prouve rien** : `Neutral→Hand_Fist` a ses deux
   extrémités propres et traverse à t = 0,8.
4. **Ne jamais mettre de valeur par défaut sur une lecture de mesure.** Un zéro
   se lit comme une mesure.
5. **Le seuil d'acceptation ne doit pas servir de zone franche** à l'optimiseur :
   il dépense la marge jusqu'au dernier centième et la franchit.
6. **UN DRIVER RÉÉCRIT SA VOIE : il faut le taire pour sonder.** Le piège le
   plus coûteux de ce chat, et il est déjà écrit page 2 du handoff précédent —
   j'y suis tombé quand même. En posant une rotation à la main sur un axe
   piloté par `Cup`, j'ai obtenu **+0,00 sur toutes les grandeurs** et j'ai
   failli en conclure « cet axe ne creuse pas ». Le driver effaçait ma valeur
   avant chaque mesure. Seul l'axe non piloté répondait, ce qui rendait le
   tableau **parfaitement cohérent et parfaitement faux**.

   Mets `driver.mute = True` le temps du test, rétablis après, et **fais
   échouer la sonde si taire n'a rien changé** — sinon tu ne saurais pas que tu
   n'atteins pas l'os que tu prétends tourner.

   Règle générale, et elle vaut au-delà de ce dépôt : *un zéro cohérent est le
   mensonge le plus difficile à voir.* Une sonde doit pouvoir échouer.

---

# CHAT 3 — CE QUI A CHANGE

Le cahier du chat 3 est **entierement ecrit en code**. Ce qui reste est de la
mesure, pas de l'ecriture.

## Ce qui est acquis et prouve

| | mesure |
| --- | --- |
| `Cup` voute et resserre | arc **+6,71 mm**, largeur **−10,79**, 7 criteres sur 7 |
| le cerclage rouge | **−4,94 mm** (etait −0,88) |
| poids repeints | **0 sommet** entre rayons non voisins (etait 12 329 ambigus) |
| os correctifs | crees, repos deplace de **0,00013 mm** |
| la chaine va au bout | un `.blend` sort enfin |

## Ce qui resiste, et ce que je sais de chacun

- **`Hand_Pinky_Thumb`** — la pose EXISTE (0,10 mm a l'approche), le nettoyage
  ne la tient pas. Les os correctifs sont en place mais leur amplitude n'est
  pas encore cherchee : c'est le §7.4, et c'est la prochaine marche.
- **`Hand_OK`** — l'anneau et le contact sont antagonistes. La recherche en
  trois etapes est ecrite (§10.3) et jamais encore prouvee. Attention : sur le
  dernier `.blend`, NI le OK NI le Pinch n'ont d'anneau mesurable — le module
  refuse, et ce refus est le resultat.
- **le poing** — 0,6 maximum, les quatre doigts SEULS se traversent 820 fois a
  0,7. `K_DIVERGENCE` est desormais cherche ; s'il ne suffit pas, c'est un
  probleme de volume et non de pose.
- **aucun rendu Cycles** n'a encore ete produit par ces scripts.

## Les pieges que j'ai payes, en plus des cinq du chat 2

6. **Un driver reecrit sa voie.** Sonder un canal pilote sans le taire rend
   +0,00 partout et un tableau parfaitement coherent et parfaitement faux.
7. **Un `except` qui ne rend pas l'etat ne rattrape rien.** Une exception a
   laisse l'armature en mode EDITION ; tout ce qui suivait a mesure une main
   immobile — compression 1,0, zero traversee — sur un poing jamais ferme.
8. **Une origine relevee avant que l'origine soit decidee n'est pas une
   origine.** Le repos capture avant le test A/B de Preserve Volume donnait
   0,0401 mm de derive.
9. **Compter la mauvaise chose.** Mon critere de repeinture punissait le
   melange entre rayons VOISINS, que le cahier declare legitime.
10. **Une tranche a un seul bord fabrique un anneau.** 19 mm de diametre utile
    attribues a un PINCEMENT, parce que le contour n'avait qu'un cote.
11. **Un masque geodesique trop large deplace la paume** au lieu de corriger le
    thenar : 10 896 sommets, soit un cinquieme de la main.

## Les instruments ajoutes

`outils/` : sonde-creux, sonde-poids-main, anneau, revue-visuelle,
matrice-acceptation.
`atelier/` : mesures_paume, correctifs, transitions, jacobienne, miroir.

Cinquante et un refus exerces par les autotests purs. Trois modules ont ete
ecrits par agents PUIS REFUTES par un second agent : onze defauts reels
trouves, dont une garde placee apres une normalisation donc aveugle, et une
contre-epreuve qui testait IEEE 754.

## La regle qui resume tout

Le verificateur etendu, lance sur le fichier que l'ancien jugeait
« 22 reussis / 9 echoues », rend cinq echecs de plus — au chiffre pres ce que
les sondes avaient trouve a la main.

**Le rig n'etait pas moins casse avant. L'instrument ne regardait pas.**
