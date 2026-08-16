# Audit packet — Hands (chat 3)

- Repository: https://github.com/OrphicDev/atlas-hand-rig
- Branch: hands/chat-2-photoreal-v2
- Base commit chat 2: e2d4b1c9e05949531d9348d68367c225b2169872
- HEAD audite chat 3: 96d017755504499545c340fa404922a631c48826
- Final commit: 13e1e4218716bb36cd42c7c2a15158a850b79fc3
- Compare URL: https://github.com/OrphicDev/atlas-hand-rig/compare/e2d4b1c9e05949531d9348d68367c225b2169872...13e1e4218716bb36cd42c7c2a15158a850b79fc3
- Status: **NON-VALIDE**
- Blender: 5.1.2 (`ec6e62d40fa9`, 2026-05-19) — macOS 26.5, Apple Silicon, 10 coeurs
- Base mesh: `human-base-meshes-bundle-v1.4.1`, 49 420 489 octets, SHA-256 `3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137`

## Les commandes, et ce qu'elles rendent

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend

# reconstruction complete — compter 4 h
blender --background --factory-startup --python-exit-code 1 \
  --python rig-main.py -- sortie homme g 110 mesure

# mode cible : quelques minutes au lieu de quatre heures
blender --background --factory-startup --python-exit-code 1 \
  --python rig-main.py -- work homme g 110 mesure focus=cup

# les rendus, DEPUIS le .blend — plus derriere la reconstruction
blender --background --factory-startup --python-exit-code 1 \
  --python outils/rendus-poses.py -- FICHIER.blend rendus/

# la matrice d'acceptation, produite et jamais recopiee
python3 outils/matrice-acceptation.py journal.txt matrice.md
```

## Les quatre blocages du chat 2

| blocage | avant | maintenant |
| --- | --- | --- |
| `Cup` aplatit et elargit | arc −10,89 mm, largeur +14,04 | **arc +6,71, largeur −10,79** |
| cerclage rouge de Sacha | −0,88 mm | **−4,94 mm** |
| poids sans proprietaire | 12 329 ambigus | **0 entre rayons non voisins** |
| la generation plante | code 1, aucun `.blend` | **va au bout** |

## Ce qui resiste, sans arrondi

- `Hand_Pinky_Thumb` : la pose EXISTE (0,10 mm a l'approche), le nettoyage ne la
  tient pas. Les os correctifs sont poses et leur amplitude cherchee ;
- `Hand_OK` : l'anneau et le contact sont antagonistes. Sur le dernier `.blend`,
  NI le OK NI le Pinch n'ont d'anneau mesurable — le module REFUSE de rendre un
  nombre, et ce refus est le resultat ;
- le poing : 0,6 maximum, les quatre doigts SEULS se traversent 820 fois a 0,7 ;
- la main droite n'existe pas — le cahier exige une gauche validee.

## Ce que le chat 3 a change aux instruments

Onze outils et modules, 51 refus exerces par les autotests hors Blender. Trois
modules ecrits par agents PUIS REFUTES par un second agent : onze defauts reels,
dont une garde placee apres une normalisation donc aveugle par construction, et
une contre-epreuve qui testait IEEE 754 au lieu du module.

**Le verificateur etendu, lance sur le fichier que l'ancien jugeait « 22 reussis
/ 9 echoues », rend cinq echecs de plus — au chiffre pres ce que les sondes
avaient trouve a la main. Le rig n'etait pas moins casse avant : l'instrument ne
regardait pas.**

---

