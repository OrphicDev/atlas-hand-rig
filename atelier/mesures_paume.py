"""
LES TROIS GRANDEURS DE LA PAUME — un seul exemplaire, pour tout le dépôt.

╔══════════════════════════════════════════════════════════════════════════╗
║  POURQUOI CE MODULE EXISTE : DEUX COPIES D'UNE MESURE FINISSENT          ║
║  TOUJOURS PAR DIVERGER.                                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

`outils/sonde-creux.py` a démontré que la grandeur du dépôt — `creux_palmaire()`,
maximum de profondeur sous un plan FIGÉ à la pose de repos — annonce un progrès
là où l'anatomie recule. Sur le rig de `b17e548`, `Cup` de 0 à 1 :

    grandeur du dépôt (plan figé)   21,00 → 21,98 mm   (+0,98)  ← « ça creuse »
    flèche de l'arc transverse      29,99 → 19,10 mm   (−10,89) ← l'arc S'APLATIT
    largeur de paume                71,99 → 86,03 mm   (+14,04) ← la paume S'ÉLARGIT
    pouce ↔ auriculaire            102,27 → 99,13 → 101,39      ← 3 mm, puis ça repart

Le plan figé ne se trompe pas d'amplitude : il se trompe de SENS SUR LE
PHÉNOMÈNE. Un écartement augmente lui aussi la profondeur sous un plan d'hier.
Les trois grandeurs qui suivent, elles, SUIVENT la main — leurs repères sont
posés, jamais au repos — et ce sont elles qui ont rendu le diagnostic.

Elles étaient enfermées dans une sonde. La construction (`rig-main.py`) doit
mesurer les mêmes pour choisir l'axe et le signe de `CUP`, et les sondes doivent
juger avec exactement le même instrument : deux exemplaires d'une même grandeur,
c'est le défaut que ce chantier corrige, pas un détail d'organisation. La
logique reprise ici est celle de `outils/sonde-creux.py`, telle quelle.

CE QUE CE MODULE NE FAIT PAS :
  · il ne reconfigure pas `sys.stdout` — un module ne touche pas à la sortie de
    son hôte ; c'est au script lancé de le faire (et tous le font) ;
  · il n'écrit aucun verdict et ne sort d'aucun code : il rend des millimètres.
    Le verdict appartient à celui qui compare.

UNITÉS : la scène est en mètres, toutes les grandeurs rendues sont en
MILLIMÈTRES (facteur 1000, comme dans la sonde).

CHARGEMENT SANS `bpy` : rien de Blender n'est importé à l'import. `bpy` est
chargé paresseusement, dans les seules fonctions qui évaluent la scène, et
`mathutils` n'est jamais nécessaire — les vecteurs viennent de Blender et
portent eux-mêmes leurs opérations ; les sommes partent du premier terme au lieu
d'un `Vector((0,0,0))` fabriqué. Les trois mesures sont donc du calcul pur et
peuvent être relues, voire testées, hors de Blender.
"""

NOMS4 = ["index", "middle", "ring", "pinky"]

# La scène est en mètres ; tout ce qui sort d'ici est en millimètres.
EN_MM = 1000.0

# Seuil de dominance d'un groupe de sommets, repris tel quel de la sonde et du
# vérificateur. Ce n'est pas une mesure, c'est le seuil qui décide à quel os un
# sommet appartient ; le changer ici rendrait les chiffres incomparables avec
# ceux déjà publiés, ce qui est exactement le défaut que ce module corrige.
POIDS_MINIMAL = 0.01

# Longueur en dessous de laquelle un vecteur ne porte plus de direction fiable.
# ═══ LE 1e-9 ÉTAIT ÉCRIT QUATRE FOIS ═══
# Relecture adverse : quatre littéraux `1e-9` séparés gardaient quatre vecteurs
# différents (la corde, la perpendiculaire, l'axe de la main, la composante
# palmaire). Quatre exemplaires d'un même seuil, c'est la faute que ce module a
# été écrit pour supprimer — appliquée à lui-même. Un seul exemplaire, sinon
# ils divergeront le jour où l'un des quatre sera « ajusté ».
LONGUEUR_NULLE = 1e-9


