"""
SONDE DE POIDS — l'audit du §6.1, et surtout : à quel point le classement du
dépôt tient-il par un cheveu ?

═══ POURQUOI CET OUTIL EXISTE ═══
Tout le contrôle de peau du dépôt repose sur UNE ligne, écrite trois fois
à l'identique (rig-main.py, verifier-rig.py, les deux sondes d'outils/) :

    DOM[v.index] = max(gs)[1]        # gs = [(poids, nom_de_groupe), …]

Un sommet est donc rangé dans la famille de son groupe le PLUS LOURD, et rien
d'autre n'est regardé. Un sommet à 51 % index et 49 % pouce est rangé « index »
avec exactement la même autorité qu'un sommet à 100 % index — alors qu'il est
tiré presque autant par le pouce, qu'il partira avec le pouce dès que le pouce
bougera, et que toutes les mesures bâties sur DOM (traversées, éventail, creux,
compression) le compteront pourtant du côté de l'index. Le classement ne ment
pas : il tait sa marge. Une marge tue est une mesure fausse en puissance, et
c'est la faute que ce dépôt a déjà commise sous d'autres formes (le zéro lu
comme une mesure, le head_local lu comme une pose).

Cette sonde publie donc, pour chaque sommet, l'ÉCART entre les deux poids
dominants. Sous 0,15, le classement est un arbitrage serré et non un fait ; les
sommets concernés sont listés à part, et ceux dont les deux dominants
appartiennent à DEUX FAMILLES différentes le sont encore à part — c'est le cas
exact du 51/49 index-pouce, celui qui fera bouger de la chair d'index quand le
pouce se pliera.

═══ CE QUI EST COMPTÉ, ET CE QUI NE L'EST PAS ═══
La normalisation ne porte QUE sur les groupes correspondant à des os
déformants (`pb.bone.use_deform`). Le maillage porte aussi des masques —
`ZONES_ARTICULAIRES` sert au lissage correctif, les `DBG_*` au diagnostic — et
ils sont pondérés. `vertex_group_normalize_all()` les normalise AVEC les os :
la somme des poids de peau d'un sommet peut donc valoir 0,80 alors que la somme
de tous ses groupes vaut 1,00. Un contrôle qui somme tout ne verrait rien ;
c'est pourquoi le tutoriel impose `poids_deformants()`, repris ici tel quel.
Le dépôt a d'ailleurs déjà payé cette confusion une fois : `ZONES_ARTICULAIRES`
dominait 203 sommets et fabriquait des intersections fantômes tant que
`famille()` le rangeait dans « hand ».

═══ AUCUNE POSE N'EST TOUCHÉE ═══
Cet audit ne lit que des données de REPOS : le maillage de base (c'est lui qui
porte les groupes de sommets — l'évalué peut en avoir un tout autre nombre si
une subdivision traîne) et les os au repos. Aucune voie pilotée par driver
n'est lue, donc rien à mettre en sourdine ici (règle 2 du dépôt) ; si quelqu'un
ajoute plus tard une mesure sur une pose, il devra taire les drivers ET faire
échouer sa sonde si les taire ne change rien. On ne remet pas non plus la pose
à zéro : un vérificateur ne modifie pas l'objet qu'il juge.

    blender --background --factory-startup --python-exit-code 1 \
      --python outils/sonde-poids-main.py -- FICHIER.blend [sortie.json]
"""
import json
import os
import sys

# ═══ NE PAS TAMPONNER LA SORTIE ═══
# Mesuré ailleurs dans ce dépôt : deux lancements de 11 et 16 minutes avaient
# écrit ZÉRO octet, et une exception laissait un journal vide — impossible de
# distinguer un calcul long d'un blocage.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

import bpy
# Pas de `mathutils` ici, et c'est délibéré : cet audit ne construit aucun
# arbre KD et ne cherche aucun voisin. Il ne pose aucune question de distance
# entre chairs — seulement des questions de poids, plus trois distances à des
# commissures, que la classe Vector de Blender rend directement.

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
NOMS4 = ["index", "middle", "ring", "pinky"]
FAMILLES_DOIGTS = NOMS4 + ["thumb"]

# ── LES SEUILS, ET D'OÙ ILS VIENNENT ──
# 0,005 : la limite exacte de `vertex_group_clean` en phase F. Exporter au-
# dessous reviendrait à publier des poids que le rig lui-même a déjà décidé
# d'effacer.
SEUIL_EXPORT = 0.005
# 0,01 : le seuil de TOUS les contrôles existants (rig-main, verifier-rig, les
# deux sondes). Le critère de phalange étrangère est repris avec CE seuil, et
# pas un autre, pour que son chiffre soit comparable ligne à ligne avec les
# rapports déjà rendus. Changer le seuil ici rendrait les deux séries
# incomparables — c'est précisément le défaut que sonde-ecartement.py corrige.
SEUIL_FAMILLE = 0.01
# 1,00 ± 0,02 : la tolérance de somme du §6.7, déjà utilisée telle quelle en
# phase F (`abs(somme - 1.0) > 0.02`).
TOLERANCE_SOMME = 0.02
INFLUENCES_MAX = 4
# 0,15 : la marge sous laquelle un classement par maximum n'est plus un fait.
SEUIL_AMBIGUITE = 0.15
# 22 mm : le rayon de commissure du dépôt (rig-main.py, `< 0.022`), établi sur
# la mesure « 1 043 sommets à deux doigts, dont 655 dans les creux ».
RAYON_COMMISSURE = 0.022


