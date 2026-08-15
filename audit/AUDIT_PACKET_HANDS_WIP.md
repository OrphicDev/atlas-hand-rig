# PAQUET D'AUDIT — état WIP du chat 1

**Ce paquet documente un état NON VALIDE.** Il existe pour qu'un tiers puisse
refaire les mesures sans faire confiance à ce qui est écrit ici.

Base auditée : `b17e54806f942736e47c4dcfd477a91b7fd6f262`
Branche : `wip/chat-1-honest-probe`

---

## 1. Ce qui a été mesuré, et par qui

Trois agents ont travaillé en parallèle du responsable, chacun sur du
vérifiable, sans toucher au rig.

| source | ce qu'elle établit |
| --- | --- |
| `audit/wip-chat-1/audit-collisions.py` | sonde indépendante, 15 couples, deux sens |
| `reports/wip-chat-1/agent-mesures.md` | collisions par pose et par transition |
| `reports/wip-chat-1/agent-lumiere.md` | lumière rasante, histogrammes, détection BVH |
| `reports/wip-chat-1/agent-livraison.md` | clone propre, dépendances, images |
| `reports/wip-chat-1/smoke-test-*` | exécution réelle du vérificateur étendu |

Chaque agent a **vérifié sa sonde avant de lui faire rendre un verdict**, et
deux d'entre eux ont jeté une première sonde fausse en cours de route :

- l'agent images prenait la **couleur modale** pour le fond — or sur un gros
  plan la couleur modale est la chair : il mesurait le sujet en croyant mesurer
  le fond ;
- l'agent lumière a contrôlé son décodeur PNG contre la lecture Blender
  (écart maximal **6,0 × 10⁻⁸**) et vérifié que sa mesure d'écrêtage réagit
  (key ×10 → 0 % puis 1,223 %).

---

## 2. Le défaut d'instrument, chiffré

**672 traversées détectées sur 3 009 réellement présentes — 22 %.**

| cause | conséquence mesurée |
| --- | --- |
| 5 couples testés sur 15 | `thumb/pinky` jamais examiné : 556 sommets dans `Hand_Pinky_Thumb` |
| comptage unidirectionnel | `ring/pinky` : 0 dans un sens, **403** dans l'autre |
| 9 poses sur 13 non contrôlées | `Point` 1 540, `Fist_75` 118, `Cupped` 80 |
| `ZONES_ARTICULAIRES` classé comme os | 203 sommets mal attribués, intersections fantômes sur `Pinch` et `OK` |

**Réserve de lecture, importante :** un « sommet signalé » n'est pas une
collision physique distincte. Un même contact peut produire des dizaines de
sommets. Ces nombres servent à comparer des états entre eux, pas à compter des
événements.

---

## 3. Collisions par pose — sonde honnête

Relevé par l'audit indépendant sur le `.blend` de `b17e548`, classement strict
(seuls les 20 groupes portant un nom d'os) :

| pose | sommets | pose | sommets |
| --- | ---: | --- | ---: |
| Neutral | 0 | Fist_50 | 0 |
| Relaxed | 0 | **Fist_75** | **118** |
| Open | 0 | Fist | 0 |
| Spread_Min | 0 | **Point** | **1 540** |
| Fist_25 | 0 | Pinch | 0 |
| **Cupped** | **80** | OK | 0 |
| **Pinky_Thumb** | **1 271** | | |

**Total strict : 3 009.**

## 4. Transitions — 4 fautives sur 6

| transition | première étape fautive | pic |
| --- | --- | ---: |
| `Neutral→Fist` | 0,8 | **355** à t = 0,9 |
| `Neutral→Point` | 0,3 | 1 942 à t = 0,9 |
| `Neutral→Pinky_Thumb` | 0,4 | 2 238 |
| `Neutral→Cupped` | 0,7 | 80 |

`Neutral→Fist` est le cas exemplaire : **les deux extrémités sont propres** et
le milieu ne l'est pas. Aucun contrôle de l'ancien dépôt ne pouvait le voir.

## 5. Deux poses n'en faisaient qu'une

`Hand_Pinch` et `Hand_OK` : **0,0 mm** d'écart maximal sur 54 019 sommets,
empreinte identique sur 73 courbes, rendus identiques au pixel près. La
bibliothèque annonçait 13 poses, elle en contenait **12** — et le vérificateur
comptait deux réussites pour un seul geste.

## 6. Reproductibilité — mesuré

| contrôle | résultat |
| --- | --- |
| clone propre (copie + vrai `git clone`) | **code 2**, 1,29 s et 1,38 s, sorties identiques |
| dépendances manquantes | **aucune** — tout vient de Blender 5.1.2 ou du dépôt |
| chemins absolus / remontées hors dépôt | **zéro** |
| scripts sortant en code 0 après plantage | **oui** → corrigé par `--python-exit-code 1` |
| exécutions muettes | 11, 16 et 34 min sans un octet écrit → **corrigé** (sortie déstamponnée) |

**Non vérifié :** la ligne « reconstruction complète, code 2 » n'a **jamais été
menée à terme** dans cette session. Deux tentatives arrêtées, une troisième
interrompue par le responsable. À refaire.

## 7. Images

| contrôle | résultat |
| --- | --- |
| images vides (> 97 % de fond) | **aucune** — maximum du lot 81,74 % |
| images surexposées (> 5 % à ≥ 0,99) | **aucune** — pixel maximal 229/255 = 0,898 |
| signalement « gros plan OK vide » | **réfuté** — 82,5 % de sujet, contraste normal |
| image à refaire | `gros-plan-Hand_Pinky_Thumb-pouce.png` (σ = 14,94 contre 41,76 min. ailleurs) |

## 8. Éclairage rasant — prouvé isolément

Key à **75,0° de la normale**, fill à 15 %, rim à 25 %, AgX / exposition 0,0 EV
verrouillés. **0,000 % d'écrêtage sur 18 images**, luminance plafonnée à 0,846.

**Réserve conservée :** sous AgX, ×10 sur la key ne donne que 1,22 %
d'écrêtage au seuil 0,99 — ce seuil ne discrimine presque rien, le chiffre
utile est celui pris au seuil 0,95.

**Non intégré** au pipeline. Le module vit dans `atelier/eclairage.py`.

---

## 9. Comment refaire ces mesures

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

Attendu : **code 2**, 22 critères passent, 9 échouent.

```bash
blender --background --factory-startup \
  --python audit/wip-chat-1/audit-collisions.py -- RIG_Hand.L-NON-VALIDE.blend
```

Le manifeste `audit/manifest-sha256.txt` donne l'empreinte de chaque fichier de
ce paquet.