# ═══════════════════════════════════════════════════════════════════
#   OUTILLAGE — aucune valeur par défaut, aucun zéro fabriqué
# ═══════════════════════════════════════════════════════════════════

def _somme(vecteurs):
    """Somme d'une suite de vecteurs, SANS origine fabriquée.

    ═══ UNE SOMME VIDE REND ZÉRO, ET UN ZÉRO SE LIT COMME UNE MESURE ═══
    Écrite `sum(v, Vector((0,0,0)))`, une somme sur une liste vide rend le
    vecteur nul, qui se normalise en vecteur nul, qui traverse ensuite tout le
    calcul sans jamais se signaler. C'est la faute type du dépôt : quatre fautes
    de sonde en un jour, dont deux rendaient un manquement FAUX. Ici, une suite
    vide lève.
    """
    suite = list(vecteurs)
    if not suite:
        raise RuntimeError("somme vectorielle sur une suite VIDE : la grandeur "
                           "qui l'utilise n'a aucun point à mesurer, elle ne "
                           "vaut pas zéro, elle n'existe pas")
    total = suite[0].copy()
    for v in suite[1:]:
        total = total + v
    return total


def _evalue(geo):
    """Les sommets du maillage ÉVALUÉ (armature comprise), en coordonnées monde.

    Repris mot pour mot de `evalue()` de la sonde. Sans `evaluated_get`, on lit
    le maillage de base : une main qui ne bouge jamais, donc une main qui passe
    tous les contrôles.

    ═══ LES INDICES DE `dominances()` VIENNENT DU MAILLAGE DE BASE ═══
    Relecture adverse : toutes les grandeurs font `p[i]` avec un `i` issu de
    `geo.data.vertices`, alors que `p` est le maillage ÉVALUÉ. Aujourd'hui la
    pile de modificateurs est Armature + CORRECTIVE_SMOOTH, qui conservent le
    nombre de sommets, et la correspondance tient. Le jour où quelqu'un ajoute
    un Subdivision ou un Mirror, les indices ne désignent plus les mêmes points
    et TOUTES les grandeurs continuent de sortir des millimètres plausibles —
    sur les mauvais sommets, sans un mot. C'est la forme la plus dangereuse de
    la faute du dépôt : pas un zéro, mais un nombre crédible et faux. Ce
    contrôle ne coûte rien et il lève au lieu de mentir.
    """
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    m = ev.to_mesh()
    mw = geo.matrix_world
    p = [mw @ v.co.copy() for v in m.vertices]
    ev.to_mesh_clear()
    if len(p) != len(geo.data.vertices):
        raise RuntimeError(
            f"le maillage évalué a {len(p)} sommets pour "
            f"{len(geo.data.vertices)} au repos : un modificateur change la "
            "topologie, donc les indices rendus par `dominances()` ne "
            "désignent plus les mêmes points et aucune des trois grandeurs ne "
            "mesure ce qu'elle annonce")
    return p


def rafraichir(rig):
    """Les trois lignes sans lesquelles rien de piloté ne s'évalue.

    ═══ EN MODE FOND, LES DRIVERS DORMENT ═══
    Sans changement d'image, le graphe ne réévalue pas les drivers : on mesure
    alors une main immobile, et une main immobile revient toujours exactement à
    sa pose de repos — donc elle passe tout. Ces trois lignes ne sont pas une
    précaution, elles sont la condition pour que la mesure porte sur la pose
    demandée.
    """
    import bpy
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def neutre(rig, SIDE):
    """Remise au repos, verbatim de la sonde et du vérificateur.

    Détacher l'action AVANT la remise à zéro : sans cela, les clés de la
    dernière pose rejouée écrasent la remise à zéro, et le contrôle du retour au
    repos mesure la pose précédente. Il rendait 123,9 mm.
    """
    pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        # On ne force pas le mode de rotation : on remet à zéro dans le mode où
        # l'os se trouve. Un instrument de mesure ne modifie pas son objet.
        if pb.rotation_mode == "QUATERNION":
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        else:
            pb.rotation_euler = (0.0, 0.0, 0.0)
    for k in list(pbh.keys()):
        if isinstance(pbh[k], float):
            pbh[k] = 0.0
    rafraichir(rig)


