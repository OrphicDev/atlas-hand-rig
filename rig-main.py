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
# ═══ NE PAS TAMPONNER LA SORTIE ═══
# Mesuré : deux lancements de 11 et 16 minutes n'avaient écrit ZÉRO octet, et
# une exception laissait un journal vide. On ne peut alors distinguer un calcul
# long d'un blocage, ni lire l'erreur qui a tout arrêté. Blender tamponne en
# amont de Python ; il faut le lui dire ligne par ligne.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

import bpy
import mathutils

# ═══ LES CHEMINS SE RÉSOLVENT DEPUIS LE DÉPÔT, PAS DEPUIS UN NIVEAU FIXE ═══
#
# `RACINE` remontait trois dossiers en dur : le script ne pouvait donc tourner
# que depuis l'arborescence d'origine, et un clone propre du dépôt public
# échouait à l'import. On CHERCHE la racine — le premier dossier ancêtre qui
# contient `atelier/humain.py` — ce qui marche aussi bien depuis le dépôt de
# travail que depuis un clone où le script est à la racine.
def _trouver_racine(depart):
    d = os.path.dirname(os.path.abspath(depart))
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "atelier", "humain.py")):
            return d
        d = os.path.dirname(d)
    raise RuntimeError(
        "atelier/humain.py introuvable en remontant depuis " + depart)


RACINE = _trouver_racine(__file__)
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


# ═══ UN TEST FAUX DOIT ARRÊTER LE PIPELINE ═══
#
# La version précédente écrivait `"reussi": false` pour la pince
# auriculaire-pouce, puis sauvegardait le .blend et affichait ATLAS_TERMINE.
# C'est la faute la plus grave de tout ce travail : un rapport qui contient son
# propre échec et conclut quand même. Aucune des autres corrections ne vaut
# quoi que ce soit tant que celle-ci n'est pas faite, parce que sans elle tout
# résultat peut mentir de la même façon.
ECHECS_ACCEPTATION = []
# Le côté palmaire, relevé par le mouvement plus bas. Déclaré ici parce qu'il
# est affecté avant d'être lu : une déclaration placée après son affectation ne
# sert à rien.
PALMAIRE_REF = [mathutils.Vector((0, 0, 1))]


def exiger(nom, ok, mesure, seuil):
    """Enregistre un critère obligatoire. Un seul faux interdit la livraison."""
    if not ok:
        ECHECS_ACCEPTATION.append({"critere": nom, "mesure": mesure,
                                   "seuil": seuil})
    print(f"ATLAS_CRITERE {'OK ' if ok else 'ÉCHEC'} · {nom} · "
          f"mesuré {mesure} · exigé {seuil}")
    return ok


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

# ═══ LES QUATRE MÉTACARPIENS NE PARTENT PLUS DU MÊME POINT ═══
#
# Ils partaient tous de BASE_PAUME. Leurs têtes superposées produisaient un
# éventail artificiel et bridaient le creusement : quatre os qui pivotent
# autour d'un centre unique ne peuvent pas creuser une paume, ils ne peuvent
# que l'ouvrir en corolle.
#
# Dans une vraie main, les bases carpo-métacarpiennes forment un ARC
# TRANSVERSAL au niveau de la rangée distale du carpe. Cet arc est bien plus
# étroit que la ligne des jointures : la main s'évase du carpe vers les doigts.
# On mesure ce rapport au lieu de le poser — l'écartement des bases est celui
# des jointures ramené à la largeur réellement disponible à hauteur du carpe.
LIGNE_CMC = poignet + AXE * (L_PAUME * 0.18)
_tranche = [q for q in pts if abs((q - LIGNE_CMC).dot(AXE)) < 0.006]
_larg_cmc = ((max(q.dot(T) for q in _tranche) - min(q.dot(T) for q in _tranche))
             if len(_tranche) > 12 else 0.030)
_t_mcp = {n: (ANATOMIE[n]["jointure"] - poignet).dot(T) for n in NOMS4}
_larg_mcp = max(_t_mcp.values()) - min(_t_mcp.values())
# On garde une marge : les bases doivent rester DANS le volume, pas sur la peau.
_ratio_arc = min(0.55, (_larg_cmc * 0.62) / max(1e-6, _larg_mcp))
_t_moyen = sum(_t_mcp.values()) / 4.0
BASES_CMC = {}
for _n in NOMS4:
    # L'arc est aussi un arc DANS LA PROFONDEUR : les bases des rayons internes
    # (annulaire, auriculaire) sont un peu plus palmaires, ce qui donne au
    # creusement un axe qui n'est pas le même pour les quatre.
    _u = abs(_t_mcp[_n] - _t_moyen) / max(1e-6, _larg_mcp / 2.0)
    BASES_CMC[_n] = (LIGNE_CMC
                     + T * ((_t_mcp[_n] - _t_moyen) * _ratio_arc)
                     - N * (_u * _u * L_PAUME * 0.055))
_ecarts_bases = sorted(round((BASES_CMC[a] - BASES_CMC[b]).length * 1000, 1)
                       for a in NOMS4 for b in NOMS4 if a < b)
print("ATLAS_ARC_CMC " + json.dumps({
    "largeur_a_hauteur_du_carpe_mm": round(_larg_cmc * 1000, 1),
    "largeur_des_jointures_mm": round(_larg_mcp * 1000, 1),
    "ratio_de_l_arc": round(_ratio_arc, 3),
    "ecarts_entre_bases_mm": _ecarts_bases}, ensure_ascii=False))

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
        depart = BASES_CMC[nom]
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

_CACHE_POSE = {"jeton": None, "valeur": None}


def sommets_evalues():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw, m3 = geo.matrix_world, geo.matrix_world.to_3x3()
    p = [mw @ v.co.copy() for v in m.vertices]
    n = [(m3 @ v.normal).normalized() for v in m.vertices]
    ev.to_mesh_clear()
    return p, n


def sommets_caches(jeton):
    """Le maillage évalué, calculé une seule fois par pose.

    Les sondes s'appellent plusieurs fois pour une même pose ; sans cache,
    chaque essai de l'optimiseur déformait le maillage quatre fois.
    """
    if _CACHE_POSE["jeton"] != jeton:
        _CACHE_POSE["jeton"] = jeton
        _CACHE_POSE["valeur"] = sommets_evalues()
    return _CACHE_POSE["valeur"]


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

# ═══ LA FERMETURE EST UNE CASCADE, PAS TROIS ARCS SIMULTANÉS ═══
#
# Les trois articulations d'un doigt suivaient `Fist` au même rythme : d'où
# quatre arcs identiques, une boucle trop ronde, et des phalanges qui ne
# s'empilent pas contre la paume. Un vrai doigt se ferme par étapes — la
# métacarpo-phalangienne engage, la proximale suit, la distale finit.
#
# L'évaluateur de drivers de Blender n'accepte que des expressions linéaires
# (mesuré : `min`/`max` et le produit de deux variables échouent en silence).
# Mais les butées de la phase E ÉCRÊTENT. En surpilotant une articulation avec
# un décalage négatif, elle reste donc plaquée sur son extension tant que
# `Fist` n'a pas rattrapé ce décalage : le retard d'entrée en action est obtenu
# sans la moindre condition.
#
#   pente > amplitude  → l'articulation SATURE avant la fin de la course
#   décalage négatif   → elle DÉMARRE plus tard
CASCADE = {"01": (1.12, 0.00),      # engage tout de suite
           "02": (1.55, -0.18),     # suit, et sature avant la fin
           "03": (1.45, -0.34)}     # finit en dernier
# Et les quatre doigts ne sont pas interchangeables : le majeur part devant,
# l'auriculaire ferme plus tôt et plus court, l'annulaire suit le majeur.
DEPART = {"index": 0.00, "middle": -0.03, "ring": -0.01, "pinky": 0.04}
for nom in NOMS4:
    for suf, mx in MAXI.items():
        mnom = f"MCH_{nom}_{suf}_result{SIDE}"
        pente, retard = CASCADE[suf]
        k = SIGNE * math.radians(mx) * AVANCE[nom] * pente
        c0 = SIGNE * math.radians(mx) * AVANCE[nom] * (retard + DEPART[nom])
        kr = SIGNE * math.radians(mx) * RELAX[nom] * (0.7 if suf == "03" else 1.0)
        driver(mnom, AXE_FLEXION,
               f"(fist + curl) * {k:.6f} + relax * {kr:.6f} + {c0:.6f}",
               {"fist": "Fist", "curl": CURL[nom], "relax": "Relax"})
# L'écartement agit sur la première phalange, autour de la normale de la paume.
ECART = {"index": 10.0, "middle": 1.0, "ring": -6.0, "pinky": -12.0}
# ═══ LES DOIGTS DIVERGENT EN SE FERMANT ═══
#
# Mesuré : les quatre doigts SEULS, sans pouce, se traversaient dès une
# fermeture de 0,7 (8 sommets) et massivement à 0,8 (444). Ce n'était donc ni
# le pouce ni la pose : c'était la fermeture. Mes doigts convergeaient en se
# repliant jusqu'à se pénétrer.
#
# Dans une vraie main ils ne se traversent pas, parce qu'ils s'écartent
# légèrement à mesure qu'ils se ferment. On ajoute ce mouvement, et on cherche
# son amplitude par la mesure — on ne la pose pas.
DIVERGENCE = {"index": 1.0, "middle": 0.35, "ring": -0.35, "pinky": -1.0}
K_DIVERGENCE = [8.0]        # cherché plus bas, en degrés

