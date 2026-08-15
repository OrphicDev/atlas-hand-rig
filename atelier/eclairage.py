"""
ÉCLAIRAGE RASANT ET CADRAGE — module de contrôle.

Produit par l'agent « rendus et lumière » du chat 1, relu et adopté ici parce
qu'un fichier laissé dans /tmp finit par disparaître. Réglages retenus, MESURÉS
par l'agent :

  · key latérale rasante à 75,0° de la normale (15° au-dessus du plan) ;
  · fill frontal à 15 % de la key, rim à 25 % ;
  · énergie = éclairement × d², donc un gros plan n'est pas plus brûlé qu'un
    plan large — c'est précisément ce qui manquait aux rendus précédents ;
  · AgX, look None, exposition 0,0 EV, verrouillés pour toute la série ;
  · clay lambertien : gris 0,50, rugosité 1,00, spéculaire 0,00.

PREUVE DISPONIBLE : 18 rendus, 0,000 % d'écrêtage pour une limite fixée à 2 %,
luminance maximale plafonnée à 0,846. Voir renders/wip-chat-1/ et
reports/wip-chat-1/lumiere-histogrammes.json.

RÉSERVE de l'agent, conservée telle quelle : sous AgX, multiplier la key par 10
ne produit que 1,22 % d'écrêtage au seuil 0,99 — ce seuil ne discrimine donc
presque rien, et le chiffre utile est celui pris au seuil 0,95.

NON VÉRIFIÉ : ce module n'a PAS encore été exécuté dans le pipeline complet
(rig-main.py). Son intégration reste entière, et à mesurer.
"""
from __future__ import annotations

# -*- coding: utf-8 -*-
"""
eclairage.py — Module autonome de studio « clay » : exposition verrouillee,
cadrage calcule, eclairage lateral rasant, et mesure d'histogramme.

Concu pour etre importe tel quel dans n'importe quel script Blender :
aucun chemin en dur, aucune dependance a un depot.

    import sys; sys.path.insert(0, "/chemin/du/module")
    import eclairage

API minimale
------------
    poser_studio(scene, materiau_clay=True)         -> dict des reglages verrouilles
    cadrer(objet_maillage, direction, cible, largeur_de_champ) -> objet camera
    eclairer_rasant(cible, direction_camera, normale_surface, cote) -> dict
    histogramme(chemin_png)                          -> dict (ecretage / ombres, en %)

Helpers utiles
--------------
    repere_objet(...)      repere orthonorme d'un objet a partir de 3 points
    sommets_evalues(...)   sommets du maillage APRES modificateurs, filtres par groupe
    boite(...)             centre + taille d'un nuage de points

Principes tenus
---------------
* Key laterale rasante : 75 deg par rapport a la normale de surface (=15 deg
  au-dessus du plan de la surface), dans la fourchette exigee 70-80 deg.
* Fill frontal plafonne a 20 % de la key (defaut 15 %).
* Rim arriere faible (defaut 25 %), placee DERRIERE le sujet : elle ne touche
  que le contour, jamais les zones jugees.
* Puissances normalisees par la distance : energie = eclairement * d^2, et
  taille de source = 2*d*tan(angle/2). Une source deux fois plus loin eclaire
  pareil ET produit la meme durete d'ombre.
* Exposition / gestion des couleurs figees par poser_studio : identiques pour
  toute la serie.
"""


import math
import os
import struct
import zlib

try:
    import bpy
    from mathutils import Vector, Matrix, Quaternion
except ImportError:  # histogramme() reste utilisable hors Blender
    bpy = None
    Vector = None

try:
    import numpy as _np
except ImportError:
    _np = None


# ---------------------------------------------------------------------------
# Reglages verrouilles de la serie. Une seule source de verite.
# ---------------------------------------------------------------------------

