"""
LES CORRECTIFS DE VOLUME — §7 du tutoriel, un seul exemplaire pour le dépôt.

╔══════════════════════════════════════════════════════════════════════════╗
║  CE QUE CE MODULE FABRIQUE, ET POURQUOI CHAQUE PIÈCE EXISTE.             ║
╚══════════════════════════════════════════════════════════════════════════╝

Le §7 corrige ce que les poids seuls ne peuvent pas corriger : la chair qui
s'écrase à l'intérieur d'un pli et le volume qui manque à l'extérieur. Il le
fait de DEUX façons, et il ne faut jamais les confondre :

  · des SHAPE KEYS pilotées par les propriétés de `CTRL_hand` — la forme
    corrigée est sculptée une fois, stockée en deltas, rappelée par un driver ;
  · des OS CORRECTIFS déformants, sans contrôleur, qui reçoivent une PART des
    poids d'un os parent (jamais des poids neufs) et se déplacent d'une
    translation linéaire pilotée par la même propriété.

Les deux sont persistés HORS du `.blend` : deltas en JSON creux, masques de
zones en JSON. Une reconstruction relit ces fichiers et retrouve exactement les
mêmes sommets, les mêmes centres d'os, les mêmes deltas.

╔══════════════════════════════════════════════════════════════════════════╗
║  LES SIX FAUTES MESURÉES DE CE DÉPÔT QUE CE FICHIER REFUSE DE REFAIRE.   ║
╚══════════════════════════════════════════════════════════════════════════╝

1. AUCUNE VALEUR PAR DÉFAUT SUR UNE LECTURE. Pas un seul `.get(cle, 0.0)` sur
   une mesure : un zéro se lit comme une mesure, et deux des quatre fautes de
   sonde d'une même journée rendaient un manquement FAUX pour cette raison.
   Ici, une clé absente LÈVE. Le seul zéro admis est celui d'un poids de groupe
   absent d'un sommet — et il n'est pas fabriqué, le sommet est SAUTÉ.

2. UN DRIVER RÉÉCRIT SA VOIE, ET DEUX DRIVERS SUR UNE MÊME VOIE S'ÉCRASENT
   SANS UN MOT. Chaque pose de driver commence par vérifier qu'aucun driver
   n'occupe déjà ce chemin exact, et LÈVE s'il y en a un.

3. APRÈS TOUTE ÉCRITURE, `rafraichir()`. Sans update_tag + frame_set +
   view_layer.update, on mesure une main IMMOBILE — et une main immobile revient
   toujours à sa pose de repos, donc elle passe tous les contrôles. C'est le
   piège le plus coûteux de ce dépôt.

4. TOUTE SONDE SE CONTRE-ÉPROUVE. Les deux drivers posés ici sont relus sur la
   copie ÉVALUÉE à DEUX valeurs de la propriété : si les deux lectures sont
   ÉGALES, le driver n'atteint pas son canal et la fonction LÈVE. Un driver
   qu'on ne peut pas voir bouger ne prouve rien.

5. JAMAIS DE DISTANCE EUCLIDIENNE POUR UN MASQUE. Le tutoriel l'écrit noir sur
   blanc : deux peaux opposées peuvent être à 2 mm l'une de l'autre dans
   l'espace et à 50 mm l'une de l'autre SUR LA SURFACE. Un masque euclidien
   attrape la peau d'en face et la tire avec la peau d'en dessous.
   `masque_geodesique()` propage le coût PAR LES ARÊTES (Dijkstra), et
   l'autotest ÉCHOUE si quelqu'un y remet une distance dans l'espace.

6. LES EXPRESSIONS DE DRIVER SONT LINÉAIRES, SANS PARENTHÈSES NI SECONDE
   VARIABLE. `min`/`max`, un appel de fonction, un produit de deux variables :
   l'évaluateur simple de Blender échoue EN SILENCE (`is_valid` faux, rotation
   à 0,0, main inerte, contrôle « retour au repos exact » vert pour la pire des
   raisons). `_exiger_expression_lineaire()` refait ce contrôle sur toute
   expression, et il est exporté pour que l'hôte puisse s'en servir aussi.

╔══════════════════════════════════════════════════════════════════════════╗
║  CE QU'UNE RELECTURE ADVERSE A TROUVÉ DANS LE PREMIER JET, ET CORRIGÉ.   ║
╚══════════════════════════════════════════════════════════════════════════╝

Le premier jet de ce fichier portait sept défauts. Chacun a été DÉMONTRÉ avant
d'être corrigé — aucun n'a été inventé pour avoir l'air utile :

  a. UNE GARDE AVEUGLE PAR CONSTRUCTION. `masque_depuis_adjacence` contrôlait
     `dist` non vide APRÈS la propagation, en annonçant « les graines ne sont
     pas dans le graphe ». Dijkstra inscrit chaque graine à la distance 0 avant
     de regarder quoi que ce soit : la garde ne pouvait pas échouer. Mesuré sur
     un graphe VIDE avec la graine 999 : `dist == {999: 0.0}`, garde verte,
     masque d'UN sommet à 1,0, correctif muet. On contrôle désormais AVANT de
     propager que chaque graine appartient bien à une arête.

  b. UNE CONTRE-ÉPREUVE QUI ÉTAIT UNE IDENTITÉ ARITHMÉTIQUE. L'autotest du
     transfert écrivait `abs((w - part) + part - w) < 1e-15` et appelait cela
     « la somme est conservée ». C'est vrai pour TOUT `part`, y compris dix fois
     le poids disponible (mesuré : écart 5,6e-17). Cette ligne testait IEEE 754,
     pas le module. Remplacée par ce qui peut réellement échouer : `0 ≤ part ≤ w`
     et le plafond respecté.

  c. UN POINT AVEUGLE DANS LA CONTRE-ÉPREUVE DU TRANSFERT. Elle comparait
     `w_correctif + w_source` relus au seul poids que la SOURCE portait avant —
     sans rien savoir de ce que le correctif portait déjà, que `REPLACE` efface.
     Deuxième passage sur la même zone : la somme du sommet tombe de 1,00 à 0,65
     (mesuré) et la garde trouve tout juste. Un refus explicite précède
     maintenant l'écriture ; les deux morceaux ne se séparent pas.

  d. DES TOLÉRANCES PLUS FINES QUE LE STOCKAGE QU'ELLES RELISENT. `1e-9 m` sur
     `b.length` et sur les bornes d'un curseur : Blender stocke en float 32 bits.
     Mesuré : un os de 12 mm posé à 0,05–0,2 m relit sa longueur à 2,8e-9 m près,
     et une borne écrite -0,3 se relit -0,30000001. Ces gardes criaient sur des
     objets JUSTES — et une garde qui crie pour une raison étrangère à ce qu'elle
     surveille finit désarmée. Voir `TOLERANCE_GEOMETRIE_M`.

  e. UNE LECTURE DE SHAPE KEY ADRESSÉE AU MAUVAIS DATABLOCK. La contre-épreuve
     lisait `obj.evaluated_get(dg).data.shape_keys` : le maillage ÉVALUÉ d'un
     objet qui porte un modificateur d'armature — c'est le cas de la main — est
     un maillage neuf sans shape keys, donc `None.key_blocks`, donc un
     AttributeError au lieu d'une mesure. Le driver d'une shape key vit sur le
     datablock « Key » : c'est sa copie évaluée qu'on lit désormais. (Ce
     défaut-ci est RAISONNÉ, pas mesuré : il demande un Blender pour se voir.)

  f. UN INDICE DE SOMMET TRONQUÉ EN SILENCE. `_entier_positif(int(i))` :
     `int(3.7)` rend 3 sans un mot, et le poids ou le delta atterrit sur le
     sommet d'à côté — faute invisible, puisque la contre-épreuve relit à son
     tour le sommet 3 et le trouve juste. `_indice_sommet` refuse la troncature.
     Au passage, un masque portant 3 ET "3" perdait une des deux valeurs.

  g. UN COMPTE ANNONCÉ DE TÊTE. L'autotest des zones annonçait
     « 4 + len(CLES_ZONE) + 3 » = 14 refus là où il en exerçait 13. Le compte est
     désormais tenu par les refus eux-mêmes (`_REFUS_EXERCES`).

╔══════════════════════════════════════════════════════════════════════════╗
║  CE QUE CE MODULE NE FAIT PAS.                                           ║
╚══════════════════════════════════════════════════════════════════════════╝

  · il ne reconfigure PAS `sys.stdout` à l'import — un module ne touche pas à
    la sortie de son hôte ; il le fait dans son autotest, qui est un script ;
  · il ne prononce AUCUN verdict de rig et ne sort d'aucun code à l'import :
    il lève ou il rend une valeur. Le verdict appartient à celui qui compare ;
  · il n'importe RIEN de Blender au chargement. `bpy` et `mathutils` sont
    chargés paresseusement dans les seules fonctions qui touchent la scène,
    exactement comme `atelier/mesures_paume.py`. Tout le calcul pur — format
    JSON creux, masque géodésique, arithmétique du transfert, contrôle
    d'expression — se relit et se TESTE hors de Blender :

        python3 atelier/correctifs.py        # autotest, code non nul si faux

UNITÉS : la scène est en MÈTRES. Tous les rayons, longueurs et amplitudes de
ce module sont en mètres ; c'est écrit dans le nom des paramètres (`_m`).

╔══════════════════════════════════════════════════════════════════════════╗
║  UN ARGUMENT DE PLUS QUE L'ESQUISSE, ET POURQUOI.                        ║
╚══════════════════════════════════════════════════════════════════════════╝

`sauver_zones` et `charger_zones` prennent un `nb_sommets` en dernier. Le
cahier demande de « refuser si le nombre de sommets OU l'empreinte ne
correspondent plus » : sans cet argument, `charger_zones` ne voit jamais
l'objet et ne PEUT PAS contrôler le nombre de sommets — il ne resterait que
l'empreinte, et le contrôle demandé serait un trou silencieux. Le paramètre
porte `None` par défaut UNIQUEMENT pour pouvoir lever avec une phrase qui dit
quoi passer, au lieu d'un `TypeError` de Python. Appelez :

    correctifs.charger_zones(chemin, SHA, len(geo.data.vertices))
"""
import hashlib
import heapq
import json
import math
import os
import re
import struct

# ═══════════════════════════════════════════════════════════════════
#   CONSTANTES — un seul exemplaire, sinon elles divergeront
# ═══════════════════════════════════════════════════════════════════

# L'espace dans lequel les deltas d'une shape key ont un sens : coordonnées
# LOCALES à l'objet, mesurées par rapport au Basis. Écrit dans chaque fichier
# et RELU à l'ouverture : un fichier produit dans un autre espace (monde, pose,
# repère d'os) appliquerait des deltas justes à des sommets justes dans un
# repère faux, et rien ne se signalerait. Ce n'est pas une décoration.
ESPACE_DELTAS = "OBJECT_LOCAL_BASIS"

# Emplacement imposé par le cahier : les masques sont persistés là et RELUS à
# chaque reconstruction. Sans ce fichier, les centres des os correctifs
# dépendraient d'une sélection restée ouverte dans un Blender — c'est-à-dire
# d'un état que personne ne peut rejouer, et le rig ne serait plus reproductible.
DOSSIER_CORRECTIFS = os.path.join("assets", "correctifs")

# Sous ce seuil, un vecteur ne porte plus de direction fiable. Un seul
# exemplaire : quatre littéraux `1e-9` séparés dans `mesures_paume.py` gardaient
# quatre vecteurs différents, c'est la faute que ce dépôt a déjà payée.
LONGUEUR_NULLE = 1e-9

# Tolérance des contre-épreuves d'arithmétique de poids. Les poids de Blender
# sont des flottants simple précision ; 1e-6 est très au-dessus du bruit de
# codage et très en dessous de tout transfert qui compte.
TOLERANCE_POIDS = 1e-6

# ═══ POURQUOI CETTE TOLÉRANCE N'EST PAS `LONGUEUR_NULLE` ═══
# Relire une géométrie qu'on vient d'écrire, c'est relire du SIMPLE PRÉCISION :
# Blender stocke les coordonnées d'os et de sommets en float 32 bits, et
# `mathutils` calcule en 32 bits lui aussi. À 0,1 m — l'ordre de grandeur d'une
# main en mètres — deux flottants 32 bits consécutifs sont distants de ~7,5e-9 m.
# Une garde à 1e-9 m mesure donc le CODAGE, pas la faute : elle échoue sur un os
# parfaitement posé, et une garde qui crie pour une raison étrangère à ce
# qu'elle prétend surveiller finit par être désarmée. 1e-6 m = 0,001 mm, soit
# dix fois plus fin que le seuil de repos de 0,01 mm auquel ce dépôt juge une
# main, et mille fois plus grossier que le bruit de codage : la garde ne peut
# plus voir que de vraies fautes (une tête d'os recollée au parent, une longueur
# écrasée), qui se comptent en millimètres.
TOLERANCE_GEOMETRIE_M = 1e-6

# Relecture d'un RÉGLAGE stocké en simple précision (bornes de curseur d'une
# shape key). Même valeur numérique que ci-dessus, volontairement SÉPARÉE : ce
# n'est pas une longueur, elle n'a pas d'unité, et la fusionner ferait dépendre
# une tolérance en mètres d'une décision prise sur un réglage sans dimension —
# le jour où l'une des deux doit bouger, l'autre bougerait en silence.
TOLERANCE_REGLAGE = 1e-6

# Les sept clés qu'une zone DOIT porter pour qu'un os correctif se reconstruise
# sans jamais consulter la sélection courante de Blender. Elles sont exigées à
# l'écriture ET à la lecture : un fichier incomplet se refuse au moment où on
# l'écrit, pas trois heures plus tard au milieu d'une reconstruction.
CLES_ZONE = ("graines", "rayon_coeur_m", "rayon_fondu_m", "masque",
             "centre", "direction", "roll_rad")


# ═══════════════════════════════════════════════════════════════════
#   OUTILLAGE PUR — rien de Blender, tout se teste hors Blender
# ═══════════════════════════════════════════════════════════════════

def _exiger(condition, message):
    """Lève `RuntimeError(message)` si la condition est fausse.

    Une fonction plutôt qu'un `assert` : `python -O` retire les `assert`, et un
    contrôle qui peut disparaître à l'exécution n'est pas un contrôle.
    """
    if not condition:
        raise RuntimeError(message)