# ═══ LE SENS DE L'ÉCARTEMENT SE MESURE, IL NE SE DÉCRÈTE PAS ═══
#
# Mesuré sur le `.blend` de `b17e548` avec `outils/sonde-ecartement.py` : monter
# `Spread` REFERMAIT l'éventail sur les trois couples voisins — index/majeur de
# 17,06 à 6,62 mm, majeur/annulaire de 15,27 à 6,84 mm, annulaire/auriculaire de
# 30,10 à 24,21 mm. `Hand_Open`, qui vaut `Spread = 1`, était donc la main la
# PLUS serrée de la bibliothèque, et `Hand_Spread_Min` la plus ouverte : deux
# poses portaient le nom de leur contraire.
#
# Le checkpoint supposait un signe inversé SUR L'ANNULAIRE. C'est faux : la
# suite `ECART` est monotone (+10, +1, −6, −12), aucun doigt ne double son
# voisin, et les drivers l'appliquaient au dixième de degré près. Ce qui était
# retourné, c'est le SENS GLOBAL de la rotation autour de la normale de la
# paume — et le signe d'une normale construite est ARBITRAIRE. C'est très
# exactement la faute que la phase C corrige déjà pour la flexion, en MESURANT
# `SENS_FLEXION` au lieu de le supposer.
#
# Retourner `ECART` à la main réparerait la gauche et casserait la droite, dont
# la normale de paume est inversée. On mesure donc, comme pour la flexion : on
# écarte dans un sens, on regarde si l'éventail s'ouvre, et on garde le sens
# qui ouvre.
_VOISINS = (("index", "middle"), ("middle", "ring"), ("ring", "pinky"))


def eventail_des_bouts(_p):
    """Écart minimal, en mm, entre les chairs de deux bouts de doigts voisins.

    Sur la CHAIR et non sur l'os : c'est elle qui se traverse, et un os peut
    diverger pendant que la chair converge.
    """
    out = {}
    for a, b in _VOISINS:
        ib = bouts_de(b)
        t = mathutils.kdtree.KDTree(len(ib))
        for k, i in enumerate(ib):
            t.insert(_p[i], k)
        t.balance()
        out[f"{a}/{b}"] = min(t.find(_p[i])[2] for i in bouts_de(a)) * 1000.0
    return out


_essai_ecart = {}
for _s in (+1.0, -1.0):
    poser_os({f"MCH_{_n}_01_result{SIDE}": (0.0, 0.0, _s * ECART[_n])
              for _n in NOMS4})
    _essai_ecart[_s] = eventail_des_bouts(sommets_evalues()[0])
au_repos()
_eventail_repos = eventail_des_bouts(sommets_evalues()[0])
SIGNE_ECART = max(_essai_ecart, key=lambda s: sum(_essai_ecart[s].values()))
_gain_ecart = {c: _essai_ecart[SIGNE_ECART][c] - _eventail_repos[c]
               for c in _eventail_repos}
dire("sens_de_l_ecartement", {
    "eventail_au_repos_mm": {c: round(v, 2) for c, v in _eventail_repos.items()},
    "eventail_a_plus_ECART_mm": {c: round(v, 2)
                                 for c, v in _essai_ecart[+1.0].items()},
    "eventail_a_moins_ECART_mm": {c: round(v, 2)
                                  for c, v in _essai_ecart[-1.0].items()},
    "signe_retenu": SIGNE_ECART,
    "gain_du_sens_retenu_mm": {c: round(v, 2) for c, v in _gain_ecart.items()},
    "regle": "écarter doit AUGMENTER l'écart entre bouts de doigts voisins"})
# ═══ UNE SONDE QUI NE PEUT PAS ÉCHOUER NE PROUVE RIEN ═══
# Deux exigences, et la construction s'arrête si l'une manque :
#   · les deux sens doivent VRAIMENT différer, sinon on lirait du bruit et le
#     `max` ci-dessus trancherait à pile ou face ;
#   · le sens retenu doit ouvrir LES TROIS couples, pas seulement leur somme —
#     un doigt qui doublerait son voisin passerait sinon inaperçu derrière un
#     total flatteur.
if abs(sum(_essai_ecart[+1.0].values())
       - sum(_essai_ecart[-1.0].values())) < 1.0:
    raise RuntimeError("les deux sens d'écartement rendent le même éventail : "
                       "la sonde ne mesure pas ce qu'elle prétend mesurer")
_ecart_muet = [c for c, g in _gain_ecart.items() if g <= 0.5]
if _ecart_muet:
    raise RuntimeError(f"l'écartement ne sépare pas {_ecart_muet} : "
                       f"gains mesurés {_gain_ecart}")

for nom in NOMS4:
    # ═══ PAS DE PRODUIT DE DEUX VARIABLES DANS UN DRIVER ═══
    # J'avais écrit `fist * div * K`. Mesuré : la propriété était bien lue
    # (0 → 30) mais la rotation restait à +0,00°. C'est le même piège que
    # `min`/`max` plus haut — un produit de deux variables réclame
    # l'évaluateur Python, désactivé en mode fond, et le driver échoue en
    # silence. L'expression reste donc linéaire, et les poses qui ferment
    # règlent `Divergence` explicitement.
    #
    # Et la variable ne s'appelle plus `div` : sous ce nom, le driver était
    # rendu INVALIDE par Blender (`is_valid = false`) pendant que les autres
    # drivers du même os restaient valides. Un nom réservé, et un échec
    # totalement silencieux — la rotation restait à +0,00° sans le moindre
    # message.
    driver(f"MCH_{nom}_01_result{SIDE}", AXE_ECART,
           f"spread * {SIGNE_ECART * math.radians(ECART[nom]):.6f}",
           {"spread": "Spread"})
# Le creusement agit sur les MÉTACARPIENS, faiblement côté index, fortement côté
# auriculaire. C'est lui qui rapproche l'auriculaire du pouce — le cerclage
# rouge de Sacha.
CUP = {"index": 0.10, "middle": 0.25, "ring": 0.60, "pinky": 1.00}
CUP_MAX = 22.0
# Creuser une paume n'est pas fléchir quatre bases du même angle : les rayons
# internes tournent AUSSI sur eux-mêmes, ce qui présente l'auriculaire au pouce
# au lieu de simplement le rapprocher. Avec des bases désormais distinctes, ces
# deux composantes ne pivotent plus autour d'un centre unique.
CUP_AXIAL = {"index": 0.0, "middle": 0.05, "ring": 0.35, "pinky": 0.70}
for nom in NOMS4:
    driver(f"MCH_{nom}_meta_result{SIDE}", AXE_FLEXION,
           f"cup * {SIGNE * math.radians(CUP_MAX) * CUP[nom]:.6f}", {"cup": "Cup"})
    if CUP_AXIAL[nom]:
        driver(f"MCH_{nom}_meta_result{SIDE}", 1,
               f"cup * {-math.radians(CUP_MAX) * CUP_AXIAL[nom]:.6f}",
               {"cup": "Cup"})
# Le pouce : flexion propre, et une opposition COMPOSÉE, comme l'exige le
# tutoriel — « Ne pilote pas l'opposition uniquement avec une rotation sur un
# seul axe. Le mouvement réel du pouce est oblique et composé. »
# ═══ FIST NE PILOTE PLUS LE POUCE ═══
#
# Il s'additionnait à Thumb_Curl sur les mêmes phalanges, ET une part de Fist
# s'ajoutait encore à l'opposition du métacarpien. La pose Hand_Fist appliquait
# Fist=1 avec Thumb_Curl=1 : les trois articulations du pouce finissaient
# plaquées contre leurs butées, et sa chair distale tombait à 0,106 de sa
# longueur de repos. Ce n'était pas un défaut de poids, c'était une pose
# impossible imposée par des commandes qui s'empilaient.
#
# La spécification dit que Fist ferme LES QUATRE DOIGTS. Le pouce a ses deux
# commandes propres, et les poses les règlent explicitement.
for suf, mx in MAXI_POUCE.items():
    driver(f"MCH_thumb_{suf}_result{SIDE}", AXE_FLEXION,
           f"curl * {SIGNE * math.radians(mx):.6f}", {"curl": "Thumb_Curl"})
OPPO = {0: SIGNE * 40.0, 1: -55.0, 2: 22.0}     # remplacé plus bas par la mesure
for ax, deg in OPPO.items():
    driver(f"MCH_thumb_meta_result{SIDE}", ax, f"opp * {math.radians(deg):.6f}",
           {"opp": "Thumb_Opposition"})

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


# Ces butées ne sont plus seulement des garde-fous : ce sont elles qui
# fabriquent la cascade, en écrêtant les droites surpilotées ci-dessus. Les
# valeurs restent celles du cahier des charges.
LIM = {"01": borne(20.0, 90.0), "02": borne(0.0, 110.0), "03": borne(10.0, 80.0)}
LIM_POUCE = {"01": borne(0.0, 60.0), "02": borne(0.0, 80.0)}
ECART_MAX = math.radians(15.0)

