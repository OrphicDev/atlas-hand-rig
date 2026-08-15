"""
LA MAIN ET LE POIGNET — première partie du corps traitée en gros plan.

╔══════════════════════════════════════════════════════════════════════════╗
║  CE QUI SE MESURE, ET CE QUI NE S'Y TROUVE PAS.                          ║
╚══════════════════════════════════════════════════════════════════════════╝

J'ai d'abord cherché les phalanges comme les autres articulations : par les
creux de section. Le relevé des cinq doigts, tranche par tranche, dit non —
le rayon monte sans jamais redescendre :

    doigt 1   3,1  4,0  5,8  7,0  7,8  8,1  8,3  8,3 … 10,6  10,5  9,7

Pas un creux. Ce maillage de base n'a AUCUN relief de phalange : les doigts
sont des tubes lisses. Chercher plus finement ne servirait à rien, et un
détecteur qui finirait par « trouver » quelque chose là-dedans trouverait du
bruit de maillage. On ne peut pas mesurer ce qui n'est pas là.

CE QUI EST MESURÉ ICI :
  · le POIGNET, creux de section du bras (relevé dans `articulations`) ;
  · les CINQ DOIGTS, par la topologie : une sphère qui grossit depuis le
    poignet finit par détacher cinq morceaux, et cinq est le maximum atteint —
    c'est donc bien les cinq doigts, pas un réglage ;
  · le POUCE, parce qu'il se détache le PREMIER (à 98 mm quand les autres
    attendent 130) — il part plus bas sur la main, c'est ce qui le définit ;
  · la LIGNE DES MÉTACARPO-PHALANGIENNES, c'est-à-dire les jointures : la
    main est à sa plus grande LARGEUR sur cette ligne. C'est d'ailleurs la
    définition anthropométrique de la largeur de main. Un maximum, rien à
    régler ;
  · la POINTE de chaque doigt.

CE QUI VIENT D'UNE RÈGLE PUBLIÉE, faute d'être dans la géométrie :
  · la position des deux articulations intermédiaires le long du doigt. Les
    proportions phalangiennes sont des constantes anthropométriques stables
    (Buryanov & Kotiuk, 2010) : pour les doigts II à V, la phalange proximale
    fait environ 46 % de la longueur du doigt, la moyenne 28 %, la distale
    26 %. L'articulation PIP tombe donc à 46 % de la jointure vers la pointe,
    la DIP à 74 %. Le pouce n'a que deux phalanges : son IP tombe à 60 %.

C'est exactement le procédé du trichion : une longueur mesurée sur CE corps,
une proportion venue de l'anatomie, et aucun millimètre tapé de mémoire.
"""

import bpy, math, mathutils, numpy as np
import articulations as A

# proportions phalangiennes, en fraction de la longueur jointure → pointe
PIP = 0.46
DIP = 0.74
IP_POUCE = 0.60
# ═══ LA LIGNE DES JOINTURES SE PREND SUR LE PLI INTERDIGITAL ═══
#
# Deux versions fausses avant celle-ci. La « plus grande largeur de paume »
# tombait une dizaine de millimètres trop en avant : la main est la plus large
# JUSTE DEVANT les têtes métacarpiennes, là où les doigts commencent à
# s'écarter. Puis un rapport paume/main, qui n'a rien arrangé.
#
# La littérature de chirurgie de la main donne le repère utile, et il est
# MESURABLE ici : « les articulations métacarpo-phalangiennes se situent 1 à
# 2 cm en amont du pli interdigital ». Ce pli, c'est exactement le rayon où
# chaque doigt se détache topologiquement de la main — 128 mm pour les quatre
# doigts, 108 pour le pouce, relevés et non choisis.
#
# On recule donc de 20 mm depuis LE PLI DE CHAQUE DOIGT, sur SON PROPRE AXE.
# Sacha a choisi 20, le haut de la fourchette, pour que le poing se ferme avec
# des angles anatomiques au lieu d'être forcé.
RECUL_JOINTURE = 0.020


def _plus_de_morceaux(corps, main, poignet, co, pas=0.004, limite=0.30):
    """Le rayon de coupe qui divise le plus la main, et les morceaux obtenus."""
    meilleur, garde, rayon = 0, [], 0.0
    r = pas
    while r < limite:
        bouts = [i for i in main if (co[i] - poignet).length > r]
        ms = [m for m in A.morceaux(corps, bouts, co) if len(m) > 40]
        if len(ms) > meilleur:
            meilleur, garde, rayon = len(ms), ms, r
        r += pas
    return rayon, garde


def _apparition(corps, main, poignet, co, morceau, pas=0.004):
    """
    À quel rayon ce doigt-là se détache. C'est ce qui distingue le POUCE :
    il part plus bas sur la main, donc il se détache le premier.
    """
    temoin = morceau[0]
    r = pas
    while r < 0.30:
        bouts = set(i for i in main if (co[i] - poignet).length > r)
        if temoin not in bouts:
            return r
        for m in A.morceaux(corps, list(bouts), co):
            if temoin in m:
                if len(m) < len(morceau) * 1.6:
                    return r
                break
        r += pas
    return r


