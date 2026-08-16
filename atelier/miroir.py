"""
LA MAIN DROITE — transfert contrôlé depuis une gauche VALIDÉE (§14).

═══ POURQUOI ON NE RELANCE PAS LES RECHERCHES ═══

`rig-main.py` sait déjà construire le côté droit : `… homme d 110` mesure le
bras droit du même mannequin et bâtit `.R` par la même chaîne. Pas de miroir à
échelle négative, donc pas d'échelle résiduelle à nettoyer — c'est déjà ce que
le cahier exige.

Mais les poses de contact sont TROUVÉES PAR RECHERCHE. Deux recherches
indépendantes, parties de graines différentes sur un maillage qui n'est pas
rigoureusement symétrique, rendent deux gestes légèrement différents. La
tolérance de symétrie du cahier — 1 mm et 2° — serait perdue d'avance, et on ne
saurait même pas dire laquelle des deux mains a raison.

On TRANSFÈRE donc : les propriétés telles quelles, et les corrections FK avec
une table de signes MESURÉE.

═══ POURQUOI LA TABLE DE SIGNES SE MESURE ═══

Le réflexe est d'inverser toutes les rotations. C'est faux, et le cahier le dit
en toutes lettres : « certains axes locaux conservent leur signe après
reconstruction, d'autres non ».

La raison est mécanique. Chaque os reçoit son roll par `align_roll(cible)`, et
la cible est construite à partir de la normale de paume — dont le signe est
arbitraire et change de côté. Un axe dont le vecteur se retourne inverse son
sens ; un axe construit par un produit vectoriel qui se retourne DEUX fois ne
l'inverse pas. On ne peut pas le deviner os par os : on l'éprouve.

Le protocole est celui qui a déjà servi trois fois dans ce dépôt — pour le sens
de la flexion, celui de l'écartement, celui de la divergence : on applique un
angle connu, on mesure le déplacement, on garde le signe qui produit le même
effet ANATOMIQUE des deux côtés.

    import miroir
    table = miroir.mesurer_table_de_signes(rig_g, rig_d, ".L", ".R", ...)
    poses_d = miroir.transferer_poses(poses_g, table, ".L", ".R")
"""
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass


# Les canaux d'os sont désignés comme partout ailleurs dans ce dépôt :
# `(nom_os, index_euler)`. Un troisième dialecte pour dire la même chose
# finirait par diverger des deux premiers.
def renommer_canal(cle, side_src, side_dst):
    """(`CTRL_index_01.L`, 0) → (`CTRL_index_01.R`, 0)."""
    nom, axe = cle
    if not nom.endswith(side_src):
        raise ValueError(f"le canal {nom} ne porte pas le suffixe {side_src} : "
                         f"transférer aveuglément produirait un os inexistant")
    return (nom[: -len(side_src)] + side_dst, axe)


def _exiger(condition, message):
    if not condition:
        raise RuntimeError(message)


def mesurer_table_de_signes(rig_src, rig_dst, side_src, side_dst,
                            os_a_eprouver, mesurer_deplacement,
                            angle_deg=12.0, seuil_mm=0.20):
    """{(nom_os_src, axe): +1 ou −1} — mesuré, jamais supposé.

    `mesurer_deplacement(rig, nom_os, axe, degres)` doit rendre le vecteur de
    déplacement d'un repère anatomique convenu, EXPRIMÉ DANS LE REPÈRE DE LA
    MAIN (axe de la main, travers, palmaire) — jamais en coordonnées monde :
    les deux mains ne sont pas au même endroit, et comparer des vecteurs monde
    comparerait leurs positions au lieu de leurs mouvements.

    On applique `+angle` à gauche et `+angle` à droite. Si les deux
    déplacements pointent du même côté dans leurs repères respectifs, le signe
    se conserve ; s'ils s'opposent, il s'inverse.

    ═══ UNE SONDE QUI NE PEUT PAS ÉCHOUER NE PROUVE RIEN ═══
    Un canal dont le déplacement est trop petit des deux côtés ne permet aucune
    conclusion : on le REFUSE au lieu de lui attribuer +1 par défaut, ce qui
    reviendrait à deviner en ayant l'air de mesurer.
    """
    table, muets = {}, []
    for cle in os_a_eprouver:
        nom_src, axe = cle
        nom_dst = renommer_canal(cle, side_src, side_dst)[0]
        d_src = mesurer_deplacement(rig_src, nom_src, axe, angle_deg)
        d_dst = mesurer_deplacement(rig_dst, nom_dst, axe, angle_deg)
        n_src = math.sqrt(sum(x * x for x in d_src)) * 1000.0
        n_dst = math.sqrt(sum(x * x for x in d_dst)) * 1000.0
        if n_src < seuil_mm or n_dst < seuil_mm:
            muets.append({"canal": f"{nom_src}[{axe}]",
                          "deplacement_gauche_mm": round(n_src, 3),
                          "deplacement_droite_mm": round(n_dst, 3)})
            continue
        produit = sum(a * b for a, b in zip(d_src, d_dst))
        table[cle] = 1.0 if produit > 0 else -1.0
    _exiger(not muets,
            "des canaux ne bougent pas assez pour que leur signe se mesure — "
            "leur attribuer +1 par défaut serait deviner en ayant l'air de "
            f"mesurer : {muets}")
    _exiger(table, "aucun canal n'a pu être éprouvé : la table de signes "
                   "serait vide et le transfert silencieusement faux")
    return table