_poses_limitees = 0
for nom in NOMS4 + ["thumb"]:
    for dnom, cnom, mnom in zip(DEF[nom], CTRL[nom], MCH[nom]):
        suf = dnom.split("_")[2].replace(SIDE, "")
        if suf == "meta":
            # ═══ LES MÉTACARPIENS SORTAIENT DE LA BOUCLE AVANT LES VERROUS ═══
            # Le `continue` était placé AVANT les verrouillages : leurs
            # contrôleurs pouvaient donc être déplacés ou redimensionnés par
            # inadvertance, ce que les défauts interdits proscrivent
            # explicitement. Ils ont leurs propres butées, adaptées au
            # creusement : les rayons internes en autorisent plus que les
            # externes, comme dans une vraie main.
            # ═══ LA TRAPÉZO-MÉTACARPIENNE N'EST PAS UNE CARPO-MÉTACARPIENNE ═══
            # En bornant les métacarpiens, j'avais appliqué au POUCE les butées
            # des quatre doigts : sa rotation d'opposition, mesurée à +53,6°,
            # se retrouvait écrasée à 12°. Les trois pinces ont régressé
            # ensemble — c'était le signe d'une cause commune, et c'était
            # celle-là : j'avais bridé le mouvement dont elles dépendent toutes.
            #
            # Le pouce s'articule sur une SELLE à trois degrés : flexion 50°,
            # extension 20°, abduction 45°, et la rotation d'opposition mesurée
            # au scanner à 100° ± 7. Élargies d'un quart, comme partout.
            if nom == "thumb":
                _bx = (SIGNE * math.radians(-20.0), SIGNE * math.radians(62.5))
                _by = (-math.radians(125.0), math.radians(125.0))
                _bz = (-math.radians(56.0), math.radians(56.0))
            else:
                _cmc = {"index": 5.0, "middle": 8.0, "ring": 16.0,
                        "pinky": 26.0}[nom]
                _a2, _b2 = (SIGNE * math.radians(_cmc),
                            SIGNE * math.radians(-_cmc * 0.35))
                _bx = (min(_a2, _b2), max(_a2, _b2))
                _by = (-math.radians(_cmc * 0.9), math.radians(_cmc * 0.9))
                _bz = (-math.radians(8.0), math.radians(8.0))
            for cible in (cnom, mnom):
                c = rig.pose.bones[cible].constraints.new("LIMIT_ROTATION")
                c.owner_space = "LOCAL"
                c.use_limit_x = c.use_limit_y = c.use_limit_z = True
                c.min_x, c.max_x = min(_bx), max(_bx)
                c.min_y, c.max_y = min(_by), max(_by)
                c.min_z, c.max_z = min(_bz), max(_bz)
                _poses_limitees += 1
            pbm = rig.pose.bones[cnom]
            pbm.lock_location = (True, True, True)
            pbm.lock_scale = (True, True, True)
            pbm.lock_rotation = (False, False, False)
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
    # ═══ SEULS LES GROUPES D'OS SONT DES FAMILLES ═══
    # `ZONES_ARTICULAIRES`, créé pour le lissage correctif, n'est l'os de
    # personne — et il domine 203 sommets. Rangé dans « hand », il fabriquait
    # des intersections fantômes sur Pinch et OK et en cachait de vraies sur
    # Point. Un groupe qui n'est pas un os n'appartient à aucune famille.
    for f in NOMS4 + ["thumb"]:
        if n.startswith(f"DEF_{f}_"):
            return f
    return "hand" if n.startswith("DEF_") else None


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
    # Les contrôleurs portent désormais des corrections FK dans certaines
    # poses ; sans cette remise à zéro, une pose déteindrait sur la suivante et
    # toute mesure ultérieure serait fausse.
    for pb in rig.pose.bones:
        if pb.name.startswith("CTRL_"):
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (0.0, 0.0, 0.0)
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


regler()
_p_rep, _ = sommets_evalues()
_long_repos = {e.index: (_p_rep[e.vertices[0]] - _p_rep[e.vertices[1]]).length
               for e in geo.data.edges}


# ═══ UN SEUL MINIMUM NE DÉCRIT PAS UNE ARTICULATION ═══
# Le minimum absolu d'une arête repère un point aberrant ; il ne dit pas si la
# chair s'effondre ou si une seule arête mal placée se ferme. On publie donc la
# distribution, et l'identité de l'arête la plus comprimée pour pouvoir aller
# la regarder.
def compression(groupe_os):
    _p, _ = sommets_evalues()
    _ii = {i for i, n in _dom.items() if n == groupe_os}
    r = []
    for e in geo.data.edges:
        if e.vertices[0] in _ii and e.vertices[1] in _ii:
            l0 = _long_repos[e.index]
            if l0 > 1e-6:
                r.append(((_p[e.vertices[0]] - _p[e.vertices[1]]).length / l0,
                          e.index))
    if not r:
        return None
    r.sort()

    def pc(q):
        return r[min(len(r) - 1, int(q * len(r)))][0]

    pire_i = r[0][1]
    _mil = (_p[geo.data.edges[pire_i].vertices[0]]
            + _p[geo.data.edges[pire_i].vertices[1]]) / 2.0
    return {"min": round(r[0][0], 4), "p1": round(pc(0.01), 4),
            "p5": round(pc(0.05), 4), "mediane": round(pc(0.50), 4),
            "aretes": len(r), "arete_la_plus_comprimee": pire_i,
            "position_mm": [round(x * 1000, 1) for x in _mil]}


def compression_max(groupe_os):
    c = compression(groupe_os)
    return 1.0 if c is None else c["min"]


# ═══ LES AUTO-INTERSECTIONS, MESURÉES SUR LE MAILLAGE ÉVALUÉ ═══
# Un contact autorisé et une pénétration se ressemblent en distance ; ils ne se
# ressemblent pas en signe. Un sommet est DEDANS s'il se trouve du mauvais côté
# de la surface la plus proche, et il faut une marge : sous 0,3 mm on est dans
# le bruit de maillage d'une main de 100 mm.
# ═══ CE QUI SÉPARE UN CONTACT D'UNE PÉNÉTRATION SUR UN MAILLAGE CONTINU ═══
#
# Ma première sonde comptait 60 sommets « dedans » entre l'index et la paume
# dans TOUTES les poses, y compris au repos. La cause est structurelle : la
# main est une surface continue, et à la frontière de deux familles d'os les
# sommets sont voisins par construction. Les compter, c'est mesurer la
# continuité du maillage, pas une faute de pose.
#
# Une vraie auto-intersection, c'est deux morceaux de peau qui étaient LOIN au
# repos et qui se superposent maintenant. On exige donc que la distance de
# repos entre les deux sommets dépasse une marge — sinon ils sont simplement
# voisins depuis toujours.
ECART_REPOS_MINIMAL = 0.014       # 14 mm : au-delà, deux surfaces distinctes
# ═══ LA TOLÉRANCE, À L'ÉCHELLE DE LA MAIN ═══
#
# Avec 0,3 mm, un appui pulpe contre pulpe comptait 1 sommet « dedans » : à
# l'endroit exact où deux surfaces se pressent, quelques sommets passent
# marginalement de l'autre côté. Ce n'est pas une traversée, c'est du bruit de
# maillage — et cet unique sommet, valant l'infini dans le score, faisait fuir
# l'optimiseur de 0,85 mm à 16,05 mm.
#
# Le tutoriel demande une tolérance cohérente avec l'échelle. Sur une main de
# 100 mm, une vraie interpénétration s'enfonce d'un demi-millimètre au moins.
# Ce seuil est VÉRIFIÉ plus bas sur une configuration connue pour traverser :
# s'il y masquait quoi que ce soit, il serait inutilisable.
PROFONDEUR_MINIMALE = 0.0005      # 0,5 mm


def intersections(pose_nom):
    _p, _n = sommets_evalues()
    par_groupe = {}
    for i, nm in _dom.items():
        _f = famille(nm)
        if _f is not None:
            par_groupe.setdefault(_f, []).append(i)
    arbres = {}
    for f, idx in par_groupe.items():
        t = mathutils.kdtree.KDTree(len(idx))
        for k, i in enumerate(idx):
            t.insert(_p[i], k)
        t.balance()
        arbres[f] = (t, idx)
    # ═══ TOUS LES COUPLES, ET DANS LES DEUX SENS ═══
    #
    # Ma liste n'en tenait que 9 sur 15, et ne comptait chaque couple que dans
    # UN sens. Mesuré par l'agent qui a audité ce code : `ring/pinky` rend 0
    # dans le sens que je testais et **403** dans l'autre, et `thumb/pinky` —
    # jamais examiné — vaut 556 dans la pose qui met justement le pouce contre
    # l'auriculaire. Au total ma sonde voyait 672 traversées sur 3 009, soit
    # 22 %. Elle écrivait « aucune auto-intersection » sur des centaines de
    # sommets traversants.
    #
    # « A dans B » et « B dans A » ne sont pas la même question : la surface
    # qui pénètre n'est pas forcément celle dont on part.
    trouve = []
    fams = [f for f in ("thumb", "index", "middle", "ring", "pinky", "hand")
            if f in arbres]
    for _x in range(len(fams)):
        for _y in range(_x + 1, len(fams)):
            fa, fb = fams[_x], fams[_y]
            n_ded = 0
            for _sens in ((fa, fb), (fb, fa)):
                _src, _dst = _sens
                tb_, ib = arbres[_dst]
                for i in par_groupe[_src]:
                    co, k, d = tb_.find(_p[i])
                    j = ib[k]
                    if (d < 0.008
                            and (_p[j] - _p[i]).dot(_n[j]) > PROFONDEUR_MINIMALE
                            and (_p_rep[i] - _p_rep[j]).length
                            > ECART_REPOS_MINIMAL):
                        n_ded += 1
            if n_ded:
                trouve.append({"entre": f"{fa}/{fb}", "sommets_dedans": n_ded})
    return trouve


# ═══ CALIBRER LA SONDE AVANT DE LIRE SON VERDICT ═══
# Un doigt qui se plie COMPRIME sa peau palmaire : c'est normal, pas un
# pincement. Sans repère, je prendrais un pli pour un défaut. On mesure donc la
# compression sur une pose franche mais saine — le poing — pour savoir ce que
# vaut « normal » sur ce maillage.

# ═══ ON VÉRIFIE LA SONDE AVANT DE LIRE SES VERDICTS ═══
# Une main au repos, doigts écartés, ne s'auto-traverse nulle part. Si la sonde
# y trouve quoi que ce soit, elle mesure autre chose que ce qu'elle prétend.
regler()
_p_repos_global, _ = sommets_evalues()
_faux_positifs = intersections("Hand_Neutral")
print("ATLAS_SONDE_INTERSECTION " + json.dumps(
    {"au_repos": _faux_positifs or "aucune",
     "verdict": "utilisable" if not _faux_positifs else "FAUX POSITIFS"},
    ensure_ascii=False))
if _faux_positifs:
    raise RuntimeError(f"sonde d'intersection non fiable : {_faux_positifs}")

# La contre-épreuve du seuil : une fermeture pleine SANS écartement fait
# franchement se traverser les doigts. Si la tolérance y voyait peu de chose,
# elle masquerait de vrais défauts et serait à jeter.
regler(Fist=1.0)
_verif_seuil = sum(x["sommets_dedans"] for x in intersections("controle"))
print("ATLAS_CONTRE_EPREUVE_DU_SEUIL " + json.dumps(
    {"fermeture_pleine_sans_ecartement": _verif_seuil,
     "verdict": "le seuil voit les vraies traversées" if _verif_seuil > 100
                else "SEUIL TROP PERMISSIF"}, ensure_ascii=False))
regler()
if _verif_seuil <= 100:
    raise RuntimeError("la tolérance de pénétration masque de vraies traversées")

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

