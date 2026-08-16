"""Un rig humain complet, construit SANS AUCUN MAILLAGE.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/rig-humain.py -- DOSSIER [taille_m] [rendus]

═══ POURQUOI IL NE MESURE RIEN ═══

Tout le reste de ce dépôt part d'un maillage et en déduit un squelette. Cela
marche pour les centres articulaires — un centre se lit bien sur une forme.
Cela ne marche pas pour les ORIENTATIONS : le pouce de ce dépôt n'est opposé
qu'à 42,2 degrés pour 70 à 90 attendus, parce que la chair du maillage de base
le porte à plat et que rien dans la géométrie ne dit que c'est faux. Toutes les
recherches de contact passent ensuite leur temps à rattraper dans les
articulations les degrés qui manquent à la racine.

Ce script inverse l'ordre. Il ne connaît qu'une TAILLE. Tout le reste vient de
l'anthropométrie : chaque longueur est une fraction de la stature, et chaque
fraction est écrite dans une table qu'un lecteur peut contester ligne à ligne.
Le maillage viendra se poser sur ce squelette, et non l'inverse.

Le rig est donc la RÉFÉRENCE, pas une déduction.
"""
import bpy
import sys
import os
import json
import math
import mathutils

_a = sys.argv[sys.argv.index("--") + 1:]
DOSSIER = _a[0]
TAILLE = float(_a[1]) if len(_a) > 1 and _a[1][0].isdigit() else 1.78
RENDUS = "rendus" in _a or "visage" in _a
VISAGE = "visage" in _a
RACINE = os.environ["ATLAS_RACINE"]
sys.path.insert(0, os.path.join(RACINE, "atelier"))
os.makedirs(DOSSIER, exist_ok=True)
import eclairage
import visage

V = mathutils.Vector
H = TAILLE


