# Chat 2 — reprise du checkpoint, et le premier fait remesuré

## Le point de départ, vérifié et non supposé

| | |
| --- | --- |
| dépôt | `OrphicDev/atlas-hand-rig` |
| commit repris | `e2d4b1c9e05949531d9348d68367c225b2169872` |
| ce commit est bien | la tête de `origin/wip/chat-1-honest-probe` |
| branche de travail | `hands/chat-2-photoreal-v2` |
| Blender | 5.1.2 (`ec6e62d40fa9`, 2026-05-19) |
| système | macOS 26.5, Apple Silicon, 10 cœurs |

Clone neuf, checkout détaché, puis branche. `git status` propre.

### Le manifeste

`shasum -a 256 -c audit/manifest-sha256.txt` : **109 lignes sur 110 conformes**.
La seule qui échoue est `audit/manifest-sha256.txt` **lui-même** — un fichier ne
peut pas contenir son propre SHA-256. Les 109 fichiers de contenu sont intacts,
et le manifeste couvre bien la totalité des 110 fichiers suivis par git.

### Le smoke test du vérificateur, reproduit

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

**Code de sortie 2. 22 critères passent, 9 échouent.** Exactement ce que le
checkpoint annonce. Journal complet : `verifier-e2d4b1c-ancien-blend.txt`.
Durée : 1 min 07 s.

#### Une correction de comptage, sans conséquence sur le verdict

`STATUS.md` et le paquet d'audit chiffrent les poses fautives à
« `Hand_Point` 978 sommets, `Hand_Pinky_Thumb` 717 ». La sortie du vérificateur
donne, en additionnant les couples : **`Hand_Point` 1 528** et
**`Hand_Pinky_Thumb` 1 271**. Les couples et les poses en échec sont identiques,
seuls les totaux publiés diffèrent — ils avaient été recopiés d'une autre
addition. Le verdict (9 échecs, code 2) est inchangé.

### Le maillage source

| | |
| --- | --- |
| fichier | `human_base_meshes_bundle.blend` |
| version | `human-base-meshes-bundle-v1.4.1` (Blender Studio, CC0) |
| taille | 49 420 489 octets |
| SHA-256 | `3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137` |

Le dépôt ne documentait aucune empreinte pour cet asset : elle est inscrite ici.

---

## Le signalement de l'écartement : reproduit dans sa cause, réfuté dans sa forme

Le checkpoint transmet ceci, en le marquant « non confirmé par le pipeline » :

> `Spread = 1` ferait se traverser **majeur et annulaire, 80 paires** —
> l'écartement rapprocherait au lieu de séparer. Signe ou axe probablement
> inversé **sur l'annulaire**.

### L'instrument

`outils/sonde-ecartement.py` balaye `Spread` de −1 à +1 par pas de 0,1 et
mesure, à chaque pas, deux grandeurs distinctes :

1. **les traversées**, avec la machinerie *verbatim* de `verifier-rig.py` —
   mêmes seuils (0,5 mm de pénétration, 14 mm d'écart au repos), mêmes
   15 couples, mêmes deux sens. Sans quoi les deux séries de chiffres ne
   seraient pas comparables ;
2. **l'éventail** — l'écart minimal entre les chairs de deux bouts de doigts
   voisins. C'est lui qui répond à la vraie question : est-ce que l'écartement
   écarte ? Un signe inversé se lit là, pas dans un compte de sommets.

La sonde se contre-éprouve avant de conclure, et refuse de rendre un verdict si
l'une des deux épreuves échoue :

| épreuve | attendu | mesuré |
| --- | --- | --- |
| faux positifs au repos | aucun | **aucun** |
| fermeture pleine sans écartement | > 100 sommets | **2 242** |

Sans cette contre-épreuve, un « 0 traversée » se lirait comme une mesure alors
qu'il ne serait qu'un silence.

### Ce que la mesure dit

Sur `RIG_Hand.L-NON-VALIDE.blend` (le `.blend` de `b17e548`) :

| `Spread` | index/majeur | majeur/annulaire | annulaire/auriculaire |
| ---: | ---: | ---: | ---: |
| **−1,0** | 27,51 mm | 23,62 mm | 35,34 mm |
| 0,0 | 17,06 mm | 15,27 mm | 30,10 mm |
| **+1,0** | **6,62 mm** | **6,84 mm** | **24,21 mm** |

Et les rotations réellement appliquées par les drivers, à `Spread = +1` :
`index +10,0°`, `majeur +1,0°`, `annulaire −6,0°`, `auriculaire −12,0°` —
c'est-à-dire exactement `ECART`, appliqué sans erreur.

**Conclusion : ce n'est pas l'annulaire.** La suite `+10, +1, −6, −12` est
monotone et cohérente : aucun doigt ne double son voisin. C'est le **sens
global** de `Spread` qui est retourné. Monter `Spread` referme l'éventail sur
les **trois** couples ; le descendre l'ouvre.

Conséquence directe et visible : **deux poses portent le nom de leur
contraire.** `Hand_Open` vaut `Spread = 1,0` — c'est la main la plus *serrée* de
la bibliothèque. `Hand_Spread_Min` vaut `Spread = −1,0` — c'est la plus ouverte.

### Ce qui est réfuté

**Aucune traversée à aucun des 21 pas**, `Spread = +1` compris. Les
« 80 paires majeur/annulaire » ne sont pas reproduites par l'instrument officiel
sur ce fichier : à `Spread = +1`, majeur et annulaire restent à **6,84 mm** l'un
de l'autre — proches, jamais en contact.

La détection BVH du chat 1 avait donc raison sur la **direction** (« l'écartement
rapproche ») et tort sur **l'endroit** (l'annulaire) comme sur le **fait** (des
traversées). Le défaut est réel, plus général, et n'est pas celui qui était
décrit.

### Ce que ça implique pour la suite

Un éventail qui se referme à 6,6 mm quand on demande l'inverse n'a pas besoin de
traverser pour être nuisible : toute pose qui **ferme en écartant** part d'une
marge trois fois plus petite que prévu. C'est la première piste à éprouver pour
les traversées `index/middle` et `middle/ring` de `Hand_Point`, `Hand_Fist_75`
et `Hand_Cupped`.

Le correctif doit porter sur la **cause** : le sens de l'écartement doit être
**mesuré**, comme le sens de la flexion l'est déjà en phase C, et non inscrit à
la main dans `ECART`. Un nombre retourné à la main sur la main gauche
retomberait faux sur la droite, dont la normale de paume est inversée.

### Commandes

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python outils/sonde-ecartement.py -- RIG_Hand.L-NON-VALIDE.blend sortie.json
```

Code de sortie **2** : la sonde sort en erreur dès qu'un couple ne s'écarte pas.
Journal : `ecartement-b17e548.txt` · données : `ecartement-b17e548.json`.
