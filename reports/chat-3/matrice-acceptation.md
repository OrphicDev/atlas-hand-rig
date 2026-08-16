# Matrice d'acceptation

Source : `journal-generation-precedent.txt`  
Critères lus : **58** — **32 réussis**, **26 échoués**

| bloc | critère | mesuré | exigé | |
| --- | --- | --- | --- | :-: |
| repos | Cup · retour exact au repos | 0.0000 mm | < 0,01 mm | ✓ |
| repos | retour exact au repos | 0.0000 mm | < 0,01 mm | ✓ |
| poids | aucun sommet partagé entre deux rayons non vo… | 0 | 0 sommet | ✓ |
| poids | aucune contamination hors des commissures | 0 | 0 sommet | ✓ |
| Spread | Hand_Spread_Min · aucune auto-intersection | aucune | aucune | ✓ |
| Cup | Cup · la paume se voûte | +6.71 mm | ≥ +6 mm de flèche | ✓ |
| Cup | Cup · la paume se resserre | -10.79 mm | ≤ −6 mm de largeur | ✓ |
| Cup | Cup · l'auriculaire rejoint le pouce | -4.94 mm | ≤ −4 mm | ✓ |
| Cup | Cup · le resserrement ne repart jamais en arr… | -0.48 mm | ≤ 0,50 mm par pas | ✓ |
| Cup | Cup · la voûte ne s'effondre jamais en chemin | -0.32 mm | ≤ 0,50 mm par pas | ✓ |
| Cup | Cup · aucune auto-intersection sur les 21 pas | 0 | 0 sommet | ✓ |
| Cup | la paume creuse se creuse vraiment | -0.8 mm | ≥ 6 mm de plus qu'au repos | ✗ |
| Pinch | Hand_Pinch · les pulpes se touchent | 1.06 mm | ≤ 1.00 mm | ✗ |
| Pinch | Hand_Pinch · les pulpes se font face | -0.788 | ≤ -0,50 | ✓ |
| Pinch | Hand_Pinch · aucune interpénétration | {'dans_les_pulpes': 0, 'dans_la_main_entiere': 0} | 0 sommet, pulpes ET main … | ✓ |
| Pinch | Hand_Pinch · aucune auto-intersection | aucune | aucune | ✓ |
| Pinch | transition Neutral→Hand_Pinch · aucune auto-i… | aucune | aucune à chaque étape | ✓ |
| OK | Hand_OK · les pulpes se touchent | 2.18 mm | ≤ 1.00 mm | ✗ |
| OK | Hand_OK · les pulpes se font face | -0.633 | ≤ -0,50 | ✓ |
| OK | Hand_OK · aucune interpénétration | {'dans_les_pulpes': 0, 'dans_la_main_entiere': 148} | 0 sommet, pulpes ET main … | ✗ |
| OK | Hand_OK · aucune auto-intersection | [{'entre': 'thumb/index', 'sommets_dedans': 95}, {'… | aucune | ✗ |
| OK | transition Neutral→Hand_OK · aucune auto-inte… | {'0.6': [{'entre': 'thumb/index', 'sommets_dedans':… | aucune à chaque étape | ✗ |
| OK | Hand_OK · aucune auto-intersection après nett… | [{'entre': 'thumb/index', 'sommets_dedans': 96}, {'… | aucune | ✗ |
| OK | le diamètre utile distingue l'anneau du pince… | OK 0.0 mm contre Pinch 19.1 mm | au moins 3 mm de plus pou… | ✗ |
| OK | l'anneau du OK est lisible | 0.0 mm | ≥ 14 mm d'ouverture | ✗ |
| Pinky_Thumb | Hand_Pinky_Thumb · les pulpes se touchent | 8.20 mm | ≤ 1.00 mm | ✗ |
| Pinky_Thumb | Hand_Pinky_Thumb · les pulpes se font face | -0.871 | ≤ -0,50 | ✓ |
| Pinky_Thumb | Hand_Pinky_Thumb · aucune interpénétration | {'dans_les_pulpes': 0, 'dans_la_main_entiere': 1495} | 0 sommet, pulpes ET main … | ✗ |
| Pinky_Thumb | Hand_Pinky_Thumb · aucune auto-intersection | [{'entre': 'thumb/index', 'sommets_dedans': 646}, {… | aucune | ✗ |
| Pinky_Thumb | transition Neutral→Hand_Pinky_Thumb · aucune … | {'0.2': [{'entre': 'thumb/index', 'sommets_dedans':… | aucune à chaque étape | ✗ |
| Pinky_Thumb | Hand_Pinky_Thumb · aucune auto-intersection a… | [{'entre': 'thumb/index', 'sommets_dedans': 592}, {… | aucune | ✗ |
| Fist | le poing se ferme complètement sans traversée | 0.6 | Fist = 1.0 | ✗ |
| Fist | Hand_Fist · aucune auto-intersection | [{'entre': 'thumb/index', 'sommets_dedans': 282}, {… | aucune | ✗ |
| Fist | Hand_Fist_25 · aucune auto-intersection | aucune | aucune | ✓ |
| Fist | Hand_Fist_50 · aucune auto-intersection | aucune | aucune | ✓ |
| Fist | Hand_Fist_75 · aucune auto-intersection | [{'entre': 'thumb/index', 'sommets_dedans': 769}, {… | aucune | ✗ |
| Fist | transition Neutral→Hand_Fist · aucune auto-in… | {'0.2': [{'entre': 'thumb/index', 'sommets_dedans':… | aucune à chaque étape | ✗ |
| Fist | Hand_Fist · aucune auto-intersection après ne… | [{'entre': 'thumb/index', 'sommets_dedans': 220}, {… | aucune | ✗ |
| Fist | compression de index au poing · minimum | 0.3708 | ≥ 0,25 | ✓ |
| Fist | compression de index au poing · percentile 1 % | 0.7405 | ≥ 0,50 | ✓ |
| Fist | compression de middle au poing · minimum | 0.2696 | ≥ 0,25 | ✓ |
| Fist | compression de middle au poing · percentile 1… | 0.7481 | ≥ 0,50 | ✓ |
| Fist | compression de ring au poing · minimum | 0.216 | ≥ 0,25 | ✗ |
| Fist | compression de ring au poing · percentile 1 % | 0.6716 | ≥ 0,50 | ✓ |
| Fist | compression de pinky au poing · minimum | 0.2281 | ≥ 0,25 | ✗ |
| Fist | compression de pinky au poing · percentile 1 % | 0.5701 | ≥ 0,50 | ✓ |
| Fist | compression de thumb au poing · minimum | 0.098 | ≥ 0,25 | ✗ |
| Fist | compression de thumb au poing · percentile 1 % | 0.4356 | ≥ 0,50 | ✗ |
| Point | Hand_Point · aucune auto-intersection | [{'entre': 'thumb/index', 'sommets_dedans': 154}, {… | aucune | ✗ |
| Point | transition Neutral→Hand_Point · aucune auto-i… | {'0.5': [{'entre': 'index/middle', 'sommets_dedans'… | aucune à chaque étape | ✗ |
| Point | Hand_Point · aucune auto-intersection après n… | [{'entre': 'thumb/index', 'sommets_dedans': 151}, {… | aucune | ✗ |
| transitions | transition Neutral→Hand_Cupped · aucune auto-… | aucune | aucune à chaque étape | ✓ |
| drivers | tous les drivers sont valides | aucun invalide | aucun invalide | ✓ |
| hors matrice | Hand_Neutral · aucune auto-intersection | aucune | aucune | ✓ |
| hors matrice | Hand_Relaxed · aucune auto-intersection | aucune | aucune | ✓ |
| hors matrice | Hand_Open · aucune auto-intersection | aucune | aucune | ✓ |
| hors matrice | Hand_Cupped · aucune auto-intersection | aucune | aucune | ✓ |
| hors matrice | Pinch et OK sont deux gestes distincts | 74.9 mm | > 15 mm d'écart | ✓ |

## Blocs que ce journal ne couvre pas

Un bloc absent n'est pas un bloc réussi. Il n'a pas été mesuré, et le déclarer vert serait la faute que cette matrice existe pour empêcher.

- **correctifs**
- **images**
