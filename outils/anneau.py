"""
LE DIAMÈTRE UTILE DE L'ANNEAU DU SIGNE « OK » — §10.1 du tutoriel.

═══ POURQUOI LA MESURE DU DÉPÔT EST FAUSSE ═══

`ouverture_anneau()`, dans `rig-main.py`, fait ceci :

    _a1 = sommets dominés par DEF_thumb_01
    _b1 = sommets dominés par DEF_index_01 / DEF_index_02
    return min(distance de chaque sommet du pouce au plus proche de l'index)

C'est un MINIMUM GLOBAL sur les chairs proximales. Or un trou ne se mesure pas
par la distance minimale de son contour : il suffit qu'UN point du pouce frôle
UN point de l'index — la commissure qui se ferme, un pli de peau, un sommet mal
pesé à la base du pouce — pour que la grandeur s'effondre alors que le TROU
CENTRAL, lui, reste parfaitement grand et parfaitement lisible.

Deux fautes se sont superposées ici, et il faut les tenir séparées :

  · LE SEUIL EN DOUBLE. L'optimiseur visait 16 mm et le verdict n'en exigeait
    que 14. Cette faute-là est DÉJÀ RÉPARÉE dans `rig-main.py` : il n'y déclare
    plus qu'un `SEUIL_ANNEAU_MM = 14.0` (ligne 1867) que `ANNEAU_EXIGE[0]`
    relit. Réécrire ici le nombre 14,0 en clair, c'est recréer de mes mains la
    faute que le dépôt vient de fermer. C'est pourquoi ce module ne se contente
    pas de porter la constante : `_verifier_seuil_unique()` RELIT
    `rig-main.py` et LÈVE si la valeur y a bougé, ou si le dépôt s'est remis à
    en déclarer plusieurs. Une copie surveillée ne diverge pas ; une copie de
    confiance diverge toujours.

  · LA GRANDEUR. Elle, personne ne l'a corrigée : le seuil unifié est toujours
    appliqué à un minimum global qui ne décrit pas un trou. C'est la faute que
    ce fichier répare.

Ce qu'on mesure ici est le DISQUE INSCRIT : le plus grand cercle qu'on puisse
poser dans le vide de l'anneau sans mordre la chair. Son diamètre est le
diamètre utile — la grandeur qu'un œil humain lit quand il dit « l'anneau est
lisible ». Un pincement, lui, n'a pas de disque inscrit digne de ce nom : c'est
exactement ce que la contre-épreuve vérifie.

═══ CE QUE CE MODULE REFUSE DE FAIRE ═══

  · aucune lecture de mesure avec valeur par défaut. Un `.get(cle, 0.0)` rend
    un zéro qui se lit comme une mesure ; ici une clé absente LÈVE ;
  · aucune lecture de `bone.head_local` : c'est le REPOS. La sonde du creux
    palmaire a rendu deux grandeurs constantes au centième sur tout un balayage
    pour cette seule faute. On lit `rig.pose.bones[...].head/.tail` sur la copie
    ÉVALUÉE, transformés par la matrice monde ;
  · aucun verdict sans contre-épreuve. Une sonde qui ne peut pas échouer ne
    prouve rien.

Sur les drivers : ce module ne sonde AUCUN canal piloté — il n'écrit que dans
des entrées (les propriétés de `CTRL_hand`, l'action posée) et ne lit que des
positions, c'est-à-dire des RÉSULTATS de drivers. La règle « taire la voie
avant de la sonder » n'a donc pas de voie à taire ici. Mais le risque qu'elle
protège, lui, demeure entier : lire une main qui n'a pas bougé. On s'en prémunit
par trois contrôles qui LÈVENT tous, plutôt que par une promesse :

  · après toute écriture, `rafraichir()` fait update_tag + data.update_tag +
    frame_set + view_layer.update — sans quoi le graphe ne repasse pas sur les
    drivers en mode fond ;
  · `Fist` est RELU sur la copie évaluée après écriture : si un driver possédait
    cette entrée, il l'aurait réécrite, et la sonde le dit par son nom au lieu
    de le laisser paraître comme une main inerte ;
  · avant chaque mesure, l'écart des deux os proximaux à leur orientation de
    REPOS est calculé, et une pose qui les laisse à moins de 1° fait lever.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/anneau.py -- FICHIER.blend Hand_OK [sortie.json]

Importable aussi :  from anneau import diametre_utile_anneau, SEUIL_ANNEAU_MM

Un importateur qui reprend `SEUIL_ANNEAU_MM` DOIT appeler `_verifier_seuil_unique()`
au moins une fois : le mode script le fait avant d'ouvrir le .blend, mais un
import ne déclenche rien (et ne doit rien déclencher — `rig-main.py` ouvre un
fichier et lance une optimisation dès qu'on l'exécute). Sans cet appel, la
surveillance du seuil ne surveille personne.
"""
import ast
import json
import math
import os
import sys

# ═══ NE PAS TAMPONNER LA SORTIE ═══
# Mesuré dans ce dépôt : deux lancements de 11 et 16 minutes avaient écrit ZÉRO
# octet, et une exception laissait un journal vide. On ne distinguait pas un
# calcul long d'un blocage. Blender tamponne en amont de Python.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

import bpy
import mathutils
import numpy as np

# ═══════════════════════════════════════════════════════════════════════
#   LES CONSTANTES — UNE SEULE PAR GRANDEUR
# ═══════════════════════════════════════════════════════════════════════

# ═══ IL Y EN AVAIT DEUX ; EN ÉCRIRE UNE TROISIÈME SERAIT PIRE ═══
# `rig-main.py` a porté DEUX seuils d'anneau : l'optimiseur visait 16 mm, le
# verdict n'en exigeait que 14. Une pose optimisée pour 16 puis jugée à 14 passe
# même quand la recherche a échoué de 2 mm. Cette faute-là est réparée : il n'y
# reste qu'un `SEUIL_ANNEAU_MM = 14.0` (ligne 1867), relu par `ANNEAU_EXIGE[0]`.
#
# D'où le piège que j'ai failli tendre : réécrire 14,0 en clair dans CE fichier
# rétablit exactement le défaut qu'on vient de fermer, avec un fichier de plus
# pour le cacher. Le jour où le contrat passe à 15, l'un des deux bouge et
# l'autre non — et c'est un verdict, pas un détail de style, qui se met à mentir.
# La copie est donc SURVEILLÉE : `_verifier_seuil_unique()` relit `rig-main.py`
# et lève à la moindre divergence. Voir cette fonction.
SEUIL_ANNEAU_MM = 14.0

