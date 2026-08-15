"""
PLAYBLASTS DES SIX TRANSITIONS.

Le paquet d'audit du chat 1 porte « Transition videos: AUCUNE ». Les
échantillons numériques à 11 étapes existaient, mais rien qui se regarde : or
une traversée à `t = 0,8` se lit en une seconde sur une vidéo, et se cherche
dix minutes dans un JSON.

Cet outil rejoue chaque transition DE LA MÊME FAÇON que `verifier-rig.py` les
mesure — interpolation linéaire depuis le repos, os par os et propriété par
propriété. Une vidéo qui montrerait un autre mouvement que celui qui est mesuré
ne prouverait rien.

L'éclairage vient d'`atelier/eclairage.py` : exposition verrouillée, clay
neutre, key rasante. Pas de lumière improvisée pour la vidéo et une autre pour
les images fixes.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/playblast-transitions.py -- FICHIER.blend DOSSIER [images]

`images` (optionnel) écrit aussi la planche des étapes 0,0 · 0,2 … 1,0 à côté
des vidéos.
"""
import json
import math
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
_racine = os.path.dirname(_ici)
sys.path.insert(0, os.path.join(_racine, "atelier"))
import eclairage                                              # noqa: E402

_args = sys.argv[sys.argv.index("--") + 1:]
FICHIER = _args[0]
DOSSIER = _args[1] if len(_args) > 1 else "videos"
PLANCHE = len(_args) > 2 and _args[2] == "images"
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

# Les contrôleurs ne doivent pas apparaître dans le rendu : on filme la chair.
rig.hide_render = True
for o in bpy.data.objects:
    if o is not geo and o.type == "MESH":
        o.hide_render = True

IMAGES_PAR_TRANSITION = 25          # 1 s à 25 i/s, du repos à la pose
TRANSITIONS = ("Hand_Fist", "Hand_Point", "Hand_Pinch", "Hand_OK",
               "Hand_Cupped", "Hand_Pinky_Thumb")


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
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def lire_pose(nom):
    """La pose cible, lue exactement comme le vérificateur la lit."""
    neutre()
    rig.animation_data_create()
    rig.animation_data.action = ACTIONS[nom]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    rot = {pb.name: tuple(pb.rotation_euler) for pb in rig.pose.bones}
    props = {k: float(pbh[k]) for k in pbh.keys() if isinstance(pbh[k], float)}
    neutre()
    return rot, props


def poser_fraction(rot, props, u):
    """La même interpolation que celle que `verifier-rig.py` mesure."""
    neutre()
    for nb, r in rot.items():
        rig.pose.bones[nb].rotation_euler = tuple(x * u for x in r)
    for k, v in props.items():
        pbh[k] = v * u
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def sommets():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw = geo.matrix_world
    p = [mw @ v.co.copy() for v in m.vertices]
    ev.to_mesh_clear()
    return p


# ── LE CÔTÉ PAUME, MESURÉ ET NON SUPPOSÉ ──
# Le signe d'une normale construite est arbitraire : la première planche du
# chat 1 étiquetait « paume » une vue du DOS. On l'établit par le mouvement —
# en fléchissant, les bouts des doigts partent DU CÔTÉ DE LA PAUME.
neutre()
_p0 = sommets()
_rot_f, _props_f = lire_pose("Hand_Fist")
poser_fraction(_rot_f, _props_f, 0.5)
_p1 = sommets()
neutre()
_ng = {g.index: g.name for g in geo.vertex_groups}
_dom = {}
for v in geo.data.vertices:
    gs = [(g.weight, _ng[g.group]) for g in v.groups
            if g.weight > 0.01 and g.group in _ng]
    if gs:
        _dom[v.index] = max(gs)[1]
_bouts = [i for i, n in _dom.items() if n.endswith(f"_03{SIDE}")]
_dep = sum(((_p1[i] - _p0[i]) for i in _bouts), mathutils.Vector((0, 0, 0)))

# L'axe de la main : du poignet vers les jointures.
_meta = [i for i, n in _dom.items() if n.endswith(f"_meta{SIDE}")]
_centre = sum((_p0[i] for i in _meta), mathutils.Vector((0, 0, 0))) / len(_meta)
_main = [i for i in _dom if not _dom[i].startswith(f"DEF_hand")]
_boite_min = mathutils.Vector((min(_p0[i][k] for i in _main) for k in range(3)))
_boite_max = mathutils.Vector((max(_p0[i][k] for i in _main) for k in range(3)))
_axe = (sum((_p0[i] for i in _bouts), mathutils.Vector((0, 0, 0)))
        / len(_bouts) - _centre).normalized()
