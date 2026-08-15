"""
LES ARTICULATIONS — relevées sur le corps lui-même, sans squelette à recaler.

Sacha a tranché, et il a raison : faire coller le squelette anatomique du
paquet sur ce corps est un chantier entier — il ne rentre bien que sur le
tronc, et les 87 os qui en sortent sont tous des mains et des pieds. Une source
de cotes qu'il faut d'abord ajuster n'est plus une source de cotes.

Le corps se mesure donc sur lui-même, avec trois instruments dont aucun ne
demande de seuil à régler.

╔══════════════════════════════════════════════════════════════════════════╗
║  1. LE PLAN MÉDIAN DONNE L'ENTREJAMBE.                                   ║
║     Les jambes sont écartées : sous l'entrejambe, il n'y a plus rien en  ║
║     x = 0. Le point le plus bas de la coupe médiane EST l'entrejambe.    ║
╠══════════════════════════════════════════════════════════════════════════╣
║  2. LA PARITÉ HORIZONTALE DONNE L'AISSELLE — mais pas n'importe où.      ║
║                                                                          ║
║     Une droite gauche-droite coupe la peau un nombre pair de fois : 2 au ║
║     ventre, 4 aux cuisses écartées, 6 aux bras décollés.                 ║
║                                                                          ║
║     PREMIÈRE VERSION, FAUSSE : je prenais la hauteur la plus haute à     ║
║     quatre traversées. Elle est tombée à 1670 mm, DANS LA TÊTE — car à   ║
║     hauteur d'oreille le rayon compte lui aussi six traversées (oreille, ║
║     crâne, oreille). Un nombre parfaitement crédible, pris sur la        ║
║     mauvaise grandeur.                                                   ║
║                                                                          ║
║     L'aisselle est le sommet de la bande CONTINUE de séparation qui part ║
║     du sol : pieds, jambes, puis bras le long du corps, sans interruption║
║     jusqu'aux épaules. Les oreilles sont une autre bande, plus haut, et  ║
║     la continuité les exclut sans qu'on ait à les nommer.                ║
╠══════════════════════════════════════════════════════════════════════════╣
║  3. LA COUPE DE MEMBRE DONNE COUDE, POIGNET, GENOU, CHEVILLE.            ║
║                                                                          ║
║     Un membre est un tube dont le rayon varie. Balayé DEPUIS LA RACINE,  ║
║     ce rayon fait des creux toujours dans le même ordre :                ║
║                                                                          ║
║        épaule → COUDE → avant-bras → POIGNET → main                      ║
║        hanche → GENOU → mollet    → CHEVILLE → pied                      ║
║                                                                          ║
║     DEPUIS LA RACINE, et non depuis l'extrémité : balayé depuis le bout  ║
║     des doigts, le premier creux tombait à 54 mm — entre les phalanges,  ║
║     pas au poignet. Les doigts et les orteils sont pleins de faux creux ;║
║     mis en DERNIER, ils ne peuvent plus rien fausser.                    ║
╚══════════════════════════════════════════════════════════════════════════╝

Comme pour la tête, chaque fonction LÈVE plutôt que de rendre un chiffre de
secours. Une sonde qui répond de façon crédible sur la mauvaise grandeur est
pire que pas de sonde.
"""

import bpy, math, mathutils


# ═══════════════════════════════════════════════════════════════════
#   L'INSTRUMENT : où une droite horizontale coupe la peau
# ═══════════════════════════════════════════════════════════════════

def coupe_horizontale(corps, z, y, x_depart, portee):
    """Les abscisses où la droite traverse la peau, dans l'ordre."""
    mi = corps.matrix_world.inverted()
    d = mathutils.Vector((1.0, 0.0, 0.0))
    dl = (mi.to_3x3() @ d).normalized()
    p = mathutils.Vector((x_depart, y, z))
    xs = []
    for _ in range(16):
        ok, loc, _nor, _idx = corps.ray_cast(mi @ p, dl, distance=portee)
        if not ok:
            break
        m = corps.matrix_world @ loc
        xs.append(m.x)
        p = m + d * 0.0004
    return xs