# Le fichier qui porte l'autre exemplaire du seuil. On le situe par rapport à
# CE fichier (`outils/anneau.py` ⇒ la racine est un cran au-dessus) et non par
# rapport au dossier courant : une sonde lancée depuis ailleurs ne doit pas
# perdre silencieusement son contrôle.
try:
    _RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:                      # exécution sans fichier (console)
    _RACINE = None

# La tranche exigée au §10.1 : ±1,5 mm autour du plan de l'anneau. Assez épaisse
# pour attraper une ceinture continue de sommets sur un maillage de main (les
# arêtes y font 2 à 4 mm), assez fine pour que la coupe reste une coupe.
TRANCHE_MM = 1.5

# Le pas de la grille exigé au §10.1. Sur un trou d'une quinzaine de
# millimètres, 0,25 mm borne l'erreur de quantification du diamètre à 0,5 mm.
GRILLE_MM = 0.25

# En deçà de ce sinus, le produit vectoriel des deux os n'oriente plus rien :
# 0,20 vaut 11,5° entre l'index et le pouce. Sous cette valeur, la normale du
# plan bascule sur la normale palmaire, comme l'exige l'algorithme.
SEUIL_COLINEAIRE = 0.20

# Nombre de secteurs angulaires du test d'encerclement (voir `_interieur`).
# 16 secteurs = 22,5° : une échancrure du contour plus large que cela laisse un
# secteur vide et le point est refusé. C'est ce test qui empêche le disque de
# fuir HORS de la main, là où il n'y a évidemment aucune chair pour l'arrêter.
SECTEURS = 16

# Le trou d'un anneau est bordé des DEUX côtés — par l'index ET par le pouce.
# Sans cette exigence, le plus grand disque inscrit trouvé pourrait être un vide
# bordé par le seul index (l'espace inter-digital, par exemple). On tolère un
# facteur 3 entre les deux bords : au-delà, ce n'est plus l'anneau.
FACTEUR_DEUX_BORDS = 3.0

# ═══ LA CONTRE-ÉPREUVE, CHIFFRÉE ═══
# Exigence du §10.1 : sur `Hand_Pinch`, où les segments proximaux se
# rapprochent, le diamètre utile doit être NETTEMENT plus petit que sur
# `Hand_OK`. « Nettement » ne peut pas rester un mot : si les deux poses
# rendaient la même chose, la grandeur ne distinguerait pas un anneau d'un
# pincement et ne mesurerait donc rien du tout. On chiffre l'écart minimal.
MARGE_DISTINCTION_MM = 3.0

# Combien de sommets il faut, de CHAQUE côté, pour qu'une tranche soit un
# contour et non une poignée de points isolés. En dessous, la sonde lève : un
# nombre nommé une fois ne peut pas être relevé d'un côté et oublié de l'autre.
MIN_SOMMETS_PAR_BORD = 8

# Au-delà de ce nombre de points de grille, la tranche contient forcément des
# sommets aberrants et la mesure serait du bruit : on lève au lieu de calculer
# une heure pour rien.
GRILLE_MAX_POINTS = 4_000_000

POSE_ANNEAU = "Hand_OK"
POSE_PINCEMENT = "Hand_Pinch"

_FAMILLES = ("index", "middle", "ring", "pinky", "thumb")


# ═══════════════════════════════════════════════════════════════════════
#   LE CONTRÔLE DU SEUIL — LA COPIE EST SURVEILLÉE, PAS SUPPOSÉE
# ═══════════════════════════════════════════════════════════════════════

def _verifier_seuil_unique():
    """`rig-main.py` déclare-t-il TOUJOURS le même seuil, et une seule fois ?

    Ce fichier porte un exemplaire de `SEUIL_ANNEAU_MM`. Un deuxième exemplaire
    d'un nombre est précisément la faute que le §10.1 a fermée dans
    `rig-main.py` — le laisser revenir par un fichier d'outillage serait la
    rouvrir en pire, car elle serait alors répartie sur deux fichiers que
    personne ne lit ensemble.

    On relit donc le source par `ast` — on l'ANALYSE, on ne l'exécute pas :
    `rig-main.py` ouvre un .blend et lance une optimisation dès l'import.

    Trois manières d'échouer, et aucune ne peut se taire :
      · le fichier est introuvable ⇒ le contrôle n'a pas eu lieu, donc il
        échoue. Un contrôle qui s'abstient quand il ne trouve pas sa cible est
        un contrôle qui passe toujours ;
      · le dépôt s'est remis à déclarer plusieurs `SEUIL_ANNEAU_MM` ;
      · la valeur déclarée là-bas n'est plus celle d'ici.

    Rend (ligne, valeur) constatées, pour que le rapport les montre.
    """
    if _RACINE is None:
        raise RuntimeError(
            "impossible de situer la racine du dépôt (pas de __file__) : le "
            "contrôle du seuil unique n'a pas pu avoir lieu, et un contrôle "
            "qui ne s'exécute pas ne prouve rien")
    chemin = os.path.join(_RACINE, "rig-main.py")
    if not os.path.isfile(chemin):
        raise RuntimeError(
            f"rig-main.py introuvable ({chemin}) : le seuil de ce module ne "
            f"peut pas être confronté à celui du pipeline. On lève plutôt que "
            f"de juger un anneau avec une constante non vérifiée")
    with open(chemin, encoding="utf-8") as f:
        source = f.read()
    vus = []
    for noeud in ast.walk(ast.parse(source, filename=chemin)):
        if not isinstance(noeud, ast.Assign):
            continue
        for cible in noeud.targets:
            if isinstance(cible, ast.Name) and cible.id == "SEUIL_ANNEAU_MM":
                if not (isinstance(noeud.value, ast.Constant)
                        and isinstance(noeud.value.value, (int, float))
                        and not isinstance(noeud.value.value, bool)):
                    raise RuntimeError(
                        f"rig-main.py ligne {noeud.lineno} : SEUIL_ANNEAU_MM "
                        f"n'y est plus un nombre écrit en clair, le contrôle "
                        f"ne peut plus le comparer")
                vus.append((noeud.lineno, float(noeud.value.value)))
    if len(vus) != 1:
        raise RuntimeError(
            f"rig-main.py déclare {len(vus)} fois SEUIL_ANNEAU_MM "
            f"({[l for l, _ in vus]}) : c'est exactement la faute des deux "
            f"seuils divergents qui revient. Un seuil, un endroit")
    ligne, valeur = vus[0]
    if valeur != SEUIL_ANNEAU_MM:
        raise RuntimeError(
            f"le seuil a divergé : rig-main.py ligne {ligne} exige "
            f"{valeur} mm, ce module {SEUIL_ANNEAU_MM} mm. Le pipeline et sa "
            f"sonde jugeraient le même anneau différemment — aucun des deux "
            f"verdicts ne vaudrait rien")
    return ligne, valeur


