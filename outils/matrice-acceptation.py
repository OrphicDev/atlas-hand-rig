#!/usr/bin/env python3
"""
LA MATRICE D'ACCEPTATION (§12.3) — produite depuis les journaux, jamais à la main.

Le cahier donne une matrice de douze blocs. La recopier à la main dans un
rapport serait exactement la faute qui a produit « Hand_Point 978 sommets » là
où le vérificateur en compte 1 528 : un nombre juste au moment où on l'écrit,
faux dès la reconstruction suivante, et que plus personne ne revérifie.

Cet outil la construit depuis les lignes `ATLAS_CRITERE` d'un journal — celles
qui font échouer le pipeline. Il n'invente aucune grandeur et n'en arrondit
aucune.

    python3 outils/matrice-acceptation.py journal.txt [sortie.md]
"""
import os
import re
import sys

LIGNE = re.compile(r"^ATLAS_CRITERE (OK |ÉCHEC) · (.+?) · mesuré (.*?) · exigé (.*)$")

# Les douze blocs du §12.3, et les motifs qui rattachent un critère à son bloc.
# L'ordre est celui du cahier : il fait autorité, pas mon idée de la lisibilité.
BLOCS = [
    ("repos", ("retour exact au repos", "retour au repos")),
    ("poids", ("poids", "influences", "contamination", "rayons non voisins",
               "repeinture")),
    ("Spread", ("écartement", "eventail", "Spread")),
    ("Cup", ("Cup ·", "paume creuse", "creuse vraiment")),
    ("Pinch", ("Hand_Pinch",)),
    ("OK", ("Hand_OK", "anneau", "diamètre utile")),
    ("Pinky_Thumb", ("Hand_Pinky_Thumb",)),
    ("Fist", ("Hand_Fist", "poing", "fermeture", "compression de")),
    ("Point", ("Hand_Point",)),
    ("transitions", ("transition", "Neutral_to_")),
    ("drivers", ("driver", "propriété pilote")),
    ("correctifs", ("correctif", "shape key", "os correctifs")),
    ("images", ("écrêtée", "key rase", "relief", "image")),
]


def lire(chemin):
    """{critère: (réussi, mesure, seuil)} — la DERNIÈRE occurrence fait foi.

    Une pose est remesurée après le nettoyage des transitions : c'est ce second
    verdict qui décrit le fichier livré, pas le premier.
    """
    out, ordre = {}, []
    for l in open(chemin, encoding="utf-8", errors="replace"):
        m = LIGNE.match(l.rstrip("\n"))
        if not m:
            continue
        etat, nom, mesure, seuil = m.groups()
        if nom not in out:
            ordre.append(nom)
        out[nom] = (etat.strip() == "OK", mesure.strip(), seuil.strip())
    return out, ordre


def bloc_de(nom):
    for bloc, motifs in BLOCS:
        if any(m in nom for m in motifs):
            return bloc
    return "hors matrice"


def court(s, n=52):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    journal = argv[0]
    sortie = argv[1] if len(argv) > 1 else None
    if not os.path.isfile(journal):
        print(f"journal introuvable : {journal}")
        return 2

    criteres, ordre = lire(journal)
    if not criteres:
        # ═══ UN JOURNAL SANS CRITÈRE N'EST PAS UNE MATRICE VIDE ═══
        # Rendre un tableau tout vert ici serait le pire résultat possible : il
        # se lirait comme « tout passe » alors qu'il signifie « je n'ai rien lu ».
        print(f"aucune ligne ATLAS_CRITERE dans {journal} — ce n'est pas une "
              f"matrice vide, c'est un journal qui n'a rien mesuré")
        return 2

    par_bloc = {}
    for nom in ordre:
        par_bloc.setdefault(bloc_de(nom), []).append(nom)

    lignes = ["# Matrice d'acceptation", "",
              f"Source : `{os.path.basename(journal)}`  ",
              f"Critères lus : **{len(criteres)}** — "
              f"**{sum(1 for v in criteres.values() if v[0])} réussis**, "
              f"**{sum(1 for v in criteres.values() if not v[0])} échoués**",
              "",
              "| bloc | critère | mesuré | exigé | |",
              "| --- | --- | --- | --- | :-: |"]
    ordre_blocs = [b for b, _ in BLOCS] + ["hors matrice"]
    for bloc in ordre_blocs:
        for nom in par_bloc.get(bloc, []):
            ok, mesure, seuil = criteres[nom]
            lignes.append(f"| {bloc} | {court(nom, 46)} | {court(mesure)} | "
                          f"{court(seuil, 26)} | {'✓' if ok else '✗'} |")

    manquants = [b for b, _ in BLOCS if b not in par_bloc]
    if manquants:
        lignes += ["", "## Blocs que ce journal ne couvre pas", "",
                   "Un bloc absent n'est pas un bloc réussi. Il n'a pas été "
                   "mesuré, et le déclarer vert serait la faute que cette "
                   "matrice existe pour empêcher.", ""]
        lignes += [f"- **{b}**" for b in manquants]

    texte = "\n".join(lignes) + "\n"
    print(texte)
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            f.write(texte)
        print(f"écrit : {sortie}")

    return 2 if (manquants or any(not v[0] for v in criteres.values())) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
