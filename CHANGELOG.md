# CHANGELOG

## wip/chat-1-honest-probe — checkpoint de transmission (NON VALIDE)

Base : `b17e54806f942736e47c4dcfd477a91b7fd6f262`
SHA de ce checkpoint : `3454e5c61fb6f80acd5cec7a6286220c229cc03e`

**Aucun `.blend` de cette branche ne reflète ces corrections.** Le
`RIG_Hand.L-NON-VALIDE.blend` présent date de la base et n'a pas été remplacé.

### L'instrument, d'abord

- sonde d'auto-intersection portée de **5 à 15 couples** de familles, comptés
  **dans les deux sens** — l'ancienne ne voyait que **22 %** des traversées
  (672 sur 3 009) ;
- groupes non-os (`ZONES_ARTICULAIRES`) exclus du classement par famille :
  203 sommets étaient mal attribués ;
- `verifier-rig.py` contrôle désormais les **13 poses** et les **6 transitions**
  à 11 étapes, au lieu de 4 poses et aucune transition ;
- une pose absente du fichier est un **échec**, plus un silence ;
- le vérificateur ne force plus le mode de rotation des os : il ne modifie plus
  l'objet qu'il juge.

### Ce que les scripts ne peuvent plus cacher

- `--python-exit-code 1` documenté : les scripts sortaient en **code 0 après un
  plantage** ;
- sorties déstamponnées : trois exécutions de 11, 16 et 34 minutes n'avaient
  écrit **aucun octet**, rendant un blocage indiscernable d'un calcul long.

### Anatomie — écrit, pas encore validé

- fermeture en **cascade MCP → PIP → DIP**, par écrêtage des butées ;
- `Hand_Pinch` et `Hand_OK` séparés — ils étaient **la même action** (0,0 mm
  d'écart, empreinte identique) ;
- **mesure de l'anneau** du signe OK et du **creux palmaire** ;
- nettoyeur générique de pose appliqué aux 13 poses ;
- bases métacarpiennes distribuées en arc, divergence des doigts cherchée par
  la mesure.

### Sauvé de `/tmp`

- `atelier/eclairage.py` — lumière rasante, key à 75° de la normale,
  **0 % d'écrêtage sur 18 images**. Prouvé isolément, **jamais intégré** au
  pipeline ;
- les trois rapports d'agents, l'audit de collisions et 18 rendus de preuve.

### Réfuté

Le signalement « gros plan paume de `Hand_OK` vide » : mesuré deux fois,
**82,5 % de sujet**, contraste normal. Aucune des 60 images n'est vide ni
surexposée.