REGLAGES = {
    # Rendu
    "moteur": "CYCLES",
    "echantillons": 96,
    "debruitage": True,
    "resolution": (900, 900),
    "fond_transparent": True,          # -> masque alpha exact pour l'histogramme
    "mode_couleur": "RGBA",
    "profondeur_png": "8",

    # Gestion des couleurs — VERROUILLEE
    "peripherique_affichage": "sRGB",
    "transformation_vue": "AgX",
    "look": "None",
    "exposition": 0.0,
    "gamma": 1.0,

    # Monde : ambiance neutre tres basse (evite le noir absolu sans faire fill)
    "monde_gris": 0.02,
    "monde_intensite": 1.0,

    # Materiau clay
    "clay_couleur": (0.50, 0.50, 0.50, 1.0),
    "clay_rugosite": 1.0,
    "clay_metallique": 0.0,
    "clay_specular_ior_level": 0.0,    # 0 = lambertien pur, aucun speculaire a ecreter

    # Cadrage
    "focale_mm": 85.0,
    "capteur_mm": 36.0,
    "marge_cadre": 1.22,               # 22 % d'air autour du sujet

    # Eclairage (fourchettes du cahier des charges)
    "key_angle_rasance_deg": 15.0,     # => 75 deg par rapport a la normale
    "key_eclairement": 26.0,           # W/m^2-equivalent a la cible
    "key_angle_source_deg": 12.0,      # diametre apparent vu de la cible
    "fill_ratio": 0.15,                # 15 % de la key (plafond exige : 20 %)
    "fill_angle_source_deg": 60.0,     # tres douce, sans ombre propre
    "rim_ratio": 0.25,
    "rim_angle_rasance_deg": 20.0,     # 20 deg DERRIERE le plan de surface
    "rim_angle_source_deg": 15.0,
    "distance_lumieres_x_largeur": 2.5,

    # Histogramme
    "seuil_ecretage": 0.99,
    "seuil_ombres": 0.02,
}

PREFIXE_LUMIERE = "LGT_studio_"


# ---------------------------------------------------------------------------
# Outils geometriques (independants de Blender autant que possible)
# ---------------------------------------------------------------------------

def _V(v):
    """Accepte Vector, tuple ou liste ; renvoie un Vector."""
    return v if isinstance(v, Vector) else Vector(tuple(v))


def _norm(v):
    v = _V(v).copy()
    n = v.length
    if n < 1e-12:
        raise ValueError("vecteur nul : direction indefinie")
    return v / n


def _perpendiculaire(v, reference):
    """Composante de `reference` orthogonale a `v`, normalisee.

    Si `reference` est colineaire a `v`, bascule sur un axe de secours.
    """
    v = _norm(v)
    r = _V(reference).copy()
    r -= v * r.dot(v)
    if r.length < 1e-6:
        for secours in ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)):
            r = _V(secours) - v * _V(secours).dot(v)
            if r.length > 1e-6:
                break
    return _norm(r)


def boite(points):
    """Centre, minimum, maximum et taille d'un nuage de points."""
    pts = [_V(p) for p in points]
    if not pts:
        raise ValueError("nuage de points vide")
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return {
        "centre": (mn + mx) * 0.5,
        "min": mn,
        "max": mx,
        "taille": mx - mn,
        "diagonale": (mx - mn).length,
    }


def repere_objet(origine, axe_principal, axe_lateral, point_de_signe=None):
    """Construit un repere orthonorme droit a partir de deux directions brutes.

    origine         : point de reference (ex. le poignet)
    axe_principal   : direction « longue » du sujet (ex. poignet -> doigts)
    axe_lateral     : direction « large » du sujet (ex. index -> auriculaire)
    point_de_signe  : point connu pour etre du cote « avant » ; si fourni, la
                      normale est retournee de sorte que ce point soit devant.

    Renvoie {'origine', 'principal' (f), 'lateral' (a), 'normal' (n)} avec
    n = f x a re-orthonormalise, et (f, a, n) direct.
    """
    o = _V(origine)
    f = _norm(axe_principal)
    a = _perpendiculaire(f, axe_lateral)
    n = _norm(f.cross(a))
    a = _norm(n.cross(f))
    if point_de_signe is not None:
        if (_V(point_de_signe) - o).dot(n) < 0.0:
            n = -n
            a = -a
    return {"origine": o, "principal": f, "lateral": a, "normal": n}


def sommets_evalues(objet_maillage, groupes=None, poids_min=0.2, depsgraph=None):
    """Sommets du maillage APRES modificateurs, en coordonnees monde.

    groupes : liste de noms de groupes de sommets, ou de prefixes se terminant
              par '*' (ex. 'DEF_index*'). None = tous les sommets.
    poids_min : poids minimal requis dans l'un des groupes retenus.

    Sert a viser une sous-partie du maillage (la main) sans embarquer le reste
    (l'avant-bras), sans jamais coder de coordonnee en dur.
    """
    if bpy is None:
        raise RuntimeError("sommets_evalues() requiert Blender")
    deps = depsgraph or bpy.context.evaluated_depsgraph_get()
    ob_eval = objet_maillage.evaluated_get(deps)
    me = ob_eval.to_mesh()
    mw = objet_maillage.matrix_world

    indices = None
    if groupes:
        noms = {g.name: g.index for g in objet_maillage.vertex_groups}
        indices = set()
        for motif in groupes:
            if motif.endswith("*"):
                base = motif[:-1]
                indices.update(i for n, i in noms.items() if n.startswith(base))
            elif motif in noms:
                indices.add(noms[motif])

    pts = []
    try:
        for v in me.vertices:
            if indices is not None:
                if not any(g.group in indices and g.weight >= poids_min for g in v.groups):
                    continue
            pts.append(mw @ v.co.copy())
    finally:
        ob_eval.to_mesh_clear()
    return pts