def rafraichir():
    # Les drivers ne s'évaluent pas en mode fond sans changement d'image.
    # Ici, l'audit ne dépend d'aucune pose — mais les matrices monde doivent
    # être cohérentes avant qu'on projette quoi que ce soit, et la règle du
    # dépôt est de ne jamais lire une donnée de graphe sans ces trois lignes.
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


rafraichir()

# ═══════════════════════════════════════════════════════════════════
#   QUELS GROUPES DÉFORMENT ? — ON LE DEMANDE AUX OS, PAS AUX NOMS
# ═══════════════════════════════════════════════════════════════════
# Filtrer sur le préfixe « DEF_ » serait une devinette de nom. La vérité est
# portée par l'os : `pb.bone.use_deform`. Un groupe sans os homonyme n'est
# tenu par personne — c'est un masque, et il n'entre pas dans la somme.
NOM_GROUPE = {g.index: g.name for g in geo.vertex_groups}
if not NOM_GROUPE:
    raise RuntimeError("le maillage ne porte aucun groupe de sommets : "
                       "il n'y a rien à auditer")

DEFORMANTS, MASQUES = set(), set()
for _nom in NOM_GROUPE.values():
    _pb = rig.pose.bones.get(_nom)
    if _pb is not None and _pb.bone.use_deform:
        DEFORMANTS.add(_nom)
    else:
        MASQUES.add(_nom)
if not DEFORMANTS:
    raise RuntimeError("aucun groupe ne correspond à un os déformant : la "
                       "sonde ne mesurerait que du vide et rendrait des "
                       "sommes nulles qu'on lirait comme des mesures")


def poids_deformants(v):
    """Les poids de `v` qui DÉFORMENT vraiment, du plus lourd au plus léger.

    ═══ AUCUNE VALEUR PAR DÉFAUT SUR UNE LECTURE ═══
    `NOM_GROUPE[g.group]` est indexé DIRECTEMENT, jamais par `.get(…, "")` :
    un indice de groupe qui n'existe pas dans la table est une incohérence de
    fichier, et elle doit lever. Rendue silencieusement sous un nom vide, elle
    ferait disparaître un poids réel de la somme — donc baisser la somme sous
    la tolérance — donc accuser le skinning d'un défaut qui serait le mien.
    """
    paires = [(g.weight, NOM_GROUPE[g.group]) for g in v.groups
              if NOM_GROUPE[g.group] in DEFORMANTS]
    paires.sort(key=lambda wn: (-wn[0], wn[1]))
    return paires


def poids_masques(v):
    """Ce que la normalisation de Blender a distribué HORS des os."""
    return [(g.weight, NOM_GROUPE[g.group]) for g in v.groups
            if NOM_GROUPE[g.group] in MASQUES]


def famille(n):
    # ═══ SEULS LES GROUPES D'OS SONT DES FAMILLES ═══
    # Repris mot pour mot de rig-main.py et verifier-rig.py : `ZONES_ARTICULAIRES`
    # n'est l'os de personne. Rangé dans « hand », il fabriquait des
    # intersections fantômes sur Pinch et OK et en cachait de vraies sur Point.
    for f in FAMILLES_DOIGTS:
        if n.startswith(f"DEF_{f}_"):
            return f
    return "hand" if n.startswith("DEF_") else None


# Un os déformant hors nomenclature « DEF_ » créerait un trou muet : ses poids
# entreraient dans la somme mais n'appartiendraient à aucune famille, et les
# critères de famille jugeraient une main incomplète en croyant la juger
# entière. On refuse de conclure plutôt que de conclure à moitié.
_sans_famille = sorted(n for n in DEFORMANTS if famille(n) is None)
if _sans_famille:
    raise RuntimeError("os déformants hors nomenclature DEF_ : "
                       f"{_sans_famille} — les critères de famille ne "
                       "couvriraient pas toute la peau")


def deux_dominants(paires):
    """Les deux plus gros poids, et l'écart qui les sépare.

    `paires` : [(poids, étiquette)] — des groupes, ou des familles déjà
    sommées. La même fonction sert aux deux, donc son auto-test (plus bas)
    couvre les deux.

    ═══ AVEC UNE SEULE INFLUENCE, IL N'Y A PAS D'ÉCART — ET ON LE DIT ═══
    Premier jet, réfuté en relecture : on rendait `(g1, w1, None, 0.0, w1)`,
    c'est-à-dire un SECOND POIDS DE 0,0 qui n'a jamais été mesuré, et un écart
    fabriqué à partir du seul poids présent. Le commentaire d'alors affirmait
    que « ça place le sommet aussi loin que possible du seuil d'ambiguïté ».
    C'est faux dès que le poids dominant est petit : un sommet tenu par UN seul
    os à 0,10 (le reste parti dans les masques) sortait avec un écart de 0,10,
    donc sous le seuil de 0,15, donc listé comme « classement serré entre deux
    concurrents » — avec un concurrent nommé None pesant 0,00. C'est très
    exactement la faute que ce dépôt s'interdit : un zéro qu'on n'a pas mesuré
    et qui se relit comme une mesure. Et l'auto-test d'alors prenait 0,8, une
    valeur choisie AU-DESSUS du seuil : il ne pouvait pas voir le défaut.

    Sans second concurrent, l'écart n'existe pas : on rend None, trois fois, et
    l'appelant doit se poser la question au lieu de comparer un nombre inventé.
    """
    if not paires:
        raise RuntimeError("deux_dominants() appelée sans aucun poids : un "
                           "sommet sans influence doit être traité comme tel "
                           "en amont, pas dilué dans un écart de 0,0")
    ordre = sorted(paires, key=lambda wn: (-wn[0], wn[1]))
    if len(ordre) == 1:
        return ordre[0][1], ordre[0][0], None, None, None
    return (ordre[0][1], ordre[0][0], ordre[1][1], ordre[1][0],
            ordre[0][0] - ordre[1][0])


