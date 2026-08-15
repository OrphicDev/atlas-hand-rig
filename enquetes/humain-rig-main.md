---
sujet: humain-rig-main
date: 2026-08-15
---

## 1. CE QUE JE CROIS SAVOIR

Sacha m'a arrêté au milieu d'une boucle et m'a donné un tutoriel complet de rig
de main. Sa remarque décisive vient d'une photo annotée : « les deux parties que
je t'encercle en rouge doivent pouvoir se rapprocher l'une de l'autre » — le
métacarpien du pouce et celui de l'auriculaire.

Je croyais que mon rig échouait sur la POSE du pouce. J'ai passé la nuit à
chercher cette pose. La cause est en amont : **mon rig ne pouvait pas creuser la
paume**, donc aucune pose n'existait à trouver.

## 2. CE QUE J'AI VÉRIFIÉ

- **Le tutoriel le dit explicitement** : « Les os métacarpiens sont
  indispensables pour obtenir une paume qui se creuse naturellement. Ne
  construis pas une main "plate" composée uniquement de trois os par doigt. » Et
  pour le creusement : « Le creusement doit rapprocher l'auriculaire du pouce
  sans casser le volume de la paume. » C'est exactement le cerclage rouge.

- **Mon ancien rig avait bien des os `doigtK_meta`**, mais tous partaient du
  MÊME point (le bout du carpe) et étaient rigidement enchaînés. Aucun degré de
  liberté propre : la paume restait un plan.

- **Trois fautes de mesure établies cette nuit**, toutes dans mes instruments et
  non dans le rig, et toutes à ne pas refaire ici :
  1. je lisais `main.data.vertices[].normal`, la normale du maillage AU REPOS —
     l'armature déforme par modificateur, donc cette valeur ne bouge jamais avec
     la pose. Ma mesure rendait `+0,98` sur 1 600 poses, identique partout.
  2. j'avais attribué les amplitudes anatomiques aux axes PAR SUPPOSITION
     (x=flexion, y=vrille, z=abduction). Mesuré : c'est **z** qui portait la
     rotation d'opposition, et je lui avais mis la butée de l'abduction — je
     rendais impossible le geste demandé.
  3. `doigt1` n'était pas le majeur mais l'ANNULAIRE. Écarts mesurés des
     phalanges moyennes : +18,7 / 0 / −19,0 / −44,5 mm. Je visais deux doigts
     trop loin.

- **Sensibilité mesurée des axes du métacarpien du pouce** (elle reste valable) :
  déplacement du bout — mx 118,8 mm, mz 50,8 mm, my 19,4 mm ; retournement de la
  pulpe — mz 0,881, my 0,602, mx 0,08.

- **Le sens de l'écartement était retourné, et ce n'était pas l'annulaire.**
  Le checkpoint transmettait, sans l'avoir confirmé par le pipeline, que
  `Spread = 1` ferait se traverser majeur et annulaire (80 paires), « signe ou
  axe probablement inversé sur l'annulaire ». Remesuré deux fois, par deux
  chemins séparés :
  1. `outils/sonde-ecartement.py` sur le `.blend` de `b17e548`, balayage de −1 à
     +1 par pas de 0,1 : monter `Spread` REFERME l'éventail sur les **trois**
     couples — index/majeur 17,06 → 6,62 mm, majeur/annulaire 15,27 → 6,84 mm,
     annulaire/auriculaire 30,10 → 24,21 mm. Les rotations appliquées valent
     exactement `ECART` (+10,0 / +1,0 / −6,0 / −12,0°) : les drivers ne se
     trompaient pas, la suite est monotone, aucun doigt ne double son voisin.
  2. la mesure ajoutée en phase D, sur un rig reconstruit : à `+ECART`
     5,78 / 7,54 / 24,68 mm, à `−ECART` 27,44 / 23,75 / 36,26 mm.

  C'est donc le **sens global** de la rotation autour de la normale de la paume
  qui était faux — et le signe d'une normale construite est arbitraire, ce que
  la phase C sait déjà pour la flexion. Conséquence visible : `Hand_Open`
  (`Spread = 1`) était la main la plus SERRÉE de la bibliothèque et
  `Hand_Spread_Min` la plus ouverte.

  **Réfuté au passage :** aucune traversée à aucun des 21 pas. Les 80 paires
  n'existent pas sur ce fichier ; à `Spread = +1`, majeur et annulaire restent
  à 6,84 mm l'un de l'autre.

## 3. CE QUE LA GÉOMÉTRIE DIT

- Portée de la chaîne du pouce : **117,7 mm** pour une cible à 46,8 mm
  (marge +71 mm). Le maillage n'a jamais été le facteur limitant.
- Les quatre pulpes touchent la paume à **0,1 mm** en poing : le poing n'était
  pas creux, contrairement à ce que j'avais lu sur une image.
- Empreintes identifiées et vérifiées : pouce 819 sommets (36 % de la phalange,
  décalage +6,64 mm du côté pulpe), index 888 sommets (38 %, +4,73 mm). Écart
  main ouverte 62,9 mm.

## 4. CE QUI RESTE INCERTAIN

**Le creusement suffira-t-il à amener l'empreinte de l'auriculaire sur celle du
pouce ?** C'est la pose que Sacha demande en livraison, et elle exige les deux
mobilités à la fois : le creusement des métacarpiens 4 et 5, et l'opposition du
pouce.
→ se tranche par la mesure : distance empreinte auriculaire / empreinte pouce
quand `Cup` et `Thumb_Opposition` vont de 0 à 1. Si elle ne tombe pas à zéro,
c'est le placement des métacarpiens qu'il faut reprendre, et non la pose.

## 5. CE QUI RÉFUTERAIT

- **Le test du Bone Roll (phase C du tutoriel).** Chaque phalange pivotée de
  +30° doit fermer le doigt VERS LA PAUME. Un seul doigt qui part à l'envers ou
  qui se vrille condamne l'orientation, et le tutoriel interdit de créer le
  moindre driver avant que ce test passe.
- **`Fist = 0` doit redonner EXACTEMENT la pose de repos.** Écart mesuré sommet
  par sommet ; au-dessus de 0,01 mm, le montage CTRL/MCH/DEF fabrique une double
  transformation et tout ce qui suit est faux.
- **Aucun sommet d'un doigt ne doit recevoir de poids d'un autre doigt.** Ce
  contrôle ne parle ni de pose ni d'amplitude, et c'est sa raison d'être : c'est
  lui qui attrape la contamination des poids automatiques, que trois mesures de
  pose ne montreraient jamais.
- **Écarter doit AUGMENTER l'écart entre bouts de doigts voisins**, et sur les
  trois couples, pas seulement sur leur somme — un doigt qui doublerait son
  voisin passerait sinon inaperçu derrière un total flatteur. Le sens est
  mesuré en phase D, jamais inscrit à la main : un nombre retourné au jugé sur
  la gauche retomberait faux sur la droite, dont la normale de paume est
  inversée. La construction s'arrête si les deux sens rendent le même éventail
  — une sonde qui ne peut pas échouer ne prouve rien.

- **L'INVARIANT : la chair de chaque doigt reste d'un seul tenant.** Deux
  transferts de poids successifs avaient déjà débité le pouce en morceaux cette
  nuit, et c'est Sacha qui l'avait vu à l'œil avant moi.