# ---------------------------------------------------------------------------
# 1. Studio : moteur, exposition, gestion des couleurs, monde, materiau
# ---------------------------------------------------------------------------

def materiau_clay(nom="CLAY_neutre", reglages=None):
    """Cree (ou met a jour) un clay neutre, mat, sans speculaire."""
    r = dict(REGLAGES); r.update(reglages or {})
    mat = bpy.data.materials.get(nom) or bpy.data.materials.new(nom)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = r["clay_couleur"]
    bsdf.inputs["Roughness"].default_value = r["clay_rugosite"]
    bsdf.inputs["Metallic"].default_value = r["clay_metallique"]
    for nom_entree, valeur in (
        ("Specular IOR Level", r["clay_specular_ior_level"]),
        ("Coat Weight", 0.0),
        ("Sheen Weight", 0.0),
        ("Subsurface Weight", 0.0),
        ("Transmission Weight", 0.0),
        ("Emission Strength", 0.0),
    ):
        if nom_entree in bsdf.inputs:
            bsdf.inputs[nom_entree].default_value = valeur
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def appliquer_clay(objets, mat=None):
    """Force un unique materiau clay sur les objets donnes."""
    mat = mat or materiau_clay()
    for ob in objets:
        if ob.type != 'MESH':
            continue
        ob.data.materials.clear()
        ob.data.materials.append(mat)
    return mat


def purger_lumieres(scene=None, prefixe=None):
    """Supprime les lumieres de la scene (toutes, ou seulement un prefixe).

    Le module possede l'eclairage : sans purge, une lampe residuelle du fichier
    fausserait tout le reste. Appelee par poser_studio().
    """
    scene = scene or bpy.context.scene
    a_virer = [ob for ob in list(scene.objects)
               if ob.type == 'LIGHT' and (prefixe is None or ob.name.startswith(prefixe))]
    for ob in a_virer:
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if data.users == 0:
            bpy.data.lights.remove(data)
    return len(a_virer)


def poser_studio(scene, materiau_clay=True, objets_clay=None, reglages=None):
    """Configure Cycles, l'exposition, la gestion des couleurs et le monde.

    Tous les reglages sont pris dans REGLAGES (surchargeables par `reglages`) et
    renvoyes tels qu'appliques : c'est le contrat verrouille de la serie.

    materiau_clay : si vrai, force le clay neutre sur `objets_clay` (defaut :
                    tous les maillages visibles au rendu de la scene).
    """
    r = dict(REGLAGES); r.update(reglages or {})

    # -- moteur
    scene.render.engine = r["moteur"]
    cy = getattr(scene, "cycles", None)
    if cy is not None:
        cy.samples = r["echantillons"]
        cy.use_denoising = r["debruitage"]
        cy.use_adaptive_sampling = True
        for attr, val in (("preview_samples", r["echantillons"]),
                          ("use_preview_denoising", r["debruitage"])):
            if hasattr(cy, attr):
                setattr(cy, attr, val)

    # -- format
    rd = scene.render
    rd.resolution_x, rd.resolution_y = r["resolution"]
    rd.resolution_percentage = 100
    rd.film_transparent = r["fond_transparent"]
    rd.image_settings.file_format = 'PNG'
    rd.image_settings.color_mode = r["mode_couleur"]
    rd.image_settings.color_depth = r["profondeur_png"]
    rd.image_settings.compression = 15
    rd.use_overwrite = True
    rd.dither_intensity = 0.0   # pas de bruit ajoute : l'histogramme doit etre net

    # -- gestion des couleurs VERROUILLEE
    scene.display_settings.display_device = r["peripherique_affichage"]
    vs = scene.view_settings
    vs.view_transform = r["transformation_vue"]
    try:
        vs.look = r["look"]
    except TypeError:
        vs.look = 'None'
    vs.exposure = r["exposition"]
    vs.gamma = r["gamma"]
    if hasattr(vs, "use_curve_mapping"):
        vs.use_curve_mapping = False
    if hasattr(vs, "use_white_balance"):
        vs.use_white_balance = False

    # -- monde : ambiance neutre tres basse
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("MONDE_studio")
        scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputWorld")
    fond = nt.nodes.new("ShaderNodeBackground")
    fond.location = (-200, 0)
    g = r["monde_gris"]
    fond.inputs["Color"].default_value = (g, g, g, 1.0)
    fond.inputs["Strength"].default_value = r["monde_intensite"]
    nt.links.new(fond.outputs["Background"], sortie.inputs["Surface"])

    # -- lumieres residuelles du fichier : degagees
    nb_purgees = purger_lumieres(scene)

    # -- clay
    mat = None
    if materiau_clay:
        cibles = objets_clay if objets_clay is not None else [
            ob for ob in scene.objects if ob.type == 'MESH' and not ob.hide_render]
        mat = appliquer_clay(cibles, materiau_clay_objet())
    r["_lumieres_purgees"] = nb_purgees
    r["_materiau"] = mat.name if mat else None
    return r


