#!/usr/bin/env python3
"""
LE TABLEAU DE RÉGRESSION.

Le cahier du chat 2 est explicite : « Après chaque correction : reconstruis en
mode mesure, compare les rapports et REFUSE TOUTE RÉGRESSION d'une pose
précédemment propre. » Comparer deux journaux à l'œil est exactement le genre
de tâche où l'on voit ce qu'on espère : cet outil le fait à ma place, et il
sort en code non nul dès qu'un critère qui passait échoue.

Il lit les lignes `ATLAS_CRITERE` des journaux de construction — celles-là
mêmes qui font échouer le pipeline — et n'invente aucune grandeur.

    python3 outils/comparer-rapports.py etiquette=journal.txt [etiquette=… …]

La dernière colonne est celle qu'on juge ; les précédentes sont ses références.
"""
import os
import re
import sys

LIGNE = re.compile(r"^ATLAS_CRITERE (OK |ÉCHEC) · (.+?) · mesuré (.*?) · exigé (.*)$")


def lire(chemin):
    """{critère: (réussi, mesure)} — la DERNIÈRE occurrence fait foi.

    Un même critère peut être prononcé deux fois dans une construction (une
    pose est remesurée après le nettoyage des transitions). C'est le dernier
    verdict qui décrit le fichier livré.
    """
    out, ordre = {}, []
    for l in open(chemin, encoding="utf-8", errors="replace"):
        m = LIGNE.match(l.rstrip("\n"))
        if m:
            etat, nom, mesure, _seuil = m.groups()
            if nom not in out:
                ordre.append(nom)
            out[nom] = (etat.strip() == "OK", mesure.strip())
    return out, ordre


def court(s, n=34):
    s = s.replace("sommets_dedans", "s").replace("'", "")
    return s if len(s) <= n else s[:n - 1] + "…"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    series, ordre_global = [], []
    for a in argv:
        if "=" not in a:
            print(f"argument attendu sous la forme etiquette=chemin : {a}")
            return 2
        etiq, chemin = a.split("=", 1)
        if not os.path.isfile(chemin):
            print(f"journal introuvable : {chemin}")
            return 2
        d, ordre = lire(chemin)
        series.append((etiq, d))
        for n in ordre:
            if n not in ordre_global:
                ordre_global.append(n)
        print(f"{etiq:<14} {len(d):3d} critères  "
              f"{sum(1 for v in d.values() if v[0]):3d} ✓  "
              f"{sum(1 for v in d.values() if not v[0]):3d} ✗   {chemin}")

    larg = max(len(n) for n in ordre_global)
    print("\n| " + "critère".ljust(larg) + " | "
          + " | ".join(e.center(13) for e, _ in series) + " |")
    print("| " + "-" * larg + " | "
          + " | ".join("-" * 13 for _ in series) + " |")

    regressions, corrections, jamais = [], [], []
    for nom in ordre_global:
        cases = []
        for _e, d in series:
            if nom not in d:
                cases.append("—".center(13))
            else:
                ok, mes = d[nom]
                cases.append(("✓" if ok else "✗ " + court(mes, 11)).center(13))
        print("| " + nom.ljust(larg) + " | " + " | ".join(cases) + " |")
        # Régression : un critère prononcé RÉUSSI dans une série antérieure et
        # ÉCHOUÉ dans la dernière. Un critère absent n'est pas une régression,
        # c'est un trou — et il est listé à part.
        dernier = series[-1][1].get(nom)
        avant = [d[nom][0] for _e, d in series[:-1] if nom in d]
        if dernier is None:
            jamais.append(nom)
        elif any(avant) and not dernier[0]:
            regressions.append((nom, dernier[1]))
        elif avant and not any(avant) and dernier[0]:
            corrections.append(nom)

    print(f"\nCorrigés depuis la première série : {len(corrections)}")
    for n in corrections:
        print(f"  ✓ {n}")
    print(f"Absents de la dernière série : {len(jamais)}")
    for n in jamais:
        print(f"  — {n}")
    print(f"RÉGRESSIONS : {len(regressions)}")
    for n, m in regressions:
        print(f"  ✗ {n} · mesuré {m}")
    if regressions:
        print("\nUne correction qui casse un critère déjà propre n'est pas une "
              "correction.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