PALMAIRE = (_dep - _axe * _dep.dot(_axe)).normalized()
print("ATLAS_PLAYBLAST_COTE " + json.dumps(
    {"palmaire": [round(x, 3) for x in PALMAIRE],
     "axe_de_la_main": [round(x, 3) for x in _axe]}, ensure_ascii=False))

# ── LE STUDIO ──
sc = bpy.context.scene
_verrous = eclairage.poser_studio(sc, materiau_clay=True, objets_clay=[geo])
print("ATLAS_PLAYBLAST_STUDIO " + json.dumps(_verrous, ensure_ascii=False,
                                             default=str))
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {
    i.identifier for i in
    sc.bl_rna.properties["render"].fixed_type.bl_rna.properties[
        "engine"].enum_items} else sc.render.engine
sc.render.resolution_x = sc.render.resolution_y = 720
sc.render.fps = 25
sc.frame_start, sc.frame_end = 1, IMAGES_PAR_TRANSITION

_cam = eclairage.cadrer(geo, -PALMAIRE, _centre, 0.215)
_ecl = eclairage.eclairer_rasant(_centre, -PALMAIRE, PALMAIRE, "paume")
print("ATLAS_PLAYBLAST_LUMIERE " + json.dumps(_ecl, ensure_ascii=False,
                                              default=str))

_fait = []
for _cible in TRANSITIONS:
    if _cible not in ACTIONS:
        print(f"ATLAS_PLAYBLAST_ABSENTE {_cible}")
        continue
    rot, props = lire_pose(_cible)
    # On CUIT la transition en clés : une par image, à la fraction exacte que
    # le vérificateur mesure. La vidéo montre alors le mouvement mesuré, pas
    # une approximation de courbe.
    neutre()
    act = bpy.data.actions.new(f"PLAYBLAST_Neutral_vers_{_cible}")
    rig.animation_data_create()
    rig.animation_data.action = act
    for f in range(1, IMAGES_PAR_TRANSITION + 1):
        u = (f - 1) / (IMAGES_PAR_TRANSITION - 1)
        poser_fraction(rot, props, u)
        for nb in rot:
            rig.pose.bones[nb].keyframe_insert("rotation_euler", frame=f)
        for k in props:
            pbh.keyframe_insert(f'["{k}"]', frame=f)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    sortie = os.path.join(DOSSIER, f"Neutral-vers-{_cible}.mp4")
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "HIGH"
    sc.render.filepath = sortie[:-4]
    bpy.ops.render.render(animation=True)
    _reel = sortie[:-4] + f"0001-{IMAGES_PAR_TRANSITION:04d}.mp4"
    if os.path.exists(_reel):
        os.replace(_reel, sortie)
    ok = os.path.exists(sortie) and os.path.getsize(sortie) > 4096
    print(f"ATLAS_PLAYBLAST {_cible} : "
          f"{'écrit' if ok else 'MANQUANT'} {sortie} "
          f"({os.path.getsize(sortie) if ok else 0} octets)")
    _fait.append({"transition": f"Neutral→{_cible}", "fichier": sortie,
                  "octets": os.path.getsize(sortie) if ok else 0,
                  "images": IMAGES_PAR_TRANSITION, "ecrit": ok})

    if PLANCHE:
        sc.render.image_settings.file_format = "PNG"
        for _u in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
            poser_fraction(rot, props, _u)
            _png = os.path.join(DOSSIER,
                                f"etape-{_cible}-{_u:.1f}".replace(".", "_")
                                + ".png")
            eclairage.rendre(_png, sc)
    rig.animation_data.action = None
    bpy.data.actions.remove(act)

neutre()
_manquantes = [x for x in _fait if not x["ecrit"]]
print("\nATLAS_PLAYBLASTS " + json.dumps(
    {"dossier": DOSSIER, "transitions": _fait,
     "manquantes": _manquantes or "aucune"}, ensure_ascii=False))
if len(_fait) != len(TRANSITIONS) or _manquantes:
    print(f"\n{len(TRANSITIONS) - len(_fait) + len(_manquantes)} playblast(s) "
          f"manquant(s).")
    sys.exit(2)
print(f"\nLes {len(TRANSITIONS)} playblasts sont écrits.")