def os_monde(rig, nom, bout=False):
    """La position POSÉE de l'os, en monde. Jamais le repos.

    ═══ head_local NE BOUGE JAMAIS ═══
    Premier jet de la sonde : `rig.data.bones[nom].head_local`, c'est-à-dire la
    position de REPOS. Deux des quatre grandeurs sortaient constantes au
    centième sur tout le balayage — 71,99 mm et 50,30 mm, de `Cup = 0` à
    `Cup = 1`. Elles n'auraient JAMAIS pu bouger, et cette constance se lisait
    comme « le creusement ne rapproche pas l'auriculaire du pouce », c'est-à-dire
    exactement la conclusion attendue. Une sonde qui rend une constante ne
    mesure pas : elle se tait.

    `bout=True` rend la TÊTE distale de l'os (`tail`), `bout=False` sa base
    (`head`). Les deux ne se valent jamais : voir `pouce_auriculaire`.
    """
    pb = rig.pose.bones[nom]
    return rig.matrix_world @ (pb.tail if bout else pb.head)


def dominances(geo):
    """{indice de sommet: nom du groupe dominant}, verbatim des trois scripts.

    Ne dépend d'AUCUNE pose : les poids de groupes sont attachés au maillage de
    base. On peut donc l'appeler à n'importe quel moment sans rien perturber.
    Les sommets sans aucun groupe au-dessus du seuil sont absents du dict — ils
    n'appartiennent à personne, et leur donner un propriétaire par défaut
    fabriquerait des familles fantômes (c'est ce que `ZONES_ARTICULAIRES` a fait
    en se faisant passer pour « hand » : 203 sommets, des intersections
    inventées sur Pinch et OK, de vraies manquées sur Point).
    """
    noms = {g.index: g.name for g in geo.vertex_groups}
    dom = {}
    for v in geo.data.vertices:
        gs = [(g.weight, noms[g.group]) for g in v.groups
              if g.weight > POIDS_MINIMAL and g.group in noms]
        if gs:
            dom[v.index] = max(gs)[1]
    return dom


# ═══════════════════════════════════════════════════════════════════
#   LES MASSES PALMAIRES — et pourquoi le pouce en est exclu
# ═══════════════════════════════════════════════════════════════════

def paume_entiere(dom, SIDE):
    """Tous les sommets tenus par un métacarpien, thénar compris."""
    s = [i for i, n in dom.items() if n.endswith(f"_meta{SIDE}")]
    if not s:
        raise RuntimeError("aucun sommet tenu par un métacarpien : les masses "
                           "palmaires que ce module prétend distinguer "
                           "n'existent pas dans ce maillage")
    return s


def paume_sans_le_pouce(dom, SIDE):
    """La paume MOINS l'éminence thénar. C'est elle que l'arc doit mesurer.

    ═══ LE MAXIMUM ÉTAIT TENU PAR LE THÉNAR ═══
    L'éminence thénar est la masse la plus saillante de la paume, et creuser les
    rayons 4 et 5 ne la déplace guère. Tant que le maximum de profondeur est
    tenu par un sommet du métacarpien du POUCE, aucun creusement des rayons
    internes ne peut faire bouger le chiffre : la grandeur est aveugle au
    phénomène qu'elle prétend suivre. La sonde a nommé le sommet tenant ce
    maximum ; c'est ce qui a tranché.
    """
    s = [i for i, n in dom.items()
         if n.endswith(f"_meta{SIDE}") and not n.startswith("DEF_thumb")]
    if not s:
        raise RuntimeError("aucun sommet palmaire hors du pouce : l'arc "
                           "transverse n'a rien à mesurer")
    return s


