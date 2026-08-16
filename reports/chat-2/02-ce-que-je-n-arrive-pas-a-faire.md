# Chat 2 — ce que j'ai fait, et ce que je n'arrive pas à faire

Rapport honnête, écrit pendant que la dernière reconstruction tourne encore.
Chaque chiffre vient d'une mesure du dépôt, pas d'une estimation.

- dépôt : `OrphicDev/atlas-hand-rig`
- branche : `hands/chat-2-photoreal-v2`
- départ : `e2d4b1c9e05949531d9348d68367c225b2169872`
- 20 commits publics au moment de cette rédaction

---

## En une page

**Statut : NON-VALIDE.** Le rig n'est pas livrable et ne l'était pas au départ.

Ce chat a fait une chose que le précédent n'avait pas faite : il a **mesuré les
instruments avant de croire leurs verdicts**. Trois sondes du dépôt validaient
des choses fausses, et une quatrième — le plantage — empêchait depuis toujours
qu'un seul fichier sorte de la chaîne. Tout cela est trouvé, corrigé et public.

Mais **trois défauts anatomiques résistent**, et je dois dire clairement que je
ne sais pas les résoudre dans l'état actuel du maillage et de l'architecture.
Ils sont listés plus bas avec ce que j'ai essayé et ce qui reste à tenter.

| | |
| --- | --- |
| causes trouvées et corrigées | **9** |
| **prouvées par la mesure** | **4** |
| corrigées, preuve en cours | 3 |
| **diagnostiquées, non corrigées** | **2** |
| défauts trouvés dans mes propres sondes | **4** |
| ce que je n'arrive pas à faire | **3 anatomiques + 4 de livraison** |

---

## 1. Ce que j'ai fait, et qui est prouvé

### `Hand_Pinch` — renversé

```
baseline    après approche 1,08 mm — 17 traversées → nettoyage 3,19 mm  ÉCHEC
maintenant  après approche 1,08 mm — 17 traversées → nettoyage 0,79 mm  ✓ 3/3
```

Trois critères sur trois, dont l'interpénétration mesurée **sur la main
entière** et plus sur un patch de 5 mm. C'était le contact le plus dégradé du
lot ; il est le plus propre.

**Comment.** Le diagnostic générique que j'ai ajouté a montré que les
17 traversées étaient entre les **deux phalanges distales du contact
lui-même** — pas entre les doigts libres, contrairement à ce que j'avais
supposé et écrit. `PINCH` ne pouvait piloter que `CTRL_index_01` : l'index ne
pouvait pas présenter sa pulpe à plat, il l'enfonçait par la tranche. La chaîne
distale des deux doigts en contact est désormais cherchable.

### L'écartement — mesuré au lieu d'être décrété

Monter `Spread` **refermait** l'éventail sur les trois couples voisins :
index/majeur de 17,06 à **6,62 mm**. `Hand_Open` était la main la plus *serrée*
de la bibliothèque et `Hand_Spread_Min` la plus ouverte — deux poses portaient
le nom de leur contraire.

Ce n'était pas l'annulaire, comme l'annonçait le checkpoint : `ECART` est
monotone et les drivers l'appliquaient au dixième de degré. C'était le **sens
global** de la rotation autour d'une normale de paume dont le signe est
arbitraire. La phase D le mesure maintenant, comme la phase C mesure déjà le
sens de la flexion.

**Réfuté au passage :** les « 80 paires majeur/annulaire à `Spread = 1` »
n'existent pas — 0 traversée aux 21 pas du balayage.

### Le plantage qui cachait tout

```
File "rig-main.py", line 2401 — KeyError: ''
53 min de calcul, code 1, aucun .blend
```

`_gnom.get(g.group, "")` rendait la chaîne **vide** pour un groupe de sommets
inconnu, et ce nom vide traversait tous les filtres. Le plantage arrive
**après** les rendus et **avant** la sauvegarde : voilà pourquoi le dépôt ne
contient aucun `.blend` à jour et pourquoi le chat 1 notait « le code de sortie
d'une génération complète n'a jamais été relevé ». Trois tentatives, aucune
menée à terme — la cause n'avait jamais été cherchée.

Le même défaut était **latent** dans les trois autres scripts, où il ne
plantait pas : il pouvait faire élire la chaîne vide comme groupe *dominant*
d'un sommet, lequel sortait alors de toute famille et de toute mesure
d'intersection, sans un mot.

### Deux critères qui mentaient