def intervalles(corps, z, ys, x0, portee):
    """
    LES SEGMENTS DE CHAIR à une hauteur donnée, du plus à gauche au plus à droite.

    C'est l'instrument qui règle la contamination la plus bête du relevé : sous
    l'entrejambe, mes « points de jambe » contenaient LES MAINS — les doigts
    descendent jusqu'à 802 mm, exactement la hauteur de l'entrejambe, et le
    genou gauche s'est retrouvé relevé à x = −448 mm, dans la paume.

    Avec les segments, plus d'ambiguïté et aucun seuil : à toute hauteur, les
    JAMBES sont les segments les plus proches de l'axe, les BRAS les plus
    éloignés. On ne suppose plus où passe la limite, on la lit.
    """
    meilleur = []
    for y in ys:
        xs = coupe_horizontale(corps, z, y, x0, portee)
        if len(xs) > len(meilleur):
            meilleur = xs
    return [(meilleur[i], meilleur[i + 1]) for i in range(0, len(meilleur) - 1, 2)]


def _sondes_y(v_par_tranche, i, y_c):
    ys = v_par_tranche.get(i)
    if not ys:
        return [y_c]
    y0, y1 = min(ys), max(ys)
    return [y0 + (y1 - y0) * (0.5 + k) / 10.0 for k in range(10)]


def separations(corps, pas=0.004):
    """L'entrejambe et l'aisselle, par le plan médian et par la continuité."""
    v = [corps.matrix_world @ x.co for x in corps.data.vertices]
    z_bas, z_haut = min(p.z for p in v), max(p.z for p in v)
    y_c = (min(p.y for p in v) + max(p.y for p in v)) / 2.0
    x0 = min(p.x for p in v) - 0.10
    portee = (max(p.x for p in v) - min(p.x for p in v)) + 0.30

    # ── L'ENTREJAMBE : le point le plus bas du plan médian.
    medians = [p for p in v if abs(p.x) <= 0.005]
    if len(medians) < 50:
        raise RuntimeError(f"plan médian trop pauvre ({len(medians)} sommets)")
    z_entrejambe = min(p.z for p in medians)

    # ── L'AISSELLE : le sommet de la bande continue de séparation partie du sol.
    #
    #    UNE SEULE DROITE NE SUFFIT PAS. J'ai d'abord balayé à un y unique — le
    #    milieu du corps — et la bande s'est rompue dès les chevilles : les
    #    pieds sont EN AVANT du milieu du corps, et la droite passait derrière
    #    eux. « Séparé » ne peut pas se décider sur une droite qui rate le
    #    membre.
    #
    #    À chaque hauteur on balaie donc plusieurs profondeurs, sur l'étendue
    #    en y que le corps occupe VRAIMENT à cette hauteur-là, et on retient le
    #    plus grand nombre de traversées. S'il existe une droite qui voit deux
    #    membres séparés, ils sont séparés.
    tranches = {}
    for p in v:
        tranches.setdefault(int((p.z - z_bas) / pas), []).append(p.y)
    z = z_bas + pas
    z_aisselle = None
    while z < z_haut:
        ys = tranches.get(int((z - z_bas) / pas), [])
        if ys:
            y0, y1 = min(ys), max(ys)
            sondes = [y0 + (y1 - y0) * (0.5 + i) / 10.0 for i in range(10)]
        else:
            sondes = [y_c]
        if max(len(coupe_horizontale(corps, z, y, x0, portee)) for y in sondes) < 4:
            z_aisselle = z - pas
            break
        z += pas
    if z_aisselle is None or z_aisselle <= z_entrejambe:
        raise RuntimeError(f"aisselle introuvable : la bande de séparation partie "
                           f"du sol ne se referme pas au-dessus de l'entrejambe "
                           f"({z_entrejambe*1000:.0f} mm)")
    return {"z_entrejambe": z_entrejambe, "z_aisselle": z_aisselle,
            "z_bas": z_bas, "z_haut": z_haut, "y_centre": y_c,
            "x_min": min(p.x for p in v), "x_max": max(p.x for p in v)}


# ═══════════════════════════════════════════════════════════════════
#   LE MEMBRE : rayon de section, balayé depuis la racine
# ═══════════════════════════════════════════════════════════════════