def thenar(dom, SIDE):
    """Les sommets du métacarpien du pouce, isolés pour pouvoir être écartés."""
    s = [i for i, n in dom.items() if n == f"DEF_thumb_meta{SIDE}"]
    if not s:
        raise RuntimeError("aucun sommet dominé par DEF_thumb_meta"
                           f"{SIDE} : le thénar est introuvable")
    return s


# ═══════════════════════════════════════════════════════════════════
#   LES CINQ TÊTES MÉTACARPIENNES, SUR LES OS POSÉS
# ═══════════════════════════════════════════════════════════════════

def tetes_metacarpiennes(rig, SIDE):
    """Les cinq têtes métacarpiennes en coordonnées MONDE, sur la pose courante.

    Ce que la sonde lit, et rien d'autre :
      · POUCE   → `DEF_thumb_meta{SIDE}`.tail — le BOUT distal du métacarpien ;
      · les 4   → `DEF_{doigt}_01{SIDE}`.head — la base de la phalange
                  proximale, c'est-à-dire l'autre lèvre de la même articulation
                  métacarpo-phalangienne (la « jointure »).

    ═══ UNE BASE NE BOUGE PAS, C'EST SA DÉFINITION ═══
    Deuxième jet de la sonde : les distances étaient prises sur les `head` des
    métacarpiens, c'est-à-dire leurs BASES, celles qui s'articulent au carpe. Un
    métacarpien tourne AUTOUR de sa base : elle est immobile par construction,
    et la grandeur rendait 50,30 mm à tous les pas du balayage. On y aurait lu
    « le creusement ne rapproche pas l'auriculaire du pouce » alors qu'on
    mesurait deux points qui ne POUVAIENT PAS se rapprocher. Ce que Sacha
    entoure en rouge, ce sont les TÊTES.

    ═══ LA CLÉ EN PLUS, ET POURQUOI ELLE N'EST PAS UN DOUBLON ═══
    `pinky_meta_bout` est la tête du 5ᵉ métacarpien lue par l'AUTRE bout :
    `DEF_pinky_meta{SIDE}`.tail. C'est ce point-là, et pas `pinky`, que
    `pouce_auriculaire()` utilise dans la sonde. Les deux lectures désignent la
    même articulation et ne coïncident que si les deux os sont CONNECTÉS dans
    l'armature — ce qui n'a pas été vérifié dans un Blender ouvert. Tant que ce
    n'est pas mesuré, on garde les deux et on reproduit la sonde à la lettre ;
    `ecart_des_deux_lectures_de_la_tete_5()` donne l'écart en millimètres, et
    c'est lui qui tranchera, pas une supposition.
    """
    t = {"thumb": os_monde(rig, f"DEF_thumb_meta{SIDE}", bout=True),
         "pinky_meta_bout": os_monde(rig, f"DEF_pinky_meta{SIDE}", bout=True)}
    for n in NOMS4:
        t[n] = os_monde(rig, f"DEF_{n}_01{SIDE}", bout=False)
    return t


def ecart_des_deux_lectures_de_la_tete_5(tetes):
    """Écart, en mm, entre les deux lectures de la tête du 5ᵉ métacarpien.

    Contre-épreuve de `tetes_metacarpiennes` : si les deux os sont connectés,
    ce nombre est nul au bruit numérique près, à TOUTE pose. S'il est franc, les
    deux points sont distincts et il faudra dire — par la mesure — lequel des
    deux est la tête que Sacha entoure. On rend le nombre ; on ne décrète pas
    de tolérance, parce qu'aucune n'a été mesurée.
    """
    return (tetes["pinky_meta_bout"] - tetes["pinky"]).length * EN_MM


