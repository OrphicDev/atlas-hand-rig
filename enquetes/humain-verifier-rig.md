---
sujet: humain-verifier-rig
date: 2026-08-15
---

## 1. CE QUE JE CROIS SAVOIR

Le tutoriel de correction exige une commande qui vérifie le `.blend` livré
**sans reconstruire le maillage**, et que le dépôt public soit jugeable depuis
un clone propre. Le maillage de base pèse 47 Mo et n'est pas versionné : sans
ce script, personne ne peut contrôler le rig sans le télécharger.

Je crois qu'un contrôle rejouant les poses de la bibliothèque et remesurant les
contacts suffit à trancher. C'est à vérifier : un contrôle qui ne mesure pas la
même chose que la construction ne prouve rien.

## 2. CE QUE J'AI VÉRIFIÉ

- **Les poses sont dans le fichier**, sous forme d'actions marquées en assets
  (`Hand_Neutral`, `Hand_Fist`, `Hand_Pinch`, `Hand_OK`, `Hand_Pinky_Thumb`…).
  Elles sont donc rejouables sans rien recalculer.
- **Les tolérances doivent être les mêmes des deux côtés.** Le script de
  construction distingue un contact d'une pénétration par deux conditions :
  profondeur supérieure à 0,5 mm, et distance de repos supérieure à 14 mm entre
  les deux sommets. Les reprendre à l'identique est ce qui rend les deux
  mesures comparables ; les changer, même « en mieux », rendrait le contrôle
  muet sur ce que la construction déclare.
- **Le seuil de 0,5 mm a été contre-éprouvé** côté construction : une fermeture
  pleine sans écartement rend 780 sommets traversants. Il voit donc les vraies
  fautes.

- **CE CONTROLE NE REGARDAIT PAS LA OU ETAIENT LES DEFAUTS.** Ma phrase du
  debut — « un controle qui ne mesure pas la meme chose que la construction ne
  prouve rien » — etait juste, et je ne l'avais pas appliquee a moi-meme.

  Mesure : lance sur `RIG_Hand.L-NON-VALIDE.blend`, ce verificateur rendait
  « 22 reussis, 9 echoues ». Etendu aux grandeurs que la construction mesure
  deja, il rend sur LE MEME FICHIER cinq echecs de plus :

      Cup · la paume se voute               −10,83 mm   l'arc S'APLATIT
      Cup · la paume se resserre            +14,04 mm   elle S'ELARGIT
      Cup · l'auriculaire rejoint le pouce   −0,88 mm
      Cup · le trajet ne repart jamais       +1,25 mm   il repart
      le poing se ferme completement           0,55

  Ce sont AU CHIFFRE PRES les valeurs que les sondes avaient trouvees a la
  main. Le rig n'etait pas moins casse : le verificateur ne regardait pas.

- **`is_valid` ne dit rien de ce qu'un driver pilote.** Le depot a vecu
  25 drivers verts dont la rotation restait a 0,00 degre parce qu'ils
  n'etaient pas EVALUES. Une contre-epreuve fonctionnelle a ete ajoutee : on
  applique 1 a chaque propriete et on mesure si le maillage BOUGE.

## 3. CE QUE LA GÉOMÉTRIE DIT

Sur le rig courant, le contrôle doit retrouver : contact index-pouce à 0,75 mm,
contact auriculaire-pouce à 0,14 mm, retour au repos à 0,0000 mm, course du
poing de l'ordre de 120 mm, et **26 sommets traversants entre l'éminence thénar
et la base de l'index** dans la pose auriculaire-pouce.

Si le contrôle rendait des nombres franchement différents sur le même fichier,
c'est lui qui serait faux — pas le rig.

## 4. CE QUI RESTE INCERTAIN

**Les empreintes seront-elles retrouvées à l'identique ?** Le script de
construction les détermine à partir du centre de la paume et des normales
déformées ; le contrôle doit refaire ce calcul sans les mêmes variables en
mémoire.
→ se tranche par comparaison : les distances de contact rendues par le contrôle
doivent coller à celles du rapport de construction. Un écart franc signalerait
que les deux scripts ne regardent pas la même zone de peau.

## 5. CE QUI RÉFUTERAIT
- **Un verificateur qui ne mesure pas une grandeur ne peut pas la declarer
  bonne.** Tout critere du cahier absent de ce script est un critere NON
  MESURE, et la matrice d'acceptation le liste a part au lieu de le passer
  sous silence. Un bloc absent n'est pas un bloc reussi — c'est la faute par
  laquelle ce depot s'est declare valide au chat 1.


- **Un contrôle qui passe sur un rig connu pour échouer.** Le fichier livré
  porte un défaut mesuré et documenté : 26 sommets traversants dans la pose
  auriculaire-pouce. Si le contrôle le déclarait bon, il serait inutilisable —
  c'est le test le plus important de ce script, et il ne demande aucun
  téléchargement.
- **Un contrôle qui passe sur une main qui ne bouge pas.** D'où le critère
  « le rig bouge vraiment » : une main inerte revient toujours exactement à sa
  pose de repos, et j'ai déjà validé un rig immobile de cette façon.
- **L'INVARIANT : le contrôle ne modifie jamais le fichier.** Il ouvre, mesure,
  et sort. Rien n'est sauvegardé, rien n'est écrasé — sans quoi une commande de
  vérification pourrait détruire ce qu'elle est censée juger.
