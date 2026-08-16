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