def dire(cle, valeur):
    print("ATLAS_" + cle.upper() + " " + json.dumps(valeur, ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════════
#   LA TABLE — chaque nombre est une fraction de la STATURE
# ═══════════════════════════════════════════════════════════════════
# Elle vient de l'anthropométrie adulte classique (proportions de Drillis &
# Contini et de NASA-STD-3000, arrondies au millième). Elle est ici pour être
# CONTESTÉE : un lecteur qui trouve une fraction fausse la corrige à un seul
# endroit, et tout le squelette suit. C'est l'inverse d'un rig ajusté os par os
# à l'œil, où chaque correction est locale et se perd.
P = {
    # hauteurs, depuis le sol
    "z_cheville":      0.039,
    "z_genou":         0.285,
    "z_hanche":        0.530,
    "z_L5":            0.560,
    "z_T12":           0.700,
    "z_T1":            0.818,   # ≈ hauteur d'épaule
    "z_C7":            0.830,
    "z_menton":        0.870,
    "z_bouche":        0.895,
    "z_nez":           0.915,
    "z_oeil":          0.936,
    "z_sourcil":       0.947,
    "z_sommet":        1.000,
    # largeurs, en demi-écarts depuis l'axe
    "demi_hanche":     0.095,
    "demi_epaule":     0.129,
    "demi_thorax":     0.096,
    "demi_tete":       0.055,
    "demi_pupille":    0.018,
    "demi_condyle":    0.043,
    # profondeurs, +Y vers l'ARRIÈRE
    "y_dos_thorax":    0.052,
    "y_sternum":      -0.055,
    "y_dos_bassin":    0.045,
    "y_face":         -0.098,
    "y_nuque":         0.058,
    # membres
    "long_bras":       0.186,
    "long_avant_bras": 0.146,
    "long_main":       0.108,
    "long_pied":       0.152,
    "large_pied":      0.055,
    "talon_arriere":   0.045,
}


def h(cle):
    return P[cle] * H


# ═══ VIDER LA SCENE DE DEPART, ET LE FAIRE EN PREMIER ═══
#
# `--factory-startup` n'ouvre pas une scene vide : il ouvre la scene par defaut
# de Blender, avec un CUBE de deux metres a l'origine, une lampe et une camera.
# Ce cube a coupe trois rendus de squelette en deux, et j'ai cherche la faute
# dans le cyclo, dans le sol, dans le monde — partout sauf dans l'inventaire de
# la scene. Une dalle claire en travers d'une image n'est pas forcement le
# decor : ca peut etre un objet qu'on n'a jamais regarde.
for _ob in list(bpy.data.objects):
    bpy.data.objects.remove(_ob, do_unlink=True)

CENSUS = []
arm = bpy.data.armatures.new("ARM_humain")
rig = bpy.data.objects.new("RIG_humain", arm)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")


def poser(nom, tete, queue, parent=None, connecte=False, groupe="divers"):
    t, q = V(tete), V(queue)
    if (q - t).length < 1e-4:
        raise SystemExit(f"ATLAS_REFUS l'os {nom} est de longueur nulle — "
                         "un os sans direction n'a pas de roulis, et tout ce "
                         "qui s'y accroche hérite d'un repère arbitraire.")
    eb = arm.edit_bones.new(nom)
    eb.head, eb.tail = t, q
    if parent:
        if parent not in arm.edit_bones:
            raise SystemExit(f"ATLAS_REFUS l'os {nom} réclame le parent "
                             f"{parent}, qui n'existe pas. Une hiérarchie qui "
                             "se replie sur un parent de secours fabrique un "
                             "squelette qui a l'air complet et ne l'est pas.")
        eb.parent = arm.edit_bones[parent]
        eb.use_connect = connecte
    CENSUS.append({"os": nom, "groupe": groupe,
                   "longueur_mm": round((q - t).length * 1000, 1)})
    return eb


# ═══════════════════════════════════════════════════════════════════
#   1 · LE RACHIS — 24 vertèbres présacrées, sur une COURBE
# ═══════════════════════════════════════════════════════════════════
# Un dos humain n'est pas droit : lordose lombaire, cyphose thoracique,
# lordose cervicale. On pose donc la ligne comme une somme de trois arcs, et
# non comme un segment — sans quoi tout ce qui s'y accroche part faux.
def y_rachis(t):
    """t va de 0 au sacrum à 1 à l'atlas ; +Y vers l'arrière."""
    lordose_l = -0.020 * H * math.sin(math.pi * min(t / 0.34, 1.0))
    cyphose_t = +0.024 * H * math.sin(math.pi * max(0.0, min(
        (t - 0.30) / 0.42, 1.0)))
    lordose_c = -0.016 * H * math.sin(math.pi * max(0.0, min(
        (t - 0.72) / 0.28, 1.0)))
    return h("y_dos_bassin") + lordose_l + cyphose_t + lordose_c


NIV = ([("L", i) for i in range(5, 0, -1)]
       + [("T", i) for i in range(12, 0, -1)]
       + [("C", i) for i in range(7, 0, -1)])
Z_BAS, Z_HAUT = h("z_L5"), h("z_C7") + (h("z_sommet") - h("z_C7")) * 0.34
_z = [Z_BAS + (Z_HAUT - Z_BAS) * (i / len(NIV)) for i in range(len(NIV) + 1)]
VERT = {}
for _i, (_l, _n) in enumerate(NIV):
    _nom = f"{_l}{_n}"
    VERT[_nom] = (V((0.0, y_rachis(_i / len(NIV)), _z[_i])),
                  V((0.0, y_rachis((_i + 1) / len(NIV)), _z[_i + 1])))

BASSIN = V((0.0, h("y_dos_bassin") * 0.4, h("z_hanche")))
poser("root", (0, 0, 0), (0, 0.20 * H, 0), groupe="racine")
poser("pelvis", BASSIN, VERT["L5"][0], "root", groupe="racine")
poser("sacrum", BASSIN, BASSIN.lerp(VERT["L5"][0], 0.6), "pelvis",
      groupe="racine")
_p = "sacrum"
for _i in range(4):
    _a0 = BASSIN.lerp(V((0.0, BASSIN.y + 0.035 * H, BASSIN.z - 0.045 * H)),
                      _i / 4.0)
    _b0 = BASSIN.lerp(V((0.0, BASSIN.y + 0.035 * H, BASSIN.z - 0.045 * H)),
                      (_i + 1) / 4.0)
    poser(f"coccyx_{_i + 1:02d}", _a0, _b0, _p, connecte=(_i > 0),
          groupe="racine")
    _p = f"coccyx_{_i + 1:02d}"

_p = "pelvis"
for _l, _n in NIV:
    _nom = f"{_l}{_n}"
    _t, _q = VERT[_nom]
    poser(_nom, _t, _q, _p, connecte=(_p not in ("pelvis",)),
          groupe=("lombaires" if _l == "L" else
                  "thoraciques" if _l == "T" else "cervicales"))
    _p = _nom

# ═══════════════════════════════════════════════════════════════════
#   2 · LA CAGE — chaque côte est un ARC de trois segments
# ═══════════════════════════════════════════════════════════════════
# Le premier jet posait un os DROIT de la vertèbre à un point latéral : les
# douze paires se croisaient en éventail et la cage ressemblait à un épi. Une
# côte réelle contourne le thorax. On la parcourt donc sur une ellipse, du dos
# vers le sternum, en trois segments — postérieur, latéral, antérieur.
_z_t1, _z_t12 = VERT["T1"][1].z, VERT["T12"][0].z
_haut_thorax = _z_t1 - _z_t12
poser("sternum",
      V((0.0, h("y_sternum"), _z_t1 - _haut_thorax * 0.10)),
      V((0.0, h("y_sternum") * 0.86, _z_t1 - _haut_thorax * 0.86)),
      "T1", groupe="cage")

for _n in range(1, 13):
    _f = (_n - 1) / 11.0
    _vert = f"T{_n}"
    _zc = VERT[_vert][0].z
    # la cage est la plus large vers la 7e côte, et se referme aux extrémités
    _amp = 0.42 + 0.58 * math.sin(math.pi * min(1.0, 0.18 + _f * 0.95))
    _a = h("demi_thorax") * _amp                 # demi-largeur
    _b = (h("y_dos_thorax") - h("y_sternum")) * 0.5 * _amp   # demi-profondeur
    _yc = (h("y_dos_thorax") + h("y_sternum")) * 0.5
    _chute = _haut_thorax * 0.10 * _amp          # une côte descend en avant
    for _c, _s in (("L", -1.0), ("R", +1.0)):
        _pts = []
        for _k in range(4):
            _ang = math.pi * (1.0 - _k / 3.0 * 0.82)   # 180° → 32°
            _pts.append(V((_s * _a * math.sin(_ang),
                           _yc + _b * math.cos(_ang),
                           _zc - _chute * (_k / 3.0) ** 1.4)))
        _pts[0] = VERT[_vert][0]
        _par = _vert
        for _k in range(3):
            poser(f"rib_{_n:02d}_{_k + 1:02d}.{_c}", _pts[_k], _pts[_k + 1],
                  _par, connecte=(_k > 0), groupe="cage")
            _par = f"rib_{_n:02d}_{_k + 1:02d}.{_c}"

# ═══════════════════════════════════════════════════════════════════
#   3 · TÊTE ET VISAGE
# ═══════════════════════════════════════════════════════════════════
_base_crane = VERT["C1"][1]
_sommet = V((0.0, h("y_nuque") * 0.5, h("z_sommet")))
poser("head", _base_crane, _sommet, "C1", connecte=True, groupe="tete")
_menton = V((0.0, h("y_face") * 0.92, h("z_menton")))
_condyle = V((0.0, h("y_nuque") * 0.35, h("z_oeil") - 0.012 * H))
poser("skull", _base_crane, V((0.0, h("y_face"), h("z_oeil"))), "head",
      groupe="tete")
# ═══ LA MACHOIRE : UNE CHARNIERE, ET UNE GLISSIERE ═══
# Une vraie machoire ne fait pas que tourner : elle AVANCE et se decale sur le
# cote. Les deux condyles etaient poses, rien n'exploitait cette translation.
poser("jaw", _condyle, _menton, "head", groupe="visage")
poser("jaw_slide", _condyle, _condyle + V((0.0, -0.030 * H, 0.0)), "head",
      groupe="visage")
for _c, _s in (("L", -1.0), ("R", +1.0)):
    poser(f"jaw_hinge.{_c}", V((_s * h("demi_condyle"), _condyle.y, _condyle.z)),
          V((_s * h("demi_condyle") * 0.55, _menton.y, _menton.z)), "jaw",
          groupe="visage")

# ═══ TOUT LE VISAGE, POSE SUR UNE SURFACE ═══
_z_bas_tete = h("z_menton") - (h("z_sommet") - h("z_menton")) * 0.10
_c_tete = V((0.0, (h("y_face") + h("y_nuque")) * 0.5,
             (_z_bas_tete + h("z_sommet")) * 0.5))
TETE = visage.Tete(_c_tete, h("demi_tete"),
                   (h("y_nuque") - h("y_face")) * 0.5,
                   (h("z_sommet") - _z_bas_tete) * 0.5)
_os_visage = visage.construire(poser, TETE, P, H, h)

# ═══════════════════════════════════════════════════════════════════
#   4 · ÉPAULES, BRAS, MAINS
# ═══════════════════════════════════════════════════════════════════
NOMS_DOIGTS = ["thumb", "index", "middle", "ring", "pinky"]
# proportions de la main : chaque phalange en fraction de la longueur de main
PHALANGES = {"thumb":  [0.46, 0.20, 0.16],
             "index":  [0.46, 0.24, 0.14, 0.10],
             "middle": [0.46, 0.26, 0.16, 0.10],
             "ring":   [0.46, 0.24, 0.15, 0.10],
             "pinky":  [0.45, 0.19, 0.11, 0.08]}
ECART_DOIGTS = {"thumb": -0.62, "index": -0.24, "middle": 0.0,
                "ring": 0.24, "pinky": 0.47}

for _c, _s in (("L", -1.0), ("R", +1.0)):
    _sf = f".{_c}"
    _ep = V((_s * h("demi_epaule"), h("y_dos_thorax") * 0.12, h("z_T1")))
    _co = _ep + V((_s * h("long_bras") * 0.86, 0.0, -h("long_bras") * 0.50))
    _po = _co + V((_s * h("long_avant_bras") * 0.80, 0.0,
                   -h("long_avant_bras") * 0.60))
    poser(f"clavicle{_sf}", V((0.0, h("y_sternum") * 0.75, h("z_T1"))), _ep,
          "T1", groupe="epaule")
    poser(f"scapula{_sf}", V((_s * h("demi_thorax") * 0.35,
                              h("y_dos_thorax") * 0.92, h("z_T1")
                              - _haut_thorax * 0.10)),
          _ep + V((0.0, h("y_dos_thorax") * 0.45, 0.0)), "T2",
          groupe="epaule")
    poser(f"upperarm{_sf}", _ep, _co, f"clavicle{_sf}", connecte=True,
          groupe="bras")
    poser(f"upperarm_twist{_sf}", _ep.lerp(_co, 0.5), _co, f"upperarm{_sf}",
          groupe="bras")
    poser(f"forearm{_sf}", _co, _po, f"upperarm{_sf}", connecte=True,
          groupe="bras")
    for _k, _f0, _f1 in ((1, 0.34, 0.67), (2, 0.67, 1.0)):
        poser(f"forearm_twist_{_k:02d}{_sf}", _co.lerp(_po, _f0),
              _co.lerp(_po, _f1), f"forearm{_sf}", groupe="bras")
    _axe = (_po - _co).normalized()
    _lat = V((0.0, 1.0, 0.0))                       # travers de la main
    _norm = _axe.cross(_lat).normalized()           # normale palmaire
    _lm = h("long_main")
    poser(f"hand{_sf}", _po, _po + _axe * (_lm * 0.44), f"forearm{_sf}",
          connecte=True, groupe="bras")
    for _nd in NOMS_DOIGTS:
        _e = ECART_DOIGTS[_nd] * h("large_pied") * 0.62
        _ph = PHALANGES[_nd]
        _dir = (_axe + _lat * (_e / max(_lm, 1e-6)) * 1.6).normalized()
        # ═══ LE POUCE EST PRONATÉ ═══
        # C'est LA correction que ce dépôt a payée le plus cher : un pouce
        # laissé dans le plan des doigts n'oppose pas, et toute recherche de
        # contact passe ensuite son temps à rattraper 30 à 45 degrés qui
        # manquent à la racine. Ici il part sous la paume, dès la construction.
        if _nd == "thumb":
            _dir = (_axe * 0.55 + _lat * (_s * -0.55) + _norm * -0.62
                    ).normalized()
        _pt = _po + _lat * _e * 0.35
        _par = f"hand{_sf}"
        for _k, _fr in enumerate(_ph):
            _suiv = _pt + _dir * (_lm * _fr)
            _nom = (f"{_nd}_meta{_sf}" if _k == 0
                    else f"{_nd}_{_k:02d}{_sf}")
            poser(_nom, _pt, _suiv, _par, connecte=(_k > 1), groupe="doigts")
            _par, _pt = _nom, _suiv
    for _nom, _a2, _b2 in (
            (f"shoulder_deform{_sf}", _ep, _ep.lerp(_co, 0.2)),
            (f"elbow_deform{_sf}", _co, _co.lerp(_po, 0.2)),
            (f"wrist_deform{_sf}", _po, _po.lerp(_co, 0.15)),
            (f"biceps{_sf}", _ep.lerp(_co, 0.25), _ep.lerp(_co, 0.72)),
            (f"triceps{_sf}", _ep.lerp(_co, 0.22), _ep.lerp(_co, 0.78)),
            (f"deltoid{_sf}", _ep, _ep.lerp(_co, 0.36))):
        poser(_nom, _a2, _b2,
              f"upperarm{_sf}" if "wrist" not in _nom and "elbow" not in _nom
              else (f"forearm{_sf}" if "elbow" in _nom else f"hand{_sf}"),
              groupe="muscles")

# ═══════════════════════════════════════════════════════════════════
#   5 · JAMBES, PIEDS, ORTEILS
# ═══════════════════════════════════════════════════════════════════
ORTEILS = ["big_toe", "toe_02", "toe_03", "toe_04", "toe_05"]
LONG_ORTEIL = {"big_toe": 1.00, "toe_02": 0.98, "toe_03": 0.92,
               "toe_04": 0.83, "toe_05": 0.70}

for _c, _s in (("L", -1.0), ("R", +1.0)):
    _sf = f".{_c}"
    _ha = V((_s * h("demi_hanche"), h("y_dos_bassin") * 0.30, h("z_hanche")))
    _ge = V((_s * h("demi_hanche") * 0.82, 0.0, h("z_genou")))
    _ch = V((_s * h("demi_hanche") * 0.74, 0.0, h("z_cheville")))
    _bo = _ch + V((0.0, -h("long_pied") * 0.80, -h("z_cheville")))
    poser(f"thigh{_sf}", _ha, _ge, "pelvis", groupe="jambe")
    for _k, _f0, _f1 in ((1, 0.0, 0.34), (2, 0.34, 0.67)):
        poser(f"thigh_twist_{_k:02d}{_sf}", _ha.lerp(_ge, _f0),
              _ha.lerp(_ge, _f1), f"thigh{_sf}", groupe="jambe")
    poser(f"shin{_sf}", _ge, _ch, f"thigh{_sf}", connecte=True, groupe="jambe")
    for _k, _f0, _f1 in ((1, 0.34, 0.67), (2, 0.67, 1.0)):
        poser(f"shin_twist_{_k:02d}{_sf}", _ge.lerp(_ch, _f0),
              _ge.lerp(_ch, _f1), f"shin{_sf}", groupe="jambe")
    poser(f"heel{_sf}", _ch, _ch + V((0.0, h("talon_arriere"),
                                      -h("z_cheville") * 0.85)),
          f"shin{_sf}", groupe="pied")
    _plante = _ch + V((0.0, -h("long_pied") * 0.42, -h("z_cheville")))
    poser(f"foot{_sf}", _ch, _plante, f"shin{_sf}", connecte=True,
          groupe="pied")
    for _k, _nt in enumerate(ORTEILS):
        _x = _plante.x + (_k - 2) * h("large_pied") * 0.38 * (-_s)
        _rac = V((_x, _plante.y, _plante.z))
        _lg = h("long_pied") * 0.30 * LONG_ORTEIL[_nt]
        poser(f"{_nt}_meta{_sf}", _ch.lerp(_rac, 0.30), _rac, f"foot{_sf}",
              groupe="orteils")
        _npl = 2 if _nt == "big_toe" else 3
        _par, _pt = f"{_nt}_meta{_sf}", _rac
        for _ph2 in range(_npl):
            _suiv = _pt + V((0.0, -_lg / _npl, 0.0))
            poser(f"{_nt}_{_ph2 + 1:02d}{_sf}", _pt, _suiv, _par,
                  connecte=(_ph2 > 0), groupe="orteils")
            _par, _pt = f"{_nt}_{_ph2 + 1:02d}{_sf}", _suiv
    for _nom, _a2, _b2, _par2 in (
            (f"hip_deform{_sf}", _ha, _ha.lerp(_ge, 0.18), f"thigh{_sf}"),
            (f"knee_deform{_sf}", _ge, _ge.lerp(_ch, 0.18), f"shin{_sf}"),
            (f"ankle_deform{_sf}", _ch, _ch.lerp(_plante, 0.35), f"foot{_sf}"),
            (f"calf{_sf}", _ge.lerp(_ch, 0.18), _ge.lerp(_ch, 0.58),
             f"shin{_sf}"),
            (f"quad{_sf}", _ha.lerp(_ge, 0.30), _ha.lerp(_ge, 0.82),
             f"thigh{_sf}"),
            (f"glute{_sf}", V((_s * h("demi_hanche") * 0.7,
                               h("y_dos_bassin") * 0.9, h("z_hanche"))),
             V((_s * h("demi_hanche") * 0.7, h("y_dos_bassin") * 1.5,
                h("z_hanche") - 0.03 * H)), "pelvis"),
            (f"hip_blade{_sf}", BASSIN,
             V((_s * h("demi_hanche") * 1.05, h("y_dos_bassin") * 0.9,
                h("z_hanche") + 0.05 * H)), "pelvis")):
        poser(_nom, _a2, _b2, _par2, groupe="muscles")

# ── le tronc, les masses ──────────────────────────────────────────
for _c, _s in (("L", -1.0), ("R", +1.0)):
    _sf = f".{_c}"
    poser(f"pec{_sf}", V((0.0, h("y_sternum") * 0.9, h("z_T1")
                          - _haut_thorax * 0.22)),
          V((_s * h("demi_thorax") * 0.78, h("y_sternum") * 0.65,
             h("z_T1") - _haut_thorax * 0.32)), "T3", groupe="muscles")
    poser(f"lat{_sf}", V((_s * h("demi_thorax") * 0.35,
                          h("y_dos_thorax") * 0.95, h("z_T1")
                          - _haut_thorax * 0.25)),
          V((_s * h("demi_thorax") * 0.92, h("y_dos_thorax") * 0.75,
             VERT["T12"][0].z)), "T6", groupe="muscles")
    poser(f"trap{_sf}", V((0.0, h("y_dos_thorax") * 0.95, h("z_C7"))),
          V((_s * h("demi_epaule") * 0.70, h("y_dos_thorax") * 0.85,
             h("z_T1"))), "T1", groupe="muscles")
poser("belly", VERT["L3"][0],
      V((0.0, h("y_sternum") * 0.80, VERT["L3"][0].z)), "L3", groupe="muscles")

bpy.ops.object.mode_set(mode="OBJECT")

_par_groupe = {}
for _e in CENSUS:
    _par_groupe[_e["groupe"]] = _par_groupe.get(_e["groupe"], 0) + 1
_cv = visage.couverture_facs([b.name for b in arm.bones])
dire("couverture_facs", _cv)
dire("recensement", {"taille_m": H, "os_total": len(arm.bones),
                     "groupes": _par_groupe,
                     "aucun_maillage_consulte": True})

# ═══ AUCUN OS NE DOIT ÊTRE ORPHELIN NI DÉMESURÉ ═══
_sans_parent = [b.name for b in arm.bones if b.parent is None
                and b.name != "root"]
_trop = [{"os": e["os"], "mm": e["longueur_mm"]} for e in CENSUS
         if e["longueur_mm"] > H * 300]
dire("controles", {"os_sans_parent": _sans_parent or "aucun",
                   "os_demesures": _trop or "aucun",
                   "regle_demesure": "plus de 30 % de la stature"})
if _sans_parent or _trop:
    raise SystemExit("ATLAS_REFUS le squelette a des os orphelins ou démesurés")

_blend = os.path.join(DOSSIER, "RIG-humain.blend")
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(_blend))
print("ATLAS_RIG_ECRIT " + _blend)


# ═══════════════════════════════════════════════════════════════════
#   6 · LE RENDRE
# ═══════════════════════════════════════════════════════════════════
if RENDUS:
    def octaedre(tete, queue, ep):
        u = queue - tete
        L = u.length
        u = u.normalized()
        a = V((0, 0, 1)) if abs(u.z) < 0.9 else V((1, 0, 0))
        e1 = u.cross(a).normalized()
        e2 = u.cross(e1).normalized()
        c = tete + u * (L * 0.14)
        vs = [tete, queue, c + e1 * ep, c + e2 * ep, c - e1 * ep, c - e2 * ep]
        fs = [(0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 2),
              (1, 3, 2), (1, 4, 3), (1, 5, 4), (1, 2, 5)]
        me = bpy.data.meshes.new("OS")
        me.from_pydata([tuple(x) for x in vs], [], fs)
        me.update()
        return me

    sc = bpy.context.scene
    _sombre = {"monde_gris": 0.012, "fond_gris": 0.035, "fond_base_z": 0.0}
    _pieces = []
    for _b in arm.bones:
        _L = (_b.tail_local - _b.head_local).length
        _me = octaedre(_b.head_local, _b.tail_local,
                       max(0.0015 * H, min(0.011 * H, _L * 0.14)))
        _ob = bpy.data.objects.new("OS_" + _b.name, _me)
        sc.collection.objects.link(_ob)
        _pieces.append(_ob)
    for _o in sc.objects:
        _o.select_set(_o in _pieces)
    bpy.context.view_layer.objects.active = _pieces[0]
    bpy.ops.object.join()
    sq = bpy.context.active_object
    sq.name = "GEO_squelette"
    bpy.ops.object.shade_flat()

    # ═══ LE TOUR DU VISAGE, DOUZE VUES ═══
    # Un visage ne se juge pas de face. Les os de paupière, de narine et de
    # commissure se lisent de trois quarts et de profil, et c'est là que se
    # voient les trous — un côté qui n'a pas son jumeau, un os qui pointe
    # dans le vide.
    if VISAGE:
        _c_tete = V((0.0, h("y_face") * 0.30,
                     (h("z_menton") + h("z_sommet")) * 0.5))
        _larg = (h("z_sommet") - h("z_menton")) * 1.15
        _hh2 = {}
        for _k in range(12):
            _ang = math.radians(_k * 30.0)
            _d = V((math.sin(_ang), math.cos(_ang), 0.10)).normalized()
            eclairage.poser_studio(sc, materiau_clay=True, objets_clay=[sq],
                                   reglages=_sombre)
            sc.render.film_transparent = False
            eclairage.cadrer(sq, -_d, _c_tete, _larg, scene=sc)
            _e3 = eclairage.eclairer_rasant(_c_tete, -_d, -_d, +1,
                                            largeur_sujet=_larg, scene=sc,
                                            reglages=_sombre)
            _r3 = eclairage.rendre(
                os.path.join(DOSSIER, f"visage-{_k * 30:03d}.png"), sc)
            _hh2[f"{_k * 30:03d}"] = {"ecretage_pct": _r3["ecretage_pct"]}
        dire("rendus_visage", _hh2)

    _centre = V((0.0, 0.0, H * 0.5))
    _histos = {}
    for _nom, _dir in (("face", V((0.0, 1.0, 0.10))),
                       ("profil", V((1.0, 0.0, 0.10))),
                       ("trois-quarts", V((0.75, 0.66, 0.14)))):
        _d = _dir.normalized()
        # ═══ LE FOND SUIT LE SUJET, IL N'EST PAS UNE CONSTANTE ═══
        # Sur la main, un fond noir écrasait le côté ombre d'une chair claire
        # et j'ai remis un cyclo gris. Sur un squelette blanc, ce même cyclo
        # gris efface la silhouette : os clair sur fond clair, on ne lit plus
        # ni les côtes ni les phalanges. Ce n'est pas une contradiction, c'est
        # la même règle — le fond se choisit CONTRE le sujet.
        eclairage.poser_studio(sc, materiau_clay=True, objets_clay=[sq],
                               reglages=_sombre)
        # ═══ SANS CECI, LE FOND N'EST PAS NOIR : IL EST ABSENT ═══
        # Le studio rend en film transparent, ce qui est juste pour composer.
        # Sur un squelette blanc regarde tel quel, l'alpha vide s'affiche BLANC
        # dans tout visualiseur — et l'os disparait dans son propre fond. On
        # rend donc le monde opaque : c'est lui qu'on veut voir.
        sc.render.film_transparent = False
        eclairage.cadrer(sq, -_d, _centre, H * 1.04, scene=sc)
        # ═══ AUCUN CYCLO ICI, ET C'EST UN CHOIX ═══
        # Trois placements du plan de fond ont donne trois images ou une dalle
        # claire coupait le sujet. Un plan de studio demande de connaitre la
        # hauteur d'objectif et l'assise du sujet ; tant que `poser_fond` ne
        # les recoit pas, le regler jusqu'a ce qu'UNE image passe le recasse au
        # cadrage suivant. Le monde presque noir suffit : un os blanc s'y
        # detache mieux que sur n'importe quelle carte grise.
        _e2 = eclairage.eclairer_rasant(_centre, -_d, -_d, +1,
                                        largeur_sujet=H * 1.04, scene=sc,
                                        reglages=_sombre)
        _hh = eclairage.rendre(os.path.join(DOSSIER, f"rig-{_nom}.png"), sc)
        _histos[_nom] = {"ecretage_pct": _hh["ecretage_pct"],
                         "key_contre_normale_deg": round(
                             _e2["key_angle_vs_normale_deg"], 1)}
    dire("rendus", _histos)

print("ATLAS_TERMINE")