# ═══════════════════════════════════════════════════════════════════
#   LES TROIS GRANDEURS PROUVÉES
# ═══════════════════════════════════════════════════════════════════

def arc_transverse(p, tetes, palmaire, sommets):
    """La flèche de l'ARC transverse, en mm, sur la pose COURANTE.

    L'arc palmaire, c'est la corde qui joint la tête du métacarpien de l'index à
    celle de l'auriculaire, et la flèche que la chair creuse dessous. Les deux
    extrémités SUIVENT la main : creuser les rapproche, et le creux se mesure
    par rapport à elles — jamais par rapport à un plan d'hier. C'est cette
    grandeur, et non celle du dépôt, qui a vu l'arc s'aplatir de 10,89 mm quand
    `Cup` monte de 0 à 1.

    ═══ POURQUOI QUATRE ARGUMENTS ET NON DEUX ═══
    Le cahier l'annonce `arc_transverse(p, tetes)`. C'est impossible sans
    tricher : la flèche est une composante SIGNÉE le long de la direction
    palmaire, et cette direction ne se déduit d'aucune des deux entrées — elle
    s'établit par le mouvement (voir `direction_palmaire`). Et le maximum se
    prend sur un jeu de sommets dont l'exclusion du thénar est le fait mesuré le
    plus important de toute l'enquête. Les fabriquer ici à partir d'une
    convention, ou pire les rendre facultatifs, remettrait dans la mesure
    exactement les deux fautes qu'elle a servi à démontrer. Ils sont donc exigés.

    `palmaire` : direction unitaire vers la paume, issue de `direction_palmaire`.
    `sommets`  : indices palmaires, normalement `paume_sans_le_pouce(dom, SIDE)`.
    """
    if not sommets:
        raise RuntimeError("arc_transverse sans aucun sommet : la flèche ne "
                           "vaut pas zéro, elle n'a pas de support")
    a, b = tetes["index"], tetes["pinky"]
    u = (b - a)
    # ═══ ON LÈVE LÀ OÙ LA SONDE RENDAIT 0.0 ═══
    # Seule entorse au verbatim, et elle est imposée par la règle du dépôt : un
    # zéro se lit comme une mesure. Une corde de longueur nulle voudrait dire
    # que la tête de l'index et celle de l'auriculaire sont au même point — ce
    # n'est pas une paume plate, c'est une lecture cassée. Le cas ne peut pas
    # se produire sur une main réelle ; s'il se produit, il doit s'entendre.
    if u.length < LONGUEUR_NULLE:
        raise RuntimeError("corde index↔auriculaire de longueur nulle : les "
                           "deux têtes métacarpiennes sont lues au même point")
    u = u.normalized()
    # Composante palmaire perpendiculaire à la corde : la flèche se mesure
    # perpendiculairement à ce qu'elle sous-tend, sinon on mesure de la longueur.
    n = (palmaire - u * palmaire.dot(u))
    if n.length < LONGUEUR_NULLE:
        raise RuntimeError("la direction palmaire est colinéaire à la corde "
                           "index↔auriculaire : la flèche n'a pas de direction")
    n = n.normalized()
    fleche = max((p[i] - a).dot(n) for i in sommets)
    # ═══ LE DERNIER ZÉRO FABRIQUÉ DU FICHIER ═══
    # Relecture adverse : la version précédente écrivait `max(0.0, fleche)`,
    # « repris tel quel de la sonde », et son propre commentaire admettait que
    # le 0,00 qui en sort veut dire « plat OU retourné » — c'est-à-dire une
    # mesure qui ne dit pas ce qu'elle mesure. C'est mot pour mot la règle 1 du
    # dépôt : un zéro se lit comme une mesure. Le fichier avait déjà rompu le
    # verbatim douze lignes plus haut pour cette raison exacte (corde nulle) ;
    # garder l'écrêtage ici était donc une incohérence, pas une fidélité.
    #
    # AUCUN CHIFFRE PUBLIÉ NE CHANGE : sur le balayage de `b17e548` la flèche
    # reste entre 19,10 et 29,99 mm, l'écrêtage n'a jamais mordu. Ce qui change,
    # c'est qu'un arc retourné s'entend au lieu de se déguiser en paume plate.
    if fleche < 0.0:
        raise RuntimeError(
            f"flèche NÉGATIVE ({fleche * EN_MM:.2f} mm) : aucun sommet palmaire "
            "n'est du côté paume de la tête métacarpienne de l'index. L'arc est "
            "retourné, ou la direction palmaire pointe vers le dos de la main — "
            "dans les deux cas ce n'est pas une paume plate, et l'écrire 0,00 "
            "serait annoncer une mesure là où il n'y a qu'une lecture cassée")
    return fleche * EN_MM