def materiau_clay_objet():
    """Alias interne : evite la collision entre le parametre `materiau_clay`
    (booleen) de poser_studio et la fonction du meme nom."""
    return materiau_clay()


# ---------------------------------------------------------------------------
# 2. Cadrage
# ---------------------------------------------------------------------------

def axes_camera(direction, haut=None):
    """Repere image d'une camera : (droite, haut_vrai, direction)."""
    d_hat = _norm(direction)
    haut_v = _V(haut) if haut is not None else Vector((0.0, 0.0, 1.0))
    if abs(_norm(haut_v).dot(d_hat)) > 0.999:
        haut_v = Vector((0.0, 1.0, 0.0))
    droite = _norm(haut_v.cross(d_hat))
    vrai_haut = _norm(d_hat.cross(droite))
    return droite, vrai_haut, d_hat


def cadre_optimal(points, direction, haut=None):
    """Cible et largeur de champ mesurees DANS LE PLAN IMAGE.

    Prendre le centre / la taille de la boite alignee sur le monde met le sujet
    de travers ou hors champ des que la camera n'est pas alignee sur les axes du
    monde. Ici on projette les points sur (droite, haut) de la camera : le centre
    est vraiment au centre de l'image et la largeur couvre vraiment le sujet.

    Renvoie {'cible', 'largeur', 'largeur_h', 'largeur_v'}.
    """
    droite, vrai_haut, d_hat = axes_camera(direction, haut)
    pts = [_V(p) for p in points]
    if not pts:
        raise ValueError("nuage de points vide")
    us = [p.dot(droite) for p in pts]
    vs = [p.dot(vrai_haut) for p in pts]
    ws = [p.dot(d_hat) for p in pts]
    cu = (min(us) + max(us)) * 0.5
    cv = (min(vs) + max(vs)) * 0.5
    cw = (min(ws) + max(ws)) * 0.5
    lu = max(us) - min(us)
    lv = max(vs) - min(vs)
    return {
        "cible": droite * cu + vrai_haut * cv + d_hat * cw,
        "largeur": max(lu, lv),
        "largeur_h": lu,
        "largeur_v": lv,
    }


def verifier_cadrage(camera, points, scene=None):
    """Le sujet tient-il dans le cadre ? Mesure, pas impression.

    Projette les points en coordonnees normalisees de camera (0..1 = cadre) et
    renvoie la boite obtenue plus la marge minimale, en % du cadre. Une marge
    negative = sujet coupe.
    """
    from bpy_extras.object_utils import world_to_camera_view
    scene = scene or bpy.context.scene
    xs, ys = [], []
    for p in points:
        c = world_to_camera_view(scene, camera, _V(p))
        if c.z <= 0:
            continue
        xs.append(c.x); ys.append(c.y)
    if not xs:
        return {"dans_le_cadre": False, "marge_min_pct": -100.0}
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    marge = min(x0, 1.0 - x1, y0, 1.0 - y1)
    return {
        "dans_le_cadre": marge >= 0.0,
        "marge_min_pct": round(100.0 * marge, 2),
        "boite_ndc": (round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)),
        "occupation_pct": round(100.0 * max(x1 - x0, y1 - y0), 2),
    }


