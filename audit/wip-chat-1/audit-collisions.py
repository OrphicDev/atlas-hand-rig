"""
AUDIT DES AUTO-INTERSECTIONS DU RIG DE MAIN — poses ET transitions.

Ce script ne modifie rien : il ouvre le .blend livré, rejoue les 13 poses de la
bibliothèque, puis balaie 11 étapes de chaque transition Neutral → X, et compte
les sommets d'une famille de doigts qui sont passés DANS une autre.

La méthode de détection est reprise telle quelle de verifier-rig.py :
un sommet i de la famille A est dans la famille B si son plus proche voisin j
de B est à moins de 8 mm, que (pos[j]-pos[i])·normale[j] > 0,5 mm, ET que les
deux sommets étaient distants de plus de 14 mm AU REPOS — cette dernière
condition est indispensable, le maillage étant continu.

Deux différences assumées avec le vérificateur, qui sont l'objet même de l'audit :
  · les 15 couples de familles sont examinés, pas 5 ;
  · les deux sens sont comptés (A dans B et B dans A), pas un seul.

    blender --background --factory-startup --python audit-collisions.py
"""
import json
import os
import sys
import time

import bpy
import mathutils

# Chemin donné en argument : le script d'audit doit pouvoir juger n'importe
# quel .blend, pas seulement celui d'une machine.
BLEND = (sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv
         else "RIG_Hand.L-NON-VALIDE.blend")
SORTIE = "/tmp/atlas-agent-mesures/collisions.json"

# Les tolérances du vérificateur, à l'identique.
PROFONDEUR_MINIMALE = 0.0005   # 0,5 mm d'enfoncement
ECART_REPOS_MINIMAL = 0.014    # 14 mm d'écart au repos
RAYON = 0.008                  # 8 mm de voisinage

FAMILLES = ["thumb", "index", "middle", "ring", "pinky", "hand"]
COUPLES = [(FAMILLES[i], FAMILLES[j])
           for i in range(len(FAMILLES)) for j in range(i + 1, len(FAMILLES))]

POSES = ["Hand_Neutral", "Hand_Relaxed", "Hand_Open", "Hand_Spread_Min",
         "Hand_Fist_25", "Hand_Fist_50", "Hand_Fist_75", "Hand_Fist",
         "Hand_Point", "Hand_Pinch", "Hand_OK", "Hand_Cupped",
         "Hand_Pinky_Thumb"]
TRANSITIONS = ["Hand_Fist", "Hand_Point", "Hand_Pinch", "Hand_OK",
               "Hand_Cupped", "Hand_Pinky_Thumb"]
ETAPES = [round(i / 10.0, 1) for i in range(11)]

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=BLEND)

geo = next(o for o in bpy.data.objects
           if o.name.startswith("GEO_Hand") and "BACKUP" not in o.name)
rig = next(o for o in bpy.data.objects if o.name.startswith("RIG_Hand"))
SIDE = rig.name[len("RIG_Hand"):]
pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]
PROPS = [k for k in pbh.keys() if isinstance(pbh[k], float)]
CTRLS = [b.name for b in rig.data.bones if b.name.startswith("CTRL")]
ACTIONS = {a.name: a for a in bpy.data.actions}
manquantes = [p for p in POSES if p not in ACTIONS]
if manquantes:
    raise RuntimeError("poses absentes du fichier : " + ", ".join(manquantes))


# ─────────────────────────── évaluation du maillage ───────────────────────────
def evalue():
    """Positions et normales monde du maillage déformé, tel que le fait le
    vérificateur : la copie évaluée du dépendency graph, pas le maillage brut."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw, m3 = geo.matrix_world, geo.matrix_world.to_3x3()
    p = [mw @ v.co.copy() for v in m.vertices]
    try:
        n = [(m3 @ v.normal).normalized() for v in m.vertices]
    except AttributeError:                     # Blender 5.x : vertex_normals
        n = [(m3 @ mathutils.Vector(v)).normalized() for v in m.vertex_normals]
    ev.to_mesh_clear()
    return p, n


def rafraichir():
    """En mode fond, les drivers ne sont PAS réévalués sans changement d'image.
    Sans ces trois lignes, on mesure une main immobile."""
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def neutre():
    """Détacher l'action AVANT la remise à zéro : sinon les clés de la dernière
    pose rejouée écrasent la remise à zéro."""
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    for k in PROPS:
        pbh[k] = 0.0
    rafraichir()


def appliquer(nom):
    neutre()
    rig.animation_data_create()
    rig.animation_data.action = ACTIONS[nom]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


# ───────────────────── lecture des valeurs d'une action ──────────────────────
def valeurs_action(nom):
    """Blender 5.x : les courbes vivent dans les channelbags des strips, plus
    dans action.fcurves. On lit la valeur à l'image 1."""
    a = ACTIONS[nom]
    out = {}
    for lay in a.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    out[(fc.data_path, fc.array_index)] = fc.evaluate(1.0)
    return out


