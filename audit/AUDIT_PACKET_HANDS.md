# Audit packet — Hands (chat 2)

- Repository: https://github.com/OrphicDev/atlas-hand-rig
- Branch: hands/chat-2-photoreal-v2
- Base commit: e2d4b1c9e05949531d9348d68367c225b2169872
- Final commit: voir `git rev-parse HEAD` — dernier publié au moment de cette rédaction : 2a73572
- Compare URL: https://github.com/OrphicDev/atlas-hand-rig/compare/e2d4b1c9e05949531d9348d68367c225b2169872...hands/chat-2-photoreal-v2
- Status: **NON-VALIDE**
- Blender version: 5.1.2 (hash `ec6e62d40fa9`, 2026-05-19)
- Operating system: macOS 26.5 (darwin, Apple Silicon), 10 cœurs, 16 Go
- Base mesh: `human-base-meshes-bundle-v1.4.1` (Blender Studio, CC0), 49 420 489 octets, SHA-256 `3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137`
- Generation command: `blender --background --factory-startup --python-exit-code 1 --python rig-main.py -- ./sortie homme g 110 mesure` (requiert `ATLAS_BASE_MESH`)
- Validation command: `blender --background --factory-startup --python-exit-code 1 --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend`
- **Generation exit code: 1 — plantage**, 53 min, 16 critères réussis, 15 échoués, aucun `.blend` produit. Cause trouvée et corrigée (`8727990`) ; la reconstruction qui doit le prouver n'a pas encore abouti.
- Validation exit code: 2 (22 réussis, 9 échoués) — reproduit depuis le commit public sur le `.blend` de `b17e548`
- Git status: clean
- Running processes: aucun
- Mandatory failures: 15 à la génération, 9 à la validation
- Reports: https://github.com/OrphicDev/atlas-hand-rig/tree/hands/chat-2-photoreal-v2/reports/chat-2
- Still renders: **aucun produit par ces scripts.** Les 60 images de `images/` datent de `b17e548`
- Contact sheets: aucune produite par ces scripts
- Transition videos: **les six playblasts existent** — `videos/b17e548/`, 150 images (6 × 25) + `playblasts.html` qui les anime. **Rendus depuis le `.blend` de `b17e548`** : ils documentent les défauts de CE rig, pas l'effet des correctifs du chat 2. Pas de MP4 : cette build de Blender est compilée sans FFmpeg (énumération sans aucun conteneur vidéo) et la machine n'a pas de binaire `ffmpeg`
- Blend files: **aucun reflétant ces scripts.** `RIG_Hand.L-NON-VALIDE.blend` date de `b17e548` · main droite : **inexistante**
- SHA-256 manifest: `audit/manifest-sha256.txt`

---

## Résultat de la baseline — étape B du cahier

**16 critères réussis, 15 échoués. Code de sortie 1 (plantage).**

| critère en échec | mesuré | exigé |
| --- | --- | --- |
| `Hand_Pinch` · les pulpes se touchent | 3,19 mm | ≤ 1,00 mm |
| `Hand_OK` · les pulpes se touchent | 1,04 mm | ≤ 1,00 mm |
| `Hand_OK` · les pulpes se font face | −0,46 | ≤ −0,50 |
| `Hand_Pinky_Thumb` · les pulpes se touchent | 2,46 mm | ≤ 1,00 mm |
| `Hand_Pinky_Thumb` · les pulpes se font face | −0,079 | ≤ −0,50 |
| `Hand_Fist_75` · aucune auto-intersection | 779 + 24 + … | aucune |
| `Hand_Point` · aucune auto-intersection | 440 + 445 + … | aucune |
| `Hand_Cupped` · aucune auto-intersection | 1 | aucune |
| `Hand_Pinky_Thumb` · aucune auto-intersection | 127 + … | aucune |
| transition `Neutral→Hand_Fist` | dès t = 0,7 | aucune à chaque étape |
| transition `Neutral→Hand_Point` | dès t = 0,3 | aucune à chaque étape |
| transition `Neutral→Hand_OK` | dès t = 0,8 | aucune à chaque étape |
| transition `Neutral→Hand_Cupped` | dès t = 0,7 | aucune à chaque étape |
| transition `Neutral→Hand_Pinky_Thumb` | dès t = 0,4 | aucune à chaque étape |
| la paume creuse se creuse vraiment | **1,0 mm** | ≥ 6 mm |

Journal complet : `reports/chat-2/baseline/journal-generation.txt`.
Rapport JSON : `reports/chat-2/baseline/rapport-rig.L.json`.

## Known limitations, en clair

1. **Aucune reconstruction n'a encore abouti.** La baseline plante en code 1
   après la phase G ; la cause est corrigée mais non éprouvée.
2. **Aucun `.blend` ne contient les corrections de scripts.**
3. **La main droite n'existe pas.** Le cahier exige qu'elle dérive d'une main
   gauche validée, qui ne l'est pas.
4. **Les playblasts existent mais viennent de l'ancien `.blend`.** Ils prouvent
   l'outil et documentent les transitions fautives ; ils ne prouvent aucun
   correctif. Aucun MP4 n'est possible dans cet environnement.
5. **Aucun rendu produit par ces scripts.** L'éclairage rasant est intégré au
   pipeline mais toutes les exécutions ont tourné en mode `mesure`.
6. **Sept correctifs versés et non prouvés.** Ils sont argumentés et publics ;
   il leur manque une mesure.
7. Une image à refaire : `gros-plan-Hand_Pinky_Thumb-pouce.png`, écart-type de
   luminance **14,9/255** contre 41,8 minimum ailleurs — vérifié
   indépendamment, le chiffre du chat 1 est exact.

## Ce que cette itération a établi

Cinq des sept causes sont la même erreur de méthode : **un instrument a été
corrigé sans que l'espace, la doctrine ou la boucle qui l'entourent le soient.**
La sonde d'intersection est passée à 15 couples sans que la recherche de pose
reçoive d'axes ; la règle « ce qui est obligatoire ne se négocie pas » n'a été
câblée que pour un critère sur quatre ; les transitions ont été mesurées sans
être corrigées ; le module d'éclairage a été prouvé sans être branché.

Et un critère nommé « aucune interpénétration » ne regardait qu'un patch de
5 mm : il se déclarait vert avec **213 sommets traversants** dans la main.