def cadrer(objet_maillage, direction, cible, largeur_de_champ,
           nom="CAM_studio", haut=None, reglages=None, scene=None):
    """Place une camera qui vise `cible` depuis `direction`.

    objet_maillage   : sujet (sert au clipping ; peut etre None)
    direction        : vecteur cible -> camera (sera normalise)
    cible            : point vise, en monde. C'est LUI qui doit etre le centre
                       de la zone a juger, pas le barycentre de tout le maillage.
    largeur_de_champ : largeur (m) qui doit tenir dans le cadre, marge comprise
                       (REGLAGES['marge_cadre']).
    haut             : vecteur « haut » du cadre (defaut : +Z monde).

    La distance est CALCULEE a partir de la focale et du capteur :
        d = (largeur * marge / 2) / tan(fov/2)
    """
    r = dict(REGLAGES); r.update(reglages or {})
    scene = scene or bpy.context.scene
    d_hat = _norm(direction)
    cible = _V(cible)

    cam = bpy.data.objects.get(nom)
    if cam is None or cam.type != 'CAMERA':
        data = bpy.data.cameras.new(nom)
        cam = bpy.data.objects.new(nom, data)
        scene.collection.objects.link(cam)
    cd = cam.data
    cd.type = 'PERSP'
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = r["capteur_mm"]
    cd.lens = r["focale_mm"]
    cd.dof.use_dof = False

    demi_fov = math.atan((r["capteur_mm"] * 0.5) / r["focale_mm"])
    largeur = float(largeur_de_champ) * r["marge_cadre"]
    distance = (largeur * 0.5) / math.tan(demi_fov)

    cam.location = cible + d_hat * distance
    droite, vrai_haut, d_hat = axes_camera(d_hat, haut)
    cam.matrix_world = Matrix((
        (droite.x, vrai_haut.x, d_hat.x, cam.location.x),
        (droite.y, vrai_haut.y, d_hat.y, cam.location.y),
        (droite.z, vrai_haut.z, d_hat.z, cam.location.z),
        (0.0, 0.0, 0.0, 1.0),
    ))
    cd.clip_start = max(1e-4, distance * 0.05)
    cd.clip_end = distance * 10.0
    scene.camera = cam

    cam["distance"] = distance
    cam["largeur_de_champ"] = largeur
    return cam


# ---------------------------------------------------------------------------
# 3. Eclairage lateral rasant
# ---------------------------------------------------------------------------

def _lampe(nom, cible, direction, distance, eclairement, angle_source_deg,
           scene, forme='DISK'):
    """Cree une area light a `distance` de la cible, dans `direction`.

    Normalisation par la distance :
      * energie   = eclairement * d^2   -> meme eclairement a toute distance
      * taille    = 2 d tan(theta/2)    -> meme durete d'ombre a toute distance
    """
    data = bpy.data.lights.new(nom, type='AREA')
    data.shape = forme
    data.size = 2.0 * distance * math.tan(math.radians(angle_source_deg) * 0.5)
    data.energy = eclairement * distance * distance
    if hasattr(data, "use_shadow"):
        data.use_shadow = True
    ob = bpy.data.objects.new(nom, data)
    scene.collection.objects.link(ob)
    d_hat = _norm(direction)
    ob.location = _V(cible) + d_hat * distance
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = d_hat.to_track_quat('Z', 'Y')
    ob["eclairement"] = eclairement
    ob["distance"] = distance
    return ob


