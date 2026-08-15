"""
RIG DE MAIN PROFESSIONNEL — exécution stricte du tutoriel de Sacha.

Sacha m'a arrêté au milieu d'une boucle de recherche de pose et m'a donné ce
tutoriel. Sa remarque décisive, photo annotée à l'appui : « les deux parties que
je t'encercle en rouge doivent pouvoir se rapprocher l'une de l'autre » — le
métacarpien du pouce et celui de l'auriculaire.

Mon ancien rig ne pouvait PAS le faire, et c'est la cause de tout ce qui a
échoué cette nuit : les métacarpiens pendaient rigidement du carpe. Une paume
qui ne se creuse jamais ne peut ni fermer un vrai poing, ni amener l'auriculaire
au pouce. Le tutoriel l'écrit noir sur blanc : « Les os métacarpiens sont
indispensables pour obtenir une paume qui se creuse naturellement. Ne construis
pas une main "plate" composée uniquement de trois os par doigt. »

Ce que ce script suit, phase par phase :
  A. audit du maillage, sauvegarde, duplication
  B. squelette de déformation DEF_ (métacarpiens compris)
  C. orientation des axes et TEST du Bone Roll
  D. séparation CTRL_ / MCH_ / DEF_, propriétés et drivers
  E. butées anatomiques et verrouillages
  F. skinning et règles de poids
  H. poses de validation et rendus

Rien n'est déclaré fini tant que les critères d'acceptation ne sont pas mesurés.
"""
import json
import math
import os
import sys

import bmesh
import bpy
import mathutils

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RACINE, "atelier"))
import humain                       # noqa: E402
import articulations as A           # noqa: E402
import mains                        # noqa: E402
import portillon                    # noqa: E402

portillon.exiger("humain-rig-main")

args = sys.argv[sys.argv.index("--") + 1:]
DOSSIER = args[0]
QUI = args[1] if len(args) > 1 else "homme"
COTE = args[2] if len(args) > 2 else "g"
MOIGNON = float(args[3]) / 1000.0 if len(args) > 3 else 0.110
SANS_RENDU = "mesure" in args
SIDE = ".L" if COTE == "g" else ".R"
os.makedirs(DOSSIER, exist_ok=True)

rapport = {"cote": "gauche" if COTE == "g" else "droite", "side": SIDE}


def dire(cle, valeur):
    rapport[cle] = valeur
    print("ATLAS_" + cle.upper() + " " + json.dumps(valeur, ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════════
#   PHASE A — AUDIT PRÉALABLE, SAUVEGARDE, DUPLICATION
# ═══════════════════════════════════════════════════════════════════
corps, z_oeil = humain.charger(QUI, RACINE)
co = [corps.matrix_world @ x.co for x in corps.data.vertices]
R = A.releve(corps)
poignet = R["bras_" + COTE]["poignet"]["centre"]
M = mains.releve(corps, poignet, R["main_idx_" + COTE], co)

garde = set(R["main_idx_" + COTE])
d_poignet = R["bras_" + COTE]["poignet"]["distance"]
epaule = max((co[i] for i in R["bras_idx_" + COTE]), key=lambda p: p.z)
for i in R["bras_idx_" + COTE]:
    if (co[i] - epaule).length > d_poignet - MOIGNON:
        garde.add(i)

geo = corps.copy()
geo.data = corps.data.copy()
geo.name = f"GEO_Hand{SIDE}"
bpy.context.collection.objects.link(geo)
bm = bmesh.new(); bm.from_mesh(geo.data); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in garde],
                 context="VERTS")
bm.to_mesh(geo.data); bm.free()
bpy.data.objects.remove(corps, do_unlink=True)

# ── A.1 · LA SAUVEGARDE, AVANT TOUTE CHOSE ──
# Règle 4 du tutoriel : dupliquer la main et ranger la copie dans une collection
# masquée. Règle 5 : ne jamais s'en servir pour le rig. Elle n'existe que pour
# qu'un travail de plusieurs heures ne se perde pas sur une fausse manœuvre.
col_backup = bpy.data.collections.new("BACKUP_Hand_Before_Rig")
bpy.context.scene.collection.children.link(col_backup)
sauve = geo.copy()
sauve.data = geo.data.copy()
sauve.name = f"GEO_Hand_BACKUP{SIDE}"
col_backup.objects.link(sauve)
col_backup.hide_viewport = col_backup.hide_render = True

# ── A.2 · ÉCHELLE, ROTATION, NORMALES, DOUBLONS ──
bpy.ops.object.select_all(action="DESELECT")
geo.select_set(True)
bpy.context.view_layer.objects.active = geo
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

