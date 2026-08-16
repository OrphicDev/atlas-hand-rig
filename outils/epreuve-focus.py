#!/usr/bin/env python3
"""Chaque mode ciblé s'arrête-t-il à SA section ?

═══ CE QUE CE TEST EXISTE POUR EMPÊCHER ═══

La sortie des modes ciblés était écrite `if not en_focus("all")`, posée UNE
seule fois, à la fin de la section `Cup`. Elle se déclenchait donc pour tout
focus autre que `all` : `focus=fist` s'arrêtait avant d'avoir touché au poing,
`focus=ok` avant d'avoir cherché l'anneau, `focus=weights` avant la repeinture.
Chacun rendait un `.blend`, un rapport JSON et la ligne « 0 critère obligatoire
en échec ». Quatre des six modes annoncés dans le README étaient des synonymes
de `focus=cup` répondant à côté de la question, avec l'aplomb d'une mesure.

Rien n'aurait planté. Rien n'aurait été rouge. C'est pourquoi ce test lit le
source plutôt que d'attendre qu'un run se plaigne : il n'y a personne pour se
plaindre.

Lancer :  python3 outils/epreuve-focus.py
Sort en code 1 dès qu'un mode n'a pas sa propre sortie, ou qu'une sortie est
placée avant la section qu'elle prétend conclure.
"""
import os
import re
import sys

SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "rig-main.py")

# L'ordre du pipeline, tel qu'il est réellement exécuté — vérifié sur le
# journal d'une reconstruction complète, pas supposé d'après les numéros de
# phase : les contacts sont cherchés à la ligne 116 du journal et le poing à la
# 1092, alors que la « phase D » du poing porte une lettre plus petite.
ORDRE = ["weights", "cup", "ok", "pinky", "fist"]


def main():
    src = open(SOURCE, encoding="utf-8").read().splitlines()

    # ── 1 · les modes déclarés ──────────────────────────────────────────
    m = re.search(r"FOCUS_CONNUS\s*=\s*\(([^)]*)\)", "\n".join(src))
    if not m:
        print("REFUS : FOCUS_CONNUS introuvable dans rig-main.py")
        return 1
    connus = [x.strip().strip('"\'') for x in m.group(1).split(",") if x.strip()]
    attendus = [f for f in connus if f != "all"]
    print(f"modes déclarés : {', '.join(connus)}")

    # ── 2 · une sortie, et une seule, par mode ──────────────────────────
    sorties = {}
    for i, ligne in enumerate(src, 1):
        mm = re.match(r"\s*fin_de_focus\((['\"])([a-z]+)\1\)", ligne)
        if mm:
            nom = mm.group(2)
            sorties.setdefault(nom, []).append(i)

    mauvais = 0
    for f in attendus:
        lignes = sorties.get(f, [])
        if len(lignes) == 1:
            print(f"OK   focus={f:<8} → sortie unique ligne {lignes[0]}")
        elif not lignes:
            print(f"FAUX focus={f:<8} → AUCUNE sortie : ce mode traverse tout "
                  "le script et livre un fichier complet sous un nom de focus")
            mauvais += 1
        else:
            print(f"FAUX focus={f:<8} → {len(lignes)} sorties {lignes} : la "
                  "première gagne, les autres sont mortes")
            mauvais += 1

    inconnus = set(sorties) - set(attendus)
    if inconnus:
        print(f"FAUX sorties pour des modes non déclarés : {sorted(inconnus)}")
        mauvais += 1

    # ── 3 · les sorties suivent l'ordre du pipeline ─────────────────────
    # Une sortie placée AVANT la section qu'elle prétend conclure est
    # exactement le défaut d'origine, sous un autre nom.
    print()
    connues = [f for f in ORDRE if f in sorties and len(sorties[f]) == 1]
    pos = [(f, sorties[f][0]) for f in connues]
    for (fa, la), (fb, lb) in zip(pos, pos[1:]):
        if la < lb:
            print(f"OK   {fa} (l.{la}) sort avant {fb} (l.{lb})")
        else:
            print(f"FAUX {fa} (l.{la}) sort APRÈS {fb} (l.{lb}) — l'ordre des "
                  "sorties ne suit pas celui du pipeline")
            mauvais += 1

    # ── 4 · la contre-épreuve : ce test peut-il tomber ? ────────────────
    # On rejoue la règle sur le source TEL QU'IL ÉTAIT — une seule sortie
    # générique — et on exige qu'elle le refuse. Un test qui accepte aussi
    # bien le code fautif que le code corrigé ne prouve rien.
    print()
    ancien = ['if not en_focus("all"):', '    sys.exit(0)']
    faux = [f for f in attendus
            if not any(re.match(rf"\s*fin_de_focus\(['\"]{f}['\"]\)", l)
                       for l in ancien)]
    if len(faux) != len(attendus):
        print("REFUS : la règle accepte l'ancien code fautif. Elle ne teste "
              "pas ce qu'elle prétend tester.")
        mauvais += 1
    else:
        print(f"la contre-épreuve mord : sur l'ancien source, les {len(faux)} "
              "modes sont tous rendus fautifs")

    # ── 5 · le focus inconnu est refusé, pas ignoré ─────────────────────
    if 'raise SystemExit(f"ATLAS_REFUS focus=' in "\n".join(src):
        print("OK   un focus mal orthographié est refusé, pas silencieusement "
              "traité comme le premier venu")
    else:
        print("FAUX rien ne refuse un focus inconnu : `focus=fst` tomberait "
              "dans la première sortie venue et rendrait « 0 critère en "
              "échec »")
        mauvais += 1

    print()
    print(f"{mauvais} défaut(s).")
    return 1 if mauvais else 0


if __name__ == "__main__":
    sys.exit(main())