def eclairer_rasant(cible, direction_camera, normale_surface, cote,
                    largeur_sujet=None, axe_vertical=None, reglages=None,
                    scene=None, purger=True):
    """Pose une key laterale rasante + un fill frontal faible + une rim faible.

    cible            : point vise (centre de la zone a juger)
    direction_camera : vecteur cible -> camera (definit le fill frontal)
    normale_surface  : normale de la surface qu'on veut faire raser
                       (pour une paume vue de face : la normale de la paume)
    cote             : +1 ou -1 — les deux directions rasantes OPPOSEES
    largeur_sujet    : taille (m) du sujet ; fixe la distance des sources
    axe_vertical     : axe servant a construire la laterale (defaut : +Z monde).
                       La laterale vaut normalize(normale x axe_vertical) : elle
                       est donc perpendiculaire a la normale, ce qui garantit
                       l'angle rasant quel que soit l'axe choisi.

    Renvoie un dict avec les objets crees et TOUS les angles/puissances reellement
    obtenus (mesures sur les vecteurs, pas recopies des consignes).
    """
    r = dict(REGLAGES); r.update(reglages or {})
    scene = scene or bpy.context.scene
    cible = _V(cible)
    n_hat = _norm(normale_surface)
    cam_hat = _norm(direction_camera)
    cote = 1.0 if float(cote) >= 0 else -1.0

    if largeur_sujet is None:
        largeur_sujet = 0.2
    distance = float(largeur_sujet) * r["distance_lumieres_x_largeur"]

    if purger:
        purger_lumieres(scene, PREFIXE_LUMIERE)

    # laterale : perpendiculaire a la normale par construction
    axe_v = _V(axe_vertical) if axe_vertical is not None else Vector((0.0, 0.0, 1.0))
    lat = n_hat.cross(axe_v)
    if lat.length < 1e-6:                       # normale // axe vertical
        lat = n_hat.cross(Vector((0.0, 1.0, 0.0)))
    lat = _norm(lat) * cote

    # --- KEY : rasante, laterale
    a_key = math.radians(r["key_angle_rasance_deg"])
    d_key = _norm(lat * math.cos(a_key) + n_hat * math.sin(a_key))
    key = _lampe(PREFIXE_LUMIERE + "key", cible, d_key, distance,
                 r["key_eclairement"], r["key_angle_source_deg"], scene)

    # --- FILL : frontal, plafonne
    ratio_fill = min(float(r["fill_ratio"]), 0.20)   # plafond du cahier des charges
    fill = _lampe(PREFIXE_LUMIERE + "fill", cible, cam_hat, distance,
                  r["key_eclairement"] * ratio_fill, r["fill_angle_source_deg"],
                  scene, forme='SQUARE')

    # --- RIM : cote oppose ET derriere le plan de surface -> ne touche que le contour
    a_rim = math.radians(r["rim_angle_rasance_deg"])
    d_rim = _norm(-lat * math.cos(a_rim) - n_hat * math.sin(a_rim))
    rim = _lampe(PREFIXE_LUMIERE + "rim", cible, d_rim, distance,
                 r["key_eclairement"] * float(r["rim_ratio"]),
                 r["rim_angle_source_deg"], scene)

    def _ang(u, v):
        return math.degrees(math.acos(max(-1.0, min(1.0, _norm(u).dot(_norm(v))))))

    return {
        "key": key, "fill": fill, "rim": rim,
        "cote": cote,
        "distance": distance,
        "key_angle_vs_normale_deg": _ang(d_key, n_hat),      # attendu 70-80
        "key_angle_vs_surface_deg": 90.0 - _ang(d_key, n_hat),
        "key_angle_vs_camera_deg": _ang(d_key, cam_hat),
        "rim_angle_vs_normale_deg": _ang(d_rim, n_hat),
        "key_energie_W": key.data.energy,
        "fill_energie_W": fill.data.energy,
        "rim_energie_W": rim.data.energy,
        "key_eclairement": r["key_eclairement"],
        "fill_ratio": ratio_fill,
        "rim_ratio": float(r["rim_ratio"]),
        "key_taille_m": key.data.size,
    }


# ---------------------------------------------------------------------------
# 4. Histogramme
# ---------------------------------------------------------------------------

