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

1. **P1 — volumes et réalisme.** Effet « saucisse », dômes de jointures absents
   au dos du poing, thénar/hypothénar, paume réellement creuse. Poids d'abord,
   correctifs pilotés ensuite — jamais l'inverse.
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