# Le côté palmaire, mesuré par le mouvement : en fléchissant, les bouts des
# doigts partent du côté de la paume. Le signe d'une normale construite ne se
# suppose pas.
regler()
_pa_r, _ = sommets_evalues()
regler(Fist=0.5)
_pb_r, _ = sommets_evalues()
regler()
_bts_r = [i for i, n in _dom.items() if n.endswith(f"_03{SIDE}")]
_dep_r = sum(((_pb_r[i] - _pa_r[i]) for i in _bts_r), mathutils.Vector((0, 0, 0)))
PALMAIRE_REF[0] = (_dep_r - AXE * _dep_r.dot(AXE)).normalized()

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


# ═══ LE CONTACT SE MESURE LÀ OÙ IL A LIEU ═══
#
# Ma mesure précédente prenait la distance minimale entre deux ENSEMBLES de
# sommets, puis la moyenne de TOUTES leurs normales. Ces deux grandeurs ne
# parlent pas du même endroit : la moyenne d'une pulpe entière peut annoncer
# une belle orientation pendant que la zone réellement en regard se présente de
# travers. C'est ainsi que « −0,70 » cohabitait avec un contact douteux.
#
# On identifie donc d'abord le point le plus proche, puis on ne mesure que
# LE PATCH autour de lui : sa distance, ses normales locales, son étendue, et
# la pénétration éventuelle.
RAYON_PATCH = 0.005          # 5 mm autour du point de contact
# (`_p_repos_global` est relevé plus haut, avec la vérification de la sonde
# d'intersection. La ligne de garde que j'avais mise ici l'écrasait par None :
# elle venait APRÈS l'affectation réelle.)


def mesurer_contact(a, b):
    _p, _n = sommets_evalues()
    if not EMP[a] or not EMP[b]:
        return None
    arbre = mathutils.kdtree.KDTree(len(EMP[b]))
    for k, i in enumerate(EMP[b]):
        arbre.insert(_p[i], k)
    arbre.balance()
    meilleur = min(((arbre.find(_p[i])[2], i) for i in EMP[a]))
    d, i_a = meilleur
    i_b = EMP[b][arbre.find(_p[i_a])[1]]
    centre = (_p[i_a] + _p[i_b]) / 2.0
    pa = [i for i in EMP[a] if (_p[i] - centre).length < RAYON_PATCH]
    pb = [i for i in EMP[b] if (_p[i] - centre).length < RAYON_PATCH]
    if not pa or not pb:
        pa, pb = [i_a], [i_b]
    na = sum((_n[i] for i in pa), mathutils.Vector((0, 0, 0)))
    nb = sum((_n[i] for i in pb), mathutils.Vector((0, 0, 0)))
    face = (na.normalized().dot(nb.normalized())
            if na.length > 1e-9 and nb.length > 1e-9 else 1.0)
    # Pénétration : un sommet de A est DANS B s'il se trouve du mauvais côté de
    # la surface de B, en son point le plus proche.
    dedans = 0
    for i in EMP[a]:
        co, k, dd = arbre.find(_p[i])
        j = EMP[b][k]
        if (dd < 0.006 and (_p[j] - _p[i]).dot(_n[j]) > PROFONDEUR_MINIMALE
                and (_p_repos_global[i] - _p_repos_global[j]).length
                > ECART_REPOS_MINIMAL):
            dedans += 1
    # Étendue du contact : combien de couples à moins de 1,5 mm.
    serres = sum(1 for i in EMP[a] if arbre.find(_p[i])[2] < 0.0015)
    return {"distance_mm": d * 1000.0, "face_local": face,
            "sommets_du_patch": len(pa) + len(pb),
            "sommets_a_moins_de_1_5_mm": serres, "penetration": dedans}


def ecart_empreintes(a, b):
    m = mesurer_contact(a, b)
    return (None, None) if m is None else (m["distance_mm"] / 1000.0,
                                           m["face_local"])


# ═══ UN OPTIMISEUR DE CONTACT, GÉNÉRIQUE ═══
# La recherche précédente n'existait que pour la pince auriculaire-pouce, si
# bien que `Hand_Pinch` et `Hand_OK` n'étaient que des réglages posés à la main
# — et ils laissaient 29,8 et 32,8 mm entre le pouce et l'index. Une pose qui
# porte le nom d'un geste doit produire ce geste.
def poser_etat(props, os_=None):
    for pb in rig.pose.bones:
        if pb.name.startswith("CTRL_"):
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (0.0, 0.0, 0.0)
    for nomp, _d, _mi, _ma in PROPS:
        pbh[nomp] = float(props.get(nomp, 0.0))
    for (nom_os, ax), v in (os_ or {}).items():
        pb = rig.pose.bones[nom_os]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler[ax] = math.radians(v)
    rig.update_tag(); rig.data.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def penetration_familles(fa, fb):
    """Sommets de fa réellement DANS fb — doigts entiers, pas seulement pulpes."""
    _p, _n = sommets_evalues()
    ia = [i for i, nm in _dom.items() if famille(nm) == fa]
    ib = [i for i, nm in _dom.items() if famille(nm) == fb]
    if not ia or not ib:
        return 0
    t = mathutils.kdtree.KDTree(len(ib))
    for k, i in enumerate(ib):
        t.insert(_p[i], k)
    t.balance()
    n = 0
    for i in ia:
        co, k, d = t.find(_p[i])
        j = ib[k]
        if (d < 0.008 and (_p[j] - _p[i]).dot(_n[j]) > PROFONDEUR_MINIMALE
                and (_p_repos_global[i] - _p_repos_global[j]).length
                > ECART_REPOS_MINIMAL):
            n += 1
    return n


# ═══ CHERCHER EN DEUX TEMPS ═══
#
# Avec la barrière lexicographique seule, la pince auriculaire-pouce restait à
# 27 mm : pour approcher, le pouce doit franchir des poses où il traverse
# l'index, et une pénalité à 10⁶ lui interdit ce passage. L'optimum propre
# existe de l'autre côté d'un mur qu'il ne peut pas escalader.
#
# On cherche donc d'abord le CONTACT avec une pénalité modérée — le pouce peut
# traverser en chemin — puis on repart de cette pose pour NETTOYER, barrière
# haute. C'est la seule façon d'atteindre un optimum que la contrainte isole.
BARRIERE = [1e6]
CIBLE_DISTANCE = [0.0]      # 0 = la distance compte toujours
ANNEAU_EXIGE = [0.0]        # ouverture minimale du trou, en mm (0 = sans objet)


def optimiser_contact(doigt_a, doigt_b, axes, base_props=None, tours=13):
    """axes : liste de (« prop », nom, lo, hi) ou (« os », (nom, axe), lo, hi)."""
    def evaluer(vec):
        props = dict(base_props or {})
        os_ = {}
        for (genre, cle, _lo, _hi), v in zip(axes, vec):
            (props if genre == "prop" else os_)[cle] = v
        poser_etat(props, os_)
        m = mesurer_contact(doigt_a, doigt_b)
        if m is None:
            return 1e9, None, (props, os_)
        # Le contact d'abord, l'orientation LOCALE ensuite, la pénétration
        # rédhibitoire — c'est l'ordre que le cahier des charges impose.
        # ═══ NI PALIER, NI ANGLE MORT ═══
        # Le terme d'orientation plafonnait à −0,5 : sitôt le seuil atteint,
        # plus rien ne poussait, et Pinch comme OK se figeaient à −0,500 pile.
        # Il progresse maintenant sans palier jusqu'à −1.
        #
        # Et l'objectif ignorait tout ce qui n'était pas la pulpe : le pouce
        # pouvait traverser l'index ailleurs sans que le score s'en aperçoive.
        # On compte donc l'intersection des deux doigts ENTIERS.
        # Les intersections index/majeur échappaient à l'objectif parce qu'il
        # ne regardait que le couple visé. Une pose de pince peut être parfaite
        # entre pouce et index tout en faisant traverser deux autres doigts.
        inter = sum(x["sommets_dedans"] for x in intersections("recherche"))
        m["intersection_des_doigts"] = inter
        # Pour le « OK », le trou de l'anneau fait partie de l'objectif : sans
        # lui, l'optimiseur retombe sur un pincement, ce qu'il a fait.
        if ANNEAU_EXIGE[0]:
            m["ouverture_anneau_mm"] = ouverture_anneau()
        # ═══ CE QUI EST OBLIGATOIRE NE SE NÉGOCIE PAS ═══
        # Avec un poids fini, l'optimiseur ÉCHANGEAIT : à 400 points par
        # sommet traversé, un sommet valait 1,3 mm de contact, et il préférait
        # s'éloigner de 2,9 mm plutôt que de nettoyer deux sommets. Or
        # « aucune interpénétration » et « les pulpes se touchent » sont tous
        # deux obligatoires.
        #
        # L'ordre est donc lexicographique : aucune pose qui traverse ne peut
        # battre une pose propre, et c'est seulement parmi les poses propres
        # que la distance et l'orientation départagent.
        # En phase de nettoyage, la distance ne coûte plus rien tant qu'elle
        # tient sous la tolérance : sans quoi l'optimiseur « améliore » en
        # s'éloignant, ce qu'il a fait quatre fois de suite.
        _d_eff = (max(0.0, m["distance_mm"] - CIBLE_DISTANCE[0])
                  if CIBLE_DISTANCE[0] else m["distance_mm"])
        sc = ((inter + m["penetration"]) * BARRIERE[0]
              + _d_eff * 300.0
              + max(0.0, m["distance_mm"] - 1.0) * 9000.0
              + (m["face_local"] + 1.0) * 2500.0
              - min(m["sommets_a_moins_de_1_5_mm"], 120) * 2.0
              + (max(0.0, ANNEAU_EXIGE[0] - m.get("ouverture_anneau_mm", 0.0))
                 * 400.0 if ANNEAU_EXIGE[0] else 0.0))
        return sc, m, (props, os_)

    # ═══ PLUSIEURS GRAINES, PAS UNE ═══
    # Une descente partie du seul milieu s'enferme : c'est ce qui a fait passer
    # la pince auriculaire-pouce de 2,47 à 28,8 mm quand l'espace de recherche a
    # changé. On sème sur les fractions de chaque plage et on garde la meilleure
    # avant d'affiner.
    graines = []
    for _f in (0.25, 0.5, 0.75, 1.0):
        graines.append([lo + (hi - lo) * _f for _g, _c, lo, hi in axes])
    graines.append([lo + (hi - lo) * (0.8 if _i % 2 else 0.35)
                    for _i, (_g, _c, lo, hi) in enumerate(axes)])
    best = None
    for g in graines:
        r = evaluer(g)
        if best is None or r[0] < best[0]:
            best = r + (list(g),)
    pas = [(hi - lo) / 3.0 for _g, _c, lo, hi in axes]
    for _t in range(tours):
        bouge = False
        for i in range(len(axes)):
            for signe in (-1.0, 1.0):
                v = list(best[3])
                v[i] = max(axes[i][2], min(axes[i][3], v[i] + signe * pas[i]))
                r = evaluer(v)
                if r[0] < best[0]:
                    best = r + (v,)
                    bouge = True
        if not bouge:
            pas = [x * 0.5 for x in pas]
    # ═══ ON REPOSE LA POSE RETENUE ET ON LA REMESURE ═══
    # Le score annonçait zéro traversée là où le contrôle final en comptait 31.
    # Un optimiseur qui rend une mesure prise dans un autre état que celui qu'il
    # livre est un optimiseur qui ment. On rejoue donc son résultat.
    props_f, os_f = best[2]
    poser_etat(props_f, os_f)
    m_f = mesurer_contact(doigt_a, doigt_b)
    i_f = sum(x["sommets_dedans"] for x in intersections("verification"))
    m_f["intersection_des_doigts"] = i_f
    if abs(m_f["distance_mm"] - best[1]["distance_mm"]) > 0.01 or \
            i_f != best[1].get("intersection_des_doigts"):
        print("ATLAS_ECART_OPTIMISEUR " + json.dumps(
            {"pendant_la_recherche": {k: best[1].get(k) for k in
                                      ("distance_mm", "intersection_des_doigts")},
             "apres_repose": {"distance_mm": round(m_f["distance_mm"], 2),
                              "intersection_des_doigts": i_f}},
            ensure_ascii=False))
    return m_f, best[2], best[3]


