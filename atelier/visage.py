"""Le visage : une ossature posée sur une surface, et sa couverture FACS.

═══ POURQUOI UNE SURFACE, ET PAS UNE LISTE DE POINTS ═══

Le premier visage de ce dépôt avait 56 os qui pointaient TOUS vers l'avant :
sourcils, joues, lèvres et narines partaient d'un point du crâne vers la face,
et la planche à 360 degrés montrait un hérisson. C'est la faute du pouce sous
un autre nom — un os dont la direction et le roulis ne veulent rien dire.
L'animateur qui en tourne un obtient un axe arbitraire, et il compensera dans
les voisins.

Ici, la tête est un ellipsoïde. Chaque os de visage se pose SUR cette surface :
il en reçoit un point, une NORMALE SORTANTE — qui devient son roulis — et deux
TANGENTES. Un sourcil court alors le long du sourcil, une lèvre le long de la
ligne de bouche, un pli nasogénien le long du pli. La direction porte enfin un
sens, et le roulis est le même pour tous : +Z sort du visage.

═══ ET LA COMPLÉTUDE SE MESURE ═══

« Il ne manque rien » est une opinion. Le FACS — Facial Action Coding System —
décrit un visage humain par une quarantaine d'unités d'action. Une ossature est
complète si chaque unité trouve les os qui la portent. `couverture_facs()` rend
la liste de celles qui passent ET de celles qui manquent : c'est un test qui
peut échouer, pas une assurance.
"""
import math
import mathutils

V = mathutils.Vector


class Tete:
    """La tête comme un ellipsoïde : un point, une normale, deux tangentes.

    Demi-axes : `a` en largeur, `b` en profondeur, `c` en hauteur, centrés sur
    `centre`. Tous viennent de la table de proportions, aucun n'est tapé ici.
    """

    def __init__(self, centre, a, b, c):
        self.c0, self.a, self.b, self.c = V(centre), a, b, c

    def point(self, u, w, avancee=1.0):
        """`u` de −1 (gauche) à +1 (droite), `w` de −1 (menton) à +1 (sommet).

        `avancee` rapproche ou éloigne de l'axe : 1 = sur la peau.
        """
        u = max(-0.999, min(0.999, u))
        w = max(-0.999, min(0.999, w))
        reste = 1.0 - u * u - w * w
        prof = math.sqrt(max(0.0, reste))
        return self.c0 + V((u * self.a, -prof * self.b * avancee, w * self.c))

    def normale(self, u, w):
        """La normale sortante — le gradient de l'ellipsoïde, normalisé."""
        u = max(-0.999, min(0.999, u))
        w = max(-0.999, min(0.999, w))
        prof = math.sqrt(max(1e-6, 1.0 - u * u - w * w))
        n = V((u / self.a, -prof / self.b, w / self.c))
        return n.normalized()

    def tangentes(self, u, w):
        """(le long du visage vers l'extérieur, vers le haut) — orthonormées."""
        n = self.normale(u, w)
        haut = V((0.0, 0.0, 1.0))
        lat = haut.cross(n)
        if lat.length < 1e-5:
            lat = V((1.0, 0.0, 0.0))
        lat.normalize()
        vert = n.cross(lat).normalized()
        return lat, vert


