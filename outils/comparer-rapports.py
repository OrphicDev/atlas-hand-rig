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


NOMBRE = re.compile(r"-?\d+(?:[.,]\d+)?")


def valeur(texte):
    """Le premier nombre d'une mesure, ou None si elle n'en est pas une."""
    m = NOMBRE.search(texte or "")
    return float(m.group(0).replace(",", ".")) if m else None


def sens(seuil):
    """+1 si monter est un progrès, −1 si descendre l'est, 0 si indécidable.

    ═══ LA DIRECTION SE LIT, ELLE NE SE DEVINE PAS ═══
    Le seuil imprimé la porte : « ≤ 1,00 mm » dit que descendre est bon,
    « > 20 mm » dit l'inverse. Sans cette lecture, je ne pourrais que comparer
    des nombres sans savoir lequel est meilleur — et je l'aurais supposé.
    """
    s = (seuil or "").strip()
    if valeur(s) is None:
        return 0
    if s.startswith("≤") or s.startswith("<"):
        return -1
    if s.startswith("≥") or s.startswith(">"):
        return +1
    return 0


def lire(chemin):
    """{critère: (réussi, mesure, seuil)} — la DERNIÈRE occurrence fait foi.

    Un même critère peut être prononcé deux fois dans une construction (une
    pose est remesurée après le nettoyage des transitions). C'est le dernier
    verdict qui décrit le fichier livré.
    """
    out, ordre = {}, []
    for l in open(chemin, encoding="utf-8", errors="replace"):
        m = LIGNE.match(l.rstrip("\n"))
        if m:
            etat, nom, mesure, seuil = m.groups()
            if nom not in out:
                ordre.append(nom)
            out[nom] = (etat.strip() == "OK", mesure.strip(), seuil.strip())
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

    regressions, corrections, jamais, aggravations = [], [], [], []
    for nom in ordre_global:
        cases = []
        for _e, d in series:
            if nom not in d:
                cases.append("—".center(13))
            else:
                ok, mes, _s = d[nom]
                cases.append(("✓" if ok else "✗ " + court(mes, 11)).center(13))
        print("| " + nom.ljust(larg) + " | " + " | ".join(cases) + " |")
        # Régression : un critère prononcé RÉUSSI dans une série antérieure et
        # ÉCHOUÉ dans la dernière. Un critère absent n'est pas une régression,
        # c'est un trou — et il est listé à part.
        dernier = series[-1][1].get(nom)
        avant = [d[nom] for _e, d in series[:-1] if nom in d]
        if dernier is None:
            jamais.append(nom)
            continue
        if any(a[0] for a in avant) and not dernier[0]:
            regressions.append((nom, dernier[1]))
        elif avant and not any(a[0] for a in avant) and dernier[0]:
            corrections.append(nom)
        # ═══ UN CHIFFRE QUI EMPIRE NE DOIT PAS SORTIR SILENCIEUX ═══
        # Première version : ce tableau annonçait « RÉGRESSIONS : 0 » pendant
        # que Hand_OK passait de 1,04 à 2,29 mm. Sa définition était celle du
        # cahier au mot près — « une pose PRÉCÉDEMMENT PROPRE » — donc un
        # critère déjà en échec pouvait doubler sans rien déclencher. Un outil
        # qui rassure à tort est pire que pas d'outil.
        _s = sens(dernier[2])
        _v = valeur(dernier[1])
        if _s and _v is not None and not dernier[0]:
            _av = [valeur(a[1]) for a in avant if valeur(a[1]) is not None]
            if _av:
                meilleur = max(_av) if _s > 0 else min(_av)
                if (_v - meilleur) * _s < 0:
                    aggravations.append((nom, meilleur, _v, dernier[2]))

    print(f"\nCorrigés depuis la première série : {len(corrections)}")
    for n in corrections:
        print(f"  ✓ {n}")
    print(f"Absents de la dernière série : {len(jamais)}")
    for n in jamais:
        print(f"  — {n}")
    print(f"Aggravations chiffrées (critère déjà en échec, mesure qui empire) :"
          f" {len(aggravations)}")
    for n, avant_v, apres_v, s in aggravations:
        print(f"  ↓ {n} · {avant_v:g} → {apres_v:g} · exigé {s}")
    print(f"RÉGRESSIONS : {len(regressions)}")
    for n, m in regressions:
        print(f"  ✗ {n} · mesuré {m}")
    if regressions:
        print("\nUne correction qui casse un critère déjà propre n'est pas une "
              "correction.")
        return 2
    if aggravations:
        print("\nAucun critère propre n'a été cassé, mais une mesure a empiré. "
              "Ce n'est pas bloquant — c'est à justifier.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