def chercher_contact(doigt_a, doigt_b, axes, base_props=None):
    """Deux temps : approcher, puis nettoyer sans lâcher le contact."""
    BARRIERE[0] = 60.0                      # le pouce peut traverser en chemin
    m1, etat1, v1 = optimiser_contact(doigt_a, doigt_b, axes, base_props, tours=10)
    # ═══ LA BARRIÈRE DE NETTOYAGE EST HAUTE, PAS INFINIE ═══
    # À 10⁶, un unique sommet marginal valait plus que tout le contact : la
    # phase 2 abandonnait un appui à 0,86 mm pour aller à 16 mm. Bornée à
    # 20 000, une traversée vaut 2 mm d'écart — assez pour être chassée en
    # priorité, pas assez pour justifier de lâcher la pince. Le critère
    # d'acceptation final, lui, reste strict : zéro.
    BARRIERE[0] = 20000.0
    CIBLE_DISTANCE[0] = 1.0
    # On repart de la pose approchée : les graines de `optimiser_contact`
    # partiraient de loin et retomberaient dans le même piège.
    axes_serres = [(g, c, max(lo, v - (hi - lo) * 0.22),
                    min(hi, v + (hi - lo) * 0.22))
                   for (g, c, lo, hi), v in zip(axes, v1)]
    m2, etat2, v2 = optimiser_contact(doigt_a, doigt_b, axes_serres,
                                      base_props, tours=18)
    CIBLE_DISTANCE[0] = 0.0
    BARRIERE[0] = 1e6
    print("ATLAS_DEUX_TEMPS " + json.dumps(
        {"contact": f"{doigt_a}/{doigt_b}",
         "apres_approche_mm": round(m1["distance_mm"], 2),
         "traversees_apres_approche": m1.get("intersection_des_doigts"),
         "apres_nettoyage_mm": round(m2["distance_mm"], 2),
         "traversees_apres_nettoyage": m2.get("intersection_des_doigts")},
        ensure_ascii=False))
    return m2, etat2, v2


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
    # Là encore, plus de part de Fist : l'opposition n'est pilotée que par sa
    # propre commande.
    driver(_mth, _ax, f"opp * {math.radians(_deg):.6f}",
           {"opp": "Thumb_Opposition"})
bpy.context.view_layer.update()

# ═══ LE CREUX DE LA PAUME SE MESURE ═══
# `Hand_Cupped` était jugée à l'œil, et le client la trouve trop plate. Le creux
# est la flèche de la paume : de combien sa surface palmaire s'enfonce sous le
# plan qui passe par le poignet et les quatre jointures. Une paume plate rend
# une flèche presque nulle.
def creux_palmaire():
    _p, _ = sommets_evalues()
    _paume = [i for i, n in _dom.items() if n.endswith(f"_meta{SIDE}")]
    if not _paume:
        return 0.0
    _plan = [ANATOMIE[n]["jointure"] for n in NOMS4] + [poignet]
    _c = sum(_plan, mathutils.Vector((0, 0, 0))) / len(_plan)
    _nrm = ((ANATOMIE["index"]["jointure"] - poignet)
            .cross(ANATOMIE["pinky"]["jointure"] - poignet)).normalized()
    if _nrm.dot(PALMAIRE_REF[0]) < 0:
        _nrm = -_nrm
    return max(0.0, max((_c - _p[i]).dot(_nrm) for i in _paume)) * 1000.0


# ═══ UN NETTOYEUR DE POSE, GÉNÉRIQUE ═══
# Le client relève des pénétrations dans Hand_Fist_75, Hand_Point et
# Hand_Cupped — des poses que je posais à la main sans jamais les contrôler.
# Elles gardent leur INTENTION (les propriétés voulues) et reçoivent les plus
# PETITES corrections FK qui suppriment les traversées : un nettoyage, pas une
# réécriture.
def nettoyer_pose(nom_pose, props, axes, tours=9, bonus=None):
    def evaluer(vec):
        os_ = {cle: v for (_g, cle, _lo, _hi), v in zip(axes, vec)}
        poser_etat(props, os_)
        inter = sum(x["sommets_dedans"] for x in intersections(nom_pose))
        ecart = sum(abs(v) for v in vec) / max(1, len(vec))
        sc = inter * 1e5 + ecart * 12.0
        if bonus is not None:
            sc += bonus()
        return sc, inter, os_

    milieu = [0.0] * len(axes)
    best = evaluer(milieu) + (list(milieu),)
    pas = [(hi - lo) / 4.0 for _g, _c, lo, hi in axes]
    for _t in range(tours):
        bouge = False
        for i in range(len(axes)):
            for signe in (-1.0, 1.0):
                v = list(best[3])
                v[i] = max(axes[i][2], min(axes[i][3], v[i] + signe * pas[i]))
                r = evaluer(v)
                if r[0] < best[0]:
                    best = r + (v,)
                    bouge = True
        if not bouge:
            pas = [x * 0.55 for x in pas]
    print(f"ATLAS_NETTOYAGE {nom_pose} : {best[1]} sommets traversants")
    return best[2], best[1]


# ── LES TROIS CONTACTS, CHACUN CHERCHÉ POUR LUI-MÊME ──
IDX = [("prop", "Index_Curl", 0.0, 1.0),
       ("prop", "Thumb_Curl", 0.0, 1.0),
       ("prop", "Thumb_Opposition", 0.0, 1.0),
       ("prop", "Cup", 0.0, 0.6),
       ("prop", "Spread", -0.6, 0.6),
       ("os", (f"CTRL_index_01{SIDE}", 0), -40.0, 40.0),
       ("os", (f"CTRL_index_02{SIDE}", 0), -40.0, 40.0),
       ("os", (f"CTRL_thumb_01{SIDE}", 0), -35.0, 35.0),
       ("os", (f"CTRL_thumb_02{SIDE}", 0), -35.0, 35.0),
       ("os", (f"CTRL_thumb_meta{SIDE}", 0), -30.0, 30.0),
       ("os", (f"CTRL_thumb_meta{SIDE}", 2), -30.0, 30.0),
       # Les trois doigts libres doivent pouvoir s'écarter du chemin : sans
       # eux dans les axes, l'index traversait le majeur sans que rien ne
       # puisse le corriger.
       ("prop", "Middle_Curl", 0.0, 0.5),
       ("prop", "Ring_Curl", 0.0, 0.5),
       ("prop", "Pinky_Curl", 0.0, 0.5)]
PKY = [# Pour rejoindre l'auriculaire, le pouce traverse la paume : il passe donc
       # devant l'index et le majeur. Sans eux dans les axes, rien ne pouvait
       # les écarter de son chemin, et la recherche fuyait à 31 mm faute de
       # pose propre à courte distance.
       # Pour laisser passer le pouce, l'index et le majeur doivent pouvoir se
       # replier COMPLÈTEMENT : bridés à 0,7, ils restaient en travers de son
       # chemin et 29 sommets continuaient de se traverser.
       ("prop", "Index_Curl", 0.75, 1.0),
       ("prop", "Middle_Curl", 0.75, 1.0),
       ("os", (f"CTRL_index_02{SIDE}", 0), -35.0, 35.0),
       ("os", (f"CTRL_middle_01{SIDE}", 0), -35.0, 35.0),
       ("prop", "Pinky_Curl", 0.0, 1.0),
       ("prop", "Ring_Curl", 0.0, 0.8),
       ("prop", "Thumb_Curl", 0.0, 1.0),
       ("prop", "Thumb_Opposition", 0.0, 1.0),
       ("prop", "Cup", 0.0, 1.0),
       ("os", (f"CTRL_pinky_01{SIDE}", 0), -35.0, 35.0),
       ("os", (f"CTRL_pinky_02{SIDE}", 0), -35.0, 35.0),
       ("os", (f"CTRL_thumb_01{SIDE}", 0), -35.0, 35.0),
       ("os", (f"CTRL_thumb_02{SIDE}", 0), -35.0, 35.0),
       ("os", (f"CTRL_thumb_meta{SIDE}", 0), -45.0, 45.0),
       ("os", (f"CTRL_thumb_meta{SIDE}", 1), -45.0, 45.0),
       ("os", (f"CTRL_thumb_meta{SIDE}", 2), -45.0, 45.0),
       ("os", (f"CTRL_index_01{SIDE}", AXE_ECART), -20.0, 20.0),
       ("os", (f"CTRL_middle_01{SIDE}", AXE_ECART), -20.0, 20.0),
       ("os", (f"CTRL_pinky_01{SIDE}", AXE_ECART), -20.0, 20.0)]