- **`aucune interpénétration`** ne regardait qu'un patch de 5 mm autour des
  pulpes : `Hand_Pinky_Thumb` était **vert avec 213 sommets traversants** dans
  la main ;
- la fermeture du poing était mesurée « sans le pouce » alors que le pouce
  restait **au repos en travers du chemin** — 1 272 traversées `thumb/index`
  comptées comme une faute des quatre doigts.

### Les playblasts

Le paquet d'audit portait « Transition videos: AUCUNE » depuis le chat 1.
Les six existent : **150 images, écrêtage 0,000 %**, première exécution réelle
de `atelier/eclairage.py`. Ils viennent de l'ancien `.blend` et le disent sur
leur première ligne.

---

## 2. CE QUE JE N'ARRIVE PAS À FAIRE

### 2.1 · `Hand_Pinky_Thumb` — le pouce contre l'auriculaire

**C'est le défaut le plus ancien du projet et je ne le résous pas.**

```
baseline    approche 0,10 mm — 823 traversées → nettoyage 2,46 mm — 213 restantes
maintenant  approche 0,10 mm — 823 traversées → nettoyage 2,66 mm — 211 restantes
```

Mes quatre correctifs ne l'ont pas bougé : **2,46 → 2,66 mm**, 213 → 211
traversées. La seule chose qui a changé, c'est qu'il ne peut plus se déclarer
propre : le critère honnête affiche désormais les 211.

**Ce qui est établi :** la recherche atteint **0,10 mm** — la pose existe
géométriquement. C'est le *nettoyage* qui n'y arrive pas : aucune configuration
accessible ne met les deux pulpes en contact sans que la chair se traverse
ailleurs.

**Ce que le chat 1 avait déjà essayé et qui est documenté** : élargir la
recherche (plafonne à 45 sommets), chercher en deux temps (plafonne à 26), un
lissage correctif (gains **négatifs**, retiré).

**Ce que j'ai ajouté et qui n'a pas suffi** : un axe de dégagement sur
l'annulaire, la chaîne distale de l'auriculaire et du pouce, la barrière
lexicographique.

**Ma lecture, et elle n'est pas prouvée :** c'est un problème de **volume**,
pas de pose. Pour que le pouce traverse la paume et rejoigne l'auriculaire, il
faut que la chair de l'éminence thénar et celle de la base de l'index cèdent
l'une devant l'autre. Un rig d'os ne peut pas faire ça — il faudrait des
**correctifs dépendants de la pose** sur ces deux masses, ce que le cahier
range en phase G et que le chat 1 avait retiré parce qu'il masquait de mauvais
poids plutôt que de les corriger.