def ecart_ambigu(ecart):
    """Un écart est ambigu s'il EXISTE et qu'il tombe sous le seuil.

    Le `is not None` porte tout le poids de cette fonction : sans lui, l'absence
    de concurrent se comparerait à 0,15 comme si c'était une mesure. On isole
    la question en une fonction pour pouvoir la faire échouer (voir plus bas) ;
    écrite en ligne dans la boucle, elle n'aurait jamais été éprouvée.
    """
    return ecart is not None and ecart < SEUIL_AMBIGUITE


# ═══ AUTO-TEST DE L'ÉCART — UNE SONDE QUI NE PEUT PAS ÉCHOUER NE PROUVE RIEN ═══
# L'écart est TOUTE la raison d'être de cet outil. S'il était calculé sur un
# tri croissant, ou sur la somme au lieu de la différence, il rendrait des
# nombres parfaitement plausibles et parfaitement faux — et il déclarerait
# « aucune ambiguïté » sur une main qui n'est qu'ambiguïtés. On le fait donc
# répondre sur un cas fabriqué dont on connaît la réponse : le 51/49 du brief.
_t = deux_dominants([(0.49, f"DEF_thumb_01{SIDE}"), (0.51, f"DEF_index_01{SIDE}")])
if (_t[0] != f"DEF_index_01{SIDE}" or _t[2] != f"DEF_thumb_01{SIDE}"
        or abs(_t[4] - 0.02) > 1e-9):
    raise RuntimeError(f"deux_dominants() se trompe sur le cas 51/49 : {_t}")
_t1 = deux_dominants([(0.8, "seul")])
if _t1[2] is not None or _t1[3] is not None or _t1[4] is not None:
    raise RuntimeError(f"deux_dominants() se trompe sur l'influence unique : {_t1}")
# ═══ LE CAS QUI A RÉFUTÉ LE PREMIER JET ═══
# L'auto-test précédent prenait 0,8 — au-DESSUS du seuil d'ambiguïté. Un écart
# fabriqué y passait inaperçu. On éprouve donc l'influence unique avec un poids
# SOUS le seuil : c'est le seul cas où la faute se voit. Si un jour quelqu'un
# refait rendre 0,0 au second poids, ce test tombe.
_t2 = deux_dominants([(0.10, "seul_et_leger")])
if _t2[3] is not None or ecart_ambigu(_t2[4]):
    raise RuntimeError(
        "un sommet à UNE seule influence de 0,10 est rendu ambigu : un second "
        f"poids jamais mesuré est relu comme une mesure ({_t2})")
# Et la contre-épreuve du contraire : le seuil doit encore mordre quand il y a
# vraiment deux concurrents serrés, sinon `ecart_ambigu` ne dirait jamais oui.
if not ecart_ambigu(deux_dominants([(0.50, "a"), (0.45, "b")])[4]):
    raise RuntimeError("ecart_ambigu() ne voit plus un écart de 0,05 : le "
                       "critère d'ambiguïté ne pourrait plus jamais se déclencher")

# ═══════════════════════════════════════════════════════════════════
#   LE REPOS : POSITIONS, NORMALES, COMMISSURES
# ═══════════════════════════════════════════════════════════════════
# Le maillage de BASE, et pas l'évalué : c'est lui qui porte les groupes de
# sommets, et un modificateur de subdivision rendrait un évalué dont les
# indices ne correspondraient à rien de ce qu'on audite.
_mw, _m3 = geo.matrix_world, geo.matrix_world.to_3x3()
POS = [_mw @ v.co.copy() for v in geo.data.vertices]
NRM = [(_m3 @ v.normal).normalized() for v in geo.data.vertices]
if not POS:
    raise RuntimeError("le maillage n'a aucun sommet : tous les comptes qui "
                       "suivent vaudraient zéro, et un zéro se lit comme une "
                       "mesure")

# ═══ ICI, head_local EST LA BONNE LECTURE — ET C'EST L'EXCEPTION ═══
# La règle du dépôt interdit `head_local` pour une position POSÉE : il rend le
# repos, et deux grandeurs de la sonde du creux sont sorties constantes au
# centième pour cette raison. Mais une commissure est un repère ANATOMIQUE de
# repos : rig-main.py la construit sur `ANATOMIE[…]["jointure"]`, relevée sur
# le maillage de base. La jointure d'un doigt, c'est la tête de son os « 01 »
# (rig-main.py, segs : ("01", d["jointure"], pip)). On la relit donc au repos,
# volontairement, et le critère reste comparable à celui du dépôt.
COMMISSURES = []
for _k in range(3):
    _a = rig.data.bones[f"DEF_{NOMS4[_k]}_01{SIDE}"].head_local
    _b = rig.data.bones[f"DEF_{NOMS4[_k + 1]}_01{SIDE}"].head_local
    COMMISSURES.append(rig.matrix_world @ ((_a + _b) / 2.0))


def distance_commissure(i):
    """Distance, en mètres, du sommet `i` à la commissure la plus proche."""
    return min((POS[i] - c).length for c in COMMISSURES)