def poser_valeurs(v):
    """Applique un dictionnaire de valeurs directement sur la pose, sans action."""
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    for k in PROPS:
        pbh[k] = 0.0
    for (path, idx), val in v.items():
        try:
            if path.endswith(".rotation_euler"):
                nom_os = path.split('"')[1]
                rig.pose.bones[nom_os].rotation_euler[idx] = val
            elif path.endswith('"]'):          # pose.bones["CTRL_hand.L"]["Fist"]
                nom_os = path.split('"')[1]
                cle = path.split('"')[3]
                rig.pose.bones[nom_os][cle] = val
        except (KeyError, IndexError):
            pass
    rafraichir()


def melange(va, vb, t):
    cles = set(va) | set(vb)
    return {k: va.get(k, 0.0) * (1.0 - t) + vb.get(k, 0.0) * t for k in cles}


# ─────────────────────── familles et sommets dominants ───────────────────────
_ng = {g.index: g.name for g in geo.vertex_groups}
neutre()
P_REPOS, _ = evalue()

# DOM_PERMISSIF : le classement du vérificateur — tous les groupes de sommets
# concourent, y compris ceux qui ne correspondent à AUCUN os.
# DOM_STRICT : seuls les groupes de déformation réels (un os DEF porte le même
# nom) concourent. Les deux sont mesurés, pour montrer ce que le classement
# du vérificateur ajoute ou retire au compte.
OS_DEF = {b.name for b in rig.data.bones if b.name.startswith("DEF_")}
DOM_PERMISSIF, DOM_STRICT = {}, {}
for v in geo.data.vertices:
    gs = [(g.weight, _ng.get(g.group, "")) for g in v.groups if g.weight > 0.01]
    if gs:
        DOM_PERMISSIF[v.index] = max(gs)[1]
    gd = [t for t in gs if t[1] in OS_DEF]
    if gd:
        DOM_STRICT[v.index] = max(gd)[1]


def famille(n):
    for f in ("index", "middle", "ring", "pinky", "thumb"):
        if n.startswith(f"DEF_{f}_"):
            return f
    return "hand"


def repartir(dom):
    par = {}
    for i, nm in dom.items():
        par.setdefault(famille(nm), []).append(i)
    return par


PAR_PERMISSIF, PAR_STRICT = repartir(DOM_PERMISSIF), repartir(DOM_STRICT)
PAR, DOM = PAR_PERMISSIF, DOM_PERMISSIF          # classement courant

# Groupes de sommets qui ne portent le nom d'aucun os, et sommets concernés.
HORS_OS = sorted({nm for nm in DOM_PERMISSIF.values() if nm not in OS_DEF})
N_HORS_OS = sum(1 for nm in DOM_PERMISSIF.values() if nm not in OS_DEF)


# ───────────────────────────── la détection ──────────────────────────────────
def arbres(p):
    t = {}
    for f, idx in PAR.items():
        k = mathutils.kdtree.KDTree(len(idx))
        for r, i in enumerate(idx):
            k.insert(p[i], r)
        k.balance()
        t[f] = k
    return t


def sens(p, n, arb, fa, fb):
    """Compte les sommets de fa qui sont DANS fb, et les couples de groupes."""
    if fa not in PAR or fb not in PAR:
        return 0, {}
    t, idxb = arb[fb], PAR[fb]
    total, detail = 0, {}
    for i in PAR[fa]:
        _co, k, d = t.find(p[i])
        if d >= RAYON:
            continue
        j = idxb[k]
        if ((p[j] - p[i]).dot(n[j]) > PROFONDEUR_MINIMALE
                and (P_REPOS[i] - P_REPOS[j]).length > ECART_REPOS_MINIMAL):
            total += 1
            c = f"{DOM[i]} → {DOM[j]}"
            detail[c] = detail.get(c, 0) + 1
    return total, detail


def mesurer():
    p, n = evalue()
    arb = arbres(p)
    couples, groupes, total = [], {}, 0
    for fa, fb in COUPLES:
        ab, da = sens(p, n, arb, fa, fb)
        ba, db = sens(p, n, arb, fb, fa)
        if ab or ba:
            couples.append({"entre": f"{fa}/{fb}",
                            "sommets": ab + ba,
                            f"{fa}_dans_{fb}": ab,
                            f"{fb}_dans_{fa}": ba})
            total += ab + ba
            for d in (da, db):
                for k, v in d.items():
                    groupes[k] = groupes.get(k, 0) + v
    couples.sort(key=lambda c: -c["sommets"])
    pires = sorted(groupes.items(), key=lambda kv: -kv[1])[:3]
    return {"total": total, "couples": couples,
            "pires_groupes": [{"couple": k, "sommets": v} for k, v in pires]}