def _serie(points, graine, pas):
    paquets = {}
    for p in points:
        paquets.setdefault(int((p - graine).length / pas), []).append(p)
    brut = []
    for i in sorted(paquets):
        q = paquets[i]
        if len(q) < 6:
            continue
        c = sum(q, mathutils.Vector((0, 0, 0))) / len(q)
        brut.append([i * pas, sum((p - c).length for p in q) / len(q), c])
    # un lissage court : le maillage a ses propres ondulations, l'anatomie non
    lisse = []
    for i in range(len(brut)):
        f = brut[max(0, i - 1):i + 2]
        lisse.append([brut[i][0], sum(x[1] for x in f) / len(f), brut[i][2]])
    return lisse


def _creux_successifs(serie):
    """Les creux dans l'ordre, chacun séparé du suivant par une bosse franche."""
    out = []
    i = 1
    while i < len(serie) - 1:
        if serie[i][1] <= serie[i - 1][1] and serie[i][1] <= serie[i + 1][1]:
            out.append(i)
            j = i + 1
            while j < len(serie) - 1 and not (serie[j][1] >= serie[j - 1][1]
                                              and serie[j][1] >= serie[j + 1][1]
                                              and serie[j][1] > serie[i][1] * 1.06):
                j += 1
            i = j + 1
        else:
            i += 1
    return out


def membre(points, graine, noms, pas=0.008):
    serie = _serie(points, graine, pas)
    if len(serie) < 12:
        raise RuntimeError(f"membre {noms} : {len(serie)} tranches, trop peu")
    creux = _creux_successifs(serie)
    if len(creux) < 2:
        raise RuntimeError(f"membre {noms} : {len(creux)} creux de section trouvés, "
                           f"il en faut deux ({noms[0]} puis {noms[1]})")
    out = {nom: {"centre": serie[i][2], "rayon": serie[i][1], "distance": serie[i][0]}
           for nom, i in zip(noms, creux[:2])}
    # LA RACINE : le centre de la première tranche pleine, c'est-à-dire l'épaule
    # ou la hanche. Elle sort de la même mesure, elle n'est pas posée à part.
    out["racine"] = {"centre": serie[0][2], "rayon": serie[0][1], "distance": 0.0}
    return out


class Familles:
    """Union-find : le seul outil dont on a besoin pour suivre ce qui tient à quoi."""

    def __init__(self, n):
        self.pere = list(range(n))

    def racine(self, a):
        while self.pere[a] != a:
            self.pere[a] = self.pere[self.pere[a]]
            a = self.pere[a]
        return a

    def unir(self, a, b):
        ra, rb = self.racine(a), self.racine(b)
        if ra != rb:
            self.pere[ra] = rb


def morceaux(corps, indices, co):
    """Les morceaux d'un sous-ensemble de sommets, par les arêtes du maillage."""
    dans = set(indices)
    f = Familles(len(co))
    for e in corps.data.edges:
        a, b = e.vertices
        if a in dans and b in dans:
            f.unir(a, b)
    paquets = {}
    for i in dans:
        paquets.setdefault(f.racine(i), []).append(i)
    return sorted(paquets.values(), key=len, reverse=True)


def doigts(corps, main, poignet, co, pas=0.004):
    """
    LES DOIGTS, ET LEURS ARTICULATIONS.

    On coupe la main par une sphère centrée au poignet, et on fait GROSSIR le
    rayon. Tant qu'on est dans la paume, il ne sort qu'un morceau ; passé la
    base des doigts, il en sort cinq ; plus loin encore, les doigts courts
    disparaissent et le compte redescend.

    LE BON RAYON EST CELUI QUI EN REND LE PLUS. Ce n'est pas un réglage : c'est
    l'endroit où la main est le plus divisée, donc l'endroit où les doigts sont
    tous là et tous séparés. Rien à choisir.

    Ensuite, chaque doigt se lit tout seul : balayé depuis sa pointe, son rayon
    de section fait un creux à chaque articulation. Les faux creux qui m'avaient
    piégé sur le bras entier n'existent plus ici — dans un doigt isolé, un creux
    de section EST une phalange.
    """
    meilleur, comment = 0, []
    r = pas
    while r < 0.30:
        bouts = [i for i in main if (co[i] - poignet).length > r]
        ms = [m for m in morceaux(corps, bouts, co) if len(m) > 60]
        if len(ms) > meilleur:
            meilleur, comment = len(ms), ms
        r += pas
    out = []
    for m in comment:
        pts = [co[i] for i in m]
        pointe = max(pts, key=lambda q: (q - poignet).length)
        serie = _serie(pts, pointe, 0.006)
        if len(serie) < 5:
            continue
        for i in _creux_successifs(serie)[:3]:
            out.append({"centre": serie[i][2], "rayon": serie[i][1]})
        out.append({"centre": pointe, "rayon": 0.004, "pointe": True})
    return out