# ═══ PINCH ET OK NE SONT PAS LE MÊME GESTE ═══
#
# Ils partageaient les mêmes axes et le même fond : le rapport leur donnait la
# même course et la même distance de contact, et les rendus étaient
# superposables. Ce n'était pas une coïncidence, c'était la même optimisation
# lancée deux fois.
#
#   PINCH : pulpe contre pulpe, index MODÉRÉMENT fléchi, les trois autres
#           doigts relâchés. Le geste de saisir une petite chose.
#   OK    : le pouce et l'index forment un ANNEAU lisible, donc l'index
#           s'enroule DAVANTAGE, et les trois autres restent ouverts.
#
# Ce qui distingue l'anneau du pincement se mesure : c'est son trou. Dans un
# « OK », les segments PROXIMAUX du pouce et de l'index restent écartés pendant
# que leurs pulpes se touchent ; dans un pincement, ils se rapprochent tous.
def ouverture_anneau():
    _p, _ = sommets_evalues()
    _a1 = [i for i, n in _dom.items() if n == f"DEF_thumb_01{SIDE}"]
    _b1 = [i for i, n in _dom.items() if n in (f"DEF_index_01{SIDE}",
                                               f"DEF_index_02{SIDE}")]
    if not _a1 or not _b1:
        return 0.0
    t = mathutils.kdtree.KDTree(len(_b1))
    for k, i in enumerate(_b1):
        t.insert(_p[i], k)
    t.balance()
    return min(t.find(_p[i])[2] for i in _a1) * 1000.0


PINCH = [("prop", "Index_Curl", 0.20, 0.55),
         ("prop", "Thumb_Curl", 0.0, 0.7),
         ("prop", "Thumb_Opposition", 0.3, 1.0),
         ("prop", "Relax", 0.25, 0.55),
         ("os", (f"CTRL_index_01{SIDE}", 0), -30.0, 30.0),
         ("os", (f"CTRL_thumb_01{SIDE}", 0), -35.0, 35.0),
         ("os", (f"CTRL_thumb_02{SIDE}", 0), -35.0, 35.0),
         ("os", (f"CTRL_thumb_meta{SIDE}", 0), -30.0, 30.0),
         ("os", (f"CTRL_thumb_meta{SIDE}", 1), -30.0, 30.0),
         ("os", (f"CTRL_thumb_meta{SIDE}", 2), -30.0, 30.0)]
ANNEAU = [("prop", "Index_Curl", 0.62, 1.0),
          ("prop", "Thumb_Curl", 0.0, 0.55),
          ("prop", "Thumb_Opposition", 0.4, 1.0),
          ("prop", "Spread", 0.0, 0.8),
          ("os", (f"CTRL_index_01{SIDE}", 0), -30.0, 20.0),
          ("os", (f"CTRL_index_02{SIDE}", 0), -20.0, 30.0),
          ("os", (f"CTRL_thumb_01{SIDE}", 0), -35.0, 35.0),
          ("os", (f"CTRL_thumb_02{SIDE}", 0), -35.0, 35.0),
          ("os", (f"CTRL_thumb_meta{SIDE}", 0), -35.0, 35.0),
          ("os", (f"CTRL_thumb_meta{SIDE}", 1), -35.0, 35.0),
          ("os", (f"CTRL_thumb_meta{SIDE}", 2), -35.0, 35.0)]

CONTACTS = {}
for _nom_c, _a, _b, _axes, _fond in (
        # Pincement : les trois autres doigts relâchés, pas enroulés.
        ("Hand_Pinch", "index", "thumb", PINCH, {}),
        # Anneau : les trois autres restent ouverts, et l'index s'enroule plus.
        ("Hand_OK", "index", "thumb", ANNEAU, {"Middle_Curl": 0.06,
                                               "Ring_Curl": 0.05,
                                               "Pinky_Curl": 0.04}),
        # Le pouce ne peut rejoindre l'auriculaire qu'en passant AU-DESSUS de
        # doigts repliés : tant que l'index et le majeur restent tendus, il se
        # faufile à travers eux et 39 sommets se traversent. On oriente donc la
        # recherche vers cette famille de solutions au lieu de la laisser
        # explorer celles où l'index barre le chemin.
        ("Hand_Pinky_Thumb", "pinky", "thumb", PKY,
         {"Index_Curl": 0.95, "Middle_Curl": 0.95})):
    ANNEAU_EXIGE[0] = 16.0 if _nom_c == "Hand_OK" else 0.0
    _m, _etat, _v = chercher_contact(_a, _b, _axes, _fond)
    ANNEAU_EXIGE[0] = 0.0
    CONTACTS[_nom_c] = {"mesure": _m, "props": _etat[0], "os": _etat[1]}
    dire(f"contact_{_nom_c}", {
        "entre": f"{_a} et {_b}",
        "distance_mm": round(_m["distance_mm"], 2),
        "orientation_locale": round(_m["face_local"], 3),
        "sommets_du_patch": _m["sommets_du_patch"],
        "sommets_a_moins_de_1_5_mm": _m["sommets_a_moins_de_1_5_mm"],
        "penetration": _m["penetration"]})
    exiger(f"{_nom_c} · les pulpes se touchent",
           _m["distance_mm"] <= 1.0, f'{_m["distance_mm"]:.2f} mm', "≤ 1,00 mm")
    exiger(f"{_nom_c} · les pulpes se font face",
           _m["face_local"] <= -0.5, round(_m["face_local"], 3), "≤ −0,50")
    exiger(f"{_nom_c} · aucune interpénétration",
           _m["penetration"] == 0, _m["penetration"], "0 sommet")

POSE_PINCE = CONTACTS["Hand_Pinky_Thumb"]["props"]
dire("pince_auriculaire_pouce", {
    "ecart_des_empreintes_mm": round(
        CONTACTS["Hand_Pinky_Thumb"]["mesure"]["distance_mm"], 2),
    "se_font_face": round(
        CONTACTS["Hand_Pinky_Thumb"]["mesure"]["face_local"], 3)})

# ── H.4 · LA SÉQUENCE DE VALIDATION ──
# ═══ LA DIVERGENCE NE PASSERA PAS PAR UN DRIVER ═══
#
# Trois tentatives, trois échecs silencieux : produit de deux variables, puis
# expression linéaire, puis renommage de la variable. Le driver restait
# `is_valid = false` pendant que ses voisins du même os fonctionnaient, et la
# rotation ne bougeait pas d'un degré — sans le moindre message.
#
# Je cesse d'insister sur ce chemin. Le tutoriel prévoit explicitement que
# l'automatisme se combine à une CORRECTION FK MANUELLE sur les contrôleurs, et
# ce mécanisme-là marche. La divergence devient donc un axe de recherche comme
# les autres : l'optimiseur trouvera de combien écarter les doigts pour que la
# fermeture cesse de les faire se traverser.
DIVERGENCE_RETENUE = 0.0

# ═══ D'OÙ VIENNENT LES TRAVERSÉES DU POING ? ═══
#
# L'optimiseur du pouce ne ment pas : sa mesure après repose colle à celle de
# la recherche. Les 28 traversées existent donc dans TOUTES les poses de pouce
# essayées — ce n'est pas le pouce qui échoue. On mesure les quatre doigts
# SEULS, sans pouce, à différentes fermetures : si la main se traverse déjà
# sans lui, l'amplitude de fermeture est trop forte pour ce maillage, et c'est
# un fait sur le maillage, pas un réglage à forcer.
_diag_poing = {}
for _f in (0.6, 0.7, 0.8, 0.9, 1.0):
    regler(Fist=_f)
    _ii = intersections(f"fist{_f}")
    _diag_poing[_f] = {"total": sum(x["sommets_dedans"] for x in _ii),
                       "detail": _ii}
regler()
dire("traversees_des_quatre_doigts_seuls", _diag_poing)
# On retient la fermeture la plus franche qui reste propre : le tutoriel range
# « Fist = 1 provoque une intersection massive » dans les défauts interdits,
# donc la fermeture réaliste de CE maillage est celle que la mesure désigne.
FERMETURE = max([f for f, v in _diag_poing.items() if v["total"] == 0] or [0.6])
dire("fermeture_retenue", {
    "valeur": FERMETURE,
    "raison": "la plus franche qui ne traverse pas, mesurée sans le pouce"})

# ═══ HAND_FIST EST CHERCHÉE, PLUS POSÉE À LA MAIN ═══
# `Fist=1, Thumb_Curl=1, Thumb_Opposition=0.6` plaquait les trois articulations
# du pouce contre leurs butées. Le pouce d'un poing ne se referme pas : il
# ENVELOPPE, sa pulpe venant se poser sur la face dorso-latérale de l'index et
# du majeur. On cherche donc ce contact-là, sans jamais dépasser les butées.
_AXES_POING = [
    # La fermeture elle-même est cherchée : mesurée, elle fait se traverser les
    # quatre doigts dès 0,7. Le tutoriel range « Fist = 1 provoque une
    # intersection massive » dans les défauts interdits, donc la fermeture
    # réaliste de CE maillage est celle que la mesure désigne, pas 1,0 par
    # principe.
    ("prop", "Fist", 0.55, 1.0),
    # Et l'écartement des quatre doigts pendant la fermeture : c'est lui qui
    # les empêche de se pénétrer, et il se cherche sur les contrôleurs.
    ("os", (f"CTRL_index_01{SIDE}", AXE_ECART), -14.0, 14.0),
    ("os", (f"CTRL_middle_01{SIDE}", AXE_ECART), -14.0, 14.0),
    ("os", (f"CTRL_ring_01{SIDE}", AXE_ECART), -14.0, 14.0),
    ("os", (f"CTRL_pinky_01{SIDE}", AXE_ECART), -14.0, 14.0)]