# ═══════════════════════════════════════════════════════════════════
#   LA CARTE DU VISAGE
# ═══════════════════════════════════════════════════════════════════
# Chaque entrée : (nom, u, w, direction, longueur_relative, parent, miroir)
#
#   `direction`  "lat"  le long du visage vers l'extérieur
#                "med"  vers l'axe
#                "haut" / "bas"
#                "sort" hors du visage (globe oculaire, cible de regard)
#   `longueur_relative` en fraction du demi-axe de largeur — de quoi lire l'os
#                sans qu'il devienne une pique. Le premier jet en faisait des
#                lances de 45 mm sur un visage de 230.
#
# Les `w` viennent des hauteurs de la table (œil, nez, bouche, menton), remises
# en coordonnée d'ellipsoïde par le constructeur.
CARTE = [
    # ── le front : il n'existait pas, et sans lui lever un sourcil ne plisse
    #    aucune peau ───────────────────────────────────────────────────────
    ("frontalis_inner", 0.16, 0.62, "haut", 0.30, "skull", True),
    ("frontalis_mid",   0.36, 0.60, "haut", 0.30, "skull", True),
    ("frontalis_outer", 0.56, 0.54, "haut", 0.28, "skull", True),
    ("temple",          0.72, 0.34, "haut", 0.26, "skull", True),
    ("scalp",           0.00, 0.86, "haut", 0.30, "skull", False),
    # ── les sourcils, le long du sourcil ────────────────────────────────
    ("corrugator", 0.09, 0.32, "med", 0.20, "skull", True),
    ("brow_inner", 0.13, 0.34, "lat", 0.24, "skull", True),
    ("brow_mid",   0.33, 0.36, "lat", 0.24, "skull", True),
    ("brow_outer", 0.53, 0.30, "lat", 0.22, "skull", True),
    # ── le globe, sa cible, et SIX os de paupière par œil ────────────────
    #    Une paupière par œil est un volet rigide : elle ne peut pas ROULER
    #    sur le globe, et le clignement est le mouvement le plus utilisé d'un
    #    visage.
    ("eye",     0.30, 0.20, "sort", 0.34, "skull", True),
    ("eye_aim", 0.30, 0.20, "sort", 0.90, "head",  True),
    ("lid_upper_inner", 0.20, 0.26, "lat", 0.18, "eye", True),
    ("lid_upper_mid",   0.30, 0.28, "lat", 0.18, "eye", True),
    ("lid_upper_outer", 0.40, 0.25, "lat", 0.18, "eye", True),
    ("lid_lower_inner", 0.20, 0.13, "lat", 0.18, "eye", True),
    ("lid_lower_mid",   0.30, 0.11, "lat", 0.18, "eye", True),
    ("lid_lower_outer", 0.40, 0.13, "lat", 0.18, "eye", True),
    ("canthus_inner", 0.17, 0.19, "med", 0.16, "skull", True),
    ("canthus_outer", 0.44, 0.19, "lat", 0.16, "skull", True),
    # ── le nez ──────────────────────────────────────────────────────────
    ("nose_bridge", 0.00, 0.24, "bas",  0.34, "skull", False),
    ("nose_tip",    0.00, -0.02, "bas", 0.22, "nose_bridge", False),
    ("nose_septum", 0.00, -0.10, "bas", 0.16, "nose_tip", False),
    ("nostril",     0.13, -0.05, "lat", 0.18, "skull", True),
    ("nose_wing",   0.19, -0.02, "haut", 0.18, "skull", True),
    # ── les joues : zygomatique, masséter, et le gonflement ──────────────
    ("cheek_zygomatic", 0.52, 0.06, "haut", 0.26, "skull", True),
    ("cheek_masseter",  0.62, -0.16, "bas", 0.28, "skull", True),
    ("cheek_puff",      0.46, -0.14, "lat", 0.26, "skull", True),
    # ── LES DEUX PLIS QUI PORTENT UN SOURIRE ────────────────────────────
    ("nasolabial_upper", 0.24, -0.08, "bas", 0.24, "skull", True),
    ("nasolabial_lower", 0.31, -0.22, "bas", 0.22, "skull", True),
    ("marionette",       0.30, -0.42, "bas", 0.24, "jaw",   True),
    # ── les lèvres : ligne EXTÉRIEURE et ligne INTÉRIEURE ────────────────
    #    Sans ligne intérieure — la lèvre humide — des lèvres ne peuvent ni se
    #    pincer ni se rentrer.
    ("lip_upper_out_in",     0.07, -0.28, "lat", 0.16, "skull", True),
    ("lip_upper_out_mid",    0.15, -0.29, "lat", 0.16, "skull", True),
    ("lip_upper_out_outer",  0.22, -0.31, "lat", 0.16, "skull", True),
    ("lip_lower_out_in",     0.07, -0.37, "lat", 0.16, "jaw", True),
    ("lip_lower_out_mid",    0.15, -0.36, "lat", 0.16, "jaw", True),
    ("lip_lower_out_outer",  0.22, -0.35, "lat", 0.16, "jaw", True),
    ("lip_corner",           0.27, -0.33, "lat", 0.18, "jaw", True),
    ("lip_upper_in_in",      0.06, -0.30, "lat", 0.13, "skull", True),
    ("lip_upper_in_mid",     0.13, -0.31, "lat", 0.13, "skull", True),
    ("lip_upper_in_outer",   0.20, -0.32, "lat", 0.13, "skull", True),
    ("lip_lower_in_in",      0.06, -0.35, "lat", 0.13, "jaw", True),
    ("lip_lower_in_mid",     0.13, -0.34, "lat", 0.13, "jaw", True),
    ("lip_lower_in_outer",   0.20, -0.34, "lat", 0.13, "jaw", True),
    ("philtrum",     0.00, -0.24, "bas",  0.20, "skull", False),
    ("lip_upper_mid_out", 0.00, -0.29, "bas", 0.14, "skull", False),
    ("lip_upper_mid_in",  0.00, -0.31, "bas", 0.12, "skull", False),
    ("lip_lower_mid_out", 0.00, -0.37, "haut", 0.14, "jaw", False),
    ("lip_lower_mid_in",  0.00, -0.35, "haut", 0.12, "jaw", False),
    # ── menton et mentonnier ────────────────────────────────────────────
    ("chin_crease", 0.00, -0.45, "bas", 0.18, "jaw", False),
    ("mentalis",    0.00, -0.52, "haut", 0.22, "jaw", False),
    ("chin",        0.00, -0.60, "bas", 0.22, "jaw", False),
    # ── les oreilles ────────────────────────────────────────────────────
    ("ear_base",  0.88, 0.10, "lat", 0.24, "skull", True),
    ("ear_helix", 0.90, 0.24, "haut", 0.22, "ear_base", True),
    ("ear_lobe",  0.88, -0.10, "bas", 0.18, "ear_base", True),
]