def morceaux_sous(corps, z_plafond, co=None):
    """
    LES MORCEAUX DU CORPS SOUS UN PLAN — par la TOPOLOGIE, pas par la géométrie.

    Le corps est un maillage d'un seul tenant ; si on ne garde que ce qui est
    sous l'entrejambe, il se sépare tout seul : jambe gauche, jambe droite,
    main gauche, main droite. Aucun seuil, aucune supposition sur l'endroit où
    passe la limite — le maillage la connaît, il suffit de suivre ses arêtes.

    Mes deux découpages précédents ont échoué exactement là : d'abord les doigts
    tombaient dans la jambe (ils descendent jusqu'à l'entrejambe), puis un rayon
    à une seule profondeur ne voyait qu'une tranche du membre et les points
    sortaient troués.
    """
    mw = corps.matrix_world
    if co is None:
        co = [mw @ x.co for x in corps.data.vertices]
    garde = [i for i, p in enumerate(co) if p.z < z_plafond]
    dans = set(garde)
    f = Familles(len(co))
    for e in corps.data.edges:
        a, b = e.vertices
        if a in dans and b in dans:
            f.unir(a, b)
    paquets = {}
    for i in garde:
        paquets.setdefault(f.racine(i), []).append(i)
    return sorted(paquets.values(), key=len, reverse=True)


def hauteur_de_soudure(corps, graine_a, graine_b, co=None):
    """
    LA HAUTEUR OÙ DEUX MORCEAUX N'EN FONT PLUS QU'UN.

    On monte : on ajoute les arêtes du bas vers le haut, et on regarde à quelle
    hauteur la main rejoint le tronc. C'est ÇA, l'aisselle — pas une hauteur
    choisie, pas un comptage de traversées qui confond une oreille avec un bras :
    la hauteur exacte où le membre cesse d'être détachable.

    Ma mesure précédente donnait 1492 mm ; à cette hauteur-là, la topologie
    montre que le bras tient encore à l'épaule. Elle était donc fausse, et
    c'est ce test-ci qui l'a dit.
    """
    mw = corps.matrix_world
    if co is None:
        co = [mw @ x.co for x in corps.data.vertices]
    aretes = []
    for e in corps.data.edges:
        a, b = e.vertices
        aretes.append((max(co[a].z, co[b].z), a, b))
    aretes.sort(key=lambda t: t[0])
    f = Familles(len(co))
    for z, a, b in aretes:
        f.unir(a, b)
        if f.racine(graine_a) == f.racine(graine_b):
            return z
    raise RuntimeError("les deux morceaux ne se rejoignent jamais")


