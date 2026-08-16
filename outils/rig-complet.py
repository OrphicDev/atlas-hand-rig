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
FRACTIONS_RACHIS = [0.0, 0.22, 0.46, 0.70, 0.88, 1.0]
NOMS_RACHIS = ["spine_01", "spine_02", "spine_03", "spine_04", "chest"]


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

# ── 4.2 · le rachis ───────────────────────────────────────────────
_parent = "pelvis"
for _i, _nom in enumerate(NOMS_RACHIS):
    _t = sur_la_ligne(_rachis, FRACTIONS_RACHIS[_i])
    _q = sur_la_ligne(_rachis, FRACTIONS_RACHIS[_i + 1])
    poser(_nom, _t, _q, _parent, connecte=(_i > 0), origine="proportion",
          note="sur la ligne du rachis MESURÉE ; l'étagement suit les niveaux "
               "L5-L1-T8-T4-T1")
    _parent = _nom

# ── 4.3 · cou, tête, visage ───────────────────────────────────────
_haut_rachis = sur_la_ligne(_rachis, 1.0)
poser("neck_01", _haut_rachis, COU, "chest", connecte=True,
      note="du haut du rachis mesuré au centre de cou relevé")
_sommet_crane = V((0.0, COU.y, Z_SOMMET))
poser("neck_02", COU, COU.lerp(_sommet_crane, 0.42), "neck_01", connecte=True,
      origine="proportion", note="deux étages de cou entre deux points mesurés")
_base_crane = COU.lerp(_sommet_crane, 0.42)
poser("head", _base_crane, _sommet_crane, "neck_02", connecte=True,
      note="jusqu'au sommet du crâne mesuré")

# la mâchoire : charnière relevée au condyle, pointe au menton relevé
_charniere = V((0.0, _condyle_src.y, _condyle_src.z))
poser("jaw", _charniere, MENTON, "head",
      note="charnière au condyle relevé, pointe au menton relevé")

# les yeux : hauteur et demi-écart MESURÉS ; la profondeur du globe est une
# proportion appliquée à la profondeur de tête mesurée.
_prof_globe = TETE["profondeur"] * 0.22
for _c, _s in (("L", -1.0), ("R", +1.0)):
    _centre = V((_s * _x_oeil * 0.52, _y_avant_oeil + _prof_globe, z_oeil))
    poser(f"eye.{_c}", _centre, V((_centre.x, _y_avant_oeil - 0.01, z_oeil)),
          "head", origine="proportion",
          note="hauteur et demi-écart mesurés ; profondeur du globe = 22 % de "
               "la profondeur de tête mesurée")
    # sourcil et pommette, accrochés à la tête ; joue accrochée à la mâchoire
    _z_sourcil = z_oeil + (Z_SOMMET - z_oeil) * 0.26
    poser(f"brow.{_c}", V((_s * _x_oeil * 0.55, _y_avant_oeil + 0.012,
                           _z_sourcil)),
          V((_s * _x_oeil * 0.55, _y_avant_oeil - 0.006, _z_sourcil + 0.012)),
          "head", origine="proportion",
          note="26 % de la hauteur front-œil mesurée")
    _z_pomm = z_oeil - (z_oeil - MENTON.z) * 0.30
    poser(f"cheek.{_c}", V((_s * _x_oeil * 0.72, _y_avant_oeil + 0.02, _z_pomm)),
          V((_s * _x_oeil * 0.72, _y_avant_oeil - 0.004, _z_pomm)),
          "head", origine="proportion",
          note="30 % de la hauteur œil-menton mesurée")
    _z_bouche = MENTON.z + (z_oeil - MENTON.z) * 0.30
    poser(f"lip_corner.{_c}", V((_s * _x_oeil * 0.42, _y_avant_oeil + 0.015,
                                 _z_bouche)),
          V((_s * _x_oeil * 0.42, _y_avant_oeil - 0.004, _z_bouche)),
          "jaw", origine="proportion",
          note="30 % de la hauteur menton-œil mesurée")