# ── la gorge : elle n'existait pas, et une tête qui tourne ne tirait
#    aucune peau ────────────────────────────────────────────────────────
GORGE = [("hyoid", 0.00, 0.20), ("adam", 0.00, 0.00),
         ("throat_lower", 0.00, -0.22)]

# ── la langue : quatre segments, pour qu'elle puisse se recourber ───────
LANGUE = ["tongue_root", "tongue_mid", "tongue_tip", "tongue_tip_up"]


# ═══════════════════════════════════════════════════════════════════
#   LE FACS — la complétude devient un test
# ═══════════════════════════════════════════════════════════════════
# Chaque unité d'action nomme les os SANS LESQUELS elle ne peut pas exister.
# Un rig qui n'en porte pas les os ne peut pas la jouer, quelle que soit
# l'ingéniosité de l'animateur. C'est donc un contrôle qui peut TOMBER.
FACS = {
    "AU1  lever le sourcil interne": ["brow_inner", "frontalis_inner"],
    "AU2  lever le sourcil externe": ["brow_outer", "frontalis_outer"],
    "AU4  froncer les sourcils": ["brow_inner", "brow_mid", "corrugator"],
    "AU5  ouvrir grand la paupière": ["lid_upper_mid", "lid_upper_inner",
                                      "lid_upper_outer"],
    "AU6  plisser la joue (vrai sourire)": ["cheek_zygomatic",
                                            "lid_lower_mid"],
    "AU7  resserrer les paupières": ["lid_lower_inner", "lid_lower_mid",
                                     "lid_lower_outer"],
    "AU9  plisser le nez": ["nose_wing", "nasolabial_upper"],
    "AU10 lever la lèvre supérieure": ["lip_upper_out_mid",
                                       "nasolabial_upper"],
    "AU11 creuser le sillon nasogénien": ["nasolabial_upper",
                                          "nasolabial_lower"],
    "AU12 étirer la commissure (sourire)": ["lip_corner", "cheek_zygomatic"],
    "AU13 gonfler la joue": ["cheek_puff"],
    "AU14 creuser les fossettes": ["lip_corner", "cheek_masseter"],
    "AU15 abaisser la commissure": ["lip_corner", "marionette"],
    "AU16 abaisser la lèvre inférieure": ["lip_lower_out_mid", "mentalis"],
    "AU17 lever le menton": ["mentalis", "chin_crease"],
    "AU18 avancer les lèvres (moue)": ["lip_upper_in_mid", "lip_lower_in_mid",
                                       "lip_corner"],
    "AU20 étirer les lèvres": ["lip_corner", "cheek_masseter"],
    "AU22 retrousser les lèvres": ["lip_upper_in_mid", "lip_lower_in_mid"],
    "AU23 serrer les lèvres": ["lip_upper_in_mid", "lip_lower_in_mid",
                               "lip_upper_out_mid"],
    "AU24 presser les lèvres": ["lip_upper_out_mid", "lip_lower_out_mid"],
    "AU25 entrouvrir les lèvres": ["jaw", "lip_lower_out_mid"],
    "AU26 laisser tomber la mâchoire": ["jaw"],
    "AU27 ouvrir la bouche en grand": ["jaw", "jaw_slide"],
    "AU28 rentrer les lèvres": ["lip_upper_in_mid", "lip_lower_in_mid"],
    "AU29 avancer la mâchoire": ["jaw_slide"],
    "AU30 décaler la mâchoire de côté": ["jaw_slide"],
    "AU31 serrer les mâchoires": ["cheek_masseter", "jaw"],
    "AU33 gonfler les joues (souffler)": ["cheek_puff"],
    "AU38 dilater les narines": ["nostril", "nose_wing"],
    "AU39 pincer les narines": ["nostril", "nose_septum"],
    "AU41 paupière tombante": ["lid_upper_mid"],
    "AU43 fermer les yeux": ["lid_upper_mid", "lid_lower_mid"],
    "AU45 cligner": ["lid_upper_inner", "lid_upper_mid", "lid_upper_outer",
                     "lid_lower_mid"],
    "AU51 tourner la tête": ["head"],
    "AU53 lever la tête": ["head", "hyoid"],
    "AU55 pencher la tête": ["head"],
    "AU61 regarder de côté": ["eye", "eye_aim"],
    "AU63 regarder en haut": ["eye", "eye_aim"],
    "déglutir / pomme d'Adam": ["adam", "hyoid", "throat_lower"],
    "langue qui se recourbe": ["tongue_tip", "tongue_tip_up"],
    "oreille qui bouge": ["ear_base"],
    "peau du crâne qui glisse": ["scalp"],
}


