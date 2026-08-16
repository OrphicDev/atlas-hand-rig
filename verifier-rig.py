"""
VÉRIFIER UN RIG DÉJÀ CONSTRUIT, SANS LE RECONSTRUIRE.

Le tutoriel de correction exige une commande qui contrôle le `.blend` livré
sans repasser par le maillage de base — de sorte qu'un clone propre du dépôt
puisse juger le travail sans télécharger les 47 Mo du mannequin.

Ce script ouvre le fichier, rejoue chaque pose de la bibliothèque, et remesure
les critères obligatoires. Il sort en code non nul si l'un d'eux est faux.

    blender --background --factory-startup --python verifier-rig.py -- RIG_Hand.L.blend
"""
import json
import math
import os
import sys

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

FICHIER = sys.argv[sys.argv.index("--") + 1:][0]
if not os.path.isfile(FICHIER):
    raise RuntimeError("fichier introuvable : " + FICHIER)
bpy.ops.wm.open_mainfile(filepath=FICHIER)

geo = next(o for o in bpy.data.objects if o.name.startswith("GEO_Hand")
           and "BACKUP" not in o.name)
rig = next(o for o in bpy.data.objects if o.name.startswith("RIG_Hand"))
SIDE = rig.name[len("RIG_Hand"):]
pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]
NOMS4 = ["index", "middle", "ring", "pinky"]

# Les mêmes tolérances que celles du script de construction, et pour la même
# raison : sur une main de 100 mm, une vraie interpénétration s'enfonce d'un
# demi-millimètre, et deux surfaces déjà voisines au repos ne se « traversent »
# pas parce qu'elles se touchent.
PROFONDEUR_MINIMALE = 0.0005
ECART_REPOS_MINIMAL = 0.014
echecs = []


def evalue():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw, m3 = geo.matrix_world, geo.matrix_world.to_3x3()
    p = [mw @ v.co.copy() for v in m.vertices]
    n = [(m3 @ v.normal).normalized() for v in m.vertices]
    ev.to_mesh_clear()
    return p, n


def neutre():
    # Détacher l'action AVANT de remettre à zéro : sans cela, les clés de la
    # dernière pose rejouée écrasent la remise à zéro, et le contrôle du retour
    # au repos mesure la pose précédente au lieu du repos. Il rendait 123,9 mm.
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        # On ne force plus le mode de rotation : un vérificateur ne modifie pas
        # l'objet qu'il juge. On remet à zéro dans le mode où l'os se trouve.
        if pb.rotation_mode == "QUATERNION":
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        else:
            pb.rotation_euler = (0.0, 0.0, 0.0)
    for k in list(pbh.keys()):
        if isinstance(pbh[k], float):
            pbh[k] = 0.0
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def appliquer(action):
    neutre()
    rig.animation_data_create()
    rig.animation_data.action = action
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


