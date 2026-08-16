# Transitions — ce que ces sequences montrent, et ce qu'elles ne montrent pas

150 images, six sequences de 25, rendues depuis le `.blend` courant.

## LE REPLI EST DECLARE, ET IL FAUT LE LIRE

Chaque sequence porte dans son journal :

> ATLAS_PLAYBLAST_SANS_ACTION <pose> — interpolation lineaire de repli,
> ce n'est PAS le mouvement que le verificateur juge

Ce `.blend` date d'avant les vraies actions de transition. Le playblast est
donc retombe sur l'interpolation lineaire, et il l'a ANNONCÉ a chaque
sequence plutot que de la faire passer pour la bonne.

C'est le mécanisme precis par lequel ce projet s'est déclaré validé au
chat 1 : une mesure dégradée qui passe pour la bonne parce que rien ne la
signale. Ici elle se signale.

## Ce que ces sequences valent donc

Elles montrent le trajet que le VÉRIFICATEUR mesurait jusqu ici — la droite
entre le repos et la pose. Elles sont utiles comme repere et comme preuve de
la chaîne de rendu. Elles ne montrent PAS le contournement que les vraies
actions produisent, parce qu'aucune action n existe dans ce fichier.

Le pouce d'un poing passe par l'EXTÉRIEUR. La droite coupe le coin et le fait
traverser l'index vers t = 0,8. C est visible sur la sequence du poing, et
c est exactement le defaut que les vraies actions corrigent.