**Ce qu'il faudrait tenter, dans cet ordre :** vérifier d'abord les poids du
thénar (le cahier l'exige : poids avant shape keys), puis, seulement s'ils sont
sains, des correctifs pilotés par `Thumb_Opposition`.

### 2.2 · `Hand_OK` — deux exigences inconciliables

```
baseline    approche 0,53 mm — 0 traversée → nettoyage 1,04 mm   ÉCHEC de 0,04
maintenant  approche 0,87 mm — 0 traversée → nettoyage 2,43 mm   ÉCHEC
```

**Mon correctif l'a aggravé** : 1,04 → 2,43 mm. Mon propre outil de régression
le signale comme une aggravation chiffrée.

J'avais diagnostiqué que le nettoyage « achetait de l'anneau avec de la
distance », et j'ai rendu les critères obligatoires lexicographiques pour
l'interdire. **Ça n'a pas marché, et je comprends maintenant pourquoi :** les
deux exigences sont **inconciliables dans cet espace de recherche**. Ouvrir
l'anneau à 16 mm et toucher à 1 mm ne peuvent pas être satisfaits ensemble ;
les deux états violent donc un critère obligatoire, la barrière ne départage
plus rien, et ce sont les termes continus qui tranchent — exactement ce que je
croyais avoir supprimé.

L'orientation, elle, est corrigée : **−0,46 → −0,542**, le critère passe.

**Ce qu'il faudrait trancher, et ce n'est pas à moi de le faire :** le seuil de
16 mm d'ouverture d'anneau est-il juste ? Un « OK » réel a un anneau plus petit
que ça quand les pulpes se touchent vraiment. Soit le seuil descend et il faut
le justifier, soit l'index doit pouvoir s'enrouler davantage — et cela demande
de rouvrir ses butées, ce qui est une décision anatomique.

### 2.3 · Le poing ne peut pas se fermer au-delà de 60 %

**Et je me suis trompé sur la cause.** J'avais affirmé qu'il était « bridé par
un pouce qu'on n'avait pas posé ». La mesure honnête dit autre chose :

```
Fist 0.6 : quatre doigts seuls     1     avec le pouce au repos     1
Fist 0.7 : quatre doigts seuls   820     avec le pouce au repos  2429
Fist 1.0 : quatre doigts seuls  1059     avec le pouce au repos  2466
```

Le pouce gonflait bien le compte d'un facteur trois — ça, c'était juste. Mais
**les quatre doigts seuls se traversent déjà 820 fois à 0,7**. Ma correction a
rendu la mesure honnête ; elle n'a pas libéré le poing.

**Et j'ai découvert pire en le vérifiant :** ce 0,6 n'est même pas mesuré.

```python
FERMETURE = max([f for f, v in _diag_poing.items() if v["total"] == 0] or [0.6])
```

Aucun niveau n'est propre — 0,6 en compte déjà 1 — donc la liste est vide et le
code retombe sur sa **valeur de repli**. Le « poing réaliste mesuré » du dépôt
est une constante écrite en dur qui n'a jamais été choisie par une mesure.

**Ce que ça veut dire :** ce maillage, avec cette densité et ces poids, ne peut
pas fermer un poing. Ce n'est pas un réglage à forcer. Il faudrait soit des
correctifs de volume aux jointures, soit admettre que la fermeture réaliste de
ce maillage est 0,6 et **le dire dans la livraison** au lieu de le laisser
passer pour un choix.

### 2.4 · Le creusement de la paume — diagnostiqué, pas corrigé

Je l'ai entièrement mesuré et je n'ai **pas** engagé la correction : elle
demande de toucher aux butées anatomiques, et ma fenêtre de contexte était trop
entamée pour commencer ça proprement.

```
Cup 0 → 1   grandeur du dépôt   21,00 → 21,98 mm   (+0,98)  ← annonce un progrès
            flèche de l'arc     29,99 → 19,10 mm   (−10,89) ← l'arc S'APLATIT
            largeur de paume    71,99 → 86,03 mm   (+14,04) ← la paume S'ÉLARGIT
            pouce ↔ auriculaire 102,27 → 99,13 → 101,39
```

**Creuser la paume l'élargit.** Le cerclage rouge de Sacha — les deux têtes
métacarpiennes qui se rapprochent, l'origine de tout ce tutoriel — n'est pas
obtenu : 3,1 mm sur 102, et ça repart en arrière après `Cup = 0,5`.

Drivers tus, axe par axe :

```
axe  angle   Δlargeur   Δarc   Δpouce-auriculaire
  0    +20     +6,20   −8,88        −8,36     ← LE SENS ACTUEL DE CUP
  0    −20     +1,42   +8,00        +5,02
  1    ±20      0,00     ∓2          0,00     ← CUP_AXIAL ne sert à RIEN
  2    −20    −13,19   −0,19       −10,35     ← piloté par PERSONNE
```

Deux causes : `CUP` pilote l'axe 0 **dans le sens qui aplatit**, et l'axe qui
fait converger les métacarpiens n'est piloté par rien.

**L'obstacle qui attend :** la phase E borne l'axe Z des métacarpiens à **±8°**,
ce qui écrêterait la convergence à moins de la moitié des 13 mm mesurés. Cette
butée est aussi arbitraire que le reste et doit être **mesurée**, pas relevée
d'un cran jusqu'à ce que le chiffre passe.

---

## 3. Ce que je n'ai pas pu produire

| livrable | pourquoi |
| --- | --- |
| **un `.blend` à jour** | la chaîne plantait ; corrigé, la reconstruction qui doit le produire tourne au moment où j'écris |
| **les rendus** | l'éclairage est intégré au pipeline mais toutes les exécutions ont tourné en mode `mesure` — ils viennent après un `.blend` valide |
| **des MP4** | **impossible dans cet environnement.** Cette build de Blender est compilée sans FFmpeg — son énumération de formats ne contient aucun conteneur vidéo — et la machine n'a pas de binaire `ffmpeg`. J'ai livré des séquences PNG + un lecteur HTML sans codec plutôt que d'installer un binaire sans accord |
| **la main droite** | le cahier exige qu'elle dérive d'une gauche **validée**, qui ne l'est pas |
| **la revue visuelle 8/10** | il n'existe aucun rendu produit par ces scripts. Noter les images de `b17e548` en les faisant passer pour le travail en cours serait un mensonge |
| **le clone propre complet** | le clone reproduit le dépôt (manifeste 275/275) mais pas encore les `.blend` et rendus, qui n'existent pas |

---

## 4. Les quatre fautes que j'ai commises

Je les écris parce qu'elles appartiennent au même motif que celles du dépôt, et
que trois d'entre elles auraient produit des chiffres crédibles et faux.

1. **Un `.get()` par défaut sur une mesure.** J'ai lu `_h.get("ecretage", 0.0)`
   là où la clé s'appelle `ecretage_pct`. Chaque image aurait rendu **0 %
   d'écrêtage et 0° de rasance**, et trois critères d'éclairage seraient passés
   **en ne mesurant rien**.
2. **Un outil qui m'a rassuré à tort.** Mon tableau de régression annonçait
   « RÉGRESSIONS : 0 » pendant que `Hand_OK` passait de 1,04 à 2,29 mm. Sa
   définition suivait le cahier au mot près — « une pose *précédemment
   propre* » — donc un critère déjà en échec pouvait doubler sans rien
   déclencher.
3. **Deux grandeurs qui rendaient des constantes.** Je lisais `head_local`, la
   position de **repos** de l'os. 71,99 mm et 50,30 mm à tous les pas. J'aurais
   pu lire cette constance comme un fait.
4. **Le pire — un tableau de zéros parfaitement cohérent.** J'ai posé des
   rotations à la main sur des axes **pilotés par driver**, obtenu `+0,00`
   partout, et failli conclure « ces axes ne creusent pas ». Le driver effaçait
   ma valeur avant chaque mesure ; seul l'axe non piloté répondait. Le handoff
   du chat 1 prévient de ce piège **en toutes lettres, page 2**. J'y suis tombé
   quand même.

Et une hypothèse énoncée avec assurance puis réfutée par ma propre sonde : je
croyais que l'éminence thénar tenait le maximum du creux palmaire et masquait
tout. Avec ou sans le pouce, la grandeur rend le même chiffre au centième.

---

## 5. Ce que ce chantier m'a appris, et qui vaut au-delà de lui

**Corriger un instrument crée une dette.** Le chat 1 a corrigé la sonde
d'intersection — de 5 couples à 15, dans les deux sens — et s'est arrêté là.
Cinq des neuf fautes que j'ai trouvées sont ce que cette sonde condamnait
désormais sans que rien n'ait été rouvert pour s'en sortir : la recherche
n'avait d'axes que sur deux doigts, la doctrine « l'obligatoire ne se négocie
pas » n'était câblée que pour un critère sur quatre, les transitions étaient
mesurées sans être corrigées, le module de lumière était prouvé sans être
branché.

**Un zéro cohérent est le mensonge le plus difficile à voir.** Un instrument
qui rend zéro parce qu'il ne mesure rien est indiscernable d'un instrument qui
rend zéro parce que tout va bien — sauf si on l'a construit pour pouvoir
échouer. Toutes les sondes de ce chat se contre-éprouvent avant de conclure, et
refusent de rendre un verdict si leur contre-épreuve échoue. C'est la seule
chose qui a marché à chaque fois.

---

## 6. Les commandes, pour tout reproduire

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend

# reconstruire — 45 min à 1 h seule sur la machine
blender --background --factory-startup --python-exit-code 1 \
  --python rig-main.py -- ./sortie homme g 110 mesure

# juger un .blend sans le reconstruire — aucun téléchargement
blender --background --factory-startup --python-exit-code 1 \
  --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend

# l'écartement écarte-t-il ?
blender --background --factory-startup --python-exit-code 1 \
  --python outils/sonde-ecartement.py -- FICHIER.blend sortie.json

# la paume se creuse-t-elle, et quel axe la creuserait ?
blender --background --factory-startup --python-exit-code 1 \
  --python outils/sonde-creux.py -- FICHIER.blend sortie.json

# les six playblasts
blender --background --factory-startup --python-exit-code 1 \
  --python outils/playblast-transitions.py -- FICHIER.blend videos/

# le tableau de régression
python3 outils/comparer-rapports.py base=journal1.txt apres=journal2.txt
```

Les cinq outils sortent en **code non nul** quand leur verdict est négatif.

Reprise détaillée : [`handoffs/HANDOFF_CHAT_2_NEXT.md`](../../handoffs/HANDOFF_CHAT_2_NEXT.md).