_m_poing, _etat_poing, _ = chercher_contact(
    "thumb", "index",
    _AXES_POING + [("prop", "Thumb_Curl", 0.0, 0.8),
     ("prop", "Thumb_Opposition", 0.0, 0.9),
     # Le pouce d'un poing passe PAR L'EXTÉRIEUR : il lui faut de l'amplitude
     # pour contourner, pas seulement pour se replier.
     ("os", (f"CTRL_thumb_meta{SIDE}", 0), -45.0, 45.0),
     ("os", (f"CTRL_thumb_meta{SIDE}", 1), -60.0, 60.0),
     ("os", (f"CTRL_thumb_meta{SIDE}", 2), -45.0, 45.0),
     ("os", (f"CTRL_thumb_01{SIDE}", 0), -40.0, 40.0),
     ("os", (f"CTRL_thumb_02{SIDE}", 0), -40.0, 40.0)],
    {})
POSE_POING = (_etat_poing[0], _etat_poing[1])
dire("pouce_du_poing", {
    "distance_a_l_index_mm": round(_m_poing["distance_mm"], 2),
    "penetration": _m_poing["penetration"],
    "reglages": {k: round(v, 3) for k, v in POSE_POING[0].items() if v},
    "corrections_fk_deg": {f"{k[0]}[{k[1]}]": round(v, 1)
                           for k, v in POSE_POING[1].items()}})

POSES = [
    ("Hand_Neutral", {}, {}),
    ("Hand_Relaxed", {"Relax": 1.0}, {}),
    ("Hand_Open", {"Spread": 1.0}, {}),
    ("Hand_Spread_Min", {"Spread": -1.0}, {}),
    ("Hand_Fist", POSE_POING[0], POSE_POING[1]),
    ("Hand_Fist_25", {"Fist": 0.25}, {}),
    ("Hand_Fist_50", {"Fist": 0.5}, {}),
    ("Hand_Fist_75", {"Fist": 0.75}, {}),
    ("Hand_Point", {"Middle_Curl": 1.0, "Ring_Curl": 1.0, "Pinky_Curl": 1.0,
                    "Thumb_Curl": 0.5, "Thumb_Opposition": 0.35}, {}),
    ("Hand_Pinch", CONTACTS["Hand_Pinch"]["props"],
     CONTACTS["Hand_Pinch"]["os"]),
    ("Hand_OK", CONTACTS["Hand_OK"]["props"], CONTACTS["Hand_OK"]["os"]),
    ("Hand_Cupped", {"Cup": 1.0}, {}),
    ("Hand_Pinky_Thumb", CONTACTS["Hand_Pinky_Thumb"]["props"],
     CONTACTS["Hand_Pinky_Thumb"]["os"]),
]
# ═══ TOUTES LES POSES SONT NETTOYÉES, PAS SEULEMENT LES QUATRE CONTRÔLÉES ═══
# Le client relève des pénétrations dans Hand_Fist_75, Hand_Point et
# Hand_Cupped. Elles y étaient parce que le validateur ne regardait que quatre
# poses : ce qu'on ne mesure pas, on ne le corrige pas.
AXES_NETTOYAGE = []
for _n4 in NOMS4:
    AXES_NETTOYAGE += [("os", (f"CTRL_{_n4}_01{SIDE}", AXE_ECART), -16.0, 16.0),
                       ("os", (f"CTRL_{_n4}_01{SIDE}", 0), -18.0, 18.0),
                       ("os", (f"CTRL_{_n4}_02{SIDE}", 0), -20.0, 20.0)]
DEJA_CHERCHEES = {"Hand_Pinch", "Hand_OK", "Hand_Pinky_Thumb", "Hand_Fist"}
_poses_propres = []
for nom_pose, reglages, os_pose in POSES:
    poser_etat(reglages, os_pose)
    _n_int = sum(x["sommets_dedans"] for x in intersections(nom_pose))
    if _n_int and nom_pose not in DEJA_CHERCHEES:
        # Le creux de la paume entre dans l'objectif de Hand_Cupped : la
        # nettoyer sans lui la rendrait propre ET plate.
        _bonus = ((lambda: -creux_palmaire() * 90.0)
                  if nom_pose == "Hand_Cupped" else None)
        _os2, _reste = nettoyer_pose(nom_pose, reglages, AXES_NETTOYAGE,
                                     bonus=_bonus)
        os_pose = {**os_pose, **_os2}
    _poses_propres.append((nom_pose, reglages, os_pose))
POSES = _poses_propres

_controle = {}
for nom_pose, reglages, os_pose in POSES:
    poser_etat(reglages, os_pose)
    _p, _n = sommets_evalues()
    _dep = max((a - b).length for a, b in zip(_repos, _p)) * 1000
    d_pi, f_pi = ecart_empreintes("pinky", "thumb")
    d_ix, f_ix = ecart_empreintes("index", "thumb")
    _inter = intersections(nom_pose)
    _controle[nom_pose] = {
        "course_max_mm": round(_dep, 1),
        "auriculaire_au_pouce_mm": round(d_pi * 1000, 1) if d_pi is not None else None,
        "index_au_pouce_mm": round(d_ix * 1000, 1) if d_ix is not None else None,
        "auto_intersections": _inter}
    if nom_pose == "Hand_Pinky_Thumb" and _inter:
        # On ne retente pas à l'aveugle : on regarde QUELS os portent les
        # sommets qui se traversent. Le « pouce » inclut son éminence thénar,
        # une masse de la paume voisine de la base de l'index — si les
        # traversées sont là, ce n'est pas un doigt qui en traverse un autre.
        _pp, _nn = sommets_evalues()
        _ia = [i for i, nm in _dom.items() if famille(nm) == "thumb"]
        _ib = [i for i, nm in _dom.items() if famille(nm) == "index"]
        _tt = mathutils.kdtree.KDTree(len(_ib))
        for _k, _i in enumerate(_ib):
            _tt.insert(_pp[_i], _k)
        _tt.balance()
        _ou = {}
        for _i in _ia:
            _co, _k, _d = _tt.find(_pp[_i])
            _j = _ib[_k]
            if (_d < 0.008 and (_pp[_j] - _pp[_i]).dot(_nn[_j]) > PROFONDEUR_MINIMALE
                    and (_p_repos_global[_i] - _p_repos_global[_j]).length
                    > ECART_REPOS_MINIMAL):
                _ou[f"{_dom[_i]} → {_dom[_j]}"] = _ou.get(
                    f"{_dom[_i]} → {_dom[_j]}", 0) + 1
        print("ATLAS_OU_CA_TRAVERSE " + json.dumps(_ou, ensure_ascii=False))
    # Toutes les poses, sans exception : le validateur n'en épargnait que
    # quatre, et les neuf autres n'étaient donc jamais contrôlées.
    exiger(f"{nom_pose} · aucune auto-intersection",
           not _inter, _inter or "aucune", "aucune")
regler()
dire("poses_de_validation", _controle)

# ═══ LES TRANSITIONS, PAS SEULEMENT LES POSES FINALES ═══
# Une pose finale sans collision ne prouve rien si les doigts se traversent au
# milieu du geste. On échantillonne le chemin depuis le repos.
_POSES_D = {n: (pr, o) for n, pr, o in POSES}
_transitions = {}
for _cible in ("Hand_Fist", "Hand_Point", "Hand_Pinch", "Hand_OK",
               "Hand_Cupped", "Hand_Pinky_Thumb"):
    if _cible not in _POSES_D:
        continue
    _pr, _o = _POSES_D[_cible]
    _fautes_t = {}
    for _k in range(11):
        _u = _k / 10.0
        poser_etat({kk: vv * _u for kk, vv in _pr.items()},
                   {kk: vv * _u for kk, vv in _o.items()})
        _it = intersections(f"{_cible}@{_u}")
        if _it:
            _fautes_t[f"{_u:.1f}"] = _it
    _transitions[f"Neutral→{_cible}"] = _fautes_t or "aucune collision"
    exiger(f"transition Neutral→{_cible} · aucune auto-intersection",
           not _fautes_t, _fautes_t or "aucune", "aucune à chaque étape")
regler()
dire("transitions", _transitions)

# ═══ PINCH ET OK DOIVENT ÊTRE DEUX GESTES ═══
# Ils rendaient exactement la même course et la même distance : c'était la même
# optimisation lancée deux fois. On mesure leur écart au lieu de l'espérer.
if "Hand_Pinch" in _POSES_D and "Hand_OK" in _POSES_D:
    poser_etat(*_POSES_D["Hand_Pinch"])
    _pp1, _ = sommets_evalues()
    _anneau_pinch = ouverture_anneau()
    poser_etat(*_POSES_D["Hand_OK"])
    _pp2, _ = sommets_evalues()
    _anneau_ok = ouverture_anneau()
    _ecart_gestes = max((a - b).length for a, b in zip(_pp1, _pp2)) * 1000
    regler()
    dire("pinch_contre_ok", {
        "ecart_maximal_entre_les_deux_poses_mm": round(_ecart_gestes, 1),
        "ouverture_de_l_anneau_pinch_mm": round(_anneau_pinch, 1),
        "ouverture_de_l_anneau_ok_mm": round(_anneau_ok, 1)})
    exiger("Pinch et OK sont deux gestes distincts", _ecart_gestes > 15.0,
           f"{_ecart_gestes:.1f} mm", "> 15 mm d'écart")
    exiger("l'anneau du OK est lisible", _anneau_ok >= 14.0,
           f"{_anneau_ok:.1f} mm", "≥ 14 mm d'ouverture")