def familles_de_phalanges(pd, seuil):
    """Les familles qui tirent ce sommet PAR UNE PHALANGE, au seuil donné.

    Ni métacarpien, ni `DEF_hand` : la règle 7 du tutoriel EXIGE que la base
    des doigts mélange DEF_hand, le métacarpien et la première phalange, et la
    paume est une chair continue. Compter le mélange des métacarpiens comme un
    défaut avait produit 12 521 faux positifs en phase F. Deux familles de
    PHALANGES sur un même sommet, en revanche, c'est un doigt qui en entraîne
    un autre — et ça, le §6.7 l'interdit.
    """
    return {famille(n) for w, n in pd
            if w > seuil and not n.endswith(f"_meta{SIDE}")
            and n != f"DEF_hand{SIDE}"} - {"hand"}


# ═══ CONTRE-ÉPREUVE DES COMMISSURES ═══
# Deux façons dont ce repère peut être faux sans qu'on le voie :
#   1. mauvais espace (local pris pour monde) — les disques tomberaient loin de
#      la chair, aucun sommet ne serait exempté, et le critère durcirait
#      silencieusement ;
#   2. disques trop larges — ils avaleraient la main entière, et le critère
#      « zéro phalange étrangère hors commissure » ne pourrait PLUS JAMAIS
#      échouer. Un critère qui ne peut pas échouer ne prouve rien.
_d_chair = [min((p - c).length for p in POS) for c in COMMISSURES]
if max(_d_chair) > 0.015:
    raise RuntimeError(
        "une commissure tombe à plus de 15 mm de toute chair "
        f"({[round(d * 1000, 1) for d in _d_chair]} mm) : le repère n'est pas "
        "dans le bon espace, et l'exemption ne protégerait rien")
_couverts = sum(1 for i in range(len(POS)) if distance_commissure(i) < RAYON_COMMISSURE)
_part_couverte = _couverts / len(POS)
if not 0.0 < _part_couverte < 0.5:
    raise RuntimeError(
        f"les disques de commissure couvrent {_part_couverte:.1%} du maillage : "
        "l'exemption est soit inexistante soit totale, et le critère de "
        "phalange étrangère ne pourrait pas être mis en défaut")

# ═══════════════════════════════════════════════════════════════════
#   LA CONNECTIVITÉ — reprise de morceaux(), rig-main.py
# ═══════════════════════════════════════════════════════════════════
# L'invariant qui avait attrapé une fragmentation du pouce que trois mesures de
# pose n'avaient pas vue, et que Sacha, lui, avait vue à l'œil.
_aretes = {}
for _e in geo.data.edges:
    _aretes.setdefault(_e.vertices[0], []).append(_e.vertices[1])
    _aretes.setdefault(_e.vertices[1], []).append(_e.vertices[0])


def morceaux(idx):
    reste, n, plus_gros = set(idx), 0, 0
    while reste:
        d = reste.pop(); pile, taille = [d], 1
        while pile:
            x = pile.pop()
            for y in _aretes.get(x, ()):
                if y in reste:
                    reste.discard(y); pile.append(y); taille += 1
        n += 1; plus_gros = max(plus_gros, taille)
    return n, plus_gros


# ═══════════════════════════════════════════════════════════════════
#   L'AUDIT, SOMMET PAR SOMMET
# ═══════════════════════════════════════════════════════════════════
sommets = []
sans_poids = []            # aucun poids déformant : ces sommets ne suivent RIEN
somme_hors_tolerance = []
trop_d_influences = []
ambigus_groupes = []       # écart des deux groupes dominants < 0,15
ambigus_familles = []      # écart des deux familles dominantes < 0,15
classement_fragile = []    # sommer les familles change la famille dominante
phalange_etrangere = []    # le critère du dépôt, seuil 0,01, hors commissure
_etrangere_au_seuil_export = 0      # le même compte au seuil d'export : la différence se dit
_masque_total = 0.0
_ecart_deux_sommes = 0
_par_famille = {}
_histogramme = {}