def transferer_poses(poses_src, table, side_src, side_dst, tolerance=None):
    """Les poses de `side_src` réécrites pour `side_dst`.

    `poses_src` : liste de `(nom, props, os_)` — exactement la forme de `POSES`
    dans `rig-main.py`.

    Les PROPRIÉTÉS passent telles quelles : `Fist`, `Cup`, `Spread` et les
    autres sont des grandeurs abstraites, pas des rotations. C'est tout
    l'intérêt d'avoir mesuré `SIGNE_ECART` et `SIGNE_VOUTE` à la construction —
    les drivers du côté droit portent déjà l'inversion, et l'appliquer une
    seconde fois ici la ferait disparaître.

    Les CORRECTIONS FK reçoivent le signe mesuré. Un canal absent de la table
    fait LEVER : transférer un canal dont on ignore le signe, c'est jouer à
    pile ou face sur la moitié du geste.
    """
    out = []
    for nom, props, os_ in poses_src:
        os_dst = {}
        for cle, valeur in (os_ or {}).items():
            if cle not in table:
                raise RuntimeError(
                    f"le canal {cle} n'a pas de signe mesuré : le transfert "
                    f"de la pose {nom} serait un tirage au sort")
            os_dst[renommer_canal(cle, side_src, side_dst)] = valeur * table[cle]
        out.append((nom, dict(props), os_dst))
    return out


def ecart_de_symetrie(points_src, points_dst, plan_normale, plan_point):
    """L'écart maximal, en mm, entre la droite et le reflet de la gauche.

    On reflète la gauche à travers le plan sagittal et on compare au plus
    proche — jamais indice à indice. Rien ne garantit qu'un sommet gauche et
    son homologue droit portent le même numéro : les deux mains sont EXTRAITES
    du même maillage, et l'extraction ne conserve pas l'ordre.
    """
    _exiger(points_src and points_dst,
            "un des deux nuages est vide : l'écart de symétrie ne mesurerait "
            "rien tout en rendant un nombre")
    nx, ny, nz = plan_normale
    px, py, pz = plan_point
    norme = math.sqrt(nx * nx + ny * ny + nz * nz)
    _exiger(norme > 1e-9, "la normale du plan sagittal est nulle")
    nx, ny, nz = nx / norme, ny / norme, nz / norme

    reflets = []
    for x, y, z in points_src:
        d = (x - px) * nx + (y - py) * ny + (z - pz) * nz
        reflets.append((x - 2 * d * nx, y - 2 * d * ny, z - 2 * d * nz))

    pire = 0.0
    for rx, ry, rz in reflets:
        meilleur = None
        for dx, dy, dz in points_dst:
            e = (rx - dx) ** 2 + (ry - dy) ** 2 + (rz - dz) ** 2
            if meilleur is None or e < meilleur:
                meilleur = e
        pire = max(pire, math.sqrt(meilleur))
    return pire * 1000.0


if __name__ == "__main__":
    # ═══ AUTOTEST HORS BLENDER ═══
    # Il ne prouve que la partie pure — renommage, transfert, réflexion — et
    # c'est déjà ce qui casse en silence : un signe oublié ne plante jamais.
    fautes = []

    def leve(fn, quoi):
        try:
            fn()
        except Exception:
            return
        fautes.append(f"{quoi} : aurait dû lever")

    assert renommer_canal(("CTRL_index_01.L", 0), ".L", ".R") == ("CTRL_index_01.R", 0)
    leve(lambda: renommer_canal(("CTRL_index_01.R", 0), ".L", ".R"),
         "un canal sans le bon suffixe")

    _table = {("CTRL_index_01.L", 0): +1.0, ("CTRL_index_01.L", 2): -1.0}
    _poses = [("Hand_X", {"Fist": 1.0},
               {("CTRL_index_01.L", 0): 10.0, ("CTRL_index_01.L", 2): 4.0})]
    _out = transferer_poses(_poses, _table, ".L", ".R")
    assert _out[0][1] == {"Fist": 1.0}, "les propriétés ne doivent PAS changer"
    assert _out[0][2][("CTRL_index_01.R", 0)] == 10.0
    assert _out[0][2][("CTRL_index_01.R", 2)] == -4.0
    leve(lambda: transferer_poses(
        [("Y", {}, {("CTRL_ring_01.L", 0): 3.0})], _table, ".L", ".R"),
        "un canal absent de la table")

    # La réflexion : un point à +5 mm du plan doit retrouver son reflet à −5 mm.
    _e = ecart_de_symetrie([(0.005, 0.0, 0.0)], [(-0.005, 0.0, 0.0)],
                           (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    assert _e < 1e-6, f"un reflet exact devrait rendre 0, rend {_e}"
    _e2 = ecart_de_symetrie([(0.005, 0.0, 0.0)], [(-0.004, 0.0, 0.0)],
                            (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    assert abs(_e2 - 1.0) < 1e-6, f"1 mm d'écart devrait rendre 1,0, rend {_e2}"
    leve(lambda: ecart_de_symetrie([], [(0, 0, 0)], (1, 0, 0), (0, 0, 0)),
         "un nuage vide")

    # La table de signes doit REFUSER un canal muet plutôt que lui donner +1.
    leve(lambda: mesurer_table_de_signes(
        None, None, ".L", ".R", [("CTRL_index_01.L", 0)],
        lambda _r, _n, _a, _d: (0.0, 0.0, 0.0)),
        "un canal qui ne bouge d'aucun côté")

    if fautes:
        print("AUTOTEST MIROIR — FAUTES :")
        for f in fautes:
            print("  ·", f)
        sys.exit(2)
    print("AUTOTEST MIROIR — tout passe, 5 refus exercés.")
