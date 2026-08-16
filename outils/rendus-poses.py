"""
LES RENDUS DE PREUVE, DEPUIS UN .blend (§13).

═══ POURQUOI CET OUTIL EXISTE ═══

Les rendus vivaient dans `rig-main.py`, donc derriere quatre heures de
reconstruction. Refaire une image demandait de tout rejouer — et c'est
exactement pour ca que les preuves visuelles du chat 1 n'ont jamais ete
refaites malgre le defaut releve sur l'une d'elles.

Ici, on part du `.blend` livre. Meme studio, meme exposition verrouillee, meme
clay : `atelier/eclairage.py` est la seule source de lumiere du depot, et une
image rendue autrement ne serait pas comparable aux autres.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/rendus-poses.py -- FICHIER.blend DOSSIER [gros-plans]
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

import bpy
import mathutils

_ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_ici), "atelier"))
import eclairage                                              # noqa: E402

_args = sys.argv[sys.argv.index("--") + 1:]
FICHIER, DOSSIER = _args[0], _args[1]
GROS_PLANS = len(_args) > 2 and _args[2] == "gros-plans"
if not os.path.isfile(FICHIER):
    raise RuntimeError("fichier introuvable : " + FICHIER)
os.makedirs(DOSSIER, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=FICHIER)

geo = next(o for o in bpy.data.objects if o.name.startswith("GEO_Hand")
           and "BACKUP" not in o.name)
rig = next(o for o in bpy.data.objects if o.name.startswith("RIG_Hand"))
SIDE = rig.name[len("RIG_Hand"):]
pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]
ACTIONS = {a.name: a for a in bpy.data.actions}
rig.hide_render = True
for o in bpy.data.objects:
    if o is not geo and o.type == "MESH":
        o.hide_render = True


def rafraichir():
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def neutre():
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        if pb.rotation_mode == "QUATERNION":
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        else:
            pb.rotation_euler = (0.0, 0.0, 0.0)
    for k in list(pbh.keys()):
        if isinstance(pbh[k], float):
            pbh[k] = 0.0
    rafraichir()


def sommets():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw = geo.matrix_world
    p = [mw @ v.co.copy() for v in m.vertices]
    ev.to_mesh_clear()
    return p


_ng = {g.index: g.name for g in geo.vertex_groups}
neutre()
_dom = {}
for v in geo.data.vertices:
    gs = [(g.weight, _ng[g.group]) for g in v.groups
          if g.weight > 0.01 and g.group in _ng]
    if gs:
        _dom[v.index] = max(gs)[1]

# ── LE COTE PAUME, PAR LE MOUVEMENT ──
# Le signe d'une normale construite est arbitraire : la premiere planche du
# chat 1 etiquetait « paume » une vue du DOS.
neutre()
_p0 = sommets()
if "Hand_Fist" in ACTIONS:
    rig.animation_data_create()
    rig.animation_data.action = ACTIONS["Hand_Fist"]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    _p1 = sommets()
    neutre()
else:
    pbh["Fist"] = 0.6
    rafraichir()
    _p1 = sommets()
    neutre()
_bouts = [i for i, n in _dom.items() if n.endswith(f"_03{SIDE}")]
_meta = [i for i, n in _dom.items() if n.endswith(f"_meta{SIDE}")]
_centre = sum((_p0[i] for i in _meta), mathutils.Vector((0, 0, 0))) / len(_meta)
_axe = (sum((_p0[i] for i in _bouts), mathutils.Vector((0, 0, 0)))
        / len(_bouts) - _centre).normalized()
_dep = sum(((_p1[i] - _p0[i]) for i in _bouts), mathutils.Vector((0, 0, 0)))
PALMAIRE = (_dep - _axe * _dep.dot(_axe)).normalized()
_thumb = [i for i, n in _dom.items() if n.startswith(f"DEF_thumb_")]
_c_thumb = sum((_p0[i] for i in _thumb), mathutils.Vector((0, 0, 0))) / len(_thumb)
_T = (_c_thumb - _centre)
Tp = (_T - _axe * _T.dot(_axe) - PALMAIRE * _T.dot(PALMAIRE)).normalized()
print("ATLAS_RENDUS_COTE " + json.dumps(
    {"palmaire": [round(x, 3) for x in PALMAIRE],
     "vers_le_pouce": [round(x, 3) for x in Tp]}, ensure_ascii=False))

sc = bpy.context.scene
_verrous = eclairage.poser_studio(sc, materiau_clay=True, objets_clay=[geo])
# Le clay ne s applique qu a la main : le cyclo garde son propre gris.
print("ATLAS_RENDUS_STUDIO " + json.dumps(_verrous, ensure_ascii=False,
                                          default=str))
_main = [i for i in _dom if _dom[i] != f"DEF_hand{SIDE}"]

VUES = [("paume-A", PALMAIRE, +1), ("paume-B", PALMAIRE, -1),
        ("dos-A", -PALMAIRE, +1), ("dos-B", -PALMAIRE, -1),
        ("pouce", Tp, +1), ("auriculaire", -Tp, +1)]

_histos, _rendues = {}, 0


def rendre(nom, direction, cote, cadre=0.205, vise=None, source_deg=None):
    _p = sommets()
    _c = vise if vise is not None else (
        sum((_p[i] for i in _main), mathutils.Vector((0, 0, 0))) / len(_main))
    eclairage.cadrer(geo, direction, _c, cadre, scene=sc)
    # Un gros plan demande une lumiere plus DURE : le module dimensionne la
    # source avec la distance, donc son angle apparent reste constant, et sur
    # un sujet quatre fois plus petit les plis sont a l'echelle du flou.
    _r = {"key_angle_source_deg": source_deg} if source_deg else None
    # Le cyclo se repose a CHAQUE vue : il doit etre derriere le sujet vu de
    # cette camera-ci, pas de la precedente. Un fond pose une fois pour toutes
    # finit de profil et ne renvoie plus rien. Et il se pose APRES `_r`, sinon
    # il lit une variable qui n'existe pas encore — ce que la premiere version
    # de ce correctif faisait, et Blender l'a dit tout de suite.
    _f = eclairage.poser_fond(sc, _c, sc.camera.matrix_world.translation - _c,
                              cadre, reglages=_r)
    _e = eclairage.eclairer_rasant(_c, direction, direction, cote,
                                   largeur_sujet=cadre, scene=sc, reglages=_r)
    _h = eclairage.rendre(os.path.join(DOSSIER, nom + ".png"), sc)
    _histos[nom] = {"ecretage_pct": _h["ecretage_pct"],
                    "luminance_max": _h["luminance_max"],
                    "luminance_moyenne": _h["luminance_moyenne"],
                    "key_contre_normale_deg": round(
                        _e["key_angle_vs_normale_deg"], 1)}
    return _h


for _nom_a in sorted(ACTIONS):
    if not _nom_a.startswith("Hand_"):
        continue
    neutre()
    rig.animation_data_create()
    rig.animation_data.action = ACTIONS[_nom_a]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    for _nv, _dir, _cote in VUES:
        rendre(f"{_nom_a}-{_nv}", _dir, _cote)
        _rendues += 1
    print(f"ATLAS_RENDU {_nom_a} — {len(VUES)} vues")
neutre()

# ═══ LES GROS PLANS ET LES OVERLAYS (§13) ═══
#
# Un tableau dit COMBIEN de sommets se traversent, jamais OU. « 211 sommets »
# ne se corrige pas : c'est pour ca que ce defaut a survecu a deux chats. Les
# sommets fautifs sont peints en rouge, avec la MEME camera que la vue propre —
# deux cadrages differents rendraient la comparaison impossible a faire a
# l'oeil, ce qui est tout le travail de ces images.
if GROS_PLANS:
    _mat = bpy.data.materials.new("ATLAS_traversant")
    _mat.use_nodes = True
    _mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"] \
        .default_value = (0.85, 0.12, 0.10, 1.0)
    geo.data.materials.append(_mat)
    _irouge = len(geo.data.materials) - 1
    _PROF, _ECART = 0.0005, 0.014
    neutre()
    _prepos = sommets()

    def _fautifs():
        _p = sommets()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = geo.evaluated_get(dg)
        m = ev.to_mesh()
        m3 = geo.matrix_world.to_3x3()
        _n = [(m3 @ v.normal).normalized() for v in m.vertices]
        ev.to_mesh_clear()
        _fam = {}
        for i, nm in _dom.items():
            for f in ("index", "middle", "ring", "pinky", "thumb"):
                if nm.startswith(f"DEF_{f}_"):
                    _fam.setdefault(f, []).append(i)
                    break
            else:
                if nm.startswith("DEF_"):
                    _fam.setdefault("hand", []).append(i)
        _arb = {}
        for f, ii in _fam.items():
            t = mathutils.kdtree.KDTree(len(ii))
            for k, i in enumerate(ii):
                t.insert(_p[i], k)
            t.balance()
            _arb[f] = (t, ii)
        out = set()
        fs = sorted(_arb)
        for x in range(len(fs)):
            for y in range(x + 1, len(fs)):
                for a, b in ((fs[x], fs[y]), (fs[y], fs[x])):
                    tb, ib = _arb[b]
                    for i in _fam[a]:
                        co, k, d = tb.find(_p[i])
                        j = ib[k]
                        if (d < 0.008
                                and (_p[j] - _p[i]).dot(_n[j]) > _PROF
                                and (_prepos[i] - _prepos[j]).length > _ECART):
                            out.add(i)
        return out

    _ov = {}
    for _na in ("Hand_Pinch", "Hand_OK", "Hand_Pinky_Thumb", "Hand_Fist",
                "Hand_Point", "Hand_Cupped"):
        if _na not in ACTIONS:
            continue
        neutre()
        rig.animation_data_create()
        rig.animation_data.action = ACTIONS[_na]
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        _f = _fautifs()
        # Une face n'est peinte que si TOUS ses sommets sont fautifs : peindre
        # des qu'un seul l'est etalerait le rouge sur des zones saines et
        # rendrait l'image plus alarmante que la mesure.
        _np = 0
        for _poly in geo.data.polygons:
            if _f and all(v in _f for v in _poly.vertices):
                _poly.material_index = _irouge
                _np += 1
        rafraichir()
        rendre(f"overlay-{_na}-paume", PALMAIRE, +1)
        for _poly in geo.data.polygons:
            _poly.material_index = 0
        rafraichir()
        _ov[_na] = {"sommets_traversants": len(_f), "faces_peintes": _np}
        print(f"ATLAS_OVERLAY {_na} : {len(_f)} sommets, {_np} faces")
    neutre()
    print("ATLAS_OVERLAYS " + json.dumps(_ov, ensure_ascii=False))

print("\nATLAS_RENDUS " + json.dumps(
    {"dossier": DOSSIER, "images": _rendues, "histogrammes": _histos},
    ensure_ascii=False))

# Les memes trois criteres que le pipeline, pour que ces images soient jugees
# comme les siennes et non selon une autre regle.
_brulees = {k: v["ecretage_pct"] for k, v in _histos.items()
            if v["ecretage_pct"] > 2.0}
_plates = {k: round(v["luminance_max"] - v["luminance_moyenne"], 4)
           for k, v in _histos.items()
           if v["luminance_max"] - v["luminance_moyenne"] < 0.10}
_rasances = sorted({v["key_contre_normale_deg"] for v in _histos.values()})
print(f"\nimages : {_rendues}")
print(f"ecretees au-dela de 2 % : {_brulees or 'aucune'}")
print(f"sans relief (amplitude < 0,10) : {_plates or 'aucune'}")
print(f"rasance de la key : {_rasances} (exige 75 ± 5)")
if _brulees or _plates or not all(70.0 <= x <= 80.0 for x in _rasances):
    sys.exit(2)
print("Les trois criteres d'image passent.")