for v in geo.data.vertices:
    i = v.index
    # Calculée UNE fois : elle sert à quatre endroits, et un maillage de main
    # compte des dizaines de milliers de sommets.
    d_com = distance_commissure(i)
    pd = poids_deformants(v)
    pm = poids_masques(v)
    somme_def = sum(w for w, _n in pd)
    somme_mask = sum(w for w, _n in pm)
    _masque_total += somme_mask
    # ═══ LA SOMME TOTALE EST LUE À PART, PAS RECONSTITUÉE ═══
    # Premier jet, réfuté en relecture : on écrivait
    #     somme_tout = somme_def + sum(w for w, _n in pm)
    # et la contre-épreuve de fin de fichier vérifiait ensuite que
    # `somme_tout` diffère de `somme_def` quelque part. C'était une IDENTITÉ
    # arithmétique : la différence VAUT le total des masques par construction,
    # elle ne pouvait pas ne pas apparaître. Cette contre-épreuve ne pouvait
    # donc pas échouer, et une contre-épreuve qui ne peut pas échouer ne prouve
    # rien — c'est la règle 4 du dépôt, retournée contre son propre auteur.
    # On relit donc le total DIRECTEMENT sur `v.groups`, par un autre chemin.
    somme_tout = sum(g.weight for g in v.groups)
    # Et on exige que la partition ferme. C'est ce que la version tautologique
    # ne pouvait PAS voir : si un groupe échappait à la fois à DEFORMANTS et à
    # MASQUES, son poids disparaîtrait des deux sommes à la fois, toutes les
    # comparaisons resteraient cohérentes, et j'accuserais le skinning d'une
    # somme trop basse qui serait mon propre trou de classement.
    if abs((somme_def + somme_mask) - somme_tout) > 1e-6:
        raise RuntimeError(
            f"sommet {i} : os {somme_def:.6f} + masques {somme_mask:.6f} ne "
            f"font pas le total {somme_tout:.6f} — un groupe n'est ni rangé "
            "parmi les déformants ni parmi les masques, et son poids "
            "s'évapore de l'audit")
    if somme_mask > 1e-6:
        _ecart_deux_sommes += 1

    if not pd:
        # ═══ UN ZÉRO SE LIT COMME UNE MESURE ═══
        # Ce sommet n'est tenu par aucun os : il restera immobile pendant que
        # la main bouge. Le passer en silence le ferait compter comme « somme
        # 0,00 », c'est-à-dire comme un simple écart de normalisation. C'est un
        # défaut d'une autre nature, et il est nommé à part. Il entre AUSSI
        # dans l'histogramme, à zéro influence : un histogramme qui commence à
        # 1 laisserait croire que tout sommet est tenu par au moins un os.
        _histogramme[0] = _histogramme.get(0, 0) + 1
        sans_poids.append({"sommet": i,
                           "position_repos_mm": [round(x * 1000, 1) for x in POS[i]],
                           "groupes_non_deformants": sorted(n for _w, n in pm)})
        sommets.append({"sommet": i,
                        "position_repos_mm": [round(x * 1000, 1) for x in POS[i]],
                        "normale_repos": [round(x, 3) for x in NRM[i]],
                        "groupes_deformants": {},
                        "somme_poids_deformants": 0.0,
                        "somme_tous_groupes": round(somme_tout, 4),
                        "poids_deformant_sous_le_seuil": 0.0,
                        "influences_deformantes": 0,
                        "famille_du_groupe_dominant": None,
                        "famille_dominante_par_somme": None,
                        "deuxieme_famille": None,
                        "poids_par_famille": {},
                        "groupe_dominant": None, "deuxieme_groupe": None,
                        "ecart_deux_poids_dominants": None,
                        "ecart_deux_familles_dominantes": None,
                        "distance_commissure_mm": round(d_com * 1000, 1),
                        "sans_aucun_poids_deformant": True})
        continue

    retenus = [(w, n) for w, n in pd if w > SEUIL_EXPORT]
    sous_seuil = somme_def - sum(w for w, _n in retenus)
    influences = len(retenus)
    _histogramme[influences] = _histogramme.get(influences, 0) + 1

    # ── LE CLASSEMENT DU DÉPÔT, ET SA MARGE ──
    g1, w1, g2, w2, ecart_g = deux_dominants(pd)
    fam_dom_depot = famille(g1)

    # ── LE MÊME SOMMET, VU PAR FAMILLE ──
    # Un doigt répartit naturellement son poids entre 01, 02 et 03 : deux
    # groupes proches d'une MÊME famille ne sont pas une ambiguïté. Sommer par
    # famille sépare les deux questions — « quel os tire le plus » et « quel
    # DOIGT tire le plus » — et il arrive qu'elles n'aient pas la même réponse.
    par_fam = {}
    for w, n in pd:
        f = famille(n)
        par_fam[f] = par_fam.get(f, 0.0) + w
    f1, fw1, f2, fw2, ecart_f = deux_dominants([(w, f) for f, w in par_fam.items()])

    _par_famille.setdefault(fam_dom_depot, []).append(i)

    fiche = {"sommet": i,
             "position_repos_mm": [round(x * 1000, 1) for x in POS[i]],
             "normale_repos": [round(x, 3) for x in NRM[i]],
             "groupes_deformants": {n: round(w, 4) for w, n in retenus},
             "somme_poids_deformants": round(somme_def, 4),
             "somme_tous_groupes": round(somme_tout, 4),
             "poids_deformant_sous_le_seuil": round(sous_seuil, 4),
             "influences_deformantes": influences,
             "famille_du_groupe_dominant": fam_dom_depot,
             "famille_dominante_par_somme": f1,
             "deuxieme_famille": f2,
             "poids_par_famille": {f: round(w, 4) for f, w in par_fam.items()},
             "groupe_dominant": g1, "deuxieme_groupe": g2,
             # None, et pas 0,0 : « pas de second concurrent » n'est pas
             # « second concurrent à zéro ». Un lecteur du JSON qui trierait
             # sur cet écart mettrait les sommets les PLUS nets en tête de
             # liste des ambigus si on rendait 0,0 ici.
             "ecart_deux_poids_dominants": (None if ecart_g is None
                                            else round(ecart_g, 4)),
             "ecart_deux_familles_dominantes": (None if ecart_f is None
                                                else round(ecart_f, 4)),
             "distance_commissure_mm": round(d_com * 1000, 1),
             "sans_aucun_poids_deformant": False}
    sommets.append(fiche)

    # ── VERDICT 1 · la somme ──
    if abs(somme_def - 1.0) > TOLERANCE_SOMME:
        somme_hors_tolerance.append({"sommet": i,
                                     "somme_poids_deformants": round(somme_def, 4),
                                     "somme_tous_groupes": round(somme_tout, 4),
                                     "poids_hors_os": round(somme_tout - somme_def, 4)})
    # ── VERDICT 2 · les influences ──
    if influences > INFLUENCES_MAX:
        trop_d_influences.append({"sommet": i, "influences": influences,
                                  "groupes": {n: round(w, 4) for w, n in retenus}})

    # ── L'AMBIGUÏTÉ, LA RAISON D'ÊTRE DE L'OUTIL ──
    # `ecart_ambigu` refuse de conclure quand il n'y a pas de second concurrent.
    # Sans lui, un sommet tenu par un SEUL os léger entrait dans cette liste
    # avec un adversaire nommé None pesant 0,00.
    if ecart_ambigu(ecart_g):
        ambigus_groupes.append(
            {"sommet": i, "groupe_dominant": g1, "poids": round(w1, 4),
             "deuxieme_groupe": g2, "poids_second": round(w2, 4),
             "ecart": round(ecart_g, 4),
             "familles_differentes": (g2 is not None
                                      and famille(g2) != fam_dom_depot),
             "position_repos_mm": [round(x * 1000, 1) for x in POS[i]],
             "distance_commissure_mm": round(d_com * 1000, 1)})
    if ecart_ambigu(ecart_f):
        ambigus_familles.append(
            {"sommet": i, "famille_dominante": f1, "poids": round(fw1, 4),
             "deuxieme_famille": f2, "poids_second": round(fw2, 4),
             "ecart": round(ecart_f, 4),
             "position_repos_mm": [round(x * 1000, 1) for x in POS[i]],
             "distance_commissure_mm": round(d_com * 1000, 1)})
    if f1 != fam_dom_depot:
        # Le dépôt range ce sommet dans la famille de son groupe le plus lourd,
        # alors qu'une AUTRE famille pèse davantage une fois ses os additionnés.
        # Toutes les mesures bâties sur DOM le comptent du mauvais côté.
        classement_fragile.append(
            {"sommet": i, "famille_selon_le_depot": fam_dom_depot,
             "famille_si_on_somme": f1,
             "poids_par_famille": {f: round(w, 4) for f, w in par_fam.items()}})

    # ── VERDICT 3 · une phalange étrangère ──
    # Critère du dépôt, repris à l'identique, seuil compris : c'est au seuil
    # 0,01 que rig-main.py a compté ses 1 043 sommets à deux doigts, et un
    # chiffre rendu à un autre seuil ne serait pas comparable au sien. On
    # compte AUSSI au seuil d'export, et on publie les deux : si l'écart entre
    # les deux comptes est grand, c'est que le critère officiel tient à des
    # poids que le nettoyage a laissés juste sous sa ligne de flottaison.
    _fams_ph = familles_de_phalanges(pd, SEUIL_FAMILLE)
    _hors_creux = d_com >= RAYON_COMMISSURE
    if len(_fams_ph) > 1 and _hors_creux:
        phalange_etrangere.append(
            {"sommet": i, "familles": sorted(_fams_ph),
             "groupes": {n: round(w, 4) for w, n in retenus},
             "position_repos_mm": [round(x * 1000, 1) for x in POS[i]],
             "distance_commissure_mm": round(d_com * 1000, 1)})
    if len(familles_de_phalanges(pd, SEUIL_EXPORT)) > 1 and _hors_creux:
        _etrangere_au_seuil_export += 1