# ─────────────────────────── contrôle de la sonde ────────────────────────────
print("── contrôle de la sonde ──")
neutre()
sonde_repos = mesurer()
print(f"repos (tout à zéro)     : {sonde_repos['total']} intersections")
appliquer("Hand_Neutral")
sonde_neutral = mesurer()
print(f"Hand_Neutral            : {sonde_neutral['total']} intersections")
appliquer("Hand_Fist")
sonde_poing = mesurer()
print(f"Hand_Fist               : {sonde_poing['total']} intersections")
if sonde_repos["total"] or sonde_neutral["total"]:
    print("SONDE FAUSSE : elle trouve des intersections sur une main au repos.")
    sys.exit(3)
if sonde_poing["total"] == sonde_neutral["total"]:
    print("SONDE MUETTE : le poing rend le même chiffre que le repos.")
    sys.exit(3)
print("La sonde rend zéro au repos et réagit au poing : elle mesure son entrée.\n")


# ──────────────────────────── le balayage complet ────────────────────────────
def balayer():
    poses, transitions = {}, {}
    for nom in POSES:
        appliquer(nom)
        m = mesurer()
        poses[nom] = m
        print(f"  {nom:20s} {m['total']:5d}  " +
              ", ".join(f"{c['entre']}={c['sommets']}" for c in m["couples"]))
    v_neutral = valeurs_action("Hand_Neutral")
    for cible in TRANSITIONS:
        v_cible = valeurs_action(cible)
        etapes = {}
        for t in ETAPES:
            poser_valeurs(melange(v_neutral, v_cible, t))
            etapes[f"{t:.1f}"] = mesurer()
        # contre-épreuve : l'étape 1,0 doit retrouver la pose jouée par l'action.
        # Si elle ne la retrouve pas, c'est l'interpolation qui est fausse.
        ecart = etapes["1.0"]["total"] - poses[cible]["total"]
        transitions[f"Hand_Neutral→{cible}"] = {
            "etapes": etapes,
            "pic": max(etapes.items(), key=lambda kv: kv[1]["total"])[0],
            "pic_sommets": max(v["total"] for v in etapes.values()),
            "premiere_etape_fautive": next(
                (k for k, v in etapes.items() if v["total"]), None),
            "etapes_fautives": [k for k, v in etapes.items() if v["total"]],
            "contre_epreuve_etape_1_moins_action": ecart,
        }
        serie = " ".join(f"{etapes[f'{t:.1f}']['total']:>5d}" for t in ETAPES)
        print(f"  Neutral→{cible:18s}{serie}   (contre-épreuve {ecart:+d})")
    return {"poses": poses, "transitions": transitions}


resultat = {
    "fichier": os.path.basename(BLEND),
    "methode": {
        "rayon_mm": RAYON * 1000,
        "profondeur_minimale_mm": PROFONDEUR_MINIMALE * 1000,
        "ecart_au_repos_minimal_mm": ECART_REPOS_MINIMAL * 1000,
        "couples_examines": len(COUPLES), "sens": "les deux",
        "etapes_par_transition": len(ETAPES),
    },
    "groupes_de_sommets_sans_os": HORS_OS,
    "sommets_dominés_par_un_groupe_sans_os": N_HORS_OS,
    "controle_de_la_sonde": {
        "repos_tout_a_zero": sonde_repos["total"],
        "Hand_Neutral": sonde_neutral["total"],
        "Hand_Fist": sonde_poing["total"],
    },
}

for etiquette, par, dom in (("classement_permissif", PAR_PERMISSIF, DOM_PERMISSIF),
                            ("classement_strict", PAR_STRICT, DOM_STRICT)):
    PAR, DOM = par, dom
    print(f"\n── {etiquette} ──")
    r = balayer()
    r["familles"] = {f: len(par[f]) for f in sorted(par)}
    resultat[etiquette] = r

# Le classement permissif est celui du vérificateur : c'est lui qui fait foi
# pour la comparaison avec le rapport existant.
resultat["poses"] = resultat["classement_permissif"]["poses"]
resultat["transitions"] = resultat["classement_permissif"]["transitions"]

neutre()
resultat["duree_s"] = round(time.time() - t0, 1)
with open(SORTIE, "w", encoding="utf-8") as f:
    json.dump(resultat, f, ensure_ascii=False, indent=2)
print(f"\nÉcrit : {SORTIE}  ({resultat['duree_s']} s)")
