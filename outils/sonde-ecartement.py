"""
SONDE D'ÉCARTEMENT — reproduire, ou réfuter, le signalement « Spread = 1 fait
se traverser majeur et annulaire ».

Le chat 1 a relevé ce défaut par une détection BVH indépendante, JAMAIS
confirmée par le pipeline principal. Un chiffre qui ne vient pas de
l'instrument officiel n'est pas une mesure : c'est une rumeur. Cette sonde le
remesure avec la machinerie EXACTE de `verifier-rig.py` — mêmes seuils, mêmes
15 couples, mêmes deux sens — pour que les nombres soient comparables ligne à
ligne.

Elle mesure DEUX choses à chaque pas, parce que « ça se traverse » et « ça
part du mauvais côté » ne sont pas la même question :

  1. les traversées, par couple de familles ;
  2. l'ÉVENTAIL : l'écart réel entre bouts de doigts voisins. C'est lui qui dit
     si l'écartement écarte ou s'il rapproche. Un signe inversé se lit ici,
     pas dans un compte de sommets.

La sonde se contre-éprouve avant de rendre le moindre verdict (voir plus bas) :
sans cela, un zéro se lirait comme une mesure alors qu'il ne serait qu'un
silence.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/sonde-ecartement.py -- FICHIER.blend [sortie.json]
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

# Les seuils du vérificateur, repris tels quels. Les changer ici rendrait les
# deux séries de chiffres incomparables, ce qui est précisément le défaut que
# ce chantier corrige.
PROFONDEUR_MINIMALE = 0.0005
ECART_REPOS_MINIMAL = 0.014


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


def rafraichir():
    # Les drivers ne s'évaluent pas en mode fond sans changement d'image. Sans
    # ces trois lignes on mesure une main immobile — et une main immobile
    # revient toujours exactement à sa pose de repos, donc elle passe tout.
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


_ng = {g.index: g.name for g in geo.vertex_groups}
neutre()
P_REPOS, _ = evalue()
DOM = {}
for v in geo.data.vertices:
    gs = [(g.weight, _ng.get(g.group, "")) for g in v.groups if g.weight > 0.01]
    if gs:
        DOM[v.index] = max(gs)[1]


def famille(n):
    for f in NOMS4 + ["thumb"]:
        if n.startswith(f"DEF_{f}_"):
            return f
    return "hand" if n.startswith("DEF_") else None


def traversees():
    _p, _n = evalue()
    par = {}
    for i, nm in DOM.items():
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


# ── L'ÉVENTAIL ──
# Le bout de chaque doigt est pris sur le MAILLAGE, pas sur l'os : c'est la
# chair qui se traverse, et un os peut diverger pendant que la chair converge.
BOUTS = {}
for _n4 in NOMS4:
    _d = f"DEF_{_n4}_03{SIDE}"
    BOUTS[_n4] = [i for i, nm in DOM.items() if nm == _d]
    if not BOUTS[_n4]:
        raise RuntimeError(f"aucun sommet dominé par {_d} : la sonde ne peut "
                           f"pas mesurer l'éventail")

VOISINS = [("index", "middle"), ("middle", "ring"), ("ring", "pinky")]


def eventail(_p):
    """Écart minimal, en mm, entre les chairs de deux bouts de doigts voisins."""
    out = {}
    for a, b in VOISINS:
        t = mathutils.kdtree.KDTree(len(BOUTS[b]))
        for k, i in enumerate(BOUTS[b]):
            t.insert(_p[i], k)
        t.balance()
        out[f"{a}/{b}"] = round(min(t.find(_p[i])[2] for i in BOUTS[a]) * 1000, 2)
    return out


def rotation_ecart_deg():
    """Ce que les drivers appliquent RÉELLEMENT autour de l'axe d'écartement."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = rig.evaluated_get(dg)
    return {n: round(math.degrees(
        ev.pose.bones[f"MCH_{n}_01_result{SIDE}"].rotation_euler[2]), 3)
        for n in NOMS4}


