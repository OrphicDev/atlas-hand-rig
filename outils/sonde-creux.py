"""
SONDE DU CREUX PALMAIRE — la paume ne se creuse-t-elle pas, ou est-ce la
mesure qui ne le voit pas ?

La baseline du chat 2 rend un gain de **1,0 mm pour 6 exigés**. Deux lectures
sont possibles et elles ne se corrigent pas au même endroit :

  · le rig ne creuse vraiment pas — c'est l'anatomie qu'il faut reprendre ;
  · la grandeur mesurée ne répond pas au creusement — c'est la sonde.

`creux_palmaire()` prend le MAXIMUM, sur tous les sommets tenus par un
métacarpien, de la profondeur sous un plan **figé à la pose de repos**. Deux
soupçons, chacun testable :

  1. les sommets du métacarpien du POUCE en font partie. L'éminence thénar est
     la masse la plus saillante de la paume, et creuser les rayons 4 et 5 ne la
     déplace guère : si c'est elle qui tient le maximum, aucun creusement ne
     peut faire bouger le chiffre ;
  2. le plan ne suit pas la main. Une paume qui se creuse fait tourner ses
     rayons internes ; un plan immobile mesure alors autre chose.

On mesure donc QUATRE grandeurs le long de `Cup`, et c'est leur comportement
relatif qui tranche — pas mon intuition.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/sonde-creux.py -- FICHIER.blend [sortie.json]
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

_args = sys.argv[sys.argv.index("--") + 1:]
FICHIER = _args[0]
SORTIE = _args[1] if len(_args) > 1 else None
if not os.path.isfile(FICHIER):
    raise RuntimeError("fichier introuvable : " + FICHIER)
bpy.ops.wm.open_mainfile(filepath=FICHIER)

geo = next(o for o in bpy.data.objects if o.name.startswith("GEO_Hand")
           and "BACKUP" not in o.name)
rig = next(o for o in bpy.data.objects if o.name.startswith("RIG_Hand"))
SIDE = rig.name[len("RIG_Hand"):]
pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]
NOMS4 = ["index", "middle", "ring", "pinky"]


def evalue():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw = geo.matrix_world
    p = [mw @ v.co.copy() for v in m.vertices]
    ev.to_mesh_clear()
    return p


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


_ng = {g.index: g.name for g in geo.vertex_groups}
neutre()
_dom = {}
for v in geo.data.vertices:
    gs = [(g.weight, _ng[g.group]) for g in v.groups
          if g.weight > 0.01 and g.group in _ng]
    if gs:
        _dom[v.index] = max(gs)[1]

PAUME_TOUT = [i for i, n in _dom.items() if n.endswith(f"_meta{SIDE}")]
PAUME_SANS_POUCE = [i for i, n in _dom.items()
                    if n.endswith(f"_meta{SIDE}") and not n.startswith("DEF_thumb")]
THENAR = [i for i, n in _dom.items() if n == f"DEF_thumb_meta{SIDE}"]
if not PAUME_SANS_POUCE or not THENAR:
    raise RuntimeError("la sonde ne trouve pas les masses palmaires qu'elle "
                       "prétend distinguer")


def os_monde(nom, bout=False):
    """La position POSÉE de l'os, en monde.

    ═══ head_local NE BOUGE JAMAIS ═══
    Premier jet : je lisais `rig.data.bones[nom].head_local`, c'est-à-dire la
    position de REPOS. Deux de mes quatre grandeurs sortaient donc constantes
    au centième sur tout le balayage — 71,99 mm et 50,30 mm, de `Cup = 0` à
    `Cup = 1`. Elles n'auraient jamais pu bouger, et j'aurais pu lire cette
    constance comme « le creusement ne rapproche pas l'auriculaire du pouce »,
    ce qui est exactement la conclusion que Sacha attend du cerclage rouge.
    Une sonde qui rend une constante ne mesure pas : elle se tait.
    """
    pb = rig.pose.bones[nom]
    return rig.matrix_world @ (pb.tail if bout else pb.head)


# ── LE CÔTÉ PAUME, PAR LE MOUVEMENT ──
# Le signe d'une normale construite est arbitraire. On l'établit en fléchissant.
neutre()
_p0 = evalue()
pbh["Fist"] = 0.5
rafraichir()
_p1 = evalue()
neutre()
_bouts = [i for i, n in _dom.items() if n.endswith(f"_03{SIDE}")]
_dep = sum(((_p1[i] - _p0[i]) for i in _bouts), mathutils.Vector((0, 0, 0)))
POIGNET = os_monde(f"DEF_hand{SIDE}")
_knuck0 = {n: os_monde(f"DEF_{n}_01{SIDE}") for n in NOMS4}
_axe = ((sum(_knuck0.values(), mathutils.Vector((0, 0, 0))) / 4) - POIGNET).normalized()
PALMAIRE = (_dep - _axe * _dep.dot(_axe)).normalized()

# ── LA GRANDEUR DU DÉPÔT, REPRODUITE ──
# Plan FIGÉ par les jointures et le poignet au repos, maximum sur toute la
# paume. C'est elle qui rend 21,0 → 22,0 mm.
_plan_pts = list(_knuck0.values()) + [POIGNET]
_C = sum(_plan_pts, mathutils.Vector((0, 0, 0))) / len(_plan_pts)
_N = ((_knuck0["index"] - POIGNET).cross(_knuck0["pinky"] - POIGNET)).normalized()
if _N.dot(PALMAIRE) < 0:
    _N = -_N


def creux_fige(p, sommets):
    return max(0.0, max((_C - p[i]).dot(_N) for i in sommets)) * 1000.0


def arc_transverse(p):
    """La flèche de l'ARC transverse, mesurée sur la pose COURANTE.

    L'arc palmaire, c'est la corde qui joint la tête du métacarpien de l'index
    à celle de l'auriculaire, et la flèche que la chair creuse dessous. Les
    deux extrémités SUIVENT la main : creuser les rapproche, et le creux se
    mesure par rapport à elles, jamais par rapport à un plan d'hier.
    """
    a, b = os_monde(f"DEF_index_01{SIDE}"), os_monde(f"DEF_pinky_01{SIDE}")
    u = (b - a)
    if u.length < 1e-9:
        return 0.0
    u = u.normalized()
    # composante palmaire perpendiculaire à la corde
    n = (PALMAIRE - u * PALMAIRE.dot(u))
    if n.length < 1e-9:
        return 0.0
    n = n.normalized()
    return max(0.0, max((p[i] - a).dot(n) for i in PAUME_SANS_POUCE)) * 1000.0


def largeur_paume():
    return (os_monde(f"DEF_pinky_01{SIDE}")
            - os_monde(f"DEF_index_01{SIDE}")).length * 1000.0


def pouce_auriculaire():
    """Le cerclage rouge de Sacha : les deux TÊTES métacarpiennes.

    ═══ UNE BASE NE BOUGE PAS, C'EST SA DÉFINITION ═══
    Deuxième jet : je mesurais tête à tête sur les `head`, c'est-à-dire les
    BASES des métacarpiens — celles qui s'articulent au carpe. Un métacarpien
    tourne autour de sa base : elle est donc immobile par construction, et ma
    grandeur rendait 50,30 mm à tous les pas. J'aurais lu « le creusement ne
    rapproche pas l'auriculaire du pouce » alors que je mesurais deux points
    qui ne pouvaient pas se rapprocher.

    Ce que Sacha entoure, ce sont les deux TÊTES : le bout distal du
    métacarpien du pouce et celui de l'auriculaire.
    """
    return (os_monde(f"DEF_pinky_meta{SIDE}", bout=True)
            - os_monde(f"DEF_thumb_meta{SIDE}", bout=True)).length * 1000.0


pas = []
print(f"{'Cup':>5} {'figé/tout':>11} {'figé/s.pouce':>13} {'arc':>8} "
      f"{'largeur':>9} {'pouce-auric':>12}")
for _k in range(11):
    c = _k / 10.0
    neutre()
    pbh["Cup"] = c
    rafraichir()
    p = evalue()
    ligne = {"cup": round(c, 1),
             "fige_toute_la_paume_mm": round(creux_fige(p, PAUME_TOUT), 2),
             "fige_sans_le_pouce_mm": round(creux_fige(p, PAUME_SANS_POUCE), 2),
             "arc_transverse_mm": round(arc_transverse(p), 2),
             "largeur_paume_mm": round(largeur_paume(), 2),
             "pouce_auriculaire_mm": round(pouce_auriculaire(), 2)}
    pas.append(ligne)
    print(f"{c:5.1f} {ligne['fige_toute_la_paume_mm']:11.2f} "
          f"{ligne['fige_sans_le_pouce_mm']:13.2f} "
          f"{ligne['arc_transverse_mm']:8.2f} "
          f"{ligne['largeur_paume_mm']:9.2f} "
          f"{ligne['pouce_auriculaire_mm']:12.2f}")
neutre()

# ── QUI RÉPOND, ET DE COMBIEN ──
gains = {k: round(pas[-1][k] - pas[0][k], 2) for k in pas[0] if k != "cup"}
# Le sommet qui TIENT le maximum de la grandeur figée : s'il appartient au
# thénar, la mesure ne pouvait pas voir le creusement des rayons internes.
neutre()
p = evalue()
_i_max = max(PAUME_TOUT, key=lambda i: (_C - p[i]).dot(_N))
tenu_par = _dom[_i_max]

resultat = {"fichier": os.path.basename(FICHIER), "balayage": pas,
            "gains_de_Cup_0_a_1_mm": gains,
            "maximum_de_la_grandeur_figee_tenu_par": tenu_par,
            "verdict": ("la sonde du dépôt est aveugle au creusement"
                        if abs(gains["fige_toute_la_paume_mm"]) < 2.0
                        and gains["arc_transverse_mm"] >= 2.0
                        else "les deux grandeurs s'accordent")}
print("\nATLAS_SONDE_CREUX " + json.dumps(resultat, ensure_ascii=False))
if SORTIE:
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=1)

print(f"\nGains de Cup 0 → 1 : {gains}")
print(f"Le maximum de la grandeur figée est tenu par : {tenu_par}")
print(f"Verdict : {resultat['verdict']}")