# ═══ LA PAUME DOIT VRAIMENT SE CREUSER ═══
if "Hand_Cupped" in _POSES_D:
    regler()
    _creux_repos = creux_palmaire()
    poser_etat(*_POSES_D["Hand_Cupped"])
    _creux_cup = creux_palmaire()
    regler()
    dire("creux_de_la_paume", {"au_repos_mm": round(_creux_repos, 1),
                               "en_paume_creuse_mm": round(_creux_cup, 1),
                               "gain_mm": round(_creux_cup - _creux_repos, 1)})
    exiger("la paume creuse se creuse vraiment",
           _creux_cup - _creux_repos >= 6.0,
           f"{_creux_cup - _creux_repos:.1f} mm", "≥ 6 mm de plus qu'au repos")

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

    # ═══ UNE MATIÈRE QUI NE CACHE RIEN ═══
    # Les rendus précédents étaient trop clairs : volumes, plis et
    # intersections y devenaient illisibles. Une argile grise moyenne, plus
    # rugueuse, révèle les jointures au lieu de les noyer.
    peau = bpy.data.materials.new("argile")
    peau.use_nodes = True
    _bs = peau.node_tree.nodes["Principled BSDF"]
    _bs.inputs["Base Color"].default_value = (0.46, 0.45, 0.44, 1.0)
    _bs.inputs["Roughness"].default_value = 0.62
    if "Specular IOR Level" in _bs.inputs:
        _bs.inputs["Specular IOR Level"].default_value = 0.35
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

    def rendre(nom_pose, plan, direction, cadre=0.205, vise_sur=None):
        for o in [x for x in bpy.data.objects if x.type in ("CAMERA", "LIGHT", "EMPTY")]:
            bpy.data.objects.remove(o, do_unlink=True)
        _p, _ = sommets_evalues()
        # On vise la MAIN, pas le bras : les sommets tenus par DEF_hand
        # appartiennent au moignon d'avant-bras, et les inclure repoussait la
        # main dans un coin du cadre.
        if vise_sur is not None:
            vise = vise_sur
        else:
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
        # ═══ UNE EXPOSITION QUI LAISSE VOIR ═══
        # À 30 W, tout partait en blanc : plis, volumes et intersections
        # devenaient invisibles, ce que le tutoriel interdit expressément. La
        # puissance suit maintenant le carré de la distance, si bien qu'un gros
        # plan n'est pas plus brûlé qu'un plan large.
        _dist = max(0.18, recul * 0.55)
        _k = (_dist / 0.45) ** 2
        for _v, _e in ((direction.normalized() * 0.6 + N * 0.5, 7.0),
                       (direction.normalized() * 0.5 - T * 0.7, 2.6),
                       (-direction.normalized() * 0.4 + AXE * 0.6, 1.7)):
            ld = bpy.data.lights.new("l", "AREA")
            ld.energy = _e * _k
            ld.size = 0.35 * min(1.0, _dist / 0.45)
            ol = bpy.data.objects.new("l", ld)
            bpy.context.collection.objects.link(ol)
            ol.location = vise + _v.normalized() * _dist
            cl = ol.constraints.new("TRACK_TO"); cl.target = cible
        sc.render.filepath = os.path.join(DOSSIER, f"{nom_pose}-{plan}.png")
        bpy.ops.render.render(write_still=True)

    # Les treize poses obligatoires, sous les quatre angles.
    for nom_pose, reglages, os_pose in POSES:
        poser_etat(reglages, os_pose)
        for plan, direction in PLANS.items():
            rendre(nom_pose, plan, direction)
        print(f"ATLAS_RENDU {nom_pose} — 4 plans")
    # Gros plans des trois contacts critiques et de la zone qui échoue.
    for nom_pose, reglages, os_pose in POSES:
        if nom_pose not in ("Hand_Pinch", "Hand_OK", "Hand_Pinky_Thumb",
                            "Hand_Fist"):
            continue
        poser_etat(reglages, os_pose)
        # Le gros plan doit montrer le CONTACT : viser le centre de la main
        # cadrait la paume et ratait ce qu'on voulait juger.
        _a, _b = (("pinky", "thumb") if nom_pose == "Hand_Pinky_Thumb"
                  else ("index", "thumb"))
        _pv, _ = sommets_evalues()
        _t = mathutils.kdtree.KDTree(len(EMP[_b]))
        for _k2, _i2 in enumerate(EMP[_b]):
            _t.insert(_pv[_i2], _k2)
        _t.balance()
        _d2, _ia = min(((_t.find(_pv[i])[2], i) for i in EMP[_a]))
        _cible_gp = (_pv[_ia] + _pv[EMP[_b][_t.find(_pv[_ia])[1]]]) / 2.0
        for plan, direction in (("paume", PLANS["paume"]),
                                ("pouce", PLANS["pouce"])):
            rendre(f"gros-plan-{nom_pose}", plan, direction, cadre=0.055,
                   vise_sur=_cible_gp)
        print(f"ATLAS_GROS_PLAN {nom_pose}")
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
poser_etat(*POSE_POING)
compression_stats = {f: compression(DEF[f][-1]) for f in NOMS4 + ["thumb"]}
dire("compression_au_poing", compression_stats)
_calibre = {f: compression_stats[f]["min"] for f in ("thumb", "pinky", "index")}
poser_etat(CONTACTS["Hand_Pinky_Thumb"]["props"],
           CONTACTS["Hand_Pinky_Thumb"]["os"])
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

poser_etat(CONTACTS["Hand_Pinky_Thumb"]["props"],
           CONTACTS["Hand_Pinky_Thumb"]["os"])
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
# ═══ LES DEUX DERNIERS SOMMETS ═══
# Le critère en exige zéro. Deux, c'est peu — mais « peu » n'est pas « zéro »,
# et un critère qu'on arrondit ne sert plus à rien. On les nomme avant de les
# corriger, pour que la correction soit vérifiable.
_restants = []
for v in geo.data.vertices:
    gs = [(g.weight, _gnom.get(g.group, "")) for g in v.groups if g.weight > 0.01]
    if not gs:
        continue
    fams = {famille(n) for _w, n in gs if not n.endswith(f"_meta{SIDE}")} - {"hand"}
    if len(fams) > 1 and min((pts[v.index] - _c).length
                             for _c in COMMISSURES) >= 0.022:
        _restants.append({"sommet": v.index,
                          "position_mm": [round(x * 1000, 1) for x in pts[v.index]],
                          "groupes": sorted(n for _w, n in gs)})
if _restants:
    print("ATLAS_SOMMETS_CONTAMINES " + json.dumps(_restants, ensure_ascii=False))
    for r_ in _restants:
        v = geo.data.vertices[r_["sommet"]]
        gs = [(g.weight, _gnom.get(g.group, "")) for g in v.groups if g.weight > 0.01]
        _ph = [(w, n) for w, n in gs if not n.endswith(f"_meta{SIDE}")
               and n != f"DEF_hand{SIDE}"]
        _garde = famille(max(_ph)[1])
        for _w, n in _ph:
            if famille(n) != _garde:
                _gr[n].remove([v.index])
    bpy.ops.object.select_all(action="DESELECT")
    geo.select_set(True)
    bpy.context.view_layer.objects.active = geo
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    _gnom = {g.index: g.name for g in geo.vertex_groups}
    _dom = {}
    for v in geo.data.vertices:
        gs = [(g.weight, _gnom.get(g.group, "")) for g in v.groups if g.weight > 0.01]
        if gs:
            _dom[v.index] = max(gs)[1]

r_contam_final = _ailleurs
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
for nom_pose, reglages, os_pose in POSES:
    poser_etat(reglages, os_pose)
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

# ═══ LA PORTE ═══
# Elle n'existait pas : le script écrivait `"reussi": false` puis sauvegardait
# et annonçait « terminé ». Désormais un seul critère faux interdit d'écraser
# le .blend validé, écrit un rapport d'échec, et sort en code non nul.
exiger("retour exact au repos", _ecart_retour < 0.01,
       f"{_ecart_retour:.4f} mm", "< 0,01 mm")
exiger("aucune contamination hors des commissures",
       r_contam_final == 0, r_contam_final, "0 sommet")
for _f in NOMS4 + ["thumb"]:
    _c = compression_stats.get(_f)
    if _c:
        exiger(f"compression de {_f} au poing · minimum",
               _c["min"] >= 0.25, _c["min"], "≥ 0,25")
        exiger(f"compression de {_f} au poing · percentile 1 %",
               _c["p1"] >= 0.50, _c["p1"], "≥ 0,50")
_drv_ko = [d.data_path for d in (rig.animation_data.drivers if rig.animation_data else [])
           if not d.driver.is_valid]
exiger("tous les drivers sont valides", not _drv_ko, _drv_ko or "aucun invalide",
       "aucun invalide")

NON_VALIDE = [False]
rapport["criteres_echoues"] = ECHECS_ACCEPTATION
if ECHECS_ACCEPTATION:
    with open(os.path.join(DOSSIER, "rapport-echec.json"), "w",
              encoding="utf-8") as f:
        json.dump({"echecs": ECHECS_ACCEPTATION, "mesures": rapport},
                  f, ensure_ascii=False, indent=2)
    print("\nATLAS_NON_LIVRABLE — "
          f"{len(ECHECS_ACCEPTATION)} critère(s) obligatoire(s) en échec :")
    for e in ECHECS_ACCEPTATION:
        print(f"  · {e['critere']} — mesuré {e['mesure']}, exigé {e['seuil']}")
    print("Le .blend validé n'est PAS remplacé ; le rig en cours est écrit "
          "sous un nom qui dit son état.")
    NON_VALIDE[0] = True

_blend = os.path.join(
    DOSSIER, f"RIG_Hand{SIDE}{'-NON-VALIDE' if NON_VALIDE[0] else ''}.blend")
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
if NON_VALIDE[0]:
    print("\nATLAS_NON_LIVRABLE — le rig n'est PAS validé. "
          "Les rendus et le rapport sont écrits pour que le défaut soit "
          "visible et repris par quelqu'un d'autre.")
    for e in ECHECS_ACCEPTATION:
        print(f"  · {e['critere']} — mesuré {e['mesure']}, exigé {e['seuil']}")
    with open(os.path.join(DOSSIER, f"rapport-rig{SIDE}.json"), "w",
              encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    sys.exit(2)

print("ATLAS_TERMINE " + json.dumps(
    {"rapport": f"rapport-rig{SIDE}.json", "blend": os.path.basename(_blend),
     "poses": len(_bibliotheque)}, ensure_ascii=False))