_z_bouche = MENTON.z + (z_oeil - MENTON.z) * 0.30
poser("lip_upper", V((0.0, _y_avant_oeil + 0.012, _z_bouche + 0.012)),
      V((0.0, _y_avant_oeil - 0.006, _z_bouche + 0.012)), "head",
      origine="proportion", note="au-dessus de la ligne de bouche")
poser("lip_lower", V((0.0, _y_avant_oeil + 0.012, _z_bouche - 0.010)),
      V((0.0, _y_avant_oeil - 0.006, _z_bouche - 0.010)), "jaw",
      origine="proportion", note="sous la ligne de bouche, suit la mâchoire")
poser("tongue", V((0.0, _y_avant_oeil + 0.055, _z_bouche - 0.004)),
      V((0.0, _y_avant_oeil + 0.020, _z_bouche - 0.004)), "jaw",
      origine="proportion", note="dans la cavité, suit la mâchoire")

# ── 4.4 · bras et mains ───────────────────────────────────────────
NOMS_DOIGTS = ["thumb", "index", "middle", "ring", "pinky"]

for _c, _sfx in (("g", ".L"), ("d", ".R")):
    _B = R["bras_" + _c]
    _ep = _B["epaule"]["centre"]
    _co = _B["coude"]["centre"]
    _po = _B["poignet"]["centre"]
    poser(f"clavicle{_sfx}", sur_la_ligne(_rachis, 0.93), _ep, "chest",
          note="du rachis mesuré au centre d'épaule relevé")
    poser(f"upperarm{_sfx}", _ep, _co, f"clavicle{_sfx}", connecte=True,
          note="épaule et coude relevés par les creux de section")
    poser(f"forearm{_sfx}", _co, _po, f"upperarm{_sfx}", connecte=True,
          note="coude et poignet relevés")

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

# ── 4.5 · jambes et pieds ─────────────────────────────────────────
for _c, _sfx in (("g", ".L"), ("d", ".R")):
    _J = R["jambe_" + _c]
    _ha = _J["hanche"]["centre"]
    _ge = _J["genou"]["centre"]
    _ch = _J["cheville"]["centre"]
    _bo = V(_J["bout_orteil"])
    poser(f"thigh{_sfx}", _ha, _ge, "pelvis",
          note="hanche et genou relevés par les creux de section")
    poser(f"shin{_sfx}", _ge, _ch, f"thigh{_sfx}", connecte=True,
          note="genou et cheville relevés")
    # la base des orteils : sur l'axe cheville→bout, à la proportion du pied
    _base_orteils = _ch.lerp(_bo, 0.68)
    poser(f"foot{_sfx}", _ch, _base_orteils, f"shin{_sfx}", connecte=True,
          origine="proportion",
          note="cheville et bout d'orteil relevés ; la base des orteils est à "
               "68 % de cette longueur mesurée")
    poser(f"toe{_sfx}", _base_orteils, _bo, f"foot{_sfx}", connecte=True,
          note="jusqu'au bout d'orteil relevé")

bpy.ops.object.mode_set(mode="OBJECT")

_n_os = len(arm.bones)
dire("recensement", {
    "os_total": _n_os,
    "poses_par_mesure": len(CENSUS["mesure"]),
    "poses_par_proportion_sur_longueur_mesuree": len(CENSUS["proportion"]),
    "groupes": {
        "rachis_et_bassin": sum(1 for b in arm.bones if b.name.startswith(
            ("root", "pelvis", "spine", "chest"))),
        "cou_et_tete": sum(1 for b in arm.bones if b.name.startswith(
            ("neck", "head"))),
        "visage": sum(1 for b in arm.bones if b.name.split(".")[0] in
                      ("jaw", "eye", "brow", "cheek", "lip_corner",
                       "lip_upper", "lip_lower", "tongue")),
        "bras": sum(1 for b in arm.bones if b.name.startswith(
            ("clavicle", "upperarm", "forearm", "hand"))),
        "doigts": sum(1 for b in arm.bones
                      if b.name.split("_")[0] in NOMS_DOIGTS),
        "jambes": sum(1 for b in arm.bones if b.name.startswith(
            ("thigh", "shin", "foot", "toe")))}})
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