def largeur_paume(tetes):
    """Distance tête de l'index ↔ tête de l'auriculaire, en mm.

    C'est la largeur anthropométrique de la main, prise sur la ligne des
    métacarpo-phalangiennes. Elle sert de CONTRE-ÉPREUVE au creusement : un vrai
    creusement RESSERRE la paume. Mesuré : `Cup` de 0 à 1 l'élargit de 14,04 mm.
    Le critère est conjoint — resserrer ET creuser ; un axe qui ne fait que l'un
    des deux n'est pas l'axe du creusement.
    """
    return (tetes["pinky"] - tetes["index"]).length * EN_MM


def pouce_auriculaire(tetes):
    """Distance tête du 1ᵉʳ métacarpien ↔ tête du 5ᵉ, en mm.

    Le cerclage rouge de Sacha : les deux TÊTES métacarpiennes qui doivent se
    rapprocher quand la paume se creuse. Mesuré sur le rig de `b17e548` :
    102,27 → 99,13 mm puis retour à 101,39 — trois millimètres, puis ça repart.

    On lit le 5ᵉ par `pinky_meta_bout` et non par `pinky` : c'est ce que fait la
    sonde, et tant que l'écart entre les deux lectures n'a pas été mesuré dans
    un Blender ouvert, changer de point serait changer la grandeur sans le dire.
    Voir `ecart_des_deux_lectures_de_la_tete_5`.
    """
    return (tetes["pinky_meta_bout"] - tetes["thumb"]).length * EN_MM


# ═══════════════════════════════════════════════════════════════════
#   LE CÔTÉ PAUME — établi PAR LE MOUVEMENT, jamais construit
# ═══════════════════════════════════════════════════════════════════

