# Atlas — rig de main / hand rig

Un rig de main Blender construit **entièrement par script**, sur un maillage
mesuré plutôt que réglé à l'œil. Chaque nombre publié ici est mesuré sur le
maillage déformé.

> ## ⚠️ Ce rig n'est PAS validé
>
> Des critères obligatoires restent faux, et ils sont nommés sans arrondi dans
> [`STATUS.md`](STATUS.md). Le fichier livré s'appelle
> `RIG_Hand.L-NON-VALIDE.blend` pour que son état soit lisible sans ouvrir quoi
> que ce soit.

---

## Ce que ce dépôt a appris, et qui vaut au-delà du rig

Le vérificateur de ce dépôt jugeait un fichier « 22 critères réussis, 9
échoués ». Le même fichier, jugé par le vérificateur **étendu**, rend cinq
échecs de plus : la paume s'aplatit au lieu de se creuser, elle s'élargit de
14 mm, le poing ne se ferme qu'à 60 %.

**Le rig n'était pas moins cassé avant. L'instrument ne regardait pas.**

Ce dépôt tient donc une règle, et tout son outillage en découle :

> **Une sonde doit pouvoir échouer.** Un instrument qui rend zéro parce qu'il
> ne mesure rien est indiscernable d'un instrument qui rend zéro parce que tout
> va bien — sauf si on l'a construit pour pouvoir tomber.

Chaque sonde ici se contre-éprouve avant de conclure et **refuse de rendre un
verdict** si sa contre-épreuve échoue. Cinquante et un refus sont exercés par
les autotests, hors Blender, à chaque exécution.

---

## Ce qu'il y a dans ce dépôt

| chemin | contenu |
| --- | --- |
| `rig-main.py` | construit tout : audit, squelette, drivers, poids, poses, correctifs, rendus |
| `verifier-rig.py` | **juge un `.blend` sans reconstruire** — poses, transitions, `Cup`, poing, poids, drivers |
| `atelier/mesures_paume.py` | arc transverse, largeur, convergence — sur la pose **courante** |
| `atelier/correctifs.py` | masques géodésiques, transfert de poids, shape keys clairsemées |
| `atelier/transitions.py` | de vraies actions clés, pas une interpolation recalculée |
| `atelier/jacobienne.py` | convertir un déplacement voulu **dans la pose** en delta de clé |
| `atelier/miroir.py` | la main droite se **transfère**, avec une table de signes mesurée |
| `atelier/eclairage.py` | studio rasant, exposition verrouillée, histogrammes |
| `outils/sonde-ecartement.py` | l'écartement écarte-t-il ? |
| `outils/sonde-creux.py` | la paume se creuse-t-elle, et quel axe la creuse ? |
| `outils/sonde-poids-main.py` | quels sommets n'ont pas de propriétaire ? |
| `outils/anneau.py` | le **diamètre utile** du trou, pas le minimum du contour |
| `outils/rendus-poses.py` | les preuves visuelles, **depuis un `.blend`** |
| `outils/playblast-transitions.py` | les six séquences de transition |
| `outils/revue-visuelle.py` | ce qu'une image montre, avant qu'on la note |
| `outils/comparer-rapports.py` | le tableau de régression |
| `outils/matrice-acceptation.py` | la matrice du cahier, **produite** et jamais recopiée |
| `reports/chat-3/final/poses/` | 78 rendus, six vues par pose |
| `reports/chat-3/transitions/` | 150 images, six séquences |

---

## Reproduire

**Blender 5.1.2.** Aucun add-on.

Juger le rig livré — ne demande **aucun** téléchargement :

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python verifier-rig.py -- RIG_Hand.L-NON-VALIDE.blend
```

Reconstruire — demande le maillage de base :

```bash
export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend
blender --background --factory-startup --python-exit-code 1 \
  --python rig-main.py -- sortie homme g 110 mesure
```

**Compter quatre heures.** Les recherches de contact et le nettoyage des
transitions dominent. Pour apprendre vite, le mode ciblé s'arrête dès que la
question posée a sa réponse :

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python rig-main.py -- work homme g 110 mesure focus=cup
```

`focus=cup|weights|pinky|fist|ok|all`. **Le fichier qu'un focus produit n'a
jamais le droit de s'appeler valide** : il existe pour apprendre, et toute
correction retenue doit être rejouée par `focus=all`.

`--python-exit-code 1` n'est pas décoratif : sans lui, les scripts sortent en
code 0 après un plantage, et un échec se lit comme un succès.

Le maillage de base est le **Human Base Meshes bundle** de Blender Studio,
publié en **CC0**
([source](https://studio.blender.org/tools/assets/human-base-meshes)),
version 1.4.1, 49 420 489 octets,
SHA-256 `3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137`.

---

## Les pièges déjà payés — ne pas les repayer

Chacun a coûté des heures, et aucun n'aurait planté bruyamment.

1. **Les drivers ne s'évaluent pas en mode fond** sans changement d'image. Sans
   `frame_set`, on mesure une main **immobile** — et une main immobile revient
   toujours exactement à sa pose de repos, donc elle passe tous les contrôles.
2. **L'évaluateur d'expressions n'accepte que des droites.** `min`, `max` et le
   produit de deux variables échouent **en silence** (`is_valid = false`).
3. **Une pose finale propre ne prouve rien.** `Neutral→Hand_Fist` a ses deux
   extrémités propres et traverse l'index à t = 0,8.
4. **Jamais de valeur par défaut sur une lecture de mesure.** Un zéro se lit
   comme une mesure.
5. **Le seuil d'acceptation ne doit pas servir de zone franche** à un
   optimiseur : il dépense la marge jusqu'au dernier centième et la franchit.
6. **Un driver réécrit sa voie.** Sonder un canal piloté sans le taire rend
   `+0,00` partout — un tableau parfaitement cohérent et parfaitement faux.
7. **Un `except` qui ne rend pas l'état ne rattrape rien**, il déplace la
   panne. Une exception a laissé l'armature en mode édition ; tout ce qui
   suivait a mesuré une main figée.
8. **Une origine relevée avant que l'origine soit décidée n'est pas une
   origine.**
9. **Compter la mauvaise chose.** Un critère peut punir exactement ce que
   l'anatomie exige.
10. **Une tranche à un seul bord fabrique un contour**, donc un anneau — 19 mm
    de diamètre utile attribués à un pincement.
11. **Un masque géodésique trop large déplace la paume** au lieu de corriger le
    thénar.
12. **Un driver de constante nulle ne pilote rien** : c'est un champ rempli au
    contrat que rien ne lit à l'arrivée.

---

## Method note (English)

This hand rig is built entirely from script: joint centres, the palm plane,
each finger's flexion axis and the thumb's opposition angles are **measured on
the mesh**, never typed in by eye. Every mandatory check can fail the build.

The single most useful finding is not about the rig but about its instruments.
The repository's own verifier rated a file "22 passed, 9 failed". The **extended**
verifier rates the same file with five more failures — the palm flattens
instead of cupping, it widens by 14 mm, the fist only closes to 60 %.

The rig was not less broken before. The instrument was not looking.

Every probe here counter-proves itself before concluding and **refuses to
return a verdict** if that counter-proof fails.

Base mesh: Blender Studio Human Base Meshes bundle (CC0). Blender 5.1.2.