def releve(corps):
    v = [corps.matrix_world @ x.co for x in corps.data.vertices]
    S = separations(corps)
    R = {k: S[k] for k in ("z_entrejambe", "z_aisselle", "z_bas", "z_haut")}
    R["z_sol"], R["z_sommet"] = S["z_bas"], S["z_haut"]
    x0 = S["x_min"] - 0.10
    portee = (S["x_max"] - S["x_min"]) + 0.30
    pas = 0.004
    par_tranche = {}
    for p in v:
        par_tranche.setdefault(int((p.z - S["z_bas"]) / pas), []).append(p.y)

    # ── LA TABLE DES SEGMENTS, sur toute la hauteur des membres.
    #    Pour chaque hauteur : le segment de jambe et le segment de bras, de
    #    chaque côté, ou None quand il n'y en a pas.
    table = {}
    z = S["z_bas"] + pas
    while z < S["z_aisselle"]:
        i = int((z - S["z_bas"]) / pas)
        segs = intervalles(corps, z, _sondes_y(par_tranche, i, S["y_centre"]), x0, portee)
        g = [t for t in segs if (t[0] + t[1]) / 2 < 0]
        d = [t for t in segs if (t[0] + t[1]) / 2 >= 0]
        table[i] = {
            "jambe_g": max(g, key=lambda t: t[1]) if g else None,   # le plus proche de l'axe
            "jambe_d": min(d, key=lambda t: t[0]) if d else None,
            "bras_g": min(g, key=lambda t: t[0]) if len(g) > 1 else None,   # le plus loin
            "bras_d": max(d, key=lambda t: t[1]) if len(d) > 1 else None,
        }
        z += pas

    def points_de(quoi, plafond):
        out = []
        for p in v:
            if p.z >= plafond:
                continue
            t = table.get(int((p.z - S["z_bas"]) / pas))
            if not t or t[quoi] is None:
                continue
            a, b = t[quoi]
            if a - 0.002 <= p.x <= b + 0.002:
                out.append(p)
        return out

    # ── LES MEMBRES, découpés par la connexité du maillage ──
    #
    # Sous l'entrejambe, le corps tombe en quatre morceaux : deux jambes et deux
    # mains. On les distingue sans aucun seuil — LES JAMBES SONT CELLES QUI
    # TOUCHENT LE SOL. C'est vrai de tout corps debout.
    co = v
    sous_entrejambe = [m for m in morceaux_sous(corps, S["z_entrejambe"], co) if len(m) > 200]
    if len(sous_entrejambe) < 4:
        raise RuntimeError(f"sous l'entrejambe, {len(sous_entrejambe)} morceaux "
                           f"au lieu de quatre (deux jambes, deux mains)")
    par_le_bas = sorted(sous_entrejambe, key=lambda m: min(co[i].z for i in m))
    jambes, mains = {}, {}
    for m in par_le_bas[:2]:
        jambes["g" if sum(co[i].x for i in m) < 0 else "d"] = [co[i] for i in m]
    for m in par_le_bas[2:4]:
        mains["g" if sum(co[i].x for i in m) < 0 else "d"] = m

    # ── L'AISSELLE : la hauteur où la main cesse d'être détachable du tronc.
    graine_tronc = min(range(len(co)), key=lambda i: co[i].z if abs(co[i].x) < 0.005
                       else 1e9)
    S["z_aisselle"] = min(hauteur_de_soudure(corps, mains[c][0], graine_tronc, co)
                          for c in ("g", "d"))
    R["z_aisselle"] = S["z_aisselle"]
    sous_aisselle = [m for m in morceaux_sous(corps, S["z_aisselle"] - 0.001, co)
                     if len(m) > 200]
    bras, bras_idx = {}, {}
    for m in sous_aisselle[1:]:
        c = "g" if sum(co[i].x for i in m) < 0 else "d"
        if c not in bras:
            bras[c] = [co[i] for i in m]
            bras_idx[c] = m

    for cote in ("g", "d"):
        if cote not in bras:
            raise RuntimeError(f"bras {cote} : {len(sous_aisselle)} morceaux sous "
                               f"l'aisselle mesurée à {S['z_aisselle']*1000:.0f} mm")
        if cote not in jambes:
            raise RuntimeError(f"jambe {cote} absente des quatre morceaux du bas")
        b = bras[cote]
        epaule = max(b, key=lambda p: p.z)
        R["bras_" + cote] = membre(b, epaule, ("coude", "poignet"))
        R["bras_" + cote]["bout_doigt"] = max(b, key=lambda p: (p - epaule).length)
        # L'ÉPAULE : le CENTRE DE LA COUPE, pas le sommet du morceau. Prendre le
        # point le plus haut donnait une tranche de 6 mm de rayon posée en
        # arrière de l'épaule — un point réel, mais pas le centre d'une
        # articulation. La coupe, elle, a le diamètre de l'épaule.
        R["bras_" + cote].pop("racine")
        coupe = [q for q in b if q.z > S["z_aisselle"] - 0.012]
        R["bras_" + cote]["epaule"] = {
            "centre": sum(coupe, mathutils.Vector((0, 0, 0))) / len(coupe),
            "rayon": max((q - sum(coupe, mathutils.Vector((0, 0, 0))) / len(coupe)).length
                         for q in coupe)}
        R["bras_" + cote]["sommets"] = len(b)
        # LES PHALANGES : la main est ce qui est au-delà du poignet.
        pg = R["bras_" + cote]["poignet"]["centre"]
        idx = [i for i in bras_idx[cote]
               if (co[i] - epaule).length > R["bras_" + cote]["poignet"]["distance"]]
        R["main_idx_" + cote] = idx
        R["bras_idx_" + cote] = bras_idx[cote]
        R["doigts_" + cote] = doigts(corps, idx, pg, co)

        j = jambes[cote]
        hanche = max(j, key=lambda p: p.z)
        R["jambe_" + cote] = membre(j, hanche, ("genou", "cheville"))
        R["jambe_" + cote]["bout_orteil"] = max(j, key=lambda p: (p - hanche).length)
        R["jambe_" + cote].pop("racine")
        coupe = [q for q in j if q.z > S["z_entrejambe"] - 0.012]
        R["jambe_" + cote]["hanche"] = {
            "centre": sum(coupe, mathutils.Vector((0, 0, 0))) / len(coupe),
            "rayon": max((q - sum(coupe, mathutils.Vector((0, 0, 0))) / len(coupe)).length
                         for q in coupe)}
        R["jambe_" + cote]["sommets"] = len(j)

    # ── LE COU : au-dessus des aisselles il n'y a plus que les épaules, le cou
    #    et la tête. Le cou est un CREUX de section — le PREMIER en montant.
    #
    #    Première version, fausse : je prenais le minimum absolu. Il est tombé à
    #    1778 mm, c'est-à-dire sur la calotte du crâne — la dernière tranche
    #    d'une forme fermée est toujours minuscule. Un minimum de bord n'est pas
    #    un creux.
    tr = {}
    for p in v:
        if p.z > R["z_aisselle"]:
            tr.setdefault(int((p.z - R["z_aisselle"]) / 0.004), []).append(p)
    serie = []
    for i in sorted(tr):
        q = tr[i]
        if len(q) < 8:
            continue
        c = sum(q, mathutils.Vector((0, 0, 0))) / len(q)
        serie.append([sum((p - c).length for p in q) / len(q), c])
    # Le maillage ondule, l'anatomie non : on lisse avant de chercher le creux,
    # sinon la toute première tranche sous les épaules passe pour le cou.
    lisse = []
    for i in range(len(serie)):
        f = serie[max(0, i - 2):i + 3]
        lisse.append([i, sum(x[0] for x in f) / len(f), serie[i][1]])
    # ── LE COU EST LÀ OÙ LA SECTION CESSE DE RÉTRÉCIR.
    #
    #    En montant depuis les aisselles, le rayon fait exactement trois choses :
    #    il diminue (épaules → cou), il remonte (la tête), puis il s'effondre
    #    (la calotte). Le cou est le fond de la première descente.
    #
    #    Deux versions fausses avant celle-ci. Le minimum ABSOLU tombait sur la
    #    calotte du crâne à 1778 mm — la dernière tranche d'une forme fermée est
    #    toujours minuscule, et un minimum de bord n'est pas un creux. Puis mon
    #    détecteur de creux successifs s'arrêtait au premier accident de
    #    maillage sous l'épaule, à 1320 mm pour 200 mm de rayon : une tranche
    #    d'épaules prise pour un cou.
    i_cou = None
    for i in range(1, len(lisse) - 6):
        if all(lisse[i + k][1] < lisse[i + k + 1][1] for k in range(5)):
            i_cou = i
            break
    if i_cou is None:
        raise RuntimeError("cou introuvable : la section ne cesse jamais de "
                           "rétrécir au-dessus des aisselles")
    R["cou"] = {"centre": serie[i_cou][1], "rayon": serie[i_cou][0]}
    return R