# ═══ CONTRE-ÉPREUVE DU FILTRE DÉFORMANT ═══
# L'essentiel du travail est fait dans la boucle : à chaque sommet, le total lu
# indépendamment sur `v.groups` doit être exactement retrouvé en additionnant
# les deux sacs. C'est cette ligne-là qui attraperait un groupe échappé.
# Il reste une seconde question, différente : le filtre avait-il de quoi
# MORDRE ? Si le maillage ne portait aucun masque, mes sommes « os seuls »
# seraient justes par chance et non par construction, et personne ne saurait
# distinguer les deux. On ne lève pas dans ce cas — un maillage sans masque est
# légitime — mais on le PUBLIE (`le_filtre_avait_de_quoi_mordre`), pour qu'un
# lecteur ne prenne pas une absence d'épreuve pour une épreuve réussie.
# On lève, en revanche, sur l'incohérence : du poids hors os existe au total,
# mais aucun sommet ne l'a vu passer.
if _masque_total > 1e-6 and _ecart_deux_sommes == 0:
    raise RuntimeError(
        f"{_masque_total:.3f} de poids hors os existe au total, et pourtant "
        "aucun sommet n'en porte : les deux comptes ne lisent pas la même "
        "chose, et l'un des deux est faux")

# ═══ CONTRE-ÉPREUVE DE morceaux() ═══
# La connectivité est reconstruite à la main ; si la table d'arêtes était vide
# ou mal remplie, morceaux() rendrait « 1 morceau » pour n'importe quoi et le
# verdict de fragmentation passerait toujours. On lui donne donc une famille
# ENTIÈRE augmentée d'un sommet qu'aucune arête ne relie à elle : le compte
# doit monter d'exactement un.
_familles_peuplees = {_f: _ii for _f, _ii in _par_famille.items()
                      if _f in FAMILLES_DOIGTS and _ii}
if not _familles_peuplees:
    raise RuntimeError("aucun sommet n'est dominé par une famille de doigt : "
                       "la sonde ne mesure pas ce qu'elle prétend")
_f_test = max(_familles_peuplees, key=lambda f: len(_familles_peuplees[f]))
_idx_test = set(_familles_peuplees[_f_test])
_intrus = None
for _i in range(len(POS)):
    if _i not in _idx_test and not (set(_aretes.get(_i, ())) & _idx_test):
        _intrus = _i
        break
if _intrus is None:
    raise RuntimeError("impossible de trouver un sommet détaché de la famille "
                       f"{_f_test} : la contre-épreuve de morceaux() ne peut "
                       "pas être menée, donc son verdict ne vaut rien")
_n_seul = morceaux(_idx_test)[0]
_n_avec = morceaux(list(_idx_test) + [_intrus])[0]
if _n_avec != _n_seul + 1:
    raise RuntimeError(
        f"morceaux() rend {_n_seul} puis {_n_avec} en ajoutant un sommet "
        "isolé : la connectivité qu'elle lit n'est pas celle du maillage")

