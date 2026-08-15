# Atlas Hand Rig — reproductibilité et livraison

Constats mesurés sur le dépôt public `OrphicDev/atlas-hand-rig`, commit `b17e548`.
Aucun fichier des dépôts n'a été modifié. Tout a été exécuté sur une copie :
`/tmp/atlas-agent-livraison/clone` (le dépôt copié, `.git` supprimé, 53 Mo).

Machine : macOS Darwin 25.5.0, Blender 5.1.2 (hash `ec6e62d40fa9`, build
2026‑05‑19), Python 3.13.9 embarqué, numpy 2.3.4 embarqué.

---

## 1. Test de clone propre

Fait deux fois : sur une copie du dépôt de travail privée de son `.git`, et sur
un **vrai `git clone` du dépôt GitHub** (`--depth 1`, HEAD = `b17e548`,
75 fichiers suivis, 104 Mo avec l'historique).

```bash
blender --background --factory-startup --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

| mesure | copie sans `.git` | clone GitHub |
| --- | --- | --- |
| **code de sortie** | **2** | **2** |
| durée réelle | **1,29 s** | **1,38 s** |
| critères imprimés | 13 | 13 |
| critères OK | **12** | **12** |
| critères en échec | **1** | **1** |
| téléchargement requis | aucun | aucun |

Les deux sorties sont **identiques ligne pour ligne**. La commande du README
fonctionne telle qu'elle est écrite, sans variable d'environnement, sans
add‑on, sans le maillage de base.

### Les 12 critères qui passent

| critère | mesuré | exigé |
| --- | --- | --- |
| retour exact au repos | 0,0000 mm | < 0,01 mm |
| le rig bouge vraiment | 123,9 mm | > 20 mm |
| Hand_Pinch · les pulpes se touchent | 0,80 mm | ≤ 1,00 mm |
| Hand_Pinch · les pulpes se font face | −0,655 | ≤ −0,50 |
| Hand_Pinch · aucune auto‑intersection | aucune | aucune |
| Hand_OK · les pulpes se touchent | 0,80 mm | ≤ 1,00 mm |
| Hand_OK · les pulpes se font face | −0,655 | ≤ −0,50 |
| Hand_OK · aucune auto‑intersection | aucune | aucune |
| Hand_Pinky_Thumb · les pulpes se touchent | 0,90 mm | ≤ 1,00 mm |
| Hand_Pinky_Thumb · les pulpes se font face | −0,733 | ≤ −0,50 |
| Hand_Fist · aucune auto‑intersection | aucune | aucune |
| tous les drivers sont valides | aucun invalide | aucun invalide |

### Le critère en échec

```
ÉCHEC · Hand_Pinky_Thumb · aucune auto-intersection
        mesuré [{'entre': 'thumb/index', 'sommets': 26},
                {'entre': 'thumb/middle', 'sommets': 14}]
        exigé aucune
```

Le fichier livré porte 21 os `CTRL`, 19 `MCH`, 20 `DEF`, et 13 actions de pose.

---

## 2. Dépendances

### Ce que le dépôt importe

| module | origine | présent ? |
| --- | --- | --- |
| `json`, `math`, `os`, `sys`, `re`, `datetime` | bibliothèque standard Python | oui (Python 3.13.9 de Blender) |
| `bpy`, `bmesh`, `mathutils` | Blender | oui |
| `numpy` (dans `atelier/mains.py`) | embarqué avec Blender | oui, **2.3.4** |
| `humain`, `articulations`, `mains`, `portillon` | `atelier/` du dépôt | oui, les 4 fichiers |

**Aucune dépendance manquante sur une machine neuve.** Aucun `pip install`,
aucun add‑on, aucun paquet tiers. Vérifié en important les quatre modules
`atelier/` depuis le clone : `IMPORT_OK` pour les quatre.

### Aucun chemin extérieur au dépôt

Recherche sur `*.py`, `*.sh`, `*.md`, `*.json` du clone :

| motif cherché | occurrences |
| --- | --- |
| `/Users/`, `/Applications/`, `/Volumes/`, `/home/`, `~/`, `expanduser` | **0** |
| `../`, `os.pardir`, `chdir`, `parent.parent` | **0** |

`rig-main.py` cherche sa racine au lieu de la coder en dur (`_trouver_racine`,
premier ancêtre contenant `atelier/humain.py`) ; `portillon.py` la déduit de son
propre `__file__`. Contrôlé : `PORTILLON_RACINE = /tmp/atlas-agent-livraison/clone`.

Le seul chemin extérieur est **voulu et documenté** : le maillage de base, via
`ATLAS_BASE_MESH` (`atelier/humain.py` l. 24). Il n'est requis que par
`rig-main.py`, jamais par `verifier-rig.py`.

### Le portillon s'ouvre dans un clone propre

`rig-main.py` appelle `portillon.exiger("humain-rig-main")` avant tout travail.
Mesuré dans le clone : `defauts("humain-rig-main") = []` et
`defauts("humain-verifier-rig") = []`. Le portillon ne bloque donc pas un clone.

### Ce qui casse quand même sur un clone propre

**Un échec de ces scripts rend le code de sortie 0.** Mesuré :

| situation | code de sortie | ce qui est imprimé |
| --- | --- | --- |
| `verifier-rig.py` avec un `.blend` inexistant | **0** | `RuntimeError: fichier introuvable` |
| `rig-main.py` sans `ATLAS_BASE_MESH` | **0** | `RuntimeError: maillage de base introuvable` |

Blender en `--background` ne propage pas les exceptions Python au code de
sortie. Le code 2 du cas nominal vient de `sys.exit(2)` et fonctionne ; mais
**tout plantage se lit comme un succès**, y compris une reconstruction qui n'a
jamais commencé. Une CI branchée sur ces commandes déclarerait vert un dépôt
cassé.

Correctif mesuré, une seule option à ajouter aux deux commandes :

```bash
blender --background --factory-startup --python-exit-code 1 --python verifier-rig.py -- ...
```

| cas | sans le drapeau | avec `--python-exit-code 1` |
| --- | --- | --- |
| fichier introuvable | 0 | **1** |
| cas nominal (1 critère faux) | 2 | **2** (inchangé) |

Autres points relevés :

- `atelier/portillon.py` renvoie vers `outils/enquete.py` (l. 148) et
  `outils/garde.py` (l. 27) : **ni l'un ni l'autre n'est dans le dépôt public**
  (`outils/` ne contient que `telecharger-mannequin.sh`). Le message n'apparaît
  que pour un sujet d'enquête absent, donc il ne bloque pas la reconstruction —
  mais il envoie vers un script inexistant.
- `rig-main.py` **salit le dépôt**. Après lancement, la comparaison entre mon
  clone et `git ls-files` du dépôt GitHub montre exactement **5 fichiers non
  suivis** créés dans l'arborescence versionnée :

  ```
  atelier/__pycache__/articulations.cpython-313.pyc
  atelier/__pycache__/humain.cpython-313.pyc
  atelier/__pycache__/mains.cpython-313.pyc
  atelier/__pycache__/portillon.cpython-313.pyc
  enquetes/journal.txt
  ```

  Les quatre `.pyc` viennent des imports `atelier/`, `journal.txt` de
  `portillon.journal()`. **Il n'y a pas de `.gitignore`** : `git status` est
  sale dès le premier lancement, et les cinq fichiers sont candidats au prochain
  `git add .`.

### Reconstruction, en mode `mesure` (sans les 60 rendus)

```bash
export ATLAS_BASE_MESH=…/human_base_meshes_bundle.blend
blender --background --factory-startup --python rig-main.py -- /tmp/…/sortie homme g 110 mesure
```

**Résultat : non conclu, sur deux tentatives.**

| tentative | durée | octets écrits | fichiers produits | fin |
| --- | --- | --- | --- | --- |
| 1 (sortie standard) | 11 min 20 s | **0** | 0 | tuée, code 144 |
| 2 (`PYTHONUNBUFFERED=1`) | **16 min 28 s** | **0** | 0 | arrêtée par moi |

`PYTHONUNBUFFERED=1` **n'y change rien** : Blender redirige lui-même sa sortie
et la tamponne en amont de Python. **Vingt-huit minutes de calcul cumulées,
zéro ligne observable, zéro fichier écrit.**

**Il calculait, il n'était pas bloqué** — mesuré, parce que « long » et
« planté » se ressemblent trop pour être supposés : temps CPU **16 min 49 s**
pour 16 min 28 s écoulées, **100,4 % de CPU**, état `RN`, 1,3 Go de mémoire
résidente. Le processus travaillait à plein régime, sans rien dire. J'ai
arrêté la seconde tentative moi-même, la mesure étant faite : la prolonger
n'aurait produit qu'un nombre plus grand.

Ce que ces lancements établissent malgré tout :

- la chaîne **franchit le portillon, importe les quatre modules `atelier/` et
  charge le maillage de base sans erreur**. Contrôle négatif à l'appui : privé
  de `ATLAS_BASE_MESH`, le même script s'arrête en quelques secondes sur
  `maillage de base introuvable`. Onze minutes de calcul signifient donc qu'il
  était bien entré dans les phases de mesure ;
- **je n'ai pas vérifié le « code 2, 25 critères passent, 1 échoue »** que le
  README annonce pour la reconstruction. Cette ligne du README reste non
  contrôlée.

Deux manques du README que ce lancement suffit à établir :

- **l'argument `mesure` n'est pas documenté**, alors que c'est le seul moyen de
  repasser le pipeline sans produire 60 images ;
- **aucun ordre de grandeur de durée n'est donné**, alors que la variante la
  plus courte dépasse seize minutes sans avoir conclu — et la commande publiée,
  elle, rend en plus 60 images. Quiconque suit le README ne peut pas distinguer
  un calcul long d'un blocage, puisque **le script n'affiche rien pendant tout
  ce temps**. C'est le même défaut que le code de sortie 0 sur exception, vu
  d'un autre angle : rien, dans ce que le pipeline donne à voir, ne permet de
  juger s'il va bien.

---

## 3. Structure et nommage

### Contenu réel (75 fichiers suivis)

| chemin | nombre | documenté au README ? |
| --- | --- | --- |
| `README.md` | 1 | — |
| `.gitattributes` | 1 | non |
| `RIG_Hand.L-NON-VALIDE.blend` (5,4 Mo) | 1 | oui |
| `rig-main.py` (108 548 o) | 1 | oui |
| `verifier-rig.py` (8 006 o) | 1 | oui |
| `atelier/` | 4 (`articulations`, `humain`, `mains`, `portillon`) | oui |
| `enquetes/` | 2 (`humain-rig-main.md`, `humain-verifier-rig.md`) | **non** |
| `outils/` | 1 (`telecharger-mannequin.sh`) | **non** |
| `mesures/` | 3 (`enquete.md`, `rapport-echec.json`, `rapport-rig.L.json`) | oui |
| `images/` | 52 PNG | oui |
| `images/gros-plans/` | 8 PNG | oui |

Aucun fichier annoncé au README n'est absent. **Aucun `LICENSE`.**

### Nommage `.L` / `.R`

- Côté gauche seul, cohérent : `RIG_Hand.L-NON-VALIDE.blend`,
  `mesures/rapport-rig.L.json`, et dans le `.blend` `GEO_Hand.L` / `RIG_Hand.L`.
  Aucune trace de `.R` : rien de contradictoire.
- **Les images ne portent pas le côté.** `rig-main.py` l. 1994 écrit
  `f"{nom_pose}-{plan}.png"` sans `SIDE`, alors que le `.blend` et le JSON
  l'incluent. Une construction `d` (droite) dans le même dossier de sortie
  **écraserait** les 60 images de la gauche.
- Le marqueur `NON-VALIDE` est cohérent : `rig-main.py` l. 2239 suffixe le
  `.blend` avec `-NON-VALIDE` si et seulement si un critère obligatoire est
  faux ; le fichier livré le porte, et la vérification confirme 1 échec.

### La sortie du script ≠ l'arborescence du dépôt

`rig-main.py` écrit **tout à plat** dans le dossier passé en argument : les 60
PNG, `rapport-rig.L.json`, `rapport-echec.json`, le `.blend`. Ni `images/`, ni
`images/gros-plans/`, ni `mesures/`. **L'arborescence publiée est un rangement
fait à la main** ; reproduire ne la reproduit pas.

### Ce que le README documente correctement

| exigence | état |
| --- | --- |
| version de Blender | **oui** — « Blender 5.1.2 », deux fois ; conforme au binaire installé (5.1.2) |
| source du maillage de base | **oui** — lien `studio.blender.org/tools/assets/human-base-meshes` |
| licence du maillage | **oui** — CC0, rappelée aussi dans `outils/telecharger-mannequin.sh` |
| version du maillage | **oui** — v1.4.1, « 47 Mo » (réel : 49 420 489 o = 47,1 Mio) |
| commande de vérification | **oui, et elle marche telle quelle** (code 2) |
| commande de reconstruction | oui, avec `export ATLAS_BASE_MESH` |

### Écarts entre ce que le README promet et ce que le dépôt contient

1. **Le défaut restant est sous‑déclaré.** Le README dit « 26 sommets », « tous
   entre `DEF_thumb_meta.L` et `DEF_index_meta.L` ». Les propres mesures du
   dépôt disent autre chose :

   | source | paires traversées | sommets |
   | --- | --- | --- |
   | README | thumb/index | 26 |
   | `verifier-rig.py` sur le fichier livré | thumb/index 26 + thumb/middle 14 | **40** |
   | `mesures/rapport-echec.json` | thumb/index 26 + thumb/middle 14 + thumb/hand 5 | **45** |

   Le README omet 14 sommets que sa propre commande de vérification affiche, et
   19 que son propre rapport d'échec enregistre.

2. **« 13 poses » — il y en a 12 distinctes.** Les actions `Hand_OK` et
   `Hand_Pinch` sont **identiques** : même signature de courbes (73 f‑curves,
   73 clés, empreinte MD5 identique). Conséquences mesurées :
   - les 4 rendus `Hand_OK-*` sont **pixel pour pixel identiques** aux
     `Hand_Pinch-*` (écart max 0, 0,000 % de pixels différents) ;
   - les 2 gros plans `Hand_OK` sont identiques aux `Hand_Pinch` ;
   - `verifier-rig.py` mesure les deux poses aux mêmes valeurs (0,80 mm,
     −0,655) et compte donc **six critères là où il y en a trois**.

   Sur 52 rendus, 4 sont des doublons ; sur 8 gros plans, 2.

3. **Deux dossiers non documentés** : `enquetes/` et `outils/` n'apparaissent
   pas dans le tableau « Ce qu'il y a dans ce dépôt ».

4. **`mesures/enquete.md` est un doublon exact** de
   `enquetes/humain-rig-main.md` (4 270 octets, `cksum 1680401248` pour les
   deux). Le README appelle `mesures/` les « carnets d'enquête » alors que les
   carnets sont dans `enquetes/`.

5. **Aucun fichier `LICENSE`.** Le README donne la licence du maillage de base
   (CC0) mais aucune licence pour le code publié.

6. **Le mode « mesure » n'est pas documenté.** `rig-main.py` accepte l'argument
   `mesure` qui saute les 60 rendus ; c'est le seul moyen abordable de
   re‑contrôler le pipeline, et le README ne le mentionne pas.

7. **Aucune image dans le README.** 60 rendus publiés, zéro affiché : la page
   d'accueil du dépôt ne montre pas le travail.

### Ce que le README annonce et qui se vérifie

Les autres lignes du tableau « avant / après » ont été recoupées avec
`mesures/rapport-rig.L.json` : elles tiennent.

| ligne du README | valeur annoncée | dans le JSON du dépôt |
| --- | --- | --- |
| compression min. du pouce au poing | 0,7494 | `compression_au_poing.thumb.min = 0.7494` ✓ |
| pouce–index dans `Hand_Pinch` | 0,8 mm | vérification : 0,80 mm ✓ |
| pouce–auriculaire | 0,9 mm | `pince_auriculaire_pouce.ecart_des_empreintes_mm = 0.9` ✓ |
| contamination hors commissures | 0 | `creux_entre_les_doigts.sommets_a_deux_doigts_ailleurs = 0` ✓ |
| écart au retour au repos | 0,0000 mm | `retour_au_repos.ecart_max_mm = 0.0` ✓ |

Écart mineur relevé au passage : `retour_au_repos.course_du_poing_mm = 121,7` au
rapport, contre **123,9 mm** mesuré par `verifier-rig.py` sur le fichier livré.
Le README ne publie pas ce chiffre ; les deux mesures ne portent donc contredit
à aucune de ses affirmations, mais elles ne s'accordent pas entre elles.

---

## 4. Contrôle des images

### Une première sonde a été écrite, puis jetée

La v1 (`analyse-images.py`) définissait le fond comme la **couleur modale** de
l'image. Sur un gros plan où la chair occupe 84 % du cadre, la couleur modale
**est la chair** (206,206,205) et non le fond de rendu (≈58,59,64) : la sonde
mesurait le sujet en croyant mesurer le fond. Le verdict final ne changeait
pas, mais les nombres étaient faux. Les chiffres ci-dessous viennent de la v2
(`analyse-images2.py`), qui n'a plus ce défaut.

Une seconde attente fausse a été attrapée par la calibration elle-même : j'avais
écrit qu'un aplat blanc devait rendre **0 %** de fond. C'est l'attente qui était
fausse — une image unie ne montre rien, quelle que soit sa couleur, donc 100 %
est la bonne réponse. La calibration a refusé de continuer (« SONDE FAUSSE »)
avant d'imprimer le moindre verdict.

### La sonde retenue, éprouvée avant son verdict

| entrée de contenu connu | fond mesuré | attendu | surexposé | attendu | |
| --- | --- | --- | --- | --- | --- |
| aplat gris uni | 100,00 % | 100,00 % | 0,00 % | 0,00 % | OK |
| aplat blanc uni | 100,00 % | 100,00 % | 100,00 % | 100,00 % | OK |
| carré blanc 40×40 sur fond gris 64×64 | 60,94 % | 60,94 % | 39,06 % | 39,06 % | OK |

Verdict de calibration : **sonde fiable**. Trois mesures indépendantes par image :

- **fond** — pixels à moins de 30 (distance RGB) de la couleur de fond de rendu,
  référence fixe (58,59,64) relevée sur la bordure des 52 plans larges. « Vide »
  = plus de 97 %.
- **uniformité** — pixels à ±6 de la couleur modale, quel que soit son ton.
  Attrape aussi bien un cadre entièrement vide qu'un cadre entièrement rempli
  d'un aplat de chair.
- **surexposition** — pixels dont les trois canaux valent ≥ 0,99 (≥ 252,45/255).
  « Surexposé » = plus de 5 %.

### Résultat sur les 60 PNG (900 × 900 ; 52 + 8)

| verdict | nombre | noms |
| --- | --- | --- |
| **VIDES (fond > 97 %)** | **0** | — |
| **VIDES (uniformité > 97 %)** | **0** | — |
| **SUREXPOSÉES (> 5 % à ≥ 0,99)** | **0** | — |

| extrême du lot | valeur | image |
| --- | --- | --- |
| fond le plus étendu | 81,74 % | `images/Hand_Open-auriculaire.png` |
| uniformité la plus forte | 80,25 % | `images/Hand_Fist_75-auriculaire.png` |
| fond le moins étendu | 0,00 % | `gros-plans/gros-plan-Hand_Pinky_Thumb-pouce.png` |

Aucune image n'approche le seuil de 97 % : la plus « vide » du lot en est à
15 points.

**Le zéro de surexposition a été contrôlé par une seconde mesure indépendante**
— un zéro se lit comme une mesure, il fallait vérifier que la sonde n'était pas
simplement muette. La valeur de pixel **maximale absolue sur les 60 images est
229/255 = 0,898** ; l'image la plus claire plafonne à 229, la plus sombre à 216.
Aucun pixel du lot n'atteint 0,99 : le zéro est vrai, pas un artefact.

### Le gros plan « paume » de `Hand_OK`

**Le signalement client est réfuté.** `images/gros-plans/gros-plan-Hand_OK-paume.png` :

- 900 × 900, 815 Ko ;
- **17,46 % de fond**, donc **82,54 % de sujet** ;
- écart-type de luminance 40,8 — dans la moyenne du lot, donc une image
  contrastée, pas un aplat ;
- inspection visuelle : deux pulpes en contact, pouce et index, plein cadre ;
- la copie du dépôt de travail
  (`Atlas/objets/humain/rig/gros-plan-Hand_OK-paume.png`) est **identique au bit
  près** à celle du dépôt public : il n'existe pas de seconde version vide.

Les huit gros plans du dépôt de travail ont été comparés un à un à ceux du dépôt
public : **les huit sont identiques**.

### En revanche, une image du lot ne montre presque rien

`images/gros-plans/gros-plan-Hand_Pinky_Thumb-pouce.png` est le seul cas
douteux du lot, et il ne se voit pas au critère « fond » :

| mesure | cette image | reste du lot |
| --- | --- | --- |
| fond de rendu visible | **0,00 %** | 5,5 à 81,7 % |
| pixels sombres (luminance < 128) | **0,38 %** | 18 à 88 % |
| **écart-type de luminance** | **14,94** | 41,76 à 53,21 |
| p95 − p5 de luminance | **41,1** | 135,7 à 150,7 |

Le cadre est entièrement rempli de chair, et le contraste y est **2,8 fois plus
faible que sur l'image la plus plate du reste du lot**. Inspection visuelle :
un champ presque blanc où les formes se devinent à peine. Elle ne dépasse aucun
des deux seuils de « vide », donc elle n'est pas fautive au sens strict — mais
c'est l'image la moins lisible des 60, et c'est précisément le gros plan censé
documenter le défaut non résolu (`Hand_Pinky_Thumb`).

### Doublons d'images

`gros-plan-Hand_OK-paume.png` et `gros-plan-Hand_OK-pouce.png` **ne montrent pas
la pose `Hand_OK`** : ils montrent `Hand_Pinch`, puisque les deux actions sont
identiques (§ 3, écart 2). Idem pour les quatre plans larges `Hand_OK-*`. Un
lecteur qui cherche un `Hand_OK` distinct voit une image juste mais redondante ;
il ne voit pas une image vide.

---

## 5. Brouillon de compte rendu factuel

> **Atlas — rig de main, état de livraison.** Dépôt public
> `OrphicDev/atlas-hand-rig`, commit `b17e548`, 75 fichiers suivis, 53 Mo.
>
> **Environnement.** Blender 5.1.2 (`ec6e62d40fa9`), Python 3.13.9 et numpy
> 2.3.4 embarqués. Aucun add‑on, aucun paquet à installer. Le seul élément
> extérieur est le maillage de base — Blender Studio Human Base Meshes v1.4.1,
> CC0, 49 420 489 octets — désigné par `ATLAS_BASE_MESH`, requis pour
> reconstruire, jamais pour vérifier.
>
> **Vérification, dans un clone propre.**
> `blender --background --factory-startup --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend`
> → **code de sortie 2 en 1,29 s** : 13 critères imprimés, **12 passent, 1
> échoue**. La commande du README fonctionne telle qu'elle est écrite, sans
> téléchargement et sans configuration.
>
> **Le critère en échec** : `Hand_Pinky_Thumb · aucune auto‑intersection`.
> La vérification affiche deux paires — thumb/index 26 sommets, thumb/middle
> 14, soit 40 — et `mesures/rapport-echec.json` en enregistre trois, soit 45.
> Le README n'en annonce que 26, sur une seule paire.
>
> **Structure.** `atelier/` (4 modules), `enquetes/` (2 carnets), `mesures/`
> (2 rapports + 1 doublon), `outils/` (1 script d'aide), `images/` (52 rendus
> 900×900), `images/gros-plans/` (8). Nommage `.L` cohérent sur le `.blend` et
> le JSON ; les images, elles, ne portent pas le côté. Le marqueur
> `NON-VALIDE` du nom de fichier est posé par le script lui‑même dès qu'un
> critère obligatoire est faux.
>
> **Images.** 60 PNG mesurés avec une sonde calibrée au préalable sur des
> aplats de contenu connu. **Aucune image vide** : le fond de rendu occupe au
> plus 81,74 % d'une image, seuil à 97 %. **Aucune image surexposée** —
> contrôlé deux fois : la valeur de pixel la plus haute de tout le lot est
> 229/255, soit 0,898, loin de 0,99. Le gros plan « paume » de `Hand_OK`
> signalé comme vide **ne l'est pas** : 82,5 % de sujet, contraste normal,
> deux pulpes en contact plein cadre ; la copie du dépôt de travail est
> identique au bit près. Une seule image mérite d'être refaite :
> `gros-plan-Hand_Pinky_Thumb-pouce.png`, cadre entièrement rempli de chair,
> écart-type de luminance 14,9 contre 41,8 minimum partout ailleurs — un champ
> presque blanc, et c'est justement le gros plan censé montrer le défaut non
> résolu.
>
> **Ce qui manque.**
> 1. Les scripts sortent en **code 0 quand ils plantent** (fichier introuvable,
>    maillage absent) : un échec se lit comme un succès. Corrigé par
>    `--python-exit-code 1`, mesuré, sans effet sur le code 2 nominal.
> 2. `Hand_OK` et `Hand_Pinch` sont **la même pose** : mêmes courbes
>    d'animation, rendus identiques au pixel près. Le dépôt annonce 13 poses,
>    il en a 12.
> 3. Le chiffre du défaut restant au README (26) est inférieur à ce que le
>    dépôt mesure lui‑même (40 à la vérification, 45 au rapport d'échec).
> 4. Pas de `LICENSE` pour le code ; pas de `.gitignore` alors qu'une
>    reconstruction écrit `enquetes/journal.txt` dans le dépôt.
> 5. `enquetes/` et `outils/` ne sont pas au sommaire du README, et
>    `mesures/enquete.md` est un doublon exact de `enquetes/humain-rig-main.md`.
> 6. `atelier/portillon.py` renvoie vers `outils/enquete.py` et
>    `outils/garde.py`, absents du dépôt public.
> 7. Le script écrit ses 60 PNG à plat : l'arborescence `images/` publiée est
>    un rangement manuel, que « reproduire » ne reproduit pas.

---

## Intégrité des dépôts

- **Dépôt public** : `git status` vide, HEAD toujours `b17e548`. **Intact.**
- **Dépôt de travail `Atlas`** : il porte des modifications (`.tour/sondes.txt`
  21 h 50, `enquetes/journal.txt` 21 h 54, entre autres) dont l'horodatage
  tombe dans ma fenêtre de travail. **Elles ne viennent pas de moi**, et la
  source est identifiée : un **autre processus Blender, PID 94136**, tourne
  depuis 34 min sur

  ```
  --python-exit-code 1 --python objets/humain/rig-main.py
      -- …/Atlas/objets/humain/rig2 homme g 110 mesure
  ```

  c'est-à-dire la même reconstruction, lancée depuis `Atlas` par une session
  concurrente. Elle écrit `enquetes/journal.txt` dans ce dépôt, exactement comme
  la mienne l'a fait dans mon clone. **Je ne l'ai pas arrêtée** — elle ne
  m'appartient pas.

  Preuve que ce n'est pas moi : toutes mes invocations ont visé
  `/tmp/atlas-agent-livraison/`, et le portillon a été mesuré comme résolvant sa
  racine sur le clone (`PORTILLON_RACINE = /tmp/atlas-agent-livraison/clone`).
  Le seul fichier d'`Atlas` que j'ai touché est le maillage de base, en lecture,
  dont la date de modification est inchangée (20 janvier 2026).

  Deux observations utiles au passage : cette session a lancé la commande **avec
  `--python-exit-code 1`**, le correctif recommandé au § 2 ; et son mode
  `mesure` en est à **34 min 26 s** (35 min de CPU) sans avoir écrit un seul
  fichier dans son dossier de sortie — ce qui confirme, sur une troisième
  exécution et depuis un autre dépôt, la durée relevée plus haut.

---

## Annexes — traces

| fichier | contenu |
| --- | --- |
| `/tmp/atlas-agent-livraison/verif-stdout.txt` | sortie complète de la vérification en clone propre |
| `/tmp/atlas-agent-livraison/analyse-images2.py` | la sonde d'images retenue, avec sa calibration |
| `/tmp/atlas-agent-livraison/analyse-images2.txt` | les 60 lignes de mesure |
| `/tmp/atlas-agent-livraison/analyse-images.py` | la sonde v1, fausse — conservée pour mémoire |
| `/tmp/atlas-agent-livraison/verif-abs.txt`, `verif-rel.txt` | chemin absolu / fichier introuvable |
| `/tmp/atlas-agent-livraison/rigmain-sansmesh.txt` | `rig-main.py` sans `ATLAS_BASE_MESH` (code 0) |
| `/tmp/atlas-agent-livraison/poses.py` | l'empreinte des 13 actions de pose |
| `/tmp/atlas-agent-livraison/mesure-stdout.txt` | reconstruction en mode `mesure` |