_PAS_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_lire(chemin):
    """Decode un PNG (8/16 bits, RGB ou RGBA, non entrelace) en valeurs
    NORMALISEES TELLES QUE STOCKEES — c'est-a-dire les valeurs d'affichage.

    Volontairement independant de la gestion des couleurs de Blender : on mesure
    ce que le fichier contient, donc ce que l'oeil verra, pas une reconversion.
    """
    with open(chemin, "rb") as f:
        donnees = f.read()
    if donnees[:8] != _PAS_SIGNATURE:
        raise ValueError("%s n'est pas un PNG" % chemin)

    pos = 8
    idat = bytearray()
    largeur = hauteur = profondeur = type_couleur = None
    entrelace = 0
    while pos < len(donnees):
        (taille,) = struct.unpack(">I", donnees[pos:pos + 4])
        nom = donnees[pos + 4:pos + 8]
        corps = donnees[pos + 8:pos + 8 + taille]
        pos += 12 + taille
        if nom == b"IHDR":
            largeur, hauteur, profondeur, type_couleur, _, _, entrelace = \
                struct.unpack(">IIBBBBB", corps)
        elif nom == b"IDAT":
            idat += corps
        elif nom == b"IEND":
            break
    if largeur is None:
        raise ValueError("PNG sans IHDR : %s" % chemin)
    if entrelace:
        raise ValueError("PNG entrelace non gere : %s" % chemin)
    canaux = {0: 1, 2: 3, 4: 2, 6: 4}.get(type_couleur)
    if canaux is None:
        raise ValueError("PNG a palette non gere : %s" % chemin)
    if profondeur not in (8, 16):
        raise ValueError("profondeur %d non geree" % profondeur)

    brut = zlib.decompress(bytes(idat))
    octets_px = canaux * (profondeur // 8)
    pas = largeur * octets_px

    if _np is not None:
        arr = _np.frombuffer(brut, dtype=_np.uint8).reshape(hauteur, pas + 1)
        filtres = arr[:, 0]
        lignes = arr[:, 1:].astype(_np.int16)
        sortie = _np.zeros((hauteur, pas), dtype=_np.uint8)
        precedente = _np.zeros(pas, dtype=_np.int16)
        for y in range(hauteur):
            f = int(filtres[y])
            ligne = lignes[y]
            if f == 0:
                cur = ligne.astype(_np.uint8)
            elif f == 2:                                   # Up : vectorisable
                cur = ((ligne + precedente) & 0xFF).astype(_np.uint8)
            else:                                          # Sub / Average / Paeth
                cur = _defiltrer_sequentiel(f, ligne, precedente, octets_px, pas)
            sortie[y] = cur
            precedente = cur.astype(_np.int16)
        if profondeur == 8:
            px = sortie.reshape(hauteur, largeur, canaux).astype(_np.float32) / 255.0
        else:
            v = sortie.reshape(hauteur, largeur, canaux, 2).astype(_np.uint32)
            px = ((v[..., 0] << 8) | v[..., 1]).astype(_np.float32) / 65535.0
        return px, canaux

    # --- repli pur Python (lent mais correct)
    return _png_lire_python(brut, largeur, hauteur, canaux, profondeur, octets_px, pas)


def _defiltrer_sequentiel(f, ligne, precedente, bpp, pas):
    cur = bytearray(pas)
    lg = ligne
    pr = precedente
    for i in range(pas):
        a = cur[i - bpp] if i >= bpp else 0
        b = int(pr[i])
        c = cur[i - bpp] if False else 0
        if i >= bpp:
            c = int(pr[i - bpp])
        x = int(lg[i])
        if f == 1:
            val = x + a
        elif f == 3:
            val = x + ((a + b) >> 1)
        elif f == 4:
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            val = x + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))
        else:
            raise ValueError("filtre PNG %d inconnu" % f)
        cur[i] = val & 0xFF
    return _np.frombuffer(bytes(cur), dtype=_np.uint8) if _np is not None else cur


def _png_lire_python(brut, largeur, hauteur, canaux, profondeur, bpp, pas):
    lignes = []
    precedente = bytearray(pas)
    off = 0
    for _ in range(hauteur):
        f = brut[off]; off += 1
        ligne = bytearray(brut[off:off + pas]); off += pas
        for i in range(pas):
            a = ligne[i - bpp] if i >= bpp else 0
            b = precedente[i]
            c = precedente[i - bpp] if i >= bpp else 0
            x = ligne[i]
            if f == 0:
                val = x
            elif f == 1:
                val = x + a
            elif f == 2:
                val = x + b
            elif f == 3:
                val = x + ((a + b) >> 1)
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                val = x + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))
            else:
                raise ValueError("filtre PNG %d inconnu" % f)
            ligne[i] = val & 0xFF
        lignes.append(ligne)
        precedente = ligne
    div = 255.0 if profondeur == 8 else 65535.0
    px = []
    for ligne in lignes:
        r = []
        for x in range(largeur):
            p = []
            for c in range(canaux):
                if profondeur == 8:
                    p.append(ligne[x * bpp + c] / div)
                else:
                    i = x * bpp + c * 2
                    p.append(((ligne[i] << 8) | ligne[i + 1]) / div)
            r.append(p)
        px.append(r)
    return px, canaux


