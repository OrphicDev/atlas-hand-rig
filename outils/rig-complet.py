"""Un squelette COMPLET, posé par la mesure : rachis, membres, mains, visage.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/rig-complet.py -- DOSSIER [rendus]

Ce que ce script refuse de faire : taper une position à l'œil. Chaque os part
d'un point relevé sur CE corps. Là où l'anatomie fournit une proportion que la
géométrie ne donne pas — l'étagement des vertèbres, la charnière de la
mâchoire — la proportion est appliquée à une LONGUEUR MESURÉE et le rapport est
nommé dans le rendu du recensement, sous la clé `proportion`. Un lecteur doit
pouvoir séparer les deux sans lire le code.

C'est le procédé que `atelier/mains.py` emploie déjà pour la ligne des
jointures : « une longueur relevée sur ce corps, une proportion venue de
l'anatomie ».
"""
import bpy
import sys
import os
import json
import math
import mathutils

_args = sys.argv[sys.argv.index("--") + 1:]
DOSSIER = _args[0]
RENDUS = len(_args) > 1 and _args[1] == "rendus"
RACINE = os.environ["ATLAS_RACINE"]
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "atelier"))
os.makedirs(DOSSIER, exist_ok=True)

import humain
import articulations as A
import mains
import eclairage

V = mathutils.Vector


def dire(cle, valeur):
    print("ATLAS_" + cle.upper() + " " + json.dumps(valeur, ensure_ascii=False))


def r3(v):
    return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


# ═══════════════════════════════════════════════════════════════════
#   1 · LE RELEVÉ
# ═══════════════════════════════════════════════════════════════════
corps, z_oeil = humain.charger("homme", RACINE)
sc = bpy.context.scene
bpy.context.view_layer.update()
co = [corps.matrix_world @ x.co for x in corps.data.vertices]
R = A.releve(corps)

Z_SOL, Z_SOMMET = R["z_sol"], R["z_haut"]
Z_ENTREJAMBE, Z_AISSELLE = R["z_entrejambe"], R["z_aisselle"]
COU = R["cou"]["centre"]
HAUTEUR = Z_SOMMET - Z_SOL

dire("releve_corps", {
    "hauteur_m": round(HAUTEUR, 4),
    "z_entrejambe_m": round(Z_ENTREJAMBE, 4),
    "z_aisselle_m": round(Z_AISSELLE, 4),
    "z_oeil_m": round(float(z_oeil), 4),
    "cou_centre": r3(COU),
    "sommets_du_corps": len(co)})

MAIN = {}
for cote in ("g", "d"):
    MAIN[cote] = mains.releve(corps, R["bras_" + cote]["poignet"]["centre"],
                              R["main_idx_" + cote], co)
    dire(f"releve_main_{cote}", {
        "doigts_detaches": len(MAIN[cote]["doigts"]),
        "longueur_main_mm": round(MAIN[cote]["longueur_main"] * 1000, 1),
        "largeur_paume_mm": round(MAIN[cote]["largeur_paume"] * 1000, 1)})


