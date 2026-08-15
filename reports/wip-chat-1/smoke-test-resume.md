# Smoke test du vérificateur étendu — état WIP

Commande :

```bash
blender --background --factory-startup --python-exit-code 1 --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

**Code de sortie réel : 2.** 22 critères passent, 9 échouent.

Le `.blend` mesuré date de `b17e548` : il ne contient PAS les corrections
de scripts de cette branche. Ces échecs décrivent donc l'état audité, vu
par un instrument enfin honnête — pas une régression.

| critère en échec | sommets | couples |
| --- | ---: | --- |
| Hand_Pinky_Thumb | 717 | thumb/index, thumb/middle, thumb/pinky, thumb/hand |
| Hand_Cupped | 80 | middle/ring |
| Hand_Fist_75 | 118 | thumb/index, index/middle, middle/ring |
| Hand_Pinky_Thumb | 717 | thumb/index, thumb/middle, thumb/pinky, thumb/hand |
| Hand_Point | 978 | thumb/middle, thumb/ring, index/middle, middle/ring |
| transition Neutral→Hand_Fist | 492 | thumb/index, thumb/index |
| transition Neutral→Hand_Point | 148 | index/middle, index/middle, index/middle |
| transition Neutral→Hand_Cupped | 101 | middle/ring, middle/ring, middle/ring |
| transition Neutral→Hand_Pinky_Thumb | 192 | thumb/index, thumb/index, thumb/index |

> L'ancienne sonde déclarait « aucune auto-intersection » sur la
> plupart de ces poses : elle n'en regardait que quatre, sur cinq couples
> de familles et dans un seul sens.