def _reel_fini(valeur, quoi):
    """Convertit en flottant et REFUSE NaN et l'infini.

    Un NaN traverse toutes les comparaisons sans jamais les faire échouer :
    `nan > seuil` est faux, `nan < seuil` est faux, donc un critère écrit dans
    un sens passe et le même critère écrit dans l'autre sens passe aussi. Une
    grandeur non finie n'est pas une mesure, elle est l'absence de mesure.
    """
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        raise RuntimeError(f"{quoi} : {valeur!r} n'est pas un nombre")
    _exiger(math.isfinite(v), f"{quoi} : valeur non finie ({v!r})")
    return v


def _entier_positif(valeur, quoi):
    """Convertit en entier >= 0, sans jamais accepter un flottant approché."""
    _exiger(isinstance(valeur, int) and not isinstance(valeur, bool),
            f"{quoi} : {valeur!r} n'est pas un entier")
    _exiger(valeur >= 0, f"{quoi} : {valeur} est négatif")
    return valeur


def _indice_sommet(cle, quoi):
    """Un indice de sommet : entier, ou chaîne d'entier. JAMAIS `int(flottant)`.

    ═══ POURQUOI PAS `int(cle)` TOUT COURT ═══
    `int(3.7)` rend 3 SANS UN MOT. Un masque dont une clé serait un flottant —
    dictionnaire construit à la main, indice sorti d'un calcul, arrondi d'un
    autre outil — pèserait alors le sommet 3 en croyant peser le 3,7e, et rien
    n'apparaîtrait nulle part : le transfert réussirait, sa contre-épreuve
    relirait le sommet 3 et le trouverait juste. C'est la forme « transfert »
    du zéro qui se lit comme une mesure — un indice faux se lit exactement
    comme un indice vrai. On refuse donc la troncature au lieu de l'accepter.
    """
    if isinstance(cle, bool):
        raise RuntimeError(f"{quoi} : {cle!r} est un booléen, pas un indice")
    if isinstance(cle, int):
        return _entier_positif(cle, quoi)
    if isinstance(cle, str):
        texte = cle.strip()
        if not texte.isdigit():
            raise RuntimeError(
                f"{quoi} : {cle!r} n'est pas un indice de sommet. Seuls un "
                "entier ou une chaîne de chiffres sont admis — un flottant "
                "serait TRONQUÉ en silence et pèserait un autre sommet.")
        return _entier_positif(int(texte), quoi)
    raise RuntimeError(
        f"{quoi} : indice de sommet {cle!r} de type "
        f"{type(cle).__name__}. Un flottant se tronquerait sans un mot.")


def _indexer(dictionnaire, cle, quoi):
    """Lecture d'une clé OBLIGATOIRE — jamais de `.get(cle, defaut)`.

    ═══ UN ZÉRO SE LIT COMME UNE MESURE ═══
    C'est la faute la plus répétée de ce dépôt : `mesures.get("profondeur", 0.0)`
    sur un rapport où la clé s'appelait autrement rendait 0,0 mm, et 0,0 mm
    passait le critère « moins de 1 mm ». Le manquement devenait VRAI par
    accident. Une clé absente n'est pas une valeur nulle, c'est une absence.
    """
    _exiger(isinstance(dictionnaire, dict),
            f"{quoi} : on attendait un dictionnaire, reçu {type(dictionnaire).__name__}")
    if cle not in dictionnaire:
        raise RuntimeError(
            f"{quoi} : la clé {cle!r} est ABSENTE. Elle ne vaut pas zéro, elle "
            f"n'existe pas. Clés présentes : {sorted(dictionnaire)}")
    return dictionnaire[cle]


def _triplet(valeur, quoi):
    """Trois réels finis, depuis un `Vector`, un tuple ou une liste JSON."""
    try:
        suite = [valeur[0], valeur[1], valeur[2]]
    except (TypeError, KeyError, IndexError):
        raise RuntimeError(f"{quoi} : on attendait trois composantes, "
                           f"reçu {valeur!r}")
    _exiger(len(valeur) == 3, f"{quoi} : {len(valeur)} composantes au lieu de 3")
    return [_reel_fini(c, f"{quoi}[{k}]") for k, c in enumerate(suite)]


