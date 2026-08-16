"""Les trois articulations d'un doigt flechissent-elles DANS LE MEME SENS ?

Une main reelle plie en CASCADE : la metacarpo-phalangienne amorce, la PIP
suit, la DIP termine — toutes dans le meme sens. Un doigt qui flechit a la
base et s'ETEND au milieu n'est pas un doigt plie, c'est un doigt casse, et la
peau se tord au coude.

Le depot connait cette regle : elle est ecrite pour la fermeture du poing. Elle
n'a jamais ete imposee aux RECHERCHES DE CONTACT, qui optimisent une distance,
une orientation de pulpes et un compte de traversees — trois criteres qu'un
doigt replie en Z satisfait parfaitement.
"""
import bpy, sys, json, math

arg = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=arg[0])
SIDE = ".L"
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")

def poser(nom_action):
    act = bpy.data.actions.get(nom_action)
    if act is None:
        return False
    rig.animation_data_create()
    rig.animation_data.action = act
    sc = bpy.context.scene
    deb = int(act.frame_range[0])
    sc.frame_set(deb)
    bpy.context.view_layer.update()
    return True

def angles(doigt):
    """L'angle de flexion signe de chaque articulation, en local."""
    out = {}
    for suf in ("01", "02", "03"):
        n = f"CTRL_{doigt}_{suf}{SIDE}"
        if n not in rig.pose.bones:
            continue
        pb = rig.pose.bones[n]
        e = pb.matrix_basis.to_euler("XYZ")
        out[suf] = {"flexion_deg": round(math.degrees(e.x), 1),
                    "vrille_deg": round(math.degrees(e.y), 1),
                    "ecart_deg": round(math.degrees(e.z), 1)}
    return out

res = {}
for pose in ("Hand_Pinch", "Hand_OK", "Hand_Pinky_Thumb", "Hand_Fist",
             "Hand_Relaxed"):
    if not poser(pose):
        continue
    p = {}
    for d in ("index", "middle", "ring", "pinky", "thumb"):
        a = angles(d)
        if not a:
            continue
        fx = [v["flexion_deg"] for v in a.values()]
        signes = {(1 if f > 2 else -1 if f < -2 else 0) for f in fx} - {0}
        p[d] = {"par_articulation": a,
                "cascade_respectee": len(signes) <= 1,
                "sens_opposes": sorted(signes) if len(signes) > 1 else None}
    res[pose] = p

print("ATLAS_SONDE_CASCADE " + json.dumps(res, ensure_ascii=False))