# ═══════════════════════════════════════════════════════════════════════
#   OUTILS DE LECTURE
# ═══════════════════════════════════════════════════════════════════════

def famille(nom):
    """La famille d'un groupe de sommets, comme dans `verifier-rig.py`.

    Seuls les groupes d'OS sont des familles : `ZONES_ARTICULAIRES`, rangé dans
    « hand » par erreur, fabriquait des intersections fantômes sur Pinch et OK.
    Un groupe qui n'est pas un os n'appartient à aucune famille.
    """
    for f in _FAMILLES:
        if nom.startswith(f"DEF_{f}_"):
            return f
    return "hand" if nom.startswith("DEF_") else None


def sommets_evalues(geo):
    """Positions ET normales du maillage DÉFORMÉ, en monde.

    On lit la copie évaluée : le maillage de repos ne porte évidemment aucune
    pose, et une sonde qui le lirait rendrait la même valeur pour toutes les
    poses — un silence qu'on lirait comme une mesure.

    ═══ TROIS DÉTAILS DE REPÈRE QUI DÉCIDENT DU SIGNE ═══
    Ce module se distingue ici de l'homonyme de `rig-main.py`, et pour des
    raisons mesurables, pas de style :

    1. LA MATRICE VIENT DE LA COPIE ÉVALUÉE. `os_pose()` lit `rev.matrix_world`
       (rig évalué) ; si l'on prenait ici `geo.matrix_world` (original), le plan
       de l'anneau et le maillage vivraient dans deux repères différents dès que
       l'objet lui-même est parenté ou contraint. Deux repères, et la coupe de
       ±1,5 mm tranche à côté du trou sans jamais s'en plaindre.

    2. LA NORMALE NE SE TRANSFORME PAS COMME UN POINT. `to_3x3()` est juste
       pour un vecteur, faux pour une normale dès que l'échelle n'est pas
       uniforme : c'est l'inverse transposée qu'il faut. Ce n'est pas une
       coquetterie — tout le test « le point est-il DEHORS de la chair ? » ne
       tient qu'au SIGNE de `(q − p)·n`, et une normale inclinée à tort fait
       basculer ce signe le long des flancs, là où le disque inscrit se décide.

    3. UNE MATRICE MIROIR EST REFUSÉE. Une main gauche obtenue en mirroir d'une
       droite porte un déterminant négatif : toutes les normales pointent alors
       vers l'INTÉRIEUR de la chair. Le test « dehors » choisirait exactement les
       points situés DANS le doigt — la faute que ce test existe pour empêcher,
       et elle rendrait un beau diamètre bien lisible. On lève : décider d'un
       retournement d'orientation n'appartient pas à une sonde.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw = ev.matrix_world
    m3 = mw.to_3x3()
    det = m3.determinant()
    if abs(det) < 1e-12:
        ev.to_mesh_clear()
        raise RuntimeError(f"la matrice monde de {geo.name} est dégénérée "
                           f"(déterminant {det:.3e}) : ni position ni normale "
                           f"n'ont de sens dans ce repère")
    if det < 0.0:
        ev.to_mesh_clear()
        raise RuntimeError(
            f"{geo.name} porte une matrice MIROIR (déterminant {det:.3e}) : "
            f"ses normales monde pointent vers l'intérieur de la chair et le "
            f"disque inscrit se logerait DANS le doigt. Appliquer l'échelle "
            f"négative avant de mesurer")
    mn = m3.inverted().transposed()
    p = [mw @ v.co.copy() for v in m.vertices]
    n = [(mn @ v.normal).normalized() for v in m.vertices]
    ev.to_mesh_clear()
    return p, n


def os_pose(rig, nom):
    """Base et bout POSÉS d'un os, en monde.

    ═══ head_local NE BOUGE JAMAIS ═══
    La sonde du creux palmaire lisait `rig.data.bones[nom].head_local` et
    rendait 71,99 mm et 50,30 mm identiques au centième de `Cup = 0` à
    `Cup = 1`. Ces grandeurs n'auraient JAMAIS pu bouger : elles décrivaient le
    repos. On passe donc par la pose, sur la copie évaluée du rig — la pose de
    l'objet original peut être en retard d'une évaluation sur les drivers.
    Une clé d'os absente lève : c'est voulu, un os manquant n'est pas un zéro.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    rev = rig.evaluated_get(dg)
    pb = rev.pose.bones[nom]
    mw = rev.matrix_world
    return mw @ pb.head.copy(), mw @ pb.tail.copy()


def _direction_repos(rig, nom):
    """La direction de REPOS d'un os, dans l'espace de l'ARMATURE.

    Elle n'entre dans aucune mesure : on ne s'en sert que pour prouver que la
    pose a réellement bougé les os de l'anneau. C'est la seule lecture de
    `head_local` autorisée dans ce fichier, et elle est là pour dénoncer
    précisément la faute qu'elle incarne.

    ═══ PAS DE matrix_world ICI, ET C'EST VOLONTAIRE ═══
    Premier jet : je multipliais les deux bouts par `rig.matrix_world`, et je
    comparais ensuite à une direction POSÉE tirée de `os_pose()`, qui passe par
    `rev.matrix_world` (la matrice ÉVALUÉE). Ces deux matrices sont la même tant
    que l'objet armature ne bouge pas — mais qu'une action fasse tourner
    l'OBJET, et l'écart mesuré entre pose et repos gonfle de la rotation de
    l'objet. La contre-épreuve « les os ont-ils bougé ? » passerait alors grâce
    à un mouvement d'objet, sur une main restée strictement au repos : elle
    validerait exactement ce qu'elle est censée surprendre.

    `head_local`/`tail_local` d'un os et `head`/`tail` d'un os de pose vivent
    tous les quatre dans l'espace de l'armature. On les compare donc là, sans
    aucune matrice : le repère se simplifie au lieu de se contaminer.
    """
    b = rig.data.bones[nom]
    d = b.tail_local - b.head_local
    if d.length < 1e-9:
        raise RuntimeError(f"l'os {nom} a une longueur nulle au repos")
    return d.normalized()