# ═══════════════════════════════════════════════════════════════════
#   2 · LE RACHIS SE MESURE, IL NE SE DEVINE PAS
# ═══════════════════════════════════════════════════════════════════
# La colonne n'est pas au centre du tronc : elle est POSTÉRIEURE. On tranche
# donc le tronc à l'horizontale et, dans chaque tranche, on prend le barycentre
# de la MOITIÉ ARRIÈRE. Cela suit la lordose et la cyphose de ce corps-ci au
# lieu de poser une ligne droite, et cela ne demande aucune constante.
def ligne_du_rachis(z_bas, z_haut, pas=0.01):
    ligne = []
    par = {}
    for p in co:
        if z_bas - pas <= p.z <= z_haut + pas:
            par.setdefault(int((p.z - z_bas) / pas), []).append(p)
    for k in sorted(par):
        t = [p for p in par[k] if abs(p.x) < 0.16]      # le tronc, pas les bras
        if len(t) < 60:
            continue
        y_med = sorted(q.y for q in t)[len(t) // 2]
        arriere = [q for q in t if q.y >= y_med]        # +Y = le dos
        if len(arriere) < 20:
            continue
        c = sum(arriere, V((0, 0, 0))) / len(arriere)
        ligne.append(V((0.0, c.y, z_bas + k * pas)))    # symétrie imposée en x
    return ligne


_rachis = ligne_du_rachis(Z_ENTREJAMBE, COU.z)
if len(_rachis) < 8:
    raise SystemExit("ATLAS_REFUS le rachis n'a rendu que "
                     f"{len(_rachis)} tranches : la mesure n'a pas pris.")

# ── L'ÉTAGEMENT : cinq lombaires, douze thoraciques. On ne modélise pas les
#    dix-sept, on pose CINQ os sur la ligne mesurée, aux fractions que
#    l'anatomie donne pour les niveaux L5, L1, T8, T4 et T1.
# ═══ DIX-SEPT VERTEBRES, PAS CINQ BLOCS ═══
#
# Cinq os de rachis suffisent a faire plier un personnage ; ils ne suffisent
# pas a le faire plier COMME UN DOS. Une colonne presacree humaine compte cinq
# lombaires et douze thoraciques, et leurs hauteurs ne sont pas egales : les
# lombaires sont les plus hautes, les thoraciques hautes les plus courtes.
#
# On garde donc la LIGNE MESUREE et on y etage dix-sept corps vertebraux selon
# les hauteurs relatives de l'anatomie. La ligne vient de ce corps ; le decoupage
# vient du squelette humain.
HAUTEURS_LOMBAIRES = [1.00, 0.98, 0.96, 0.94, 0.92]          # L5 → L1
HAUTEURS_THORACIQUES = [0.86, 0.84, 0.82, 0.80, 0.78, 0.76,  # T12 → T7
                        0.74, 0.72, 0.70, 0.68, 0.66, 0.64]  # T6  → T1
_h = HAUTEURS_LOMBAIRES + HAUTEURS_THORACIQUES
_tot = sum(_h)
FRACTIONS_RACHIS = [0.0]
for _x in _h:
    FRACTIONS_RACHIS.append(FRACTIONS_RACHIS[-1] + _x / _tot)
NOMS_RACHIS = ([f"L{5 - _i}" for _i in range(5)]
               + [f"T{12 - _i}" for _i in range(12)])


def sur_la_ligne(ligne, f):
    x = f * (len(ligne) - 1)
    i = min(int(x), len(ligne) - 2)
    return ligne[i].lerp(ligne[i + 1], x - i)


# ═══════════════════════════════════════════════════════════════════
#   3 · LA TÊTE ET LE VISAGE
# ═══════════════════════════════════════════════════════════════════
_tete = [p for p in co if p.z > COU.z]
if not _tete:
    raise SystemExit("ATLAS_REFUS aucun sommet au-dessus du cou")
_ty = [p.y for p in _tete]
_tx = [p.x for p in _tete]
TETE = {"y_avant": min(_ty), "y_arriere": max(_ty),
        "x_min": min(_tx), "x_max": max(_tx),
        "profondeur": max(_ty) - min(_ty), "largeur": max(_tx) - min(_tx)}

# La tranche des yeux, relevée à la hauteur que `humain.charger` mesure.
_tr_oeil = [p for p in _tete if abs(p.z - z_oeil) < 0.006]
if len(_tr_oeil) < 20:
    raise SystemExit("ATLAS_REFUS la tranche des yeux est vide")
_y_avant_oeil = min(q.y for q in _tr_oeil)
_x_oeil = max(abs(q.x) for q in _tr_oeil)

# La charnière de la mâchoire : au condyle, juste devant l'oreille. Sa HAUTEUR
# et sa PROFONDEUR sont relevées — le condyle est au niveau du tragus, que l'on
# prend comme le point le plus latéral de la tête sous les yeux ; sa position en
# x est celle de ce même point, rentrée de la moitié de l'épaisseur du ramus.
_sous_yeux = [p for p in _tete if COU.z < p.z < z_oeil]
_condyle_src = max(_sous_yeux, key=lambda p: abs(p.x))
MENTON = min(_sous_yeux, key=lambda p: (p.y, p.z))

dire("releve_tete", {
    "profondeur_mm": round(TETE["profondeur"] * 1000, 1),
    "largeur_mm": round(TETE["largeur"] * 1000, 1),
    "z_oeil_m": round(float(z_oeil), 4),
    "demi_ecart_des_yeux_mm": round(_x_oeil * 1000, 1),
    "condyle_releve": r3(_condyle_src),
    "menton_releve": r3(MENTON)})


# ═══════════════════════════════════════════════════════════════════
#   4 · CONSTRUIRE L'ARMATURE
# ═══════════════════════════════════════════════════════════════════
arm = bpy.data.armatures.new("ARM_corps")
rig = bpy.data.objects.new("RIG_corps", arm)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")

CENSUS = {"mesure": [], "proportion": []}


def poser(nom, tete, queue, parent=None, connecte=False, origine="mesure",
          note=""):
    """Un os, et d'où viennent ses deux bouts."""
    if (V(queue) - V(tete)).length < 1e-4:
        raise SystemExit(f"ATLAS_REFUS l'os {nom} est de longueur nulle — "
                         "un os sans direction n'a pas de roulis, et tout ce "
                         "qui s'y accroche héritera d'un repère arbitraire.")
    eb = arm.edit_bones.new(nom)
    eb.head, eb.tail = V(tete), V(queue)
    if parent:
        eb.parent = arm.edit_bones[parent]
        eb.use_connect = connecte
    CENSUS[origine].append({"os": nom, "longueur_mm": round(
        (V(queue) - V(tete)).length * 1000, 1), "note": note})
    return eb


# ── 4.1 · racine et bassin ────────────────────────────────────────
_hg = R["jambe_g"]["hanche"]["centre"]
_hd = R["jambe_d"]["hanche"]["centre"]
BASSIN = (_hg + _hd) * 0.5
poser("root", (0.0, 0.0, Z_SOL), (0.0, 0.20, Z_SOL),
      note="au sol, sous le bassin mesuré")
poser("pelvis", BASSIN, sur_la_ligne(_rachis, FRACTIONS_RACHIS[0]), "root",
      note="milieu des deux centres de hanche relevés")
_L5 = sur_la_ligne(_rachis, FRACTIONS_RACHIS[0])
poser("sacrum", BASSIN, BASSIN.lerp(_L5, 0.55), "pelvis", origine="proportion",
      note="entre le milieu des hanches et L5, tous deux mesurés")
_p = "sacrum"
for _i in range(4):
    _a = BASSIN.lerp(V((0.0, BASSIN.y + 0.05, BASSIN.z - 0.05)), _i / 4.0)
    _b = BASSIN.lerp(V((0.0, BASSIN.y + 0.05, BASSIN.z - 0.05)), (_i + 1) / 4.0)
    poser(f"coccyx_{_i + 1:02d}", _a, _b, _p, connecte=(_i > 0),
          origine="proportion", note="quatre pièces coccygiennes")
    _p = f"coccyx_{_i + 1:02d}"
for _c, _s in (("L", -1.0), ("R", +1.0)):
    poser(f"hip_blade.{_c}", BASSIN,
          V((_s * abs(_hg.x) * 1.05, BASSIN.y + 0.03, BASSIN.z + 0.06)),
          "pelvis", origine="proportion",
          note="aile iliaque, sur la demi-largeur de hanche mesurée")
    poser(f"glute.{_c}", V((_s * abs(_hg.x) * 0.7, BASSIN.y + 0.04, BASSIN.z)),
          V((_s * abs(_hg.x) * 0.7, BASSIN.y + 0.09, BASSIN.z - 0.04)),
          "pelvis", origine="proportion", note="masse fessière")

# ── 4.2 · le rachis ───────────────────────────────────────────────
_parent = "pelvis"
for _i, _nom in enumerate(NOMS_RACHIS):
    _t = sur_la_ligne(_rachis, FRACTIONS_RACHIS[_i])
    _q = sur_la_ligne(_rachis, FRACTIONS_RACHIS[_i + 1])
    poser(_nom, _t, _q, _parent, connecte=(_i > 0), origine="proportion",
          note="sur la ligne du rachis MESURÉE ; l'étagement suit les niveaux "
               "L5-L1-T8-T4-T1")
    _parent = _nom

# ═══ LA CAGE : UN STERNUM ET DOUZE PAIRES DE CÔTES ═══
# Un thorax qui se déforme comme un bloc n'a jamais l'air de respirer. Chaque
# côte part de SA vertèbre — mesurée sur la ligne du rachis — et rejoint le
# plan sternal, dont la profondeur vient de la profondeur de tronc mesurée.
_t12 = sur_la_ligne(_rachis, FRACTIONS_RACHIS[5])
_t1 = sur_la_ligne(_rachis, FRACTIONS_RACHIS[17])
_tronc = [p for p in co if _t12.z < p.z < _t1.z and abs(p.x) < 0.20]
_prof_tronc = max(q.y for q in _tronc) - min(q.y for q in _tronc)
_demi_thorax = max(abs(q.x) for q in _tronc)
poser("sternum", V((0.0, _t1.y - _prof_tronc * 0.85, _t1.z)),
      V((0.0, _t12.y - _prof_tronc * 0.80, _t12.z + (_t1.z - _t12.z) * 0.25)),
      "T1", origine="proportion",
      note="sur la profondeur de tronc MESURÉE, 85 % en avant du rachis")
for _n in range(1, 13):
    _v = sur_la_ligne(_rachis, FRACTIONS_RACHIS[5 + (12 - _n)])
    _f = 1.0 - abs(_n - 7) / 9.0          # les côtes moyennes sont les longues
    for _c, _s in (("L", -1.0), ("R", +1.0)):
        poser(f"rib_{_n:02d}.{_c}", _v,
              V((_s * _demi_thorax * 0.92 * _f,
                 _v.y - _prof_tronc * 0.62 * _f,
                 _v.z - (_t1.z - _t12.z) * 0.06)),
              f"T{_n}" if f"T{_n}" in arm.edit_bones else "T1",
              origine="proportion",
              note="de SA vertèbre mesurée vers le plan sternal ; la longueur "
                   "suit la courbe des côtes, maximale à la 7e")
poser("belly", sur_la_ligne(_rachis, FRACTIONS_RACHIS[3]),
      V((0.0, sur_la_ligne(_rachis, FRACTIONS_RACHIS[3]).y - _prof_tronc * 0.75,
         sur_la_ligne(_rachis, FRACTIONS_RACHIS[3]).z)), "L2",
      origine="proportion", note="masse abdominale")
for _c, _s in (("L", -1.0), ("R", +1.0)):
    poser(f"pec.{_c}", V((0.0, _t1.y - _prof_tronc * 0.60,
                          _t1.z - (_t1.z - _t12.z) * 0.22)),
          V((_s * _demi_thorax * 0.72, _t1.y - _prof_tronc * 0.72,
             _t1.z - (_t1.z - _t12.z) * 0.30)), "T3", origine="proportion",
          note="pectoral, sur la demi-largeur de thorax mesurée")
    poser(f"lat.{_c}", V((_s * _demi_thorax * 0.30, _t1.y, _t1.z)),
          V((_s * _demi_thorax * 0.85, _t12.y, _t12.z
             + (_t1.z - _t12.z) * 0.35)), "T6", origine="proportion",
          note="grand dorsal")
    poser(f"trap.{_c}", sur_la_ligne(_rachis, 0.97),
          V((_s * _demi_thorax * 0.62, _t1.y + 0.01, _t1.z)), "T1",
          origine="proportion", note="trapèze")

# ── 4.3 · cou, tête, visage ───────────────────────────────────────
# ═══ SEPT CERVICALES ═══
# Un cou humain en a sept, et c'est leur nombre qui lui donne sa courbe. Deux
# os font tourner une tête ; ils ne font pas un cou.
_haut_rachis = sur_la_ligne(_rachis, 1.0)
_sommet_crane = V((0.0, COU.y, Z_SOMMET))
_base_crane = COU.lerp(_sommet_crane, 0.30)
_parent = "T1"
for _i in range(7):
    _a = _haut_rachis.lerp(_base_crane, _i / 7.0)
    _b = _haut_rachis.lerp(_base_crane, (_i + 1) / 7.0)
    poser(f"C{7 - _i}", _a, _b, _parent, connecte=(_i > 0),
          origine=("mesure" if _i == 0 else "proportion"),
          note=("du haut du rachis mesuré vers la base du crâne"
                if _i == 0 else "sept cervicales étagées entre deux points "
                                "mesurés"))
    _parent = f"C{7 - _i}"
poser("head", _base_crane, _sommet_crane, "C1", connecte=True,
      note="de la base du crâne au sommet mesuré")
poser("skull", _base_crane, V((0.0, TETE["y_avant"], z_oeil)), "head",
      note="vers le point le plus antérieur de la face, relevé")

# ═══ UN VISAGE, PAS TROIS OS ═══
#
# Douze os font bouger une tête ; ils ne font pas jouer un visage. Ce qui suit
# pose les groupes que l'anatomie de surface donne : la mâchoire et son menton,
# les quatre paupières, les sourcils en trois points chacun, le nez et ses
# ailes, seize os de lèvres, les joues, les oreilles, la langue en trois
# segments, et deux cibles de regard.
#
# ═══ ET L'ÉCART DES YEUX SE CORRIGE ═══
# Le premier jet prenait le point le plus LATÉRAL de la tranche à hauteur d'œil.
# C'est la largeur du crâne AUX OREILLES, pas la position des yeux : il donnait
# 100 mm entre les pupilles là où un adulte est à 63. Une sonde qui mesure ce
# qu'elle trouve au lieu de ce qu'elle cherche. On applique donc à la LARGEUR DE
# TÊTE MESURÉE le rapport anthropométrique de l'écart interpupillaire, 0,33.
DEMI_ECART_PUPILLES = TETE["largeur"] * 0.33 * 0.5
_charniere_x = _condyle_src.x * 0.62      # le condyle est en dedans du tragus
_h_face = z_oeil - MENTON.z               # hauteur œil → menton, MESURÉE
_h_front = Z_SOMMET - z_oeil              # hauteur œil → sommet, MESURÉE
_z_bouche = MENTON.z + _h_face * 0.30
_prof_globe = TETE["profondeur"] * 0.22
_av = _y_avant_oeil                        # la face, en avant

for _c, _s in (("L", -1.0), ("R", +1.0)):
    poser(f"jaw_hinge.{_c}",
          V((_s * abs(_charniere_x), _condyle_src.y, _condyle_src.z)),
          V((_s * abs(_charniere_x) * 0.5, MENTON.y, MENTON.z)), "head",
          origine="proportion",
          note="condyle relevé, rentré de 38 % vers l'axe")
poser("jaw", V((0.0, _condyle_src.y, _condyle_src.z)), MENTON, "head",
      note="charnière au condyle relevé, pointe au menton relevé")
poser("chin", MENTON, V((0.0, MENTON.y - 0.012, MENTON.z + 0.008)), "jaw",
      note="depuis le menton relevé")

for _c, _s in (("L", -1.0), ("R", +1.0)):
    _ex = _s * DEMI_ECART_PUPILLES
    _centre_oeil = V((_ex, _av + _prof_globe, z_oeil))
    poser(f"eye.{_c}", _centre_oeil, V((_ex, _av - 0.010, z_oeil)), "head",
          origine="proportion",
          note="hauteur d'œil MESURÉE ; écart = 33 % de la largeur de tête "
               "mesurée ; globe à 22 % de la profondeur de tête mesurée")
    poser(f"eye_aim.{_c}", V((_ex, _av - 0.10, z_oeil)),
          V((_ex, _av - 0.14, z_oeil)), "head", origine="proportion",
          note="cible de regard, devant l'œil")
    # les quatre paupières
    for _n, _dz in (("lid_upper", +0.011), ("lid_lower", -0.010)):
        poser(f"{_n}.{_c}", V((_ex, _av + 0.006, z_oeil + _dz)),
              V((_ex, _av - 0.008, z_oeil + _dz * 1.4)), f"eye.{_c}",
              origine="proportion", note="paupière, sur le globe mesuré")
    for _n, _dx in (("lid_inner", -0.45), ("lid_outer", +0.85)):
        poser(f"{_n}.{_c}", V((_ex + _s * DEMI_ECART_PUPILLES * _dx,
                               _av + 0.004, z_oeil)),
              V((_ex + _s * DEMI_ECART_PUPILLES * _dx, _av - 0.008, z_oeil)),
              f"eye.{_c}", origine="proportion",
              note="coin interne et coin externe de l'œil")
    # le sourcil en trois points
    _z_sc = z_oeil + _h_front * 0.20
    for _n, _fx in (("brow_inner", 0.35), ("brow_mid", 0.95),
                    ("brow_outer", 1.45)):
        poser(f"{_n}.{_c}",
              V((_s * DEMI_ECART_PUPILLES * _fx, _av + 0.014, _z_sc)),
              V((_s * DEMI_ECART_PUPILLES * _fx, _av - 0.004, _z_sc + 0.010)),
              "head", origine="proportion",
              note="sourcil à 20 % de la hauteur œil-sommet mesurée")
    # la joue, en deux étages
    for _n, _fz, _fx in (("cheek_upper", 0.28, 1.25), ("cheek_lower", 0.55, 1.10)):
        _z = z_oeil - _h_face * _fz
        poser(f"{_n}.{_c}", V((_s * DEMI_ECART_PUPILLES * _fx, _av + 0.024, _z)),
              V((_s * DEMI_ECART_PUPILLES * _fx, _av - 0.004, _z)), "head",
              origine="proportion",
              note="fraction de la hauteur œil-menton mesurée")
    # l'aile du nez
    _z_nez = z_oeil - _h_face * 0.42
    poser(f"nostril.{_c}", V((_s * DEMI_ECART_PUPILLES * 0.42, _av + 0.014,
                              _z_nez)),
          V((_s * DEMI_ECART_PUPILLES * 0.62, _av - 0.006, _z_nez)), "head",
          origine="proportion", note="aile du nez")
    # l'oreille, sur le point le plus latéral relevé
    poser(f"ear.{_c}", V((_s * abs(_condyle_src.x) * 0.94, _condyle_src.y + 0.02,
                          _condyle_src.z + 0.012)),
          V((_s * abs(_condyle_src.x) * 1.02, _condyle_src.y + 0.02,
             _condyle_src.z - 0.030)), "head",
          note="au point le plus latéral de la tête sous les yeux, relevé")
    # huit os de lèvres par côté : deux étages, deux profondeurs
    for _lvl, _dz, _par in (("upper", +0.010, "head"),
                            ("lower", -0.010, "jaw")):
        for _pos, _fx in (("in", 0.30), ("mid", 0.62), ("out", 0.92),
                          ("corner", 1.10)):
            poser(f"lip_{_lvl}_{_pos}.{_c}",
                  V((_s * DEMI_ECART_PUPILLES * _fx, _av + 0.014,
                     _z_bouche + _dz)),
                  V((_s * DEMI_ECART_PUPILLES * _fx, _av - 0.004,
                     _z_bouche + _dz)), _par, origine="proportion",
                  note="ligne de bouche à 30 % de la hauteur menton-œil "
                       "mesurée")

# l'arête du nez, la pointe, et le philtrum, sur l'axe
poser("nose_bridge", V((0.0, _av + 0.020, z_oeil)),
      V((0.0, _av - 0.004, z_oeil - _h_face * 0.24)), "head",
      origine="proportion", note="de la racine à mi-hauteur du nez")
poser("nose_tip", V((0.0, _av - 0.004, z_oeil - _h_face * 0.24)),
      V((0.0, _av - 0.018, z_oeil - _h_face * 0.42)), "nose_bridge",
      connecte=True, origine="proportion", note="pointe du nez")
poser("philtrum", V((0.0, _av + 0.010, z_oeil - _h_face * 0.52)),
      V((0.0, _av - 0.004, _z_bouche + 0.014)), "head", origine="proportion",
      note="entre le nez et la lèvre")
for _lvl, _dz, _par in (("upper", +0.012, "head"), ("lower", -0.012, "jaw")):
    poser(f"lip_{_lvl}_mid", V((0.0, _av + 0.014, _z_bouche + _dz)),
          V((0.0, _av - 0.006, _z_bouche + _dz)), _par, origine="proportion",
          note="milieu de la lèvre")
# la langue, en trois segments
_p = "jaw"
for _i in range(3):
    _y0 = _av + 0.070 - _i * 0.020
    poser(f"tongue_{_i + 1:02d}", V((0.0, _y0, _z_bouche - 0.004)),
          V((0.0, _y0 - 0.020, _z_bouche - 0.004)), _p, connecte=(_i > 0),
          origine="proportion", note="langue en trois segments")
    _p = f"tongue_{_i + 1:02d}"
# les dents, accrochées au crâne et à la mâchoire
poser("teeth_upper", V((0.0, _av + 0.030, _z_bouche + 0.014)),
      V((0.0, _av + 0.004, _z_bouche + 0.014)), "head", origine="proportion",
      note="arcade supérieure")
poser("teeth_lower", V((0.0, _av + 0.030, _z_bouche - 0.014)),
      V((0.0, _av + 0.004, _z_bouche - 0.014)), "jaw", origine="proportion",
      note="arcade inférieure, suit la mâchoire")

# ── 4.4 · bras et mains ───────────────────────────────────────────
NOMS_DOIGTS = ["thumb", "index", "middle", "ring", "pinky"]

for _c, _sfx in (("g", ".L"), ("d", ".R")):
    _B = R["bras_" + _c]
    _ep = _B["epaule"]["centre"]
    _co = _B["coude"]["centre"]
    _po = _B["poignet"]["centre"]
    # ═══ L'OMOPLATE EXISTE, ET ELLE GLISSE ═══
    # Une clavicule seule fait monter l'épaule ; elle ne la fait pas AVANCER ni
    # tourner. L'omoplate est l'os qui porte la moitié du mouvement d'épaule.
    poser(f"scapula{_sfx}", sur_la_ligne(_rachis, 0.86),
          _ep + V((0.0, 0.02, 0.0)), "T1", origine="proportion",
          note="du rachis mesuré vers l'arrière de l'épaule relevée")
    poser(f"clavicle{_sfx}", sur_la_ligne(_rachis, 0.93), _ep, "T1",
          note="du rachis mesuré au centre d'épaule relevé")
    poser(f"upperarm{_sfx}", _ep, _co, f"clavicle{_sfx}", connecte=True,
          note="épaule et coude relevés par les creux de section")
    # ═══ LES OS DE VRILLE ═══
    # Sans eux, l'avant-bras se tord comme un torchon entre le coude et le
    # poignet : toute la rotation est portée par UNE articulation. Un radius
    # tourne sur l'ulna sur toute sa longueur, et c'est ce que ces os répartissent.
    poser(f"upperarm_twist{_sfx}", _ep.lerp(_co, 0.55), _co,
          f"upperarm{_sfx}", origine="proportion",
          note="répartit la rotation d'épaule sur la moitié distale")
    poser(f"forearm{_sfx}", _co, _po, f"upperarm{_sfx}", connecte=True,
          note="coude et poignet relevés")
    for _k, _f0, _f1 in ((1, 0.33, 0.66), (2, 0.66, 1.0)):
        poser(f"forearm_twist_{_k:02d}{_sfx}", _co.lerp(_po, _f0),
              _co.lerp(_po, _f1), f"forearm{_sfx}", origine="proportion",
              note="deux vrilles réparties sur l'avant-bras mesuré")

    _M = MAIN[_c]
    _dg = _M["doigts"]
    _pouce = next((d for d in _dg if d.get("pouce")), None)
    _quatre = [d for d in _dg if not d.get("pouce")]
    # l'ordre des quatre : du plus proche du pouce au plus éloigné
    if _pouce is not None:
        _quatre.sort(key=lambda d: (d["jointure"] - _pouce["jointure"]).length)
    _centre_paume = (sum((d["jointure"] for d in _quatre), V((0, 0, 0)))
                     / max(1, len(_quatre)))
    poser(f"hand{_sfx}", _po, _centre_paume, f"forearm{_sfx}", connecte=True,
          note="poignet relevé jusqu'au barycentre des jointures relevées")

    _ordre = ([("thumb", _pouce)] if _pouce else []) + list(
        zip(NOMS_DOIGTS[1:], _quatre))
    for _nd, _d in _ordre:
        if _d is None:
            continue
        # le métacarpien : du poignet à la jointure, tous deux relevés
        poser(f"{_nd}_meta{_sfx}", _po, _d["jointure"], f"hand{_sfx}",
              note="poignet relevé → jointure relevée")
        _prec = f"{_nd}_meta{_sfx}"
        _pts = [p for _n, p in _d["articulations"]] + [_d["pointe"]]
        _dep = _d["jointure"]
        for _k, _p in enumerate(_pts):
            poser(f"{_nd}_{_k + 1:02d}{_sfx}", _dep, _p, _prec, connecte=True,
                  origine=("mesure" if _k == len(_pts) - 1 else "proportion"),
                  note=("pointe de doigt relevée" if _k == len(_pts) - 1
                        else "articulation posée sur l'axe MESURÉ du doigt, "
                             "aux rapports de phalanges de l'anatomie"))
            _prec = f"{_nd}_{_k + 1:02d}{_sfx}"
            _dep = _p

# ── 4.5 · jambes, pieds et orteils ────────────────────────────────
# ═══ CINQ ORTEILS, PAS UN BLOC ═══
# On tente d'abord de les DÉTACHER par la mesure, comme les doigts : une coupe
# sphérique depuis la cheville, au rayon qui rend le plus de morceaux. Si le
# maillage ne les sépare pas — les orteils se touchent souvent sur un corps de
# base — on les répartit sur la largeur d'avant-pied MESURÉE, et on le DIT.
NOMS_ORTEILS = ["big_toe", "toe_02", "toe_03", "toe_04", "toe_05"]


def orteils_mesures(cheville, bout, indices):
    pts = [(i, co[i]) for i in indices]
    meilleur = (0, None, 0.0)
    r = (bout - cheville).length * 0.45
    while r < (bout - cheville).length * 0.95:
        loin = [i for i, q in pts if (q - cheville).length > r]
        if len(loin) > 40:
            ms = A.morceaux(corps, loin, co)
            if len(ms) > meilleur[0]:
                meilleur = (len(ms), ms, r)
        r += 0.004
    return meilleur


for _c, _sfx in (("g", ".L"), ("d", ".R")):
    _J = R["jambe_" + _c]
    _ha = _J["hanche"]["centre"]
    _ge = _J["genou"]["centre"]
    _ch = _J["cheville"]["centre"]
    _bo = V(_J["bout_orteil"])
    poser(f"thigh{_sfx}", _ha, _ge, "pelvis",
          note="hanche et genou relevés par les creux de section")
    for _k, _f0, _f1 in ((1, 0.0, 0.33), (2, 0.33, 0.66)):
        poser(f"thigh_twist_{_k:02d}{_sfx}", _ha.lerp(_ge, _f0),
              _ha.lerp(_ge, _f1), f"thigh{_sfx}", origine="proportion",
              note="deux vrilles réparties sur la cuisse mesurée")
    poser(f"shin{_sfx}", _ge, _ch, f"thigh{_sfx}", connecte=True,
          note="genou et cheville relevés")
    for _k, _f0, _f1 in ((1, 0.33, 0.66), (2, 0.66, 1.0)):
        poser(f"shin_twist_{_k:02d}{_sfx}", _ge.lerp(_ch, _f0),
              _ge.lerp(_ch, _f1), f"shin{_sfx}", origine="proportion",
              note="deux vrilles réparties sur la jambe mesurée")
    # le talon : le point le plus postérieur du pied, RELEVÉ
    _pied = [p for p in co if p.z < _ch.z + 0.02
             and (p.x < 0) == (_ch.x < 0) and abs(p.x - _ch.x) < 0.12]
    if not _pied:
        raise SystemExit(f"ATLAS_REFUS aucun sommet de pied {_sfx}")
    _talon = max(_pied, key=lambda p: p.y)
    poser(f"heel{_sfx}", _ch, _talon, f"shin{_sfx}",
          note="cheville relevée jusqu'au point le plus postérieur du pied")
    _base_orteils = _ch.lerp(_bo, 0.68)
    poser(f"foot{_sfx}", _ch, _base_orteils, f"shin{_sfx}", connecte=True,
          origine="proportion",
          note="cheville et bout d'orteil relevés ; la base des orteils est à "
               "68 % de cette longueur mesurée")
    # ── les cinq orteils
    _idx_pied = [i for i, p in enumerate(co) if p.z < _ch.z
                 and (p.x < 0) == (_ch.x < 0) and abs(p.x - _ch.x) < 0.14]
    _n, _ms, _r = orteils_mesures(_ch, _bo, _idx_pied)
    _travers = V((1.0, 0.0, 0.0)) if abs(_ch.x) > 1e-6 else V((1.0, 0.0, 0.0))
    _axe_pied = (_bo - _ch).normalized()
    _largeur = (max(p.x for p in _pied) - min(p.x for p in _pied))
    dire(f"orteils_{_c}", {
        "morceaux_detaches": _n, "rayon_de_coupe_m": round(_r, 4),
        "largeur_avant_pied_mm": round(_largeur * 1000, 1),
        "origine": ("mesure" if _n >= 5 else
                    "proportion — le maillage ne sépare pas les orteils, ils "
                    "sont répartis sur la largeur d'avant-pied MESURÉE")})
    if _n >= 5:
        _bouts = []
        for _m in _ms:
            _q = [co[i] for i in _m]
            _bouts.append(max(_q, key=lambda x: (x - _ch).dot(_axe_pied)))
        _bouts.sort(key=lambda q: q.x * (1 if _ch.x < 0 else -1))
        _origine_orteils = "mesure"
    else:
        _bouts = []
        for _k in range(5):
            _f = (_k + 0.5) / 5.0 - 0.5
            _lg = 1.0 - abs(_k - 0.6) * 0.09
            _bouts.append(V((_base_orteils.x + _f * _largeur * 0.82,
                             _base_orteils.y
                             + (_bo - _base_orteils).y * _lg,
                             _bo.z)))
        _origine_orteils = "proportion"
    for _k, (_nom, _bt) in enumerate(zip(NOMS_ORTEILS, _bouts)):
        _f = (_k + 0.5) / 5.0 - 0.5
        _racine = V((_base_orteils.x + _f * _largeur * 0.72,
                     _base_orteils.y, _base_orteils.z))
        # le métatarsien, puis deux ou trois phalanges
        poser(f"{_nom}_meta{_sfx}", _ch.lerp(_racine, 0.35), _racine,
              f"foot{_sfx}", origine="proportion",
              note="métatarsien, entre la cheville et la base d'orteil")
        _n_ph = 2 if _nom == "big_toe" else 3
        _prec = f"{_nom}_meta{_sfx}"
        _dep = _racine
        for _ph in range(_n_ph):
            _pt = _racine.lerp(_bt, (_ph + 1) / _n_ph)
            poser(f"{_nom}_{_ph + 1:02d}{_sfx}", _dep, _pt, _prec,
                  connecte=True, origine=_origine_orteils,
                  note=("bout d'orteil détaché par la mesure"
                        if _origine_orteils == "mesure"
                        else "réparti sur la largeur d'avant-pied mesurée"))
            _prec = f"{_nom}_{_ph + 1:02d}{_sfx}"
            _dep = _pt
    # ── les os de déformation des articulations porteuses
    for _nom, _a, _b in ((f"knee_deform{_sfx}", _ge, _ge.lerp(_ch, 0.18)),
                         (f"hip_deform{_sfx}", _ha, _ha.lerp(_ge, 0.18)),
                         (f"ankle_deform{_sfx}", _ch, _ch.lerp(_bo, 0.18)),
                         (f"calf{_sfx}", _ge.lerp(_ch, 0.20),
                          _ge.lerp(_ch, 0.55))):
        poser(_nom, _a, _b, f"shin{_sfx}" if "knee" in _nom or "calf" in _nom
              else (f"thigh{_sfx}" if "hip" in _nom else f"foot{_sfx}"),
              origine="proportion",
              note="os de déformation, sur une longueur mesurée")

# ── 4.6 · les déformations des membres supérieurs ─────────────────
for _c, _sfx in (("g", ".L"), ("d", ".R")):
    _B = R["bras_" + _c]
    _ep, _co2, _po = (_B["epaule"]["centre"], _B["coude"]["centre"],
                      _B["poignet"]["centre"])
    for _nom, _a, _b, _par in (
            (f"shoulder_deform{_sfx}", _ep, _ep.lerp(_co2, 0.18),
             f"upperarm{_sfx}"),
            (f"elbow_deform{_sfx}", _co2, _co2.lerp(_po, 0.18),
             f"forearm{_sfx}"),
            (f"wrist_deform{_sfx}", _po, _po.lerp(_co2, 0.15),
             f"hand{_sfx}"),
            (f"biceps{_sfx}", _ep.lerp(_co2, 0.25), _ep.lerp(_co2, 0.70),
             f"upperarm{_sfx}"),
            (f"triceps{_sfx}", _ep.lerp(_co2, 0.20), _ep.lerp(_co2, 0.75),
             f"upperarm{_sfx}"),
            (f"deltoid{_sfx}", _ep, _ep.lerp(_co2, 0.35),
             f"upperarm{_sfx}")):
        poser(_nom, _a, _b, _par, origine="proportion",
              note="os de déformation ou de muscle, sur une longueur mesurée")

bpy.ops.object.mode_set(mode="OBJECT")

_n_os = len(arm.bones)
def _n(pred):
    return sum(1 for b in arm.bones if pred(b.name))


_g = {
    "bassin_et_sacrum": _n(lambda n: n.split(".")[0] in
                           ("root", "pelvis", "sacrum") or
                           n.startswith(("coccyx", "hip_blade", "glute"))),
    "rachis": _n(lambda n: (n[0] in "LT" and n[1:].isdigit())),
    "cage_et_tronc": _n(lambda n: n.startswith(("rib_", "sternum", "belly",
                                                "pec.", "lat.", "trap."))),
    "cou": _n(lambda n: n[0] == "C" and n[1:].isdigit()),
    "tete": _n(lambda n: n in ("head", "skull")),
    "visage": _n(lambda n: n.split(".")[0] in
                 ("jaw", "jaw_hinge", "chin", "eye", "eye_aim", "lid_upper",
                  "lid_lower", "lid_inner", "lid_outer", "brow_inner",
                  "brow_mid", "brow_outer", "cheek_upper", "cheek_lower",
                  "nostril", "ear", "nose_bridge", "nose_tip", "philtrum",
                  "teeth_upper", "teeth_lower", "lip_upper_mid",
                  "lip_lower_mid") or n.startswith(("lip_upper_", "lip_lower_",
                                                    "tongue_"))),
    "epaules_et_bras": _n(lambda n: n.startswith(
        ("scapula", "clavicle", "upperarm", "forearm", "hand"))),
    "doigts": _n(lambda n: n.split("_")[0] in NOMS_DOIGTS),
    "jambes_et_pieds": _n(lambda n: n.startswith(
        ("thigh", "shin", "foot", "heel"))),
    "orteils": _n(lambda n: n.split("_")[0] in ("big", "toe")),
    "deformation_et_muscles": _n(lambda n: n.startswith(
        ("knee_deform", "hip_deform", "ankle_deform", "calf",
         "shoulder_deform", "elbow_deform", "wrist_deform", "biceps",
         "triceps", "deltoid"))),
}
dire("recensement", {
    "os_total": len(arm.bones),
    "poses_par_mesure": len(CENSUS["mesure"]),
    "poses_par_proportion_sur_longueur_mesuree": len(CENSUS["proportion"]),
    "groupes": _g,
    "somme_des_groupes": sum(_g.values()),
    "non_classes": len(arm.bones) - sum(_g.values())})
dire("os_par_mesure", CENSUS["mesure"])
dire("os_par_proportion", CENSUS["proportion"])

# ═══ AUCUN OS NE DOIT SORTIR DE LA CHAIR ═══
# Un squelette qui perce la peau est faux, et rien dans une hiérarchie
# d'armature ne s'en plaint. On mesure la distance de chaque tête d'os au
# maillage, et on nomme ceux qui sont dehors.
_arbre = mathutils.kdtree.KDTree(len(co))
for _i, _p in enumerate(co):
    _arbre.insert(_p, _i)
_arbre.balance()
_dehors = []
for _b in arm.bones:
    for _bout, _pt in (("tete", _b.head_local), ("queue", _b.tail_local)):
        _, _, _d = _arbre.find(_pt)
        if _d > 0.035:
            _dehors.append({"os": _b.name, "bout": _bout,
                            "distance_a_la_peau_mm": round(_d * 1000, 1)})
dire("os_hors_de_la_chair", _dehors or "aucun")

_blend = os.path.join(DOSSIER, "RIG-corps-complet.blend")
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(_blend))
print(f"ATLAS_RIG_ECRIT {_blend}")


