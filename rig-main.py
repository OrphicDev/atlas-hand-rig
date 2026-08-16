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
from contextlib import contextmanager

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
import mesures_paume                # noqa: E402
import correctifs                   # noqa: E402
sys.path.insert(0, os.path.join(RACINE, "outils"))
import anneau                       # noqa: E402
import eclairage                    # noqa: E402

portillon.exiger("humain-rig-main")

args = sys.argv[sys.argv.index("--") + 1:]
DOSSIER = args[0]
QUI = args[1] if len(args) > 1 else "homme"
COTE = args[2] if len(args) > 2 else "g"
MOIGNON = float(args[3]) / 1000.0 if len(args) > 3 else 0.110
SANS_RENDU = "mesure" in args
SIDE = ".L" if COTE == "g" else ".R"
os.makedirs(DOSSIER, exist_ok=True)

# ═══ UN MODE CIBLÉ, PARCE QU'UNE RECONSTRUCTION COMPLÈTE COÛTE DEUX HEURES ═══
#
# Mesuré : la reconstruction complète en mode `mesure` prend 53 min seule sur la
# machine, et plus de deux heures dès que le nettoyage des transitions entre en
# jeu. Apprendre quoi que ce soit sur `Cup` en payant deux heures par essai est
# impossible — c'est ce qui a fait que `Cup` n'a jamais été éprouvé.
#
# `focus=` s'arrête dès que la question posée a sa réponse. Le fichier qu'il
# produit n'a JAMAIS le droit de s'appeler valide : il existe pour apprendre
# vite, et toute correction retenue doit être rejouée par `focus=all`.
FOCUS = "all"
for _arg in args:
    if _arg.startswith("focus="):
        FOCUS = _arg.split("=", 1)[1].strip().lower()


def en_focus(*noms):
    return FOCUS == "all" or FOCUS in noms

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

# ═══ LA CONSERVATION DE VOLUME EST UN CHOIX, DONC ELLE SE MESURE ═══
#
# `use_deform_preserve_volume` fait passer la déformation en quaternions duaux
# au lieu d'une interpolation linéaire de matrices. Elle évite une part de
# l'écrasement aux articulations — l'effet « saucisse » que le cahier interdit.
#
# Ce n'est PAS un substitut aux poids ni aux correctifs, et ce n'est pas une
# case à cocher par principe : la déformation par quaternions duaux gonfle les
# vrilles là où la linéaire les écrase. Le réglage est donc figé par un test
# A/B mesuré (plus bas), et plus jamais touché une fois les shape keys créées —
# sinon leurs deltas, sculptés sur une déformation, s'appliqueraient à une autre.
MODIF_ARMATURE = next(m for m in geo.modifiers
                      if m.type == "ARMATURE" and m.object == rig)
MODIF_ARMATURE.use_deform_preserve_volume = True
MODIF_ARMATURE.show_in_editmode = True
MODIF_ARMATURE.show_on_cage = True


def forcer_evaluation(quoi=None):
    """La seule façon de lire un maillage à jour en mode fond.

    ═══ LES DRIVERS NE S'ÉVALUENT PAS SANS CHANGEMENT D'IMAGE ═══
    Sans ces quatre lignes on mesure une main IMMOBILE — et une main immobile
    revient toujours exactement à sa pose de repos, donc elle passe tous les
    contrôles. C'est le piège le plus coûteux de ce dépôt, et il a été payé
    plusieurs fois. Une seule fonction, appelée partout, pour qu'il ne puisse
    plus être oublié à un endroit.
    """
    o = quoi if quoi is not None else rig
    o.update_tag()
    o.data.update_tag()
    _sc = bpy.context.scene
    _sc.frame_set(_sc.frame_current)
    bpy.context.view_layer.update()


@contextmanager
def drivers_rotation_mutes(noms_os):
    """Taire les drivers de rotation le temps de sonder leurs canaux.

    ═══ UN DRIVER RÉÉCRIT SA VOIE ═══
    Mesuré, et j'y suis tombé : en posant une rotation à la main sur un axe
    piloté par `Cup`, on obtient +0,00 sur TOUTES les grandeurs et on conclut
    « cet axe ne fait rien ». Le driver efface la valeur avant qu'elle soit
    mesurée. Seul un axe non piloté répond, ce qui rend le tableau parfaitement
    cohérent ET parfaitement faux.

    L'appelant DOIT contre-éprouver : si taire n'a rien changé, c'est qu'on
    n'atteint pas le canal qu'on prétend tester.
    """
    chemins = {f'pose.bones["{n}"].rotation_euler' for n in noms_os}
    fcs = [fc for fc in (rig.animation_data.drivers
                         if rig.animation_data else [])
           if fc.data_path in chemins]
    etat = [(fc, fc.mute) for fc in fcs]
    try:
        for fc in fcs:
            fc.mute = True
        forcer_evaluation()
        yield len(fcs)
    finally:
        for fc, ancien in etat:
            fc.mute = ancien
        forcer_evaluation()


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
         ("Cup", 0.0, 0.0, 1.0), ("Relax", 0.0, 0.0, 1.0),
         # ═══ LES DEUX PROPRIÉTÉS CORRECTIVES DU §7.1 ═══
         # Elles ne servent QUE aux derniers millimètres des deux contacts qui
         # ne se règlent pas par la pose. Elles font partie de PROPS, donc
         # `regler()` et `poser_etat()` les remettent à zéro dès qu'on ne les
         # demande pas — sans quoi un correctif sculpté pour une pose
         # contaminerait toutes les autres.
         ("PSD_PinkyThumb", 0.0, 0.0, 1.0), ("PSD_OK", 0.0, 0.0, 1.0)]
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

# ═══ LA DIVERGENCE EXISTAIT DANS LE CODE ET NE PILOTAIT RIEN ═══
#
# `DIVERGENCE` est écrit depuis le chat 1, avec son commentaire expliquant que
# les doigts s'écartent en se fermant — c'est ce qui les empêche de se
# pénétrer. Mais aucun driver ne le lisait : la constante était morte, et la
# fermeture reposait entièrement sur des corrections FK cherchées pose par
# pose. D'où des doigts qui se traversent 820 fois dès `Fist = 0,7`.
#
# On l'ajoute au driver d'écartement, en SOMME LINÉAIRE — jamais en produit de
# deux variables, l'évaluateur de Blender échouerait en silence. Et son signe
# se mesure, pour la même raison que celui de l'écartement : sur la main
# droite, le repère est inversé.
_essai_div = {}
for _s in (+1.0, -1.0):
    poser_os({f"MCH_{_n}_01_result{SIDE}": (0.0, 0.0, _s * DIVERGENCE[_n] * 10.0)
              for _n in NOMS4})
    _essai_div[_s] = eventail_des_bouts(sommets_evalues()[0])
au_repos()
SIGNE_DIVERGENCE = max(_essai_div, key=lambda s: sum(_essai_div[s].values()))
_gain_div = {c: _essai_div[SIGNE_DIVERGENCE][c] - _eventail_repos[c]
             for c in _eventail_repos}
dire("sens_de_la_divergence", {
    "eventail_a_plus_DIVERGENCE_mm": {c: round(v, 2)
                                      for c, v in _essai_div[+1.0].items()},
    "eventail_a_moins_DIVERGENCE_mm": {c: round(v, 2)
                                       for c, v in _essai_div[-1.0].items()},
    "signe_retenu": SIGNE_DIVERGENCE,
    "gain_du_sens_retenu_mm": {c: round(v, 2) for c, v in _gain_div.items()},
    "regle": "diverger en fermant doit ÉCARTER les bouts de doigts voisins"})
if abs(sum(_essai_div[+1.0].values())
       - sum(_essai_div[-1.0].values())) < 1.0:
    raise RuntimeError("les deux sens de divergence rendent le même éventail : "
                       "la sonde ne mesure pas ce qu'elle prétend")
_div_muet = [c for c, g in _gain_div.items() if g <= 0.5]
if _div_muet:
    raise RuntimeError(f"la divergence ne sépare pas {_div_muet} : {_gain_div}")

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
           f"spread * {SIGNE_ECART * math.radians(ECART[nom]):.6f}"
           f" + fist * {SIGNE_DIVERGENCE * math.radians(K_DIVERGENCE[0] * DIVERGENCE[nom]):.6f}",
           {"spread": "Spread", "fist": "Fist"})
# Le creusement agit sur les MÉTACARPIENS, faiblement côté index, fortement côté
# auriculaire. C'est lui qui rapproche l'auriculaire du pouce — le cerclage
# rouge de Sacha.
# ═══ CREUSER, C'EST DEUX MOUVEMENTS — ET AUCUN N'ÉTAIT LE BON ═══
#
# Mesuré sur le rig de `b17e548`, `Cup` de 0 à 1 :
#
#     flèche de l'arc     29,99 → 19,10 mm   (−10,89)  l'arc S'APLATIT
#     largeur de paume    71,99 → 86,03 mm   (+14,04)  la paume S'ÉLARGIT
#     pouce ↔ auriculaire 102,27 → 99,13 → 101,39      3 mm, puis ça repart
#
# Creuser la paume l'ÉLARGISSAIT. Et `creux_palmaire()` annonçait +0,98 mm,
# donc un progrès : il prend le maximum de profondeur sous un plan FIGÉ à la
# pose de repos, qu'un splay augmente aussi. Il ne se trompait pas d'amplitude,
# il se trompait de SENS sur le phénomène.
#
# Éprouvé ensuite axe par axe, drivers tus :
#
#     axe  angle   Δlargeur   Δarc   Δpouce-auriculaire
#       0    +20     +6,20   −8,88        −8,36     ← le sens qu'employait CUP
#       0    −20     +1,42   +8,00        +5,02
#       1    ±20      0,00     ∓2          0,00     ← CUP_AXIAL ne servait à RIEN
#       2    −20    −13,19   −0,19       −10,35     ← piloté par PERSONNE
#
# Un creusement fait DEUX choses, et une seule ne suffit pas : il VOÛTE (la
# flèche transverse augmente) et il RESSERRE (la largeur diminue, et le 5ᵉ rayon
# se rapproche du pouce — le cerclage rouge de Sacha). La flexion des phalanges
# n'est ni l'une ni l'autre.
#
# Les deux axes, leurs signes et leurs amplitudes ne sont donc plus écrits : ils
# sont ÉLUS par la mesure, comme le sens de l'écartement. Sur la main droite le
# repère est inversé et ces élections retomberont d'elles-mêmes.
CUP_VOUTE = {"index": 0.05, "middle": 0.20, "ring": 0.60, "pinky": 1.00}
CUP_CONVERGENCE = {"index": 0.00, "middle": 0.10, "ring": 0.55, "pinky": 1.00}
META_CUP = [f"MCH_{_n}_meta_result{SIDE}" for _n in NOMS4]
PALMAIRE_CUP = mesures_paume.direction_palmaire(rig, geo, SIDE, _dom)
_SOMMETS_PAUME = mesures_paume.paume_sans_le_pouce(_dom, SIDE)
au_repos()
_tetes0 = mesures_paume.tetes_metacarpiennes(rig, SIDE)
REF_CUP = {
    "arc_mm": mesures_paume.arc_transverse(sommets_evalues()[0], _tetes0,
                                           PALMAIRE_CUP, _SOMMETS_PAUME),
    "largeur_mm": mesures_paume.largeur_paume(_tetes0),
    "pouce_auriculaire_mm": mesures_paume.pouce_auriculaire(_tetes0)}