# ═══ ON VÉRIFIE LA SONDE AVANT DE LIRE SES VERDICTS ═══
# Deux contre-épreuves, et la sonde refuse de conclure si l'une échoue.
#   1. au repos, une main saine ne se traverse nulle part : si la sonde y
#      trouve quelque chose, elle mesure autre chose que ce qu'elle prétend ;
#   2. une fermeture pleine traverse franchement : si la sonde n'y voit rien,
#      son silence à Spread = 1 ne vaudrait rien non plus.
neutre()
_faux_positifs = traversees()
_p0, _ = evalue()
_eventail_repos = eventail(_p0)

neutre()
pbh["Fist"] = 1.0
rafraichir()
_controle = sum(x["sommets"] for x in traversees())
neutre()

_sonde = {"faux_positifs_au_repos": _faux_positifs or "aucun",
          "fermeture_pleine_sans_ecartement": _controle,
          "eventail_au_repos_mm": _eventail_repos,
          "verdict": ("utilisable" if not _faux_positifs and _controle > 100
                      else "INUTILISABLE")}
print("ATLAS_SONDE_CONTRE_EPREUVE " + json.dumps(_sonde, ensure_ascii=False))
if _sonde["verdict"] != "utilisable":
    raise RuntimeError(f"sonde d'écartement non fiable : {_sonde}")

# ── LE BALAYAGE, DE −1 À +1 PAR PAS DE 0,1 ──
pas = []
for _k in range(-10, 11):
    s = _k / 10.0
    neutre()
    pbh["Spread"] = s
    rafraichir()
    _p, _ = evalue()
    _t = traversees()
    _e = eventail(_p)
    _r = rotation_ecart_deg()
    pas.append({"spread": round(s, 1), "traversees": _t or "aucune",
                "total_sommets": sum(x["sommets"] for x in _t),
                "eventail_mm": _e, "rotation_ecart_deg": _r})
    print(f"ATLAS_ECARTEMENT spread={s:+.1f} "
          f"traversees={sum(x['sommets'] for x in _t):5d} "
          f"eventail={_e} rot={_r}")
neutre()

# ── LE VERDICT, TIRÉ DE LA MESURE ET NON DE L'INTENTION ──
# « L'écartement écarte » se prouve sur l'éventail : chaque couple voisin doit
# gagner de l'écart quand Spread monte, et en perdre quand il descend.
_bas, _zero, _haut = pas[0], pas[10], pas[20]
_sens = {}
for _cp in _eventail_repos:
    _sens[_cp] = {"a_spread_-1_mm": _bas["eventail_mm"][_cp],
                  "a_spread_0_mm": _zero["eventail_mm"][_cp],
                  "a_spread_+1_mm": _haut["eventail_mm"][_cp],
                  "ecarte_bien": _haut["eventail_mm"][_cp] > _zero["eventail_mm"][_cp]
                  > _bas["eventail_mm"][_cp]}
_inverses = [c for c, v in _sens.items() if not v["ecarte_bien"]]
_fautifs = [p for p in pas if p["total_sommets"]]

resultat = {"fichier": os.path.basename(FICHIER),
            "contre_epreuve_de_la_sonde": _sonde,
            "sens_de_l_eventail": _sens,
            "couples_dont_l_ecartement_ne_separe_pas": _inverses or "aucun",
            "pas_avec_traversees": [{"spread": p["spread"],
                                     "traversees": p["traversees"]}
                                    for p in _fautifs] or "aucun",
            "balayage": pas}
print("\nATLAS_SONDE_ECARTEMENT " + json.dumps(resultat, ensure_ascii=False))
if SORTIE:
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=1)
    print("écrit : " + SORTIE)

print(f"\nCouples dont l'écartement ne sépare pas : {_inverses or 'aucun'}")
print(f"Pas du balayage avec au moins une traversée : {len(_fautifs)} sur 21")
if _inverses or _fautifs:
    sys.exit(2)
print("L'écartement écarte, et ne traverse à aucun pas.")
