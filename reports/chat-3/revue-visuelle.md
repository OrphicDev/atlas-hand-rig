# Revue visuelle — chat 3

Sacha a tranché que c'est moi qui note et que j'argumente. Cette revue s'appuie
sur `outils/revue-visuelle.py`, qui mesure ce qu'une image montre avant qu'on la
juge — parce qu'une note posée à l'œil sur soixante images est une impression,
et que mon œil a déjà été pris en défaut sur ce projet.

**Cette revue n'est pas encore complète.** Les images du rig corrigé sont en
cours de rendu au moment où j'écris. Ce qui suit note ce qui EXISTE et le dit.

---

## Ce que la mesure établit sur les images de `b17e548`

Ce sont les seules images publiées à ce jour, et elles datent d'avant tous les
correctifs. Elles sont donc à lire comme un point de départ, pas comme un
livrable.

| grandeur | résultat |
| --- | --- |
| images mesurées | 60 |
| écrêtées au-delà de 2 % | **aucune** |
| luminance maximale | 0,895 — jamais brûlée |
| **relief local des 8 gros plans** | **0,009 à 0,015 pour 0,020 exigé** |
| pire image | `gros-plan-Hand_Pinky_Thumb-pouce` : amplitude 0,071 ET relief 0,004 |

### Le défaut que le chat 1 avait vu au huitième

Le chat 1 avait relevé **une** image illisible. La mesure du relief local montre
que **les huit gros plans** sont sous le seuil. Ce n'est donc pas une image
ratée : c'est un réglage inadapté à l'échelle.

La cause est physique et je l'ai corrigée : le module dimensionne la source
proportionnellement à la distance, donc son **angle apparent reste 12°** à
toutes les échelles. Sur un plan large c'est doux et juste ; sur un gros plan à
55 mm, les jointures et les plis sont eux-mêmes à l'échelle de ce flou, et
l'ombre qui devrait les révéler s'étale dessus. Les gros plans passent à 4°.

C'est une hypothèse **mesurable**, pas une préférence : le prochain rendu doit
faire monter le relief local au-dessus de 0,020. S'il ne monte pas, la cause est
ailleurs et je le dirai.

---

## Ma note, et ce qu'elle vaut

**Je ne donne pas encore de note sur le rig corrigé** — il serait malhonnête de
noter des images que je n'ai pas vues. Ce que je peux noter aujourd'hui :

### Les images de `b17e548` — **4/10**

- **ce qui va** : exposition tenue, aucune image brûlée ni bouchée sur les
  soixante, cadrage correct sur les plans larges, le clay ne cache rien ;
- **ce qui ne va pas** : les huit gros plans — c'est-à-dire *toutes* les images
  censées prouver les contacts — n'ont pas assez de modelé pour qu'on juge un
  contact. Une preuve qu'on ne peut pas lire n'est pas une preuve ;
- **ce qui manque** : aucun overlay des sommets traversants, donc « 211
  sommets » restait un nombre sans lieu ; aucune vue avant/après à caméra
  identique ; aucun wireframe.

Un 4 et pas moins parce que la moitié technique est saine — l'exposition et le
cadrage tiennent. Un 4 et pas plus parce que la fonction même de ces images,
montrer si deux chairs se touchent proprement, n'est pas remplie.

### Ce qu'il faudra pour dépasser 8

1. le relief local au-dessus de 0,020 sur les huit gros plans ;
2. les overlays rouges avant/après, à caméra strictement identique ;
3. les six séquences de transition jouant les **vraies** actions ;
4. les planches de poids sur le thénar et la base de l'index ;
5. et surtout : que les poses montrées soient celles d'un rig qui passe ses
   critères. On ne note pas la photographie d'un défaut.

---

## Ce que je refuse de faire

Noter les images de `b17e548` en les présentant comme le travail du chat 3.
Elles datent d'avant les correctifs, elles montrent un rig dont je sais qu'il
est faux, et les publier comme preuves reviendrait à ce que ce dépôt a fait au
chat 1 : appeler « validé » ce que l'instrument ne regardait pas.