# ── Contrôle d'expression de driver ──────────────────────────────────
#
# ═══ POURQUOI CE CONTRÔLE EXISTE, ET CE QU'IL A COÛTÉ ═══
# Premier jet du dépôt : `min(max(fist + curl, 0.0), 1.0) * k`. Résultat
# MESURÉ : `Fist = 1` ne déplaçait AUCUN sommet, course du poing 0,0 mm. Les
# drivers existaient, leurs expressions se lisaient bien, et ils échouaient en
# silence — `--factory-startup` désactive l'exécution automatique des scripts,
# et `min`/`max` réclament l'évaluateur Python. L'évaluateur simple ne fait que
# de l'arithmétique. Pire : la main inerte faisait PASSER le contrôle « retour
# au repos exact », parce qu'une main qui ne bouge pas revient toujours
# exactement à sa place.
#
# Le contrôle ci-dessous est volontairement PLUS STRICT que Blender : pas de
# parenthèses du tout (ce qui interdit tout appel de fonction par construction),
# et au plus UNE variable par terme additif (ce qui interdit `p * q`, produit de
# deux variables, non linéaire donc refusé par l'évaluateur simple).
_IDENTIFIANT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CARACTERES_ADMIS = set("0123456789._+-*/ \tabcdefghijklmnopqrstuvwxyz"
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _exiger_expression_lineaire(expression, variables):
    """LÈVE si l'expression ne tient pas dans l'évaluateur simple de Blender.

    `variables` : les noms déclarés sur le driver. Tout autre identifiant —
    `min`, `max`, `abs`, `pi`, une variable oubliée — fait lever.

    Trois refus, chacun pour une panne SILENCIEUSE observée ou documentée :
      · un caractère hors de l'arithmétique (parenthèse, virgule) → appel de
        fonction ou expression conditionnelle, l'évaluateur simple abandonne ;
      · un identifiant inconnu → variable non déclarée, lue comme 0.0 sans un
        mot, donc un driver muet qui a l'air correct ;
      · deux identifiants dans un même terme additif → produit de deux
        variables, non linéaire, refusé sans message.
    """
    _exiger(isinstance(expression, str) and expression.strip() != "",
            "expression de driver vide")
    noms = set(variables)
    _exiger(noms, "expression de driver sans aucune variable déclarée : "
                  "elle ne peut pas dépendre de la main")
    inconnus = sorted(set(expression) - _CARACTERES_ADMIS)
    _exiger(not inconnus,
            f"expression {expression!r} : caractères interdits {inconnus}. "
            "Ni parenthèses ni virgules — l'évaluateur simple de Blender ne "
            "sait pas appeler une fonction, il échoue EN SILENCE (mesuré : "
            "course du poing 0,0 mm avec min/max).")
    # Chaque terme additif au plus une variable : `a*0.5 + b*0.5` passe,
    # `a*b` non. On sépare sur + et -, ce qui est exactement la décomposition
    # d'une forme linéaire dans le sous-ensemble arithmétique autorisé.
    for terme in re.split(r"[+\-]", expression):
        idents = _IDENTIFIANT.findall(terme)
        etrangers = [i for i in idents if i not in noms]
        _exiger(not etrangers,
                f"expression {expression!r} : identifiant(s) non déclaré(s) "
                f"{etrangers}. Une variable inconnue est lue 0.0 sans un mot.")
        _exiger(len(idents) <= 1,
                f"expression {expression!r} : le terme {terme.strip()!r} "
                f"contient {len(idents)} variables. Un produit de deux "
                "variables n'est pas linéaire et échoue EN SILENCE.")
    return expression


def _constante_texte(valeur, quoi):
    """Écrit une constante SANS notation exponentielle, pour un driver.

    ═══ POURQUOI PAS `repr(x)` ═══
    `repr(1e-3)` rend `'0.001'`, mais `repr(1e-5)` rend `'1e-05'` : un `e` que
    l'évaluateur simple ne sait pas lire, et qui rend l'expression fausse SANS
    message. On force donc une écriture décimale, et on REFUSE toute valeur
    trop petite pour être écrite ainsi sans devenir zéro — un driver dont la
    constante s'est arrondie à zéro est un driver qui ne fait rien tout en
    ayant l'air posé.
    """
    v = _reel_fini(valeur, quoi)
    texte = f"{v:.12f}".rstrip("0")
    if texte.endswith("."):
        texte += "0"
    if texte in ("0.0", "-0.0"):
        raise RuntimeError(
            f"{quoi} : {v!r} s'écrit {texte} en décimal sur 12 chiffres, "
            "c'est-à-dire ZÉRO. Un driver de constante nulle ne déplace rien "
            "tout en paraissant posé — ce qui est exactement la panne "
            "silencieuse que ce module refuse.")
    # Contre-épreuve immédiate : le texte doit se relire comme le nombre.
    relu = float(texte)
    _exiger(abs(relu - v) <= max(1e-12, abs(v) * 1e-9),
            f"{quoi} : {v!r} s'écrit {texte} qui se relit {relu!r} — la "
            "constante du driver ne serait pas celle demandée")
    _exiger("e" not in texte and "E" not in texte,
            f"{quoi} : {texte!r} porte une notation exponentielle")
    return texte


# ═══════════════════════════════════════════════════════════════════
#   1 · L'EMPREINTE DU MAILLAGE AU REPOS
# ═══════════════════════════════════════════════════════════════════

def _coordonnees_basis(obj):
    """Les coordonnées du Basis, jamais celles d'une shape key active.

    Trois cas, et AUCUN repli silencieux :
      · pas de shape keys du tout → le maillage EST son propre Basis, c'est un
        fait de Blender, pas une valeur par défaut ;
      · des shape keys avec un bloc `Basis` → on lit ce bloc ;
      · des shape keys SANS bloc `Basis` → on LÈVE. Lire `mesh.vertices` dans
        ce cas rendrait les coordonnées d'un mélange, l'empreinte changerait au
        gré du curseur d'une forme, et deux reconstructions identiques
        n'auraient pas la même empreinte.
    """
    me = obj.data
    cles = me.shape_keys
    if cles is None:
        return [tuple(v.co) for v in me.vertices]
    blocs = cles.key_blocks
    if "Basis" not in blocs:
        raise RuntimeError(
            f"{obj.name} porte des shape keys mais AUCUN bloc « Basis ». "
            "L'empreinte se refuse : sans Basis on ne sait pas de quelle forme "
            "les deltas partent, et deux reconstructions identiques ne "
            "rendraient pas la même empreinte. "
            f"Blocs présents : {[b.name for b in blocs]}")
    return [tuple(p.co) for p in blocs["Basis"].data]


def empreinte_maillage_basis(obj):
    """SHA-256 de la TOPOLOGIE et des coordonnées du Basis. Jamais d'un chemin.

    ═══ POURQUOI PAS LE NOM DU FICHIER, NI SA DATE ═══
    Un chemin ne dit rien du maillage : le même nom peut porter une
    retopologie, un miroir, un sommet fusionné. Or les deltas d'une shape key
    creuse sont indexés PAR NUMÉRO DE SOMMET. Appliquer les deltas d'hier à la
    numérotation d'aujourd'hui déplace des sommets QUELCONQUES, produit une
    main tordue, et rien ne se signale : le fichier s'est chargé, la forme
    existe, le driver marche. L'empreinte est la seule barrière possible.

    Ce qui entre dans le condensat, dans cet ordre exact (code du tutoriel) :
      1. `<II` : nombre de sommets, nombre de polygones ;
      2. `<I3d` par sommet : son indice, puis ses trois coordonnées de Basis ;
      3. les polygones : la taille de chacun, puis ses indices de sommets.

    L'indice est réinjecté à chaque sommet (`<I3d` et non `<3d`) pour que deux
    maillages qui portent les mêmes points dans un ORDRE différent aient deux
    empreintes différentes — l'ordre est précisément ce qui compte ici.

    Les coordonnées sont empaquetées en `d` (double) et non en `f` : Blender
    stocke du simple précision, Python manipule des doubles, et convertir vers
    `f` réintroduirait un arrondi dépendant de la plateforme. Le condensat doit
    être le même sur toutes les machines qui lisent le même `.blend`.
    """
    me = obj.data
    coords = _coordonnees_basis(obj)
    _exiger(len(coords) == len(me.vertices),
            f"{obj.name} : {len(coords)} points de Basis pour "
            f"{len(me.vertices)} sommets — le Basis ne décrit pas ce maillage")
    h = hashlib.sha256()
    h.update(struct.pack("<II", len(me.vertices), len(me.polygons)))
    for i, co in enumerate(coords):
        h.update(struct.pack("<I3d", i, float(co[0]), float(co[1]), float(co[2])))
    for p in me.polygons:
        sommets = list(p.vertices)
        h.update(struct.pack("<I", len(sommets)))
        for vi in sommets:
            h.update(struct.pack("<I", int(vi)))
    return h.hexdigest()


# ═══════════════════════════════════════════════════════════════════
#   RAFRAÎCHISSEMENT — les quatre lignes sans lesquelles on mesure
#   une main immobile
# ═══════════════════════════════════════════════════════════════════

def rafraichir(*objets):
    """update_tag + data.update_tag + frame_set + view_layer.update.

    ═══ LES DRIVERS NE S'ÉVALUENT PAS SANS CHANGEMENT D'IMAGE ═══
    En mode fond, l'évaluation de l'animation ne se déclenche pas tant que
    l'image ne change pas. Les 25 drivers du dépôt existaient, leurs
    expressions étaient bonnes, `is_valid` rendait vrai — et la rotation
    restait à 0,0 jusque dans le graphe évalué. Ils n'étaient pas fautifs : ils
    n'étaient pas ÉVALUÉS. Sans ces lignes, `Fist = 1` ne déplace aucun sommet,
    et le contrôle « retour au repos exact » passe pour la pire des raisons.

    Ces quatre lignes existent aussi dans `rig-main.forcer_evaluation()`. Ce
    n'est pas un doublon de MESURE — il n'y a ici aucune grandeur, aucun seuil,
    rien qui puisse diverger : c'est la même incantation du dépôt, écrite ici
    parce qu'un module ne peut pas importer le script qui l'importe.
    """
    import bpy
    for o in objets:
        if o is None:
            continue
        o.update_tag()
        # Tous les identifiants n'ont pas de `.data` (une scène, une collection).
        # Branche explicite plutôt que `getattr(o, "data", None)` : la forme
        # d'une lecture à repli est proscrite dans ce fichier, même quand le
        # repli est un fait de structure et non une mesure absente.
        if hasattr(o, "data") and o.data is not None:
            o.data.update_tag()
    sc = bpy.context.scene
    _exiger(sc is not None,
            "aucune scène dans le contexte : impossible de forcer "
            "l'évaluation, donc impossible de mesurer autre chose qu'une main "
            "immobile")
    sc.frame_set(sc.frame_current)
    bpy.context.view_layer.update()


def _drivers_de(donnees):
    """Les fcurves de driver d'un datablock, liste VIDE s'il n'en a aucun."""
    ad = donnees.animation_data
    return [] if ad is None else list(ad.drivers)


def _refuser_driver_existant(donnees, chemin, indice, quoi):
    """LÈVE si un driver occupe déjà ce chemin (et cet indice).

    ═══ DEUX DRIVERS SUR UNE MÊME VOIE : LE SECOND ÉCRASE LE PREMIER ═══
    Faute mesurée de ce dépôt sur `rotation_euler` : Blender accepte la
    deuxième pose, n'affiche rien, et seule la dernière agit. On croit avoir
    additionné deux effets, on n'en a qu'un — et le diagnostic est impossible
    puisque les deux drivers sont bien là, tous deux `is_valid`. La seule
    parade est de refuser AVANT d'écrire, et d'additionner les constantes en
    amont quand deux effets doivent cohabiter.
    """
    for fc in _drivers_de(donnees):
        if fc.data_path == chemin and (indice is None or fc.array_index == indice):
            raise RuntimeError(
                f"{quoi} : un driver occupe DÉJÀ {chemin}"
                f"{'' if indice is None else f'[{indice}]'}. En poser un second "
                "ne les additionne pas : le second écrase le premier SANS un "
                "mot. Additionnez les constantes en amont, ou supprimez "
                "l'ancien explicitement.")


def _echapper(nom):
    """Nom sûr dans un `data_path` entre guillemets."""
    _exiger('"' not in nom and "\\" not in nom,
            f"nom {nom!r} : un guillemet ou une contre-oblique casserait le "
            "chemin de données du driver, qui pointerait alors ailleurs — ou "
            "nulle part, ce qui se lit 0.0 sans un mot")
    return nom


def _exiger_propriete(rig, SIDE, propriete):
    """Le contrôleur et la propriété DOIVENT exister avant qu'on les vise.

    ═══ UNE CIBLE DE DRIVER QUI N'EXISTE PAS SE LIT 0.0 ═══
    Blender ne se plaint pas d'un `data_path` qui ne résout pas : la variable
    vaut 0.0, le driver s'évalue, la forme reste à sa valeur de repos, et le
    rig a l'air simplement « pas encore réglé ». C'est la variante driver du
    zéro qui se lit comme une mesure. On contrôle donc AVANT d'écrire.
    """
    nom_ctrl = f"CTRL_hand{SIDE}"
    _exiger(nom_ctrl in rig.pose.bones,
            f"{rig.name} n'a pas d'os de pose {nom_ctrl!r} : la cible du "
            "driver n'existerait pas et la variable serait lue 0.0 sans un mot")
    pbh = rig.pose.bones[nom_ctrl]
    _exiger(propriete in pbh.keys(),
            f"{nom_ctrl} ne porte pas la propriété {propriete!r}. Une "
            "propriété absente se lit 0.0 : le correctif serait posé, piloté, "
            "et définitivement muet. "
            f"Propriétés présentes : {sorted(pbh.keys())}")
    return pbh


# ═══════════════════════════════════════════════════════════════════
#   2 + 3 · LES SHAPE KEYS CREUSES — écriture et relecture
# ═══════════════════════════════════════════════════════════════════

def _valider_charge_sparse(charge, nom_attendu, nb_sommets, sha):
    """Contrôle PUR d'un fichier de shape key creuse. Rend les deltas typés.

    Séparé de `charger_shape_sparse` exprès : tout ce qui peut se vérifier sans
    Blender se vérifie sans Blender, et l'autotest de fin de fichier éprouve
    ces refus un par un. Un contrôle qu'on n'a jamais vu échouer n'est pas un
    contrôle, c'est une intention.
    """
    _exiger(isinstance(charge, dict),
            "fichier de shape key : la racine n'est pas un objet JSON")
    nom = _indexer(charge, "name", "shape key creuse")
    compte = _indexer(charge, "mesh_vertex_count", "shape key creuse")
    empreinte = _indexer(charge, "mesh_source_sha256", "shape key creuse")
    espace = _indexer(charge, "space", "shape key creuse")
    _indexer(charge, "source_pose", "shape key creuse")   # présence exigée
    deltas = _indexer(charge, "deltas", "shape key creuse")

    _exiger(nom == nom_attendu,
            f"shape key : le fichier porte {nom!r}, on attendait "
            f"{nom_attendu!r}. Charger l'un pour l'autre poserait des deltas "
            "justes sur la mauvaise forme.")
    _exiger(espace == ESPACE_DELTAS,
            f"shape key {nom!r} : espace {espace!r} au lieu de "
            f"{ESPACE_DELTAS!r}. Des deltas exprimés dans un autre repère "
            "s'appliqueraient sans erreur et tordraient la main.")
    _exiger(compte == nb_sommets,
            f"shape key {nom!r} : le fichier décrit {compte} sommets, l'objet "
            f"en a {nb_sommets}. TOPOLOGIE DIFFÉRENTE — surtout ne pas "
            "appliquer les deltas aux mauvais sommets.")
    _exiger(empreinte == sha,
            f"shape key {nom!r} : empreinte du fichier {empreinte} ≠ empreinte "
            f"du maillage {sha}. Topologie ou Basis CHANGÉS. Les deltas sont "
            "indexés par numéro de sommet : les appliquer déplacerait des "
            "sommets quelconques, et rien ne se signalerait.")
    _exiger(isinstance(deltas, dict),
            f"shape key {nom!r} : « deltas » n'est pas un objet")

    propres = {}
    for cle, valeur in deltas.items():
        # `_indice_sommet` et non `int(cle)` : `int(3.7)` rend 3 sans un mot et
        # poserait le delta sur un sommet voisin, ce que plus rien ne dirait.
        i = _indice_sommet(cle, f"shape key {nom!r}, indice de sommet")
        _exiger(0 <= i < nb_sommets,
                f"shape key {nom!r} : indice {i} hors du maillage "
                f"(0..{nb_sommets - 1}). Blender lèverait un IndexError — ou "
                "pire, un indice recyclé déplacerait un sommet innocent.")
        _exiger(i not in propres,
                f"shape key {nom!r} : l'indice {i} apparaît deux fois")
        propres[i] = _triplet(valeur, f"shape key {nom!r}, delta du sommet {i}")
    return propres


def exporter_shape_sparse(obj, nom, chemin, source_pose, sha, epsilon=1e-7):
    """Écrit les deltas NON NULS d'une shape key, au format du §7.

    `epsilon` (mètres) : en deçà, un delta est du bruit de sculpture, pas une
    correction. 1e-7 m = 0,0001 mm, c'est-à-dire mille fois plus fin que le
    seuil de 0,01 mm auquel le repos est jugé — on ne jette donc jamais rien de
    mesurable, on jette le bruit qui ferait grossir le fichier de tous les
    sommets de la main.

    `sha` est passé par l'appelant ET RECONTRÔLÉ ici contre l'objet. Un
    exportateur qui écrit l'empreinte qu'on lui donne, sans vérifier, appose un
    cachet de conformité sur un fichier qui peut décrire un autre maillage :
    c'est un contrôle qui ne peut pas échouer, donc pas un contrôle.
    """
    _exiger(isinstance(source_pose, dict),
            "source_pose doit être un dictionnaire : la pose dans laquelle la "
            "forme a été sculptée fait partie de sa définition, sans elle "
            "personne ne peut la resculpter ni la juger")
    eps = _reel_fini(epsilon, "epsilon")
    _exiger(eps > 0.0, "epsilon doit être strictement positif")

    reelle = empreinte_maillage_basis(obj)
    _exiger(reelle == sha,
            f"exportation de {nom!r} : l'empreinte fournie ({sha}) n'est pas "
            f"celle du maillage ({reelle}). On refuse d'apposer une empreinte "
            "non vérifiée : le fichier prétendrait décrire un maillage qu'il "
            "ne décrit pas, et sa relecture passerait sans broncher.")

    cles = obj.data.shape_keys
    _exiger(cles is not None,
            f"{obj.name} n'a aucune shape key : rien à exporter sous {nom!r}")
    _exiger(nom in cles.key_blocks,
            f"{obj.name} n'a pas de shape key {nom!r}. "
            f"Formes présentes : {[b.name for b in cles.key_blocks]}")

    basis = _coordonnees_basis(obj)
    bloc = cles.key_blocks[nom]
    _exiger(len(bloc.data) == len(basis),
            f"shape key {nom!r} : {len(bloc.data)} points pour {len(basis)} "
            "sommets de Basis")

    deltas = {}
    for i, point in enumerate(bloc.data):
        b = basis[i]
        dx = float(point.co[0]) - float(b[0])
        dy = float(point.co[1]) - float(b[1])
        dz = float(point.co[2]) - float(b[2])
        if max(abs(dx), abs(dy), abs(dz)) > eps:
            deltas[str(i)] = [dx, dy, dz]

    _exiger(deltas,
            f"shape key {nom!r} : AUCUN sommet ne s'écarte du Basis de plus de "
            f"{eps} m. Une correction vide se chargerait sans erreur, se "
            "piloterait sans erreur, et ne corrigerait rien — c'est très "
            "exactement la panne muette que ce module refuse d'emballer.")

    charge = {"name": nom,
              "mesh_vertex_count": len(obj.data.vertices),
              "mesh_source_sha256": sha,
              "space": ESPACE_DELTAS,
              "source_pose": source_pose,
              "deltas": deltas}

    # Contre-épreuve avant d'écrire : ce qu'on s'apprête à poser sur le disque
    # doit franchir le validateur qui le relira. Un fichier qui ne repasse pas
    # sa propre porte n'a rien à faire dans `assets/`.
    _valider_charge_sparse(charge, nom, len(obj.data.vertices), sha)

    dossier = os.path.dirname(os.path.abspath(chemin))
    if dossier:
        os.makedirs(dossier, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(charge, f, ensure_ascii=False, indent=1, sort_keys=True)
    return {"chemin": chemin, "sommets_deplaces": len(deltas),
            "sommets_du_maillage": len(obj.data.vertices), "epsilon_m": eps}


def charger_shape_sparse(obj, chemin, nom_attendu):
    """Recrée la shape key `nom_attendu` depuis son fichier creux. Rend le bloc.

    Trois refus AVANT la moindre écriture — nom, nombre de sommets, empreinte.
    Une empreinte différente signifie topologie ou Basis changés : on LÈVE, on
    n'applique surtout pas les deltas aux mauvais sommets. La main serait
    tordue et tout aurait l'air d'avoir marché.
    """
    _exiger(os.path.isfile(chemin),
            f"shape key {nom_attendu!r} : fichier introuvable — {chemin}")
    with open(chemin, "r", encoding="utf-8") as f:
        charge = json.load(f)

    sha = empreinte_maillage_basis(obj)
    nb = len(obj.data.vertices)
    deltas = _valider_charge_sparse(charge, nom_attendu, nb, sha)

    # Le Basis doit exister AVANT la forme. On le crée s'il manque : à cet
    # instant précis le maillage EST son propre Basis, donc l'empreinte qu'on
    # vient de vérifier reste vraie. Créer le Basis plus tard, après une
    # première forme, la rendrait fausse.
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    _exiger("Basis" in obj.data.shape_keys.key_blocks,
            f"{obj.name} : shape keys sans bloc « Basis » — les deltas n'ont "
            "aucune origine")
    _exiger(nom_attendu not in obj.data.shape_keys.key_blocks,
            f"{obj.name} porte DÉJÀ une shape key {nom_attendu!r}. En ajouter "
            "une seconde du même nom la ferait renommer en «.001» par Blender, "
            "sans un mot : le driver piloterait alors l'ancienne, et la forme "
            "chargée resterait inerte.")

    basis = _coordonnees_basis(obj)
    bloc = obj.shape_key_add(name=nom_attendu, from_mix=False)
    _exiger(len(bloc.data) == nb,
            f"shape key {nom_attendu!r} : {len(bloc.data)} points pour {nb} "
            "sommets")

    for i, d in deltas.items():
        b = basis[i]
        bloc.data[i].co = (b[0] + d[0], b[1] + d[1], b[2] + d[2])

    # ═══ CONTRE-ÉPREUVE : LA FORME A-T-ELLE VRAIMENT BOUGÉ ? ═══
    # On relit la forme posée et on recompte les sommets qui s'écartent du
    # Basis. Si le compte ne retombe pas exactement sur le nombre de deltas, ou
    # si un delta relu ne vaut pas celui du fichier, c'est que l'écriture n'a
    # pas pris — cas déjà vu quand `bloc.data` ne pointe pas sur la forme
    # qu'on croit. Sans cette relecture, une shape key vide se chargerait
    # « avec succès » et le correctif serait muet pour toujours.
    deplaces, pire = 0, 0.0
    for i, point in enumerate(bloc.data):
        b = basis[i]
        e = (float(point.co[0]) - float(b[0]),
             float(point.co[1]) - float(b[1]),
             float(point.co[2]) - float(b[2]))
        if max(abs(e[0]), abs(e[1]), abs(e[2])) > 0.0:
            deplaces += 1
        if i in deltas:
            d = deltas[i]
            pire = max(pire, abs(e[0] - d[0]), abs(e[1] - d[1]),
                       abs(e[2] - d[2]))
    _exiger(deplaces == len(deltas),
            f"shape key {nom_attendu!r} : {deplaces} sommets écartés du Basis "
            f"après écriture, {len(deltas)} attendus. Les deltas n'ont pas été "
            "posés là où on croit.")
    # Même raison qu'ailleurs : les points d'une shape key sont en simple
    # précision, un delta relu s'écarte donc de quelques nanomètres sans faute.
    # 1e-6 m sépare sans ambiguïté « écrit puis relu » de « pas écrit du tout ».
    _exiger(pire <= TOLERANCE_GEOMETRIE_M,
            f"shape key {nom_attendu!r} : le pire delta relu s'écarte de "
            f"{pire:.3e} m de celui du fichier — l'écriture n'a pas pris")

    rafraichir(obj)
    return bloc


# ═══════════════════════════════════════════════════════════════════
#   4 · PILOTER UNE SHAPE KEY DEPUIS UNE PROPRIÉTÉ DE LA MAIN
# ═══════════════════════════════════════════════════════════════════

def piloter_shape(rig, key, SIDE, propriete, obj=None, plage=(0.0, 1.0)):
    """Driver AVERAGE, UNE variable SINGLE_PROP. Rend la fcurve.

    ═══ POURQUOI « AVERAGE » ET PAS « SCRIPTED » ═══
    Avec une seule variable, la moyenne EST la variable : la sortie vaut
    exactement la propriété, sans la moindre expression. Or c'est l'expression
    qui casse en silence dans ce dépôt (`min`/`max` sous `--factory-startup`,
    course du poing mesurée à 0,0 mm). Un driver sans expression ne peut pas
    tomber dans ce piège : il n'a rien à faire évaluer.

    ═══ LE PIÈGE DES BORNES DU CURSEUR ═══
    La valeur d'une shape key est ÉCRÊTÉE à `slider_min`/`slider_max`. Une
    forme pilotée par `Spread`, qui va de -1 à +1, resterait donc bloquée à 0
    sur toute la moitié négative — silencieusement, driver valide à l'appui.
    `plage` est écrite explicitement sur le bloc, et doit couvrir la course de
    la propriété qui la pilote.

    `obj` : passez-le. Avec lui, la contre-épreuve est FORTE — la forme est lue
    sur la copie ÉVALUÉE à deux valeurs de la propriété, et la fonction LÈVE si
    les deux lectures sont égales, c'est-à-dire si le driver n'atteint pas son
    canal. Sans lui, on ne contrôle que la structure du driver.
    """
    pbh = _exiger_propriete(rig, SIDE, propriete)
    nom = _echapper(key.name)
    donnees = key.id_data          # le datablock « Key », porteur des drivers
    chemin = f'key_blocks["{nom}"].value'
    _refuser_driver_existant(donnees, chemin, None, f"shape key {nom!r}")

    bas, haut = _reel_fini(plage[0], "plage[0]"), _reel_fini(plage[1], "plage[1]")
    _exiger(haut > bas, f"plage de curseur vide ou inversée : {bas}..{haut}")
    # L'ORDRE D'ÉCRITURE COMPTE : Blender écrête `slider_min` à la valeur
    # courante de `slider_max` et réciproquement. Poser un minimum de -1 alors
    # que le maximum vaut encore 1 passe ; poser un maximum de 2 alors que le
    # minimum vaut 0 passe aussi — mais l'ordre inverse, sur une plage
    # déplacée, écrête EN SILENCE. On écrit donc dans l'ordre qui ne peut pas
    # écrêter, puis on RELIT.
    if haut >= key.slider_max:
        key.slider_max = haut
        key.slider_min = bas
    else:
        key.slider_min = bas
        key.slider_max = haut
    # Tolérance de RELECTURE D'UN RÉGLAGE, pas de zéro : `slider_min` et
    # `slider_max` sont stockés en simple précision, donc écrire -0,3 et relire
    # -0,30000001 est le fonctionnement NORMAL de Blender. La faute visée —
    # Blender ÉCRÊTE la borne à celle d'en face — déplace la borne de plusieurs
    # dixièmes ; 1e-6 la voit sans jamais confondre un écrêtage avec un arrondi.
    _exiger(abs(key.slider_min - bas) <= TOLERANCE_REGLAGE
            and abs(key.slider_max - haut) <= TOLERANCE_REGLAGE,
            f"shape key {key.name!r} : bornes du curseur relues "
            f"{key.slider_min!r}..{key.slider_max!r} au lieu de {bas!r}..{haut!r}. "
            "La valeur d'une shape key est ÉCRÊTÉE à ces bornes : une forme "
            "pilotée par une propriété qui sort de la plage resterait bloquée "
            "sur toute une moitié de sa course, driver valide à l'appui.")

    fc = donnees.driver_add(chemin)
    d = fc.driver
    d.type = "AVERAGE"
    v = d.variables.new()
    v.name = "p"
    v.type = "SINGLE_PROP"
    v.targets[0].id = rig
    v.targets[0].data_path = (f'pose.bones["{_echapper(f"CTRL_hand{SIDE}")}"]'
                              f'["{_echapper(propriete)}"]')
    _exiger(len(d.variables) == 1,
            f"shape key {nom!r} : {len(d.variables)} variables sur un driver "
            "AVERAGE — la moyenne de plusieurs entrées n'est plus la propriété")

    rafraichir(rig, obj)
    _exiger(d.is_valid is not False,
            f"shape key {nom!r} : le driver est invalide après évaluation — "
            f"son chemin ne résout pas ({v.targets[0].data_path})")

    if obj is not None:
        def lire_valeur_evaluee(dg):
            """La valeur PILOTÉE, lue sur la copie évaluée du datablock « Key ».

            ═══ POURQUOI PAS `obj.evaluated_get(dg).data.shape_keys` ═══
            Premier jet : on lisait la valeur à travers l'objet évalué. Or la
            géométrie de la main porte un modificateur d'armature, et le maillage
            ÉVALUÉ d'un objet modifié est un maillage neuf, fabriqué par la pile
            de modificateurs — les shape keys y ont déjà été consommées et son
            `shape_keys` vaut None. `None.key_blocks` lève un AttributeError :
            au lieu d'une MESURE avec un message, la contre-épreuve rendait une
            panne d'un autre genre, sur une ligne qui ne parle pas de drivers.
            Et si d'aventure un `Key` était bien accroché là, rien ne dirait
            que c'est la copie ÉVALUÉE plutôt que l'originale, donc la valeur
            d'avant driver.

            Le driver d'une shape key vit sur le datablock « Key » lui-même
            (`key_blocks[...].value`) : c'est donc la copie évaluée de CE
            datablock qu'il faut lire, et elle seule.

            ═══ SI LA CONTRE-ÉPREUVE ÉCHOUE, REGARDER ICI D'ABORD ═══
            `evaluated_get` ne rend jamais None : faute de copie évaluée, il
            rend le datablock D'ORIGINE, dont la valeur est celle d'avant
            driver. Les deux lectures seraient alors identiques et la
            contre-épreuve dénoncerait un driver muet. On ne pose PAS de garde
            sur ce cas — une garde sur `is not None` ne pourrait pas échouer,
            et une garde sur l'identité des deux datablocks accuserait à tort
            une version de Blender qui répercuterait le driver sur l'original.
            On l'écrit ici pour que le diagnostic commence au bon endroit.
            """
            evaluee = donnees.evaluated_get(dg)
            _exiger(nom in evaluee.key_blocks,
                    f"shape key {nom!r} : absente de la copie évaluée. "
                    f"Formes évaluées : {[b.name for b in evaluee.key_blocks]}")
            return float(evaluee.key_blocks[nom].value)

        _contre_epreuve_driver(
            rig, pbh, propriete, obj,
            lire=lire_valeur_evaluee,
            quoi=f"shape key {nom!r} pilotée par {propriete!r}",
            entrees=(bas, haut))
    return fc


def _contre_epreuve_driver(rig, pbh, propriete, objet_a_rafraichir, lire, quoi,
                           entrees):
    """Deux valeurs d'entrée, deux lectures sur la copie ÉVALUÉE. LÈVE si égales.

    `lire` reçoit le DEPSGRAPH, pas un objet évalué : c'est l'appelant qui sait
    quel datablock porte son driver. Un driver de shape key vit sur le
    datablock « Key », un driver de translation sur l'objet armature ; leur
    faire traverser à tous deux la copie évaluée de l'OBJET GÉOMÉTRIE était une
    erreur de destinataire, et pour la shape key elle levait un AttributeError
    au lieu de mesurer (le maillage évalué d'un objet modifié ne porte plus de
    shape keys du tout).

    `objet_a_rafraichir` ne sert qu'à `rafraichir()` — il peut valoir None.

    ═══ POURQUOI CETTE FONCTION EXISTE ═══
    Règle du dépôt : une sonde qui ne peut pas échouer ne prouve rien. Poser un
    driver et déclarer « c'est piloté » parce qu'aucune exception n'est levée,
    c'est exactement ce qui a laissé passer 25 drivers valides et parfaitement
    inertes. On CHANGE l'entrée, on relit la SORTIE sur la copie évaluée, et si
    la sortie n'a pas bougé on lève au lieu de conclure.

    On restaure la valeur d'origine de la propriété : une contre-épreuve qui
    laisse la main dans une pose de test fausse toutes les mesures suivantes.
    """
    import bpy
    avant = float(pbh[propriete])
    bas, haut = entrees
    lectures = []
    try:
        for entree in (bas, haut):
            pbh[propriete] = float(entree)
            rafraichir(rig, objet_a_rafraichir)
            dg = bpy.context.evaluated_depsgraph_get()
            # `_reel_fini` : une lecture NaN traverserait la comparaison qui
            # suit sans jamais la faire échouer, et le driver muet passerait.
            lectures.append(_reel_fini(lire(dg), f"{quoi} : lecture évaluée"))
    finally:
        pbh[propriete] = avant
        rafraichir(rig, objet_a_rafraichir)
    _exiger(abs(float(pbh[propriete]) - avant) <= TOLERANCE_REGLAGE,
            f"{quoi} : {propriete} n'a pas été RENDUE à sa valeur d'origine "
            f"({avant!r} → {float(pbh[propriete])!r}). Toutes les mesures "
            "suivantes porteraient sur une main restée en pose d'essai.")
    ecart = abs(lectures[1] - lectures[0])
    _exiger(ecart > LONGUEUR_NULLE,
            f"{quoi} : passer {propriete} de {bas} à {haut} ne change RIEN "
            f"({lectures[0]!r} puis {lectures[1]!r}). Le driver n'atteint pas "
            "son canal — un canal muet se lit exactement comme un canal au "
            "repos, c'est le piège le plus coûteux de ce dépôt.")
    return {"entrees": [bas, haut], "sorties": lectures, "ecart": ecart}


# ═══════════════════════════════════════════════════════════════════
#   5 · UN OS CORRECTIF
# ═══════════════════════════════════════════════════════════════════

def ajouter_bone_correctif(eb, nom, parent, centre, direction, roll_cible,
                           longueur=0.012):
    """Crée un os DÉFORMANT, sans contrôleur, décroché de son parent.

    `eb` : `armature.edit_bones` — l'armature DOIT être en mode ÉDITION, c'est
    le seul mode où ces os existent. `roll_cible` est en RADIANS.

    Trois choix, trois raisons :

    · `use_deform = True` — c'est tout l'objet de la pièce : cet os porte des
      poids. Un correctif non déformant serait un os décoratif.

    · `use_connect = False` — un os connecté colle sa tête au bout de son
      parent, et Blender DÉPLACE silencieusement la tête pour l'y coller. Le
      centre qu'on vient de lire dans le fichier de zones serait alors perdu,
      et le correctif agirait à côté de sa zone. C'est le même « Keep Offset »
      que les métacarpiens du dépôt.

    · pas de contrôleur — le correctif est piloté par un driver depuis
      `CTRL_hand`, jamais posé à la main. Un animateur qui pourrait le bouger
      pourrait le désaccorder de la forme sur laquelle il a été réglé.

    Deux refus AVANT création :
    · un nom déjà pris — Blender renomme en «.001» SANS un mot, et le groupe de
      sommets, le driver et l'os ne parlent alors plus du même objet ;
    · une direction nulle — la tête et la queue se confondent, et Blender
      SUPPRIME les os de longueur nulle en quittant le mode édition. L'os
      disparaîtrait après coup, le groupe de poids resterait, et le maillage
      aurait des poids orphelins invisibles à tout contrôle.
    """
    import mathutils
    _exiger(nom not in eb,
            f"l'armature a déjà un os d'édition {nom!r} : Blender renommerait "
            "le nouveau en «.001» sans un mot, et le groupe de sommets, le "
            "driver et l'os cesseraient de désigner la même chose")
    _exiger(parent in eb,
            f"os correctif {nom!r} : parent {parent!r} introuvable. "
            "Un correctif sans parent flotte dans le repère de l'armature et "
            "ne suit pas la chair qu'il corrige.")

    c = mathutils.Vector(_triplet(centre, f"os correctif {nom!r}, centre"))
    d = mathutils.Vector(_triplet(direction, f"os correctif {nom!r}, direction"))
    _exiger(d.length > LONGUEUR_NULLE,
            f"os correctif {nom!r} : direction de longueur nulle. Tête et "
            "queue confondues : Blender SUPPRIME les os de longueur nulle en "
            "quittant le mode édition, l'os s'évaporerait après coup et ses "
            "poids resteraient orphelins.")
    L = _reel_fini(longueur, f"os correctif {nom!r}, longueur")
    _exiger(L > LONGUEUR_NULLE,
            f"os correctif {nom!r} : longueur {L} — même raison, un os de "
            "longueur nulle est supprimé en silence")
    roll = _reel_fini(roll_cible, f"os correctif {nom!r}, roll")

    b = eb.new(nom)
    _exiger(b.name == nom,
            f"os correctif : demandé {nom!r}, Blender a créé {b.name!r} — le "
            "nom a été renommé, tout ce qui le vise pointerait à côté")
    b.head = c
    b.tail = c + d.normalized() * L
    b.roll = roll
    # L'ORDRE COMPTE : `use_connect` D'ABORD, le parent ENSUITE. Poser le parent
    # sur un os encore connecté fait recoller sa tête au bout du parent, et le
    # centre lu dans le fichier de zones est perdu à cet instant — le remettre à
    # False après ne le ramène pas. La contre-épreuve ci-dessous verrait le
    # déplacement, mais on ne fait pas dépendre d'une garde ce qu'un ordre
    # d'écriture rend impossible.
    b.use_connect = False
    b.use_deform = True
    b.parent = eb[parent]

    # Contre-épreuve : la géométrie posée doit être celle qu'on a demandée.
    # `use_connect` mal placé, un parent qui recolle la tête, un `roll`
    # réabsorbé : tout cela se lit ici, pas trois heures plus tard sur un
    # rendu.
    #
    # ═══ POURQUOI 1e-6 m ET NON 1e-9 m ═══
    # On relit ici du SIMPLE PRÉCISION : `head`, `tail` et `mathutils` sont en
    # float 32 bits. Sur une main en mètres, les centres d'os valent 0,05 à
    # 0,2 m, où deux flottants 32 bits consécutifs sont distants de 7 à 15 nm.
    # `b.length` se recalcule par différence de deux coordonnées de cet ordre :
    # son écart à `L` atteint donc couramment quelques nanomètres, sans la
    # moindre faute. Une garde à 1e-9 m aurait crié sur des os parfaitement
    # posés — et une garde qui crie pour une raison étrangère à ce qu'elle
    # surveille finit désarmée. Les fautes visées ici (tête recollée au bout du
    # parent, longueur écrasée) se comptent en MILLIMÈTRES : 0,001 mm les
    # attrape toutes, et n'attrape qu'elles.
    _exiger((b.head - c).length <= TOLERANCE_GEOMETRIE_M,
            f"os correctif {nom!r} : la tête a été DÉPLACÉE de "
            f"{(b.head - c).length * 1000:.4f} mm après parentage — le centre "
            "lu dans le fichier de zones n'est plus respecté")
    _exiger(abs(b.length - L) <= TOLERANCE_GEOMETRIE_M,
            f"os correctif {nom!r} : longueur {b.length!r} m au lieu de {L!r} m "
            f"— écart {abs(b.length - L) * 1000:.4f} mm")
    return b


# ═══════════════════════════════════════════════════════════════════
#   6 · LE MASQUE GÉODÉSIQUE — par les ARÊTES, jamais dans l'espace
# ═══════════════════════════════════════════════════════════════════

def _dijkstra_sur_aretes(adjacence, graines, rayon_max):
    """{sommet: distance PAR LES ARÊTES} pour tout sommet à ≤ `rayon_max`.

    Propagation de coût classique (file de priorité). Aucune coordonnée
    n'intervient ici : seules les LONGUEURS D'ARÊTES entrent, ce qui rend la
    fonction incapable, par construction, de retomber sur une distance
    euclidienne.

    Le rayon borne la propagation : sur une main de 100 mm et une zone de
    12 mm, parcourir tout le maillage pour chaque zone serait du gaspillage,
    mais surtout la coupure est SÛRE — au-delà du rayon de fondu le poids vaut
    zéro, donc rien de ce qu'on abandonne n'aurait été utilisé.
    """
    dist = {}
    tas = []
    for g in graines:
        heapq.heappush(tas, (0.0, g))
    while tas:
        d, i = heapq.heappop(tas)
        if i in dist:
            continue          # déjà réglé par un chemin plus court
        dist[i] = d
        # ═══ PAS DE `.get(i, ())` ICI, MÊME SI L'EFFET SERAIT LE MÊME ═══
        # La règle du dépôt interdit la valeur par défaut sur une lecture, et
        # elle l'interdit dans sa FORME autant que dans son effet : un
        # `.get(cle, defaut)` relu six mois plus tard ne dit pas si le défaut
        # est un fait ou un oubli. Ici c'est un fait — un sommet qu'aucune
        # arête ne touche n'a réellement aucun voisin, ce n'est pas une mesure
        # manquante — et la branche explicite le dit.
        voisins = adjacence[i] if i in adjacence else ()
        for j, L in voisins:
            nd = d + L
            if nd <= rayon_max and j not in dist:
                heapq.heappush(tas, (nd, j))
    return dist


def masque_depuis_adjacence(adjacence, indices_graine, rayon_coeur_m,
                            rayon_fondu_m):
    """Le masque, sur un graphe déjà construit. Cœur à 1,0, fondu linéaire, 0 au-delà.

    Le cœur du §7, isolé de Blender pour être TESTABLE : c'est cette fonction
    que l'autotest de fin de fichier éprouve sur un graphe replié où deux
    sommets sont à 2 mm dans l'espace et à 50 mm sur la surface.
    """
    coeur = _reel_fini(rayon_coeur_m, "rayon_coeur_m")
    fondu = _reel_fini(rayon_fondu_m, "rayon_fondu_m")
    _exiger(coeur >= 0.0, f"rayon de cœur négatif : {coeur}")
    _exiger(fondu > coeur,
            f"rayon de fondu ({fondu}) ≤ rayon de cœur ({coeur}) : le fondu "
            "n'aurait aucune épaisseur et la division qui l'interpole serait "
            "une division par zéro — ou pire, un masque à bord franc qui "
            "produit une arête visible sur la peau")
    graines = list(indices_graine)
    _exiger(graines,
            "masque géodésique sans AUCUNE graine : il rendrait un masque vide, "
            "le transfert de poids ne transférerait rien, et le correctif "
            "serait posé et muet")
    for g in graines:
        _entier_positif(g, "indice de graine")

    # ═══ UNE GRAINE HORS DU GRAPHE : LA GARDE D'AVANT NE POUVAIT PAS LA VOIR ═══
    # Le premier jet contrôlait `dist` non vide APRÈS la propagation, avec pour
    # message « les graines ne sont pas dans le graphe ». C'était une garde
    # AVEUGLE PAR CONSTRUCTION : Dijkstra inscrit chaque graine dans `dist` à la
    # distance 0 avant même de regarder ses voisins, donc `dist` n'est jamais
    # vide dès qu'il y a une graine — la garde ne pouvait pas échouer, et son
    # vert ne disait rien. Le cas qu'elle prétendait attraper — un sommet isolé,
    # sans une seule arête, ou un indice qui n'appartient à aucune arête du
    # maillage — passait donc en silence et rendait un masque d'UN sommet à 1,0 :
    # un correctif pesé sur un point, invisible au rendu, muet à tout contrôle.
    # On contrôle donc ce qu'on voulait contrôler : la graine est-elle dans le
    # graphe des arêtes ? Et on le contrôle AVANT de propager.
    orphelines = [g for g in graines if g not in adjacence]
    _exiger(not orphelines,
            f"masque géodésique : la ou les graines {orphelines} n'appartiennent "
            "à AUCUNE arête du graphe. Elles ne sont donc reliées à aucune "
            "chair : le masque se réduirait à ces sommets seuls, à 1,0, et le "
            "correctif serait pesé sur un point — posé, piloté, et invisible.")

    dist = _dijkstra_sur_aretes(adjacence, graines, fondu)
    _exiger(len(dist) > len(set(graines)),
            "masque géodésique : la propagation n'a atteint AUCUN sommet "
            f"au-delà des graines elles-mêmes ({sorted(set(graines))}). Toutes "
            f"leurs arêtes sont donc plus longues que le rayon de fondu "
            f"({fondu} m) — le maillage n'est pas à l'échelle attendue (la "
            "scène est en MÈTRES) ou le rayon est mille fois trop petit.")

    masque = {}
    for i, d in dist.items():
        if d <= coeur:
            masque[i] = 1.0
        elif d < fondu:
            masque[i] = (fondu - d) / (fondu - coeur)
        # d >= fondu : poids nul. On ne l'inscrit PAS — un poids nul n'est pas
        # un transfert, et une entrée à 0,0 dans le masque ferait croire à un
        # sommet concerné là où il n'y en a pas.
    _exiger(masque,
            "masque géodésique vide : même les graines sont hors du rayon, ce "
            "qui est arithmétiquement impossible sauf graphe incohérent")
    return masque


def _adjacence_du_maillage(obj):
    """Le graphe des arêtes, avec leurs longueurs prises sur le BASIS.

    ═══ POURQUOI LE BASIS, ET PAS LA POSE COURANTE ═══
    Deux raisons, la seconde est la vraie.
    · Une arête s'allonge et se raccourcit avec la pose ; un masque mesuré sur
      une main fléchie ne serait pas celui d'une main tendue, et la
      reconstruction ne retomberait jamais deux fois sur le même masque.
    · Surtout, c'est la même faute que les zones non persistées : la géométrie
      du masque dépendrait d'un état laissé ouvert dans Blender — une pose, une
      sélection — c'est-à-dire de rien que l'on puisse rejouer.
    Le repos est le seul état que deux exécutions partagent avec certitude.
    """
    coords = _coordonnees_basis(obj)
    adjacence = {}
    for e in obj.data.edges:
        a, b = int(e.vertices[0]), int(e.vertices[1])
        pa, pb = coords[a], coords[b]
        L = math.sqrt((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2
                      + (pa[2] - pb[2]) ** 2)
        adjacence.setdefault(a, []).append((b, L))
        adjacence.setdefault(b, []).append((a, L))
    _exiger(adjacence,
            f"{obj.name} n'a aucune arête : il n'y a pas de surface sur "
            "laquelle propager une distance géodésique")
    return adjacence


def masque_geodesique(obj, indices_graine, rayon_coeur_m, rayon_fondu_m):
    """{indice: poids} autour des graines, DISTANCE PAR LES ARÊTES.

    ╔══════════════════════════════════════════════════════════════════════╗
    ║  JAMAIS EUCLIDIENNE. LE TUTORIEL L'ÉCRIT NOIR SUR BLANC.             ║
    ╚══════════════════════════════════════════════════════════════════════╝
    Une main repliée met la pulpe du pouce à deux millimètres de la paume, et
    un doigt fermé met sa peau dorsale contre sa propre peau palmaire. Un
    masque euclidien attrape ces peaux d'en face : le correctif du pli
    palmaire tirerait le dos du doigt, et le défaut apparaîtrait très loin de
    l'endroit qu'on corrige — donc sans que personne ne fasse le lien.

    La distance géodésique, elle, suit la surface : deux peaux opposées sont
    séparées par tout le tour du doigt. C'est la seule mesure qui exprime « la
    même chair ».

    Les poids : 1,0 partout dans le cœur, fondu LINÉAIRE jusqu'au rayon de
    fondu, rien au-delà. Le fondu n'est pas un raffinement esthétique — un
    masque à bord franc pose une arête de poids visible sur la peau, et cette
    arête ne part plus jamais.
    """
    nb = len(obj.data.vertices)
    for g in indices_graine:
        _exiger(_entier_positif(g, "indice de graine") < nb,
                f"graine {g} hors du maillage (0..{nb - 1})")
    return masque_depuis_adjacence(_adjacence_du_maillage(obj), indices_graine,
                                   rayon_coeur_m, rayon_fondu_m)


# ═══════════════════════════════════════════════════════════════════
#   7 · TRANSFÉRER DES POIDS — jamais en créer
# ═══════════════════════════════════════════════════════════════════

def part_transferee(poids_masque, poids_source, maximum):
    """min(maximum × masque, poids_source) — l'arithmétique, isolée et testable.

    Deux propriétés, et ce sont elles qui garantissent le repos :
      · la part ne dépasse JAMAIS le poids disponible sur la source, donc le
        poids retiré ne devient jamais négatif ;
      · la part s'ajoute au correctif ce qu'elle retire à la source, donc la
        SOMME des poids du sommet est rigoureusement inchangée.
    Au repos, tous les os sont à l'identité : un sommet dont la somme des poids
    n'a pas bougé occupe exactement la même position, quelle que soit la
    répartition entre os. C'est la raison arithmétique — et non un réglage
    heureux — pour laquelle l'écart au repos reste sous 0,01 mm.
    """
    m = _reel_fini(poids_masque, "poids de masque")
    w = _reel_fini(poids_source, "poids source")
    mx = _reel_fini(maximum, "maximum")
    _exiger(0.0 <= m <= 1.0, f"poids de masque hors [0,1] : {m}")
    _exiger(w >= 0.0, f"poids source négatif : {w}")
    _exiger(0.0 < mx <= 1.0,
            f"maximum hors ]0,1] : {mx}. À 0 le correctif ne reçoit rien et "
            "reste muet ; au-delà de 1 on prétendrait transférer plus que tout "
            "le poids d'un sommet.")
    return min(mx * m, w)


def _indice_groupe(obj, nom, quoi):
    _exiger(nom in obj.vertex_groups,
            f"{quoi} : {obj.name} n'a pas de groupe de sommets {nom!r}. "
            f"Groupes présents : {sorted(g.name for g in obj.vertex_groups)}")
    return obj.vertex_groups[nom].index


def _poids_si_present(sommet, indice_groupe):
    """(présent, poids) — et JAMAIS un zéro fabriqué.

    ═══ LE SEUL ZÉRO ADMIS DE CE FICHIER, ET POURQUOI IL N'EN EST PAS UN ═══
    Blender stocke les poids de façon creuse : un sommet qui n'appartient pas à
    un groupe n'a tout simplement pas d'entrée pour lui. Ce n'est pas une
    mesure manquante, c'est un FAIT de structure. On rend quand même le couple
    (présent, poids) plutôt qu'un `0.0` déguisé, pour que l'appelant décide —
    et ici il SAUTE le sommet au lieu de lui transférer zéro, ce qui évite
    d'inscrire dans le groupe correctif des entrées de poids nul qui feraient
    croire à une zone plus large qu'elle n'est.
    """
    for g in sommet.groups:
        if g.group == indice_groupe:
            return True, float(g.weight)
    return False, None


def transferer_vers_correctif(obj, masque, source, correctif, maximum=0.35):
    """TRANSFÈRE une part des poids de `source` vers `correctif`. N'en crée pas.

    ╔══════════════════════════════════════════════════════════════════════╗
    ║  TRANSFÉRER, ET SURTOUT PAS AJOUTER.                                 ║
    ╚══════════════════════════════════════════════════════════════════════╝
    Ajouter du poids à un correctif sans en retirer au parent change la SOMME
    des poids du sommet. Le modificateur d'armature normalise implicitement à
    la somme : un sommet dont la somme passe de 1,0 à 1,35 se retrouve tiré
    différemment DÈS LE REPOS. La main, au repos, ne serait plus la main de
    référence — et toutes les mesures du dépôt, qui comparent une pose au
    repos, deviendraient fausses d'un coup, sans rien de visible.

    D'où la forme imposée :
        w_corr = min(maximum × masque, w_src)   puis   w_src -= w_corr
    La somme est conservée sommet par sommet, exactement, et l'écart au repos
    reste sous 0,01 mm par ARITHMÉTIQUE, pas par chance.

    `correctif` est créé s'il n'existe pas — un groupe de sommets vide n'est
    pas une mesure absente, c'est le point de départ normal d'un correctif
    neuf. `source`, en revanche, doit exister : un nom de parent mal orthographié
    est une faute, pas un cas.
    """
    _exiger(isinstance(masque, dict) and masque,
            "transfert : masque vide ou absent. Rien ne serait transféré, le "
            "correctif serait posé, pesé à zéro et définitivement muet.")
    mx = _reel_fini(maximum, "maximum")
    i_src = _indice_groupe(obj, source, "transfert")
    g_src = obj.vertex_groups[source]
    sommets = obj.data.vertices
    nb = len(sommets)

    # Les indices du masque sont validés UNE FOIS, ici, et c'est cette table qui
    # sert ensuite. `_indice_sommet` et non `int(i)` : `int(3.7)` rend 3 sans un
    # mot, et le transfert pèserait un sommet voisin — faute parfaitement
    # invisible, puisque la contre-épreuve relirait à son tour le sommet 3 et le
    # trouverait juste. Et deux écritures du même sommet (3 et "3") s'écraseraient
    # l'une l'autre en silence : on les refuse.
    indices = {}
    for i, m in masque.items():
        idx = _indice_sommet(i, "transfert, indice du masque")
        _exiger(idx < nb, f"transfert : indice {idx} hors du maillage "
                          f"(0..{nb - 1})")
        _exiger(idx not in indices,
                f"transfert : le sommet {idx} apparaît DEUX FOIS dans le masque "
                "(une fois en entier, une fois en chaîne) — l'un des deux poids "
                "serait perdu sans un mot")
        indices[idx] = m

    # ═══ LE POINT AVEUGLE DE LA CONTRE-ÉPREUVE, FERMÉ ICI ═══
    # La contre-épreuve de fin compare `w_cor + w_new` au poids que la SOURCE
    # portait avant l'écriture. Elle ne sait rien de ce que le CORRECTIF portait
    # déjà — et `add(..., "REPLACE")` l'efface. Deuxième passage sur la même
    # zone : la source vaut 0,65, le correctif 0,35 ; on retransfère 0,35, la
    # source tombe à 0,30, le correctif est REMPLACÉ par 0,35, et la somme du
    # sommet passe de 1,00 à 0,65. Du poids DISPARAÎT — le repos bouge, donc
    # toutes les mesures qui le prennent pour origine deviennent fausses — et la
    # contre-épreuve trouve tout juste, parce qu'elle mesure la seule moitié de
    # l'affaire qu'elle connaît. Une garde calibrée pour ne pas voir sa propre
    # faute ne vaut pas mieux que pas de garde.
    # On refuse donc AVANT d'écrire un correctif qui porte déjà du poids sur la
    # zone. La contre-épreuve de fin n'est valide QUE parce que ce refus la
    # précède : ne pas retirer l'un sans retirer l'autre.
    # Le refus passe AVANT la création du groupe : un appel qui échoue ne doit
    # pas laisser un groupe de sommets vide derrière lui, que le contrôle
    # suivant prendrait pour un correctif posé.
    if correctif in obj.vertex_groups:
        g_cor = obj.vertex_groups[correctif]
        i_deja = g_cor.index
        deja_pesants = []
        for idx in indices:
            present_cor, w_deja = _poids_si_present(sommets[idx], i_deja)
            if present_cor and w_deja > 0.0:
                deja_pesants.append(idx)
        _exiger(not deja_pesants,
                f"transfert {source!r} → {correctif!r} : le groupe {correctif!r} "
                f"porte DÉJÀ du poids sur {len(deja_pesants)} sommet(s) du "
                f"masque (par exemple {deja_pesants[:5]}). Un second transfert "
                "le REMPLACERAIT au lieu de s'y ajouter, et la somme des poids "
                "du sommet DIMINUERAIT d'autant : la main au repos ne serait "
                "plus la main de référence. Repartez du .blend de référence, ou "
                "supprimez explicitement le groupe avant de retransférer.")
    else:
        g_cor = obj.vertex_groups.new(name=correctif)
    _exiger(g_cor.name == correctif,
            f"transfert : groupe demandé {correctif!r}, créé {g_cor.name!r} — "
            "Blender l'a renommé, l'os et le groupe ne se correspondraient plus")
    i_cor = g_cor.index

    attendus, touches = {}, 0
    total_transfere, pire_part = 0.0, 0.0
    sans_source = 0

    for idx, m in indices.items():
        present, w_src = _poids_si_present(sommets[idx], i_src)
        if not present:
            # Le sommet n'appartient pas au parent : il n'y a RIEN à lui
            # prendre. On le saute — on ne lui fabrique pas un poids de zéro,
            # et on ne lui en crée surtout pas un.
            sans_source += 1
            continue
        part = part_transferee(m, w_src, mx)
        if part <= 0.0:
            continue
        reste = w_src - part
        g_cor.add([idx], part, "REPLACE")
        g_src.add([idx], reste, "REPLACE")
        attendus[idx] = (w_src, part, reste)
        touches += 1
        total_transfere += part
        pire_part = max(pire_part, part)

    _exiger(touches > 0,
            f"transfert {source!r} → {correctif!r} : AUCUN sommet transféré "
            f"sur {len(masque)} du masque ({sans_source} n'appartiennent pas à "
            f"{source!r}). Un correctif sans poids se pose, se pilote, et ne "
            "déforme rien — panne parfaitement muette.")

    # ═══ CONTRE-ÉPREUVE : ON RELIT CE QU'ON VIENT D'ÉCRIRE ═══
    # `vertex_groups.add` peut échouer sans lever (mode d'objet inattendu,
    # groupe verrouillé). Et surtout, c'est ici qu'on vérifie la propriété qui
    # tient tout le §7 : la somme des poids du sommet est INCHANGÉE. Si elle a
    # bougé, le repos a bougé, et toutes les mesures du dépôt sont fausses.
    #
    # ATTENTION : `w_src` est le poids de la SOURCE avant écriture, et la somme
    # relue `w_cor + w_new` ne lui est comparable que parce que le refus posé
    # plus haut garantit que le correctif ne portait RIEN sur ces sommets. Ces
    # deux morceaux ne se séparent pas : sans le refus, cette ligne déclarerait
    # la somme conservée alors qu'elle aurait fondu.
    pire_somme = 0.0
    for idx, (w_src, part, reste) in attendus.items():
        p_cor, w_cor = _poids_si_present(sommets[idx], i_cor)
        p_new, w_new = _poids_si_present(sommets[idx], i_src)
        _exiger(p_cor, f"transfert : le sommet {idx} n'a PAS reçu de poids "
                       f"dans {correctif!r} — l'écriture n'a pas pris")
        _exiger(p_new, f"transfert : le sommet {idx} a perdu toute entrée dans "
                       f"{source!r} au lieu d'être réduit")
        _exiger(abs(w_cor - part) <= TOLERANCE_POIDS,
                f"transfert : sommet {idx}, poids correctif relu {w_cor!r} au "
                f"lieu de {part!r}")
        _exiger(abs(w_new - reste) <= TOLERANCE_POIDS,
                f"transfert : sommet {idx}, poids source relu {w_new!r} au "
                f"lieu de {reste!r}")
        pire_somme = max(pire_somme, abs((w_cor + w_new) - w_src))
    _exiger(pire_somme <= TOLERANCE_POIDS,
            f"transfert {source!r} → {correctif!r} : la somme des poids a "
            f"bougé de {pire_somme:.3e} sur au moins un sommet. Du poids a été "
            "CRÉÉ au lieu d'être déplacé : la main au repos n'est plus la main "
            "de référence, et toutes les mesures qui la prennent pour origine "
            "deviennent fausses en silence.")

    rafraichir(obj)
    return {"source": source, "correctif": correctif,
            "sommets_du_masque": len(masque),
            "sommets_transferes": touches,
            "sommets_hors_source": sans_source,
            "poids_total_transfere": total_transfere,
            "part_maximale": pire_part,
            "ecart_de_somme_maximal": pire_somme}


# ═══════════════════════════════════════════════════════════════════
#   8 · TRANSLATION LINÉAIRE PILOTÉE
# ═══════════════════════════════════════════════════════════════════

def driver_translation_lineaire(rig, nom_os, axe, SIDE, propriete, amplitude_m):
    """`location[axe] = p × amplitude_m`, où `p` est une propriété de la main.

    La SEULE forme d'expression prouvée valide dans ce dépôt : une variable,
    une constante, un produit. Pas de `min`, pas de `max`, pas de parenthèses,
    pas de seconde variable — l'évaluateur simple de Blender les refuse EN
    SILENCE, et c'est ainsi que 25 drivers valides sont restés inertes pendant
    deux exécutions de plus d'une heure.

    `amplitude_m` est en MÈTRES et sur l'axe LOCAL de l'os : un correctif de
    volume déplace la chair de quelques millimètres, pas de quelques
    centimètres. La constante est écrite en décimal, jamais en notation
    exponentielle, parce que le `e` de `1e-05` n'est pas de l'arithmétique.

    Contre-épreuve OBLIGATOIRE en fin de fonction : on met la propriété aux
    deux bouts de sa course, on relit `location[axe]` sur la copie ÉVALUÉE, et
    on LÈVE si les deux lectures sont égales. Un driver qu'on ne voit pas
    bouger n'est pas un driver, c'est une intention.
    """
    _exiger(axe in (0, 1, 2), f"axe de translation {axe!r} : attendu 0, 1 ou 2")
    pbh = _exiger_propriete(rig, SIDE, propriete)
    _exiger(nom_os in rig.pose.bones,
            f"{rig.name} n'a pas d'os de pose {nom_os!r} : le driver viserait "
            "un chemin qui ne résout pas, et une cible absente se lit 0.0")
    amp = _reel_fini(amplitude_m, f"amplitude de {nom_os!r}")
    constante = _constante_texte(amp, f"amplitude de {nom_os!r}")

    chemin = f'pose.bones["{_echapper(nom_os)}"].location'
    _refuser_driver_existant(rig, chemin, axe, f"translation de {nom_os!r}")

    pb = rig.pose.bones[nom_os]
    fc = pb.driver_add("location", axe)
    d = fc.driver
    d.type = "SCRIPTED"
    v = d.variables.new()
    v.name = "p"
    v.type = "SINGLE_PROP"
    v.targets[0].id = rig
    v.targets[0].data_path = (f'pose.bones["{_echapper(f"CTRL_hand{SIDE}")}"]'
                              f'["{_echapper(propriete)}"]')
    expression = f"p * {constante}"
    _exiger_expression_lineaire(expression, {"p"})
    d.expression = expression

    rafraichir(rig)
    _exiger(d.is_valid is not False,
            f"translation de {nom_os!r} : driver invalide après évaluation. "
            f"Expression {expression!r}, cible {v.targets[0].data_path!r}.")

    # ═══ LA CONTRE-ÉPREUVE, SUR LA COPIE ÉVALUÉE ═══
    # Lire `rig.pose.bones[...].location` sur l'objet D'ORIGINE rendrait la
    # valeur d'avant driver : les drivers écrivent dans la copie évaluée du
    # graphe de dépendances. C'est la même faute que lire `bone.head_local`
    # pour une position posée — on lit le repos et on croit lire le résultat.
    #
    # C'est `_contre_epreuve_driver` qui mène la manœuvre — un seul exemplaire
    # du couple « je change l'entrée, je relis la sortie évaluée, je RENDS la
    # propriété à sa valeur » pour les deux sortes de drivers de ce module. Deux
    # copies de cette mécanique, c'est deux occasions d'en laisser une derrière.
    #
    # Les entrées sont 0 et 1 et ne peuvent pas être autre chose : le contrôle
    # d'amplitude qui suit compare la course mesurée à `amp`, et cela n'a de
    # sens que pour une variation de la propriété égale à UN (l'expression vaut
    # `p * amp`, la course vaut donc `Δp × amp`).
    mesure = _contre_epreuve_driver(
        rig, pbh, propriete, None,
        lire=lambda dg: float(
            rig.evaluated_get(dg).pose.bones[nom_os].location[axe]),
        quoi=f"translation de {nom_os!r} sur l'axe {axe} pilotée par {propriete!r}",
        entrees=(0.0, 1.0))
    bouge = mesure["ecart"]
    # Tolérance : la course est relue en simple précision, et 1e-6 m = 0,001 mm
    # reste cent fois plus fin que le plus petit correctif de volume utile. La
    # faute visée — un second driver, une contrainte ou une butée qui réécrit ce
    # canal — change la course de plusieurs dixièmes de millimètre au moins.
    _exiger(abs(bouge - abs(amp)) <= max(TOLERANCE_GEOMETRIE_M,
                                         abs(amp) * 1e-4),
            f"translation de {nom_os!r} : course mesurée {bouge!r} m pour une "
            f"amplitude demandée de {amp!r} m. Un autre driver, une contrainte "
            "ou une butée réécrit ce canal.")
    return fc


# ═══════════════════════════════════════════════════════════════════
#   9 · LES ZONES, PERSISTÉES ET RELUES
# ═══════════════════════════════════════════════════════════════════

def chemin_zones(racine, SIDE):
    """`<racine>/assets/correctifs/zones-main<SIDE>.json` — un seul exemplaire."""
    return os.path.join(racine, DOSSIER_CORRECTIFS, f"zones-main{SIDE}.json")


def chemin_shape(racine, SIDE, nom):
    """`<racine>/assets/correctifs/<nom>-main<SIDE>.json`."""
    return os.path.join(racine, DOSSIER_CORRECTIFS, f"{nom}-main{SIDE}.json")


def _valider_zone(nom, zone, nb_sommets):
    """Contrôle PUR d'une zone, à l'écriture comme à la lecture.

    Les sept clés sont EXIGÉES parce que c'est exactement ce qu'il faut pour
    reconstruire la zone et son os sans jamais consulter l'état courant de
    Blender. Une zone qui ne porterait que son masque obligerait à retrouver le
    centre de l'os autrement — c'est-à-dire depuis une sélection ouverte dans
    une session, donc depuis un état que personne ne peut rejouer. Le rig
    cesserait d'être reproductible, et il ne s'en apercevrait qu'au rendu
    suivant.
    """
    for cle in CLES_ZONE:
        _indexer(zone, cle, f"zone {nom!r}")

    graines = zone["graines"]
    _exiger(isinstance(graines, list) and graines,
            f"zone {nom!r} : « graines » vide ou absente — le masque ne "
            "pourrait pas être recalculé et l'on ne saurait plus d'où il vient")
    for g in graines:
        _exiger(_entier_positif(g, f"zone {nom!r}, graine") < nb_sommets,
                f"zone {nom!r} : graine {g} hors du maillage (0..{nb_sommets - 1})")

    coeur = _reel_fini(zone["rayon_coeur_m"], f"zone {nom!r}, rayon_coeur_m")
    fondu = _reel_fini(zone["rayon_fondu_m"], f"zone {nom!r}, rayon_fondu_m")
    _exiger(coeur >= 0.0, f"zone {nom!r} : rayon de cœur négatif")
    _exiger(fondu > coeur,
            f"zone {nom!r} : rayon de fondu ({fondu}) ≤ rayon de cœur ({coeur})")

    _triplet(zone["centre"], f"zone {nom!r}, centre")
    d = _triplet(zone["direction"], f"zone {nom!r}, direction")
    _exiger(math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2) > LONGUEUR_NULLE,
            f"zone {nom!r} : direction de longueur nulle — l'os correctif "
            "serait de longueur nulle et Blender le SUPPRIMERAIT en silence")
    _reel_fini(zone["roll_rad"], f"zone {nom!r}, roll_rad")

    masque = zone["masque"]
    _exiger(isinstance(masque, dict) and masque,
            f"zone {nom!r} : masque vide — le correctif serait pesé à zéro")
    propre = {}
    for cle, poids in masque.items():
        i = _indice_sommet(cle, f"zone {nom!r}, indice de masque")
        _exiger(0 <= i < nb_sommets,
                f"zone {nom!r} : indice {i} hors du maillage "
                f"(0..{nb_sommets - 1}) — le maillage a changé sous le fichier")
        # Un masque en mémoire peut porter 3 ET "3" : les deux se ramènent au
        # même sommet, et sans ce refus la seconde entrée écraserait la
        # première SANS UN MOT — un poids perdu se lit comme un poids qui n'a
        # jamais existé. `_valider_charge_sparse` fait déjà ce refus sur les
        # deltas ; il manquait ici, sur les masques.
        _exiger(i not in propre,
                f"zone {nom!r} : le sommet {i} apparaît DEUX FOIS dans le "
                "masque (une fois en entier, une fois en chaîne). L'une des "
                "deux valeurs serait perdue en silence.")
        w = _reel_fini(poids, f"zone {nom!r}, poids du sommet {i}")
        _exiger(0.0 < w <= 1.0,
                f"zone {nom!r} : poids {w} au sommet {i}, hors ]0,1]. Un poids "
                "nul inscrit dans un masque fait croire à un sommet concerné "
                "là où il n'y en a pas.")
        propre[i] = w
    return propre


def sauver_zones(chemin, zones, sha, nb_sommets=None):
    """Écrit les masques et la géométrie des zones. `nb_sommets` est OBLIGATOIRE.

    Voir l'en-tête du module : l'argument porte `None` par défaut uniquement
    pour lever avec une phrase utile plutôt qu'un `TypeError`. Sans lui,
    `charger_zones` ne pourrait pas refaire le contrôle du nombre de sommets
    que le cahier exige, et ce contrôle serait un trou silencieux.
    """
    _exiger(nb_sommets is not None,
            "sauver_zones : passez le nombre de sommets — "
            "sauver_zones(chemin, zones, sha, len(geo.data.vertices)). Sans "
            "lui, la relecture ne pourrait pas refuser un maillage dont le "
            "nombre de sommets a changé.")
    nb = _entier_positif(nb_sommets, "nb_sommets")
    _exiger(nb > 0, "sauver_zones : un maillage de zéro sommet")
    _exiger(isinstance(sha, str) and len(sha) == 64,
            f"sauver_zones : empreinte {sha!r} — on attend un sha256 "
            "hexadécimal de 64 caractères, pas un chemin de fichier ni une date")
    _exiger(isinstance(zones, dict) and zones,
            "sauver_zones : aucune zone. Un fichier de zones vide se relirait "
            "sans erreur et la reconstruction n'aurait plus aucun correctif, "
            "sans que rien ne le dise.")

    sorties = {}
    for nom, zone in zones.items():
        # On écrit le masque VALIDÉ que rend `_valider_zone`, jamais une
        # seconde conversion des clés brutes : deux conversions séparées du
        # même masque, c'est deux règles qui peuvent diverger, et celle qui
        # écrit sur le disque gagnerait sans qu'on le sache.
        masque_valide = _valider_zone(nom, zone, nb)
        copie = dict(zone)     # les clés supplémentaires sont conservées
        copie["graines"] = [int(g) for g in zone["graines"]]
        copie["masque"] = {str(k): float(v) for k, v in masque_valide.items()}
        copie["centre"] = _triplet(zone["centre"], f"zone {nom!r}, centre")
        copie["direction"] = _triplet(zone["direction"], f"zone {nom!r}, direction")
        copie["rayon_coeur_m"] = float(zone["rayon_coeur_m"])
        copie["rayon_fondu_m"] = float(zone["rayon_fondu_m"])
        copie["roll_rad"] = float(zone["roll_rad"])
        sorties[nom] = copie

    charge = {"mesh_vertex_count": nb,
              "mesh_source_sha256": sha,
              "space": ESPACE_DELTAS,
              "zones": sorties}

    dossier = os.path.dirname(os.path.abspath(chemin))
    if dossier:
        os.makedirs(dossier, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(charge, f, ensure_ascii=False, indent=1, sort_keys=True)
    return {"chemin": chemin, "zones": len(sorties),
            "sommets": sum(len(z["masque"]) for z in sorties.values())}


def charger_zones(chemin, sha, nb_sommets=None):
    """Relit les zones et REFUSE si le maillage n'est plus le même.

    Rend `{nom: zone}` avec les masques réindexés en entiers et les graines en
    entiers — c'est-à-dire prêts pour `transferer_vers_correctif` et
    `ajouter_bone_correctif`, sans qu'aucun centre ne vienne d'une sélection
    laissée ouverte dans une session Blender.

    Deux refus, et le second suffirait presque : l'empreinte commence par le
    nombre de sommets, donc un maillage qui en perd un change forcément
    d'empreinte. On garde quand même les deux — le contrôle du compte se lit,
    se comprend et nomme la panne, là où une empreinte différente ne dit que
    « quelque chose a changé ».
    """
    _exiger(nb_sommets is not None,
            "charger_zones : passez le nombre de sommets — "
            "charger_zones(chemin, sha, len(geo.data.vertices)). Sans lui, le "
            "contrôle du nombre de sommets exigé par le cahier serait un trou "
            "silencieux.")
    nb = _entier_positif(nb_sommets, "nb_sommets")
    _exiger(os.path.isfile(chemin),
            f"fichier de zones introuvable : {chemin}. Les masques sont "
            "persistés et RELUS à chaque reconstruction ; sans ce fichier, les "
            "centres des os correctifs dépendraient d'une sélection restée "
            "ouverte dans Blender, c'est-à-dire de rien de reproductible.")
    with open(chemin, "r", encoding="utf-8") as f:
        charge = json.load(f)

    compte = _indexer(charge, "mesh_vertex_count", "fichier de zones")
    empreinte = _indexer(charge, "mesh_source_sha256", "fichier de zones")
    espace = _indexer(charge, "space", "fichier de zones")
    brutes = _indexer(charge, "zones", "fichier de zones")

    _exiger(espace == ESPACE_DELTAS,
            f"fichier de zones : espace {espace!r} au lieu de {ESPACE_DELTAS!r}")
    _exiger(compte == nb,
            f"fichier de zones : {compte} sommets décrits, {nb} dans l'objet. "
            "Le maillage a changé sous les masques : les indices ne désignent "
            "plus les mêmes sommets, et les appliquer peserait des sommets "
            "quelconques sans que rien ne se signale.")
    _exiger(empreinte == sha,
            f"fichier de zones : empreinte {empreinte} ≠ {sha}. Topologie ou "
            "Basis changés — on refuse de continuer.")
    _exiger(isinstance(brutes, dict) and brutes,
            "fichier de zones : aucune zone dedans")

    zones = {}
    for nom, zone in brutes.items():
        masque = _valider_zone(nom, zone, nb)
        sortie = dict(zone)
        sortie["masque"] = masque
        sortie["graines"] = [int(g) for g in zone["graines"]]
        zones[nom] = sortie
    return zones


# ═══════════════════════════════════════════════════════════════════
#   AUTOTEST — la partie PURE, hors Blender
#
#   `python3 atelier/correctifs.py`   → code 0 si tout passe, 1 sinon.
#
#   Ce que ce test défend, et pourquoi il ne peut pas passer par accident :
#     · chaque refus du format JSON creux est EXERCÉ, un par un. Un contrôle
#       qu'on n'a jamais vu échouer n'est pas un contrôle ;
#     · le masque est éprouvé sur un graphe REPLIÉ où deux sommets sont à 2 mm
#       dans l'espace et à 50 mm par les arêtes. Si quelqu'un remet une
#       distance euclidienne, l'assertion tombe ;
#     · et le test se contre-éprouve lui-même : il VÉRIFIE d'abord que les deux
#       sommets sont bel et bien proches dans l'espace. Sans cela, il passerait
#       aussi sur un graphe où ils sont loin partout — c'est-à-dire pour la
#       mauvaise raison, ce qui est la faute que ce dépôt a payée le plus cher.
# ═══════════════════════════════════════════════════════════════════

# ═══ LE COMPTE ANNONCÉ NE PEUT PLUS DIVERGER DE CE QUI EST EXERCÉ ═══
# Le premier jet annonçait « 4 + len(CLES_ZONE) + 3 » = 14 refus là où le test
# en exerçait 13 : un nombre écrit à la main, recalculé de tête, jamais remesuré.
# C'est exactement la faute de sur-comptage que ce dépôt traîne — un rapport qui
# annonce plus que ce qu'il a fait. Le compte est désormais tenu PAR les refus
# eux-mêmes : chaque refus réellement exercé s'inscrit ici, et le test n'annonce
# que la longueur de cette liste.
_REFUS_EXERCES = []


def _leve_bien(quoi, fonction, motif):
    """Exige qu'un appel LÈVE. Un contrôle qui ne peut pas échouer ne prouve rien."""
    try:
        fonction()
    except RuntimeError as e:
        _exiger(motif.lower() in str(e).lower(),
                f"{quoi} : a bien levé, mais sur un autre motif que "
                f"{motif!r} — message reçu : {e}")
        _REFUS_EXERCES.append(quoi)
        return str(e)
    raise RuntimeError(f"{quoi} : N'A PAS LEVÉ alors qu'il aurait dû. "
                       "Le refus annoncé est un trou.")


def _autotest_expression():
    debut = len(_REFUS_EXERCES)
    _exiger_expression_lineaire("p * 0.004", {"p"})
    _exiger_expression_lineaire("a * 1.12 + b * 0.9 - 0.18", {"a", "b"})
    _leve_bien("min/max dans une expression",
               lambda: _exiger_expression_lineaire("min(p, 1.0) * 0.004", {"p"}),
               "caractères interdits")
    _leve_bien("produit de deux variables",
               lambda: _exiger_expression_lineaire("p * q", {"p", "q"}),
               "2 variables")
    _leve_bien("variable non déclarée",
               lambda: _exiger_expression_lineaire("p + z", {"p"}),
               "non déclaré")
    _leve_bien("notation exponentielle",
               lambda: _exiger_expression_lineaire("p * 1e-5", {"p"}),
               "non déclaré")
    _exiger(_constante_texte(0.004, "essai") == "0.004",
            "constante 0.004 mal écrite")
    t = _constante_texte(1e-5, "essai")
    _exiger("e" not in t and abs(float(t) - 1e-5) < 1e-15,
            f"constante 1e-5 écrite {t!r} : exponentielle ou imprécise")
    _leve_bien("constante qui s'arrondit à zéro",
               lambda: _constante_texte(1e-15, "essai"), "zéro")
    _leve_bien("valeur non finie",
               lambda: _reel_fini(float("nan"), "essai"), "non finie")
    _leve_bien("clé absente lue sans défaut",
               lambda: _indexer({"a": 1}, "b", "essai"), "absente")
    # Un indice de sommet flottant se TRONQUE en silence si on le passe à
    # `int()` : on exige qu'il soit refusé, sans quoi le delta ou le poids
    # atterrirait sur le sommet d'à côté sans que rien ne le dise.
    _exiger(_indice_sommet(12, "essai") == 12, "indice entier mal lu")
    _exiger(_indice_sommet("12", "essai") == 12, "indice en chaîne mal lu")
    _leve_bien("indice de sommet flottant",
               lambda: _indice_sommet(3.7, "essai"), "tronquerait")
    _leve_bien("indice de sommet en chaîne flottante",
               lambda: _indice_sommet("3.7", "essai"), "tronqué")
    _leve_bien("indice de sommet négatif",
               lambda: _indice_sommet(-1, "essai"), "négatif")
    print(f"  · expressions, constantes, lectures sans défaut, indices : "
          f"{len(_REFUS_EXERCES) - debut} refus exercés")


def _autotest_format_sparse():
    debut = len(_REFUS_EXERCES)
    sha = "f" * 64
    bonne = {"name": "CORR_thenar",
             "mesh_vertex_count": 2048,
             "mesh_source_sha256": sha,
             "space": ESPACE_DELTAS,
             "source_pose": {"Fist": 1.0},
             "deltas": {"1024": [0.001, -0.0005, 0.0]}}
    deltas = _valider_charge_sparse(bonne, "CORR_thenar", 2048, sha)
    _exiger(deltas == {1024: [0.001, -0.0005, 0.0]},
            f"deltas relus faux : {deltas}")

    def sans(cle):
        c = dict(bonne)
        del c[cle]
        return lambda: _valider_charge_sparse(c, "CORR_thenar", 2048, sha)

    for cle in ("name", "mesh_vertex_count", "mesh_source_sha256", "space",
                "source_pose", "deltas"):
        _leve_bien(f"clé {cle!r} manquante", sans(cle), "absente")

    _leve_bien("mauvais nom",
               lambda: _valider_charge_sparse(bonne, "CORR_autre", 2048, sha),
               "on attendait")
    _leve_bien("mauvais nombre de sommets",
               lambda: _valider_charge_sparse(bonne, "CORR_thenar", 2047, sha),
               "topologie différente")
    _leve_bien("mauvaise empreinte",
               lambda: _valider_charge_sparse(bonne, "CORR_thenar", 2048, "0" * 64),
               "changés")
    mauvais_espace = dict(bonne, space="WORLD")
    _leve_bien("mauvais espace",
               lambda: _valider_charge_sparse(mauvais_espace, "CORR_thenar",
                                              2048, sha),
               "espace")
    hors = dict(bonne, deltas={"9999": [0.0, 0.0, 0.001]})
    _leve_bien("indice hors du maillage",
               lambda: _valider_charge_sparse(hors, "CORR_thenar", 2048, sha),
               "hors du maillage")
    tronque = dict(bonne, deltas={"12": [0.001, 0.0]})
    _leve_bien("delta à deux composantes",
               lambda: _valider_charge_sparse(tronque, "CORR_thenar", 2048, sha),
               "trois composantes")
    print(f"  · format JSON creux : {len(_REFUS_EXERCES) - debut} refus "
          "exercés, aucun n'est un trou")


def _graphe_replie():
    """Une bande repliée en épingle : loin par la surface, proche dans l'espace.

    Onze sommets. Les six premiers s'éloignent en ligne droite, les cinq
    suivants reviennent à 2 mm au-dessus. Le sommet 10 se retrouve donc à 2 mm
    du sommet 0 DANS L'ESPACE, et à plus de 50 mm de lui PAR LES ARÊTES.

    C'est le cas exact que le tutoriel décrit : deux peaux opposées, la
    palmaire et la dorsale d'un doigt fermé, ou la pulpe du pouce contre la
    paume. Un masque euclidien les confond.
    """
    coords = [(0.005 * i, 0.0, 0.0) for i in range(6)]
    coords += [(0.005 * (10 - i), 0.002, 0.0) for i in range(6, 11)]
    aretes = [(i, i + 1) for i in range(10)]
    adjacence = {}
    for a, b in aretes:
        pa, pb = coords[a], coords[b]
        L = math.dist(pa, pb)
        adjacence.setdefault(a, []).append((b, L))
        adjacence.setdefault(b, []).append((a, L))
    return coords, adjacence


def _autotest_masque_geodesique():
    debut = len(_REFUS_EXERCES)
    coords, adjacence = _graphe_replie()
    coeur, fondu = 0.004, 0.012

    # ═══ CONTRE-ÉPREUVE DU TEST LUI-MÊME ═══
    # Si les deux extrémités n'étaient PAS proches dans l'espace, l'assertion
    # qui suit passerait sans rien prouver — un test vert pour la mauvaise
    # raison, exactement la faute que ce dépôt a payée le plus cher.
    d_espace = math.dist(coords[0], coords[10])
    _exiger(d_espace < coeur,
            f"le graphe d'essai est mal construit : les sommets 0 et 10 sont à "
            f"{d_espace * 1000:.2f} mm dans l'espace, il les faut à moins de "
            f"{coeur * 1000:.1f} mm pour qu'un masque euclidien les confonde. "
            "Sans cela, le test ne pourrait pas distinguer géodésique et "
            "euclidien, et son vert ne vaudrait rien.")

    masque = masque_depuis_adjacence(adjacence, [0], coeur, fondu)

    # ═══ L'ASSERTION QUI TOMBE SI LA DISTANCE REDEVIENT EUCLIDIENNE ═══
    _exiger(10 not in masque,
            f"LE MASQUE EST REDEVENU EUCLIDIEN. Le sommet 10 est à "
            f"{d_espace * 1000:.2f} mm du sommet 0 dans l'espace — donc dans "
            f"le cœur — mais à {5 * 0.005 + math.dist(coords[5], coords[6]) + 4 * 0.005:.4f} m "
            "de lui PAR LES ARÊTES, donc hors de la zone. Le tutoriel l'écrit "
            "noir sur blanc : deux peaux opposées se touchent dans l'espace et "
            "sont éloignées sur la surface. Un masque euclidien lui donnerait "
            "1,0 et le correctif du pli palmaire tirerait le dos du doigt.")
    for i in (6, 7, 8, 9, 10):
        _exiger(i not in masque,
                f"sommet {i} : à plus de 20 mm par les arêtes, il n'a rien à "
                "faire dans un masque de 12 mm")

    # Les valeurs exactes du fondu linéaire, terme à terme.
    attendu = {0: 1.0,
               1: (fondu - 0.005) / (fondu - coeur),
               2: (fondu - 0.010) / (fondu - coeur)}
    _exiger(set(masque) == set(attendu),
            f"masque = {sorted(masque)}, attendu {sorted(attendu)}")
    for i, w in attendu.items():
        _exiger(abs(masque[i] - w) < 1e-12,
                f"sommet {i} : poids {masque[i]!r}, attendu {w!r}")

    # Un cœur plus large : le sommet 1 doit basculer à 1,0 exactement.
    large = masque_depuis_adjacence(adjacence, [0], 0.006, fondu)
    _exiger(large[1] == 1.0,
            f"cœur à 6 mm : le sommet 1 (à 5 mm) devrait valoir 1,0, il vaut "
            f"{large[1]!r}")

    # Deux graines : la distance est celle de la PLUS PROCHE, pas de la première.
    deux = masque_depuis_adjacence(adjacence, [0, 10], coeur, fondu)
    _exiger(deux[10] == 1.0 and deux[9] > 0.0,
            "avec une graine en 10, son voisinage doit entrer dans le masque")

    # Le rayon de fondu doit être STRICTEMENT plus grand que le cœur.
    _leve_bien("fondu sans épaisseur",
               lambda: masque_depuis_adjacence(adjacence, [0], 0.01, 0.01),
               "rayon de fondu")
    _leve_bien("masque sans graine",
               lambda: masque_depuis_adjacence(adjacence, [], coeur, fondu),
               "aucune graine")

    # ═══ LES DEUX REFUS QUI REMPLACENT UNE GARDE AVEUGLE ═══
    # L'ancienne garde contrôlait `dist` non vide APRÈS la propagation en
    # annonçant « les graines ne sont pas dans le graphe ». Elle ne pouvait pas
    # échouer : Dijkstra inscrit la graine à la distance 0 avant de regarder
    # quoi que ce soit. Une graine étrangère au graphe rendait alors, sans un
    # mot, un masque d'un seul sommet à 1,0. Les deux refus ci-dessous EXERCENT
    # ce que l'ancienne prétendait couvrir — et ils tombent pour de bon.
    _leve_bien("graine qui n'appartient à aucune arête",
               lambda: masque_depuis_adjacence(adjacence, [999], coeur, fondu),
               "aucune arête")
    une_seule_arete_trop_longue = {0: [(1, 1.0)], 1: [(0, 1.0)]}
    _leve_bien("propagation qui n'atteint aucun voisin",
               lambda: masque_depuis_adjacence(une_seule_arete_trop_longue,
                                               [0], coeur, fondu),
               "au-delà des graines")
    print(f"  · masque géodésique : replié, éprouvé, l'euclidien le ferait "
          f"échouer, {len(_REFUS_EXERCES) - debut} refus exercés")


def _autotest_transfert():
    debut = len(_REFUS_EXERCES)
    # On ne CRÉE pas de poids : la part ne dépasse jamais le disponible.
    _exiger(part_transferee(1.0, 1.0, 0.35) == 0.35, "part pleine fausse")
    _exiger(part_transferee(0.5, 1.0, 0.35) == 0.175, "part à mi-masque fausse")
    # LE test de la pièce : le plafond (0,35) dépasse le poids disponible
    # (0,10), et c'est le POIDS DISPONIBLE qui doit gagner. Si quelqu'un
    # remplace `min(mx * m, w)` par `mx * m` — la faute « ajouter au lieu de
    # transférer » — cette ligne tombe, et elle est la seule à tomber.
    _exiger(part_transferee(1.0, 0.10, 0.35) == 0.10,
            "la part dépasse le poids disponible : du poids serait CRÉÉ")

    # ═══ CE QU'ON N'ÉCRIT SURTOUT PAS ICI, ET POURQUOI ═══
    # Le premier jet contrôlait la conservation de la somme ainsi :
    #     _exiger(abs((w - part) + part - w) < 1e-15, "somme non conservée")
    # C'est une IDENTITÉ ARITHMÉTIQUE : `(w - part) + part` rend `w` pour tout
    # couple de flottants, quelle que soit la valeur de `part` — même une part
    # ABSURDE, même une part supérieure au poids disponible. Cette ligne ne
    # testait pas `part_transferee`, elle testait l'addition d'IEEE 754. Une
    # contre-épreuve qui ne peut pas échouer est un trou déguisé en garde, et
    # c'est la faute que ce dépôt a payée le plus cher.
    # Ce qui peut réellement échouer, et qu'on contrôle donc : la part reste
    # dans [0, w] — donc le reste `w - part` ne devient jamais négatif, et rien
    # n'est créé. La conservation de la somme, elle, n'est pas une propriété de
    # CETTE fonction : c'est une propriété de `transferer_vers_correctif`, qui
    # retire à la source ce qu'il donne au correctif, et elle s'y contre-éprouve
    # à l'exécution en RELISANT les deux poids sur le maillage.
    for m, w in ((1.0, 1.0), (0.3, 0.2), (0.9, 0.05), (1.0, 0.0)):
        part = part_transferee(m, w, 0.35)
        _exiger(0.0 <= part <= w,
                f"part {part!r} hors de [0, {w!r}] : le reste deviendrait "
                "négatif, ou du poids serait CRÉÉ")
        _exiger(part <= 0.35,
                f"part {part!r} au-dessus du plafond 0.35 : le correctif "
                "prendrait plus que la part qu'on lui accorde")
    # La part est le plafond exactement quand le plafond est le plus petit des
    # deux — ce qu'aucune identité ne rend vrai d'office.
    _exiger(part_transferee(1.0, 0.9, 0.35) == 0.35, "plafond non respecté")
    _exiger(part_transferee(0.5, 0.9, 0.35) == 0.35 * 0.5,
            "le masque ne module pas la part")

    _leve_bien("maximum nul", lambda: part_transferee(1.0, 1.0, 0.0), "hors ]0,1]")
    _leve_bien("masque hors bornes",
               lambda: part_transferee(1.4, 1.0, 0.35), "hors [0,1]")
    _leve_bien("poids source négatif",
               lambda: part_transferee(1.0, -0.1, 0.35), "négatif")
    print(f"  · transfert de poids : ne crée jamais de poids, "
          f"{len(_REFUS_EXERCES) - debut} refus exercés")


def _autotest_zones():
    import shutil
    import tempfile
    debut = len(_REFUS_EXERCES)
    sha = "a" * 64
    zone = {"graines": [3, 4],
            "rayon_coeur_m": 0.004,
            "rayon_fondu_m": 0.012,
            "masque": {3: 1.0, 4: 1.0, 5: 0.5},
            "centre": [0.01, 0.02, 0.03],
            "direction": [0.0, 0.0, 1.0],
            "roll_rad": 0.0,
            "os": "DEF_thenar.L"}      # clé libre : elle doit survivre au tour
    dossier = tempfile.mkdtemp(prefix="correctifs-autotest-")
    try:
        chemin = chemin_zones(dossier, ".L")
        sauver_zones(chemin, {"thenar": zone}, sha, 2048)
        _exiger(chemin.endswith(os.path.join("assets", "correctifs",
                                             "zones-main.L.json")),
                f"le chemin imposé par le cahier n'est pas respecté : {chemin}")
        relu = charger_zones(chemin, sha, 2048)
        z = relu["thenar"]
        _exiger(z["masque"] == {3: 1.0, 4: 1.0, 5: 0.5},
                f"masque relu faux : {z['masque']}")
        _exiger(z["graines"] == [3, 4], "graines relues fausses")
        _exiger(z["centre"] == [0.01, 0.02, 0.03],
                "le centre de l'os n'a pas survécu au tour : il redeviendrait "
                "dépendant d'une sélection ouverte dans Blender")
        _exiger(z["os"] == "DEF_thenar.L", "les clés libres doivent survivre")

        _leve_bien("empreinte différente",
                   lambda: charger_zones(chemin, "b" * 64, 2048), "empreinte")
        _leve_bien("nombre de sommets différent",
                   lambda: charger_zones(chemin, sha, 2047), "sommets décrits")
        _leve_bien("nb_sommets oublié",
                   lambda: charger_zones(chemin, sha), "passez le nombre")
        _leve_bien("indice de masque hors du maillage",
                   lambda: sauver_zones(chemin, {"z": dict(zone, masque={9999: 1.0})},
                                        sha, 2048),
                   "hors du maillage")
        _leve_bien("direction nulle",
                   lambda: sauver_zones(chemin,
                                        {"z": dict(zone, direction=[0.0, 0.0, 0.0])},
                                        sha, 2048),
                   "longueur nulle")
        for cle in CLES_ZONE:
            incomplete = dict(zone)
            del incomplete[cle]
            _leve_bien(f"zone sans {cle!r}",
                       (lambda z=incomplete: sauver_zones(
                           chemin, {"z": z}, sha, 2048)),
                       "absente")
        _leve_bien("empreinte qui n'est pas un sha256",
                   lambda: sauver_zones(chemin, {"z": zone},
                                        "assets/zones.json", 2048),
                   "sha256")
        # Le même sommet deux fois, une fois en entier une fois en chaîne :
        # sans refus, la seconde valeur écrase la première SANS UN MOT.
        _leve_bien("sommet en double dans un masque",
                   lambda: sauver_zones(chemin,
                                        {"z": dict(zone,
                                                   masque={3: 1.0, "3": 0.5})},
                                        sha, 2048),
                   "deux fois")
        print(f"  · zones : tour disque complet, "
              f"{len(_REFUS_EXERCES) - debut} refus exercés")
    finally:
        shutil.rmtree(dossier, ignore_errors=True)


def _autotest():
    print("AUTOTEST atelier/correctifs.py — partie PURE, hors Blender")
    _autotest_expression()
    _autotest_format_sparse()
    _autotest_masque_geodesique()
    _autotest_transfert()
    _autotest_zones()
    print(f"TOUT PASSE — {len(_REFUS_EXERCES)} refus exercés au total, "
          "comptés par les refus eux-mêmes et non annoncés de tête. "
          "La partie Blender (shape keys, drivers, os, poids) n'est pas "
          "couverte ici : elle se contre-éprouve à l'exécution, dans chaque "
          "fonction, et LÈVE au lieu de conclure.")


if __name__ == "__main__":
    import sys
    # ═══ NE PAS TAMPONNER LA SORTIE ═══
    # Mesuré sur ce dépôt : deux lancements de 11 et 16 minutes n'avaient écrit
    # ZÉRO octet, et une exception laissait un journal vide. On ne pouvait
    # distinguer un calcul long d'un blocage. Un module ne touche pas à la
    # sortie de son hôte — mais ici le module EST le script lancé.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    try:
        _autotest()
    except Exception as e:
        # ═══ CODE DE SORTIE NON NUL SI LE VERDICT EST NÉGATIF ═══
        # Le dépôt a déjà écrit `"reussi": false` puis conclu quand même. Un
        # rapport qui contient son propre échec et sort à 0 est la faute la
        # plus grave de tout ce travail.
        print(f"ÉCHEC · {type(e).__name__} · {e}")
        sys.exit(1)
    sys.exit(0)