def _direction_posee(rig, nom):
    """La direction POSÉE d'un os, dans l'espace de l'armature évaluée.

    Pendant du repère de `_direction_repos()` : même espace, aucune matrice
    monde, pour que leur comparaison ne mesure QUE le mouvement de l'os. On lit
    la copie évaluée, la pose de l'objet original pouvant être en retard d'une
    évaluation sur les drivers.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    pb = rig.evaluated_get(dg).pose.bones[nom]
    d = pb.tail - pb.head
    if d.length < 1e-9:
        raise RuntimeError(f"l'os {nom} est de longueur nulle en pose : sa "
                           f"direction ne peut pas être comparée au repos")
    return d.normalized()


# ═══════════════════════════════════════════════════════════════════════
#   LA MESURE
# ═══════════════════════════════════════════════════════════════════════

def _interieur(gx, gy, px, py, dmin, masque_index, masque_pouce):
    """Le point (gx, gy) est-il DANS le trou de l'anneau ?

    Deux conditions, et la seconde est celle qui a manqué à toutes mes
    premières versions :

      1. ENCERCLEMENT. Le contour projeté doit occuper les 16 secteurs
         angulaires autour du point. Sans ce test, le plus grand disque
         « inscrit » se posait DEHORS, dans le vide qui entoure la main, où
         aucune chair ne le borne : la mesure rendait alors la moitié de la
         diagonale de la boîte englobante, soit une quarantaine de millimètres,
         sur n'importe quelle pose.

      2. LES DEUX BORDS. Un anneau est borné par l'index ET par le pouce. Un
         vide bordé par le seul index — l'espace entre index et majeur, par
         exemple — est encerclé lui aussi mais n'est pas l'anneau.

    Rend un couple (verdict, détail) ; le détail sert au rapport.
    """
    dx = px - gx
    dy = py - gy
    d = np.hypot(dx, dy)

    # 1 · encerclement
    sec = ((np.arctan2(dy, dx) + math.pi) * (SECTEURS / (2.0 * math.pi)))
    sec = np.clip(sec.astype(np.int32), 0, SECTEURS - 1)
    occupe = np.zeros(SECTEURS, dtype=bool)
    occupe[sec] = True
    if not occupe.all():
        return False, None

    # 2 · les deux bords
    d_index = float(d[masque_index].min())
    d_pouce = float(d[masque_pouce].min())
    if (d_index > FACTEUR_DEUX_BORDS * dmin
            or d_pouce > FACTEUR_DEUX_BORDS * dmin):
        return False, None

    return True, {"distance_au_bord_index_mm": round(d_index, 2),
                  "distance_au_bord_pouce_mm": round(d_pouce, 2)}


def diametre_utile_anneau(rig, geo, SIDE, dom, palmaire, detail=None):
    """Le DIAMÈTRE UTILE de l'anneau, en millimètres, sur la pose COURANTE.

    Ce n'est pas `ouverture_anneau()` et ce ne doit jamais porter ce nom : la
    grandeur du dépôt est le minimum global des distances entre les chairs
    proximales, c'est-à-dire l'endroit où le contour se PINCE. Celle-ci est le
    diamètre du plus grand disque qu'on peut inscrire dans le vide — le trou.

    `dom`      : {index de sommet -> nom du groupe dominant}, comme partout
                 ailleurs dans le dépôt.
    `palmaire` : le côté paume, mesuré par le mouvement (jamais supposé : le
                 signe d'une normale construite est arbitraire, et c'est cette
                 faute-là qui avait fait poser les ongles du mauvais côté).
    `detail`   : dictionnaire optionnel, rempli avec le détail de la mesure.
                 Il n'est jamais LU : rien ici ne dépend de son contenu.

    Lève si la géométrie ne permet pas la mesure. Elle ne rend jamais 0,0 « par
    prudence » : un zéro rendu par prudence se lit comme un anneau fermé.
    """
    # ── 1 · les directions POSÉES des deux os proximaux ──
    nom_i = f"DEF_index_01{SIDE}"
    nom_p = f"DEF_thumb_01{SIDE}"
    tete_i, bout_i = os_pose(rig, nom_i)
    tete_p, bout_p = os_pose(rig, nom_p)
    d_i, d_p = bout_i - tete_i, bout_p - tete_p
    if d_i.length < 1e-9 or d_p.length < 1e-9:
        raise RuntimeError(f"{nom_i} ou {nom_p} est de longueur nulle en pose : "
                           f"le plan de l'anneau n'a pas de direction")
    d_i, d_p = d_i.normalized(), d_p.normalized()

    # ── 2 et 3 · la normale du plan de l'anneau ──
    croix = d_i.cross(d_p)
    if croix.length >= SEUIL_COLINEAIRE:
        N = croix.normalized()
        source_normale = "produit vectoriel index × pouce"
    else:
        # Os presque colinéaires : leur produit vectoriel n'oriente plus rien,
        # sa direction devient du bruit numérique. Le §10.1 impose alors la
        # normale palmaire, qui est mesurée par le mouvement et non construite.
        if palmaire is None:
            raise RuntimeError("os presque colinéaires et aucune normale "
                               "palmaire fournie : la sonde n'a pas de plan")
        N = mathutils.Vector(palmaire)
        if N.length < 1e-9:
            raise RuntimeError("la normale palmaire fournie est nulle")
        N = N.normalized()
        source_normale = (f"normale palmaire de secours "
                          f"(sinus des deux os = {croix.length:.3f} "
                          f"< {SEUIL_COLINEAIRE})")

    # L'origine du plan : le milieu des deux segments proximaux. C'est le point
    # qui appartient aux deux os à la fois, donc au plan qu'ils tendent — et il
    # tombe naturellement au cœur du trou quand l'anneau est formé.
    O = ((tete_i + bout_i) / 2.0 + (tete_p + bout_p) / 2.0) / 2.0

    # Le repère du plan. `u` suit l'index ; si le repli sur la normale palmaire
    # rendait l'index parallèle à N, on bascule sur le pouce, et en dernier
    # recours sur un axe quelconque du plan — un repère mal choisi ne change
    # rien à la mesure, seul son absence l'empêcherait.
    u = d_i - N * d_i.dot(N)
    if u.length < 1e-6:
        u = d_p - N * d_p.dot(N)
    if u.length < 1e-6:
        u = N.orthogonal()
    u = u.normalized()
    v = N.cross(u).normalized()

    # ── 4 · la tranche de ±1,5 mm ──
    pos, nrm = sommets_evalues(geo)
    if len(pos) != len(geo.data.vertices):
        # `dom` indexe le maillage ORIGINAL. Si un modificateur change le nombre
        # de sommets, chaque index désigne alors une autre chair et la sonde
        # mesure un anneau qui n'existe pas — sans jamais s'en apercevoir.
        raise RuntimeError(
            f"le maillage évalué a {len(pos)} sommets contre "
            f"{len(geo.data.vertices)} au repos : les index de `dom` ne "
            f"désignent plus les mêmes chairs")

    xs, ys, ss, nus, nvs, nns, fam = [], [], [], [], [], [], []
    for i, nom_groupe in dom.items():
        f = famille(nom_groupe)
        if f not in ("index", "thumb"):
            continue
        q = (pos[i] - O) * 1000.0            # en mm, relatif au plan
        s = q.dot(N)
        if abs(s) > TRANCHE_MM:
            continue
        # ── 5 · la projection 2D dans le plan ──
        xs.append(q.dot(u))
        ys.append(q.dot(v))
        ss.append(s)
        n = nrm[i]
        nus.append(n.dot(u))
        nvs.append(n.dot(v))
        nns.append(n.dot(N))
        fam.append(0 if f == "index" else 1)

    px = np.asarray(xs, dtype=np.float64)
    py = np.asarray(ys, dtype=np.float64)
    ps = np.asarray(ss, dtype=np.float64)
    pnu = np.asarray(nus, dtype=np.float64)
    pnv = np.asarray(nvs, dtype=np.float64)
    pnn = np.asarray(nns, dtype=np.float64)
    pfam = np.asarray(fam, dtype=np.int8)
    masque_index = pfam == 0
    masque_pouce = pfam == 1

    # Une tranche vide, ou bordée d'un seul côté, ne décrit aucun anneau. Rendre
    # 0,0 ici serait la faute la plus grave possible : ce zéro se lirait comme
    # « anneau fermé » alors qu'il signifie « je n'ai rien regardé ».
    n_index = int(masque_index.sum())
    n_pouce = int(masque_pouce.sum())
    if n_index < MIN_SOMMETS_PAR_BORD or n_pouce < MIN_SOMMETS_PAR_BORD:
        raise RuntimeError(
            f"la tranche de ±{TRANCHE_MM} mm ne contient que {n_index} sommets "
            f"d'index et {n_pouce} de pouce, pour {MIN_SOMMETS_PAR_BORD} exigés "
            f"de chaque côté : trop peu pour un contour")

    # ── 6 · la grille de 0,25 mm, et le point intérieur le plus éloigné ──
    x0, x1 = float(px.min()), float(px.max())
    y0, y1 = float(py.min()), float(py.max())
    gxs = np.arange(x0, x1 + GRILLE_MM * 0.5, GRILLE_MM)
    gys = np.arange(y0, y1 + GRILLE_MM * 0.5, GRILLE_MM)
    if gxs.size * gys.size > GRILLE_MAX_POINTS:
        raise RuntimeError(
            f"grille déraisonnable ({gxs.size}×{gys.size}) : la tranche "
            f"contient des sommets aberrants, la mesure serait du bruit")
    GX, GY = np.meshgrid(gxs, gys, indexing="ij")
    gx, gy = GX.ravel(), GY.ravel()

    # Distance de chaque point de la grille au contour projeté, par arbre k-d :
    # la même machinerie que le reste du dépôt, et en C plutôt qu'en Python.
    arbre = mathutils.kdtree.KDTree(px.size)
    for k in range(px.size):
        arbre.insert((float(px[k]), float(py[k]), 0.0), k)
    arbre.balance()
    dist = np.empty(gx.size, dtype=np.float64)
    proche = np.empty(gx.size, dtype=np.int32)
    for k in range(gx.size):
        _co, j, d = arbre.find((float(gx[k]), float(gy[k]), 0.0))
        dist[k] = d
        proche[k] = j

    # On parcourt les candidats du PLUS ÉLOIGNÉ au plus proche : le premier qui
    # satisfait « intérieur » est donc le maximum, sans avoir à tester les
    # centaines de milliers d'autres.
    ordre = np.argsort(-dist)
    trouve = None
    essais = 0
    for k in ordre:
        d0 = float(dist[k])
        if d0 <= 0.0:
            break
        essais += 1
        j = int(proche[k])
        # Test de chair : le point est-il DEHORS de la surface la plus proche ?
        # (q − p)·n, en 3D complet — le point de grille est dans le plan, le
        # sommet du contour à ±1,5 mm de lui, et cette composante compte.
        # Sans ce test, le plus gros disque inscrit se logeait DANS le doigt :
        # une coupe longitudinale de l'index est une bande de ~18 mm de large,
        # dont le disque inscrit bat celui d'un anneau serré.
        dehors = ((float(gx[k]) - float(px[j])) * float(pnu[j])
                  + (float(gy[k]) - float(py[j])) * float(pnv[j])
                  + (0.0 - float(ps[j])) * float(pnn[j]))
        if dehors <= 0.0:
            continue
        ok, det = _interieur(float(gx[k]), float(gy[k]), px, py, d0,
                             masque_index, masque_pouce)
        if ok:
            trouve = (float(gx[k]), float(gy[k]), d0, det)
            break

    if trouve is None:
        raise RuntimeError(
            "aucun point intérieur trouvé : le contour projeté n'enferme aucun "
            "vide. Ce n'est pas un anneau de diamètre nul, c'est une mesure "
            "impossible — et un 0,0 rendu ici passerait pour un anneau fermé")

    gxi, gyi, rayon, det = trouve
    # ── 7 · le diamètre utile ──
    diametre = 2.0 * rayon

    if detail is not None:
        detail.clear()
        detail.update({
            "diametre_utile_anneau_mm": round(diametre, 2),
            "rayon_du_disque_inscrit_mm": round(rayon, 2),
            "source_de_la_normale": source_normale,
            "sinus_entre_les_deux_os": round(croix.length, 4),
            "angle_entre_les_deux_os_deg": round(
                math.degrees(math.asin(min(1.0, croix.length))), 1),
            "sommets_dans_la_tranche": {"index": n_index, "pouce": n_pouce},
            "grille": {"pas_mm": GRILLE_MM,
                       "colonnes": int(gxs.size), "lignes": int(gys.size)},
            "candidats_essayes": essais,
            "centre_dans_le_plan_mm": [round(gxi, 2), round(gyi, 2)],
            "centre_en_monde_mm": [round(c, 1) for c in
                                   ((O + (u * gxi + v * gyi) / 1000.0) * 1000.0)],
            **det})
    return diametre


def ouverture_anneau_du_depot(geo, SIDE, dom):
    """La grandeur RÉFUTÉE de `rig-main.py`, reproduite pour comparaison.

    Elle n'entre dans aucun verdict. On la calcule pour que le rapport montre
    noir sur blanc l'écart entre « la distance minimale du contour » et « le
    diamètre du trou » : c'est cet écart qui prouve que le §10.1 corrigeait une
    vraie faute et pas une nuance.
    """
    p, _ = sommets_evalues(geo)
    a1 = [i for i, n in dom.items() if n == f"DEF_thumb_01{SIDE}"]
    b1 = [i for i, n in dom.items() if n in (f"DEF_index_01{SIDE}",
                                             f"DEF_index_02{SIDE}")]
    if not a1 or not b1:
        raise RuntimeError("chairs proximales introuvables : la grandeur du "
                           "dépôt ne peut pas être reproduite")
    t = mathutils.kdtree.KDTree(len(b1))
    for k, i in enumerate(b1):
        t.insert(p[i], k)
    t.balance()
    return min(t.find(p[i])[2] for i in a1) * 1000.0


# ═══════════════════════════════════════════════════════════════════════
#   MODE SCRIPT AUTONOME
# ═══════════════════════════════════════════════════════════════════════

def _principal():
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) < 2:
        raise RuntimeError(
            "usage : blender --background --factory-startup "
            "--python-exit-code 1 --python outils/anneau.py -- "
            "FICHIER.blend NOM_DE_POSE [sortie.json]")
    fichier, pose_demandee = args[0], args[1]
    sortie = args[2] if len(args) > 2 else None
    if not os.path.isfile(fichier):
        raise RuntimeError("fichier introuvable : " + fichier)

    # ═══ AVANT TOUTE MESURE : LE SEUIL EST-IL ENCORE LE MÊME QU'AILLEURS ? ═══
    # On le contrôle ici, et pas après le calcul : ouvrir un .blend et mesurer
    # trois poses pour découvrir ensuite qu'on jugeait avec un seuil périmé,
    # c'est du temps perdu sur un verdict qu'il faudrait jeter.
    _ligne_seuil, _valeur_seuil = _verifier_seuil_unique()
    print(f"Seuil d'anneau : {SEUIL_ANNEAU_MM} mm, confronté à rig-main.py "
          f"ligne {_ligne_seuil} ({_valeur_seuil} mm) — ils concordent.")

    bpy.ops.wm.open_mainfile(filepath=fichier)

    geo = next(o for o in bpy.data.objects if o.name.startswith("GEO_Hand")
               and "BACKUP" not in o.name)
    rig = next(o for o in bpy.data.objects if o.name.startswith("RIG_Hand"))
    SIDE = rig.name[len("RIG_Hand"):]
    pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]
    NOMS4 = ["index", "middle", "ring", "pinky"]
    ACTIONS = {a.name: a for a in bpy.data.actions}

    def rafraichir():
        # ═══ LES DRIVERS NE S'ÉVALUENT PAS EN MODE FOND ═══
        # Sans changement d'image, le graphe ne repasse pas sur les drivers : on
        # mesure alors une main immobile, et une main immobile revient toujours
        # exactement à sa pose de repos — donc elle passe tout.
        # `rig.data.update_tag()` en plus de `rig.update_tag()` : c'est la paire
        # que `poser_etat()` de `rig-main.py` emploie, et l'armature (donc les
        # os) est une DONNÉE, pas l'objet. N'en marquer qu'un des deux laisse
        # passer les cas où seule la donnée a changé.
        rig.update_tag()
        rig.data.update_tag()
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        bpy.context.view_layer.update()

    def neutre():
        # Détacher l'action AVANT la remise à zéro : sinon les clés de la
        # dernière pose rejouée écrasent la remise à zéro, et l'on mesure la
        # pose précédente en croyant mesurer le repos.
        if rig.animation_data:
            rig.animation_data.action = None
        for pb in rig.pose.bones:
            if pb.rotation_mode == "QUATERNION":
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            else:
                pb.rotation_euler = (0.0, 0.0, 0.0)
        for k in list(pbh.keys()):
            if isinstance(pbh[k], float):
                pbh[k] = 0.0
        rafraichir()

    def appliquer(nom):
        # Une pose absente doit LEVER, pas se taire : un .blend sans la pose
        # contrôlée sortait autrefois en code 0.
        if nom not in ACTIONS:
            raise RuntimeError(f"pose « {nom} » absente du fichier. Poses "
                               f"présentes : {sorted(ACTIONS)}")
        neutre()
        rig.animation_data_create()
        rig.animation_data.action = ACTIONS[nom]
        # ═══ LE RAFRAÎCHISSEMENT EST UNE PAIRE, PAS UN frame_set ═══
        # Premier jet : je posais l'action puis j'appelais `frame_set(1)` seul.
        # Or le fichier s'ouvre déjà à l'image 1 : `frame_set(1)` y est un
        # aller-retour vers la même image, et rien ne garantissait que le rig,
        # non marqué, soit recalculé. La règle du dépôt est explicite —
        # update_tag PUIS frame_set PUIS view_layer.update — et elle vient
        # d'avoir raison contre moi.
        rig.update_tag()
        rig.data.update_tag()
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()

    # ── la carte des chairs, établie au repos ──
    ng = {g.index: g.name for g in geo.vertex_groups}
    neutre()
    dom = {}
    for v in geo.data.vertices:
        gs = [(g.weight, ng[g.group]) for g in v.groups
              if g.weight > 0.01 and g.group in ng]
        if gs:
            dom[v.index] = max(gs)[1]
    if not dom:
        raise RuntimeError("aucun sommet n'est dominé par un groupe : la sonde "
                           "n'a aucune chair à mesurer")

    # ── le côté palmaire, MESURÉ par le mouvement ──
    # Le signe d'une normale construite est arbitraire ; c'est cette faute qui
    # avait fait poser les ongles du mauvais côté. En fléchissant, les bouts des
    # doigts partent du côté de la paume : on le lit au lieu de le décréter.
    neutre()
    p_a, _ = sommets_evalues(geo)
    # ═══ ÉCRIRE UNE CLÉ ABSENTE NE LÈVE PAS : ÇA LA CRÉE ═══
    # Le commentaire de mon premier jet affirmait « clé absente ⇒ lève, pas de
    # `.get` ». C'est faux, et c'est la même famille de faute que le `.get(…,
    # 0.0)` qu'on pourchasse : `pbh["Fist"] = 0.5` sur un rig SANS propriété
    # `Fist` la FABRIQUE, silencieusement, et l'écriture ne pilote alors plus
    # rien. On LIT donc la clé avant de l'écrire — c'est l'indexation en
    # lecture, et elle seule, qui lève sur une clé absente.
    _fist_avant = pbh["Fist"]          # indexation NUE : clé absente ⇒ lève ici
    if not isinstance(_fist_avant, float):
        raise RuntimeError(
            f"CTRL_hand{SIDE}[\"Fist\"] n'est pas un flottant mais un "
            f"{type(_fist_avant).__name__} : `neutre()` ne le remet donc jamais "
            f"à zéro, et la pose de repos traînerait un reste de flexion")
    pbh["Fist"] = 0.5
    rafraichir()
    # ═══ ET ON VÉRIFIE QUE L'ÉCRITURE A TENU ═══
    # `Fist` est une ENTRÉE : rien ici ne la pilote, en principe. Mais si un
    # driver venait à la posséder, il la réécrirait à l'évaluation et notre 0,5
    # n'existerait que sur l'objet original. Le symptôme serait « aucun bout de
    # doigt ne bouge » — et j'aurais cherché du côté des poses pendant une heure.
    # On relit la valeur sur la copie ÉVALUÉE, qui est celle que le graphe a
    # réellement utilisée, et on nomme la cause au lieu de subir le symptôme.
    _dg = bpy.context.evaluated_depsgraph_get()
    _fist_vu = rig.evaluated_get(_dg).pose.bones[f"CTRL_hand{SIDE}"]["Fist"]
    if abs(float(_fist_vu) - 0.5) > 1e-6:
        raise RuntimeError(
            f"Fist a été écrit à 0,5 mais le graphe a évalué {_fist_vu} : la "
            f"propriété est pilotée ou bornée. Toute pose posée par propriété "
            f"est suspecte, et le côté palmaire mesuré ici serait faux")
    p_b, _ = sommets_evalues(geo)
    neutre()
    bouts = [i for i, n in dom.items() if n.endswith(f"_03{SIDE}")]
    if not bouts:
        raise RuntimeError("aucun sommet de bout de doigt : le côté palmaire "
                           "ne peut pas être mesuré par le mouvement")
    dep = sum(((p_b[i] - p_a[i]) for i in bouts), mathutils.Vector((0, 0, 0)))
    if dep.length < 1e-6:
        # Contre-épreuve du repère lui-même : si `Fist = 0.5` ne déplace RIEN,
        # les drivers ne tournent pas et tout ce qui suit mesurerait le repos.
        raise RuntimeError("Fist = 0,5 ne déplace aucun bout de doigt : les "
                           "drivers ne s'évaluent pas, aucune mesure ne vaut")
    poignet = os_pose(rig, f"DEF_hand{SIDE}")[0]
    jointures = [os_pose(rig, f"DEF_{n}_01{SIDE}")[0] for n in NOMS4]
    # ═══ normalized() SUR UN VECTEUR NUL REND UN VECTEUR NUL ═══
    # Et ne lève pas. Les deux normalisations qui suivent pouvaient donc rendre
    # (0, 0, 0) sans un mot, et cette normale palmaire nulle voyageait jusqu'au
    # cœur de la mesure : elle n'y était contrôlée que dans la branche de
    # secours des os colinéaires, c'est-à-dire presque jamais. Un vecteur nul
    # est un silence, et le silence se lit ici comme une direction.
    axe = ((sum(jointures, mathutils.Vector((0, 0, 0))) / len(jointures))
           - poignet)
    if axe.length < 1e-9:
        raise RuntimeError("les jointures se confondent avec le poignet : "
                           "l'axe de la main n'a pas de direction, le côté "
                           "palmaire ne peut pas être projeté")
    axe = axe.normalized()
    palmaire = dep - axe * dep.dot(axe)
    if palmaire.length < 1e-9:
        raise RuntimeError(
            "le déplacement des bouts de doigts est ENTIÈREMENT porté par "
            "l'axe de la main : après projection il ne reste aucune composante "
            "palmaire. Le côté paume ne peut pas être mesuré par ce mouvement, "
            "et le supposer est précisément la faute qui a posé les ongles du "
            "mauvais côté")
    palmaire = palmaire.normalized()

    # ── la mesure, pose par pose ──
    a_mesurer = [pose_demandee]
    for p in (POSE_ANNEAU, POSE_PINCEMENT):
        if p not in a_mesurer:
            a_mesurer.append(p)

    rep_i, rep_p = (_direction_repos(rig, f"DEF_index_01{SIDE}"),
                    _direction_repos(rig, f"DEF_thumb_01{SIDE}"))
    mesures = {}
    for nom in a_mesurer:
        appliquer(nom)
        # ═══ CONTRE-ÉPREUVE : LA POSE A-T-ELLE BOUGÉ LES OS DE L'ANNEAU ? ═══
        # Si les deux os proximaux gardent leur orientation de repos, c'est le
        # repos qu'on mesure — et les trois poses rendraient le même nombre, ce
        # que j'aurais lu comme « la mesure ne distingue rien ». Un silence ne
        # doit jamais pouvoir se déguiser en mesure.
        # Repère de l'ARMATURE des deux côtés (voir `_direction_repos`) : une
        # rotation de l'OBJET armature ne doit pas pouvoir se faire passer pour
        # un mouvement de doigt. Et un seul appel par os : deux évaluations
        # successives du graphe pour une même grandeur, c'est deux chances
        # qu'elle change entre-temps.
        d_i = _direction_posee(rig, f"DEF_index_01{SIDE}")
        d_p = _direction_posee(rig, f"DEF_thumb_01{SIDE}")
        ecart_deg = max(math.degrees(math.acos(max(-1.0, min(1.0, d_i.dot(rep_i))))),
                        math.degrees(math.acos(max(-1.0, min(1.0, d_p.dot(rep_p))))))
        if ecart_deg < 1.0:
            raise RuntimeError(
                f"la pose « {nom} » laisse l'index ET le pouce à moins de 1° "
                f"de leur repos ({ecart_deg:.3f}°) : ce qui serait mesuré ici "
                f"est la pose de repos, pas la pose demandée")
        detail = {}
        d = diametre_utile_anneau(rig, geo, SIDE, dom, palmaire, detail)
        detail["ecart_des_os_au_repos_deg"] = round(ecart_deg, 1)
        detail["ouverture_anneau_du_depot_mm_REFUTEE"] = round(
            ouverture_anneau_du_depot(geo, SIDE, dom), 2)
        mesures[nom] = detail
        print(f"ATLAS_ANNEAU_POSE {nom} · diamètre utile "
              f"{d:.2f} mm · disque inscrit r = {d / 2.0:.2f} mm · "
              f"normale : {detail['source_de_la_normale']} · "
              f"grandeur réfutée du dépôt : "
              f"{detail['ouverture_anneau_du_depot_mm_REFUTEE']:.2f} mm")
    neutre()

    # ═══════════════════════════════════════════════════════════════════
    #   LA CONTRE-ÉPREUVE EXIGÉE : UN ANNEAU N'EST PAS UN PINCEMENT
    # ═══════════════════════════════════════════════════════════════════
    # Indexation DIRECTE, sans `.get(..., 0.0)` : une pose manquante doit faire
    # exploser la sonde, pas rendre un zéro qu'on lirait comme une mesure.
    d_ok = mesures[POSE_ANNEAU]["diametre_utile_anneau_mm"]
    d_pinch = mesures[POSE_PINCEMENT]["diametre_utile_anneau_mm"]
    ecart = d_ok - d_pinch
    contre = {"diametre_sur_" + POSE_ANNEAU + "_mm": d_ok,
              "diametre_sur_" + POSE_PINCEMENT + "_mm": d_pinch,
              "ecart_mm": round(ecart, 2),
              "marge_exigee_mm": MARGE_DISTINCTION_MM,
              "verdict": ("la mesure distingue l'anneau du pincement"
                          if ecart >= MARGE_DISTINCTION_MM
                          else "INUTILISABLE")}
    print("ATLAS_ANNEAU_CONTRE_EPREUVE " + json.dumps(contre,
                                                      ensure_ascii=False))
    if ecart < MARGE_DISTINCTION_MM:
        raise RuntimeError(
            f"contre-épreuve en échec : {POSE_ANNEAU} rend {d_ok:.2f} mm et "
            f"{POSE_PINCEMENT} {d_pinch:.2f} mm, soit {ecart:.2f} mm d'écart "
            f"pour {MARGE_DISTINCTION_MM} exigés. Une grandeur qui ne sépare "
            f"pas un anneau d'un pincement ne mesure pas un anneau — aucun "
            f"verdict tiré d'elle ne vaut quoi que ce soit")

    # ── le verdict sur la pose demandée ──
    d_demande = mesures[pose_demandee]["diametre_utile_anneau_mm"]
    juge = pose_demandee == POSE_ANNEAU
    passe = (d_demande >= SEUIL_ANNEAU_MM) if juge else True
    resultat = {"fichier": os.path.basename(fichier),
                "pose_demandee": pose_demandee,
                "diametre_utile_anneau_mm": d_demande,
                "seuil_anneau_mm": SEUIL_ANNEAU_MM,
                # Le rapport porte la trace du contrôle : un lecteur doit
                # pouvoir constater que le seuil du juge est celui du pipeline
                # sans avoir à rouvrir les deux fichiers.
                "seuil_confronte_a": {"fichier": "rig-main.py",
                                      "ligne": _ligne_seuil,
                                      "valeur_mm": _valeur_seuil},
                "tranche_mm": TRANCHE_MM, "pas_de_grille_mm": GRILLE_MM,
                "contre_epreuve": contre,
                "mesures": mesures,
                "verdict": (("l'anneau est lisible" if passe
                             else "ANNEAU TROP FERMÉ") if juge
                            else "mesuré, non jugé : "
                                 f"le seuil ne vaut que pour {POSE_ANNEAU}")}
    print("\nATLAS_ANNEAU " + json.dumps(resultat, ensure_ascii=False))
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=1)
        print("écrit : " + sortie)

    print(f"\nDiamètre utile de l'anneau sur {pose_demandee} : "
          f"{d_demande:.2f} mm · exigé ≥ {SEUIL_ANNEAU_MM:.1f} mm")
    print(f"Contre-épreuve {POSE_ANNEAU} contre {POSE_PINCEMENT} : "
          f"{d_ok:.2f} contre {d_pinch:.2f} mm ({ecart:+.2f})")
    if not passe:
        # ═══ CODE DE SORTIE NON NUL ═══
        # Le dépôt a déjà écrit `"reussi": false` puis sauvegardé le .blend et
        # affiché ATLAS_TERMINE. Un rapport qui contient son propre échec et
        # conclut quand même est la faute la plus grave de tout ce travail.
        print(f"ÉCHEC · {pose_demandee} · mesuré {d_demande:.2f} mm · "
              f"exigé ≥ {SEUIL_ANNEAU_MM:.1f} mm")
        sys.exit(2)
    print("Le critère du §10.1 passe.")


if __name__ == "__main__":
    # Le module doit rester IMPORTABLE par `rig-main.py` : rien de tout ce qui
    # précède ne s'exécute à l'import, et l'analyse de `sys.argv` — qui lèverait
    # dans un Blender lancé sans `--` — vit ici et nulle part ailleurs.
    _principal()
