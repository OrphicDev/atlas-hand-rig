"""
CHARGER UN CORPS — un seul endroit, pour que tout le monde mesure le même.

Le chargement était recopié dans chaque script. Deux copies, c'est deux corps
qui divergent en silence : celui qu'on mesure et celui qu'on coiffe. Ici il n'y
en a qu'un.

La collection vient du paquet Blender Studio (Human Base Meshes v1.4.1, CC0).
On applique les modificateurs AVANT toute mesure — une cage de subdivision non
appliquée n'a pas la silhouette qu'on croit relever — et on met à l'échelle
avant de lire quoi que ce soit, parce que TOUTES les cotes en dépendent.
"""

import bpy, mathutils, os

CORPS = {"homme": {"collection": "Body Male - Realistic", "taille_m": 1.78},
         "femme": {"collection": "Body Female - Realistic", "taille_m": 1.65}}


def charger(qui, racine):
    # Le maillage de base est un asset CC0 de Blender Studio, trop lourd pour
    # être versionné. Son chemin est donc surchargeable : un clone propre le
    # désigne par ATLAS_BASE_MESH sans avoir à recréer l'arborescence de cache.
    paquet = os.environ.get("ATLAS_BASE_MESH") or os.path.join(
        racine, ".cache/modeles/humains",
        "human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend")
    if not os.path.isfile(paquet):
        raise RuntimeError(
            "maillage de base introuvable : " + paquet
            + "\nTéléchargez le Human Base Meshes bundle (CC0) de Blender Studio "
              "et donnez son chemin dans ATLAS_BASE_MESH.")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(paquet, link=False) as (src, dst):
        dst.collections = [CORPS[qui]["collection"]]
    col = dst.collections[0]
    # LIER LA COLLECTION À LA SCÈNE : sans ça les transformations des parents ne
    # s'évaluent pas, et les yeux — qui portent la seule cote fiable du visage —
    # se lisent à l'origine du monde.
    bpy.context.scene.collection.children.link(col)
    bpy.context.view_layer.update()
    mailles = [x for x in col.all_objects if x.type == "MESH"]
    corps = max(mailles, key=lambda x: len(x.data.vertices))
    yeux = [x for x in mailles if "eye" in x.name.lower()]

    k = CORPS[qui]["taille_m"] / corps.dimensions.z
    av = [corps.matrix_world @ x.co for x in corps.data.vertices]
    ref = mathutils.Vector(((min(q.x for q in av) + max(q.x for q in av)) / 2.0, 0.0,
                            min(q.z for q in av)))
    places = []
    for o in yeux:
        pts = [o.matrix_world @ mathutils.Vector(v) for v in o.bound_box]
        places.append((mathutils.Vector([(min(q[i] for q in pts) + max(q[i] for q in pts)) / 2
                                         for i in range(3)]) - ref) * k)
    for x in [y for y in col.all_objects if y is not None and y is not corps]:
        bpy.data.objects.remove(x, do_unlink=True)
    corps.hide_render = False
    bpy.context.view_layer.objects.active = corps
    corps.select_set(True)
    for m in list(corps.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception:
            corps.modifiers.remove(m)
    corps.scale = [k] * 3
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    v = [corps.matrix_world @ x.co for x in corps.data.vertices]
    corps.location.x -= (min(p.x for p in v) + max(p.x for p in v)) / 2.0
    corps.location.z -= min(p.z for p in v)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    bpy.ops.object.shade_smooth()
    corps.select_set(False)
    z_oeil = places[0].z if places else None
    return corps, z_oeil