# ── VERDICT 4 · chaque doigt d'un seul tenant ──
_entiers = {}
for _f in FAMILLES_DOIGTS:
    _idx = _par_famille.get(_f)
    if not _idx:
        # Une famille sans aucun sommet n'est pas « en un morceau » : elle est
        # absente. Le taire la ferait passer le critère par le silence.
        _entiers[_f] = {"morceaux": 0, "plus_gros": 0, "sommets": 0}
        continue
    _n, _g = morceaux(_idx)
    _entiers[_f] = {"morceaux": _n, "plus_gros": _g, "sommets": len(_idx)}
familles_fragmentees = [f for f, e in _entiers.items() if e["morceaux"] != 1]

# ═══════════════════════════════════════════════════════════════════
#   LES VERDICTS
# ═══════════════════════════════════════════════════════════════════
echecs = []


def exiger(nom, ok, mesure, seuil):
    if not ok:
        echecs.append({"critere": nom, "mesure": mesure, "seuil": seuil})
    print(f"{'OK   ' if ok else 'ÉCHEC'} · {nom} · mesuré {mesure} · exigé {seuil}")


print(f"\nFichier   : {os.path.basename(FICHIER)}")
print(f"Maillage  : {geo.name} · {len(POS)} sommets · {len(NOM_GROUPE)} groupes")
print(f"Os        : {len(DEFORMANTS)} groupes déformants, "
      f"{len(MASQUES)} masque(s) : {sorted(MASQUES) or 'aucun'}")
print(f"Poids distribué hors os (masques) : {_masque_total:.3f} "
      f"sur {_ecart_deux_sommes} sommet(s)")
print(f"Disques de commissure : {_couverts} sommets exemptés "
      f"({_part_couverte:.1%} du maillage, rayon {RAYON_COMMISSURE * 1000:.0f} mm)")

print("\n── Répartition par famille dominante (classement du dépôt) ──")
print(f"{'famille':>10} {'sommets':>9} {'morceaux':>9} {'plus gros':>10}")
for _f in FAMILLES_DOIGTS + ["hand"]:
    _idx = _par_famille.get(_f)
    _n_s = len(_idx) if _idx else 0
    if _f in _entiers:
        _e = _entiers[_f]
        print(f"{_f:>10} {_n_s:9d} {_e['morceaux']:9d} {_e['plus_gros']:10d}")
    else:
        _mm = morceaux(_idx) if _idx else (0, 0)
        print(f"{_f:>10} {_n_s:9d} {_mm[0]:9d} {_mm[1]:10d}")

print("\n── Nombre d'influences déformantes par sommet ──")
for _k in sorted(_histogramme):
    print(f"  {_k} influence(s) : {_histogramme[_k]} sommets")

print("\n── L'AMBIGUÏTÉ DU CLASSEMENT ──")
_croises = [a for a in ambigus_groupes if a["familles_differentes"]]
print(f"Sommets dont les deux groupes dominants sont séparés de moins de "
      f"{SEUIL_AMBIGUITE} : {len(ambigus_groupes)}")
print(f"  · dont les deux dominants appartiennent à DEUX FAMILLES : {len(_croises)}")
print(f"Sommets dont les deux FAMILLES dominantes sont séparées de moins de "
      f"{SEUIL_AMBIGUITE} : {len(ambigus_familles)}")
print(f"Sommets que le dépôt range dans une famille alors qu'une autre pèse "
      f"plus une fois sommée : {len(classement_fragile)}")
for _a in sorted(_croises, key=lambda a: a["ecart"])[:20]:
    print(f"  sommet {_a['sommet']:>6} · {_a['groupe_dominant']} {_a['poids']:.3f} "
          f"vs {_a['deuxieme_groupe']} {_a['poids_second']:.3f} · "
          f"écart {_a['ecart']:.3f} · commissure à "
          f"{_a['distance_commissure_mm']:.1f} mm")
if len(_croises) > 20:
    print(f"  … et {len(_croises) - 20} autres (liste complète dans le JSON)")

print("\n── Les quatre critères du §6.7 ──")
exiger("somme des poids déformants à 1,00 ± 0,02",
       not somme_hors_tolerance and not sans_poids,
       f"{len(somme_hors_tolerance)} hors tolérance + "
       f"{len(sans_poids)} sans aucun poids déformant",
       "0 sommet")
exiger(f"au plus {INFLUENCES_MAX} influences de déformation",
       not trop_d_influences, f"{len(trop_d_influences)} sommet(s) au-delà",
       f"0 sommet à plus de {INFLUENCES_MAX}")
exiger("aucune phalange étrangère hors commissure",
       not phalange_etrangere,
       f"{len(phalange_etrangere)} sommet(s) au seuil {SEUIL_FAMILLE} "
       f"({_etrangere_au_seuil_export} au seuil {SEUIL_EXPORT})",
       "0 sommet")
exiger("chaque famille de doigt en un seul morceau",
       not familles_fragmentees,
       {f: _entiers[f]["morceaux"] for f in FAMILLES_DOIGTS},
       "1 morceau par doigt")

for _liste, _titre in ((somme_hors_tolerance, "sommes hors tolérance"),
                       (trop_d_influences, "sommets à trop d'influences"),
                       (phalange_etrangere, "phalanges étrangères hors commissure"),
                       (sans_poids, "sommets sans aucun poids déformant")):
    if _liste:
        print(f"\n{_titre} ({len(_liste)}) — vingt premiers :")
        for _x in _liste[:20]:
            print("  " + json.dumps(_x, ensure_ascii=False))
        if len(_liste) > 20:
            print(f"  … et {len(_liste) - 20} autres (liste complète dans le JSON)")