def direction_palmaire(rig, geo, SIDE, dom):
    """La direction unitaire qui pointe vers la paume, établie par le MOUVEMENT.

    ═══ LE SIGNE D'UNE NORMALE CONSTRUITE EST ARBITRAIRE ═══
    Un produit vectoriel `(jointure_index − poignet) × (jointure_auriculaire −
    poignet)` donne une normale au plan de la paume, mais son sens dépend de
    l'ordre des deux facteurs, donc d'une convention — pas de l'anatomie. Idem
    pour une normale d'analyse en composantes principales : son signe est
    indéterminé par construction. C'est exactement la faute qui a fait poser les
    ongles du MAUVAIS CÔTÉ de la main, et c'est la même famille de faute que le
    signe de `Spread` déduit d'une convention d'axes au lieu d'être mesuré. Une
    convention se transporte mal : ce qui « marche » sur la main gauche retombe
    faux sur la droite, en silence.

    Le fait, lui, est observable : EN FLÉCHISSANT, LES BOUTS DES DOIGTS PARTENT
    DU CÔTÉ DE LA PAUME. On ferme donc à moitié, on relève le déplacement des
    bouts, on lui retire ce qui va le long de la main (poignet → jointures) — un
    doigt qui se replie avance aussi vers le poignet — et ce qui reste EST le
    côté paume. Aucune convention n'intervient.

    ═══ CETTE FONCTION LAISSE LE RIG AU REPOS ═══
    Elle pose `Fist = 0,5` puis remet tout à zéro : elle DÉTRUIT la pose
    courante. On l'appelle une fois, avant de poser quoi que ce soit, et on
    garde son résultat — c'est ce que fait la sonde. L'appeler au milieu d'un
    balayage mesurerait la suite au repos sans rien dire.
    """
    pbh = rig.pose.bones[f"CTRL_hand{SIDE}"]

    bouts = [i for i, n in dom.items() if n.endswith(f"_03{SIDE}")]
    if not bouts:
        raise RuntimeError(f"aucun sommet dominé par un os _03{SIDE} : sans "
                           "bouts de doigts, le mouvement ne peut rien établir")
    # Par doigt, pour la contre-épreuve : une moyenne globale peut être franche
    # alors que deux doigts partent en sens opposés et s'annulent à moitié.
    bouts_par_doigt = {}
    for n in NOMS4:
        d = f"DEF_{n}_03{SIDE}"
        idx = [i for i, nm in dom.items() if nm == d]
        if not idx:
            raise RuntimeError(f"aucun sommet dominé par {d} : la contre-épreuve "
                               "par doigt est impossible")
        bouts_par_doigt[n] = idx

    neutre(rig, SIDE)
    p0 = _evalue(geo)
    # Indexation DIRECTE de la propriété : si `Fist` n'existe pas sur ce rig, ça
    # doit lever ici. Un `.get("Fist", 0.0)` rendrait une main immobile, donc un
    # déplacement nul, donc une direction nulle — et le zéro se lirait comme une
    # mesure jusqu'au bout de la chaîne.
    pbh["Fist"] = 0.5
    rafraichir(rig)
    p1 = _evalue(geo)
    neutre(rig, SIDE)

    dep = _somme(p1[i] - p0[i] for i in bouts)
    if dep.length < LONGUEUR_NULLE:
        raise RuntimeError("fléchir à Fist = 0,5 ne déplace AUCUN bout de "
                           "doigt : soit les drivers n'ont pas été évalués, "
                           "soit le rig ne fléchit pas — dans les deux cas la "
                           "direction palmaire ne s'établit pas")

    poignet = os_monde(rig, f"DEF_hand{SIDE}")
    knuck = {n: os_monde(rig, f"DEF_{n}_01{SIDE}") for n in NOMS4}
    # ═══ UNE GARDE PLACÉE APRÈS `.normalized()` NE GARDE PLUS RIEN ═══
    # Relecture adverse : la version précédente écrivait
    #     axe = (centre - poignet).normalized()
    #     if axe.length < 1e-9: ...
    # `mathutils` ne lève pas sur un vecteur nul, il rend un vecteur nul — donc
    # ce test n'attrapait QUE le zéro strict. Un axe long de 1e-12 (poignet et
    # jointures quasi confondus, ou lecture partiellement cassée) passait la
    # garde et sortait normalisé : une direction de bruit, unitaire, donc
    # parfaitement crédible dans la suite du calcul, où elle sert à retirer la
    # composante axiale du déplacement. La direction palmaire entière en
    # dépendait. Les trois autres gardes du fichier éprouvent le vecteur BRUT
    # avant de le normaliser ; celle-ci était la seule à faire l'inverse, et
    # c'est la seule qui ne pouvait pas échouer comme elle le prétendait.
    #
    # Le diviseur vient de `len(knuck)` et non d'un `4.0` écrit à la main : le
    # `4` en dur était un second exemplaire de `len(NOMS4)`, et deux exemplaires
    # d'une même quantité finissent par diverger — ajouter un cinquième rayon
    # aurait laissé le centre des jointures faux sans rien casser visiblement.
    axe = (_somme(knuck.values()) / float(len(knuck))) - poignet
    if axe.length < LONGUEUR_NULLE:
        raise RuntimeError("le poignet et le centre des jointures sont au même "
                           "point : l'axe de la main ne s'établit pas")
    axe = axe.normalized()
    palmaire = (dep - axe * dep.dot(axe))
    if palmaire.length < LONGUEUR_NULLE:
        raise RuntimeError("le déplacement des bouts est entièrement le long de "
                           "la main : il ne reste rien pour désigner la paume")
    palmaire = palmaire.normalized()

    # ═══ LA CONTRE-ÉPREUVE, ET ELLE PEUT ÉCHOUER ═══
    # Une direction moyenne ne prouve rien si les quatre doigts ne s'accordent
    # pas : deux doigts partant à l'opposé laisseraient une résultante franche
    # et pourtant dénuée de sens. On exige donc que CHAQUE doigt ait avancé du
    # côté trouvé. Le critère est un signe, pas un seuil : il n'y a aucun nombre
    # à régler, donc rien à faire passer en trichant.
    for n, idx in bouts_par_doigt.items():
        moyen = _somme(p1[i] - p0[i] for i in idx) / float(len(idx))
        if moyen.dot(palmaire) <= 0.0:
            raise RuntimeError(
                f"le bout de {n} part du côté OPPOSÉ à la direction trouvée "
                f"({moyen.dot(palmaire) * EN_MM:.3f} mm de composante "
                "palmaire) : les quatre doigts ne fléchissent pas du même "
                "côté, la direction palmaire est indéterminée")
    return palmaire