def _mesurer_meta(axe, degres, facteurs):
    """Pose les quatre métacarpiens sur un axe local et mesure la paume."""
    poser_os({f"MCH_{_n}_meta_result{SIDE}":
              tuple(degres * facteurs[_n] if k == axe else 0.0
                    for k in range(3))
              for _n in NOMS4})
    _t = mesures_paume.tetes_metacarpiennes(rig, SIDE)
    _p = sommets_evalues()[0]
    return {"arc_mm": mesures_paume.arc_transverse(_p, _t, PALMAIRE_CUP,
                                                   _SOMMETS_PAUME),
            "largeur_mm": mesures_paume.largeur_paume(_t),
            "pouce_auriculaire_mm": mesures_paume.pouce_auriculaire(_t)}


_AMPLITUDES = (4.0, 8.0, 12.0, 16.0, 20.0, 24.0)
_essais_cup = []
for _axe in (0, 1, 2):
    for _signe in (+1.0, -1.0):
        for _amp in _AMPLITUDES:
            _r = _mesurer_meta(_axe, _signe * _amp, CUP_VOUTE)
            _rc = _mesurer_meta(_axe, _signe * _amp, CUP_CONVERGENCE)
            _essais_cup.append({
                "axe": _axe, "signe": _signe, "amplitude_deg": _amp,
                "gain_arc_mm": _r["arc_mm"] - REF_CUP["arc_mm"],
                "gain_largeur_mm": _rc["largeur_mm"] - REF_CUP["largeur_mm"],
                "gain_pouce_auriculaire_mm": (_rc["pouce_auriculaire_mm"]
                                              - REF_CUP["pouce_auriculaire_mm"])})
au_repos()

# ═══ UNE SONDE QUI NE PEUT PAS ÉCHOUER NE PROUVE RIEN ═══
# Si aucun axe ne déplace la paume, on ne pilote rien et toute élection serait
# un tirage au sort présenté comme une mesure.
if max(abs(e["gain_largeur_mm"]) for e in _essais_cup) < 0.5:
    raise RuntimeError("aucun axe métacarpien ne déplace la paume : la sonde "
                       "de creusement n'atteint pas les os qu'elle tourne")

# Voûte : le plus grand gain de flèche, à la plus petite amplitude à gain égal.
_voute = max(_essais_cup,
             key=lambda e: (round(e["gain_arc_mm"], 2), -e["amplitude_deg"]))
# Convergence : la plus forte BAISSE de largeur, puis le meilleur rapprochement
# pouce–auriculaire, puis la plus petite amplitude.
_conv = min(_essais_cup,
            key=lambda e: (round(e["gain_largeur_mm"], 2),
                           round(e["gain_pouce_auriculaire_mm"], 2),
                           e["amplitude_deg"]))
AXE_VOUTE, SIGNE_VOUTE = _voute["axe"], _voute["signe"]
CUP_VOUTE_DEG = _voute["amplitude_deg"]
AXE_CONVERGENCE, SIGNE_CONVERGENCE = _conv["axe"], _conv["signe"]
CUP_CONVERGENCE_DEG = _conv["amplitude_deg"]
dire("cup_axes_elus", {
    "reference": {k: round(v, 2) for k, v in REF_CUP.items()},
    "voute": {"axe": AXE_VOUTE, "signe": SIGNE_VOUTE,
              "amplitude_deg": CUP_VOUTE_DEG,
              "gain_arc_mm": round(_voute["gain_arc_mm"], 2)},
    "convergence": {"axe": AXE_CONVERGENCE, "signe": SIGNE_CONVERGENCE,
                    "amplitude_deg": CUP_CONVERGENCE_DEG,
                    "gain_largeur_mm": round(_conv["gain_largeur_mm"], 2),
                    "gain_pouce_auriculaire_mm": round(
                        _conv["gain_pouce_auriculaire_mm"], 2)},
    "regle": "voûter = augmenter la flèche ; resserrer = diminuer la largeur"})
if _voute["gain_arc_mm"] <= 0.5:
    raise RuntimeError(f"aucun axe ne VOÛTE la paume : {_voute}")
if _conv["gain_largeur_mm"] >= -0.5:
    raise RuntimeError(f"aucun axe ne RESSERRE la paume : {_conv}")