_av = len(geo.data.vertices)
bm = bmesh.new(); bm.from_mesh(geo.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
_nm = [e for e in bm.edges if not e.is_manifold]
_nm_n = len(_nm)
bm.to_mesh(geo.data); bm.free()
geo.data.update()

dire("audit_maillage", {
    "objet": geo.name, "sauvegarde": sauve.name,
    "echelle": [round(x, 4) for x in geo.scale],
    "rotation_deg": [round(math.degrees(x), 4) for x in geo.rotation_euler],
    "sommets_avant": _av, "sommets_apres": len(geo.data.vertices),
    "doublons_soudes": _av - len(geo.data.vertices),
    # Les arêtes de bord du moignon d'avant-bras sont non-manifold par
    # construction : la main est une surface COUPÉE, pas un volume fermé. On les
    # compte pour ne pas confondre ce bord légitime avec un défaut.
    "aretes_non_manifold": _nm_n,
    "note_non_manifold": "le bord de coupe du moignon en fait partie"})

pts = [geo.matrix_world @ v.co for v in geo.data.vertices]

# ── A.3 · AUDIT DE LA TOPOLOGIE DES ARTICULATIONS ──
# Le tutoriel interdit de poursuivre si une articulation n'a qu'une seule
# boucle transversale. On COMPTE donc les boucles réellement présentes autour
# de chaque pli, au lieu de supposer que le maillage est assez dense.
doigts_tri = sorted(M["doigts"], key=lambda d: (d["pointe"] - poignet).dot(M["travers"]))
_pouce_d = [d for d in doigts_tri if d.get("pouce")][0]
_quatre = [d for d in doigts_tri if not d.get("pouce")]
# Du pouce vers l'auriculaire : l'ordre est établi par la projection sur le
# travers de la paume, dont le sens est donné par la position du pouce.
_sens_t = 1.0 if (_pouce_d["pointe"] - poignet).dot(M["travers"]) > 0 else -1.0
_quatre.sort(key=lambda d: -_sens_t * (d["pointe"] - poignet).dot(M["travers"]))
NOMS4 = ["index", "middle", "ring", "pinky"]
ANATOMIE = {"index": _quatre[0], "middle": _quatre[1],
            "ring": _quatre[2], "pinky": _quatre[3], "thumb": _pouce_d}


def _boucles_autour(centre, axe, rayon=0.008, pas=0.0012):
    """Combien de tranches distinctes de sommets autour d'une articulation."""
    u = axe.normalized()
    tranches = set()
    for q in pts:
        v = q - centre
        d = v.dot(u)
        if abs(d) <= rayon and (v - u * d).length <= rayon * 2.2:
            tranches.add(round(d / pas))
    return len(tranches)


audit_art = {}
for nom, d in ANATOMIE.items():
    arts = [("MCP", d["jointure"])]
    if nom == "thumb":
        arts.append(("IP", d["articulations"][0][1]))
    else:
        arts += [("PIP", d["articulations"][0][1]),
                 ("DIP", d["articulations"][1][1])]
    axe = (d["pointe"] - d["jointure"]).normalized()
    for lbl, p in arts:
        audit_art[f"{nom}_{lbl}"] = _boucles_autour(p, axe)
_pauvres = {k: v for k, v in audit_art.items() if v < 3}
dire("audit_articulations", {"boucles_par_articulation": audit_art,
                             "sous_le_minimum_de_3": _pauvres})
if _pauvres:
    raise RuntimeError(
        "PHASE A ÉCHOUE — le tutoriel interdit de poursuivre avec une "
        f"articulation à moins de 3 boucles : {_pauvres}")

# ═══════════════════════════════════════════════════════════════════
#   PHASE B — SQUELETTE DE DÉFORMATION
# ═══════════════════════════════════════════════════════════════════
# ═══ LE PLAN DE LA PAUME SE CONSTRUIT, IL NE SE SUPPOSE PAS ═══
#
# J'employais `normale_paume` et `travers`, rendus par une analyse en
# composantes principales. Mesuré sur les os construits : `z_axis · N = 0,263`
# là où `align_roll(N)` aurait dû donner 1, et surtout **N n'est pas
# perpendiculaire aux doigts** — N·Y = −0,56, T·Y = −0,82. Ces repères ne
# décrivent donc pas le plan de la main, et tout roll fondé sur eux est faux.
#
# On construit le plan sur des POINTS RELEVÉS : le poignet, la jointure de
# l'index, celle de l'auriculaire. Sa normale est perpendiculaire aux doigts
# par construction, ce que la PCA ne garantissait pas.
_j_index = _quatre[0]["jointure"]
_j_pinky = _quatre[3]["jointure"]
N = ((_j_index - poignet).cross(_j_pinky - poignet)).normalized()
AXE = M["axe"].normalized()
# Le travers découle du plan, il n'est plus lu ailleurs.
T = N.cross(AXE).normalized()
_ctrl_perp = {
    "normale_contre_axe_de_la_main": round(N.dot(AXE), 3),
    "travers_contre_axe": round(T.dot(AXE), 3),
    "normale_contre_travers": round(N.dot(T), 3)}
print("ATLAS_PLAN_DE_PAUME " + json.dumps(_ctrl_perp, ensure_ascii=False))
if max(abs(v) for v in _ctrl_perp.values()) > 0.25:
    raise RuntimeError(f"le plan de la paume n'est pas orthogonal : {_ctrl_perp}")

arm = bpy.data.armatures.new(f"ARM_Hand{SIDE}")
rig = bpy.data.objects.new(f"RIG_Hand{SIDE}", arm)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
arm.show_axes = True
try:
    arm.show_in_front = True
except AttributeError:
    rig.show_in_front = True

# Trois collections d'os, comme l'exige le tutoriel (4.1).
for _c in ("CONTROLS", "MECHANISMS", "DEFORM"):
    try:
        arm.collections.new(_c)
    except AttributeError:
        pass

bpy.ops.object.mode_set(mode="EDIT")
EB = arm.edit_bones

# ── B.1 · L'OS DE LA MAIN ──
# Du poignet vers le centre de la paume. Le centre de la paume se mesure : c'est
# là où la main commence à s'évaser, donc où les métacarpiens s'écartent.
_ptsax = {}
for q in pts:
    _ptsax.setdefault(int((q - poignet).dot(AXE) / 0.004), []).append(q)
_serie = []
for kk in sorted(_ptsax):
    g = _ptsax[kk]
    if len(g) < 10 or not (0.0 <= kk * 0.004 <= 0.070):
        continue
    c = sum(g, mathutils.Vector((0, 0, 0))) / len(g)
    _serie.append((kk * 0.004, sum((x - c).length for x in g) / len(g)))
_acc = [(_serie[i + 1][1] - 2 * _serie[i][1] + _serie[i - 1][1], _serie[i][0])
        for i in range(1, len(_serie) - 1)]
L_PAUME = max(_acc)[1]
BASE_PAUME = poignet + AXE * L_PAUME

b_hand = EB.new(f"DEF_hand{SIDE}")
b_hand.head = poignet
b_hand.tail = BASE_PAUME
b_hand.align_roll(N)

# ── B.2 · LES CINQ MÉTACARPIENS, ET C'EST LÀ QUE TOUT SE JOUE ──
# Chacun part de la base de la paume et rejoint la jointure de son doigt. Ils
# sont enfants de DEF_hand SANS être connectés (Keep Offset) : c'est ce qui leur
# permet de bouger indépendamment, donc à la paume de se creuser, donc à
# l'auriculaire de rejoindre le pouce.
#
# Le pouce fait exception : sa trapézo-métacarpienne s'articule beaucoup plus
# bas sur la main. Sa racine mesurée est projetée sur l'axe de la paume.
DEF, ROLL_CIBLE = {}, {}
for nom in NOMS4 + ["thumb"]:
    d = ANATOMIE[nom]
    if nom == "thumb":
        u = (d["racine"] - poignet).dot(AXE)
        depart = poignet + AXE * max(0.0, min(L_PAUME, u))
        segs = [("meta", depart, d["jointure"]),
                ("01", d["jointure"], d["articulations"][0][1]),
                ("02", d["articulations"][0][1], d["pointe"])]
    else:
        depart = BASE_PAUME
        pip, dip = d["articulations"][0][1], d["articulations"][1][1]
        segs = [("meta", depart, d["jointure"]),
                ("01", d["jointure"], pip),
                ("02", pip, dip),
                ("03", dip, d["pointe"])]
    parent, noms = b_hand, []
    for suf, tete, queue in segs:
        b = EB.new(f"DEF_{nom}_{suf}{SIDE}")
        b.head, b.tail = tete, queue
        # ── LE ROLL, MESURÉ OS PAR OS ──
        # `align_roll(v)` oriente le Z de l'os aussi près que possible de `v`
        # TOUT EN RESTANT perpendiculaire à l'os. Passer un vecteur qui n'est
        # pas perpendiculaire à l'os ne donne donc pas ce qu'on croit : c'est
        # ce qui m'a valu un z_axis à 0,263 de la normale.
        #
        # Pour les quatre doigts, la normale du plan de paume convient : elle
        # leur est perpendiculaire par construction, et fléchir autour de X les
        # referme vers la paume.
        #
        # Le pouce est oblique — le tutoriel interdit de lui copier les axes des
        # autres. Son plan de flexion est celui qui l'amène vers l'index : on
        # aligne donc son Z sur la direction de sa jointure vers celle de
        # l'index, débarrassée de sa composante le long de l'os.
        if nom == "thumb":
            _u = (queue - tete).normalized()
            _v = ANATOMIE["index"]["jointure"] - tete
            _v = _v - _u * _v.dot(_u)
            _cible = _v.normalized() if _v.length > 1e-6 else N
        else:
            _cible = N
        b.align_roll(_cible)
        if suf == "01":
            # Le PLAN DE FLEXION du doigt, retenu pour le test du Bone Roll :
            # il est porté par l'os et par sa cible de roll. Sa normale est donc
            # la direction où un doigt sain ne va PAS.
            ROLL_CIBLE[nom] = ((queue - tete).normalized().cross(_cible)).normalized()
        b.parent = parent
        b.use_connect = (suf != "meta")    # Keep Offset pour les métacarpiens
        b.use_deform = True
        parent = b
        noms.append(b.name)
    DEF[nom] = noms

bpy.ops.object.mode_set(mode="OBJECT")
dire("squelette_deformation", {
    "os_de_la_main": b_hand.name,
    "longueur_paume_mm": round(L_PAUME * 1000, 1),
    "chaines": DEF,
    "nombre_os_def": sum(len(v) for v in DEF.values()) + 1})

bpy.ops.object.mode_set(mode="OBJECT")
print("ATLAS_PHASE_B terminée")


# ═══════════════════════════════════════════════════════════════════
#   PHASE C — ORIENTATION DES AXES ET TEST DU BONE ROLL
# ═══════════════════════════════════════════════════════════════════
# Le tutoriel est catégorique : « Ne crée aucun driver avant la réussite
# complète de ce test. » On pivote chaque phalange de +30° et on vérifie que
# TOUS les doigts se ferment vers la paume, sans vrille.
#
# Encore faut-il savoir de quel côté est la paume. Je ne le suppose pas : la
# normale rendue par une analyse en composantes principales a un signe
# ARBITRAIRE — c'est très exactement la faute qui m'avait fait poser les ongles
# du mauvais côté. On l'établit par le mouvement : fléchir vers la paume ramène
# le bout du doigt AU-DESSUS de la main, fléchir vers le dos l'en éloigne.

def sommets_evalues():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw, m3 = geo.matrix_world, geo.matrix_world.to_3x3()
    p = [mw @ v.co.copy() for v in m.vertices]
    n = [(m3 @ v.normal).normalized() for v in m.vertices]
    ev.to_mesh_clear()
    return p, n


def au_repos():
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def poser_os(angles):
    """angles : {nom_os: (x, y, z) en degrés}."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    for nom, a in angles.items():
        if nom in rig.pose.bones:
            rig.pose.bones[nom].rotation_euler = tuple(math.radians(x) for x in a)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


# Le maillage doit suivre l'armature pour que ce test veuille dire quelque
# chose : on lie provisoirement avec des poids automatiques.
bpy.ops.object.select_all(action="DESELECT")
geo.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")

_ng = {g.index: g.name for g in geo.vertex_groups}
_dom = {}
for v in geo.data.vertices:
    if v.groups:
        _dom[v.index] = _ng.get(max(v.groups, key=lambda g: g.weight).group, "")


def bouts_de(nom):
    return [i for i, n in _dom.items()
            if n == DEF[nom][-1]]


au_repos()
_p0, _n0 = sommets_evalues()
CENTRE_PAUME = sum((_p0[i] for i in range(len(_p0))
                    if _dom.get(i, "").endswith(f"_meta{SIDE}")),
                   mathutils.Vector((0, 0, 0)))
_nmeta = sum(1 for i in range(len(_p0)) if _dom.get(i, "").endswith(f"_meta{SIDE}"))
CENTRE_PAUME = CENTRE_PAUME / max(1, _nmeta)

# ── C.1 · DE QUEL CÔTÉ SE FERME UN DOIGT ? ──
_essai = {}
for _s in (+30.0, -30.0):
    poser_os({b: (_s, 0.0, 0.0) for nom in NOMS4 for b in DEF[nom][1:]})
    _p, _ = sommets_evalues()
    _d = 0.0
    for nom in NOMS4:
        bts = bouts_de(nom)
        c = sum((_p[i] for i in bts), mathutils.Vector((0, 0, 0))) / len(bts)
        _d += (c - CENTRE_PAUME).length
    _essai[_s] = _d / 4.0
SENS_FLEXION = min(_essai, key=_essai.get)
au_repos()
dire("sens_de_flexion", {
    "distance_moyenne_bout_paume_a_+30_mm": round(_essai[+30.0] * 1000, 1),
    "distance_moyenne_bout_paume_a_-30_mm": round(_essai[-30.0] * 1000, 1),
    "sens_retenu": SENS_FLEXION,
    "regle": "fléchir vers la paume rapproche le bout du centre de la paume"})

# ── C.2 · LE TEST DU BONE ROLL, DOIGT PAR DOIGT ──
# Deux exigences : le bout doit se rapprocher de la paume (il se ferme du bon
# côté), et il ne doit pas VRILLER — le déplacement doit rester dans le plan de
# flexion du doigt, donc sa composante latérale doit rester petite.
_test_roll, _fautes, _signes = {}, [], []
for nom in NOMS4 + ["thumb"]:
    au_repos()
    _p, _ = sommets_evalues()
    bts = bouts_de(nom)
    c0 = sum((_p[i] for i in bts), mathutils.Vector((0, 0, 0))) / len(bts)
    poser_os({b: (SENS_FLEXION, 0.0, 0.0) for b in DEF[nom][1:]})
    _p, _ = sommets_evalues()
    c1 = sum((_p[i] for i in bts), mathutils.Vector((0, 0, 0))) / len(bts)
    rapproche = ((c0 - CENTRE_PAUME).length - (c1 - CENTRE_PAUME).length) * 1000
    course = (c1 - c0)
    # ═══ LA VRILLE SE MESURE CONTRE L'AXE DE ROTATION, PAS CONTRE LA PAUME ═══
    # Premier jet : je la mesurais contre le travers de la paume. Le pouce
    # rendait 0,99 et le test le condamnait — alors que le tutoriel dit
    # lui-même que « ses axes sont obliques ». C'était mon critère qui était
    # faux : le pouce se déplace légitimement dans un AUTRE plan.
    #
    # La définition juste est générale et vaut pour les cinq doigts : une
    # rotation pure autour de l'axe local X ne produit aucun déplacement LE
    # LONG de cet axe. Toute composante qui s'y trouve est une vrille.
    # ═══ UNE SONDE QUI NE PEUT PAS ÉCHOUER NE PROUVE RIEN ═══
    #
    # Troisième formulation, et les deux premières étaient fausses pour la même
    # raison : je raisonnais sur une convention d'axes au lieu de la mesurer.
    # La troisième était pire — elle rendait 0,000 sur les cinq doigts, un
    # résultat parfait qui aurait dû me réjouir. Vérifié : mon axe valait
    # `os × cible_de_roll`, et c'est exactement autour de celui-là
    # qu'`align_roll` fait tourner. Le produit était nul PAR CONSTRUCTION, quel
    # que soit le roll. Une tautologie déguisée en validation.
    #
    # Le vrai risque d'un roll fautif, c'est que les doigts ne plient pas dans
    # le MÊME plan : l'un vers la paume, l'autre de côté. On mesure donc ce qui
    # peut vraiment échouer — l'axe de flexion de chaque doigt doit être
    # parallèle au travers de la paume, et tous de même sens.
    _x = ROLL_CIBLE[nom]
    # (La sonde qui affichait les axes a fait son travail : c'est elle qui a
    # montré que `align_roll` mettait la normale sur X et non sur Z, et donc que
    # mes deux premiers critères de vrille lisaient la mauvaise grandeur.)
    lateral = abs(course.dot(_x)) / max(1e-9, course.length)
    _align = _x.dot(T)          # +1 ou −1 si l'axe de flexion suit le travers
    _test_roll[nom] = {"rapprochement_mm": round(rapproche, 1),
                       "axe_de_flexion_contre_travers": round(_align, 3),
                       "course_mm": round(course.length * 1000, 1)}
    if rapproche <= 0:
        _fautes.append(f"{nom} : ne se ferme pas vers la paume")
    # Le pouce est OBLIQUE par nature — le tutoriel interdit de lui copier les
    # axes des autres. On ne lui demande donc pas d'être parallèle au travers ;
    # on lui demande le contraire, sans quoi il plierait comme un doigt ordinaire
    # (défaut listé en toutes lettres dans les problèmes interdits).
    if nom == "thumb":
        if abs(_align) > 0.80:
            _fautes.append(f"{nom} : plie comme un doigt ordinaire "
                           f"({_align:+.2f} d'alignement sur le travers)")
    elif abs(_align) < 0.80:
        _fautes.append(f"{nom} : son axe de flexion sort du plan de la paume "
                       f"({_align:+.2f})")
    else:
        _signes.append((nom, 1 if _align > 0 else -1))
au_repos()
# Les quatre doigts doivent plier dans le même sens : c'est ce qu'un roll
# retourné casse en premier, et ce que le tutoriel décrit par « un seul doigt
# part à l'envers ».
if len({v for _n, v in _signes}) > 1:
    _fautes.append(f"les doigts ne plient pas tous dans le même sens : {_signes}")
dire("test_bone_roll", {"par_doigt": _test_roll,
                        "sens_des_quatre_doigts": _signes, "fautes": _fautes})
if _fautes:
    raise RuntimeError("PHASE C ÉCHOUE — le tutoriel interdit de créer le "
                       f"moindre driver avant que ce test passe : {_fautes}")
print("ATLAS_PHASE_C réussie")


# ═══════════════════════════════════════════════════════════════════
#   PHASE D — CTRL_ / MCH_ / DEF_, PROPRIÉTÉS ET DRIVERS
# ═══════════════════════════════════════════════════════════════════
# Le sens de flexion est MESURÉ (phase C) : SENS_FLEXION vaut −30, donc fermer
# se fait vers les X négatifs. Le tutoriel prévient : « Si l'axe de flexion
# choisi est négatif, applique le même signe négatif à toute la famille d'os. »
SIGNE = -1.0 if SENS_FLEXION < 0 else 1.0

# Quel euler fait quoi, ÉTABLI et non supposé : la phase C a montré que
# `rotation_euler.x` tourne autour de l'axe de flexion (≈ le travers de la
# paume). Le repère de l'os étant orthonormé avec Y le long de l'os, le
# troisième axe — `rotation_euler.z` — tourne donc autour de la normale de la
# paume : c'est lui qui écarte les doigts.
AXE_FLEXION, AXE_ECART = 0, 2

bpy.ops.object.mode_set(mode="EDIT")
EB = arm.edit_bones
_rest = {b.name: (b.head.copy(), b.tail.copy(), b.roll) for b in EB}

b_world = EB.new(f"CTRL_world{SIDE}")
b_world.head = poignet - AXE * 0.020
b_world.tail = poignet
b_world.align_roll(N)
b_ctrl_hand = EB.new(f"CTRL_hand{SIDE}")
b_ctrl_hand.head, b_ctrl_hand.tail = _rest[f"DEF_hand{SIDE}"][0], _rest[f"DEF_hand{SIDE}"][1]
b_ctrl_hand.roll = _rest[f"DEF_hand{SIDE}"][2]
b_ctrl_hand.parent = b_world
EB[f"DEF_hand{SIDE}"].parent = b_world
EB[f"DEF_hand{SIDE}"].use_connect = False

# Les couches CTRL_ et MCH_ reproduisent EXACTEMENT les poses de repos de la
# couche DEF_ : c'est la condition pour que « Fist = 0 » redonne la pose neutre.
CTRL, MCH = {}, {}
for nom in NOMS4 + ["thumb"]:
    CTRL[nom], MCH[nom] = [], []
    parent_c = b_ctrl_hand
    for k, dnom in enumerate(DEF[nom]):
        suf = dnom.split("_")[2].replace(SIDE, "")
        h, t, r = _rest[dnom]
        c = EB.new(f"CTRL_{nom}_{suf}{SIDE}")
        c.head, c.tail, c.roll = h, t, r
        c.use_deform = False
        m = EB.new(f"MCH_{nom}_{suf}_result{SIDE}")
        m.head, m.tail, m.roll = h, t, r
        m.use_deform = False
        # 6.2 du tutoriel : CTRL et MCH du premier segment pendent de CTRL_hand ;
        # ceux des segments suivants pendent du MCH_result précédent. C'est ce
        # qui fait qu'un contrôleur enfant suit réellement l'automatisation.
        c.parent = parent_c
        m.parent = parent_c
        c.use_connect = m.use_connect = False
        parent_c = m
        CTRL[nom].append(c.name)
        MCH[nom].append(m.name)

bpy.ops.object.mode_set(mode="OBJECT")

# ── D.1 · RANGER LES OS DANS LEURS COLLECTIONS ──
try:
    _cols = {c.name: c for c in arm.collections}
    for b in arm.bones:
        cible = ("CONTROLS" if b.name.startswith("CTRL_")
                 else "MECHANISMS" if b.name.startswith("MCH_") else "DEFORM")
        if cible in _cols:
            _cols[cible].assign(rig.pose.bones[b.name].bone)
except Exception as _e:
    print("ATLAS_COLLECTIONS_OS non assignées :", _e)

# ── D.2 · LES CONTRAINTES ──
def contrainte(os_, type_, cible, **kw):
    c = rig.pose.bones[os_].constraints.new(type_)
    c.target = rig
    c.subtarget = cible
    for k, v in kw.items():
        setattr(c, k, v)
    return c


contrainte(f"DEF_hand{SIDE}", "COPY_TRANSFORMS", f"CTRL_hand{SIDE}",
           target_space="LOCAL", owner_space="LOCAL")
_mix_add = None
for nom in NOMS4 + ["thumb"]:
    for dnom, cnom, mnom in zip(DEF[nom], CTRL[nom], MCH[nom]):
        # Le MCH porte l'automatisation (drivers) et lui AJOUTE la rotation
        # manuelle du contrôleur. C'est cette addition qui permet à l'animateur
        # de corriger une pose automatique sans la détruire.
        c = contrainte(mnom, "COPY_ROTATION", cnom,
                       target_space="LOCAL", owner_space="LOCAL")
        if _mix_add is None:
            _mix_add = ("ADD" if "ADD" in
                        {i.identifier for i in c.bl_rna.properties["mix_mode"].enum_items}
                        else "AFTER")
        c.mix_mode = _mix_add
        # Le DEF ne fait que reproduire le résultat, sans double transformation.
        contrainte(dnom, "COPY_ROTATION", mnom,
                   target_space="LOCAL", owner_space="LOCAL", mix_mode="REPLACE")

# ── D.3 · LES PROPRIÉTÉS DE LA MAIN ──
pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]
PROPS = [("Fist", 0.0, 0.0, 1.0), ("Index_Curl", 0.0, 0.0, 1.0),
         ("Middle_Curl", 0.0, 0.0, 1.0), ("Ring_Curl", 0.0, 0.0, 1.0),
         ("Pinky_Curl", 0.0, 0.0, 1.0), ("Thumb_Curl", 0.0, 0.0, 1.0),
         ("Thumb_Opposition", 0.0, 0.0, 1.0), ("Spread", 0.0, -1.0, 1.0),
         ("Cup", 0.0, 0.0, 1.0), ("Relax", 0.0, 0.0, 1.0)]
for nomp, defaut, mini, maxi in PROPS:
    pbh[nomp] = defaut
    try:
        pbh.id_properties_ui(nomp).update(min=mini, max=maxi,
                                          soft_min=mini, soft_max=maxi)
    except AttributeError:
        pbh["_RNA_UI"] = pbh.get("_RNA_UI", {})
        pbh["_RNA_UI"][nomp] = {"min": mini, "max": maxi}


# ═══ POURQUOI LES EXPRESSIONS NE CONTIENNENT NI min NI max ═══
#
# Premier jet : `min(max(fist + curl, 0.0), 1.0) * k`. Résultat mesuré :
# `Fist = 1` ne déplaçait AUCUN sommet — course du poing 0,0 mm. Le rig était
# inerte, et mon contrôle « retour au repos exact » passait pour la pire des
# raisons : une main qui ne bouge pas revient toujours exactement à sa place.
#
# La cause : `--factory-startup` désactive l'exécution automatique des scripts,
# et `min`/`max` réclament l'évaluateur Python de Blender. L'évaluateur simple,
# lui, ne fait que de l'arithmétique — les drivers échouaient en silence.
#
# On n'a de toute façon pas besoin de borner ici : les contraintes Limit
# Rotation de la phase E s'en chargent, et le tutoriel les prévoit très
# exactement pour ça (« Place également une limite finale sur les mécanismes de
# résultat afin que l'addition contrôle manuel + automatisation ne dépasse
# jamais l'amplitude anatomique »).
try:
    bpy.context.preferences.filepaths.use_scripts_auto_execute = True
except Exception:
    pass


def driver(os_, indice, expr, vars_):
    pb = rig.pose.bones[os_]
    pb.rotation_mode = "XYZ"
    fc = pb.driver_add("rotation_euler", indice)
    d = fc.driver
    d.type = "SCRIPTED"
    for vn, prop in vars_.items():
        v = d.variables.new()
        v.name = vn
        v.type = "SINGLE_PROP"
        v.targets[0].id = rig
        v.targets[0].data_path = f'pose.bones["CTRL_hand{SIDE}"]["{prop}"]'
    d.expression = expr
    return fc


# Amplitudes de départ du tutoriel (6.4), en degrés.
MAXI = {"01": 85.0, "02": 105.0, "03": 75.0}
MAXI_POUCE = {"01": 55.0, "02": 75.0}
CURL = {"index": "Index_Curl", "middle": "Middle_Curl",
        "ring": "Ring_Curl", "pinky": "Pinky_Curl"}
# « Ne rends pas les quatre doigts parfaitement identiques » : le majeur part
# légèrement avant, l'annulaire et l'auriculaire se courbent davantage au repos.
AVANCE = {"index": 1.00, "middle": 1.06, "ring": 1.02, "pinky": 0.96}
RELAX = {"index": 0.18, "middle": 0.24, "ring": 0.30, "pinky": 0.36}

for nom in NOMS4:
    for suf, mx in MAXI.items():
        mnom = f"MCH_{nom}_{suf}_result{SIDE}"
        k = SIGNE * math.radians(mx) * AVANCE[nom]
        kr = SIGNE * math.radians(mx) * RELAX[nom] * (0.7 if suf == "03" else 1.0)
        driver(mnom, AXE_FLEXION,
               f"(fist + curl) * {k:.6f} + relax * {kr:.6f}",
               {"fist": "Fist", "curl": CURL[nom], "relax": "Relax"})
# L'écartement agit sur la première phalange, autour de la normale de la paume.
ECART = {"index": 10.0, "middle": 1.0, "ring": -6.0, "pinky": -12.0}
for nom in NOMS4:
    driver(f"MCH_{nom}_01_result{SIDE}", AXE_ECART,
           f"spread * {math.radians(ECART[nom]):.6f}", {"spread": "Spread"})
# Le creusement agit sur les MÉTACARPIENS, faiblement côté index, fortement côté
# auriculaire. C'est lui qui rapproche l'auriculaire du pouce — le cerclage
# rouge de Sacha.
CUP = {"index": 0.10, "middle": 0.25, "ring": 0.60, "pinky": 1.00}
CUP_MAX = 22.0
for nom in NOMS4:
    driver(f"MCH_{nom}_meta_result{SIDE}", AXE_FLEXION,
           f"cup * {SIGNE * math.radians(CUP_MAX) * CUP[nom]:.6f}", {"cup": "Cup"})
# Le pouce : flexion propre, et une opposition COMPOSÉE, comme l'exige le
# tutoriel — « Ne pilote pas l'opposition uniquement avec une rotation sur un
# seul axe. Le mouvement réel du pouce est oblique et composé. »
for suf, mx in MAXI_POUCE.items():
    driver(f"MCH_thumb_{suf}_result{SIDE}", AXE_FLEXION,
           f"(curl + fist * 0.85) * {SIGNE * math.radians(mx):.6f}",
           {"curl": "Thumb_Curl", "fist": "Fist"})
OPPO = {0: SIGNE * 40.0, 1: -55.0, 2: 22.0}     # paume · axiale · vers l'index
for ax, deg in OPPO.items():
    driver(f"MCH_thumb_meta_result{SIDE}", ax,
           f"opp * {math.radians(deg):.6f} + fist * {math.radians(deg) * 0.75:.6f}",
           {"opp": "Thumb_Opposition", "fist": "Fist"})

bpy.context.view_layer.update()
dire("phase_d", {
    "os_ctrl": sum(len(v) for v in CTRL.values()) + 2,
    "os_mch": sum(len(v) for v in MCH.values()),
    "os_def": sum(len(v) for v in DEF.values()) + 1,
    "proprietes": [p[0] for p in PROPS],
    "melange_des_rotations": _mix_add,
    "signe_de_flexion": SIGNE,
    "axe_flexion_euler": AXE_FLEXION, "axe_ecartement_euler": AXE_ECART})
print("ATLAS_PHASE_D terminée")


# ═══════════════════════════════════════════════════════════════════
#   PHASE E — BUTÉES ANATOMIQUES ET VERROUILLAGES
# ═══════════════════════════════════════════════════════════════════
# Valeurs de départ du tutoriel (7.2). Le signe des minima et maxima dépend du
# sens de flexion MESURÉ : appliquer ces nombres tels quels sans en tenir compte
# interdirait la flexion au lieu de la borner.
def borne(deg_ext, deg_flex):
    a, b = SIGNE * math.radians(deg_flex), SIGNE * math.radians(-deg_ext)
    return (min(a, b), max(a, b))


LIM = {"01": borne(20.0, 90.0), "02": borne(0.0, 110.0), "03": borne(10.0, 80.0)}
LIM_POUCE = {"01": borne(0.0, 60.0), "02": borne(0.0, 80.0)}
ECART_MAX = math.radians(15.0)

_poses_limitees = 0
for nom in NOMS4 + ["thumb"]:
    for dnom, cnom, mnom in zip(DEF[nom], CTRL[nom], MCH[nom]):
        suf = dnom.split("_")[2].replace(SIDE, "")
        if suf == "meta":
            continue
        lo, hi = (LIM_POUCE if nom == "thumb" else LIM)[suf]
        # La butée se pose sur le CONTRÔLEUR *et* sur le résultat : sans la
        # seconde, l'addition « automatisme + main de l'animateur » pourrait
        # dépasser l'amplitude anatomique. Le tutoriel l'exige explicitement.
        for cible in (cnom, mnom):
            c = rig.pose.bones[cible].constraints.new("LIMIT_ROTATION")
            c.owner_space = "LOCAL"
            c.use_limit_x = c.use_limit_y = c.use_limit_z = True
            c.min_x, c.max_x = lo, hi
            c.min_y = c.max_y = 0.0          # aucune vrille sur une phalange
            # PIP et DIP sont des CHARNIÈRES : pas d'écartement. Seule la
            # métacarpo-phalangienne en autorise un, et modéré.
            e = ECART_MAX if suf == "01" else 0.0
            c.min_z, c.max_z = -e, e
            _poses_limitees += 1
        # Verrouillages d'ergonomie : un contrôleur de phalange ne se déplace
        # ni ne se redimensionne — c'est listé dans les défauts interdits.
        pb = rig.pose.bones[cnom]
        pb.lock_location = (True, True, True)
        pb.lock_scale = (True, True, True)
        pb.lock_rotation = (False, True, suf != "01")

dire("phase_e", {"contraintes_de_butee": _poses_limitees,
                 "mcp_deg": [round(math.degrees(x), 1) for x in LIM["01"]],
                 "pip_deg": [round(math.degrees(x), 1) for x in LIM["02"]],
                 "dip_deg": [round(math.degrees(x), 1) for x in LIM["03"]],
                 "pouce_mcp_deg": [round(math.degrees(x), 1) for x in LIM_POUCE["01"]],
                 "pouce_ip_deg": [round(math.degrees(x), 1) for x in LIM_POUCE["02"]],
                 "ecartement_max_deg": 15.0})


# ═══════════════════════════════════════════════════════════════════
#   PHASE F — SKINNING ET RÈGLES DE POIDS
# ═══════════════════════════════════════════════════════════════════
# Le tutoriel : « Ne considère jamais les poids automatiques comme un résultat
# final. » On les nettoie, on les normalise, et surtout on VÉRIFIE la règle qui
# ne se voit pas à l'œil : aucun sommet d'un doigt ne doit recevoir de poids
# venant d'un autre doigt.
bpy.ops.object.select_all(action="DESELECT")
geo.select_set(True)
bpy.context.view_layer.objects.active = geo
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.005)
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

_gnom = {g.index: g.name for g in geo.vertex_groups}


def famille(n):
    for f in NOMS4 + ["thumb"]:
        if n.startswith(f"DEF_{f}_"):
            return f
    return "hand"


_contamine, _somme_fausse, _melange_paume = 0, 0, 0
_dom = {}
for v in geo.data.vertices:
    gs = [(g.weight, _gnom.get(g.group, "")) for g in v.groups if g.weight > 0.01]
    if not gs:
        continue
    _dom[v.index] = max(gs)[1]
    # ═══ DISTINGUER LA PAUME DES DOIGTS ═══
    # Premier compte : 12 521 sommets « contaminés ». Mais je comptais aussi le
    # mélange entre MÉTACARPIENS voisins, et le tutoriel le demande exprès
    # (règle 7 : « La base de chaque doigt doit mélanger progressivement
    # DEF_hand, le métacarpien correspondant et la première phalange »). La
    # paume est une chair continue ; c'est entre PHALANGES que le mélange est
    # interdit, parce que deux doigts qui s'entraînent l'un l'autre est un
    # défaut visible.
    fams_ph = {famille(n) for _w, n in gs
               if not n.endswith(f"_meta{SIDE}")} - {"hand"}
    if len(fams_ph) > 1:
        _contamine += 1
    if len({famille(n) for _w, n in gs} - {"hand"}) > 1:
        _melange_paume += 1
    if abs(sum(g.weight for g in v.groups) - 1.0) > 0.02:
        _somme_fausse += 1

# L'INVARIANT : la chair de chaque doigt doit rester d'un seul tenant. C'est lui
# qui avait attrapé, cette nuit, une fragmentation du pouce que trois mesures de
# pose n'auraient jamais montrée — et que Sacha, lui, avait vue à l'œil.
_aretes = {}
for e in geo.data.edges:
    _aretes.setdefault(e.vertices[0], []).append(e.vertices[1])
    _aretes.setdefault(e.vertices[1], []).append(e.vertices[0])


def morceaux(idx):
    reste, n, plus_gros = set(idx), 0, 0
    while reste:
        d = reste.pop(); pile, taille = [d], 1
        while pile:
            x = pile.pop()
            for y in _aretes.get(x, ()):
                if y in reste:
                    reste.discard(y); pile.append(y); taille += 1
        n += 1; plus_gros = max(plus_gros, taille)
    return n, plus_gros


_entiers = {}
for f in NOMS4 + ["thumb"]:
    idx = [i for i, n in _dom.items() if famille(n) == f]
    _entiers[f] = morceaux(idx) if idx else (0, 0)

dire("phase_f", {
    "sommets_contamines_entre_phalanges": _contamine,
    "sommets_melangeant_deux_metacarpiens": _melange_paume,
    "note_paume": "le mélange entre métacarpiens voisins est demandé par la "
                  "règle 7 du tutoriel : la paume est une chair continue",
    "sommets_dont_la_somme_des_poids_n_est_pas_1": _somme_fausse,
    "morceaux_par_doigt": {k: {"morceaux": v[0], "plus_gros": v[1]}
                           for k, v in _entiers.items()},
    "groupes": len(geo.vertex_groups)})
_defauts_f = []
if _contamine:
    _defauts_f.append(
        f"{_contamine} sommets d'un doigt sont tirés par les phalanges d'un autre")
for f, (n, _g) in _entiers.items():
    if n != 1:
        _defauts_f.append(f"la chair de {f} est en {n} morceaux")
if _defauts_f:
    print("ATLAS_PHASE_F_DEFAUTS " + json.dumps(_defauts_f, ensure_ascii=False))
print("ATLAS_PHASE_F terminée")


# ── F.2 · LA CONTAMINATION SE CORRIGE PAR UNE RÈGLE ──
# 3 642 sommets étaient tirés par les phalanges d'un autre doigt. Le tutoriel
# l'interdit (règle 6) et prévient que les poids automatiques ne sont qu'un
# point de départ. On ne retouche pas ces sommets un par un : on applique une
# règle qui vaut pour tout doigt — un sommet qui appartient à un doigt perd les
# poids venus des PHALANGES des autres, et on renormalise. La paume, elle,
# garde son mélange de métacarpiens, que la règle 7 demande.
# Une seule passe laissait 1 043 sommets contaminés : en retirant les intrus, le
# groupe dominant de certains sommets CHANGE, et de nouveaux intrus apparaissent.
# On répète donc jusqu'à ce que la règle n'ait plus rien à retirer.
COMMISSURES = [(ANATOMIE[NOMS4[_k]]["jointure"]
                + ANATOMIE[NOMS4[_k + 1]]["jointure"]) / 2.0 for _k in range(3)]
_gr = {g.name: g for g in geo.vertex_groups}
_corriges = 0
for _passe in range(6):
  _avant_passe = _corriges
  for v in geo.data.vertices:
      gs = [(g.weight, _gnom.get(g.group, "")) for g in v.groups if g.weight > 0.01]
      if not gs:
          continue
      dom = max(gs)[1]
      if dom.endswith(f"_meta{SIDE}") or dom == f"DEF_hand{SIDE}":
          # Sommet de paume. Le mélange y est légitime — mais SEULEMENT dans
          # les creux interdigitaux, que la règle 7 vise expressément. Mesuré :
          # sur 1 043 sommets à deux doigts, 655 sont dans ces creux et 388
          # sont ailleurs. Ces 388 ne relèvent d'aucune règle, et le critère
          # « aucun doigt ne déforme un autre doigt » les interdit.
          if min((pts[v.index] - _c).length for _c in COMMISSURES) < 0.022:
              continue
          _fams = [(w, n) for w, n in gs
                   if not n.endswith(f"_meta{SIDE}") and n != f"DEF_hand{SIDE}"]
          if len({famille(n) for _w, n in _fams}) > 1:
              _garde = famille(max(_fams)[1])
              for _w, n in _fams:
                  if famille(n) != _garde:
                      _gr[n].remove([v.index])
              _corriges += 1
          continue
      f_dom = famille(dom)
      intrus = [n for _w, n in gs
                if not n.endswith(f"_meta{SIDE}") and n != f"DEF_hand{SIDE}"
                and famille(n) not in (f_dom, "hand")]
      if not intrus:
          continue
      for n in intrus:
          _gr[n].remove([v.index])
      _corriges += 1
  if _corriges == _avant_passe:
      break
bpy.ops.object.select_all(action="DESELECT")
geo.select_set(True)
bpy.context.view_layer.objects.active = geo
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

_gnom = {g.index: g.name for g in geo.vertex_groups}
_reste, _dom = 0, {}
for v in geo.data.vertices:
    gs = [(g.weight, _gnom.get(g.group, "")) for g in v.groups if g.weight > 0.01]
    if not gs:
        continue
    _dom[v.index] = max(gs)[1]
    if len({famille(n) for _w, n in gs
            if not n.endswith(f"_meta{SIDE}")} - {"hand"}) > 1:
        _reste += 1
_ent2 = {f: morceaux([i for i, n in _dom.items() if famille(n) == f])
         for f in NOMS4 + ["thumb"]}
dire("phase_f_correction", {
    "sommets_corriges": _corriges,
    "contamination_restante": _reste,
    "chair_encore_d_un_seul_tenant": {k: v[0] for k, v in _ent2.items()}})


# ═══════════════════════════════════════════════════════════════════
#   PHASE H — POSES DE VALIDATION
# ═══════════════════════════════════════════════════════════════════
def regler(**kw):
    for k, v in kw.items():
        pbh[k] = float(v)
    for p, _d, _mi, _ma in PROPS:
        if p not in kw:
            pbh[p] = 0.0
    # ═══ POURQUOI UN frame_set ICI ═══
    # Les 25 drivers existaient, leurs expressions étaient bonnes, `is_valid`
    # rendait vrai — et la rotation du mécanisme restait à 0,0 jusque dans le
    # graphe évalué. Ils n'étaient donc pas fautifs : ils n'étaient pas
    # ÉVALUÉS. En mode fond, l'évaluation de l'animation ne se déclenche pas
    # tant que l'image ne change pas. Sans cette ligne, `Fist = 1` ne déplaçait
    # aucun sommet, et mon contrôle « retour au repos exact » passait pour la
    # pire des raisons : une main inerte revient toujours à sa place.
    rig.update_tag()
    rig.data.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


# ── H.1 · LE RETOUR EXACT À LA POSE DE REPOS ──
# Critère d'acceptation du tutoriel : « Fist = 0 ne revient pas exactement à la
# pose de repos » figure dans les défauts interdits. C'est LE contrôle du
# montage CTRL/MCH/DEF : au-dessus de quelques microns, il fabrique une double
# transformation et tout ce qui suit serait faux.
regler()
_repos, _ = sommets_evalues()
regler(Fist=1.0)
# On ne cherche pas un remède au hasard : on lit ce que vaut la chaîne à chaque
# maillon — la propriété, la rotation du mécanisme, celle de l'os déformant.
_dg = bpy.context.evaluated_depsgraph_get()
_rev = rig.evaluated_get(_dg)
print("ATLAS_SONDE_DRIVER " + json.dumps({
    "propriete_Fist": float(pbh["Fist"]),
    "mch_brut_deg": [round(math.degrees(x), 2)
                     for x in rig.pose.bones[f"MCH_index_01_result{SIDE}"].rotation_euler],
    "mch_evalue_deg": [round(math.degrees(x), 2)
                       for x in _rev.pose.bones[f"MCH_index_01_result{SIDE}"].rotation_euler],
    "mch_matrice_evaluee": [round(x, 3)
                            for x in _rev.pose.bones[f"MCH_index_01_result{SIDE}"].matrix_basis.to_euler()],
    "def_evalue_deg": [round(math.degrees(x), 2)
                       for x in _rev.pose.bones[f"DEF_index_01{SIDE}"].rotation_euler],
    "def_matrice_evaluee": [round(math.degrees(x), 2)
                            for x in _rev.pose.bones[f"DEF_index_01{SIDE}"].matrix_basis.to_euler()],
    "nb_drivers": len(rig.animation_data.drivers) if rig.animation_data else 0,
    "expression": (rig.animation_data.drivers[0].driver.expression
                   if rig.animation_data and len(rig.animation_data.drivers) else None),
    "driver_valide": (rig.animation_data.drivers[0].driver.is_valid
                      if rig.animation_data and len(rig.animation_data.drivers) else None),
}, ensure_ascii=False))
_ferme, _ = sommets_evalues()
regler()
_retour, _ = sommets_evalues()
_ecart_retour = max((a - b).length for a, b in zip(_repos, _retour)) * 1000
_course_poing = max((a - b).length for a, b in zip(_repos, _ferme)) * 1000
dire("retour_au_repos", {
    "ecart_max_mm": round(_ecart_retour, 6),
    "course_du_poing_mm": round(_course_poing, 1),
    "verdict": "exact" if _ecart_retour < 0.01 else "DOUBLE TRANSFORMATION"})
if _ecart_retour >= 0.01:
    raise RuntimeError(f"Fist=0 ne redonne pas la pose de repos : "
                       f"{_ecart_retour:.4f} mm d'écart")

# ── H.2 · LES EMPREINTES, ET LA POSE QUE SACHA DEMANDE ──
PALMAIRE = None


def empreinte(nom):
    """Les sommets de la face pulpaire de la dernière phalange d'un doigt."""
    dnom = DEF[nom][-1]
    ii = [i for i, n in _dom.items() if n == dnom]
    if not ii:
        return []
    b = rig.data.bones[dnom]
    axe = (rig.matrix_world @ b.tail_local - rig.matrix_world @ b.head_local).normalized()
    # La pulpe regarde du côté vers lequel le doigt se referme : c'est mesuré
    # par le mouvement, jamais supposé — le signe d'une normale de PCA est
    # arbitraire, et c'est ce qui m'avait fait poser les ongles du mauvais côté.
    ref = (CENTRE_PAUME - (rig.matrix_world @ b.head_local))
    ref = (ref - axe * ref.dot(axe))
    if ref.length < 1e-6:
        return []
    ref = ref.normalized()
    _p, _n = sommets_evalues()
    return [i for i in ii if _n[i].dot(ref) > 0.25]


regler()
EMP = {f: empreinte(f) for f in ("thumb", "index", "pinky")}
_p0, _n0 = sommets_evalues()
dire("empreintes", {
    f: {"sommets": len(v),
        "part_de_la_phalange": round(
            len(v) / max(1, sum(1 for i, n in _dom.items() if n == DEF[f][-1])), 2)}
    for f, v in EMP.items()})


def ecart_empreintes(a, b):
    _p, _n = sommets_evalues()
    if not EMP[a] or not EMP[b]:
        return None, None
    arbre = mathutils.kdtree.KDTree(len(EMP[b]))
    for k, i in enumerate(EMP[b]):
        arbre.insert(_p[i], k)
    arbre.balance()
    d = min(arbre.find(_p[i])[2] for i in EMP[a])
    na = sum((_n[i] for i in EMP[a]), mathutils.Vector((0, 0, 0)))
    nb = sum((_n[i] for i in EMP[b]), mathutils.Vector((0, 0, 0)))
    face = (na.normalized().dot(nb.normalized())
            if na.length > 1e-9 and nb.length > 1e-9 else 1.0)
    return d, face


print("ATLAS_PHASE_H_PRETE")


# ── H.3 · LA POSE QUE SACHA DEMANDE : AURICULAIRE CONTRE POUCE ──
# C'est le cerclage rouge : elle exige les DEUX mobilités à la fois — le
# creusement des métacarpiens, qui amène l'auriculaire vers le pouce, et
# l'opposition du pouce, qui tourne sa pulpe vers lui. Aucune des deux ne
# suffit seule, et mon ancien rig n'avait ni l'une ni l'autre.
#
# On ne devine pas les réglages : on les cherche, et on mesure ce qu'ils
# donnent. Réussi = les empreintes se touchent en se faisant face.
# ═══ LES AMPLITUDES DE L'OPPOSITION SE MESURENT ═══
#
# Mes angles de départ (40° vers la paume, −55° axial, +22° vers l'index)
# donnaient au mieux 72,4 mm d'écart, et la recherche ramenait
# `Thumb_Opposition` à 0,05 : mon opposition ÉLOIGNAIT le pouce de
# l'auriculaire. C'était écrit dans le code — « vers l'index » — alors que pour
# rejoindre l'auriculaire le pouce doit passer AU-DELÀ de l'index.
#
# On ne réajuste pas ces trois nombres au jugé. On libère le métacarpien du
# pouce de son driver, on cherche les angles qui amènent réellement les
# empreintes l'une sur l'autre, et on inscrit CE résultat dans le driver.
_mth = f"MCH_thumb_meta_result{SIDE}"
for _i in (0, 1, 2):
    try:
        rig.driver_remove(f'pose.bones["{_mth}"].rotation_euler', _i)
    except Exception:
        pass


def _poser_pouce(x, y, z, **props):
    regler(**props)
    rig.pose.bones[_mth].rotation_mode = "XYZ"
    rig.pose.bones[_mth].rotation_euler = (math.radians(x), math.radians(y),
                                           math.radians(z))
    bpy.context.view_layer.update()


_libre = None
for x in (0.0, 25.0, 50.0, -25.0, -50.0):
    for y in (0.0, -50.0, -100.0, 50.0, 100.0):
        for z in (0.0, -30.0, -60.0, 30.0, 60.0):
            for cup in (0.6, 1.0):
                for pk in (0.4, 0.7):
                    _poser_pouce(x, y, z, Cup=cup, Pinky_Curl=pk,
                                 Ring_Curl=pk * 0.5, Thumb_Curl=0.35)
                    d, face = ecart_empreintes("pinky", "thumb")
                    if d is None:
                        continue
                    sc = d * 1000.0 * 100.0 + (face + 1.0) * 2000.0
                    if _libre is None or sc < _libre[0]:
                        _libre = (sc, d, face, (x, y, z), cup, pk)
_pas3 = [12.0, 25.0, 15.0]
for _t in range(6):
    bx, by, bz = _libre[3]
    for _i, _st in enumerate(_pas3):
        for _dv in (-_st, +_st):
            _a = [bx, by, bz]
            _a[_i] += _dv
            _poser_pouce(*_a, Cup=_libre[4], Pinky_Curl=_libre[5],
                         Ring_Curl=_libre[5] * 0.5, Thumb_Curl=0.35)
            d, face = ecart_empreintes("pinky", "thumb")
            if d is None:
                continue
            sc = d * 1000.0 * 100.0 + (face + 1.0) * 2000.0
            if sc < _libre[0]:
                _libre = (sc, d, face, tuple(_a), _libre[4], _libre[5])
    _pas3 = [v * 0.6 for v in _pas3]
OPPO_MESUREE = _libre[3]
dire("opposition_mesuree", {
    "angles_du_metacarpien_deg": [round(v, 1) for v in OPPO_MESUREE],
    "ecart_des_empreintes_mm": round(_libre[1] * 1000, 2),
    "se_font_face": round(_libre[2], 3),
    "creusement": _libre[4], "repli_auriculaire": _libre[5],
    "ce_que_j_avais_suppose_deg": [round(OPPO[0], 1), round(OPPO[1], 1),
                                   round(OPPO[2], 1)]})

# On réinscrit le driver avec les amplitudes MESURÉES.
for _ax, _deg in enumerate(OPPO_MESUREE):
    driver(_mth, _ax,
           f"opp * {math.radians(_deg):.6f} + fist * {math.radians(_deg) * 0.55:.6f}",
           {"opp": "Thumb_Opposition", "fist": "Fist"})
bpy.context.view_layer.update()

_meilleur, _journal_pince = None, []
for cup in (0.4, 0.7, 1.0):
    for opp in (0.4, 0.7, 1.0):
        for pk in (0.3, 0.5, 0.7):
            for tc in (0.2, 0.4, 0.6):
                regler(Cup=cup, Thumb_Opposition=opp, Pinky_Curl=pk,
                       Thumb_Curl=tc, Ring_Curl=pk * 0.5)
                d, face = ecart_empreintes("pinky", "thumb")
                if d is None:
                    continue
                # Se toucher NE SUFFIT PAS : deux empreintes doivent se faire
                # face, sinon c'est le flanc du doigt qui touche. C'est la faute
                # que Sacha a vue sur mes images avant que je la voie dans mes
                # chiffres.
                sc = d * 1000.0 * 100.0 + (face + 1.0) * 2000.0
                if _meilleur is None or sc < _meilleur[0]:
                    _meilleur = (sc, d, face, dict(Cup=cup, Thumb_Opposition=opp,
                                                   Pinky_Curl=pk, Thumb_Curl=tc,
                                                   Ring_Curl=pk * 0.5))
_pas = {"Cup": 0.15, "Thumb_Opposition": 0.15, "Pinky_Curl": 0.1, "Thumb_Curl": 0.1}
for _t in range(5):
    base = dict(_meilleur[3])
    for k, st in _pas.items():
        for dv in (-st, +st):
            essai = dict(base)
            essai[k] = max(0.0, min(1.0, base[k] + dv))
            essai["Ring_Curl"] = essai["Pinky_Curl"] * 0.5
            regler(**essai)
            d, face = ecart_empreintes("pinky", "thumb")
            if d is None:
                continue
            sc = d * 1000.0 * 100.0 + (face + 1.0) * 2000.0
            if sc < _meilleur[0]:
                _meilleur = (sc, d, face, essai)
    _pas = {k: v * 0.6 for k, v in _pas.items()}
    _journal_pince.append({"tour": _t + 1, "ecart_mm": round(_meilleur[1] * 1000, 2),
                           "se_font_face": round(_meilleur[2], 3)})
POSE_PINCE = _meilleur[3]
dire("pince_auriculaire_pouce", {
    "ecart_des_empreintes_mm": round(_meilleur[1] * 1000, 2),
    "se_font_face": round(_meilleur[2], 3),
    "reglages": {k: round(v, 3) for k, v in POSE_PINCE.items()},
    "journal": _journal_pince,
    "reussi": bool(_meilleur[1] * 1000 < 2.0 and _meilleur[2] < -0.5)})

# ── H.4 · LA SÉQUENCE DE VALIDATION ──
POSES = [
    ("Hand_Neutral", {}),
    ("Hand_Relaxed", {"Relax": 1.0}),
    ("Hand_Open", {"Spread": 1.0}),
    ("Hand_Spread_Min", {"Spread": -1.0}),
    ("Hand_Fist", {"Fist": 1.0, "Thumb_Curl": 1.0, "Thumb_Opposition": 0.6}),
    ("Hand_Fist_25", {"Fist": 0.25}),
    ("Hand_Fist_50", {"Fist": 0.5}),
    ("Hand_Fist_75", {"Fist": 0.75}),
    ("Hand_Point", {"Middle_Curl": 1.0, "Ring_Curl": 1.0, "Pinky_Curl": 1.0,
                    "Thumb_Curl": 0.5}),
    ("Hand_Pinch", {"Index_Curl": 0.55, "Thumb_Opposition": 0.85,
                    "Thumb_Curl": 0.35}),
    ("Hand_OK", {"Index_Curl": 0.6, "Thumb_Opposition": 0.9, "Thumb_Curl": 0.4,
                 "Spread": 0.4}),
    ("Hand_Cupped", {"Cup": 1.0}),
    ("Hand_Pinky_Thumb", POSE_PINCE),
]
_controle = {}
for nom_pose, reglages in POSES:
    regler(**reglages)
    _p, _n = sommets_evalues()
    _dep = max((a - b).length for a, b in zip(_repos, _p)) * 1000
    d_pi, f_pi = ecart_empreintes("pinky", "thumb")
    d_ix, f_ix = ecart_empreintes("index", "thumb")
    _controle[nom_pose] = {
        "course_max_mm": round(_dep, 1),
        "auriculaire_au_pouce_mm": round(d_pi * 1000, 1) if d_pi is not None else None,
        "index_au_pouce_mm": round(d_ix * 1000, 1) if d_ix is not None else None}
regler()
dire("poses_de_validation", _controle)

with open(os.path.join(DOSSIER, f"rapport-rig{SIDE}.json"), "w",
          encoding="utf-8") as f:
    json.dump(rapport, f, ensure_ascii=False, indent=2)
print("ATLAS_PHASE_H terminée")


# ═══════════════════════════════════════════════════════════════════
#   LES RENDUS
# ═══════════════════════════════════════════════════════════════════
if not SANS_RENDU:
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = 900
    sc.view_settings.view_transform = "AgX"
    sc.render.film_transparent = False

    peau = bpy.data.materials.new("peau")
    peau.use_nodes = True
    _bs = peau.node_tree.nodes["Principled BSDF"]
    _bs.inputs["Base Color"].default_value = (0.82, 0.62, 0.55, 1.0)
    _bs.inputs["Roughness"].default_value = 0.42
    if "Subsurface Weight" in _bs.inputs:
        _bs.inputs["Subsurface Weight"].default_value = 0.12
    geo.data.materials.clear()
    geo.data.materials.append(peau)

    _monde = bpy.data.worlds.new("fond")
    _monde.use_nodes = True
    _monde.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    sc.world = _monde

    # ═══ QUEL CÔTÉ EST LA PAUME : MESURÉ, PAS SUPPOSÉ ═══
    # Le signe d'une normale construite par produit vectoriel dépend de l'ordre
    # des points ; ma première planche étiquetait « paume » une vue du DOS. On
    # l'établit par le mouvement : en fléchissant, les bouts des doigts partent
    # DU CÔTÉ DE LA PAUME.
    regler()
    _pa, _ = sommets_evalues()
    regler(Fist=0.5)
    _pb, _ = sommets_evalues()
    regler()
    _bouts = [i for i, n in _dom.items() if n.endswith(f"_03{SIDE}")]
    _dep = sum(((_pb[i] - _pa[i]) for i in _bouts), mathutils.Vector((0, 0, 0)))
    _dep = _dep - AXE * _dep.dot(AXE)
    PALMAIRE = _dep.normalized()
    _cote_pouce = (ANATOMIE["thumb"]["pointe"] - poignet).dot(T)
    Tp = T if _cote_pouce > 0 else -T
    print("ATLAS_COTE_PAUME " + json.dumps(
        {"palmaire_contre_normale_construite": round(PALMAIRE.dot(N), 3),
         "travers_oriente_vers_le_pouce": round(Tp.dot(T), 1)}, ensure_ascii=False))
    # La caméra se place DU CÔTÉ qu'elle photographie.
    PLANS = {"paume": PALMAIRE, "dos": -PALMAIRE,
             "pouce": Tp, "auriculaire": -Tp}

    def rendre(nom_pose, plan, direction, cadre=0.205):
        for o in [x for x in bpy.data.objects if x.type in ("CAMERA", "LIGHT", "EMPTY")]:
            bpy.data.objects.remove(o, do_unlink=True)
        _p, _ = sommets_evalues()
        # On vise la MAIN, pas le bras : les sommets tenus par DEF_hand
        # appartiennent au moignon d'avant-bras, et les inclure repoussait la
        # main dans un coin du cadre.
        _ii = [i for i, n in _dom.items() if n != f"DEF_hand{SIDE}"]
        vise = sum((_p[i] for i in _ii), mathutils.Vector((0, 0, 0))) / len(_ii)
        cam = bpy.data.cameras.new("cam"); cam.lens = 85.0
        oc = bpy.data.objects.new("cam", cam)
        bpy.context.collection.objects.link(oc)
        sc.camera = oc
        recul = (cadre / 2.0) / math.tan(cam.angle / 2.0)
        cam.clip_start, cam.clip_end = recul / 400.0, recul * 400.0
        oc.location = vise + direction.normalized() * recul
        cible = bpy.data.objects.new("cible", None)
        bpy.context.collection.objects.link(cible)
        cible.location = vise
        c = oc.constraints.new("TRACK_TO"); c.target = cible
        # Puissances revues : 260 W à 45 cm saturait complètement l'image, elle
        # sortait blanche. Une source de 0,35 m à cette distance éclaire une
        # main avec quelques dizaines de watts.
        for _v, _e in ((direction.normalized() * 0.6 + N * 0.5, 30.0),
                       (direction.normalized() * 0.5 - T * 0.7, 11.0),
                       (-direction.normalized() * 0.4 + AXE * 0.6, 7.0)):
            ld = bpy.data.lights.new("l", "AREA"); ld.energy = _e; ld.size = 0.35
            ol = bpy.data.objects.new("l", ld)
            bpy.context.collection.objects.link(ol)
            ol.location = vise + _v.normalized() * 0.45
            cl = ol.constraints.new("TRACK_TO"); cl.target = cible
        sc.render.filepath = os.path.join(DOSSIER, f"{nom_pose}-{plan}.png")
        bpy.ops.render.render(write_still=True)

    A_RENDRE = ["Hand_Open", "Hand_Fist", "Hand_Pinky_Thumb", "Hand_Relaxed",
                "Hand_Pinch", "Hand_Cupped"]
    for nom_pose, reglages in POSES:
        if nom_pose not in A_RENDRE:
            continue
        regler(**reglages)
        for plan, direction in PLANS.items():
            rendre(nom_pose, plan, direction)
        print(f"ATLAS_RENDU {nom_pose} — 4 plans")
    regler()


# ═══════════════════════════════════════════════════════════════════
#   PHASE G — PRÉSERVATION DU VOLUME
# ═══════════════════════════════════════════════════════════════════
# Le tutoriel prévient : « Les correctifs ne doivent jamais masquer de mauvais
# poids. » On limite donc le lissage aux ZONES ARTICULAIRES, et on VÉRIFIE
# qu'il améliore vraiment au lieu de simplement flouter.
#
# Le défaut visé est mesurable : un pincement, c'est de la chair localement
# écrasée, donc des arêtes bien plus courtes qu'au repos. On mesure ce taux de
# compression avant et après.
regler()
_p_rep, _ = sommets_evalues()
_long_repos = {e.index: (_p_rep[e.vertices[0]] - _p_rep[e.vertices[1]]).length
               for e in geo.data.edges}


def compression_max(groupe_os):
    _p, _ = sommets_evalues()
    _ii = {i for i, n in _dom.items() if n == groupe_os}
    pire = 1.0
    for e in geo.data.edges:
        if e.vertices[0] in _ii and e.vertices[1] in _ii:
            l0 = _long_repos[e.index]
            if l0 > 1e-6:
                pire = min(pire, (_p[e.vertices[0]] - _p[e.vertices[1]]).length / l0)
    return pire


# ═══ CALIBRER LA SONDE AVANT DE LIRE SON VERDICT ═══
# Un doigt qui se plie COMPRIME sa peau palmaire : c'est normal, pas un
# pincement. Sans repère, je prendrais un pli pour un défaut. On mesure donc la
# compression sur une pose franche mais saine — le poing — pour savoir ce que
# vaut « normal » sur ce maillage.
regler(Fist=1.0)
_calibre = {f: compression_max(DEF[f][-1]) for f in ("thumb", "pinky", "index")}
regler(**POSE_PINCE)
_avant_g = {f: compression_max(DEF[f][-1]) for f in ("thumb", "pinky", "index")}

gz = geo.vertex_groups.new(name="ZONES_ARTICULAIRES")
gz_idx = []
_zones = []
for nom, d in ANATOMIE.items():
    _zones.append(d["jointure"])
    _zones += [a[1] for a in d["articulations"]]
for i, q in enumerate(pts):
    m = min((q - z).length for z in _zones)
    if m < 0.014:
        gz.add([i], max(0.0, 1.0 - m / 0.014), "REPLACE")
        gz_idx.append(i)
lisse = geo.modifiers.new("correctif_lissage", "CORRECTIVE_SMOOTH")
lisse.vertex_group = gz.name
lisse.factor = 0.35
lisse.iterations = 12
lisse.use_only_smooth = True

regler(**POSE_PINCE)
_apres_g = {f: compression_max(DEF[f][-1]) for f in ("thumb", "pinky", "index")}
# S'il n'améliore rien, il ne fait que flouter : on le retire.
_gain = {f: round(_apres_g[f] - _avant_g[f], 4) for f in _avant_g}
if sum(_gain.values()) <= 0:
    geo.modifiers.remove(lisse)
    _verdict_g = "retiré — il n'améliorait pas la compression, il n'aurait fait que flouter"
else:
    _verdict_g = f"conservé (facteur {lisse.factor}, limité aux zones articulaires)"
regler()
dire("phase_g", {
    "compression_de_reference_poing": {k: round(v, 4) for k, v in _calibre.items()},
    "compression_avant": {k: round(v, 4) for k, v in _avant_g.items()},
    "compression_apres": {k: round(v, 4) for k, v in _apres_g.items()},
    "gain": _gain, "verdict": _verdict_g,
    "sommets_dans_les_zones": len(gz_idx)})

# ═══ LE CREUX ENTRE LES DOIGTS (règle 8) ═══
# Il restait 1 043 sommets portant des poids de deux doigts. Avant d'appeler ça
# un défaut, on regarde OÙ ils sont : le tutoriel demande justement que la base
# des doigts mélange, et que le creux interdigital soit inspecté à part.
_commissures = COMMISSURES
_dans_le_creux, _ailleurs = 0, 0
for v in geo.data.vertices:
    gs = [(g.weight, _gnom.get(g.group, "")) for g in v.groups if g.weight > 0.01]
    if not gs:
        continue
    if len({famille(n) for _w, n in gs
            if not n.endswith(f"_meta{SIDE}")} - {"hand"}) > 1:
        q = pts[v.index]
        if min((q - c).length for c in _commissures) < 0.022:
            _dans_le_creux += 1
        else:
            _ailleurs += 1
dire("creux_entre_les_doigts", {
    "sommets_a_deux_doigts_dans_le_creux": _dans_le_creux,
    "sommets_a_deux_doigts_ailleurs": _ailleurs,
    "lecture": "la règle 7 demande ce mélange à la base des doigts ; seuls les "
               "sommets « ailleurs » seraient un défaut"})

# ═══════════════════════════════════════════════════════════════════
#   FORMES DE CONTRÔLE, BIBLIOTHÈQUE DE POSES, LIVRAISON
# ═══════════════════════════════════════════════════════════════════
col_wgt = bpy.data.collections.new("WIDGETS_Hand")
bpy.context.scene.collection.children.link(col_wgt)
col_wgt.hide_viewport = col_wgt.hide_render = True


def widget(nom, rayon, segments=16, plat=True):
    me = bpy.data.meshes.new(f"WGT_{nom}")
    bm2 = bmesh.new()
    bmesh.ops.create_circle(bm2, cap_ends=False, radius=rayon, segments=segments)
    bm2.to_mesh(me); bm2.free()
    o = bpy.data.objects.new(f"WGT_{nom}", me)
    col_wgt.objects.link(o)
    return o


_w_world = widget("world", 0.055, 24)
_w_hand = widget("hand", 0.040, 20)
_w_meta = widget("meta", 0.012, 12)
_w_pha = widget("phalange", 0.008, 10)
rig.pose.bones[f"CTRL_world{SIDE}"].custom_shape = _w_world
rig.pose.bones[f"CTRL_hand{SIDE}"].custom_shape = _w_hand
for nom in NOMS4 + ["thumb"]:
    for cnom in CTRL[nom]:
        rig.pose.bones[cnom].custom_shape = (
            _w_meta if cnom.split("_")[2].startswith("meta") else _w_pha)

# La bibliothèque de poses : une action par pose nommée.
_bibliotheque = []
for nom_pose, reglages in POSES:
    regler(**reglages)
    act = bpy.data.actions.new(nom_pose)
    rig.animation_data_create()
    _anc = rig.animation_data.action
    rig.animation_data.action = act
    for pb in rig.pose.bones:
        if pb.name.startswith("CTRL_"):
            pb.keyframe_insert("rotation_euler", frame=1)
    for nomp, _d, _mi, _ma in PROPS:
        pbh.keyframe_insert(f'["{nomp}"]', frame=1)
    act.use_fake_user = True
    try:
        act.asset_mark()
    except Exception:
        pass
    rig.animation_data.action = _anc
    _bibliotheque.append(nom_pose)
regler()

# Livraison : seuls les contrôleurs sont visibles ; rien n'est supprimé.
try:
    for c in arm.collections:
        c.is_visible = (c.name == "CONTROLS")
except Exception:
    pass
for pb in rig.pose.bones:
    if not pb.name.startswith("CTRL_"):
        pb.bone.hide = True

_blend = os.path.join(DOSSIER, f"RIG_Hand{SIDE}.blend")
bpy.ops.wm.save_as_mainfile(filepath=_blend)

rapport["livraison"] = {
    "maillage": geo.name, "armature": rig.name,
    "os": {"CTRL": sum(1 for b in arm.bones if b.name.startswith("CTRL_")),
           "MCH": sum(1 for b in arm.bones if b.name.startswith("MCH_")),
           "DEF": sum(1 for b in arm.bones if b.name.startswith("DEF_"))},
    "proprietes": [p[0] for p in PROPS],
    "contraintes": ["COPY_TRANSFORMS", "COPY_ROTATION", "LIMIT_ROTATION"],
    "correctifs": _verdict_g,
    "bibliotheque_de_poses": _bibliotheque,
    "fichier_blend": os.path.basename(_blend)}
with open(os.path.join(DOSSIER, f"rapport-rig{SIDE}.json"), "w",
          encoding="utf-8") as f:
    json.dump(rapport, f, ensure_ascii=False, indent=2)
print("ATLAS_TERMINE " + json.dumps(
    {"rapport": f"rapport-rig{SIDE}.json", "blend": os.path.basename(_blend),
     "poses": len(_bibliotheque)}, ensure_ascii=False))