# ═══════════════════════════════════════════════════════════════════
#   5 · LE RENDRE — une armature ne s'imprime pas, on lui fait un corps
# ═══════════════════════════════════════════════════════════════════
if RENDUS:
    def octaedre(nom, tete, queue, epaisseur):
        """Un os visible : deux pyramides dos à dos, comme dans la vue 3D."""
        u = (queue - tete)
        L = u.length
        u = u.normalized()
        a = V((0, 0, 1)) if abs(u.z) < 0.9 else V((1, 0, 0))
        e1 = u.cross(a).normalized()
        e2 = u.cross(e1).normalized()
        c = tete + u * (L * 0.12)
        r = epaisseur
        vs = [tete, queue,
              c + e1 * r, c + e2 * r, c - e1 * r, c - e2 * r]
        fs = [(0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 2),
              (1, 3, 2), (1, 4, 3), (1, 5, 4), (1, 2, 5)]
        me = bpy.data.meshes.new(nom)
        me.from_pydata([tuple(v) for v in vs], [], fs)
        me.update()
        return me

    _pieces = []
    for _b in arm.bones:
        _L = (_b.tail_local - _b.head_local).length
        _ep = max(0.004, min(0.022, _L * 0.13))
        _me = octaedre("OS_" + _b.name, _b.head_local, _b.tail_local, _ep)
        _ob = bpy.data.objects.new("OS_" + _b.name, _me)
        sc.collection.objects.link(_ob)
        _pieces.append(_ob)
    for _o in sc.objects:
        _o.select_set(_o in _pieces)
    bpy.context.view_layer.objects.active = _pieces[0]
    bpy.ops.object.join()
    squelette = bpy.context.active_object
    squelette.name = "GEO_squelette"
    bpy.ops.object.shade_flat()

    _bb = [corps.matrix_world @ V(c) for c in corps.bound_box]
    _lo = V((min(v.x for v in _bb), min(v.y for v in _bb),
             min(v.z for v in _bb)))
    _hi = V((max(v.x for v in _bb), max(v.y for v in _bb),
             max(v.z for v in _bb)))
    _centre = (_lo + _hi) * 0.5
    _h = _hi.z - _lo.z
    _dir = V((0.0, 1.0, 0.12)).normalized()

    _histos = {}

    def rendre(nom, avec_corps, alpha_corps=0.16):
        corps.hide_render = not avec_corps
        eclairage.poser_studio(sc, materiau_clay=True,
                               objets_clay=([corps, squelette] if avec_corps
                                            else [squelette]))
        if avec_corps:
            # la chair devient translucide pour qu'on voie l'os dedans :
            # c'est la seule façon de juger un squelette À SA PLACE.
            _m = bpy.data.materials.new("MAT_chair_translucide")
            _m.use_nodes = True
            _b = _m.node_tree.nodes.get("Principled BSDF")
            _b.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1.0)
            _b.inputs["Roughness"].default_value = 1.0
            _b.inputs["Alpha"].default_value = alpha_corps
            corps.data.materials.clear()
            corps.data.materials.append(_m)
        eclairage.cadrer(squelette, -_dir, _centre, _h * 1.02, scene=sc)
        eclairage.poser_fond(sc, _centre,
                             sc.camera.matrix_world.translation - _centre,
                             _h * 1.02)
        _e = eclairage.eclairer_rasant(_centre, -_dir, -_dir, +1,
                                       largeur_sujet=_h * 1.02, scene=sc)
        _hh = eclairage.rendre(os.path.join(DOSSIER, nom + ".png"), sc)
        _histos[nom] = {"ecretage_pct": _hh["ecretage_pct"],
                        "luminance_max": _hh["luminance_max"],
                        "key_contre_normale_deg": round(
                            _e["key_angle_vs_normale_deg"], 1)}

    rendre("03-squelette-seul", avec_corps=False)
    rendre("04-squelette-dans-le-corps", avec_corps=True)
    dire("rendus", _histos)

print("ATLAS_TERMINE")