def couverture_facs(noms_presents):
    """Quelles unités d'action l'ossature peut porter, et lesquelles non."""
    base = set()
    for n in noms_presents:
        base.add(n.split(".")[0])
    passe, manque = [], {}
    for au, requis in FACS.items():
        absents = [r for r in requis if r not in base]
        if absents:
            manque[au] = absents
        else:
            passe.append(au)
    return {"unites_totales": len(FACS), "portees": len(passe),
            "non_portees": len(manque), "detail_manquant": manque,
            "taux": round(100.0 * len(passe) / len(FACS), 1)}


def construire(poser, tete, P, H, h):
    """Pose toute l'ossature du visage. `poser` vient de l'appelant."""
    poses = []

    def direction(nom_dir, u, w):
        lat, vert = tete.tangentes(u, w)
        n = tete.normale(u, w)
        return {"lat": lat, "med": -lat, "haut": vert, "bas": -vert,
                "sort": -n}[nom_dir]

    for nom, u, w, sens, lg, parent, miroir in CARTE:
        cotes = ((-1.0, ".L"), (1.0, ".R")) if miroir else ((1.0, ""),)
        for _s, _sfx in cotes:
            _u = u * _s
            _t = tete.point(_u, w, avancee=(0.72 if sens == "sort" else 1.0))
            _d = direction(sens, _u, w)
            if _s < 0 and sens in ("lat", "med"):
                _d = -_d if False else _d      # `lat` suit déjà le signe de u
            _q = _t + _d * (tete.a * lg)
            _par = parent + (_sfx if parent in
                             ("eye", "ear_base", "nose_bridge", "nose_tip")
                             and miroir else "")
            eb = poser(nom + _sfx, _t, _q, _par, groupe="visage")
            # ═══ LE ROULIS N'EST PAS LAISSÉ AU HASARD ═══
            # +Z de chaque os sort du visage. Un contrôleur « vers le haut »
            # veut alors dire la même chose sur tout le visage — c'est ce qui
            # manquait au pouce, et ce qui fabrique les compensations.
            eb.align_roll(tete.normale(_u, w))
            poses.append(nom + _sfx)

    # la gorge, sous le menton, sur l'axe
    _par = "C4"
    for _n, _u, _w in GORGE:
        _t = tete.point(_u, -0.62 - (0.10 if _n != "hyoid" else 0.0),
                        avancee=0.55)
        _t = _t + V((0.0, 0.0, (_w - 0.20) * tete.c * 0.55))
        _q = _t + V((0.0, -tete.b * 0.18, 0.0))
        poser(_n, _t, _q, _par, groupe="visage")
        poses.append(_n)
    for _s, _sfx in ((-1.0, ".L"), (1.0, ".R")):
        _t = tete.point(_s * 0.80, -0.58, avancee=0.80)
        _q = _t + V((_s * tete.a * 0.10, tete.b * 0.30, -tete.c * 0.70))
        poser("scm" + _sfx, _t, _q, "C6", groupe="visage")
        poses.append("scm" + _sfx)

    # la langue, quatre segments
    _par = "jaw"
    _base = tete.point(0.0, -0.34, avancee=0.30)
    for _i, _n in enumerate(LANGUE):
        _t = _base + V((0.0, -tete.b * 0.22 * _i, 0.0))
        _q = _t + V((0.0, -tete.b * 0.22,
                     tete.c * (0.10 if _n == "tongue_tip_up" else 0.0)))
        poser(_n, _t, _q, _par, connecte=(_i > 0), groupe="visage")
        _par = _n
        poses.append(_n)

    # les dents
    for _n, _dw, _par in (("teeth_upper", -0.27, "skull"),
                          ("teeth_lower", -0.36, "jaw")):
        _t = tete.point(0.0, _dw, avancee=0.40)
        poser(_n, _t, _t + V((0.0, -tete.b * 0.30, 0.0)), _par,
              groupe="visage")
        poses.append(_n)

    return poses