def releve(corps, poignet, main, co):
    """Le relevé de la main : jointures, articulations, pointes."""
    rayon, morceaux_doigts = _plus_de_morceaux(corps, main, poignet, co)
    if len(morceaux_doigts) < 5:
        raise RuntimeError(f"seulement {len(morceaux_doigts)} doigts détachés "
                           f"au meilleur rayon ({rayon*1000:.0f} mm)")

    doigts = []
    for m in morceaux_doigts:
        pts = [co[i] for i in m]
        pointe = max(pts, key=lambda q: (q - poignet).length)
        proche = min((q - poignet).length for q in pts)
        base = [q for q in pts if (q - poignet).length < proche + 0.006]
        racine = sum(base, mathutils.Vector((0, 0, 0))) / len(base)
        doigts.append({"pointe": pointe, "racine": racine, "sommets": len(m),
                       "apparition": _apparition(corps, main, poignet, co, m)})
    # LE POUCE : celui qui se détache le premier.
    pouce = min(doigts, key=lambda d: d["apparition"])
    pouce["pouce"] = True
    # ET SA BASE N'EST PAS SUR LA LIGNE DES AUTRES. Le pouce s'articule bien
    # plus bas sur la main ; le projeter sur la ligne des métacarpo-phalangiennes
    # des quatre doigts lui donnait 14,9 mm de long. On prend donc SA propre
    # séparation : la coupe au rayon où il se détache le premier.
    restants = [i for i in main if (co[i] - poignet).length > pouce["apparition"] - 0.004]
    for m in A.morceaux(corps, restants, co):
        q = [co[i] for i in m]
        if min((x - pouce["pointe"]).length for x in q) < 0.004:
            proche = min((x - poignet).length for x in q)
            base = [x for x in q if (x - poignet).length < proche + 0.006]
            pouce["racine"] = sum(base, mathutils.Vector((0, 0, 0))) / len(base)
            break

    # ── LA LIGNE DES JOINTURES : la main est à sa plus grande largeur dessus.
    #    On balaie la PAUME seule — au-delà, les doigts s'écartent et la largeur
    #    remonterait pour une raison qui n'a rien à voir avec une articulation.
    axe = (max(doigts, key=lambda d: (d["pointe"] - poignet).length)["pointe"]
           - poignet).normalized()
    paume = [co[i] for i in main if (co[i] - poignet).length < rayon]
    tranches = {}
    for q in paume:
        tranches.setdefault(int((q - poignet).dot(axe) / 0.003), []).append(q)
    large, d_large = 0.0, None
    for k in sorted(tranches):
        t = tranches[k]
        if len(t) < 20:
            continue
        c = sum(t, mathutils.Vector((0, 0, 0))) / len(t)
        l = max((q - c).length for q in t)
        if l > large:
            large, d_large = l, k * 0.003
    if d_large is None:
        raise RuntimeError("ligne des jointures introuvable : la paume ne rend "
                           "aucune tranche assez peuplée")

    # ── LA LIGNE DES JOINTURES, CORRIGÉE.
    #
    # Premier jet : la plus grande largeur de paume. Le rendu l'a montrée une
    # DIZAINE DE MILLIMÈTRES TROP EN AVANT — les billes tombaient dans la
    # commissure, pas sur l'os. C'est logique : la main est la plus large juste
    # devant les têtes métacarpiennes, là où les doigts commencent à s'écarter.
    #
    # On garde donc la longueur de main, qui est MESURÉE — poignet au bout du
    # majeur — et on y applique le rapport paume/main de l'anthropométrie
    # adulte. Même procédé que le trichion : une longueur relevée sur ce corps,
    # une proportion venue de l'anatomie. La plus grande largeur reste mesurée
    # et rendue, comme contre-épreuve.
    longueur_main = max((d["pointe"] - poignet).dot(axe) for d in doigts)

    for d in doigts:
        # ── LA JOINTURE : le pli de CE doigt, reculé de 20 mm sur SON axe.
        u = (d["pointe"] - d["racine"])
        if u.length < 1e-6:
            raise RuntimeError("doigt sans direction")
        d["jointure"] = d["racine"] - u.normalized() * RECUL_JOINTURE
        d["axe_doigt"] = u.normalized()
        if False:
            pass
        v = d["pointe"] - d["jointure"]
        if d.get("pouce"):
            d["articulations"] = [("IP", d["jointure"] + v * IP_POUCE)]
        else:
            d["articulations"] = [("PIP", d["jointure"] + v * PIP),
                                  ("DIP", d["jointure"] + v * DIP)]
        d["longueur"] = v.length
    # ── LE PLAN DE LA PAUME, pour savoir d'où photographier.
    #    Le premier gros plan regardait la main EN ENFILADE : je choisissais
    #    l'azimut de la caméra, alors qu'une main a une orientation propre.
    #    L'axe le moins étalé du nuage de points EST la normale de la paume.
    q = np.array([[x.x, x.y, x.z] for x in
                  [co[i] for i in main]], dtype=float)
    q -= q.mean(axis=0)
    val, vec = np.linalg.eigh(q.T @ q)
    normale = mathutils.Vector(vec[:, 0]).normalized()      # plus petite variance
    if normale.dot(mathutils.Vector((0.0, -1.0, 0.0))) < 0:
        normale = -normale
    travers = normale.cross(axe).normalized()
    proj = [(mathutils.Vector(x) ).dot(travers) for x in q]
    d_jointure = sum((d["jointure"] - poignet).dot(axe) for d in doigts) / len(doigts)
    return {"rayon_de_coupe": rayon, "largeur_max": large, "axe": axe,
            "longueur_main": longueur_main, "distance_plus_large": d_large,
            "recul_jointure": RECUL_JOINTURE,
            "normale_paume": normale, "travers": travers,
            "largeur_paume": max(proj) - min(proj),
            "distance_jointures": d_jointure, "doigts": doigts}
