"""Le pouce est-il OPPOSE au repos, ou couche dans le plan des doigts ?

Un pouce humain est PRONATE d'environ 90 degres par rapport aux quatre doigts :
sa pulpe regarde la paume, son ongle regarde lateralement. Si le rig le laisse
dans le plan des doigts, il se comporte comme un cinquieme doigt — et aucune
recherche de contact ne peut faire se faire face deux pulpes qui ne sont pas
orientees pour cela.

On ne le juge pas a l'oeil : on mesure l'angle entre la normale palmaire du
pouce et celle de l'index, au REPOS.
"""
import bpy, sys, json, math, mathutils

arg = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=arg[0])
SIDE = ".L"

rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
geo = next(o for o in bpy.data.objects
           if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers))

bpy.context.scene.frame_set(bpy.context.scene.frame_current)
bpy.context.view_layer.update()

def os_(n):
    return rig.pose.bones[n]

def axe_long(n):
    pb = os_(n)
    return (pb.tail - pb.head).normalized()

# Le plan de la paume : donne par deux metacarpiens qui ne sont pas colineaires
a = axe_long(f"DEF_index_meta{SIDE}")
b = axe_long(f"DEF_pinky_meta{SIDE}")
n_paume = a.cross(b).normalized()

def repere(n):
    """Le triedre local d'un os : long, et les deux transverses."""
    pb = os_(n)
    m = pb.matrix.to_3x3()
    return [m.col[i].normalized() for i in range(3)]

res = {}
for nom in ("index", "middle", "ring", "pinky", "thumb"):
    seg = f"DEF_{nom}_02{SIDE}" if nom == "thumb" else f"DEF_{nom}_03{SIDE}"
    if seg not in rig.pose.bones:
        seg = f"DEF_{nom}_02{SIDE}"
    x, y, z = repere(seg)
    # la « normale de pulpe » : la transverse la plus alignee avec la paume
    cands = [("x", x), ("y", y), ("z", z)]
    nrm = max(cands, key=lambda c: abs(c[1].dot(n_paume)))
    res[nom] = {"segment": seg,
                "axe_le_plus_palmaire": nrm[0],
                "cos_avec_la_normale_palmaire": round(nrm[1].dot(n_paume), 3),
                "angle_deg": round(math.degrees(math.acos(
                    max(-1.0, min(1.0, abs(nrm[1].dot(n_paume)))))), 1),
                "longueur_mm": round(sum(
                    (os_(f"DEF_{nom}_{s}{SIDE}").tail
                     - os_(f"DEF_{nom}_{s}{SIDE}").head).length
                    for s in (("01", "02") if nom == "thumb"
                              else ("01", "02", "03"))
                    if f"DEF_{nom}_{s}{SIDE}" in rig.pose.bones) * 1000, 1)}

# L'ANGLE QUI COMPTE : entre la pulpe du pouce et celle de l'index
xp, yp, zp = repere(f"DEF_thumb_02{SIDE}")
xi, yi, zi = repere(f"DEF_index_03{SIDE}")
def pulpe(t):
    return max(t, key=lambda v: abs(v.dot(n_paume)))
ang = math.degrees(math.acos(max(-1.0, min(1.0,
        abs(pulpe([xp, yp, zp]).dot(pulpe([xi, yi, zi])))))))
print("ATLAS_SONDE_POUCE " + json.dumps({
    "normale_de_paume": [round(v, 3) for v in n_paume],
    "par_doigt": res,
    "opposition_pouce_contre_index_deg": round(ang, 1),
    "attendu_humain_deg": "70 a 90 : le pouce est PRONATE",
    "verdict": ("COUCHE DANS LE PLAN DES DOIGTS — il se comporte comme un "
                "cinquieme doigt" if ang < 40 else
                "partiellement oppose" if ang < 65 else "oppose")},
    ensure_ascii=False))