_ng = {g.index: g.name for g in geo.vertex_groups}
neutre()
P_REPOS, _ = evalue()
DOM = {}
for v in geo.data.vertices:
    gs = [(g.weight, _ng[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _ng]
    if gs:
        DOM[v.index] = max(gs)[1]


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


def empreinte(doigt):
    dnom = f"DEF_{doigt}_" + ("02" if doigt == "thumb" else "03") + SIDE
    ii = [i for i, n in DOM.items() if n == dnom]
    if not ii:
        return []
    b = rig.data.bones[dnom]
    axe = (rig.matrix_world @ b.tail_local
           - rig.matrix_world @ b.head_local).normalized()
    paume = sum((P_REPOS[i] for i, n in DOM.items()
                 if n.endswith(f"_meta{SIDE}")), mathutils.Vector((0, 0, 0)))
    nmeta = sum(1 for i, n in DOM.items() if n.endswith(f"_meta{SIDE}"))
    centre = paume / max(1, nmeta)
    ref = centre - (rig.matrix_world @ b.head_local)
    ref = (ref - axe * ref.dot(axe))
    if ref.length < 1e-6:
        return []
    ref = ref.normalized()
    _p, _n = evalue()
    return [i for i in ii if _n[i].dot(ref) > 0.25]


EMP = {d: empreinte(d) for d in ("thumb", "index", "pinky")}


def contact(a, b):
    _p, _n = evalue()
    if not EMP[a] or not EMP[b]:
        return None
    t = mathutils.kdtree.KDTree(len(EMP[b]))
    for k, i in enumerate(EMP[b]):
        t.insert(_p[i], k)
    t.balance()
    d, ia = min(((t.find(_p[i])[2], i) for i in EMP[a]))
    ib = EMP[b][t.find(_p[ia])[1]]
    c = (_p[ia] + _p[ib]) / 2.0
    pa = [i for i in EMP[a] if (_p[i] - c).length < 0.005] or [ia]
    pb = [i for i in EMP[b] if (_p[i] - c).length < 0.005] or [ib]
    na = sum((_n[i] for i in pa), mathutils.Vector((0, 0, 0)))
    nb = sum((_n[i] for i in pb), mathutils.Vector((0, 0, 0)))
    face = (na.normalized().dot(nb.normalized())
            if na.length > 1e-9 and nb.length > 1e-9 else 1.0)
    return {"distance_mm": d * 1000.0, "face": face}


def traversees():
    _p, _n = evalue()
    par = {}
    for i, nm in DOM.items():
        f = famille(nm)
        if f is not None:
            par.setdefault(f, []).append(i)
    # Les 15 couples, dans les DEUX sens. La version précédente n'en testait
    # que 5 dans un seul sens et ne voyait donc que 22 % des traversées.
    arbres = {}
    for f, idx in par.items():
        t = mathutils.kdtree.KDTree(len(idx))
        for k, i in enumerate(idx):
            t.insert(_p[i], k)
        t.balance()
        arbres[f] = (t, idx)
    out = []
    fams = [f for f in ("thumb", "index", "middle", "ring", "pinky", "hand")
            if f in arbres]
    for x in range(len(fams)):
        for y in range(x + 1, len(fams)):
            fa, fb = fams[x], fams[y]
            n = 0
            for src, dst in ((fa, fb), (fb, fa)):
                t, idx = arbres[dst]
                for i in par[src]:
                    co, k, d = t.find(_p[i])
                    j = idx[k]
                    if (d < 0.008
                            and (_p[j] - _p[i]).dot(_n[j]) > PROFONDEUR_MINIMALE
                            and (P_REPOS[i] - P_REPOS[j]).length
                            > ECART_REPOS_MINIMAL):
                        n += 1
            if n:
                out.append({"entre": f"{fa}/{fb}", "sommets": n})
    return out


def exiger(nom, ok, mesure, seuil):
    if not ok:
        echecs.append({"critere": nom, "mesure": mesure, "seuil": seuil})
    print(f"{'OK   ' if ok else 'ÉCHEC'} · {nom} · mesuré {mesure} · exigé {seuil}")


ACTIONS = {a.name: a for a in bpy.data.actions}
resultat = {"fichier": os.path.basename(FICHIER),
            "os": {p: sum(1 for b in rig.data.bones if b.name.startswith(p + "_"))
                   for p in ("CTRL", "MCH", "DEF")},
            "poses": sorted(ACTIONS)}

# ── le retour exact au repos ──
neutre()
p0, _ = evalue()
if "Hand_Fist" in ACTIONS:
    appliquer(ACTIONS["Hand_Fist"])
    pf, _ = evalue()
    course = max((a - b).length for a, b in zip(p0, pf)) * 1000
else:
    course = 0.0
neutre()
p1, _ = evalue()
retour = max((a - b).length for a, b in zip(p0, p1)) * 1000
resultat["course_du_poing_mm"] = round(course, 1)
exiger("retour exact au repos", retour < 0.01, f"{retour:.4f} mm", "< 0,01 mm")
exiger("le rig bouge vraiment", course > 20.0, f"{course:.1f} mm", "> 20 mm")

# ── les contacts nommés ──
for pose, a, b in (("Hand_Pinch", "index", "thumb"),
                   ("Hand_OK", "index", "thumb"),
                   ("Hand_Pinky_Thumb", "pinky", "thumb")):
    if pose not in ACTIONS:
        # Une pose absente passait en silence : un .blend sans aucune des poses
        # contrôlées sortait en code 0. L'absence est un échec.
        exiger(f"{pose} · la pose existe dans le fichier", False, "absente",
               "présente")
        continue
    appliquer(ACTIONS[pose])
    c = contact(a, b)
    t = traversees()
    resultat[pose] = {"distance_mm": round(c["distance_mm"], 2),
                      "face": round(c["face"], 3), "traversees": t}
    exiger(f"{pose} · les pulpes se touchent", c["distance_mm"] <= 1.0,
           f'{c["distance_mm"]:.2f} mm', "≤ 1,00 mm")
    exiger(f"{pose} · les pulpes se font face", c["face"] <= -0.5,
           round(c["face"], 3), "≤ −0,50")
    exiger(f"{pose} · aucune auto-intersection", not t, t or "aucune", "aucune")

# ═══ TOUTES LES POSES, PAS QUATRE ═══
# Le vérificateur n'en contrôlait que quatre : Pinch, OK, Pinky_Thumb et Fist.
# Les neuf autres n'étaient donc jamais regardées — et c'est exactement là que
# l'audit a trouvé le gros des traversées (Point 1 540, Fist_75 118,
# Cupped 80). Ce qu'on ne mesure pas, on ne le corrige pas.
resultat["toutes_les_poses"] = {}
for _nom in sorted(ACTIONS):
    appliquer(ACTIONS[_nom])
    _t = traversees()
    resultat["toutes_les_poses"][_nom] = _t or "aucune"
    exiger(f"{_nom} · aucune auto-intersection", not _t, _t or "aucune", "aucune")

# ═══ LES TRANSITIONS, PAS SEULEMENT LES POSES FINALES ═══
# Une pose finale propre ne prouve rien si les doigts se traversent au milieu
# du geste : l'audit a relevé 355 traversées à l'étape 0,9 de Neutral→Fist,
# alors que les deux extrémités sont nettes.
resultat["transitions"] = {}
# ═══ UNE ACTION PRÉSENTE NE SE REMPLACE PAS PAR UNE DROITE (§11.3) ═══
#
# Ce vérificateur RECALCULAIT la transition — la pose cible multipliée par la
# fraction. Il mesurait donc un mouvement que personne n'anime, et un
# contournement lui était invisible par construction : le pouce d'un poing
# passe par l'extérieur, la droite coupe le coin et traverse l'index.
#
# Quand l'action `Neutral_to_<pose>` existe, on joue SES images. Elle fait
# autorité, et la substituer serait juger autre chose que ce qui est livré.
try:
    import transitions as _trans_mod
except Exception:                                            # noqa: BLE001
    _trans_mod = None

resultat["transitions_reelles"] = {}
for _cible in ("Hand_Fist", "Hand_Point", "Hand_Pinch", "Hand_OK",
               "Hand_Cupped", "Hand_Pinky_Thumb"):
    _nom_act = f"Neutral_to_{_cible}"
    if _nom_act in ACTIONS and _trans_mod is not None:
        _act_r = ACTIONS[_nom_act]
        _fr = {}
        for _img in range(1, _trans_mod.IMAGES_TUTO + 1):
            _trans_mod.rejouer(rig, SIDE, _act_r, _img)
            _t = traversees()
            if _t:
                _fr[str(_img)] = _t
        neutre()
        resultat["transitions_reelles"][_nom_act] = _fr or "aucune"
        exiger(f"{_nom_act} · aucune auto-intersection sur ses images",
               not _fr, _fr or "aucune", "aucune à chaque image")
        continue
    # Pas d'action réelle : on retombe sur l'échantillonnage linéaire, et on le
    # DIT. Un repli silencieux ferait passer une mesure dégradée pour la bonne.
    if _cible in ACTIONS:
        print(f"ATLAS_TRANSITION_SANS_ACTION {_cible} — "
              f"échantillonnage linéaire de repli, moins sévère")
    if _cible not in ACTIONS:
        continue
    _fautes = {}
    for _k in range(11):
        _u = _k / 10.0
        neutre()
        rig.animation_data_create()
        rig.animation_data.action = ACTIONS[_cible]
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        # Interpolation depuis le repos : on relit la pose cible puis on la
        # ramène à la fraction voulue, os par os et propriété par propriété.
        _cible_rot = {pb.name: tuple(pb.rotation_euler) for pb in rig.pose.bones}
        _cible_prop = {k: float(pbh[k]) for k in pbh.keys()
                       if isinstance(pbh[k], float)}
        neutre()
        for _nb, _r in _cible_rot.items():
            rig.pose.bones[_nb].rotation_euler = tuple(x * _u for x in _r)
        for _kp, _vp in _cible_prop.items():
            pbh[_kp] = _vp * _u
        rig.update_tag()
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        bpy.context.view_layer.update()
        _t = traversees()
        if _t:
            _fautes[f"{_u:.1f}"] = _t
    resultat["transitions"][f"Neutral→{_cible}"] = _fautes or "aucune"
    exiger(f"transition Neutral→{_cible} · aucune auto-intersection",
           not _fautes, _fautes or "aucune", "aucune à chaque étape")

# ═══════════════════════════════════════════════════════════════════
#   CE QUE LE VÉRIFICATEUR NE CONTRÔLAIT PAS (§12.1)
# ═══════════════════════════════════════════════════════════════════
# Il jugeait les poses et les transitions, et rien d'autre. Or trois des quatre
# blocages du chat 2 vivaient hors de son regard : le creusement de la paume,
# la fermeture réelle du poing, et la somme des poids. Un vérificateur qui ne
# regarde pas là où les défauts sont ne peut que les déclarer absents.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "atelier"))
try:
    import mesures_paume
except Exception as _e:                                   # noqa: BLE001
    mesures_paume = None
    print(f"ATLAS_VERIF_SANS_MESURES_PAUME {_e}")

if mesures_paume is not None:
    # ── Cup : voûte, resserrement, convergence, et la MONOTONIE du trajet ──
    _dom_v = {i: n for i, n in DOM.items()}
    _palm = mesures_paume.direction_palmaire(rig, geo, SIDE, _dom_v)
    _pau = mesures_paume.paume_sans_le_pouce(_dom_v, SIDE)

    def _mesure_cup():
        _t = mesures_paume.tetes_metacarpiennes(rig, SIDE)
        _p, _ = evalue()
        return (mesures_paume.arc_transverse(_p, _t, _palm, _pau),
                mesures_paume.largeur_paume(_t),
                mesures_paume.pouce_auriculaire(_t))

    neutre()
    _cup_pas = []
    for _k in range(21):
        _c = _k / 20.0
        neutre()
        pbh["Cup"] = _c
        rig.update_tag()
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        bpy.context.view_layer.update()
        _a, _l, _pa = _mesure_cup()
        _cup_pas.append({"cup": round(_c, 2), "arc_mm": round(_a, 2),
                         "largeur_mm": round(_l, 2),
                         "pouce_auriculaire_mm": round(_pa, 2),
                         "traversees": sum(x["sommets"] for x in traversees())})
    neutre()
    _d_arc = _cup_pas[-1]["arc_mm"] - _cup_pas[0]["arc_mm"]
    _d_lar = _cup_pas[-1]["largeur_mm"] - _cup_pas[0]["largeur_mm"]
    _d_pa = (_cup_pas[-1]["pouce_auriculaire_mm"]
             - _cup_pas[0]["pouce_auriculaire_mm"])
    _recul_l = max(_cup_pas[i + 1]["largeur_mm"] - _cup_pas[i]["largeur_mm"]
                   for i in range(20))
    _recul_a = max(_cup_pas[i]["arc_mm"] - _cup_pas[i + 1]["arc_mm"]
                   for i in range(20))
    resultat["cup"] = {"pas": _cup_pas, "gain_arc_mm": round(_d_arc, 2),
                       "gain_largeur_mm": round(_d_lar, 2),
                       "gain_pouce_auriculaire_mm": round(_d_pa, 2)}
    exiger("Cup · la paume se voûte", _d_arc >= 6.0,
           f"{_d_arc:+.2f} mm", "≥ +6 mm")
    exiger("Cup · la paume se resserre", _d_lar <= -6.0,
           f"{_d_lar:+.2f} mm", "≤ −6 mm")
    exiger("Cup · l'auriculaire rejoint le pouce", _d_pa <= -4.0,
           f"{_d_pa:+.2f} mm", "≤ −4 mm")
    exiger("Cup · le trajet ne repart jamais en arrière",
           _recul_l <= 0.5 and _recul_a <= 0.5,
           f"largeur {_recul_l:+.2f} / flèche {_recul_a:+.2f}", "≤ 0,50 mm")
    exiger("Cup · aucune auto-intersection sur les 21 pas",
           sum(p["traversees"] for p in _cup_pas) == 0,
           sum(p["traversees"] for p in _cup_pas), "0 sommet")

# ── Le poing se ferme-t-il vraiment ? (§12.1) ──
# `Hand_Fist` peut exister, être propre, et ne fermer qu'à 60 %. Une pose
# nommée « poing » qui n'en est pas un passait sans un mot.
if "Hand_Fist" in ACTIONS:
    appliquer(ACTIONS["Hand_Fist"])
    _fist = float(pbh["Fist"]) if "Fist" in pbh.keys() else None
    neutre()
    resultat["fermeture_du_poing"] = _fist
    exiger("le poing se ferme complètement", _fist is not None and _fist >= 0.999,
           _fist if _fist is not None else "propriété absente", "Fist = 1,0")

# ── La somme des poids déformants (§12.1) ──
_os_def = {pb.name for pb in rig.pose.bones if pb.bone.use_deform}
_hors, _trop = 0, 0
for _v in geo.data.vertices:
    _wd = [g.weight for g in _v.groups
           if g.group in _ng and _ng[g.group] in _os_def and g.weight > 0.005]
    if not _wd:
        continue
    if abs(sum(_wd) - 1.0) > 0.02:
        _hors += 1
    if len(_wd) > 4:
        _trop += 1
resultat["poids"] = {"somme_hors_tolerance": _hors, "plus_de_4_influences": _trop}
exiger("somme des poids déformants à 1,00 ± 0,02", _hors == 0, _hors, "0 sommet")
exiger("au plus 4 influences de déformation", _trop == 0, _trop, "0 sommet")

# ── les drivers ──
drv = [d.data_path for d in (rig.animation_data.drivers
                             if rig.animation_data else []) if not d.driver.is_valid]
exiger("tous les drivers sont valides", not drv, drv or "aucun invalide",
       "aucun invalide")

# ═══ LES CORRECTIFS ET LES SHAPE KEYS (§12.1) ═══
#
# Un correctif de volume est un os déformant SANS contrôleur : rien ne le
# surveille, et c'est précisément ce qui le rend dangereux. Au repos il doit
# être rigoureusement à zéro — un correctif qui déplace la chair au repos
# décale l'origine de TOUTES les autres mesures, sans qu'aucune d'elles ne le
# signale.
neutre()
_corr_os = [pb for pb in rig.pose.bones if pb.name.endswith(f"_corr{SIDE}")]
_corr_bouge = {}
for _pb in _corr_os:
    _dep = _pb.location.length * 1000.0
    _rot = max(abs(math.degrees(x)) for x in _pb.rotation_euler)
    if _dep > 0.001 or _rot > 0.01:
        _corr_bouge[_pb.name] = {"translation_mm": round(_dep, 4),
                                 "rotation_deg": round(_rot, 4)}
resultat["os_correctifs"] = {"nombre": len(_corr_os),
                             "non_nuls_au_repos": _corr_bouge or "aucun"}
exiger("les os correctifs sont à zéro au repos", not _corr_bouge,
       _corr_bouge or "aucun", "translation et rotation nulles")

# Les shape keys : présence, valeur au repos, et driver valide. Une key
# sculptée qui reste active au repos déforme la pose neutre en silence.
_keys = (geo.data.shape_keys.key_blocks
         if geo.data.shape_keys is not None else [])
_keys_actives, _keys_sans_driver = {}, []
_chemins_drv = {d.data_path for d in (geo.data.shape_keys.animation_data.drivers
                                      if (geo.data.shape_keys is not None
                                          and geo.data.shape_keys.animation_data)
                                      else [])}
for _k in list(_keys)[1:]:                       # [0] est le Basis
    if abs(_k.value) > 1e-6:
        _keys_actives[_k.name] = round(_k.value, 5)
    if f'key_blocks["{_k.name}"].value' not in _chemins_drv:
        _keys_sans_driver.append(_k.name)
resultat["shape_keys"] = {
    "nombre": max(0, len(_keys) - 1),
    "actives_au_repos": _keys_actives or "aucune",
    "sans_driver": _keys_sans_driver or "aucune"}
exiger("aucune shape key active au repos", not _keys_actives,
       _keys_actives or "aucune", "valeur nulle au repos")
if len(_keys) > 1:
    exiger("chaque shape key est pilotée", not _keys_sans_driver,
           _keys_sans_driver or "aucune", "un driver par key")

# ═══ VALIDE NE VEUT PAS DIRE FONCTIONNEL (§12.2) ═══
#
# `is_valid` dit que Blender sait évaluer l'expression. Il ne dit RIEN sur ce
# qu'elle pilote. Un driver peut être vert et viser le mauvais os, le mauvais
# axe, ou une propriété que plus personne ne règle — le dépôt en a fait
# l'expérience : 25 drivers valides dont la rotation restait à 0,00°, parce
# qu'ils n'étaient pas ÉVALUÉS.
#
# On applique donc 0, puis 1, à chaque propriété publique, et on regarde si le
# maillage BOUGE. Une propriété qui ne déplace aucun sommet ne pilote rien,
# qu'elle soit déclarée valide ou non.
neutre()
_p_ref, _ = evalue()
_inertes, _bougent = [], {}
for _prop in sorted(k for k in pbh.keys() if isinstance(pbh[k], float)):
    neutre()
    pbh[_prop] = 1.0
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()
    _pp, _ = evalue()
    _d = max((a - b).length for a, b in zip(_p_ref, _pp)) * 1000
    _bougent[_prop] = round(_d, 3)
    if _d < 0.05:
        _inertes.append(_prop)
neutre()
resultat["proprietes_deplacement_mm"] = _bougent
# Les propriétés correctives PSD_* n'ont d'effet que si leur shape key existe :
# leur inertie est un fait à publier, pas un échec du rig tant que les
# correctifs ne sont pas construits.
_inertes_durs = [p for p in _inertes if not p.startswith("PSD_")]
exiger("chaque propriété pilote vraiment quelque chose", not _inertes_durs,
       _inertes_durs or "aucune inerte", "déplacement > 0,05 mm à la valeur 1")
if [p for p in _inertes if p.startswith("PSD_")]:
    print("ATLAS_PSD_INERTES " + json.dumps(
        [p for p in _inertes if p.startswith("PSD_")], ensure_ascii=False))

neutre()
resultat["echecs"] = echecs
print("\nATLAS_VERIFICATION " + json.dumps(resultat, ensure_ascii=False))
if echecs:
    print(f"\n{len(echecs)} critère(s) obligatoire(s) en échec.")
    sys.exit(2)
print("\nTous les critères vérifiés passent.")