for nom in NOMS4:
    _m = f"MCH_{nom}_meta_result{SIDE}"
    _a_voute = math.radians(CUP_VOUTE_DEG * CUP_VOUTE[nom] * SIGNE_VOUTE)
    _a_conv = math.radians(CUP_CONVERGENCE_DEG * CUP_CONVERGENCE[nom]
                           * SIGNE_CONVERGENCE)
    # JAMAIS deux drivers sur le même index de rotation_euler : le second
    # écraserait le premier en silence. Si les deux composantes tombent sur le
    # même axe, on additionne leurs constantes avant d'en créer un seul.
    if AXE_VOUTE == AXE_CONVERGENCE:
        driver(_m, AXE_VOUTE, f"cup * {_a_voute + _a_conv:.6f}", {"cup": "Cup"})
    else:
        driver(_m, AXE_VOUTE, f"cup * {_a_voute:.6f}", {"cup": "Cup"})
        if abs(_a_conv) > 1e-6:
            driver(_m, AXE_CONVERGENCE, f"cup * {_a_conv:.6f}", {"cup": "Cup"})
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
                # ═══ UNE BUTÉE QUI ÉCRÊTE CE QU'ON PILOTE NE PROTÈGE RIEN ═══
                # Le ±8° uniforme sur Z coupait la convergence à moins de la
                # moitié des 13 mm mesurés : le driver demandait un angle que
                # la contrainte refusait, en silence. Chaque axe doit couvrir
                # ce qu'il reçoit réellement, plus 2° de marge — et jamais
                # au-delà de l'amplitude CMC déjà donnée à ce rayon, qui est
                # la seule borne anatomique que ce dépôt ait mesurée.
                _pilote = {AXE_VOUTE: CUP_VOUTE_DEG * CUP_VOUTE[nom],
                           AXE_CONVERGENCE: CUP_CONVERGENCE_DEG
                           * CUP_CONVERGENCE[nom]}
                _bornes = [list(_bx), list(_by), list(_bz)]
                for _ax, _ang in _pilote.items():
                    _req = math.radians(min(26.0, abs(_ang) + 2.0))
                    _bornes[_ax][0] = min(_bornes[_ax][0], -_req)
                    _bornes[_ax][1] = max(_bornes[_ax][1], _req)
                _bx, _by, _bz = (tuple(b) for b in _bornes)
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
    gs = [(g.weight, _gnom[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _gnom]
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


# ═══════════════════════════════════════════════════════════════════
#   F.1bis — REPEINDRE LA PAUME PAR LA GÉODÉSIQUE (§6.3 à 6.6)
# ═══════════════════════════════════════════════════════════════════
# ═══ 2 375 SOMMETS SANS PROPRIÉTAIRE, ET LE CRITÈRE NE LES VOYAIT PAS ═══
#
# Mesuré par `outils/sonde-poids-main.py` sur le rig livré : 2 375 sommets ont
# moins de 0,15 d'écart entre leurs DEUX familles dominantes. Le contrôle du
# dépôt classe par groupe dominant, donc il les range sans hésiter et les
# déclare sains — c'est le cas « 51 % index / 49 % pouce » que le cahier décrit
# en préambule de son §6.
#
#     46229 · DEF_middle_meta 0,396 vs DEF_index_meta 0,396 · écart 0,000
#     51465 · DEF_thumb_meta  0,301 vs DEF_pinky_meta  0,301 · écart 0,001
#     35497 · DEF_hand        0,322 vs DEF_thumb_meta  0,322 · commissure à 92 mm
#
# Un sommet partagé à parts égales entre le métacarpien du POUCE et celui de
# l'AURICULAIRE — les deux bords opposés de la paume — et des dizaines à plus
# de 90 mm de toute commissure, donc sans la moindre justification anatomique.
#
# Tant que la paume ne bougeait presque pas, ça ne se voyait pas. Avec un
# creusement qui la voûte de 7,3 mm et la resserre de 10,8, la même bouillie
# écrase la chair à 0,0986 de sa longueur de repos. Le cahier l'ordonne :
# poids d'abord, correctifs ensuite, jamais l'inverse.
#
# On ne repeint pas à l'œil — il n'y a pas d'interface ici. On repeint par la
# GÉODÉSIQUE, qui est la façon dont la chair est réellement reliée : chaque
# masse palmaire appartient au métacarpien dont elle est la plus proche EN
# SUIVANT LA SURFACE. Une distance euclidienne rapprocherait deux peaux qui se
# font face sans être voisines.
_META_PAUME = [f"DEF_{_n}_meta{SIDE}" for _n in NOMS4 + ["thumb"]]
_gr_pau = {g.name: g for g in geo.vertex_groups}
_gnom_p = {g.index: g.name for g in geo.vertex_groups}


def _poids_de(v):
    return {_gnom_p[g.group]: g.weight for g in v.groups
            if g.group in _gnom_p and g.weight > 0.005}


# Le NOYAU d'un métacarpien : les sommets qu'il tient sans ambiguïté. Ce sont
# eux les graines, et c'est pour ça qu'on exige un écart FRANC — semer sur un
# sommet douteux propagerait le doute au lieu de le lever.
_noyaux, _ambigus = {n: [] for n in _META_PAUME}, []
for _v in geo.data.vertices:
    _w = _poids_de(_v)
    _wm = {k: x for k, x in _w.items() if k in _META_PAUME}
    if not _wm:
        continue
    _tri = sorted(_wm.items(), key=lambda kv: -kv[1])
    if len(_tri) == 1 or _tri[0][1] - _tri[1][1] >= 0.30:
        _noyaux[_tri[0][0]].append(_v.index)
    else:
        _ambigus.append(_v.index)

# L'ordre des rayons EN TRAVERS de la paume : c'est lui qui dit quels
# métacarpiens sont voisins. Deux rayons éloignés de plus d'un rang ne
# partagent aucune chair.
_RANG_RAYON = {f"DEF_{_n}_meta{SIDE}": _i
               for _i, _n in enumerate(["thumb", "index", "middle",
                                        "ring", "pinky"])}
_adj = correctifs._adjacence_du_maillage(geo)
_dist = {}
for _b, _graines in _noyaux.items():
    if _graines:
        _dist[_b] = correctifs._dijkstra_sur_aretes(_adj, _graines, 0.090)

# ═══ UNE SONDE QUI NE PEUT PAS ÉCHOUER NE PROUVE RIEN ═══
if not _ambigus:
    print("ATLAS_REPEINTURE aucun sommet ambigu : rien à repeindre")
elif len(_dist) < 2:
    raise RuntimeError("moins de deux métacarpiens ont un noyau : la "
                       "repeinture n'aurait aucun repère pour trancher")
else:
    _repeints = 0
    for _i in _ambigus:
        _v = geo.data.vertices[_i]
        _w = _poids_de(_v)
        _wm = {k: x for k, x in _w.items() if k in _META_PAUME}
        _somme_meta = sum(_wm.values())
        # Distances géodésiques du sommet à chaque noyau. Un métacarpien que la
        # propagation n'atteint pas ne peut pas revendiquer ce sommet.
        _d = {b: _dd[_i] for b, _dd in _dist.items() if _i in _dd and b in _wm}
        if len(_d) < 2:
            continue
        # ═══ UNE MASSE PALMAIRE N'APPARTIENT QU'À DEUX RAYONS VOISINS ═══
        #
        # Premier jet : je distribuais à TOUS les métacarpiens que la
        # géodésique atteint. Mesuré, ça laissait 4 730 sommets partagés entre
        # rayons NON VOISINS — index et auriculaire sur les sommets 0 à 3.
        # Or ces deux-là ne se touchent nulle part sur une main : le sommet
        # était atteint par les deux noyaux, donc il recevait les deux, et mon
        # exposant n'y changeait rien puisqu'il opérait APRÈS.
        #
        # On ne garde que les DEUX plus proches, et seulement s'ils sont
        # voisins dans l'ordre des rayons. Sinon le plus proche prend tout : un
        # sommet que deux rayons éloignés se disputent n'a qu'un propriétaire
        # possible, le plus proche par la surface.
        _proches = sorted(_d.items(), key=lambda kv: kv[1])[:2]
        if (len(_proches) == 2
                and abs(_RANG_RAYON[_proches[0][0]]
                        - _RANG_RAYON[_proches[1][0]]) > 1):
            _proches = _proches[:1]
        _d = dict(_proches)
        # Poids ∝ 1/(d + ε)³ : l'exposant TRANCHE au lieu de moyenner. C'est
        # tout l'objet de l'opération — un sommet à 0,000 d'écart doit sortir
        # avec un propriétaire, pas avec un demi-propriétaire de plus.
        _inv = {b: 1.0 / (x + 0.002) ** 3 for b, x in _d.items()}
        _tot = sum(_inv.values())
        for _b, _x in _inv.items():
            _gr_pau[_b].add([_i], _somme_meta * _x / _tot, "REPLACE")
        # Les métacarpiens non atteints perdent leur revendication.
        for _b in _wm:
            if _b not in _inv:
                _gr_pau[_b].add([_i], 0.0, "REPLACE")
        _repeints += 1
    # ═══ SAUTER UN SOMMET QU'ON NE SAIT PAS TRANCHER, C'EST LE LAISSER FAUX ═══
    #
    # La boucle géodésique fait `continue` quand la propagation n'atteint pas
    # deux rayons. Mesuré : elle laissait 1 958 sommets partagés entre rayons
    # NON VOISINS — index et auriculaire sur les sommets 0, 1, 3 — parce
    # qu'elle les sautait au lieu de les résoudre.
    #
    # Or la règle anatomique ne dépend d'aucune propagation : une masse
    # palmaire appartient à son rayon dominant et AU PLUS à ses voisins
    # immédiats. L'index et l'auriculaire ne partagent aucune chair, quelle
    # que soit la façon dont on mesure. On l'applique donc à TOUS les sommets
    # palmaires, et la somme retirée revient au rayon dominant pour que le
    # repos ne bouge pas.
    _elagues = 0
    for _v in geo.data.vertices:
        _wm = {k: x for k, x in _poids_de(_v).items() if k in _META_PAUME}
        if len(_wm) < 2:
            continue
        _tri = sorted(_wm.items(), key=lambda kv: -kv[1])
        _dom_rayon = _RANG_RAYON[_tri[0][0]]
        _a_couper = [b for b, _x in _tri[1:]
                     if abs(_RANG_RAYON[b] - _dom_rayon) > 1]
        if not _a_couper:
            continue
        _rendu = sum(_wm[b] for b in _a_couper)
        for _b in _a_couper:
            _gr_pau[_b].add([_v.index], 0.0, "REPLACE")
        _gr_pau[_tri[0][0]].add([_v.index], _tri[0][1] + _rendu, "REPLACE")
        _elagues += 1

    bpy.context.view_layer.objects.active = geo
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.005)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    forcer_evaluation(geo)

    # ═══ JE COMPTAIS LA MAUVAISE CHOSE ═══
    #
    # Premier critère : « moins de 35 % d'ambigus restants ». Mesuré,
    # 12 329 → 5 612, soit 45 % — et il échouait. Sauf que le cahier du chat 1
    # dit lui-même que « le mélange entre métacarpiens VOISINS est demandé par
    # la règle 7 : la paume est une chair continue ». Un sommet partagé entre
    # l'index et le majeur est anatomiquement JUSTE, et mon seuil punissait la
    # continuité de la chair au lieu de punir le défaut.
    #
    # Ce qui est absurde, c'est le sommet partagé entre deux rayons NON
    # VOISINS — pouce et auriculaire, index et annulaire. Ceux-là ne se
    # touchent nulle part sur une main, et aucune règle ne les autorise.
    # C'est cela qu'on compte, et il doit tomber à zéro.
    _ORDRE = ["thumb", "index", "middle", "ring", "pinky"]
    _rang = {f"DEF_{n}_meta{SIDE}": i for i, n in enumerate(_ORDRE)}
    _voisins, _lointains, _reste = 0, [], 0
    _gnom_p = {g.index: g.name for g in geo.vertex_groups}
    for _v in geo.data.vertices:
        _wm = {k: x for k, x in _poids_de(_v).items() if k in _META_PAUME}
        _tri = sorted(_wm.items(), key=lambda kv: -kv[1])
        if len(_tri) < 2 or _tri[0][1] - _tri[1][1] >= 0.15:
            continue
        _reste += 1
        _ecart_rang = abs(_rang[_tri[0][0]] - _rang[_tri[1][0]])
        if _ecart_rang <= 1:
            _voisins += 1
        else:
            _lointains.append({"sommet": _v.index,
                               "entre": f"{_tri[0][0]} / {_tri[1][0]}",
                               "rangs_ecartes_de": _ecart_rang})
    dire("repeinture_palmaire", {
        "ambigus_avant": len(_ambigus), "repeints": _repeints,
        "elagues_rayons_eloignes": _elagues,
        "ambigus_apres": _reste,
        "dont_entre_rayons_VOISINS": _voisins,
        "dont_entre_rayons_NON_VOISINS": len(_lointains),
        "exemples_non_voisins": _lointains[:8],
        "noyaux": {b: len(v) for b, v in _noyaux.items()},
        "regle": "chaque masse palmaire appartient au métacarpien dont elle est "
                 "la plus proche EN SUIVANT LA SURFACE ; le mélange entre "
                 "rayons VOISINS est légitime, entre rayons éloignés jamais"})
    exiger("aucun sommet partagé entre deux rayons non voisins",
           not _lointains, len(_lointains), "0 sommet")


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
      gs = [(g.weight, _gnom[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _gnom]
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
    gs = [(g.weight, _gnom[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _gnom]
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
#   PHASE F.3 — LES DEUX OS CORRECTIFS DE PAUME (§7.2 à 7.4)
# ═══════════════════════════════════════════════════════════════════
# ═══ UNE POSE DÉPLACE DES OS ; UN CORRECTIF DÉPLACE DE LA CHAIR ═══
#
# `Hand_Pinky_Thumb` plafonne depuis deux chats : la recherche atteint 0,10 mm
# — donc la pose EXISTE — mais le nettoyage ne descend pas sous ~211 sommets
# traversants. Le diagnostic du chat 1 le dit déjà : ce n'est pas un doigt qui
# en traverse un autre, c'est **l'éminence thénar contre la base de l'index**,
# deux masses de la paume qui se replient l'une sur l'autre.
#
# Aucune pose ne peut résoudre ça. Deux masses de chair doivent CÉDER l'une
# devant l'autre, et un rig d'os ne sait pas faire céder de la chair. D'où ces
# deux petits os déformants, sans contrôleur : ils déplacent une masse sans
# toucher à l'intention de la pose.
#
# Ils sont créés APRÈS la repeinture — leurs poids sont TRANSFÉRÉS depuis le
# parent, jamais ajoutés, donc la somme de chaque sommet ne bouge pas et le
# repos reste exact. C'est arithmétique, pas un réglage heureux.
_ZONES = {}
try:
    # Le repos AVANT toute création : `_p_repos_global` n'existe pas encore à
    # cet endroit du pipeline (il est relevé en phase H, après le choix de la
    # déformation). S'y référer ici aurait levé un NameError à la première
    # exécution — une comparaison ne vaut que contre une origine qui existe.
    au_repos()
    _p_avant_corr, _ = sommets_evalues()
    _sha_maillage = correctifs.empreinte_maillage_basis(geo)
    _idx_thenar = [i for i, n in _dom.items() if n == f"DEF_thumb_meta{SIDE}"]
    _idx_index = [i for i, n in _dom.items() if n == f"DEF_index_meta{SIDE}"]
    if len(_idx_thenar) < 20 or len(_idx_index) < 20:
        raise RuntimeError(f"masses palmaires trop petites pour un correctif : "
                           f"thénar {len(_idx_thenar)}, base index {len(_idx_index)}")
    _ZONES = {
        "thenar": correctifs.masque_geodesique(geo, _idx_thenar, 0.018, 0.032),
        "index_root": correctifs.masque_geodesique(geo, _idx_index, 0.010, 0.022)}
    _pts_now = [geo.matrix_world @ v.co for v in geo.data.vertices]

    def _centre(masque):
        _s = sum((_pts_now[i] for i in masque), mathutils.Vector((0, 0, 0)))
        return _s / max(1, len(masque))

    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    _EB = arm.edit_bones
    correctifs.ajouter_bone_correctif(
        _EB, f"DEF_thumb_thenar_corr{SIDE}", _EB[f"DEF_thumb_meta{SIDE}"],
        _centre(_ZONES["thenar"]), PALMAIRE_CUP, T)
    correctifs.ajouter_bone_correctif(
        _EB, f"DEF_index_root_corr{SIDE}", _EB[f"DEF_index_meta{SIDE}"],
        _centre(_ZONES["index_root"]), PALMAIRE_CUP, T)
    bpy.ops.object.mode_set(mode="OBJECT")

    correctifs.transferer_vers_correctif(
        geo, _ZONES["thenar"], f"DEF_thumb_meta{SIDE}",
        f"DEF_thumb_thenar_corr{SIDE}", maximum=0.35)
    correctifs.transferer_vers_correctif(
        geo, _ZONES["index_root"], f"DEF_index_meta{SIDE}",
        f"DEF_index_root_corr{SIDE}", maximum=0.35)
    forcer_evaluation(geo)

    # ═══ LE REPOS DOIT ÊTRE INTACT, ET ON LE MESURE ═══
    # Transférer conserve la somme, donc le repos ne peut pas bouger — mais
    # « ne peut pas » n'est pas « n'a pas ». On vérifie.
    au_repos()
    _p_apres_corr, _ = sommets_evalues()
    _bouge = max((a - b).length for a, b in zip(_p_avant_corr,
                                                _p_apres_corr)) * 1000
    dire("os_correctifs", {
        "thenar": {"sommets": len(_ZONES["thenar"]),
                   "centre_mm": [round(x * 1000, 1) for x in _centre(_ZONES["thenar"])]},
        "index_root": {"sommets": len(_ZONES["index_root"]),
                       "centre_mm": [round(x * 1000, 1)
                                     for x in _centre(_ZONES["index_root"])]},
        "deplacement_du_repos_mm": round(_bouge, 5),
        "regle": "les poids sont TRANSFÉRÉS depuis le parent, jamais ajoutés"})
    exiger("les os correctifs ne déplacent pas le repos", _bouge < 0.01,
           f"{_bouge:.5f} mm", "< 0,01 mm")
    CORRECTIFS_PRETS = True
except Exception as _e:                                       # noqa: BLE001
    # On n'avale pas l'échec : on le publie et on continue sans correctifs, de
    # sorte que le rapport dise pourquoi ils manquent au lieu de les taire.
    print("ATLAS_OS_CORRECTIFS_ECHEC " + json.dumps(str(_e), ensure_ascii=False))
    dire("os_correctifs", {"echec": str(_e)})
    CORRECTIFS_PRETS = False


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


def intersections(pose_nom, familles=None):
    """Les traversées, par couple de familles.

    `familles` restreint la question à un sous-ensemble. Sans lui, on ne
    pouvait pas demander « est-ce que les quatre doigts se traversent ENTRE
    EUX ? » — la réponse incluait toujours le pouce, même immobile, même
    quand il n'était pas le sujet.
    """
    _p, _n = sommets_evalues()
    par_groupe = {}
    for i, nm in _dom.items():
        _f = famille(nm)
        if _f is not None and (familles is None or _f in familles):
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


def ou_ca_traverse():
    """Quels OS portent les sommets qui se traversent, et non quelles familles.

    « thumb/index » ne dit pas s'il s'agit de deux doigts qui se croisent ou de
    l'éminence thénar qui se replie contre la base de l'index — deux défauts
    qui ne se corrigent pas au même endroit. Ce diagnostic n'existait que pour
    `Hand_Pinky_Thumb`, écrit à la main sur un seul couple : les deux autres
    contacts se corrigeaient donc à l'aveugle. Il est ici générique, et rendu
    trié par nombre de sommets décroissant.
    """
    _p, _n = sommets_evalues()
    par = {}
    for i, nm in _dom.items():
        f = famille(nm)
        if f is not None:
            par.setdefault(f, []).append(i)
    arbres = {}
    for f, idx in par.items():
        t = mathutils.kdtree.KDTree(len(idx))
        for k, i in enumerate(idx):
            t.insert(_p[i], k)
        t.balance()
        arbres[f] = (t, idx)
    ou = {}
    fams = [f for f in ("thumb", "index", "middle", "ring", "pinky", "hand")
            if f in arbres]
    for _x in range(len(fams)):
        for _y in range(_x + 1, len(fams)):
            for _src, _dst in ((fams[_x], fams[_y]), (fams[_y], fams[_x])):
                tb_, ib = arbres[_dst]
                for i in par[_src]:
                    co, k, d = tb_.find(_p[i])
                    j = ib[k]
                    if (d < 0.008
                            and (_p[j] - _p[i]).dot(_n[j]) > PROFONDEUR_MINIMALE
                            and (_p_repos_global[i] - _p_repos_global[j]).length
                            > ECART_REPOS_MINIMAL):
                        cle = f"{_dom[i]} → {_dom[j]}"
                        ou[cle] = ou.get(cle, 0) + 1
    return dict(sorted(ou.items(), key=lambda kv: -kv[1]))


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

# ═══ PRESERVE VOLUME SE MESURE, IL NE SE COCHE PAS ═══
#
# Le cahier l'exige : figer ce choix par un test A/B AVANT toute shape key,
# parce qu'un delta sculpté sur une déformation ne vaut rien sur l'autre. La
# déformation par quaternions duaux évite l'écrasement des articulations, mais
# elle gonfle les vrilles là où l'interpolation linéaire les écrase — donc rien
# ne dit d'avance qu'elle est meilleure SUR CE MAILLAGE.
#
# On compare sur des états franchement déformés, pas au repos : au repos les
# deux méthodes coïncident par construction, et un test qui ne peut pas
# distinguer ne prouve rien.
_ETATS_AB = [("poing", {"Fist": 1.0}),
             ("paume_creuse", {"Cup": 1.0}),
             ("opposition", {"Thumb_Opposition": 1.0}),
             ("poing_et_creux", {"Fist": 0.8, "Cup": 0.8})]
_ab = {}
for _pv in (False, True):
    MODIF_ARMATURE.use_deform_preserve_volume = _pv
    forcer_evaluation(geo)
    _inter_tot, _comp_min, _comp_p1, _n_mes = 0, 1.0, 1.0, 0
    for _nom_e, _regl in _ETATS_AB:
        regler(**_regl)
        _inter_tot += sum(x["sommets_dedans"] for x in intersections(f"ab-{_nom_e}"))
        # ═══ J'AI SUPPOSÉ DEUX FOIS LA FORME DE compression() ═══
        # D'abord en lui passant `DEF[doigt]`, une LISTE, alors qu'elle prend
        # UN nom d'os : chaque doigt rendait du vide. Puis en la lisant comme
        # une suite de couples (ratio, arête) : elle rend un DICT, et itérer un
        # dict donne ses clés — d'où `too many values to unpack`. Deux fautes
        # sur la même fonction, toutes deux évitables en l'ouvrant.
        # Elle rend : min, p1, p5, mediane, aretes, arete_la_plus_comprimee.
        for _g in NOMS4 + ["thumb"]:
            for _os in DEF[_g]:
                _c = compression(_os)
                if not _c or not _c.get("aretes"):
                    continue
                _n_mes += _c["aretes"]
                _comp_min = min(_comp_min, _c["min"])
                _comp_p1 = min(_comp_p1, _c["p1"])
    regler()
    if _n_mes == 0:
        raise RuntimeError("le test A/B de Preserve Volume n'a mesuré aucune "
                           "arête : il ne peut rien trancher")
    _ab[_pv] = {"intersections": _inter_tot,
                "compression_min": round(_comp_min, 4),
                "compression_p1": round(_comp_p1, 4),
                "aretes_mesurees": _n_mes}

# Le classement est lexicographique et il suit l'ordre du cahier : d'abord les
# collisions, ensuite la compression minimale, ensuite le percentile 1 %. En
# cas d'égalité stricte, on garde True — le cahier tranche ainsi, parce que la
# conservation du volume est ce qu'on cherche.
# ═══ « TRUE SAUF SI LE RAPPORT PROUVE UNE RÉGRESSION » ═══
#
# Mon premier classement était lexicographique — collisions, puis compression,
# puis percentile — et il retenait True sur ces mesures :
#
#     sans : 11 903 traversées | compression min 0,0626 | p1 0,2759
#     avec : 11 750 traversées | compression min 0,0147 | p1 0,1388
#
# Soit 153 collisions gagnées sur 11 903 — 1,3 % — payées par une compression
# minimale QUATRE FOIS pire. 0,0147 veut dire une arête écrasée à 1,5 % de sa
# longueur de repos, quand ce dépôt exige 0,25 au minimum. Un ordre strict
# laissait donc un gain marginal dominer un effondrement de volume.
#
# La règle du cahier est plus juste et plus simple : on garde la conservation
# de volume SAUF si une grandeur stricte régresse. Ici deux régressent.
def _regresse(avec, sans):
    out = []
    for k, meilleur_si_grand in (("intersections", False),
                                 ("compression_min", True),
                                 ("compression_p1", True)):
        pire = (avec[k] < sans[k]) if meilleur_si_grand else (avec[k] > sans[k])
        if pire:
            out.append(k)
    return out


# Et une contre-épreuve du test lui-même : si les deux réglages rendent
# exactement les mêmes nombres, c'est que le modificateur n'a pas été relu — un
# test qui ne peut pas distinguer ne tranche rien.
if _ab[True] == _ab[False]:
    raise RuntimeError("Preserve Volume actif et inactif rendent des mesures "
                       f"identiques : {_ab[True]} — le test ne distingue rien")
_regressions_pv = _regresse(_ab[True], _ab[False])
PRESERVE_VOLUME = not _regressions_pv
MODIF_ARMATURE.use_deform_preserve_volume = PRESERVE_VOLUME
forcer_evaluation(geo)
regler()
dire("preserve_volume", {
    "sans": _ab[False], "avec": _ab[True], "retenu": PRESERVE_VOLUME,
    "grandeurs_qui_regressent_avec": _regressions_pv or "aucune",
    "regle": "on garde la conservation de volume SAUF si une grandeur stricte "
             "régresse ; sur ce maillage les quaternions duaux pincent plus "
             "qu'ils ne préservent",
    "gele": "ne plus toucher après création des shape keys"})

# ═══ LE REPOS SE RELÈVE APRÈS QUE LA DÉFORMATION EST CHOISIE ═══
#
# `_p_repos_global` avait été capturé plus haut, sous `Preserve Volume = True`
# — la valeur que je posais à la création du modificateur. Le test A/B le fait
# ensuite basculer à False, et la pose de repos change alors de méthode de
# déformation. Mesuré : le critère « Cup · retour exact au repos » rendait
# 0,0000 mm en `focus=cup` et 0,0401 mm dans la reconstruction complète, pour
# ce seul motif. Une origine relevée avant que l'origine soit décidée n'est pas
# une origine.
regler()
_p_repos_global, _ = sommets_evalues()

# ═══ L'AMPLITUDE SE CHERCHE SOUS CONTRAINTE DE PROPRETÉ ═══
#
# L'élection des axes (phase D) ne pouvait pas compter les traversées :
# `intersections()` n'existe qu'ici. Elle a donc classé sur le seul gain, et
# retenu la plus FORTE amplitude du balayage — 24°. Mesuré : la paume se voûte
# de +44,74 mm et se resserre de −20,61, mais elle se traverse 16 119 fois sur
# les 21 pas, propre seulement jusqu'à `Cup = 0,20`.
#
# Le cahier met `intersections > 0` en PREMIÈRE clé du classement, et il a
# raison : un gain obtenu en faisant se traverser la chair n'est pas un gain.
# Les axes et les signes élus sont justes — ils sont confirmés par deux sondes
# indépendantes — donc on ne rejoue pas l'élection : on cherche la plus GRANDE
# amplitude qui reste propre sur tout le trajet.
_DRIVERS_CUP = {}
for _fc in (rig.animation_data.drivers if rig.animation_data else []):
    for _n in NOMS4:
        if _fc.data_path == f'pose.bones["MCH_{_n}_meta_result{SIDE}"].rotation_euler':
            _DRIVERS_CUP[(_n, _fc.array_index)] = _fc
if not _DRIVERS_CUP:
    raise RuntimeError("les drivers de creusement sont introuvables : la "
                       "recherche d'amplitude ne pilote rien")


def _appliquer_cup(echelle):
    for (_n, _ax), _fc in _DRIVERS_CUP.items():
        _av = math.radians(CUP_VOUTE_DEG * echelle * CUP_VOUTE[_n] * SIGNE_VOUTE)
        _ac = math.radians(CUP_CONVERGENCE_DEG * echelle * CUP_CONVERGENCE[_n]
                           * SIGNE_CONVERGENCE)
        if AXE_VOUTE == AXE_CONVERGENCE:
            _fc.driver.expression = f"cup * {_av + _ac:.6f}"
        elif _ax == AXE_VOUTE:
            _fc.driver.expression = f"cup * {_av:.6f}"
        else:
            _fc.driver.expression = f"cup * {_ac:.6f}"
    forcer_evaluation()


def _balayer_cup():
    _out = []
    for _k in range(21):
        _c = _k / 20.0
        regler(Cup=_c)
        _t = mesures_paume.tetes_metacarpiennes(rig, SIDE)
        _p = sommets_evalues()[0]
        _out.append({
            "cup": round(_c, 2),
            "arc_mm": round(mesures_paume.arc_transverse(_p, _t, PALMAIRE_CUP,
                                                         _SOMMETS_PAUME), 2),
            "largeur_mm": round(mesures_paume.largeur_paume(_t), 2),
            "pouce_auriculaire_mm": round(mesures_paume.pouce_auriculaire(_t), 2),
            "intersections": sum(x["sommets_dedans"]
                                 for x in intersections(f"cup{_c:.2f}"))})
    regler()
    return _out


_recherche_amplitude = {}
CUP_ECHELLE = None
for _e in (1.0, 0.85, 0.7, 0.55, 0.45, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1):
    _appliquer_cup(_e)
    _bal = _balayer_cup()
    _it = sum(x["intersections"] for x in _bal)
    _g_arc = _bal[-1]["arc_mm"] - _bal[0]["arc_mm"]
    _g_lar = _bal[-1]["largeur_mm"] - _bal[0]["largeur_mm"]
    _recherche_amplitude[_e] = {"intersections": _it,
                                "gain_arc_mm": round(_g_arc, 2),
                                "gain_largeur_mm": round(_g_lar, 2)}
    print(f"ATLAS_CUP_AMPLITUDE échelle={_e:.2f} "
          f"traversées={_it:6d} arc={_g_arc:+6.2f} largeur={_g_lar:+6.2f}")
    if _it == 0:
        CUP_ECHELLE = _e
        break
if CUP_ECHELLE is None:
    # On garde la plus petite essayée : la construction échouera au critère, et
    # c'est ce qu'elle doit faire — mais elle ira au bout et livrera ses mesures
    # au lieu de mourir ici.
    CUP_ECHELLE = 0.1
_appliquer_cup(CUP_ECHELLE)
dire("cup_amplitude_cherchee", {
    "recherche": {str(k): v for k, v in _recherche_amplitude.items()},
    "echelle_retenue": CUP_ECHELLE,
    "voute_deg_effectif": round(CUP_VOUTE_DEG * CUP_ECHELLE, 2),
    "convergence_deg_effectif": round(CUP_CONVERGENCE_DEG * CUP_ECHELLE, 2),
    "regle": "la plus GRANDE amplitude qui ne fait se traverser la paume à "
             "aucun des 21 pas"})

# ═══ LE BALAYAGE DE CUP, ET SES SEPT CRITÈRES ═══
#
# Vingt et un pas, et on juge le TRAJET autant que l'arrivée : une paume qui
# atteindrait la bonne forme en passant par une mauvaise ne serait pas creuse,
# elle serait chanceuse. Le chat 2 a mesuré un pouce–auriculaire qui se
# rapproche jusqu'à `Cup = 0,5` puis REPART — c'est exactement ce qu'un
# contrôle sur la seule arrivée ne peut pas voir.
_balayage_cup = _balayer_cup()
regler()
_p_apres_cup, _ = sommets_evalues()
_retour_cup = max((a - b).length for a, b in zip(_p_repos_global,
                                                 _p_apres_cup)) * 1000

_c0, _c1 = _balayage_cup[0], _balayage_cup[-1]
_recul_largeur = max((_balayage_cup[i + 1]["largeur_mm"]
                      - _balayage_cup[i]["largeur_mm"])
                     for i in range(len(_balayage_cup) - 1))
_recul_arc = max((_balayage_cup[i]["arc_mm"] - _balayage_cup[i + 1]["arc_mm"])
                 for i in range(len(_balayage_cup) - 1))
_inter_cup = sum(e["intersections"] for e in _balayage_cup)
dire("balayage_cup", {
    "pas": _balayage_cup,
    "gain_arc_mm": round(_c1["arc_mm"] - _c0["arc_mm"], 2),
    "gain_largeur_mm": round(_c1["largeur_mm"] - _c0["largeur_mm"], 2),
    "gain_pouce_auriculaire_mm": round(_c1["pouce_auriculaire_mm"]
                                       - _c0["pouce_auriculaire_mm"], 2),
    "pire_recul_de_largeur_mm": round(_recul_largeur, 2),
    "pire_recul_de_fleche_mm": round(_recul_arc, 2),
    "intersections_totales": _inter_cup,
    "retour_au_repos_mm": round(_retour_cup, 4)})
exiger("Cup · la paume se voûte", _c1["arc_mm"] - _c0["arc_mm"] >= 6.0,
       f'{_c1["arc_mm"] - _c0["arc_mm"]:+.2f} mm', "≥ +6 mm de flèche")
exiger("Cup · la paume se resserre", _c1["largeur_mm"] - _c0["largeur_mm"] <= -6.0,
       f'{_c1["largeur_mm"] - _c0["largeur_mm"]:+.2f} mm', "≤ −6 mm de largeur")
exiger("Cup · l'auriculaire rejoint le pouce",
       _c1["pouce_auriculaire_mm"] - _c0["pouce_auriculaire_mm"] <= -4.0,
       f'{_c1["pouce_auriculaire_mm"] - _c0["pouce_auriculaire_mm"]:+.2f} mm',
       "≤ −4 mm")
exiger("Cup · le resserrement ne repart jamais en arrière",
       _recul_largeur <= 0.5, f"{_recul_largeur:+.2f} mm", "≤ 0,50 mm par pas")
exiger("Cup · la voûte ne s'effondre jamais en chemin",
       _recul_arc <= 0.5, f"{_recul_arc:+.2f} mm", "≤ 0,50 mm par pas")
exiger("Cup · aucune auto-intersection sur les 21 pas",
       _inter_cup == 0, _inter_cup, "0 sommet")
exiger("Cup · retour exact au repos", _retour_cup < 0.01,
       f"{_retour_cup:.4f} mm", "< 0,01 mm")

if not en_focus("all"):
    # ═══ UN FICHIER DE FOCUS N'EST JAMAIS VALIDE ═══
    # Il existe pour apprendre vite, pas pour livrer. Son nom le dit, et le
    # rapport aussi, pour qu'aucune relecture ultérieure ne s'y trompe.
    with open(os.path.join(DOSSIER, f"rapport-focus-{FOCUS}.json"), "w",
              encoding="utf-8") as _f:
        json.dump(rapport, _f, ensure_ascii=False, indent=2)
    _wip = os.path.join(DOSSIER, f"WIP-focus-{FOCUS}-NON-VALIDE.blend")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(_wip))
    print(f"ATLAS_FOCUS_TERMINE {FOCUS} → {_wip}")
    print(f"\n{len(ECHECS_ACCEPTATION)} critère(s) obligatoire(s) en échec.")
    sys.exit(2 if ECHECS_ACCEPTATION else 0)

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
# ═══ LA RECHERCHE OPTIMISE EXACTEMENT LE CRITÈRE QUI LA JUGE ═══
# Ces deux seuils étaient écrits en clair à DEUX endroits : dans le score de
# l'optimiseur et dans les `exiger` qui prononcent le verdict. Deux copies d'un
# même nombre finissent toujours par diverger, et une recherche qui vise autre
# chose que son juge ne peut réussir que par chance.
SEUIL_CONTACT_MM = 1.0
SEUIL_FACE = -0.5
# ═══ UN SEUL SEUIL D'ANNEAU, ET C'EST LE CONTRAT ═══
# Le dépôt en portait DEUX : l'optimiseur visait 16 mm, le verdict exigeait 14.
# Une recherche qui vise autre chose que son juge ne réussit que par chance, et
# viser 16 pour n'en devoir que 14 a coûté le contact du OK — l'optimiseur
# achetait de l'anneau avec de la distance jusqu'à franchir le seuil.
SEUIL_ANNEAU_MM = 14.0


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
            m["ouverture_anneau_mm"] = diametre_anneau()
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
        # ═══ LA DOCTRINE N'ÉTAIT CÂBLÉE QUE POUR L'INTERPÉNÉTRATION ═══
        #
        # « Ce qui est obligatoire ne se négocie pas » ne valait que pour les
        # traversées. La distance, l'orientation et l'anneau, eux, étaient de
        # simples poids — donc ils s'ÉCHANGEAIENT. Mesuré sur `Hand_OK` :
        #
        #     après approche   0,53 mm — 0 traversée
        #     après nettoyage  1,04 mm — 0 traversée   →  ÉCHEC
        #
        # Le nettoyage a DÉGRADÉ un contact déjà propre. Sous 1,00 mm la
        # distance ne coûtait plus rien, et l'exigence d'anneau — 400 points
        # par millimètre manquant — est antagoniste du contact : écarter le
        # pouce de l'index ouvre l'anneau ET éloigne les pulpes. L'optimiseur a
        # donc dépensé toute la marge, puis franchi le seuil de 0,04 mm parce
        # que le millimètre d'anneau gagné valait plus que le dépassement.
        #
        # On compte donc les critères OBLIGATOIRES violés, et cette somme entre
        # dans la barrière. Aucune pose qui en viole un ne peut alors battre une
        # pose qui les respecte tous, quel que soit son avantage ailleurs : les
        # termes continus ne servent plus qu'à guider vers eux et à départager
        # entre poses également acceptables.
        _violes = ((1 if inter + m["penetration"] > 0 else 0)
                   + (1 if m["distance_mm"] > SEUIL_CONTACT_MM else 0)
                   + (1 if m["face_local"] > SEUIL_FACE else 0)
                   + (1 if (ANNEAU_EXIGE[0]
                            and m.get("ouverture_anneau_mm", 0.0)
                            < ANNEAU_EXIGE[0]) else 0))
        sc = (_violes * BARRIERE[0]
              + (inter + m["penetration"]) * BARRIERE[0]
              + _d_eff * 300.0
              + max(0.0, m["distance_mm"] - SEUIL_CONTACT_MM) * 9000.0
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
    # ═══ UNE RECHERCHE MUETTE EST INDISCERNABLE D'UN BLOCAGE ═══
    # Le chat 1 a déstampé les sorties du pipeline, mais PAS l'intérieur des
    # boucles : une recherche de contact peut rester trois minutes sans écrire
    # un octet. Sacha a cru à un plantage et arrêté une reconstruction qui
    # travaillait. Un battement par tour suffit à lever le doute, et il coûte
    # une ligne pour une minute de calcul.
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
        print(f"ATLAS_BATTEMENT {doigt_a}/{doigt_b} tour {_t + 1}/{tours} "
              f"score={best[0]:.1f} distance={best[1]['distance_mm']:.2f}mm "
              f"traversées={best[1].get('intersection_des_doigts', '?')}"
              f"{'' if bouge else ' (pas resserré)'}")
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


def axes_de_degagement(doigt_a, doigt_b, deja):
    """Les doigts ÉTRANGERS au contact doivent pouvoir sortir du chemin.

    ═══ ON A CORRIGÉ L'INSTRUMENT SANS ROUVRIR L'ESPACE QU'IL CONDAMNE ═══

    Mesuré sur la baseline du chat 2, reproduite depuis le commit public :

        ATLAS_DEUX_TEMPS  après approche   1,08 mm — 17 traversées
                          après nettoyage  3,19 mm —  0 traversée

    La recherche SAIT venir à 1,08 mm. Aucune pose propre n'existe à cette
    distance dans les axes qu'on lui donne, alors le nettoyeur fait la seule
    chose qu'il peut : il RECULE le pouce, et rend 3,19 mm pour un seuil à
    1,00 mm.

    Les axes de `PINCH` étaient `Index_Curl`, `Thumb_Curl`,
    `Thumb_Opposition`, `Relax` et six corrections FK sur l'index et le pouce.
    Pas un seul sur le majeur, l'annulaire ou l'auriculaire. Or depuis que la
    sonde compte les 15 couples dans les deux sens, ces trois doigts sont
    JUGÉS — sans avoir aucun moyen de s'écarter. C'est la même faute de forme
    que la sonde aveugle, prise par l'autre bout.

    UNE seule liberté par doigt libre, et c'est l'écartement. Dans une vraie
    main, un doigt évite son voisin LATÉRALEMENT — c'est le même fait que
    « les doigts divergent en se fermant », établi plus haut par la mesure.
    Lui donner aussi la flexion serait lui permettre de changer de geste :
    l'optimiseur ouvrirait le poing pour le rendre propre, et rendrait un
    poing qui n'en est plus un.

    L'amplitude est celle de la butée anatomique de la phase E (±15°) et pas
    un degré de plus : au-delà, la contrainte écrête et l'optimiseur explore
    une plage morte où deux valeurs différentes donnent la même pose.

    `deja` porte les clés déjà pilotées par l'appelant : sans cette
    déduplication, deux entrées écriraient la même rotation et le vecteur de
    l'optimiseur ne correspondrait plus à ce qu'il croit régler.
    """
    return [("os", (f"CTRL_{n}_01{SIDE}", AXE_ECART), -15.0, 15.0)
            for n in NOMS4
            if n not in (doigt_a, doigt_b)
            and (f"CTRL_{n}_01{SIDE}", AXE_ECART) not in deja]


def axes_de_presentation(doigt_a, doigt_b, deja):
    """Les articulations qui PRÉSENTENT les deux pulpes l'une à l'autre.

    ═══ LE DIAGNOSTIC A RÉFUTÉ MA PREMIÈRE HYPOTHÈSE ═══

    J'avais conclu des 17 traversées de `Hand_Pinch` que les doigts libres
    barraient le chemin. Le diagnostic générique dit autre chose, et il est
    sans appel :

        ATLAS_OU_CA_TRAVERSE_APPROCHE index/thumb
            DEF_index_03.L → DEF_thumb_02.L : 12
            DEF_thumb_02.L → DEF_index_03.L :  5

    Les 17 sommets sont ENTRE LES DEUX PHALANGES DISTALES DU CONTACT — les
    deux pulpes qui se pincent, et rien d'autre. Aucun doigt libre n'y est
    pour quoi que ce soit.

    La cause se lit en comparant les deux recherches. `ANNEAU` porte
    `CTRL_index_02` ; `PINCH` n'a que `CTRL_index_01` ; aucune des deux n'a
    `CTRL_index_03`. Et `Hand_OK`, qui a une articulation de plus, approche
    PROPRE à 0,53 mm là où `Hand_Pinch` approche à 1,08 mm avec 17 traversées.
    Les articulations qui orientent la pulpe n'étaient pas dans la recherche :
    l'index ne pouvait pas présenter sa pulpe à plat, il l'enfonçait par la
    tranche.

    La règle est générale et vaut pour les trois contacts : la chaîne
    distale des DEUX doigts en contact doit être cherchable. Une pulpe qui ne
    peut pas s'orienter ne peut se poser que de travers.

    Pas d'écartement ici : la phase E verrouille le Z des phalanges au-delà de
    la métacarpo-phalangienne, parce qu'une interphalangienne est une
    CHARNIÈRE. On ne cherche donc que la flexion, à l'amplitude que `PINCH`
    emploie déjà pour l'index (±30°).
    """
    ax = []
    for _d in (doigt_a, doigt_b):
        for _suf in (("01", "02") if _d == "thumb" else ("01", "02", "03")):
            cle = (f"CTRL_{_d}_{_suf}{SIDE}", 0)
            if cle not in deja:
                ax.append(("os", cle, -30.0, 30.0))
    return ax


def chercher_contact(doigt_a, doigt_b, axes, base_props=None, presentation=True):
    """Deux temps : approcher, puis nettoyer sans lâcher le contact.

    `presentation=False` pour le poing : sa proximité pouce/index n'est jugée
    par AUCUN `exiger` — c'est un sous-produit de l'enroulement, pas un
    critère. Sa silhouette, elle, en est un. Ouvrir l'index jusqu'à 30° pour
    améliorer un non-critère troquerait donc le poing contre rien.
    """
    BARRIERE[0] = 60.0                      # le pouce peut traverser en chemin
    # La présentation entre dès l'APPROCHE : c'est là que le contact se forme,
    # et un contact formé de travers ne se redresse pas au nettoyage.
    if presentation:
        axes = axes + axes_de_presentation(doigt_a, doigt_b,
                                           {c for _g, c, _lo, _hi in axes})
    m1, etat1, v1 = optimiser_contact(doigt_a, doigt_b, axes, base_props, tours=10)
    # On NOMME ce qui traverse avant de le corriger : sans ça, élargir les axes
    # serait un coup de dés de plus.
    print(f"ATLAS_OU_CA_TRAVERSE_APPROCHE {doigt_a}/{doigt_b} "
          + json.dumps(ou_ca_traverse(), ensure_ascii=False))
    # ═══ LA BARRIÈRE DE NETTOYAGE EST HAUTE, PAS INFINIE ═══
    # À 10⁶, un unique sommet marginal valait plus que tout le contact : la
    # phase 2 abandonnait un appui à 0,86 mm pour aller à 16 mm. Bornée à
    # 20 000, une traversée vaut 2 mm d'écart — assez pour être chassée en
    # priorité, pas assez pour justifier de lâcher la pince. Le critère
    # d'acceptation final, lui, reste strict : zéro.
    BARRIERE[0] = 20000.0
    # La zone franche s'arrête AVANT le seuil d'acceptation, pas dessus. Calée
    # sur le seuil lui-même, l'optimiseur dépensait la marge jusqu'au dernier
    # centième et rendait 1,04 mm — et `ATLAS_ECART_OPTIMISEUR` existe
    # justement parce que la mesure prise pendant la recherche et celle prise
    # après repose ne coïncident pas toujours. Les 20 % restants continuent
    # donc de coûter.
    CIBLE_DISTANCE[0] = SEUIL_CONTACT_MM * 0.8
    # On repart de la pose approchée : les graines de `optimiser_contact`
    # partiraient de loin et retomberaient dans le même piège.
    axes_serres = [(g, c, max(lo, v - (hi - lo) * 0.22),
                    min(hi, v + (hi - lo) * 0.22))
                   for (g, c, lo, hi), v in zip(axes, v1)]
    # Le dégagement n'entre qu'ici, pas dans l'approche : approcher n'a pas
    # besoin des doigts libres, et les lui donner coûterait la moitié du temps
    # de recherche pour rien.
    axes_serres += axes_de_degagement(doigt_a, doigt_b,
                                      {c for _g, c, _lo, _hi in axes})
    m2, etat2, v2 = optimiser_contact(doigt_a, doigt_b, axes_serres,
                                      base_props, tours=18)
    CIBLE_DISTANCE[0] = 0.0
    BARRIERE[0] = 1e6
    print("ATLAS_DEUX_TEMPS " + json.dumps(
        {"contact": f"{doigt_a}/{doigt_b}",
         "apres_approche_mm": round(m1["distance_mm"], 2),
         "traversees_apres_approche": m1.get("intersection_des_doigts"),
         "apres_nettoyage_mm": round(m2["distance_mm"], 2),
         "traversees_apres_nettoyage": m2.get("intersection_des_doigts"),
         "axes_de_degagement": len(axes_serres) - len(axes)},
        ensure_ascii=False))
    if m2.get("intersection_des_doigts"):
        print(f"ATLAS_OU_CA_TRAVERSE_NETTOYAGE {doigt_a}/{doigt_b} "
              + json.dumps(ou_ca_traverse(), ensure_ascii=False))

    # ═══ LE SECOND ÉTAT N'EST PAS MEILLEUR PARCE QU'IL EST PLUS TARDIF ═══
    #
    # Mesuré sur `Hand_OK`, deux fois : l'approche rendait 0,53 mm PROPRE et le
    # nettoyage rendait 1,04 mm ; puis, après élargissement des axes, l'approche
    # rendait 0,87 mm propre et le nettoyage 2,43 mm. Le nettoyage DÉGRADAIT un
    # contact déjà bon, et on gardait quand même son résultat — uniquement
    # parce qu'il venait après.
    #
    # On compare donc explicitement les deux états sur les critères
    # OBLIGATOIRES, dans l'ordre du cahier, et on rend le meilleur.
    def _rang(m):
        _anneau = m.get("ouverture_anneau_mm", ANNEAU_EXIGE[0])
        return (1 if (m.get("intersection_des_doigts") or m["penetration"]) else 0,
                1 if m["distance_mm"] > SEUIL_CONTACT_MM else 0,
                1 if m["face_local"] > SEUIL_FACE else 0,
                1 if (ANNEAU_EXIGE[0] and _anneau < ANNEAU_EXIGE[0]) else 0,
                max(0.0, m["distance_mm"] - SEUIL_CONTACT_MM),
                max(0.0, m["face_local"] - SEUIL_FACE),
                max(0.0, ANNEAU_EXIGE[0] - _anneau) if ANNEAU_EXIGE[0] else 0.0)

    if _rang(m1) < _rang(m2):
        print("ATLAS_APPROCHE_MEILLEURE " + json.dumps(
            {"contact": f"{doigt_a}/{doigt_b}",
             "approche_mm": round(m1["distance_mm"], 2),
             "nettoyage_mm": round(m2["distance_mm"], 2),
             "retenu": "approche"}, ensure_ascii=False))
        poser_etat(*etat1)
        return m1, etat1, v1
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
        print(f"ATLAS_BATTEMENT nettoyage {nom_pose} tour {_t + 1}/{tours} "
              f"reste={best[1]}{'' if bouge else ' (pas resserré)'}")
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
# ═══ ON NE MESURE PAS UN TROU PAR LA DISTANCE MINIMALE DE SON CONTOUR ═══
#
# `ouverture_anneau()` rend le MINIMUM global entre les chairs proximales du
# pouce et de l'index. Un seul point proche fait donc chuter la valeur alors
# que le trou central reste grand — et inversement, un contour qui se pince
# quelque part peut afficher une belle ouverture. C'est l'endroit où le contour
# se SERRE, pas la taille du vide.
#
# `outils/anneau.py` mesure le diamètre du plus grand disque inscrit dans le
# vide, dans le plan de l'anneau, sur la pose courante. C'est ce que le cahier
# appelle le diamètre utile, et c'est lui qui décide si un « OK » se lit.
ANNEAU_INTROUVABLE = [0]


def diametre_anneau():
    """Le diamètre utile, ou 0 quand la pose n'a PAS d'anneau.

    ═══ UN ANNEAU ABSENT N'EST PAS UNE MESURE MANQUANTE ═══
    Le module lève quand la tranche du plan ne contient pas assez de sommets
    pour dessiner un contour — mesuré pendant la recherche du OK : « 591
    sommets d'index et 0 de pouce ». C'est juste, et ça tuait la construction.
    Or pendant une recherche, la plupart des poses candidates n'ont
    légitimement aucun anneau : le pouce n'est pas encore en face.
    On rend donc 0, ce qui est VRAI — le trou est de taille nulle — et le
    critère ≥ 14 mm l'écarte comme il doit. Mais on COMPTE ces cas et on les
    publie : sans ça, un zéro « pas d'anneau ici » deviendrait indiscernable
    d'un zéro « je n'ai pas su mesurer », et c'est la faute que ce dépôt
    combat depuis le début.
    """
    try:
        return anneau.diametre_utile_anneau(rig, geo, SIDE, _dom, PALMAIRE_CUP)
    except RuntimeError:
        ANNEAU_INTROUVABLE[0] += 1
        return 0.0


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
    ANNEAU_EXIGE[0] = SEUIL_ANNEAU_MM if _nom_c == "Hand_OK" else 0.0
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
           _m["distance_mm"] <= SEUIL_CONTACT_MM,
           f'{_m["distance_mm"]:.2f} mm', f"≤ {SEUIL_CONTACT_MM:.2f} mm")
    exiger(f"{_nom_c} · les pulpes se font face",
           _m["face_local"] <= SEUIL_FACE, round(_m["face_local"], 3),
           f"≤ {SEUIL_FACE:.2f}".replace(".", ","))
    # ═══ UN CRITÈRE VERT QUI MENTAIT ═══
    # Il ne lisait que `penetration` — les sommets qui se traversent DANS LE
    # PATCH des deux pulpes. Mesuré sur la baseline, `Hand_Pinky_Thumb` rendait
    # « aucune interpénétration · 0 · OK » avec 213 sommets traversants ailleurs
    # dans la main. C'est très exactement la cécité que tout le chat 1 a
    # corrigée, survivante à un endroit qu'on n'avait pas regardé. Les deux
    # comptes sont désormais exigés, et tous deux affichés.
    exiger(f"{_nom_c} · aucune interpénétration",
           _m["penetration"] == 0 and not _m.get("intersection_des_doigts"),
           {"dans_les_pulpes": _m["penetration"],
            "dans_la_main_entiere": _m.get("intersection_des_doigts")},
           "0 sommet, pulpes ET main entière")

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
#
# ═══ « SANS POUCE » NE L'ÉTAIT PAS ═══
#
# `regler(Fist=f)` ne bouge QUE les quatre doigts — le pouce a ses commandes
# propres depuis la correction de l'écrasement. Il reste donc AU REPOS, en
# travers du chemin, et les quatre doigts se referment dessus. La mesure
# comptait ces chocs-là et les attribuait à la fermeture : à 0,7 elle rendait
# 2 429 traversées dont 1 272 sur le couple `thumb/index`, dans un relevé qui
# se disait « mesuré sans le pouce ».
#
# La conséquence n'était pas cosmétique : `FERMETURE` retombait à 0,6, et le
# poing livré n'était fermé qu'à 60 %. Un poing qui n'en est pas un, à cause
# d'un pouce qu'on n'avait pas posé.
#
# On restreint donc la question aux quatre doigts, ce qui est ce qu'elle a
# toujours prétendu être.
_QUATRE = ("index", "middle", "ring", "pinky")


def _profondeur_propre(pas=0.05, cup=0.0):
    """Jusqu'où les quatre doigts se ferment SANS se traverser entre eux.

    `cup` entre dans la mesure parce qu'une paume qui se creuse présente les
    rayons internes différemment : la fermeture propre n'est pas la même à
    plat et en coupe.
    """
    _f = 0.0
    _detail = {}
    while _f <= 1.0 + 1e-9:
        regler(Fist=_f, Cup=cup)
        _ii = intersections(f"fist{_f:.2f}", familles=_QUATRE)
        _t = sum(x["sommets_dedans"] for x in _ii)
        _detail[round(_f, 2)] = _t
        if _t:
            regler()
            return round(_f - pas, 2), _detail
        _f += pas
    regler()
    return 1.0, _detail


# ═══ K_DIVERGENCE SE CHERCHE, IL NE SE POSE PAS ═══
#
# La divergence est désormais pilotée par `Fist` (phase D). Son amplitude
# décide jusqu'où les doigts peuvent se fermer sans se pénétrer : c'est
# exactement la grandeur que le chat 1 avait laissée à 8° sans jamais
# l'éprouver, pendant que la fermeture plafonnait à 0,6.
#
# On retient la PLUS PETITE amplitude qui atteint la fermeture la plus
# profonde : au-delà, on écarterait les doigts plus que nécessaire et le poing
# cesserait d'être un poing.
_DRIVERS_ECART = {}
for _n in NOMS4:
    for _fc in (rig.animation_data.drivers if rig.animation_data else []):
        if (_fc.data_path == f'pose.bones["MCH_{_n}_01_result{SIDE}"].rotation_euler'
                and _fc.array_index == AXE_ECART):
            _DRIVERS_ECART[_n] = _fc


def _poser_k(k):
    for _n, _fc in _DRIVERS_ECART.items():
        _fc.driver.expression = (
            f"spread * {SIGNE_ECART * math.radians(ECART[_n]):.6f}"
            f" + fist * {SIGNE_DIVERGENCE * math.radians(k * DIVERGENCE[_n]):.6f}")
    forcer_evaluation()


if len(_DRIVERS_ECART) != len(NOMS4):
    raise RuntimeError("les drivers d'écartement sont introuvables : la "
                       f"recherche de K_DIVERGENCE ne pilote rien ({_DRIVERS_ECART})")

_balayage_k = {}
for _k in (0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0):
    _poser_k(_k)
    _prof, _det = _profondeur_propre()
    _balayage_k[_k] = {"fermeture_propre": _prof, "detail": _det}
    print(f"ATLAS_DIVERGENCE k={_k:.0f}° → fermeture propre {_prof}")
_meilleure = max(v["fermeture_propre"] for v in _balayage_k.values())
K_DIVERGENCE[0] = min(k for k, v in _balayage_k.items()
                      if v["fermeture_propre"] >= _meilleure - 1e-9)
_poser_k(K_DIVERGENCE[0])
dire("divergence_cherchee", {
    "balayage": {str(k): v["fermeture_propre"] for k, v in _balayage_k.items()},
    "k_retenu_deg": K_DIVERGENCE[0],
    "fermeture_propre_atteinte": _meilleure,
    "regle": "la plus PETITE amplitude qui atteint la fermeture la plus profonde"})

# ═══ LE CREUSEMENT DU POING SE CHERCHE AUSSI ═══
# Une paume creuse présente les rayons internes autrement : la fermeture propre
# n'est pas la même à plat qu'en coupe. On ne pose donc pas `Cup = 0,7` comme
# graine, on regarde lequel laisse aller le plus loin.
_balayage_cup_poing = {}
for _c in (0.0, 0.25, 0.5, 0.7, 0.9):
    _p, _ = _profondeur_propre(cup=_c)
    _balayage_cup_poing[_c] = _p
    print(f"ATLAS_CUP_POING cup={_c:.2f} → fermeture propre {_p}")
_meilleur_cup = max(_balayage_cup_poing.values())
CUP_POING = min(c for c, p in _balayage_cup_poing.items()
                if p >= _meilleur_cup - 1e-9)
dire("creusement_du_poing", {
    "balayage": {str(c): p for c, p in _balayage_cup_poing.items()},
    "cup_retenu": CUP_POING,
    "fermeture_propre_atteinte": _meilleur_cup,
    "regle": "le plus PETIT creusement qui laisse aller le plus loin"})

_prof_finale, _diag_poing_detail = _profondeur_propre(pas=0.02, cup=CUP_POING)
_diag_poing = {f: {"total": t} for f, t in _diag_poing_detail.items()}
regler()
dire("traversees_des_quatre_doigts_seuls", _diag_poing)

# ═══ UNE FERMETURE À 0,6 EST UN DIAGNOSTIC, JAMAIS UNE LIVRAISON ═══
#
# L'ancienne ligne était `max([...] or [0.6])`. Mesuré : AUCUN niveau n'était
# propre — 0,6 en comptait déjà 1 — donc la liste était vide et le code
# retombait sur sa valeur de repli. Le « poing réaliste mesuré » du dépôt était
# une constante écrite en dur qu'aucune mesure n'avait jamais choisie, et
# personne ne pouvait le voir puisque le nombre semblait venir d'un calcul.
_propres = [f for f, m in _diag_poing.items() if m["total"] == 0]
FERMETURE = max(_propres) if _propres else None
dire("fermeture_retenue", {
    "valeur": FERMETURE,
    "profondeur_propre_mesuree": _prof_finale,
    "raison": "la plus franche qui ne traverse pas, quatre doigts SEULS"})
exiger("le poing se ferme complètement sans traversée",
       FERMETURE is not None and abs(FERMETURE - 1.0) < 1e-6,
       FERMETURE if FERMETURE is not None else "aucun niveau propre",
       "Fist = 1.0")
if FERMETURE is None:
    FERMETURE = _prof_finale

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
    # ═══ L'OPTIMISEUR DU POUCE NE PEUT PLUS ROUVRIR LES DOIGTS ═══
    # Il pouvait descendre Fist jusqu'à 0,55 pour améliorer SON contact : le
    # poing livré cessait alors d'être un poing pour qu'un pouce touche mieux.
    # La fermeture est fixée à 1,0 et cherchée ailleurs.
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
    # La fermeture est IMPOSÉE au fond de la recherche, plus laissée à
    # l'optimiseur : on construit d'abord les quatre doigts, puis on cherche le
    # pouce autour d'eux. Le creusement suit la fermeture retenue.
    {"Fist": 1.0, "Cup": CUP_POING}, presentation=False)
POSE_POING = ({**_etat_poing[0], "Fist": 1.0, "Cup": CUP_POING},
              _etat_poing[1])
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


def etapes_fautives(pr, o):
    """Les fractions du trajet où la main se traverse, et de combien."""
    out = {}
    for _k in range(11):
        _u = _k / 10.0
        poser_etat({kk: vv * _u for kk, vv in pr.items()},
                   {kk: vv * _u for kk, vv in o.items()})
        _n = sum(x["sommets_dedans"] for x in intersections(f"chemin@{_u}"))
        if _n:
            out[round(_u, 1)] = _n
    return out


def nettoyer_transition(nom_pose, pr, o, axes, rondes=3, tours=6):
    """Corriger le CHEMIN, et pas seulement son point d'arrivée.

    ═══ CE QU'ON MESURE SANS LE CORRIGER RESTE FAUX ═══

    `rig-main.py` échantillonnait déjà les six transitions à onze étapes et
    faisait échouer la construction dessus — mais rien ne les corrigeait
    jamais. Quatre des neuf critères en échec du checkpoint sont des
    transitions, dont une, `Neutral→Hand_Fist`, dont les DEUX extrémités sont
    propres : le pouce traverse l'index à t = 0,8 et 0,9, puis en ressort.
    Nettoyer la pose d'arrivée ne pouvait pas l'atteindre.

    Les corrections FK d'une pose sont interpolées avec elle : les régler
    déplace donc tout le trajet d'un coup. On cherche celles qui rendent
    propres LES ÉTAPES FAUTIVES et l'arrivée — jamais l'arrivée seule, sans
    quoi le nettoyage rachèterait le milieu du geste avec sa fin.

    L'échantillonnage est ADAPTATIF : évaluer les onze étapes à chaque essai
    coûterait onze fois le prix pour une information qu'on a déjà. On ne garde
    que les étapes réellement fautives, plus l'arrivée, et on relit le trajet
    entier entre deux rondes — corriger une étape peut en salir une autre.
    """
    for _ronde in range(rondes):
        fautives = etapes_fautives(pr, o)
        if not fautives:
            return o, {}
        echantillon = sorted(set(list(fautives) + [1.0]))
        print(f"ATLAS_TRANSITION_A_NETTOYER {nom_pose} ronde {_ronde + 1} : "
              + json.dumps({str(k): v for k, v in fautives.items()},
                           ensure_ascii=False))

        def evaluer(vec):
            corr = {cle: v for (_g, cle, _lo, _hi), v in zip(axes, vec)}
            o2 = {**o, **{k: o.get(k, 0.0) + v for k, v in corr.items()}}
            total = 0
            for _u in echantillon:
                poser_etat({kk: vv * _u for kk, vv in pr.items()},
                           {kk: vv * _u for kk, vv in o2.items()})
                total += sum(x["sommets_dedans"]
                             for x in intersections(f"{nom_pose}@{_u}"))
            # Le second terme garde la correction MINIMALE parmi celles qui
            # nettoient : une transition propre obtenue en défigurant la pose
            # d'arrivée ne serait pas un progrès.
            return total * 1e5 + sum(abs(v) for v in vec) / max(1, len(vec)) * 12.0, total, o2

        milieu = [0.0] * len(axes)
        best = evaluer(milieu) + (list(milieu),)
        pas = [(hi - lo) / 4.0 for _g, _c, lo, hi in axes]
        # ═══ TROISIÈME FOIS QUE J'OUBLIE UN BATTEMENT ═══
        # Posés dans `optimiser_contact` et `nettoyer_pose`, pas ici. Sacha a
        # vu sept minutes de silence et demandé si la reconstruction buguait —
        # elle tournait à 100 % de CPU. Une boucle muette est indiscernable
        # d'un blocage, et cette boucle-ci est la plus lente de toutes :
        # chaque essai remesure TOUTES les étapes fautives du trajet.
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
            print(f"ATLAS_BATTEMENT transition {nom_pose} ronde {_ronde + 1} "
                  f"tour {_t + 1}/{tours} reste={best[1]} sur "
                  f"{len(echantillon)} étapes"
                  f"{'' if bouge else ' (pas resserré)'}")
            if not bouge:
                pas = [x * 0.55 for x in pas]
        print(f"ATLAS_TRANSITION_NETTOYEE {nom_pose} ronde {_ronde + 1} : "
              f"{best[1]} sommets traversants sur {len(echantillon)} étapes")
        if best[1] == 0:
            return best[2], {"rondes": _ronde + 1}
        o = best[2]
    return o, {"rondes": rondes, "reste": etapes_fautives(pr, o)}


_transitions = {}
_TRANSITIONS = ("Hand_Fist", "Hand_Point", "Hand_Pinch", "Hand_OK",
                "Hand_Cupped", "Hand_Pinky_Thumb")
for _cible in _TRANSITIONS:
    if _cible not in _POSES_D:
        continue
    _pr, _o = _POSES_D[_cible]
    if etapes_fautives(_pr, _o):
        _o, _info = nettoyer_transition(_cible, _pr, _o, AXES_NETTOYAGE)
        _POSES_D[_cible] = (_pr, _o)
        POSES = [(n, p, (_o if n == _cible else oo)) for n, p, oo in POSES]
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

# ═══ NETTOYER UN CHEMIN PEUT SALIR SON ARRIVÉE ═══
# Les corrections de transition s'appliquent aussi à la pose finale, puisque
# c'est l'étape t = 1,0 du même trajet. On remesure donc TOUTES les poses après
# coup : sans ce contrôle, on troquerait un échec de transition contre un échec
# de pose sans que rien ne le dise.
for nom_pose, reglages, os_pose in POSES:
    poser_etat(reglages, os_pose)
    _inter2 = intersections(nom_pose)
    if _inter2 != _controle[nom_pose]["auto_intersections"]:
        _controle[nom_pose]["auto_intersections_apres_transitions"] = _inter2
        exiger(f"{nom_pose} · aucune auto-intersection après nettoyage "
               f"des transitions", not _inter2, _inter2 or "aucune", "aucune")
regler()

# ═══ PINCH ET OK DOIVENT ÊTRE DEUX GESTES ═══
# Ils rendaient exactement la même course et la même distance : c'était la même
# optimisation lancée deux fois. On mesure leur écart au lieu de l'espérer.
if "Hand_Pinch" in _POSES_D and "Hand_OK" in _POSES_D:
    poser_etat(*_POSES_D["Hand_Pinch"])
    _pp1, _ = sommets_evalues()
    _anneau_pinch = diametre_anneau()
    poser_etat(*_POSES_D["Hand_OK"])
    _pp2, _ = sommets_evalues()
    _anneau_ok = diametre_anneau()
    _ecart_gestes = max((a - b).length for a, b in zip(_pp1, _pp2)) * 1000
    regler()
    dire("pinch_contre_ok", {
        "ecart_maximal_entre_les_deux_poses_mm": round(_ecart_gestes, 1),
        "diametre_utile_pinch_mm": round(_anneau_pinch, 1),
        "diametre_utile_ok_mm": round(_anneau_ok, 1),
        "note": "diamètre du plus grand disque inscrit dans le trou, pas le "
                "minimum du contour",
        "poses_sans_anneau_mesurable_pendant_la_recherche":
            ANNEAU_INTROUVABLE[0]})
    # Contre-épreuve du §10.1 : un pincement n'a pas d'anneau. Si les deux
    # poses rendent le même diamètre, la mesure ne distingue pas un anneau d'un
    # pincement et son verdict sur le OK ne vaut rien.
    exiger("le diamètre utile distingue l'anneau du pincement",
           _anneau_ok > _anneau_pinch + 3.0,
           f"OK {_anneau_ok:.1f} mm contre Pinch {_anneau_pinch:.1f} mm",
           "au moins 3 mm de plus pour le OK")
    exiger("Pinch et OK sont deux gestes distincts", _ecart_gestes > 15.0,
           f"{_ecart_gestes:.1f} mm", "> 15 mm d'écart")
    exiger("l'anneau du OK est lisible", _anneau_ok >= SEUIL_ANNEAU_MM,
           f"{_anneau_ok:.1f} mm", f"≥ {SEUIL_ANNEAU_MM:.0f} mm d'ouverture")

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
    # ═══ L'ÉCLAIRAGE N'EST PLUS IMPROVISÉ ICI ═══
    #
    # `atelier/eclairage.py` existait depuis le chat 1, prouvé isolément —
    # 18 rendus, 0,000 % d'écrêtage, key mesurée à 75,0° de la normale — et
    # n'avait JAMAIS été exécuté dans le pipeline. Pendant ce temps ce bloc
    # posait trois lampes à la main, avec des puissances rattrapées deux fois
    # (« 260 W saturait », « à 30 W tout partait en blanc »). Deux éclairages
    # pour un même dépôt, dont un seul était mesuré.
    #
    # Le module devient la seule source : exposition verrouillée pour toute la
    # série, clay lambertien, distance des sources calculée sur la largeur du
    # sujet — donc un gros plan n'est pas plus brûlé qu'un plan large — et un
    # histogramme rendu à chaque image, qui fait échouer la construction si
    # l'écrêtage dépasse la limite.
    _verrous = eclairage.poser_studio(sc, materiau_clay=True, objets_clay=[geo])
    try:
        sc.cycles.device = "GPU"
    except Exception:
        pass
    dire("studio_verrouille", {k: (v if isinstance(v, (int, float, str, bool,
                                                       list, tuple))
                                   else str(v))
                               for k, v in _verrous.items()})
    ECRETAGE_MAX = 2.0          # en % — la limite que l'agent lumière s'est fixée
    _histos = {}

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

    def rendre(nom_image, direction, cadre=0.205, vise_sur=None, cote=1):
        """Une image, sous lumière rasante mesurée, et son histogramme.

        `direction` va de la cible vers la caméra : c'est donc aussi la
        normale de la surface qu'on photographie, et c'est elle qu'on fait
        raser. `cote` vaut +1 ou −1 — les deux directions rasantes opposées
        que le cahier exige pour la paume et le dos, parce qu'un pli que la
        première noie, la seconde le révèle.
        """
        _p, _ = sommets_evalues()
        # On vise la MAIN, pas le bras : les sommets tenus par DEF_hand
        # appartiennent au moignon d'avant-bras, et les inclure repoussait la
        # main dans un coin du cadre.
        if vise_sur is not None:
            vise = vise_sur
        else:
            _ii = [i for i, n in _dom.items() if n != f"DEF_hand{SIDE}"]
            vise = sum((_p[i] for i in _ii), mathutils.Vector((0, 0, 0))) / len(_ii)
        eclairage.cadrer(geo, direction, vise, cadre, scene=sc)
        _e = eclairage.eclairer_rasant(vise, direction, direction, cote,
                                       largeur_sujet=cadre, scene=sc)
        _chemin = os.path.join(DOSSIER, f"{nom_image}.png")
        _h = eclairage.rendre(_chemin, sc)
        # ═══ PAS DE VALEUR PAR DÉFAUT SUR UNE MESURE ═══
        # Premier jet : je lisais `_h.get("ecretage", 0.0)` alors que la clé
        # s'appelle `ecretage_pct`. Chaque image aurait rendu 0 % d'écrêtage et
        # 0° de rasance, et le critère serait passé en ne mesurant RIEN. Un
        # zéro se lit comme une mesure. On indexe donc directement : une clé
        # absente doit lever, pas valoir zéro.
        _histos[nom_image] = {
            "ecretage_pct": _h["ecretage_pct"],
            "ombres_pct": _h["ombres_pct"],
            "luminance_max": _h["luminance_max"],
            "luminance_moyenne": _h["luminance_moyenne"],
            "couverture_pct": _h.get("couverture_pct"),
            "key_contre_normale_deg": round(_e["key_angle_vs_normale_deg"], 1)}
        return _h

    # ═══ DEUX DIRECTIONS RASANTES POUR LA PAUME ET LE DOS ═══
    # Le cahier les exige, et pour une raison qui se mesure : une lumière
    # rasante ne révèle que les plis PERPENDICULAIRES à elle. Une seule
    # direction laisse donc invisible la moitié du relief. Les tranches
    # (pouce, auriculaire) n'en reçoivent qu'une : leur silhouette suffit à
    # les juger, et doubler y coûterait 26 images pour rien.
    VUES = [("paume-A", PALMAIRE, +1), ("paume-B", PALMAIRE, -1),
            ("dos-A", -PALMAIRE, +1), ("dos-B", -PALMAIRE, -1),
            ("pouce", Tp, +1), ("auriculaire", -Tp, +1)]
    for nom_pose, reglages, os_pose in POSES:
        poser_etat(reglages, os_pose)
        for _nv, _dir, _cote in VUES:
            rendre(f"{nom_pose}-{_nv}", _dir, cote=_cote)
        print(f"ATLAS_RENDU {nom_pose} — {len(VUES)} vues")
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
            rendre(f"gros-plan-{nom_pose}-{plan}", direction, cadre=0.055,
                   vise_sur=_cible_gp)
        print(f"ATLAS_GROS_PLAN {nom_pose}")
    regler()

    # ═══ UNE IMAGE ILLISIBLE EST UN DÉFAUT, PAS UN DÉTAIL ═══
    # Le chat 1 avait relevé `gros-plan-Hand_Pinky_Thumb-pouce.png` : écart-type
    # de luminance 14,9 sur 255 contre 41,8 au minimum ailleurs. Remesuré ici :
    # confirmé au chiffre près. Un contact qu'on ne peut pas voir ne peut pas
    # être jugé, donc l'écrêtage ET le contraste entrent dans les critères.
    dire("histogrammes", _histos)
    _brulees = {k: v["ecretage_pct"] for k, v in _histos.items()
                if v["ecretage_pct"] > ECRETAGE_MAX}
    exiger("aucune image écrêtée", not _brulees, _brulees or "aucune",
           f"≤ {ECRETAGE_MAX:.1f} % par image")
    _rasances = {v["key_contre_normale_deg"] for v in _histos.values()}
    exiger("la key rase vraiment la surface",
           bool(_rasances) and all(70.0 <= x <= 80.0 for x in _rasances),
           sorted(_rasances) or "aucune image rendue",
           "75° ± 5 par rapport à la normale")
    # Le contraste : c'est LUI qui a condamné `gros-plan-Hand_Pinky_Thumb-pouce`
    # au chat 1, et l'écrêtage ne l'aurait jamais vu — une image plate n'est ni
    # brûlée ni bouchée, elle est simplement illisible. Seuil pris sur la série
    # elle-même et non inventé : le pire des 60 rendus de `b17e548` valait 5,86,
    # le deuxième 16,38. Un écart de trois pour un, donc la coupure est nette.
    _plates = {k: v["luminance_max"] - v["luminance_moyenne"]
               for k, v in _histos.items()
               if v["luminance_max"] - v["luminance_moyenne"] < 0.10}
    exiger("aucune image sans relief lisible", not _plates,
           _plates or "aucune", "amplitude de luminance ≥ 0,10")


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
    gs = [(g.weight, _gnom[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _gnom]
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
    gs = [(g.weight, _gnom[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _gnom]
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
        gs = [(g.weight, _gnom[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _gnom]
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
        gs = [(g.weight, _gnom[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _gnom]
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