def histogramme(chemin_png, seuil_haut=None, seuil_bas=None, masque_alpha=True,
                zone=None):
    """Pourcentage de pixels ecretes et de pixels en ombres bouchees.

    Le FOND EST IGNORE : les rendus sont produits avec film_transparent, donc le
    fond a alpha = 0. Le masque « sujet » est alpha > 0.5 — exact, sans deviner
    une couleur de fond. Si l'image n'a pas d'alpha, tous les pixels comptent.

    Mesure faite sur les valeurs STOCKEES dans le PNG (donc affichees), en
    luminance Rec.709.

    Renvoie :
      ecretage_pct  % de pixels sujet de luminance >= seuil_haut (defaut 0.99)
      ombres_pct    % de pixels sujet de luminance <= seuil_bas  (defaut 0.02)
      + luminance moyenne / mediane / max, et le nombre de pixels sujet.
    """
    seuil_haut = REGLAGES["seuil_ecretage"] if seuil_haut is None else seuil_haut
    seuil_bas = REGLAGES["seuil_ombres"] if seuil_bas is None else seuil_bas
    px, canaux = _png_lire(chemin_png)

    if _np is not None:
        rgb = px[..., :3] if canaux >= 3 else _np.repeat(px[..., :1], 3, axis=2)
        lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])
        if masque_alpha and canaux in (2, 4):
            masque = px[..., -1] > 0.5
        else:
            masque = _np.ones(lum.shape, dtype=bool)
        if zone is not None:
            # zone en coordonnees normalisees camera (origine en bas a gauche)
            h, w = lum.shape
            x0, y0, x1, y1 = zone
            c0 = max(0, int(math.floor(x0 * w))); c1 = min(w, int(math.ceil(x1 * w)))
            r0 = max(0, int(math.floor((1.0 - y1) * h))); r1 = min(h, int(math.ceil((1.0 - y0) * h)))
            boite_m = _np.zeros(lum.shape, dtype=bool)
            boite_m[r0:r1, c0:c1] = True
            masque = masque & boite_m
        n = int(masque.sum())
        if n == 0:
            return {"chemin": chemin_png, "pixels_sujet": 0, "pixels_total": int(lum.size),
                    "ecretage_pct": 0.0, "ombres_pct": 0.0, "luminance_moyenne": 0.0,
                    "luminance_mediane": 0.0, "luminance_max": 0.0,
                    "couverture_pct": 0.0, "seuil_haut": seuil_haut, "seuil_bas": seuil_bas}
        l = lum[masque]
        return {
            "chemin": chemin_png,
            "pixels_sujet": n,
            "pixels_total": int(lum.size),
            "couverture_pct": round(100.0 * n / lum.size, 3),
            "ecretage_pct": round(100.0 * float((l >= seuil_haut).sum()) / n, 4),
            # seuil d'alerte : AgX ne sature qu'a des valeurs enormes, donc le
            # 0.99 seul ne discrimine rien. 0.95 dit ou on commence a perdre.
            "quasi_ecretage_pct": round(100.0 * float((l >= 0.95).sum()) / n, 4),
            "ombres_pct": round(100.0 * float((l <= seuil_bas).sum()) / n, 4),
            "luminance_moyenne": round(float(l.mean()), 4),
            "luminance_mediane": round(float(_np.median(l)), 4),
            "luminance_max": round(float(l.max()), 4),
            "seuil_haut": seuil_haut, "seuil_bas": seuil_bas,
        }

    # --- repli pur Python
    total = ecret = ombre = 0
    somme = 0.0
    maxi = 0.0
    valeurs = []
    for ligne in px:
        for p in ligne:
            if masque_alpha and canaux in (2, 4) and p[-1] <= 0.5:
                continue
            if canaux >= 3:
                l = 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]
            else:
                l = p[0]
            total += 1; somme += l; valeurs.append(l)
            if l >= seuil_haut: ecret += 1
            if l <= seuil_bas: ombre += 1
            if l > maxi: maxi = l
    if total == 0:
        total = 1
    valeurs.sort()
    return {
        "chemin": chemin_png, "pixels_sujet": total,
        "ecretage_pct": round(100.0 * ecret / total, 4),
        "ombres_pct": round(100.0 * ombre / total, 4),
        "luminance_moyenne": round(somme / total, 4),
        "luminance_mediane": round(valeurs[len(valeurs) // 2], 4),
        "luminance_max": round(maxi, 4),
        "seuil_haut": seuil_haut, "seuil_bas": seuil_bas,
    }


# ---------------------------------------------------------------------------
# 5. Rendu
# ---------------------------------------------------------------------------

def rendre(chemin_png, scene=None, zone=None):
    """Rend l'image courante vers `chemin_png` et renvoie son histogramme.

    zone : boite NDC (x0, y0, x1, y1) limitant la mesure a la region a juger
           (ex. la main seule, avant-bras exclu).
    """
    scene = scene or bpy.context.scene
    dossier = os.path.dirname(chemin_png)
    if dossier:
        os.makedirs(dossier, exist_ok=True)
    scene.render.filepath = chemin_png
    bpy.ops.render.render(write_still=True)
    return histogramme(chemin_png, zone=zone)
