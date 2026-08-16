#!/usr/bin/env python3
"""Le classement des candidats du signe OK, éprouvé hors Blender.

Trois étapes cherchent le signe OK — A ignore l'anneau, B rouvre le trou à
±30 % autour de A, C repart de toute la course avec l'anneau obligatoire — et
c'est ce classement qui décide laquelle est livrée. Une règle qui décide seule
doit pouvoir être prise en défaut sans lancer Blender pendant deux heures.

Les nombres de A et B sont ceux **mesurés** sur la reconstruction complète.
Les autres candidats sont fabriqués pour éprouver les arêtes de la règle.

Lancer :  python3 outils/epreuve-classement-ok.py
Sort en code 1 dès qu'un cas tombe.
"""
import sys

SEUIL_CONTACT_MM = 1.0
SEUIL_FACE = -0.5
SEUIL_ANNEAU_MM = 14.0


def rang(m, anneau_mm):
    """La règle exacte de `_rang_ok` dans `rig-main.py`.

    Quatre critères OBLIGATOIRES d'abord, dans l'ordre du cahier — chacun rend
    1 s'il est violé, jamais une pénalité continue, pour qu'aucune quantité de
    marge sur l'un ne puisse acheter la violation d'un autre. Les trois termes
    continus ne servent qu'à départager des candidats qui violent exactement
    les mêmes critères.
    """
    return (1 if (m.get("inter") or m.get("pen")) else 0,
            1 if m["d"] > SEUIL_CONTACT_MM else 0,
            1 if m["f"] > SEUIL_FACE else 0,
            1 if anneau_mm < SEUIL_ANNEAU_MM else 0,
            max(0.0, m["d"] - SEUIL_CONTACT_MM),
            max(0.0, m["f"] - SEUIL_FACE),
            max(0.0, SEUIL_ANNEAU_MM - anneau_mm))


# ═══ LES DEUX CANDIDATS RÉELS, TELS QUE LA RECONSTRUCTION LES A RENDUS ═══
A = ({"d": 0.81, "f": -0.699, "inter": 90, "pen": 0}, 0.0)
B = ({"d": 1.03, "f": -0.764, "inter": 79, "pen": 0}, 8.1)
# ═══ ET DES CANDIDATS FABRIQUÉS POUR LES ARÊTES ═══
C = ({"d": 0.90, "f": -0.800, "inter": 0, "pen": 0}, 15.0)   # tient tout
D = ({"d": 2.50, "f": -0.800, "inter": 0, "pen": 0}, 16.0)   # propre + anneau
E = ({"d": 0.85, "f": -0.700, "inter": 0, "pen": 0}, 0.0)    # propre + contact
F = ({"d": 0.90, "f": -0.300, "inter": 0, "pen": 0}, 15.0)   # pulpes de biais


def gagne(*candidats):
    return sorted([(rang(*x), nom) for x, nom in candidats])[0][1]


CAS = [
    ("A contre B, les deux MESURÉS", [(A, "A"), (B, "B")], "A",
     "B viole un obligatoire de plus : contact 1,03 mm pour 1,00 exigé, "
     "et cela lui coûte l'anneau de 8,1 mm qu'il était le seul à avoir"),
    ("un C qui tient tout", [(A, "A"), (B, "B"), (C, "C")], "C",
     "aucune violation — c'est la seule sortie du blocage"),
    ("D : propre et annelé, mais le contact raté de 1,5 mm",
     [(A, "A"), (B, "B"), (D, "D")], "D",
     "l'interpénétration passe AVANT le contact dans le cahier : D viole un "
     "critère, A en viole deux. Un état propre qui rate le contact bat une "
     "main qui se traverse 90 fois"),
    ("E : propre et en contact, mais aucun anneau",
     [(A, "A"), (D, "D"), (E, "E")], "E",
     "E et D violent chacun un obligatoire ; E gagne parce que le contact est "
     "classé avant l'anneau"),
    ("C contre D", [(C, "C"), (D, "D")], "C",
     "C tient le contact en plus"),
    ("F : tout bon sauf l'orientation des pulpes",
     [(C, "C"), (F, "F")], "C",
     "des pulpes de biais ne font pas un signe OK, même avec le bon trou"),
    ("l'anneau ne s'achète pas avec de la marge de contact",
     [(({"d": 0.01, "f": -0.99, "inter": 0, "pen": 0}, 0.0), "parfait-sans-trou"),
      (C, "C")], "C",
     "un contact parfait à 0,01 mm et une orientation parfaite ne compensent "
     "PAS l'absence d'anneau : les termes continus n'agissent qu'à égalité "
     "de violations"),
]


def main():
    mauvais = 0
    for nom, candidats, attendu, pourquoi in CAS:
        obtenu = gagne(*candidats)
        ok = obtenu == attendu
        mauvais += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAUX'} {nom}")
        print(f"       → {obtenu} (attendu {attendu}) · {pourquoi}")

    # ═══ LA CONTRE-ÉPREUVE DE LA CONTRE-ÉPREUVE ═══
    #
    # Une épreuve qui ne peut pas tomber ne prouve rien. On casse la règle
    # exprès — on SOMME les violations au lieu de les CLASSER — et on exige
    # qu'un cas au moins change de verdict. Sinon, tous ces cas ne testeraient
    # que le nombre de violations, jamais leur ordre, et le cahier serait
    # respecté par accident.
    #
    # Le premier cas que j'avais écrit ici (D contre A) ne mordait pas : D gagne
    # dans les deux règles, puisqu'il viole aussi MOINS de critères. Il faut un
    # couple où celui qui viole le PLUS de critères gagne quand même, parce que
    # ceux qu'il viole sont classés plus bas.
    def rang_somme(m, an):
        return sum(rang(m, an)[:4])

    # X ne viole QUE l'interpénétration — le premier critère du cahier.
    X = ({"d": 0.50, "f": -0.900, "inter": 50, "pen": 0}, 15.0)
    # Y est propre, et viole les TROIS autres.
    Y = ({"d": 2.00, "f": -0.300, "inter": 0, "pen": 0}, 5.0)
    v_classe = sorted([(rang(*X), "X"), (rang(*Y), "Y")])[0][1]
    v_somme = sorted([(rang_somme(*X), "X"), (rang_somme(*Y), "Y")])[0][1]
    print()
    if v_classe == v_somme:
        print("REFUS : classer et sommer rendent le même verdict sur le couple "
              "qui devait les séparer. Ces cas ne testent pas l'ORDRE.")
        mauvais += 1
    elif v_classe != "Y":
        print(f"REFUS : la règle classée rend {v_classe}, or une main qui se "
              "traverse 50 fois ne peut pas battre une main propre.")
        mauvais += 1
    else:
        print(f"la contre-épreuve mord : classé → {v_classe} (1 violation "
              f"bien placée), sommé → {v_somme} (3 violations, mais basses). "
              "L'ordre du cahier agit, il n'est pas décoratif.")

    print()
    print(f"{len(CAS)} cas, {mauvais} en échec.")
    print("Ce que le classement établit sur les nombres MESURÉS : A gagne, donc")
    print("le OK livré tient 0,81 mm de contact et AUCUN anneau. L'étape C est")
    print("la seule sortie — pas un seuil qu'on abaisserait.")
    return 1 if mauvais else 0


if __name__ == "__main__":
    sys.exit(main())