# ═══════════════════════════════════════════════════════════════════
#   LA RÉFÉRENCE — REF_CUP
# ═══════════════════════════════════════════════════════════════════

def reference(rig, geo, SIDE, dom, palmaire):
    """Les trois grandeurs dans l'état COURANT. C'est le REF_CUP du cahier.

    À relever une fois, sur l'état choisi comme référence, puis à comparer aux
    mêmes trois grandeurs après avoir posé `Cup`. Le verdict se lit sur le
    couple, jamais sur une seule : creuser doit RESSERRER la paume (largeur en
    baisse) ET creuser l'arc (flèche en hausse). Le rig mesuré fait l'inverse
    des deux, et la grandeur au plan figé annonçait pourtant +0,98 mm.

    ═══ POURQUOI `palmaire` EST EXIGÉ ═══
    Le cahier l'annonce `reference(rig, geo, SIDE, dom)`. Le calculer ici serait
    un piège : `direction_palmaire` fléchit puis remet le rig AU REPOS. Une
    référence « dans l'état courant » qui commence par détruire l'état courant
    rendrait, dans tous les appels, les grandeurs de la POSE DE REPOS — sans
    rien dire, et avec des chiffres parfaitement plausibles. C'est la forme
    exacte du défaut de signature déjà rencontré une vingtaine de fois dans le
    dépôt : un champ rempli que personne ne lit, ou lu autrement qu'annoncé. La
    direction s'établit donc UNE fois, au repos, avant tout posage, et se passe.

    Ne rafraîchit pas et ne pose rien : mesurer ne doit pas déplacer. C'est à
    l'appelant d'avoir appelé `rafraichir(rig)` après sa dernière modification —
    sans quoi, en mode fond, il mesurerait l'état d'avant.
    """
    p = _evalue(geo)
    tetes = tetes_metacarpiennes(rig, SIDE)
    sommets = paume_sans_le_pouce(dom, SIDE)
    return {"arc_mm": arc_transverse(p, tetes, palmaire, sommets),
            "largeur_mm": largeur_paume(tetes),
            "pouce_auriculaire_mm": pouce_auriculaire(tetes)}
