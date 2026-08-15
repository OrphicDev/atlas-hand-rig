# Audit packet — Hands

- Repository: https://github.com/OrphicDev/atlas-hand-rig
- Branch: wip/chat-1-honest-probe
- Base commit: b17e54806f942736e47c4dcfd477a91b7fd6f262
- Final commit: 4750c21b0722594a3c600489d5e70888fb1dcb5b
- Compare URL: https://github.com/OrphicDev/atlas-hand-rig/compare/b17e54806f942736e47c4dcfd477a91b7fd6f262...4750c21b0722594a3c600489d5e70888fb1dcb5b
- Status: NON-VALIDE
- Blender version: 5.1.2
- Operating system: macOS 26.5 (darwin, Apple Silicon)
- Generation command: `blender --background --factory-startup --python-exit-code 1 --python rig-main.py -- ./sortie homme g 110 mesure` (requiert `ATLAS_BASE_MESH`)
- Validation command: `blender --background --factory-startup --python-exit-code 1 --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend`
- Generation exit code: NON MESURÉ — la dernière reconstruction a été interrompue avant la fin ; aucun `.blend` n'en est issu
- Validation exit code: 2
- Git status: clean
- Running processes: aucun
- Mandatory failures: 9
- Known limitations: voir la liste ci-dessous
- Reports: https://github.com/OrphicDev/atlas-hand-rig/tree/4750c21b0722594a3c600489d5e70888fb1dcb5b/reports/wip-chat-1
- Still renders: https://github.com/OrphicDev/atlas-hand-rig/tree/4750c21b0722594a3c600489d5e70888fb1dcb5b/images · https://github.com/OrphicDev/atlas-hand-rig/tree/4750c21b0722594a3c600489d5e70888fb1dcb5b/renders/wip-chat-1/preuves-lumiere
- Contact sheets: https://github.com/OrphicDev/atlas-hand-rig/blob/4750c21b0722594a3c600489d5e70888fb1dcb5b/renders/wip-chat-1/planche-lumiere.html
- Transition videos: AUCUNE — non produites, tâche transmise au chat 2
- Blend files: https://github.com/OrphicDev/atlas-hand-rig/blob/4750c21b0722594a3c600489d5e70888fb1dcb5b/RIG_Hand.L-NON-VALIDE.blend (main gauche, **antérieur aux corrections de scripts de cette branche**) · main droite : **inexistante**
- SHA-256 manifest: https://github.com/OrphicDev/atlas-hand-rig/blob/4750c21b0722594a3c600489d5e70888fb1dcb5b/audit/manifest-sha256.txt

---

## Résultat de la validation

**22 critères passent, 9 échouent.** Code de sortie 2.

| critère en échec | sommets | couples |
| --- | ---: | --- |
| `Hand_Point` | 978 | thumb/middle, thumb/ring, index/middle, middle/ring |
| `Hand_Pinky_Thumb` | 717 | thumb/index, thumb/middle, thumb/pinky, thumb/hand |
| `Hand_Fist_75` | 118 | thumb/index, index/middle, middle/ring |
| `Hand_Cupped` | 80 | middle/ring |
| transition `Neutral→Hand_Fist` | 492 | thumb/index |
| transition `Neutral→Hand_Point` | — | plusieurs, dès l'étape 0,3 |
| transition `Neutral→Hand_Cupped` | — | middle/ring, dès l'étape 0,7 |
| transition `Neutral→Hand_Pinky_Thumb` | — | plusieurs, dès l'étape 0,4 |

Le `.blend` mesuré date de `b17e548`. Ces échecs décrivent l'état audité vu
par un instrument enfin honnête — **ce n'est pas une régression**.

## Known limitations, en clair

1. **Aucun `.blend` ne contient les corrections de scripts** de cette branche.
   La reconstruction a été arrêtée avant la fin ; rien n'a été republié sous un
   nom laissant croire le contraire.
2. **La main droite n'existe pas.** Le cahier des charges exige qu'elle dérive
   d'une main gauche validée, qui ne l'est pas.
3. **Aucune vidéo ni playblast de transition** n'a été produit — seuls les
   échantillons numériques à 11 étapes existent.
4. **`atelier/eclairage.py` n'a jamais été exécuté dans le pipeline.** Il est
   prouvé isolément : 0 % d'écrêtage sur 18 images, key à 75° de la normale.
5. **Le code de sortie de la génération complète n'a jamais été relevé.** Trois
   tentatives, aucune menée à terme.
6. **`Spread = 1` ferait se traverser majeur et annulaire** (80 paires) selon
   une détection BVH indépendante — non confirmé par le pipeline principal.
7. Une image à refaire : `gros-plan-Hand_Pinky_Thumb-pouce.png`, écart-type de
   luminance 14,94 contre 41,76 minimum ailleurs.

## Ce que cette itération a réellement établi

L'ancienne sonde d'auto-intersection **ne voyait que 22 % des traversées** —
672 sur 3 009 — parce qu'elle testait 5 couples de familles sur 15, dans un seul
sens, sur 4 poses sur 13. Tout ce que le commit `b17e548` déclarait validé
reposait sur elle.