resume = {
    "fichier": os.path.basename(FICHIER),
    "maillage": geo.name,
    "sommets": len(POS),
    "groupes_deformants": sorted(DEFORMANTS),
    "groupes_masques_exclus_de_la_somme": sorted(MASQUES),
    "poids_total_hors_os": round(_masque_total, 4),
    "sommets_ou_les_deux_sommes_different": _ecart_deux_sommes,
    "seuils": {"export": SEUIL_EXPORT, "famille": SEUIL_FAMILLE,
               "tolerance_somme": TOLERANCE_SOMME,
               "influences_max": INFLUENCES_MAX,
               "ambiguite": SEUIL_AMBIGUITE,
               "rayon_commissure_mm": RAYON_COMMISSURE * 1000},
    "commissures_mm": [[round(x * 1000, 1) for x in c] for c in COMMISSURES],
    "sommets_exemptes_par_les_commissures": _couverts,
    "part_du_maillage_exemptee": round(_part_couverte, 4),
    "histogramme_influences": {str(k): _histogramme[k] for k in sorted(_histogramme)},
    "familles": _entiers,
    "sommets_par_famille_dominante": {_f: len(_ii)
                                      for _f, _ii in _par_famille.items()},
    "ambiguite": {
        "seuil": SEUIL_AMBIGUITE,
        "sommets_a_ecart_de_groupes_faible": len(ambigus_groupes),
        "dont_deux_familles_differentes": len(_croises),
        "sommets_a_ecart_de_familles_faible": len(ambigus_familles),
        "sommets_dont_la_famille_change_si_on_somme": len(classement_fragile)},
    "verdicts": {
        "somme_hors_tolerance": len(somme_hors_tolerance),
        "sans_aucun_poids_deformant": len(sans_poids),
        "trop_d_influences": len(trop_d_influences),
        "phalange_etrangere_hors_commissure": len(phalange_etrangere),
        "phalange_etrangere_au_seuil_d_export": _etrangere_au_seuil_export,
        "familles_fragmentees": familles_fragmentees or "aucune"},
    "echecs": echecs,
    # ═══ CE QUE LA SONDE A DÛ PROUVER AVANT DE PARLER ═══
    # Chacune de ces lignes correspond à un test qui aurait fait LEVER le
    # script. Elles sont publiées pour qu'un lecteur puisse juger la sonde
    # avant de juger le rig — c'est la règle 4 du dépôt.
    "contre_epreuves": {
        "deux_dominants_sur_le_cas_51_49": "écart 0,02, familles index/thumb",
        "deux_dominants_sur_une_influence_unique":
            "pas de second concurrent : second poids et écart rendus None, "
            "jamais 0,0",
        "influence_unique_legere_0_10_non_declaree_ambigue":
            "éprouvé SOUS le seuil, seul endroit où un écart fabriqué se voit",
        "ecart_ambigu_mord_encore_sur_0_05": True,
        "partition_deformants_masques_fermee_sur_chaque_sommet":
            "os + masques = total relu sur v.groups, à 1e-6",
        # « 0 sommet » ici ne veut PAS dire « le filtre marche » : il veut dire
        # que le filtre n'avait rien à retirer. Les deux se lisent au même
        # endroit, on les distingue donc explicitement.
        "sommets_ou_le_filtre_a_retire_du_poids": _ecart_deux_sommes,
        "poids_total_retire_par_le_filtre": round(_masque_total, 4),
        "le_filtre_avait_de_quoi_mordre": _masque_total > 1e-6,
        "morceaux_sur_famille_puis_famille_plus_un_sommet_isole":
            f"{_n_seul} → {_n_avec} sur {_f_test}",
        "distance_de_chaque_commissure_a_la_chair_mm":
            [round(d * 1000, 1) for d in _d_chair],
        "part_du_maillage_exemptee_par_les_commissures": round(_part_couverte, 4)}}

print("\nATLAS_SONDE_POIDS " + json.dumps(resume, ensure_ascii=False))

if SORTIE:
    complet = dict(resume)
    complet["sommets_detail"] = sommets
    complet["listes"] = {
        "somme_hors_tolerance": somme_hors_tolerance,
        "sans_aucun_poids_deformant": sans_poids,
        "trop_d_influences": trop_d_influences,
        "phalange_etrangere_hors_commissure": phalange_etrangere,
        "ambigus_par_groupe": ambigus_groupes,
        "ambigus_par_groupe_familles_differentes": _croises,
        "ambigus_par_famille": ambigus_familles,
        "classement_qui_change_si_on_somme": classement_fragile}
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(complet, f, ensure_ascii=False, indent=1)
    print("écrit : " + SORTIE)
else:
    # Le détail par sommet est volumineux ; le déverser sur stdout noierait les
    # verdicts. On dit qu'il n'a pas été rendu plutôt que de laisser croire
    # qu'il n'existe pas.
    print("aucun fichier de sortie demandé : le détail sommet par sommet "
          "n'est pas rendu (passer un second argument pour l'obtenir)")

if echecs:
    print(f"\n{len(echecs)} critère(s) obligatoire(s) en échec.")
    sys.exit(2)
print("\nLes quatre critères de poids passent. "
      f"Reste {len(_croises)} sommet(s) dont le classement se joue à moins de "
      f"{SEUIL_AMBIGUITE} entre deux familles : ils passent les critères, "
      "mais leur appartenance n'est pas un fait.")
