"""
LE PORTILLON — on ne construit rien sans avoir cherché d'abord.

╔══════════════════════════════════════════════════════════════════════════╗
║  POURQUOI CE FICHIER EXISTE                                              ║
╚══════════════════════════════════════════════════════════════════════════╝

Le 14 août 2026, Sacha a relevé deux fautes sur la main :

  · les phalanges se courbent au lieu de rester droites entre les
    articulations — un doigt n'est pas un tentacule ;
  · le pouce se ferme dans le mauvais plan — son axe de flexion est tourné
    d'environ 90° par rapport aux quatre autres doigts.

Les deux étaient VÉRIFIABLES avant de construire. Aucune des deux ne demandait
une mesure : elles demandaient de connaître, ou d'aller chercher, l'anatomie de
la main. J'ai construit d'abord.

Sa consigne : « rends ça obligatoire et non à la lecture uniquement ». Le dépôt
le dit déjà autrement — UNE LOI SANS MACHINE EST UN VŒU. Écrire « je chercherai
avant » dans un CLAUDE.md n'a jamais empêché personne de ne pas le faire.

Donc : ce module LÈVE. Tout script de `objets/` doit appeler `exiger(sujet)`
avant sa première ligne de travail, et l'appel échoue tant qu'il n'existe pas,
dans `enquetes/<sujet>.md`, une enquête complète. Pas de contournement, pas de
mode silencieux, pas de variable d'environnement pour passer outre : si on veut
sauter l'enquête, il faut supprimer l'appel — et `outils/garde.py` refuse alors
le dépôt.

╔══════════════════════════════════════════════════════════════════════════╗
║  CE QU'EST UNE ENQUÊTE                                                   ║
╚══════════════════════════════════════════════════════════════════════════╝

Cinq sections, toutes obligatoires, toutes non vides :

  1. CE QUE JE CROIS SAVOIR     — dit à voix haute, pour pouvoir être démenti.
  2. CE QUE J'AI VÉRIFIÉ        — au moins deux vérifications nommées. Une
                                  connaissance qu'on n'a pas confrontée n'est
                                  pas une vérification, c'est un souvenir.
  3. CE QUE LA GÉOMÉTRIE DIT    — la mesure sur CE maillage. Elle peut démentir
                                  l'anatomie : c'est même son intérêt.
  4. CE QUI RESTE INCERTAIN     — les questions à poser à Sacha AVANT de faire,
                                  ou « néant » assumé.
  5. CE QUI RÉFUTERAIT          — le contrôle qui montrerait que j'ai tort. Sans
                                  lui, on ne construit pas, on espère.

La cinquième est la plus importante. Le poing était exactement ça : un contrôle
qui a montré deux fautes qu'une main ouverte cachait. Il aurait dû être prévu
comme épreuve, pas découvert comme accident.
"""

import os, re, sys, datetime

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "enquetes")

SECTIONS = (
    ("croire", "CE QUE JE CROIS SAVOIR", 120),
    ("verifie", "CE QUE J'AI VÉRIFIÉ", 200),
    ("geometrie", "CE QUE LA GÉOMÉTRIE DIT", 120),
    ("incertain", "CE QUI RESTE INCERTAIN", 40),
    ("refute", "CE QUI RÉFUTERAIT", 160),
)

MODELE = """---
sujet: {sujet}
date: {date}
---

## 1. CE QUE JE CROIS SAVOIR

## 2. CE QUE J'AI VÉRIFIÉ
<!-- au moins deux vérifications nommées, chacune sur une ligne « - » -->

## 3. CE QUE LA GÉOMÉTRIE DIT

## 4. CE QUI RESTE INCERTAIN
<!-- les questions à poser AVANT de faire, ou « néant » -->

## 5. CE QUI RÉFUTERAIT
"""


class PortillonFerme(RuntimeError):
    pass


def chemin(sujet):
    return os.path.join(DOSSIER, sujet + ".md")


def _corps(texte, titre):
    m = re.search(r"^##\s*\d+\.\s*" + re.escape(titre) + r"\s*$(.*?)(?=^##\s|\Z)",
                  texte, re.M | re.S)
    if m is None:
        return None
    corps = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    return corps.strip()


def defauts(sujet):
    """La liste de ce qui manque. Vide = l'enquête tient."""
    p = chemin(sujet)
    if not os.path.exists(p):
        return [f"aucune enquête : {os.path.relpath(p, RACINE)} n'existe pas"]
    texte = open(p, encoding="utf-8").read()
    manques = []
    for cle, titre, minimum in SECTIONS:
        corps = _corps(texte, titre)
        if corps is None:
            manques.append(f"section « {titre} » absente")
        elif len(corps) < minimum:
            manques.append(f"section « {titre} » trop courte "
                           f"({len(corps)} caractères, il en faut {minimum})")
    v = _corps(texte, "CE QUE J'AI VÉRIFIÉ") or ""
    if len([l for l in v.splitlines() if l.strip().startswith("-")]) < 2:
        manques.append("« CE QUE J'AI VÉRIFIÉ » doit lister au moins DEUX "
                       "vérifications, une par ligne commençant par « - »")
    r = _corps(texte, "CE QUI RÉFUTERAIT") or ""
    if len([l for l in r.splitlines() if l.strip().startswith("-")]) < 2:
        manques.append("« CE QUI RÉFUTERAIT » doit lister au moins DEUX "
                       "contrôles, un par ligne commençant par « - »")
    if "invariant" not in r.lower():
        manques.append("« CE QUI RÉFUTERAIT » ne nomme aucun INVARIANT — un "
                       "contrôle qui ne parle pas du changement, et qui dirait "
                       "si l'objet a cessé d'être lui-même (maille déchirée, "
                       "volume perdu, morceau détaché)")
    q = _corps(texte, "CE QUI RESTE INCERTAIN") or ""
    if "?" in q and "→" not in q:
        manques.append("des questions sont posées sans réponse : il faut les "
                       "poser à Sacha et écrire sa réponse après « → », ou les "
                       "retirer")
    return manques


def exiger(sujet):
    """
    LE PORTILLON. À appeler AVANT la première ligne de travail d'un script
    d'objet. Lève tant que l'enquête n'est pas complète.
    """
    manques = defauts(sujet)
    if not manques:
        journal(sujet, "ouvert")
        return chemin(sujet)
    modele = ""
    if not os.path.exists(chemin(sujet)):
        modele = ("\n\nPour commencer :\n"
                  f"    python3 outils/enquete.py ouvrir {sujet}")
    raise PortillonFerme(
        "PORTILLON FERMÉ — on ne construit pas « {}» sans enquête.\n\n  · {}{}"
        .format(sujet, "\n  · ".join(manques), modele))


def journal(sujet, etat):
    os.makedirs(DOSSIER, exist_ok=True)
    with open(os.path.join(DOSSIER, "journal.txt"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M}\t{sujet}\t{etat}\n")
