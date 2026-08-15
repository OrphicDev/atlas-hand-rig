# Playblasts — ATTENTION À CE QU'ILS MONTRENT

Ces six séquences sont rendues depuis `RIG_Hand.L-NON-VALIDE.blend`, **le
fichier de `b17e548`**. Elles montrent donc les défauts de CE rig-là, pas
l'effet des correctifs du chat 2 — aucun `.blend` ne les porte encore.

Elles ont deux raisons d'exister :

1. le paquet d'audit portait « Transition videos: AUCUNE » depuis le chat 1,
   et l'outil qui devait les produire n'avait jamais tourné ;
2. une traversée à `t = 0,8` se lit en une seconde sur une animation, et se
   cherche dix minutes dans un JSON.

## Ce ne sont pas des MP4, et ce n'est pas un choix

Mesuré : cette build de Blender 5.1.2 est compilée **sans FFmpeg** — son
énumération de formats vaut `(AVIF, JPEG, OPEN_EXR, PNG, WEBP, BMP, CINEON,
DPX, IRIS, JPEG2000, HDR, TARGA, TARGA_RAW, TIFF)`, aucun conteneur vidéo. La
machine n'a pas non plus de binaire `ffmpeg`. Un playblast reste une SÉQUENCE
du geste : elle est écrite en PNG, et `playblasts.html` l'anime sans aucun
codec.

## Mesuré sur les 150 images

| | |
| --- | --- |
| images | 150 (6 × 25) |
| sujet | 26 à 31 % du cadre |
| luminance moyenne | 0,55 |
| luminance maximale | 0,835 |
| **écrêtage** | **0,000 %** |

C'est la première exécution du module `atelier/eclairage.py` dans une chaîne
réelle depuis qu'il existe. Il tient ce qu'il annonçait isolément.
