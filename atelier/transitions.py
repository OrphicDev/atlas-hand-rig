"""
LES VRAIES ACTIONS DE TRANSITION — §11 du tutoriel.

╔══════════════════════════════════════════════════════════════════════════╗
║  POURQUOI CE MODULE EXISTE : UNE DROITE ENTRE DEUX ÉTATS PROPRES         ║
║  PASSE À TRAVERS LA CHAIR.                                               ║
╚══════════════════════════════════════════════════════════════════════════╝

`verifier-rig.py` (lignes 259-294) et `outils/playblast-transitions.py`
(`poser_fraction`) fabriquent tous deux le même mouvement : ils lisent la pose
d'arrivée, la multiplient par `u`, et appellent ça « la transition ». C'est une
INTERPOLATION LINÉAIRE entre le repos et l'arrivée, os par os et propriété par
propriété — un mouvement que personne n'a construit et que rien ne corrige.

Mesuré dans ce dépôt, et c'est la raison d'être du fichier :

    Neutral→Hand_Fist : les DEUX extrémités sont propres,
                        le pouce traverse l'index à t = 0,8 et 0,9,
                        puis il en ressort.

`nettoyer_transition()` (rig-main.py, ligne 3078) a été écrit pour ça, mais il
ne peut corriger le chemin qu'en déformant l'ARRIVÉE, puisque le chemin n'est
que l'arrivée multipliée. Il achète le milieu du geste avec sa fin. Le vrai
remède, celui du §11, est de donner au geste des ÉTATS CLÉS intermédiaires :
le pouce doit CONTOURNER l'index, et un contournement n'est pas sur la droite
qui joint deux états propres — il en sort, par définition.

L'ORDRE DES ÉVÉNEMENTS, qui est le fond du §11 :

    dégager · creuser · contourner · contacter · comprimer

Il est ici une DONNÉE (`ORDRE`) et un CONTRÔLE (`_verifier_profil`) : une
doctrine écrite dans un commentaire ne protège de rien, une doctrine qui lève
protège de tout ce qu'elle nomme.

CE QUE CE MODULE FOURNIT
    · `construire_action(rig, SIDE, nom_pose, etapes, images=25)` → Action
      nommée `Neutral_to_<nom_pose>`, avec de vraies clés à de vraies images ;
    · `scenario(nom_pose, reperes, props_arrivee, os_arrivee)` → les étapes
      des scénarios du tutoriel, calculées à partir de la pose d'arrivée
      RÉELLEMENT mesurée par l'appelant ;
    · `rejouer(rig, SIDE, action, image)` → pose l'état d'une image et
      rafraîchit, pour que le vérificateur mesure L'ACTION et non une
      interpolation qu'il aurait recalculée lui-même.

CE QUE CE MODULE NE FAIT PAS
    · il ne décide d'aucune valeur définitive : les coefficients de `PROFILS`
      et les degrés de `DETOURS` sont des POINTS DE DÉPART que l'appelant
      optimise (il possède les sondes d'intersection, pas nous) ;
    · il ne prononce aucun verdict de collision : il ne sait pas ce qu'est un
      sommet traversant. Il fournit la structure, l'interpolation, et de quoi
      rejouer honnêtement ;
    · il ne suppose RIEN sur les axes ni sur les signes : `Reperes` les exige
      de l'appelant, qui les a MESURÉS (phases C et D de `rig-main.py`).
      Réécrire ici `AXE_ECART = 2` serait un second exemplaire d'une grandeur
      mesurée ailleurs, c'est-à-dire la faute que tout ce dépôt combat.

═══ SUR BLENDER 5.x : UNE ACTION N'A PLUS DE `.fcurves` ═══

Mesuré ici même, `outils/playblast-transitions.py` ligne 195 : sous 5.x
`act.fcurves` lève `'Action' object has no attribute 'fcurves'` — les courbes
vivent dans `action.layers[…].strips[…].channelbag(slot).fcurves`. La
documentation de cette build donne la voie juste :

    Action.fcurve_ensure_for_datablock(datablock, data_path, index=0)
        « will also create the layer, keyframe strip, and action slot if
          necessary, and take care of assigning the action slot too »

C'est celle qu'on emprunte pour ÉCRIRE, et l'énumération
`layers→strips→channelbags` pour RELIRE. On ne relit jamais par la voie qui
crée : une lecture qui fabrique ce qu'elle ne trouve pas rend toujours un
résultat, donc ne prouve jamais rien.
"""
import math
import sys

# ═══ NE PAS TAMPONNER LA SORTIE ═══
# Mesuré dans ce dépôt : deux lancements de 11 et 16 minutes n'avaient écrit
# ZÉRO octet, et une exception laissait un journal vide. `mesures_paume.py`
# soutient qu'un module ne touche pas à la sortie de son hôte ; la règle de
# travail de ce chantier l'exige en tête de fichier. On tranche en faveur de la
# règle, mais SANS ÉCRASER un réglage existant : `line_buffering=True` ne
# change rien pour un hôte qui l'a déjà posé, et sauve celui qui l'a oublié.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass


# ═══════════════════════════════════════════════════════════════════
#   LA DOCTRINE, EN DONNÉES
# ═══════════════════════════════════════════════════════════════════

# L'ordre des événements du §11. « repos » ouvre la liste parce qu'une
# transition part toujours du neutre — c'est ce que son nom promet.
ORDRE = ("repos", "degager", "creuser", "contourner", "contacter", "comprimer")

# Le correctif de forme du §8.5. Il n'existe pas encore sur le rig de ce dépôt
# (aucun `shape_key` dans `rig-main.py`) : `scenario()` ne l'émet donc que si
# l'appelant déclare le canal disponible, et il ÉCRIT son omission au lieu de
# la taire. Un canal qu'on croit piloté et qui n'existe pas est la « signature
# Iris » du dépôt : un champ rempli que rien ne lit à l'arrivée.
#
# ═══ POURQUOI CE NOM EST DÉCLARÉ ICI, AVANT `ROLES` ═══
# Il était écrit DEUX FOIS : en toutes lettres dans `ROLES["correctif"]`, et
# ici. Deux exemplaires d'une même constante finissent toujours par diverger —
# c'est la faute que ce dépôt combat partout ailleurs. Et la divergence aurait
# été SILENCIEUSE : la branche « le rig porte le canal » de `scenario()` écrit
# `roles_props[PROP_CORRECTIF] = "correctif"` sans passer par
# `role_de_la_propriete()`, donc sans jamais consulter `ROLES`. Un seul
# exemplaire, et `ROLES` le cite.
PROP_CORRECTIF = "PSD_PinkyThumb"

# Les rôles regroupent les propriétés de la main par ce qu'elles FONT, et non
# par leur nom. Un rôle avance d'un seul coefficient dans un état clé : c'est
# ce qui permet d'écrire « à f13 la fermeture est aux deux tiers » sans réécrire
# les cinq propriétés qui la portent.
#
# ═══ POURQUOI PAS « MCP / PIP / DIP » COMME LE TUTORIEL ═══
# Le §9.8 décrit la fermeture articulation par articulation. Sur CE rig, le
# décalage entre MCP, PIP et DIP est DÉJÀ dans les drivers : `CASCADE`
# (rig-main.py, ligne 862) donne à chaque articulation sa pente et son retard,
# et les butées de la phase E écrêtent. `Fist = 0,35` produit donc exactement
# « MCP engagées, PIP qui commencent, DIP encore à plat ». Refaire ce décalage
# ici, dans les clés, le compterait DEUX FOIS.
ROLES = {
    "fermeture": ("Fist", "Index_Curl", "Middle_Curl", "Ring_Curl",
                  "Pinky_Curl"),
    "pouce": ("Thumb_Curl", "Thumb_Opposition"),
    "creux": ("Cup",),
    "ecartement": ("Spread",),
    "detente": ("Relax",),
    "correctif": (PROP_CORRECTIF,),
}

# ═══ LE ROLE D'UN OS DE CORRECTION SUIT SON DOIGT ═══
# Les corrections FK que l'optimiseur a trouvées pour la pose d'arrivée doivent
# arriver au même rythme que le doigt qu'elles corrigent : une correction de
# pouce qui monterait à la vitesse de la fermeture des quatre doigts poserait
# le pouce avant que la place soit faite.
def _role_de_l_os(nom_os):
    return "pouce" if "_thumb_" in nom_os else "fermeture"


def role_de_la_propriete(nom_prop):
    """Le rôle d'une propriété. Une propriété inconnue LÈVE.

    ═══ AUCUNE VALEUR PAR DÉFAUT SUR UNE LECTURE ═══
    Rendre « fermeture » pour une propriété qu'on ne connaît pas la ferait
    avancer au mauvais rythme, sans un mot. Une propriété nouvelle doit se
    déclarer dans `ROLES`, sinon le module refuse de deviner à quel moment du
    geste elle appartient.
    """
    for role, propriétés in ROLES.items():
        if nom_prop in propriétés:
            return role
    raise KeyError(
        f"propriété « {nom_prop} » dans aucun rôle de transitions.ROLES : "
        f"déclare-la (rôles connus : {', '.join(sorted(ROLES))})")


# ═══ LES DÉTOURS : CE QUI N'EST PAS SUR LA DROITE ═══
#
# Un détour est un écart TEMPORAIRE à la trajectoire, qui vaut 0 au repos et 0
# à l'arrivée, et qui culmine au milieu. C'est très exactement ce qu'une
# interpolation linéaire ne peut pas produire, et c'est ce qui manque au
# `t = 0,8` de Neutral→Hand_Fist.
#
# Chaque détour se lit : (gabarit d'os, axe nommé, degrés dans le sens utile).
# L'axe et le SIGNE ne sont pas écrits ici en dur : « flexion » et « ecart »
# sont résolus par les `Reperes` que l'appelant a mesurés. Retourner un signe à
# la main réparerait la main gauche et casserait la droite — c'est la faute
# que `SIGNE_ECART` corrige déjà dans `rig-main.py`.
#
# Les degrés sont des POINTS DE DÉPART, à l'échelle de ce qu'on observe : le
# pouce doit s'écarter d'une vingtaine de degrés pour laisser passer les quatre
# doigts. L'appelant les optimise avec ses sondes d'intersection.
DETOURS = {
    # Le pouce reste DEHORS pendant que les quatre doigts se ferment : c'est le
    # « pouce encore extérieur » de f7 (§9.8) et de f9 (§8.5).
    "pouce_dehors": (("CTRL_thumb_meta", "ecart", +22.0),
                     ("CTRL_thumb_01", "ecart", +8.0)),
    # Puis il CONTOURNE : il passe par-dessus les doigts déjà repliés au lieu
    # de traverser leur chair. C'est l'étape que la droite saute.
    "pouce_contourne": (("CTRL_thumb_meta", "flexion", +14.0),
                        ("CTRL_thumb_01", "flexion", +8.0)),
    # L'index s'écarte pour ouvrir le passage à la base duquel le pouce glisse
    # (§8.5, f16 : « le pouce contourne la base de l'index »).
    "index_s_ecarte": (("CTRL_index_01", "ecart", +9.0),),
    # L'auriculaire remonte VERS le pouce : à contre-sens de l'ouverture de
    # l'éventail, d'où le signe négatif sur le même axe mesuré.
    "auriculaire_remonte": (("CTRL_pinky_01", "ecart", -11.0),),
}

# Le nombre d'images du tutoriel. Les images des profils sont écrites dans
# cette échelle et remises à l'échelle demandée par `construire_action`.
IMAGES_TUTO = 25


def _etape_profil(image, phase, *, fermeture, pouce, creux, ecartement,
                  detente, correctif, pouce_dehors, pouce_contourne,
                  index_s_ecarte, auriculaire_remonte):
    """Un état clé du scénario, TOUS ses champs obligatoires.

    ═══ POURQUOI DES ARGUMENTS NOMMÉS SANS DÉFAUT ═══
    Un dictionnaire partiel se complète en silence par des zéros, et un zéro se
    lit comme une mesure. Ici, oublier `creux` sur une seule ligne lève un
    `TypeError` à l'import : c'est Python lui-même qui garantit que le tableau
    est complet, sans une ligne de contrôle.
    """
    return {"image": image, "phase": phase,
            "parts": {"fermeture": fermeture, "pouce": pouce, "creux": creux,
                      "ecartement": ecartement, "detente": detente,
                      "correctif": correctif},
            "detours": {"pouce_dehors": pouce_dehors,
                        "pouce_contourne": pouce_contourne,
                        "index_s_ecarte": index_s_ecarte,
                        "auriculaire_remonte": auriculaire_remonte}}


# ═══════════════════════════════════════════════════════════════════
#   LES SCÉNARIOS DU TUTORIEL — DES DONNÉES, PAS DU CODE FIGÉ
# ═══════════════════════════════════════════════════════════════════
#
# Les coefficients sont des FRACTIONS DE LA POSE D'ARRIVÉE, jamais des valeurs
# absolues. « Cup ~0,75 » du §8.5 se lit donc « aux trois quarts du creusement
# que l'optimiseur a retenu » : si la recherche trouve `Cup = 0,88`, l'étape
# vaut 0,66 et le geste reste juste. Écrire 0,75 en absolu ferait de cette
# étape un nombre qui ne suit plus rien.
PROFILS = {
    # ── §9.8 · LE POING ──
    # f1 repos ; f7 MCP engagées, PIP commencent, pouce encore extérieur ;
    # f13 PIP avancées, DIP commencent, Cup monte ; f19 quatre doigts presque
    # fermés, pouce contourne ; f25 fermeture complète, pouce posé.
    "Hand_Fist": (
        _etape_profil(1, "repos",
                      fermeture=0.00, pouce=0.00, creux=0.00, ecartement=0.00,
                      detente=0.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        # `Fist = 0,35` : la cascade des drivers met les MCP en route et fait
        # tout juste démarrer les PIP. Le pouce est écarté au maximum — il doit
        # être HORS du volume que les doigts vont balayer.
        _etape_profil(7, "degager",
                      fermeture=0.35, pouce=0.08, creux=0.15, ecartement=0.35,
                      detente=0.30, correctif=0.00,
                      pouce_dehors=1.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        # Le creux monte AVANT le contournement : une paume qui se creuse
        # déplace la base du pouce, et il vaut mieux qu'elle ait fini de bouger
        # quand le pouce cherche son passage.
        _etape_profil(13, "creuser",
                      fermeture=0.68, pouce=0.30, creux=0.60, ecartement=0.60,
                      detente=0.55, correctif=0.00,
                      pouce_dehors=0.70, pouce_contourne=0.00,
                      index_s_ecarte=0.35, auriculaire_remonte=0.00),
        # L'étape qui n'existe sur AUCUNE droite : le pouce rentre en fléchissant
        # par-dessus les doigts pendant qu'il perd son écartement. C'est ici que
        # le t = 0,8 mesuré traversait l'index.
        _etape_profil(19, "contourner",
                      fermeture=0.92, pouce=0.65, creux=0.90, ecartement=0.85,
                      detente=0.80, correctif=0.00,
                      pouce_dehors=0.30, pouce_contourne=1.00,
                      index_s_ecarte=0.20, auriculaire_remonte=0.00),
        _etape_profil(25, "contacter",
                      fermeture=1.00, pouce=1.00, creux=1.00, ecartement=1.00,
                      detente=1.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
    ),
    # ── §8.5 · LA PINCE AURICULAIRE-POUCE ──
    # f1 repos ; f9 index et majeur commencent à se replier, pouce encore
    # extérieur ; f16 Cup ~0,75, auriculaire remonte, pouce contourne la base
    # de l'index ; f21 pulpes proches, PSD_PinkyThumb commence à monter ;
    # f25 contact final, correctif à 1,0.
    "Hand_Pinky_Thumb": (
        _etape_profil(1, "repos",
                      fermeture=0.00, pouce=0.00, creux=0.00, ecartement=0.00,
                      detente=0.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        _etape_profil(9, "degager",
                      fermeture=0.35, pouce=0.10, creux=0.25, ecartement=0.40,
                      detente=0.35, correctif=0.00,
                      pouce_dehors=1.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        # Le creusement est ici aux trois quarts (« Cup ~0,75 » du tutoriel,
        # lu comme une fraction de l'arrivée) ET le pouce contourne : deux
        # événements sur la même image, étiquetée par le plus contraignant.
        _etape_profil(16, "contourner",
                      fermeture=0.80, pouce=0.55, creux=0.75, ecartement=0.75,
                      detente=0.70, correctif=0.00,
                      pouce_dehors=0.45, pouce_contourne=0.80,
                      index_s_ecarte=1.00, auriculaire_remonte=0.70),
        _etape_profil(21, "contacter",
                      fermeture=0.96, pouce=0.90, creux=0.95, ecartement=0.92,
                      detente=0.90, correctif=0.35,
                      pouce_dehors=0.00, pouce_contourne=0.35,
                      index_s_ecarte=0.45, auriculaire_remonte=0.30),
        # La compression : les pulpes sont en contact, le correctif de forme
        # finit de monter. Il monte EN DERNIER, sinon il corrigerait un
        # écrasement qui n'a pas encore lieu.
        _etape_profil(25, "comprimer",
                      fermeture=1.00, pouce=1.00, creux=1.00, ecartement=1.00,
                      detente=1.00, correctif=1.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
    ),
    # ── LES AUTRES : REPOS, DÉGAGEMENT, ARRIVÉE ──
    # Trois états au minimum, parce que même un geste simple doit dégager le
    # pouce avant de fermer quoi que ce soit. Les deux gestes de contact
    # (Pinch, OK) en portent quatre : leurs pulpes se rejoignent, donc leur
    # pouce contourne, donc l'étape de contournement leur est due.
    "Hand_Point": (
        _etape_profil(1, "repos",
                      fermeture=0.00, pouce=0.00, creux=0.00, ecartement=0.00,
                      detente=0.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        # L'index reste tendu pendant que les trois autres se ferment : il doit
        # s'écarter d'eux, sinon le majeur qui se replie vient le heurter.
        _etape_profil(10, "degager",
                      fermeture=0.40, pouce=0.20, creux=0.20, ecartement=0.45,
                      detente=0.40, correctif=0.00,
                      pouce_dehors=1.00, pouce_contourne=0.00,
                      index_s_ecarte=0.50, auriculaire_remonte=0.00),
        _etape_profil(25, "contacter",
                      fermeture=1.00, pouce=1.00, creux=1.00, ecartement=1.00,
                      detente=1.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
    ),
    "Hand_Cupped": (
        _etape_profil(1, "repos",
                      fermeture=0.00, pouce=0.00, creux=0.00, ecartement=0.00,
                      detente=0.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        # Le creux part DEVANT la fermeture : c'est le geste de la coupe, pas
        # celui d'un poing qu'on ouvrirait.
        _etape_profil(10, "creuser",
                      fermeture=0.25, pouce=0.25, creux=0.55, ecartement=0.50,
                      detente=0.45, correctif=0.00,
                      pouce_dehors=0.60, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        _etape_profil(25, "contacter",
                      fermeture=1.00, pouce=1.00, creux=1.00, ecartement=1.00,
                      detente=1.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
    ),
    "Hand_Pinch": (
        _etape_profil(1, "repos",
                      fermeture=0.00, pouce=0.00, creux=0.00, ecartement=0.00,
                      detente=0.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        _etape_profil(8, "degager",
                      fermeture=0.30, pouce=0.15, creux=0.20, ecartement=0.40,
                      detente=0.35, correctif=0.00,
                      pouce_dehors=1.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        _etape_profil(17, "contourner",
                      fermeture=0.75, pouce=0.60, creux=0.65, ecartement=0.75,
                      detente=0.70, correctif=0.00,
                      pouce_dehors=0.45, pouce_contourne=0.65,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        _etape_profil(25, "contacter",
                      fermeture=1.00, pouce=1.00, creux=1.00, ecartement=1.00,
                      detente=1.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
    ),
    "Hand_OK": (
        _etape_profil(1, "repos",
                      fermeture=0.00, pouce=0.00, creux=0.00, ecartement=0.00,
                      detente=0.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        _etape_profil(8, "degager",
                      fermeture=0.30, pouce=0.12, creux=0.15, ecartement=0.45,
                      detente=0.30, correctif=0.00,
                      pouce_dehors=1.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
        # L'anneau se ferme par l'extérieur : l'index reste écarté des trois
        # autres pendant que le pouce vient à sa rencontre, sinon le trou —
        # qui EST le geste, cf. `outils/anneau.py` — se referme en pincement.
        _etape_profil(17, "contourner",
                      fermeture=0.78, pouce=0.55, creux=0.55, ecartement=0.80,
                      detente=0.60, correctif=0.00,
                      pouce_dehors=0.50, pouce_contourne=0.55,
                      index_s_ecarte=0.60, auriculaire_remonte=0.00),
        _etape_profil(25, "contacter",
                      fermeture=1.00, pouce=1.00, creux=1.00, ecartement=1.00,
                      detente=1.00, correctif=0.00,
                      pouce_dehors=0.00, pouce_contourne=0.00,
                      index_s_ecarte=0.00, auriculaire_remonte=0.00),
    ),
}


# ═══════════════════════════════════════════════════════════════════
#   L'INTERPOLATION — §11.2
# ═══════════════════════════════════════════════════════════════════
#
# BEZIER doux pour les propriétés globales et les flexions : un geste qui part
# et s'arrête net n'est pas un geste, c'est une téléportation en 25 images.
#
# LINEAR pour ce qui doit rester STRICTEMENT MONOTONE, et il y a deux familles :
#
#   · les DÉTOURS. Un détour vaut 0, puis 22, puis 0. Une poignée de Bézier au
#     sommet d'un tel triangle produit un dépassement — c'est-à-dire une
#     SUR-ROTATION entre deux clés, très exactement le défaut qu'on cherche à
#     éviter : le pouce s'écarte de 26° là où on en avait demandé 22, et il
#     ressort du volume de la main.
#   · le CORRECTIF de forme. Il monte de 0 à 1 et ne doit jamais dépasser 1 :
#     au-delà, le delta sculpté s'applique en excès et la chair gonfle.
#
# Ce n'est pas une opinion : `_controler_depassements()` MESURE la courbe
# évaluée et rétrograde en LINEAR tout canal qui déborde, puis remesure.
INTERPOLATION = {"propriete": "BEZIER", "correctif": "LINEAR", "os": "LINEAR"}

# Les poignées automatiques CLAMPÉES ne dépassent pas aux extrema locaux ; les
# poignées `AUTO` simples, si. Le contrôle mesure de toute façon, mais on ne
# demande pas à Blender de fabriquer le défaut qu'on va traquer ensuite.
TYPE_DE_POIGNEE = "AUTO_CLAMPED"

# Tolérances du contrôle de dépassement. Séparées par nature : une propriété
# 0..1 et un angle en radians n'ont pas la même échelle, et un seuil unique
# serait aveugle sur l'une ou hystérique sur l'autre.
TOLERANCE_PROPRIETE = 1e-4              # sans unité
TOLERANCE_ANGLE = math.radians(0.02)    # radians ; 0,02° est du bruit de calcul
# Nombre de points d'échantillonnage entre deux clés. Une Bézier ne dépasse
# jamais très loin de son milieu : 9 points par intervalle suffisent à le voir,
# et le coût est nul (aucune évaluation de maillage n'est en jeu).
SOUS_PAS = 9


# ═══════════════════════════════════════════════════════════════════
#   LES REPÈRES MESURÉS PAR L'APPELANT
# ═══════════════════════════════════════════════════════════════════
class Reperes:
    """Ce que ce module refuse de deviner, et que l'appelant a MESURÉ.

    ═══ POURQUOI AUCUN DE CES CHAMPS N'A DE VALEUR PAR DÉFAUT ═══
    `AXE_FLEXION = 0` et `AXE_ECART = 2` sont ÉTABLIS par la phase C de
    `rig-main.py`, `SIGNE` par le test du sens de flexion, `SIGNE_ECART` par le
    balayage de l'éventail. Les réécrire ici en créerait un second exemplaire,
    et deux exemplaires d'une même mesure finissent toujours par diverger — la
    droite a sa normale de paume inversée, et un signe recopié la casserait.
    """

    __slots__ = ("side", "axe_flexion", "axe_ecart", "signe_flexion",
                 "signe_ecart", "canaux")

    def __init__(self, side, axe_flexion, axe_ecart, signe_flexion,
                 signe_ecart, canaux):
        if axe_flexion not in (0, 1, 2) or axe_ecart not in (0, 1, 2):
            raise ValueError("un axe d'euler vaut 0, 1 ou 2 : "
                             f"reçu {axe_flexion} et {axe_ecart}")
        if axe_flexion == axe_ecart:
            # Deux rôles sur le même index d'euler, c'est la faute 7 des règles
            # de ce dépôt : le second écrase le premier sans un mot.
            raise ValueError("flexion et écartement ne peuvent pas partager "
                             f"l'index d'euler {axe_flexion}")
        if abs(abs(float(signe_flexion)) - 1.0) > 1e-9 or \
                abs(abs(float(signe_ecart)) - 1.0) > 1e-9:
            raise ValueError("les signes mesurés valent +1 ou −1 : "
                             f"reçu {signe_flexion} et {signe_ecart}")
        self.side = side
        self.axe_flexion = int(axe_flexion)
        self.axe_ecart = int(axe_ecart)
        self.signe_flexion = float(signe_flexion)
        self.signe_ecart = float(signe_ecart)
        # Les canaux réellement disponibles sur ce rig (noms de propriétés de
        # `CTRL_hand`). Ils servent à REFUSER d'émettre un canal qui n'existe
        # pas, au lieu de le laisser filer jusqu'à un `KeyError` de Blender ou,
        # pire, jusqu'à une clé posée sur rien.
        self.canaux = frozenset(canaux)
        if not self.canaux:
            raise ValueError("aucun canal déclaré : passe les noms des "
                             "propriétés de CTRL_hand (PROPS de rig-main.py)")

    def axe(self, nom_axe):
        """« flexion » ou « ecart » → (index d'euler, signe mesuré)."""
        if nom_axe == "flexion":
            return self.axe_flexion, self.signe_flexion
        if nom_axe == "ecart":
            return self.axe_ecart, self.signe_ecart
        raise KeyError(f"axe nommé inconnu : {nom_axe!r} "
                       "(« flexion » ou « ecart »)")


# ═══════════════════════════════════════════════════════════════════
#   CONSTRUIRE LES ÉTAPES — PARTIE PUREMENT ARITHMÉTIQUE
# ═══════════════════════════════════════════════════════════════════
#
# Rien de Blender n'est nécessaire ici : ces fonctions se relisent, se testent
# et se lancent avec un `python3` ordinaire (`python3 atelier/transitions.py`).
# C'est délibéré — le tableau des scénarios est ce qu'il y a de plus facile à
# se tromper et de plus coûteux à éprouver dans Blender.

def _verifier_profil(nom_pose, profil):
    """L'ordre des événements est un CONTRÔLE, pas un commentaire.

    On y joint le domaine des coefficients : une part supérieure à 1 ferait
    DÉPASSER la pose d'arrivée au milieu du geste — c'est la même sur-rotation
    que celle qu'on traque dans les poignées de Bézier, glissée cette fois dans
    le tableau. Une part négative ferait reculer le geste avant de le faire.
    """
    rangs = []
    for etat in profil:
        phase = etat["phase"]
        if phase not in ORDRE:
            raise ValueError(f"{nom_pose} : phase inconnue {phase!r} "
                             f"(attendu l'une de {ORDRE})")
        for nom, valeur in etat["parts"].items():
            if not 0.0 <= valeur <= 1.0:
                raise ValueError(
                    f"{nom_pose} image {etat['image']} : la part « {nom} » vaut "
                    f"{valeur} — une fraction de la pose d'arrivée vit dans "
                    "[0, 1], au-delà elle dépasse la pose validée")
        for nom, valeur in etat["detours"].items():
            if not 0.0 <= valeur <= 1.0:
                raise ValueError(
                    f"{nom_pose} image {etat['image']} : le détour « {nom} » "
                    f"vaut {valeur} — un coefficient de détour vit dans [0, 1] ; "
                    "c'est le degré du détour, dans DETOURS, qui porte le signe")
        rangs.append(ORDRE.index(phase))
    if rangs != sorted(rangs):
        raise ValueError(
            f"{nom_pose} : les phases ne respectent pas l'ordre du §11 "
            f"({' → '.join(e['phase'] for e in profil)}) ; l'ordre est "
            f"{' → '.join(ORDRE)}")
    if profil[0]["phase"] != "repos":
        raise ValueError(f"{nom_pose} : une transition Neutral→… part du repos")


def _images_du_profil(profil, images):
    """Les images du tutoriel, remises à l'échelle demandée.

    Les profils sont écrits sur 25 images (§11). Demander 50 images ne doit pas
    tasser tout le geste dans la première seconde : on remet à l'échelle, et on
    LÈVE si deux états clés retombent sur la même image — un état clé écrasé
    par son voisin disparaîtrait sans un mot.
    """
    if images < len(profil):
        raise ValueError(f"{images} images pour {len(profil)} états clés : "
                         "il en faut au moins autant que d'états")
    sorties = []
    for etat in profil:
        f = etat["image"]
        if images == IMAGES_TUTO:
            sorties.append(f)
        else:
            sorties.append(1 + int(round((f - 1) * (images - 1)
                                         / float(IMAGES_TUTO - 1))))
    for a, b in zip(sorties, sorties[1:]):
        if b <= a:
            raise ValueError(
                f"remise à l'échelle sur {images} images : deux états clés "
                f"tombent sur les images {a} et {b} — augmente `images`")
    if sorties[0] != 1 or sorties[-1] != images:
        raise ValueError(f"après remise à l'échelle, le geste va de "
                         f"{sorties[0]} à {sorties[-1]} au lieu de 1 à {images}")
    return sorties


def scenario(nom_pose, reperes, props_arrivee, os_arrivee, images=IMAGES_TUTO):
    """Les étapes du §11 pour `nom_pose`, calées sur la pose d'arrivée MESURÉE.

    `props_arrivee` : {nom_propriété: valeur} — celui de `POSES` / `CONTACTS`.
    `os_arrivee`    : {(nom_os, index_euler): degrés} — les corrections FK que
                      l'optimiseur a retenues pour l'arrivée.

    Rend le couple `(etapes, omissions)` :
        · `etapes`    = la liste de triplets `(image, props, os)` attendue par
          `construire_action`, COMPLÈTE — chaque canal est présent à chaque
          étape. Un canal qui n'apparaîtrait qu'à partir de f19 serait
          extrapolé en constante vers l'arrière par Blender, et l'image 1 ne
          serait plus le repos : la transition ne mériterait plus son nom ;
        · `omissions` = les canaux du tutoriel que CE rig ne porte pas. La
          liste est rendue, pas tue : un scénario amputé qu'on croit complet
          est pire qu'un scénario refusé.
    """
    if nom_pose not in PROFILS:
        raise KeyError(
            f"aucun scénario pour {nom_pose!r} ; scénarios connus : "
            f"{', '.join(sorted(PROFILS))}. Écris-en un dans PROFILS, ou "
            "passe tes propres étapes directement à construire_action().")
    profil = PROFILS[nom_pose]
    _verifier_profil(nom_pose, profil)
    numeros = _images_du_profil(profil, images)

    # ── Les propriétés à piloter, et le rôle de chacune ──
    # Une propriété d'arrivée sans rôle LÈVE : elle avancerait sinon au rythme
    # de quelqu'un d'autre, ce qui est indétectable à la lecture du rapport.
    roles_props = {}
    for nom_prop in props_arrivee:
        if nom_prop not in reperes.canaux:
            raise KeyError(
                f"{nom_pose} : la pose d'arrivée pilote « {nom_prop} », que ce "
                "rig ne porte pas. Un canal absent est une clé posée sur rien.")
        roles_props[nom_prop] = role_de_la_propriete(nom_prop)

    # ── Le correctif de forme du §8.5 ──
    omissions = []
    veut_correctif = any(e["parts"]["correctif"] > 0.0 for e in profil)
    if veut_correctif:
        if PROP_CORRECTIF in props_arrivee:
            pass                      # déjà pris en charge ci-dessus
        elif PROP_CORRECTIF in reperes.canaux:
            # Le tutoriel donne son arrivée : 1,0. On l'ajoute explicitement.
            props_arrivee = dict(props_arrivee)
            props_arrivee[PROP_CORRECTIF] = 1.0
            roles_props[PROP_CORRECTIF] = "correctif"
        else:
            # ═══ UNE OMISSION SE DIT ═══
            # Le rig de ce dépôt n'a AUCUNE shape key (aucun `shape_key` dans
            # rig-main.py) : le correctif du §8.5 n'existe pas encore. On ne
            # pose pas une clé sur un canal inexistant, et on ne se tait pas
            # non plus — un champ au contrat que rien ne lit à l'arrivée est la
            # faute la plus répétée de ce chantier.
            omissions.append(PROP_CORRECTIF)
            print(f"ATLAS_TRANSITION_CANAL_ABSENT {nom_pose} : "
                  f"« {PROP_CORRECTIF} » n'existe pas sur ce rig — l'étape de "
                  "compression du §8.5 est construite SANS son correctif de "
                  "forme. Crée la shape key et son pilote pour l'obtenir.")

    # ── Les os à piloter : ceux de l'arrivée, plus ceux des détours ──
    # Un même (os, axe) peut recevoir une correction d'arrivée ET un détour :
    # on ADDITIONNE les deux avant d'écrire, jamais deux écritures sur la même
    # voie (règle 7 : le second écraserait le premier sans un mot).
    canaux_os = {}
    for cle, valeur in os_arrivee.items():
        if (not isinstance(cle, tuple)) or len(cle) != 2:
            raise TypeError(
                "os_arrivee se lit {(nom_os, index_euler): degrés} ; "
                f"reçu la clé {cle!r}")
        voie = (cle[0], int(cle[1]))
        # ═══ LA NORMALISATION EST ELLE-MÊME UN ÉCRASEMENT POSSIBLE ═══
        # `int(cle[1])` ramène `2` et `2.7` sur la MÊME voie, alors que ce sont
        # deux clés distinctes du dictionnaire de l'appelant : la seconde
        # écrasait la première sans un mot, ce qui est très exactement la
        # règle 7 déplacée du rig vers le tableau. On refuse au lieu de choisir.
        if voie in canaux_os:
            raise ValueError(
                f"{nom_pose} : os_arrivee décrit deux fois la voie "
                f"{voie[0]}[{voie[1]}] (clés distinctes ramenées au même index "
                "d'euler) — la seconde écraserait la première en silence")
        canaux_os[voie] = {"arrivee": float(valeur),
                           "role": _role_de_l_os(cle[0]),
                           "detours": {}}
    for nom_detour, morceaux in DETOURS.items():
        # `!= 0` et non `> 0` : un coefficient négatif serait refusé plus
        # haut, mais une lecture qui ne voit que le positif rendrait
        # « inutilisé » un détour bel et bien demandé.
        utilise = any(e["detours"][nom_detour] != 0.0 for e in profil)
        if not utilise:
            # ═══ PAS DE COURBE PLATE ═══
            # Un canal nul d'un bout à l'autre n'anime rien, encombre l'action
            # et fausse tout contrôle qui compte les courbes « qui bougent ».
            continue
        for gabarit, nom_axe, degres in morceaux:
            nom_os = gabarit + reperes.side
            indice, signe = reperes.axe(nom_axe)
            entree = canaux_os.setdefault(
                (nom_os, indice),
                {"arrivee": 0.0, "role": _role_de_l_os(nom_os), "detours": {}})
            if nom_detour in entree["detours"]:
                raise ValueError(f"{nom_detour} écrit deux fois sur "
                                 f"{nom_os}[{indice}]")
            entree["detours"][nom_detour] = degres * signe

    # ── Les étapes, enfin ──
    etapes = []
    for numero, etat in zip(numeros, profil):
        parts, coefs = etat["parts"], etat["detours"]
        props = {}
        for nom_prop, valeur in props_arrivee.items():
            part = parts[roles_props[nom_prop]]      # KeyError si rôle inconnu
            props[nom_prop] = float(valeur) * float(part)
        os_ = {}
        for (nom_os, indice), entree in canaux_os.items():
            v = entree["arrivee"] * parts[entree["role"]]
            for nom_detour, degres in entree["detours"].items():
                v += degres * coefs[nom_detour]      # KeyError si non déclaré
            os_[(nom_os, indice)] = v
        etapes.append((numero, props, os_))

    # ── Contre-épreuve de la construction ──
    # Sans elle, un profil dont tous les coefficients seraient nuls rendrait un
    # jeu d'étapes parfaitement cohérent et parfaitement immobile — et une main
    # immobile revient toujours à sa pose de repos, donc elle passe tout.
    if len(etapes) < 3:
        raise ValueError(f"{nom_pose} : {len(etapes)} état(s) clé(s) ; le §11 "
                         "en exige trois au minimum (repos, dégagement, arrivée)")
    _, props_fin, os_fin = etapes[-1]
    _, props_dep, os_dep = etapes[0]
    if any(abs(v) > 1e-12 for v in props_dep.values()) or \
            any(abs(v) > 1e-12 for v in os_dep.values()):
        raise ValueError(f"{nom_pose} : l'image 1 n'est pas le repos")

    # ═══ LE DÉPART ÉTAIT CONTRÔLÉ, L'ARRIVÉE NE L'ÉTAIT PAS ═══
    # Cette asymétrie laissait passer la faute la plus répétée de ce chantier :
    # un champ au contrat, rempli par l'appelant, que rien ne relit à
    # l'arrivée. Concrètement — le jour où le rig portera `PSD_PinkyThumb` et
    # où il entrera dans la pose d'arrivée d'un scénario dont la DERNIÈRE ligne
    # porte `correctif=0.00` (c'est le cas de Hand_Fist, Hand_Point,
    # Hand_Cupped, Hand_Pinch, Hand_OK), l'action livrerait ce canal à 0 dans
    # une pose que l'optimiseur a validée à 1,0, et personne ne le dirait.
    # Même chose pour toute ligne finale écrite à 0,98 « pour adoucir » : elle
    # livrerait une pose qui n'est PAS celle qui a été validée.
    #
    # Le contrôle porte aussi sur les voies de DÉTOUR (`arrivee` valant 0 pour
    # elles) : un détour qui ne reviendrait pas à zéro n'est plus un détour,
    # c'est une déformation permanente de la pose validée.
    for nom_prop, valeur in props_arrivee.items():
        if abs(props_fin[nom_prop] - float(valeur)) > 1e-9:
            raise ValueError(
                f"{nom_pose} : à l'image {etapes[-1][0]}, « {nom_prop} » vaut "
                f"{props_fin[nom_prop]!r} au lieu de la valeur validée "
                f"{float(valeur)!r}. La dernière ligne du profil doit porter le "
                f"rôle « {roles_props[nom_prop]} » à 1,00 exactement — sinon "
                "l'action ne finit pas sur la pose que l'optimiseur a retenue.")
    for voie, entree in canaux_os.items():
        if abs(os_fin[voie] - entree["arrivee"]) > 1e-9:
            raise ValueError(
                f"{nom_pose} : à l'image {etapes[-1][0]}, "
                f"{voie[0]}[{voie[1]}] vaut {os_fin[voie]:+.6f}° au lieu de "
                f"{entree['arrivee']:+.6f}° — soit une correction FK amputée, "
                "soit un détour qui ne revient pas à zéro.")

    # Pas de `default=` sur une lecture : un `max(..., default=0.0)` sur un
    # dictionnaire vide rend un zéro qui se lit comme une mesure. Un scénario
    # qui ne pilote AUCUN canal se dit tout seul, avec sa propre phrase.
    if not props_fin and not os_fin:
        raise ValueError(f"{nom_pose} : le scénario ne pilote aucun canal — "
                         "ni propriété de la main, ni voie d'os")
    bouge = (any(abs(v) > 1e-9 for v in props_fin.values())
             or any(abs(v) > 1e-9 for v in os_fin.values()))
    if not bouge:
        raise ValueError(f"{nom_pose} : la pose d'arrivée est le repos — "
                         "il n'y a pas de transition à construire")
    milieu = any(
        any(abs(props[k] - props_dep[k] - (props_fin[k] - props_dep[k])
                * (num - etapes[0][0]) / float(etapes[-1][0] - etapes[0][0]))
            > 1e-6 for k in props)
        or any(abs(os_[k] - os_dep[k] - (os_fin[k] - os_dep[k])
                   * (num - etapes[0][0]) / float(etapes[-1][0] - etapes[0][0]))
               > 1e-6 for k in os_)
        for num, props, os_ in etapes[1:-1])
    if not milieu:
        # Un scénario dont tous les états intermédiaires tombent PILE sur la
        # droite repos→arrivée ne fait rien d'autre que ce que le vérificateur
        # recalculait déjà. Le construire serait un mensonge par redondance.
        raise ValueError(
            f"{nom_pose} : tous les états clés sont sur la droite "
            "repos→arrivée — ce scénario ne contourne rien, il ne vaut pas "
            "mieux que l'interpolation linéaire qu'il remplace")
    return etapes, omissions


def completer_etapes(etapes):
    """Rendre explicite un jeu d'étapes écrit à la main, sans inventer de zéro.

    Un canal absent d'une étape intermédiaire est INTERPOLÉ LINÉAIREMENT entre
    les deux étapes voisines qui le mentionnent. Un canal absent de la première
    ou de la dernière étape LÈVE : on n'a alors rien pour l'interpoler, et le
    compléter par 0,0 fabriquerait une mesure.
    """
    canaux_p, canaux_o = set(), set()
    for _num, props, os_ in etapes:
        canaux_p |= set(props)
        canaux_o |= set(os_)
    for bord, quoi in ((etapes[0], "première"), (etapes[-1], "dernière")):
        manquants = ([c for c in canaux_p if c not in bord[1]]
                     + [c for c in canaux_o if c not in bord[2]])
        if manquants:
            raise KeyError(f"la {quoi} étape ne dit rien de {manquants} : "
                           "impossible d'interpoler sans inventer un zéro")

    def interpoler(indice, canal, ou):
        num = etapes[indice][0]
        avant = max(k for k in range(indice) if canal in etapes[k][ou])
        apres = min(k for k in range(indice + 1, len(etapes))
                    if canal in etapes[k][ou])
        n0, n1 = etapes[avant][0], etapes[apres][0]
        v0, v1 = etapes[avant][ou][canal], etapes[apres][ou][canal]
        return v0 + (v1 - v0) * (num - n0) / float(n1 - n0)

    sorties = []
    for i, (num, props, os_) in enumerate(etapes):
        p = dict(props)
        o = dict(os_)
        for c in canaux_p:
            if c not in p:
                p[c] = interpoler(i, c, 1)
        for c in canaux_o:
            if c not in o:
                o[c] = interpoler(i, c, 2)
        sorties.append((num, p, o))
    return sorties


# ═══════════════════════════════════════════════════════════════════
#   CÔTÉ BLENDER
# ═══════════════════════════════════════════════════════════════════
#
# `bpy` est importé PARESSEUSEMENT, comme dans `atelier/mesures_paume.py` :
# tout ce qui précède se relit et se teste hors de Blender.

def _bpy():
    import bpy                                            # noqa: WPS433
    return bpy


def _rafraichir(rig):
    """Les quatre lignes sans lesquelles on mesure une main immobile.

    ═══ LE PIÈGE LE PLUS COÛTEUX DE CE DÉPÔT ═══
    En mode fond, l'animation et les drivers ne s'évaluent pas tant que l'image
    ne change pas. Sans ceci, `rig.pose.bones[…].rotation_euler` rend la valeur
    qu'on vient d'écrire soi-même, ou celle de la pose de repos — et une main
    immobile revient toujours exactement à sa place, donc elle passe tous les
    contrôles. Une seule fonction, appelée partout, pour qu'elle ne puisse plus
    être oubliée à un endroit.
    """
    bpy = _bpy()
    rig.update_tag()
    rig.data.update_tag()
    scene = bpy.context.scene
    scene.frame_set(scene.frame_current)
    bpy.context.view_layer.update()


def _controleur_de_main(rig, side):
    nom = f"CTRL_hand{side}"
    if nom not in rig.pose.bones:
        raise KeyError(f"{rig.name} n'a pas d'os {nom} : ce n'est pas un rig "
                       "de main construit par rig-main.py")
    return rig.pose.bones[nom]


def _chemin(canal, side):
    """Un canal → (data_path, index) tels que Blender les écrit.

    `canal` vaut ("prop", nom) ou ("os", nom_os, index_euler).
    """
    if canal[0] == "prop":
        return f'pose.bones["CTRL_hand{side}"]["{canal[1]}"]', 0
    if canal[0] == "os":
        return f'pose.bones["{canal[1]}"].rotation_euler', int(canal[2])
    raise ValueError(f"canal inconnu : {canal!r}")


def _bornes_de_propriete(pbh, nom_prop):
    """Les butées DÉCLARÉES de la propriété, lues sur le rig.

    Aucune valeur par défaut : `as_dict()["min"]` lève si la propriété n'a pas
    d'interface. Une propriété sans butée déclarée n'est pas une propriété
    « sans limite », c'est une propriété dont on ignore la limite — et rendre
    (−inf, +inf) transformerait cette ignorance en autorisation.
    """
    ui = pbh.id_properties_ui(nom_prop)
    d = ui.as_dict()
    return float(d["min"]), float(d["max"])


def _toutes_les_courbes(action):
    """Les courbes de l'action, PAR LA VOIE QUI NE CRÉE RIEN.

    ═══ NE JAMAIS RELIRE PAR `fcurve_ensure_for_datablock` ═══
    Cette méthode CRÉE la courbe absente : une vérification qui l'emploierait
    trouverait toujours ce qu'elle cherche, et ne pourrait donc jamais échouer.
    On énumère `layers → strips → channelbags`, et on retombe sur l'ancienne
    `action.fcurves` pour les Blender d'avant 4.4 — d'où le `getattr`, puisque
    sous 5.x l'attribut n'existe plus et qu'y toucher lève.

    ═══ CE QUE CETTE FONCTION NE FAIT PAS ═══
    Elle ne LÈVE PAS sur une action sans courbe : elle rend `([], [])`. Le
    commentaire d'origine promettait ici une levée qui n'était écrite nulle
    part — un champ au contrat que rien ne lit à l'arrivée, la faute même que
    ce module documente. La levée appartient aux appelants, parce qu'eux seuls
    savent dire POURQUOI le vide est fautif (`construire_action` : l'écriture
    n'a rien produit ; `rejouer` : il n'y a rien à rejouer). Les deux la font,
    immédiatement après l'appel. Un futur appelant doit faire de même.
    """
    trouvees, voies = [], []
    couches = getattr(action, "layers", None)
    if couches:
        for couche in couches:
            for bande in couche.strips:
                sacs = getattr(bande, "channelbags", None)
                if sacs is not None:
                    for sac in sacs:
                        trouvees.extend(list(sac.fcurves))
                    voies.append("layers→strips→channelbags")
                    continue
                for emplacement in getattr(action, "slots", ()):
                    try:
                        sac = bande.channelbag(emplacement)
                    except (TypeError, RuntimeError):
                        sac = None
                    if sac is not None:
                        trouvees.extend(list(sac.fcurves))
                        voies.append("layers→strips→channelbag(slot)")
    if not trouvees:
        anciennes = getattr(action, "fcurves", None)
        if anciennes is not None:
            trouvees.extend(list(anciennes))
            voies.append("action.fcurves (avant 4.4)")
    return trouvees, sorted(set(voies))


def _courbe_a_ecrire(rig, action, data_path, index):
    """La courbe où écrire, par la voie 5.x, sinon par l'ancienne."""
    faire = getattr(action, "fcurve_ensure_for_datablock", None)
    if faire is not None:
        # Elle crée au besoin la couche, la bande, l'emplacement, ET assigne
        # l'emplacement au rig — c'est-à-dire tout ce qu'un `actions.new()` nu
        # laisse manquant sous 4.4+, et sans quoi l'action ne pilote rien.
        return faire(rig, data_path, index=index)
    anciennes = getattr(action, "fcurves", None)
    if anciennes is None:
        raise RuntimeError(
            "cette build n'expose ni Action.fcurve_ensure_for_datablock ni "
            "Action.fcurves : impossible d'écrire des courbes sans supposer "
            "une API. Aucune supposition ne sera faite.")
    existante = anciennes.find(data_path, index=index)
    return existante if existante is not None else anciennes.new(
        data_path, index=index)


def _emplacement_unique(action):
    """L'emplacement (slot) de l'action, s'il n'y en a qu'un.

    Sous 4.4+ une action assignée sans emplacement n'anime RIEN : le rig reste
    au repos et tous les contrôles passent, pour la pire des raisons.
    """
    emplacements = list(getattr(action, "slots", ()))
    if not emplacements:
        return None
    if len(emplacements) > 1:
        raise RuntimeError(
            f"{action.name} porte {len(emplacements)} emplacements : "
            "on ne devinera pas lequel anime le rig")
    return emplacements[0]


def _assigner(rig, action):
    """Assigner l'action ET son emplacement, puis rendre l'action précédente."""
    donnees = rig.animation_data or rig.animation_data_create()
    precedente = donnees.action
    donnees.action = action
    if hasattr(donnees, "action_slot"):
        emplacement = _emplacement_unique(action)
        if emplacement is not None and donnees.action_slot is not emplacement:
            donnees.action_slot = emplacement
    return donnees, precedente


def _remettre_a_zero(rig, side):
    """Le repos : tous les contrôleurs à zéro, toutes les propriétés à zéro.

    ═══ CE QUI N'EST PAS DANS L'ACTION GARDE LA POSE PRÉCÉDENTE ═══
    Mesuré dans `verifier-rig.py` (son commentaire de `neutre()`) : sans
    détacher l'action et remettre à zéro, le contrôle du retour au repos
    mesurait la pose précédente et rendait 123,9 mm. Un canal absent de
    l'action garde donc la valeur de l'étape d'avant, et on croirait mesurer
    l'image demandée alors qu'on mesure un mélange de deux.
    """
    donnees = rig.animation_data
    if donnees is not None:
        donnees.action = None
    for pb in rig.pose.bones:
        if pb.rotation_mode == "QUATERNION":
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        else:
            pb.rotation_euler = (0.0, 0.0, 0.0)
    pbh = _controleur_de_main(rig, side)
    for cle in list(pbh.keys()):
        if isinstance(pbh[cle], float):
            pbh[cle] = 0.0
    _rafraichir(rig)


# ═══════════════════════════════════════════════════════════════════
#   LE CONTRÔLE DE DÉPASSEMENT — §11.2
# ═══════════════════════════════════════════════════════════════════

def _depassement(courbe, bas, haut, tolerance):
    """Le pire débordement de la courbe ÉVALUÉE hors de [bas, haut].

    On échantillonne entre les clés, parce que c'est ENTRE elles qu'une poignée
    de Bézier déborde : aux clés, la valeur est celle qu'on a écrite, et une
    sonde qui ne regarderait que les clés rendrait toujours 0,00 — un résultat
    parfait qui ne prouverait rien.
    """
    points = list(courbe.keyframe_points)
    if len(points) < 2:
        return 0.0, None
    pire, ou = 0.0, None
    for a, b in zip(points, points[1:]):
        f0, f1 = a.co[0], b.co[0]
        # Les bornes LOCALES : entre deux clés, une valeur qui sort de
        # l'intervalle formé par ces deux clés est une sur-rotation, même si
        # elle reste dans les butées globales de la propriété.
        loc_bas = min(a.co[1], b.co[1])
        loc_haut = max(a.co[1], b.co[1])
        for k in range(SOUS_PAS + 1):
            f = f0 + (f1 - f0) * k / float(SOUS_PAS)
            v = courbe.evaluate(f)
            for seuil_bas, seuil_haut, genre in ((bas, haut, "butée"),
                                                 (loc_bas, loc_haut, "sur-rotation")):
                exces = max(seuil_bas - v, v - seuil_haut)
                if exces > tolerance and exces > pire:
                    pire, ou = exces, {"image": round(f, 3),
                                       "valeur": v, "genre": genre}
    return pire, ou


def _contre_epreuve_du_depassement(courbes, bornes):
    """Fabriquer un dépassement, et EXIGER que la sonde le voie.

    ═══ UNE SONDE QUI NE PEUT PAS ÉCHOUER NE PROUVE RIEN ═══
    Quatre fautes de sonde en un jour dans ce dépôt, dont deux rendaient un
    manquement FAUX. Ici, on prend une courbe qui varie, on tire sa poignée
    droite très au-dessus de son enveloppe, et on demande à `_depassement` de
    le signaler. S'il ne le voit pas, tout verdict « aucun dépassement » rendu
    plus haut est sans valeur, et on lève.

    ═══ ON ÉPROUVE L'APPEL EXACT SUR LEQUEL REPOSE LE VERDICT ═══
    Premier jet : la contre-épreuve appelait `_depassement(courbe, min(clés),
    max(clés), 0.0)`. Elle prouvait donc que la sonde voit un dépassement
    à tolérance NULLE et contre l'enveloppe des clés — deux arguments que le
    contrôle réel n'emploie jamais : lui passe les butées déclarées de la
    propriété et `TOLERANCE_PROPRIETE` / `TOLERANCE_ANGLE`. Une contre-épreuve
    qui n'éprouve pas l'appel réel est calibrée pour ne pas voir sa propre
    faute. On lui passe donc `bornes`, les MÊMES que `_controler_depassements`,
    et on lève si la clé manque plutôt que d'inventer un intervalle.

    Le pic fabriqué est calé au-dessus de la borne haute ET au-dessus de
    l'enveloppe des clés, pour qu'il déborde quelle que soit celle des deux qui
    est la plus lâche — sinon un canal d'os aux butées larges rendrait « rien
    vu » pour une raison parfaitement légitime, et la levée serait fausse.
    """
    for courbe in courbes:
        points = list(courbe.keyframe_points)
        if len(points) < 2:
            continue
        valeurs = [p.co[1] for p in points]
        amplitude = max(valeurs) - min(valeurs)
        if amplitude <= 1e-9:
            continue
        # KeyError si le canal manque : pas de borne inventée pour une sonde
        # dont tout le rôle est de prouver qu'on sait mesurer.
        bas, haut, tolerance = bornes[(courbe.data_path, courbe.array_index)]
        saut = max(amplitude, abs(haut - bas), 1.0) * 10.0
        k = points[0]
        memoire = (k.interpolation, k.handle_right_type,
                   tuple(k.handle_right), k.handle_left_type)
        try:
            k.interpolation = "BEZIER"
            k.handle_right_type = "FREE"
            k.handle_right = (k.co[0] + (points[1].co[0] - k.co[0]) * 0.5,
                              max(max(valeurs), haut) + saut)
            courbe.update()
            vu, _ou = _depassement(courbe, bas, haut, tolerance)
        finally:
            k.interpolation = memoire[0]
            k.handle_right_type = memoire[1]
            k.handle_right = memoire[2]
            k.handle_left_type = memoire[3]
            courbe.update()
        if vu <= 0.0:
            raise RuntimeError(
                "CONTRE-ÉPREUVE ÉCHOUÉE : une poignée tirée dix fois au-delà "
                f"de l'enveloppe de {courbe.data_path}[{courbe.array_index}] "
                f"et de sa borne haute ({haut:.6f}) n'a produit AUCUN "
                f"dépassement mesuré à la tolérance réelle ({tolerance:.2e}). "
                "La sonde ne peut pas échouer, donc ses verdicts ne valent "
                "rien.")
        return {"courbe": courbe.data_path, "index": courbe.array_index,
                "tolerance_eprouvee": tolerance,
                "depassement_fabrique": round(vu, 6)}
    raise RuntimeError(
        "aucune courbe ne varie dans cette action : rien à contre-éprouver, "
        "et une action immobile n'est pas une transition")


def _controler_depassements(courbes, bornes):
    """Mesurer, rétrograder en LINEAR ce qui déborde, remesurer, sinon LEVER."""
    rapport = {"corrigees": [], "restantes": []}
    for courbe in courbes:
        cle = (courbe.data_path, courbe.array_index)
        bas, haut, tolerance = bornes[cle]      # KeyError si un canal manque
        pire, ou = _depassement(courbe, bas, haut, tolerance)
        if pire <= 0.0:
            continue
        for point in courbe.keyframe_points:
            point.interpolation = "LINEAR"
        courbe.update()
        rapport["corrigees"].append({"courbe": cle[0], "index": cle[1],
                                     "depassement": round(pire, 6),
                                     "ou": ou})
        pire2, ou2 = _depassement(courbe, bas, haut, tolerance)
        if pire2 > 0.0:
            # Une droite entre deux clés ne peut pas sortir de l'intervalle de
            # ces deux clés : si ça déborde encore, ce sont les CLÉS qui sont
            # hors butées, et ce n'est pas un défaut d'interpolation.
            rapport["restantes"].append({"courbe": cle[0], "index": cle[1],
                                         "depassement": round(pire2, 6),
                                         "ou": ou2})
    if rapport["restantes"]:
        raise RuntimeError(
            "des clés sortent des butées de propriété, en LINEAR : "
            f"{rapport['restantes']} — corrige le scénario, pas la courbe")
    return rapport


# ═══════════════════════════════════════════════════════════════════
#   CONSTRUIRE L'ACTION
# ═══════════════════════════════════════════════════════════════════

def construire_action(rig, SIDE, nom_pose, etapes, images=IMAGES_TUTO,
                      bornes_os=None, remplacer=False):
    """L'action `Neutral_to_<nom_pose>`, avec de VRAIES clés intermédiaires.

    `etapes` : liste de triplets `(numero_image, props, os)`, où
        · `props` = {nom_propriété: valeur}
        · `os`    = {(nom_os, index_euler): degrés}
      exactement les deux formes que `poser_etat()` de `rig-main.py` accepte
      déjà — un troisième dialecte pour dire la même chose finirait par
      diverger du premier.

    `bornes_os` (facultatif) : {(nom_os, index_euler): (bas_deg, haut_deg)}.
      Sans lui, un canal d'os n'est contrôlé que contre l'enveloppe de ses
      propres clés. Ce n'est pas un défaut par défaut : les butées angulaires
      vivent dans les contraintes Limit Rotation de la phase E, et les
      recopier ici en ferait un second exemplaire.

    Rend l'Action. Le rig est laissé au repos, son action précédente rendue.
    """
    bpy = _bpy()
    if not etapes:
        raise ValueError("aucune étape : il n'y a rien à construire")
    pbh = _controleur_de_main(rig, SIDE)

    # ── 1 · les images ──
    numeros = [e[0] for e in etapes]
    if any(int(n) != n for n in numeros):
        raise TypeError(f"les numéros d'image sont des entiers : {numeros}")
    if numeros != sorted(set(numeros)):
        raise ValueError(f"images non strictement croissantes : {numeros}")
    if numeros[0] != 1 or numeros[-1] != images:
        raise ValueError(f"le geste doit aller de l'image 1 à l'image {images} ; "
                         f"reçu {numeros[0]} → {numeros[-1]}")
    if len(etapes) < 3:
        raise ValueError(
            f"{len(etapes)} état(s) clé(s) : le §11 en exige trois au minimum. "
            "Deux états, c'est exactement l'interpolation linéaire que ce "
            "module existe pour remplacer.")

    # ── 2 · les canaux, et leur complétude ──
    canaux = []
    for nom_prop in sorted(etapes[0][1]):
        canaux.append(("prop", nom_prop))
    for nom_os, indice in sorted(etapes[0][2]):
        canaux.append(("os", nom_os, int(indice)))
    for numero, props, os_ in etapes:
        attendus_p = {c[1] for c in canaux if c[0] == "prop"}
        attendus_o = {(c[1], c[2]) for c in canaux if c[0] == "os"}
        if set(props) != attendus_p or {(a, int(b)) for a, b in os_} != attendus_o:
            raise ValueError(
                f"l'image {numero} ne parle pas des mêmes canaux que l'image "
                f"{etapes[0][0]}. Une étape muette sur un canal le laisserait "
                "extrapolé en constante vers l'arrière, et l'image 1 ne serait "
                "plus le repos. Passe par completer_etapes().")
    # L'image 1 EST le repos : c'est ce que le nom `Neutral_to_…` promet, et
    # c'est ce que le vérificateur croit mesurer.
    if any(abs(v) > 1e-9 for v in etapes[0][1].values()) or \
            any(abs(v) > 1e-9 for v in etapes[0][2].values()):
        raise ValueError("l'image 1 n'est pas le repos : l'action porterait un "
                         "nom qui ment")

    # ── 3 · ces canaux existent-ils, et personne d'autre ne les écrit-il ? ──
    bornes = {}
    for canal in canaux:
        data_path, index = _chemin(canal, SIDE)
        if canal[0] == "prop":
            if canal[1] not in pbh.keys():
                raise KeyError(f"{pbh.name} n'a pas de propriété {canal[1]!r} : "
                               "une clé y serait posée sur rien")
            bas, haut = _bornes_de_propriete(pbh, canal[1])
            bornes[(data_path, index)] = (bas, haut, TOLERANCE_PROPRIETE)
        else:
            if canal[1] not in rig.pose.bones:
                raise KeyError(f"{rig.name} n'a pas d'os {canal[1]!r}")
            pb = rig.pose.bones[canal[1]]
            if pb.rotation_mode in ("QUATERNION", "AXIS_ANGLE"):
                # Keyer `rotation_euler` sur un os en quaternion écrit dans un
                # champ que Blender n'utilise pas : la clé existe, la courbe est
                # valide, et l'os ne bouge pas d'un degré. Silence complet.
                raise RuntimeError(
                    f"{canal[1]} est en mode {pb.rotation_mode} : une clé sur "
                    "rotation_euler n'y piloterait rien")
            valeurs = [math.radians(e[2][(canal[1], canal[2])]) for e in etapes]
            if bornes_os is not None and (canal[1], canal[2]) in bornes_os:
                b, h = bornes_os[(canal[1], canal[2])]
                bas, haut = math.radians(b), math.radians(h)
            else:
                bas, haut = min(valeurs), max(valeurs)
            bornes[(data_path, index)] = (bas, haut, TOLERANCE_ANGLE)
    # ═══ UN DRIVER RÉÉCRIT SA VOIE ═══
    # Règle 2 du dépôt, appliquée en amont : si un driver pilote déjà l'un de
    # ces canaux, notre clé sera écrasée à chaque évaluation SANS un mot, et le
    # rapport dira que la transition a été construite. Les drivers de ce rig
    # vivent sur les `MCH_*_result` ; s'il en apparaît un sur un `CTRL_` ou sur
    # une propriété de la main, c'est un conflit, pas un détail.
    pilotes = []
    if rig.animation_data:
        voies = {(d.data_path, d.array_index) for d in rig.animation_data.drivers}
        for canal in canaux:
            data_path, index = _chemin(canal, SIDE)
            if (data_path, index) in voies:
                pilotes.append(f"{data_path}[{index}]")
    if pilotes:
        raise RuntimeError("un driver pilote déjà " + ", ".join(pilotes)
                           + " : il écraserait nos clés en silence")

    # ── 4 · l'action ──
    nom_action = f"Neutral_to_{nom_pose}"
    if nom_action in bpy.data.actions:
        if not remplacer:
            # `actions.new()` renommerait silencieusement en « …001 », et
            # l'appelant rejouerait ensuite l'ANCIENNE action en croyant avoir
            # construit la nouvelle.
            raise RuntimeError(
                f"{nom_action} existe déjà ; passe remplacer=True pour "
                "l'écraser sciemment")
        ancienne = bpy.data.actions[nom_action]
        if rig.animation_data and rig.animation_data.action is ancienne:
            rig.animation_data.action = None
        bpy.data.actions.remove(ancienne)

    # ═══ CAPTURER L'ACTION PRÉCÉDENTE AVANT DE REMETTRE À ZÉRO ═══
    # `_remettre_a_zero` DÉTACHE l'action (c'est sa raison d'être, cf. le
    # `neutre()` de verifier-rig.py). La lire après lui rendrait `None`, et on
    # rendrait la main à l'appelant en ayant perdu son action en chemin, sans
    # un mot — la construction d'une transition n'a pas à défaire la pose sur
    # laquelle l'appelant travaillait.
    precedente = (rig.animation_data.action if rig.animation_data else None)
    # Sous 4.4+ l'emplacement fait partie de l'assignation : rendre l'action
    # sans son emplacement rendrait une action qui n'anime plus rien.
    precedent_emplacement = getattr(rig.animation_data, "action_slot", None) \
        if rig.animation_data else None
    _remettre_a_zero(rig, SIDE)
    action = bpy.data.actions.new(nom_action)
    donnees, _detachee = _assigner(rig, action)

    # ═══ ON N'INSÈRE PAS LES CLÉS PAR LA POSE ═══
    #
    # La voie « poser la valeur, puis `keyframe_insert` » oblige à rafraîchir
    # entre deux images ; or l'action est assignée, donc le rafraîchissement
    # RÉÉVALUE l'action et réécrit la pose avec les clés déjà posées. On
    # keyerait alors la valeur de l'image courante au lieu de celle qu'on
    # vient d'écrire. `outils/playblast-transitions.py` court exactement ce
    # risque (`poser_fraction` finit par un `frame_set`).
    #
    # On écrit donc directement dans les courbes : la valeur posée est celle
    # qu'on a calculée, sans aller-retour par la pose ni par le graphe.

    # ═══ ON MÉMORISE AVANT D'ÉCRIRE, ET ON REND CE QU'ON A PRIS ═══
    # Premier jet : la lecture et les deux écritures vivaient dans le même
    # `try`, et l'`except AttributeError` remettait `memoire_prefs = None`. Si
    # la seconde écriture échouait, la PREMIÈRE restait posée et n'était jamais
    # rendue : une préférence globale de Blender modifiée en silence par un
    # module d'atelier. On lit d'abord, on écrit ensuite, champ par champ, et
    # on ne rend que ce qu'on a effectivement pris.
    prefs = getattr(bpy.context.preferences, "edit", None)
    memoire_prefs = {}
    if prefs is not None:
        for champ, valeur in (("keyframe_new_interpolation_type",
                               INTERPOLATION["propriete"]),
                              ("keyframe_new_handle_type", TYPE_DE_POIGNEE)):
            if not hasattr(prefs, champ):
                continue
            memoire_prefs[champ] = getattr(prefs, champ)
            setattr(prefs, champ, valeur)
    try:
        for canal in canaux:
            data_path, index = _chemin(canal, SIDE)
            if canal[0] == "prop":
                mode = (INTERPOLATION["correctif"] if canal[1] == PROP_CORRECTIF
                        else INTERPOLATION["propriete"])
                lire = lambda e, c=canal: float(e[1][c[1]])          # noqa: E731
            else:
                mode = INTERPOLATION["os"]
                lire = lambda e, c=canal: math.radians(                # noqa: E731
                    float(e[2][(c[1], c[2])]))
            courbe = _courbe_a_ecrire(rig, action, data_path, index)
            if len(courbe.keyframe_points):
                raise RuntimeError(
                    f"{data_path}[{index}] portait déjà des clés dans une "
                    "action neuve : deux écritures sur la même voie")
            courbe.keyframe_points.add(len(etapes))
            for point, etape in zip(courbe.keyframe_points, etapes):
                point.co = (float(etape[0]), lire(etape))
                point.interpolation = mode
                point.handle_left_type = TYPE_DE_POIGNEE
                point.handle_right_type = TYPE_DE_POIGNEE
            # Hors de la plage de clés, la valeur reste celle du bord : une
            # extrapolation linéaire ferait continuer le geste au-delà de son
            # arrivée, et le rig s'auto-traverserait à l'image 26.
            courbe.extrapolation = "CONSTANT"
            courbe.update()
    finally:
        for champ, valeur in memoire_prefs.items():
            setattr(prefs, champ, valeur)

    # ── 5 · la relecture, par la voie qui ne crée rien ──
    courbes, voies = _toutes_les_courbes(action)
    if not courbes:
        raise RuntimeError(
            f"{nom_action} : aucune courbe relue après insertion. Sous 5.x les "
            "courbes vivent dans layers→strips→channelbags ; si cette voie est "
            "vide, l'écriture n'a rien produit et la transition n'existe pas.")
    attendues = {_chemin(c, SIDE) for c in canaux}
    relues = {(c.data_path, c.array_index) for c in courbes}
    if relues != attendues:
        raise RuntimeError(
            f"{nom_action} : courbes relues {sorted(relues - attendues)} en "
            f"trop, {sorted(attendues - relues)} manquantes")
    for courbe in courbes:
        if len(courbe.keyframe_points) != len(etapes):
            raise RuntimeError(
                f"{courbe.data_path}[{courbe.array_index}] porte "
                f"{len(courbe.keyframe_points)} clés pour {len(etapes)} états")

    # ── 6 · le contrôle de dépassement, et sa contre-épreuve ──
    preuve = _contre_epreuve_du_depassement(courbes, bornes)
    rapport = _controler_depassements(courbes, bornes)

    # ── 7 · l'action bouge-t-elle VRAIMENT le rig ? ──
    # Sans ce contrôle, une action bien formée mais non branchée (emplacement
    # 4.4+ non assigné, canal muet) laisse le rig au repos — et une main
    # immobile passe tous les contrôles.
    debut = rejouer(rig, SIDE, action, etapes[0][0])
    fin = rejouer(rig, SIDE, action, etapes[-1][0])
    ecarts = [abs(fin["props"][k] - debut["props"][k]) for k in debut["props"]]
    ecarts += [abs(fin["os"][k] - debut["os"][k]) for k in debut["os"]]
    if not ecarts or max(ecarts) < 1e-4:
        raise RuntimeError(
            f"{nom_action} : la première et la dernière image donnent le même "
            "état lu. L'action n'anime pas ce rig — vérifie l'emplacement "
            "(action_slot) et l'absence de NLA.")

    # ── 8 · rendre la scène comme on l'a trouvée ──
    # `_remettre_a_zero` détache l'action ; on rend ensuite celle que le rig
    # portait, ET on rafraîchit — sans quoi le rig resterait à la pose zéro
    # alors que son action dit autre chose, et la mesure suivante lirait un
    # état qui n'appartient à personne.
    _remettre_a_zero(rig, SIDE)
    donnees.action = precedente
    if precedente is not None and precedent_emplacement is not None \
            and hasattr(donnees, "action_slot"):
        donnees.action_slot = precedent_emplacement
    _rafraichir(rig)
    action.use_fake_user = True
    action["atlas_pose"] = nom_pose
    action["atlas_images"] = int(images)
    action["atlas_etats_cles"] = [int(n) for n in numeros]
    print(f"ATLAS_TRANSITION {nom_action} : {len(etapes)} états clés "
          f"{numeros}, {len(courbes)} courbes, voies {voies}, "
          f"contre-épreuve {preuve}, dépassements corrigés "
          f"{len(rapport['corrigees'])}")
    return action


# ═══════════════════════════════════════════════════════════════════
#   REJOUER — POUR QUE LE VÉRIFICATEUR MESURE L'ACTION
# ═══════════════════════════════════════════════════════════════════

def rejouer(rig, SIDE, action, image):
    """Poser l'état d'une image de l'action, et le rafraîchir.

    ═══ POURQUOI CETTE FONCTION EXISTE ═══
    `verifier-rig.py` et le playblast RECALCULENT la transition (`_cible_rot`
    multiplié par `_u`). Ils mesurent donc un mouvement que personne n'anime,
    et un contournement leur est invisible par construction. Avec `rejouer`,
    ils mesurent la courbe elle-même, à l'image elle-même.

    Rend {"props": {...}, "os": {(nom_os, indice): degrés}} — l'état RELU sur
    le rig, pas celui qu'on voulait poser.
    """
    bpy = _bpy()
    courbes, _voies = _toutes_les_courbes(action)
    if not courbes:
        raise RuntimeError(f"{action.name} n'expose aucune courbe : rien à "
                           "rejouer (sous 5.x, voir layers→strips→channelbags)")
    debuts = [c.keyframe_points[0].co[0] for c in courbes
              if len(c.keyframe_points)]
    fins = [c.keyframe_points[-1].co[0] for c in courbes
            if len(c.keyframe_points)]
    if not debuts:
        raise RuntimeError(f"{action.name} : des courbes sans aucune clé")
    if image < min(debuts) - 1e-9 or image > max(fins) + 1e-9:
        # Hors plage, l'extrapolation constante rend l'état du bord : on
        # croirait mesurer l'image demandée et on mesurerait l'arrivée.
        raise ValueError(f"image {image} hors de la plage de {action.name} "
                         f"({min(debuts):.0f} à {max(fins):.0f})")

    _remettre_a_zero(rig, SIDE)
    donnees, _precedente = _assigner(rig, action)
    if hasattr(donnees, "action_slot") and donnees.action_slot is None:
        raise RuntimeError(
            f"{action.name} est assignée sans emplacement : sous 4.4+ elle "
            "n'anime alors RIEN, et le rig reste au repos en silence")
    if donnees.use_nla and any(not p.mute for p in donnees.nla_tracks):
        # Une piste NLA active mélange ou remplace l'action : ce qu'on lirait
        # ne serait plus la courbe qu'on croit mesurer.
        raise RuntimeError(f"{rig.name} porte des pistes NLA actives : "
                           "l'action assignée n'est pas seule à décider")
    rig.update_tag()
    rig.data.update_tag()
    bpy.context.scene.frame_set(int(image))
    bpy.context.view_layer.update()

    # ── La relecture, et sa contre-épreuve ──
    # ═══ ON COMPARE À LA COURBE, PAS À CE QU'ON VOULAIT ═══
    # Si un driver, une contrainte, une piste NLA ou un emplacement manquant
    # réécrit la voie, la valeur lue diffère de la valeur de la courbe. C'est
    # la seule façon de s'apercevoir que la main n'est pas là où l'action le
    # dit — et c'est exactement la faute « un driver réécrit sa voie » de la
    # règle 2, prise du côté du résultat.
    pbh = _controleur_de_main(rig, SIDE)
    # ═══ LE CANAL LU DOIT ÊTRE CELUI QUE LA COURBE NOMME ═══
    # Une courbe de propriété porte le nom de son os dans son `data_path` ; on
    # lisait pourtant `pbh`, c'est-à-dire `CTRL_hand{SIDE}`, sans jamais
    # vérifier que les deux coïncident. Rejouer une action de main GAUCHE avec
    # `SIDE=".R"` lisait donc les propriétés de l'autre main. Et la contre-
    # épreuve « lu == courbe » ne l'attrapait pas à l'image 1 : les deux mains
    # y valent zéro, la comparaison passe, et `rejouer` rendait un état qui
    # n'appartient pas à l'action demandée. C'est le zéro qui se lit comme une
    # mesure, sous une autre forme.
    prefixe_prop = f'pose.bones["{pbh.name}"]['
    etat = {"image": int(image), "props": {}, "os": {}}
    ecarts = []
    for courbe in courbes:
        attendu = courbe.evaluate(float(image))
        chemin, index = courbe.data_path, courbe.array_index
        if chemin.endswith(".rotation_euler"):
            nom_os = chemin.split('"')[1]
            lu = rig.pose.bones[nom_os].rotation_euler[index]
            etat["os"][(nom_os, index)] = math.degrees(lu)
            toler = TOLERANCE_ANGLE * 10.0
        else:
            if not chemin.startswith(prefixe_prop):
                raise RuntimeError(
                    f"{action.name} : la courbe {chemin} ne porte pas sur "
                    f"{pbh.name}. Cette action n'est pas celle du côté "
                    f"{SIDE!r} — la lire ici mesurerait l'autre main.")
            nom_prop = chemin.split('"')[-2]
            if nom_prop not in pbh.keys():
                raise KeyError(f"{pbh.name} n'a pas de propriété "
                               f"{nom_prop!r} : la courbe {chemin} pilote un "
                               "canal qui n'existe pas")
            lu = float(pbh[nom_prop])
            etat["props"][nom_prop] = lu
            toler = TOLERANCE_PROPRIETE * 10.0
        if abs(lu - attendu) > toler:
            ecarts.append({"voie": f"{chemin}[{index}]",
                           "lu": round(lu, 6), "courbe": round(attendu, 6)})
    if ecarts:
        raise RuntimeError(
            f"{action.name} image {image} : l'état LU diffère de la courbe — "
            f"{ecarts}. Quelque chose d'autre écrit sur ces voies ; la mesure "
            "qui suivrait serait fausse sans le dire.")
    return etat


# ═══════════════════════════════════════════════════════════════════
#   AUTO-CONTRÔLE — se lance sans Blender : python3 atelier/transitions.py
# ═══════════════════════════════════════════════════════════════════

def _auto_controle():
    """Éprouver le tableau des scénarios, hors de Blender.

    Un profil se relit mal et coûte cher à éprouver dans Blender (une
    reconstruction est chiffrée à 53 min dans `rig-main.py`). Tout ce qui peut
    échouer sans Blender doit échouer ici, en une seconde.
    """
    fautes = []
    # Repères FICTIFS : cet auto-contrôle éprouve l'arithmétique du tableau,
    # pas le rig. Aucun de ces nombres ne doit servir ailleurs.
    reperes = Reperes(side=".L", axe_flexion=0, axe_ecart=2,
                      signe_flexion=-1.0, signe_ecart=+1.0,
                      canaux=("Fist", "Index_Curl", "Middle_Curl", "Ring_Curl",
                              "Pinky_Curl", "Thumb_Curl", "Thumb_Opposition",
                              "Spread", "Cup", "Relax"))
    arrivee = {"Fist": 1.0, "Cup": 0.8, "Thumb_Curl": 0.6,
               "Thumb_Opposition": 0.9, "Spread": -0.2, "Relax": 0.1}
    os_arrivee = {("CTRL_thumb_meta.L", 0): -7.5, ("CTRL_index_01.L", 2): 3.0}

    for nom in sorted(PROFILS):
        try:
            _verifier_profil(nom, PROFILS[nom])
        except Exception as e:
            fautes.append(f"{nom} · phases : {e}")
            continue
        try:
            etapes, omissions = scenario(nom, reperes, arrivee, os_arrivee)
        except Exception as e:
            fautes.append(f"{nom} · scénario : {e}")
            continue
        # L'image 1 est le repos, la dernière est l'arrivée EXACTE : un
        # coefficient final à 0,98 livrerait une pose qui n'est pas celle que
        # l'optimiseur a validée.
        for cle, valeur in arrivee.items():
            if abs(etapes[-1][1][cle] - valeur) > 1e-9:
                fautes.append(f"{nom} · l'arrivée de {cle} vaut "
                              f"{etapes[-1][1][cle]} au lieu de {valeur}")
        for cle, valeur in os_arrivee.items():
            if abs(etapes[-1][2][cle] - valeur) > 1e-9:
                fautes.append(f"{nom} · l'arrivée FK de {cle} vaut "
                              f"{etapes[-1][2][cle]} au lieu de {valeur}")
        # Les détours reviennent à zéro : un détour qui resterait à l'arrivée
        # ne serait pas un détour, ce serait une déformation de la pose validée.
        for (nom_os, indice), valeur in etapes[-1][2].items():
            # Pas de `.get(cle, 0.0)` : un zéro par défaut se lirait comme une
            # mesure, et ce contrôle-ci porte justement sur des zéros. Une voie
            # qui n'est pas dans l'arrivée est une voie de DÉTOUR, et un détour
            # doit valoir exactement zéro à l'arrivée.
            if (nom_os, indice) in os_arrivee:
                attendu = os_arrivee[(nom_os, indice)]
            else:
                attendu = 0.0
            if abs(valeur - attendu) > 1e-9:
                fautes.append(f"{nom} · le détour sur {nom_os}[{indice}] ne "
                              f"revient pas à zéro ({valeur:+.2f}°)")
        # Complétude : chaque canal à chaque étape.
        canaux_p = {frozenset(p) for _n, p, _o in etapes}
        canaux_o = {frozenset(o) for _n, _p, o in etapes}
        if len(canaux_p) != 1 or len(canaux_o) != 1:
            fautes.append(f"{nom} · les étapes ne parlent pas des mêmes canaux")
        # Le commentaire qui figurait ici annonçait « le contournement existe
        # VRAIMENT : au moins un canal quitte la droite » — au-dessus d'un code
        # qui imprimait les omissions. Une doctrine annoncée là où rien ne la
        # contrôle ne protège de rien. Ce contrôle-là existe, mais dans
        # `scenario()` (la garde `milieu`), et il LÈVE : arriver ici prouve
        # donc déjà que le scénario quitte la droite repos→arrivée.
        if omissions:
            print(f"  (omission signalée sur {nom} : {omissions})")
        print(f"  {nom} : {len(etapes)} états clés "
              f"{[n for n, _p, _o in etapes]} — "
              f"{len(etapes[0][1])} propriétés, {len(etapes[0][2])} voies d'os")

    # ═══ DEUX GARDES DISTINCTES, DEUX CONTRE-ÉPREUVES DISTINCTES ═══
    # `_images_du_profil` en porte deux : « pas assez d'images pour le nombre
    # d'états » et « deux états clés retombent sur la même image ». L'essai qui
    # figurait ici — Hand_Fist sur 4 images — passait par la PREMIÈRE : 4 < 5
    # états, la fonction lève au comptage et n'atteint jamais la boucle de
    # collision. La garde `b <= a` aurait donc pu être supprimée sans que
    # l'auto-contrôle s'en aperçoive : une contre-épreuve calibrée pour ne pas
    # voir sa propre faute, exactement le défaut que ce fichier documente.
    # On éprouve désormais les deux branches, et on EXIGE la bonne phrase :
    # sans ça, on referait la même erreur en croyant l'avoir corrigée.
    try:
        _images_du_profil(PROFILS["Hand_Fist"], 4)
        fautes.append("4 images pour 5 états clés aurait dû lever au comptage")
    except ValueError as _e:
        if "au moins autant que d'états" not in str(_e):
            fautes.append(f"le comptage d'images a levé pour une autre raison "
                          f"que la sienne : {_e}")
    # La collision, elle, ne s'obtient qu'avec des états clés SERRÉS : deux
    # états à une image d'écart, remis à l'échelle sur trois images, retombent
    # tous deux sur l'image 1. Aucun profil de PROFILS n'est assez serré pour
    # y arriver — c'est bien pour ça qu'il fallait le fabriquer.
    serre = tuple(
        _etape_profil(f, ph, fermeture=0.0, pouce=0.0, creux=0.0,
                      ecartement=0.0, detente=0.0, correctif=0.0,
                      pouce_dehors=0.0, pouce_contourne=0.0,
                      index_s_ecarte=0.0, auriculaire_remonte=0.0)
        for f, ph in ((1, "repos"), (2, "degager"), (25, "contacter")))
    try:
        _images_du_profil(serre, 3)
        fautes.append("deux états clés retombant sur la même image auraient dû "
                      "lever : un état clé écrasé disparaît sans un mot")
    except ValueError as _e:
        if "tombent sur les images" not in str(_e):
            fautes.append(f"la collision d'états clés a levé pour une autre "
                          f"raison que la sienne : {_e}")

    # Et le geste doit couvrir TOUTE la plage : un profil qui s'arrêterait à
    # l'image 20 sur 25 laisserait les cinq dernières images en extrapolation
    # constante — la main y serait figée sur son arrivée, et un playblast de
    # 25 images montrerait un geste qui finit avant la fin sans le dire.
    court = tuple(
        _etape_profil(f, ph, fermeture=0.0, pouce=0.0, creux=0.0,
                      ecartement=0.0, detente=0.0, correctif=0.0,
                      pouce_dehors=0.0, pouce_contourne=0.0,
                      index_s_ecarte=0.0, auriculaire_remonte=0.0)
        for f, ph in ((1, "repos"), (10, "degager"), (20, "contacter")))
    try:
        _images_du_profil(court, IMAGES_TUTO)
        fautes.append("un profil qui s'arrête à l'image 20 sur 25 aurait dû "
                      "lever : le geste ne couvre pas sa plage")
    except ValueError as _e:
        if "au lieu de 1 à" not in str(_e):
            fautes.append(f"la plage du geste a levé pour une autre raison "
                          f"que la sienne : {_e}")

    # ═══ UNE PROPRIÉTÉ SANS RÔLE NE PREND PAS LE RÔLE DU VOISIN ═══
    # `role_de_la_propriete` est le seul endroit du module où une valeur par
    # défaut serait invisible : rendre « fermeture » pour une propriété
    # inconnue la ferait avancer au rythme des quatre doigts sans un mot, et le
    # rapport n'en dirait rien. On éprouve la levée par la voie RÉELLE — un
    # canal déclaré sur le rig mais absent de `ROLES` —, pas seulement en
    # appelant la fonction à nu : c'est `scenario()` qui doit refuser.
    reperes_inconnu = Reperes(side=".L", axe_flexion=0, axe_ecart=2,
                              signe_flexion=-1.0, signe_ecart=+1.0,
                              canaux=tuple(reperes.canaux) + ("Canal_Sans_Role",))
    try:
        scenario("Hand_Fist", reperes_inconnu,
                 {**arrivee, "Canal_Sans_Role": 0.5}, os_arrivee)
        fautes.append("une propriété absente de ROLES aurait dû lever : sans "
                      "quoi elle avance au rythme de quelqu'un d'autre")
    except KeyError as _e:
        if "dans aucun rôle" not in str(_e):
            fautes.append(f"la propriété sans rôle a levé pour une autre "
                          f"raison que la sienne : {_e}")

    # ═══ CE QUE `Reperes` REFUSE ═══
    # Sa garde la plus importante est la règle 7 du dépôt : flexion et
    # écartement sur le même index d'euler, c'est le second driver qui écrase
    # le premier sans un mot. Aucune n'était éprouvée.
    _base_rep = dict(side=".L", axe_flexion=0, axe_ecart=2,
                     signe_flexion=-1.0, signe_ecart=+1.0,
                     canaux=tuple(reperes.canaux))
    for _mauvais, _phrase in ((dict(axe_flexion=3), "vaut 0, 1 ou 2"),
                              (dict(axe_flexion=2), "partager"),
                              (dict(signe_flexion=0.0), "les signes mesurés"),
                              (dict(canaux=()), "aucun canal déclaré")):
        _args = dict(_base_rep)
        _args.update(_mauvais)
        try:
            Reperes(**_args)
            fautes.append(f"Reperes a accepté {_mauvais} : il devait lever")
        except ValueError as _e:
            if _phrase not in str(_e):
                fautes.append(f"Reperes({_mauvais}) a levé pour une autre "
                              f"raison que la sienne : {_e}")
    try:
        reperes.axe("de_travers")
        fautes.append("Reperes.axe a accepté un axe nommé inconnu")
    except KeyError:
        pass

    # ═══ LA REMISE À L'ÉCHELLE CALCULE-T-ELLE JUSTE ? ═══
    # Ses deux GARDES étaient éprouvées, son ARITHMÉTIQUE ne l'était pas : rien
    # n'appelait `_images_du_profil` avec un nombre d'images différent de 25.
    # Sur 49 images, le pas double exactement — 1, 7, 13, 19, 25 devient
    # 1, 13, 25, 37, 49. L'attente est DÉDUITE (le doublement), pas recopiée
    # d'une sortie observée : une attente recopiée d'un résultat ne prouve que
    # sa propre stabilité.
    _ech = _images_du_profil(PROFILS["Hand_Fist"], 49)
    _double = [1 + 2 * (e["image"] - 1) for e in PROFILS["Hand_Fist"]]
    if _ech != _double:
        fautes.append(f"remise à l'échelle sur 49 images : {_ech} au lieu du "
                      f"pas doublé {_double}")

    # ═══ LE RÔLE D'UN OS DE CORRECTION SUIT SON DOIGT ═══
    # Une correction FK de pouce qui monterait au rythme de la fermeture des
    # quatre doigts poserait le pouce AVANT que la place soit faite — c'est le
    # défaut que tout ce module existe pour éviter. Rien ne le vérifiait.
    _etat_f7 = PROFILS["Hand_Fist"][1]["parts"]
    if abs(_etat_f7["pouce"] - _etat_f7["fermeture"]) < 1e-6:
        fautes.append("l'épreuve du rôle d'os ne distingue rien : à cette "
                      "image, « pouce » et « fermeture » avancent pareil")
    _e_pouce, _ = scenario("Hand_Fist", reperes, arrivee,
                           {("CTRL_thumb_meta.L", 0): -7.5})
    # À l'image 7, le détour `pouce_contourne` est nul : la voie ne porte donc
    # que la correction d'arrivée, multipliée par la part de SON rôle.
    _v7 = _e_pouce[1][2][("CTRL_thumb_meta.L", 0)]
    if abs(_v7 - (-7.5 * _etat_f7["pouce"])) > 1e-9:
        fautes.append(f"la correction FK du pouce vaut {_v7:+.4f}° à l'image "
                      f"7, soit {-7.5 * _etat_f7['fermeture']:+.4f}° si elle "
                      "suit la fermeture au lieu du pouce")

    # Le correctif de forme n'a qu'un seul nom dans ce module, et `ROLES` le
    # cite. Si un jour quelqu'un réintroduit un second exemplaire, il faut que
    # ça se dise ici plutôt que dans une pose livrée six mois plus tard.
    if role_de_la_propriete(PROP_CORRECTIF) != "correctif":
        fautes.append(f"PROP_CORRECTIF ({PROP_CORRECTIF}) n'a pas le rôle "
                      "« correctif » dans ROLES : les deux ont divergé")

    # ═══ LE SIGNE MESURÉ DOIT ARRIVER JUSQU'AU RÉSULTAT ═══
    # `DETOURS` ne porte que des degrés « dans le sens utile » ; c'est
    # `reperes.axe()` qui donne le signe, parce qu'un signe recopié à la main
    # réparerait la main gauche et casserait la droite. Rien ne le vérifiait :
    # en supprimant le `* signe`, tous les essais passaient encore (vérifié par
    # mutation), puisqu'ils ne regardent les détours qu'à l'arrivée, où ils
    # valent zéro — et zéro fois n'importe quel signe fait zéro.
    #
    # La contre-épreuve est SYMÉTRIQUE, sans nombre attendu écrit à la main :
    # on construit le même scénario avec les signes mesurés, puis avec les
    # signes inverses, et on exige que chaque valeur intermédiaire s'inverse.
    # Et on exige qu'au moins une soit non nulle, sinon « 0 == −0 » ferait
    # passer l'épreuve par identité arithmétique.
    _canaux_essai = tuple(reperes.canaux)
    _miroir = Reperes(side=".L", axe_flexion=0, axe_ecart=2,
                      signe_flexion=+1.0, signe_ecart=-1.0,
                      canaux=_canaux_essai)
    # `os_arrivee` vide : les seules voies d'os sont alors des DÉTOURS purs,
    # sans composante d'arrivée qui masquerait l'inversion.
    _e_mes, _ = scenario("Hand_Fist", reperes, arrivee, {})
    _e_mir, _ = scenario("Hand_Fist", _miroir, arrivee, {})
    _vus = 0
    for (_n1, _p1, _o1), (_n2, _p2, _o2) in zip(_e_mes[1:-1], _e_mir[1:-1]):
        for _voie, _v in _o1.items():
            if abs(_v) > 1e-9:
                _vus += 1
            if abs(_v + _o2[_voie]) > 1e-9:      # KeyError si la voie manque
                fautes.append(
                    f"signes inversés : {_voie[0]}[{_voie[1]}] vaut {_v:+.3f}° "
                    f"et {_o2[_voie]:+.3f}° au lieu de son opposé — le signe "
                    "mesuré n'atteint pas le résultat")
    if not _vus:
        fautes.append("l'épreuve des signes n'a vu que des zéros : elle "
                      "passerait par identité arithmétique, pas par mesure")

    # ═══ UN DÉTOUR NE S'ÉCRIT PAS DEUX FOIS SUR LA MÊME VOIE ═══
    # C'est la règle 7 du dépôt appliquée au tableau : deux morceaux d'un même
    # détour sur le même (os, axe), et le second écrase le premier sans un mot.
    # Aucune entrée de `DETOURS` ne le fait aujourd'hui — c'est bien pourquoi
    # la garde doit être éprouvée EN FABRIQUANT la faute : elle ne protège que
    # des écritures futures, et rien d'autre ici ne peut la déclencher.
    _memoire_detour = DETOURS["index_s_ecarte"]
    DETOURS["index_s_ecarte"] = (("CTRL_index_01", "ecart", +9.0),
                                 ("CTRL_index_01", "ecart", +4.0))
    try:
        scenario("Hand_Fist", reperes, arrivee, os_arrivee)
        fautes.append("un détour décrivant deux fois la même voie aurait dû "
                      "lever : le second morceau écrase le premier")
    except ValueError as _e:
        if "écrit deux fois" not in str(_e):
            fautes.append(f"le détour écrit deux fois a levé pour une autre "
                          f"raison que la sienne : {_e}")
    finally:
        DETOURS["index_s_ecarte"] = _memoire_detour

    # ═══ UN DÉTOUR INUTILISÉ N'OUVRE PAS DE COURBE ═══
    # « Un canal nul d'un bout à l'autre n'anime rien, encombre l'action et
    # fausse tout contrôle qui compte les courbes qui bougent », dit le code —
    # et rien ne le vérifiait. On l'éprouve DANS LES DEUX SENS, sinon un
    # module qui garderait tout, ou qui jetterait tout, passerait à moitié :
    # `auriculaire_remonte` est à zéro partout dans Hand_Fist et engagé dans
    # Hand_Pinky_Thumb ; sa voie doit donc être absente de l'un et présente
    # dans l'autre.
    _voie_auriculaire = (f"CTRL_pinky_01{reperes.side}", reperes.axe_ecart)
    _sans, _ = scenario("Hand_Fist", reperes, arrivee, {})
    _avec, _ = scenario("Hand_Pinky_Thumb", reperes, arrivee, {})
    if _voie_auriculaire in _sans[0][2]:
        fautes.append(f"Hand_Fist ouvre {_voie_auriculaire} alors que le "
                      "détour « auriculaire_remonte » y est nul partout")
    if _voie_auriculaire not in _avec[0][2]:
        fautes.append(f"Hand_Pinky_Thumb n'ouvre pas {_voie_auriculaire} alors "
                      "que « auriculaire_remonte » y est engagé à 0,70")

    # ═══ LES DEUX GARDES QUI NE FONT QU'AMÉLIORER LE MESSAGE ═══
    # « phase inconnue » et « aucun scénario pour … » retomberaient sinon sur
    # un `ORDRE.index()` ou un `PROFILS[…]` nus, qui lèvent bien mais sans dire
    # QUOI faire. On les éprouve quand même : le jour où quelqu'un les enlève
    # en les croyant décoratives, l'auto-contrôle doit le dire — c'est ce que
    # la mutation a montré, elles étaient les deux seules non éprouvées.
    inconnue = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=0.0,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c in ((1, "repos", 0.0), (13, "flotter", 0.5),
                         (25, "contacter", 1.0)))
    PROFILS["_essai_phase"] = inconnue
    try:
        scenario("_essai_phase", reperes, arrivee, os_arrivee)
        fautes.append("une phase absente d'ORDRE aurait dû lever : l'ordre des "
                      "événements du §11 est une donnée, pas une intention")
    except ValueError as _e:
        if "phase inconnue" not in str(_e):
            fautes.append(f"la phase inconnue a levé pour une autre raison "
                          f"que la sienne : {_e}")
    finally:
        del PROFILS["_essai_phase"]
    try:
        scenario("Hand_Salut_Militaire", reperes, arrivee, os_arrivee)
        fautes.append("une pose sans scénario aurait dû lever")
    except KeyError as _e:
        if "aucun scénario pour" not in str(_e):
            fautes.append(f"la pose sans scénario a levé pour une autre "
                          f"raison que la sienne : {_e}")

    # ═══ UN CANAL QUE LE RIG NE PORTE PAS EST UNE CLÉ POSÉE SUR RIEN ═══
    # Éprouvé avec une pose d'arrivée qui pilote `Cup` sur un rig déclaré sans
    # `Cup` : sans cette garde, l'étape serait construite, l'action écrite, et
    # c'est Blender qui aurait le dernier mot — ou personne.
    reperes_sans_cup = Reperes(
        side=".L", axe_flexion=0, axe_ecart=2,
        signe_flexion=-1.0, signe_ecart=+1.0,
        canaux=tuple(c for c in reperes.canaux if c != "Cup"))
    try:
        scenario("Hand_Fist", reperes_sans_cup, arrivee, os_arrivee)
        fautes.append("une propriété d'arrivée absente du rig aurait dû "
                      "lever : la clé serait posée sur rien")
    except KeyError as _e:
        if "que ce rig ne porte pas" not in str(_e):
            fautes.append(f"le canal absent a levé pour une autre raison que "
                          f"la sienne : {_e}")

    # ═══ DEUX ÉTATS, C'EST L'INTERPOLATION LINÉAIRE QU'ON REMPLACE ═══
    # Le commentaire annonçait « un jeu d'étapes à deux états doit être refusé…
    # On le fabrique » — et n'en fabriquait aucun : seul le scénario plat
    # l'était. Une deuxième doctrine annoncée sans contrôle. Vérifié par
    # mutation : en supprimant `len(etapes) < 3`, rien ne bronchait. Et il faut
    # EXIGER la phrase, car un profil à deux états n'a aucun état intermédiaire
    # et tombe donc aussi dans la garde « tous les états sont sur la droite » —
    # `except ValueError` tout court se ferait sauver par le voisin.
    duo = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=0.0,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c in ((1, "repos", 0.0), (25, "contacter", 1.0)))
    PROFILS["_essai_duo"] = duo
    try:
        scenario("_essai_duo", reperes, arrivee, os_arrivee)
        fautes.append("un profil à deux états aurait dû lever : deux états, "
                      "c'est exactement la droite que ce module remplace")
    except ValueError as _e:
        if "en exige trois au minimum" not in str(_e):
            fautes.append(f"le profil à deux états a levé pour une autre "
                          f"raison que la sienne : {_e}")
    finally:
        del PROFILS["_essai_duo"]

    # …et un scénario dont TOUS les états tombent sur la droite repos→arrivée.
    plat = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=0.0,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c in ((1, "repos", 0.0), (13, "degager", 0.5),
                         (25, "contacter", 1.0)))
    PROFILS["_essai_plat"] = plat
    try:
        scenario("_essai_plat", reperes, arrivee, os_arrivee)
        fautes.append("un scénario entièrement sur la droite aurait dû lever : "
                      "sans quoi ce module ne vaut pas mieux que "
                      "l'interpolation linéaire qu'il remplace")
    except ValueError:
        pass
    finally:
        del PROFILS["_essai_plat"]

    # Une part au-delà de 1 dépasserait la pose d'arrivée AU MILIEU du geste :
    # la sur-rotation, entrée par le tableau au lieu d'entrer par les poignées.
    #
    # ═══ CET ESSAI NE PROUVAIT PLUS CE QU'IL ANNONÇAIT ═══
    # Sa première écriture ne portait 1,4 que sur `fermeture` et laissait les
    # autres rôles à 0,00 sur la DERNIÈRE ligne. Depuis que `scenario()` exige
    # que l'arrivée soit la pose validée, ce profil-là lève de toute façon —
    # par la garde d'arrivée, pas par la garde de domaine. Vérifié par
    # mutation : en supprimant la garde de domaine, l'essai passait quand même.
    # On corrige des DEUX côtés : le profil ne faute désormais que sur 1,4, et
    # on EXIGE la phrase de la garde visée. Attraper `ValueError` sans lire son
    # texte, c'est accepter d'être sauvé par n'importe quelle autre garde.
    trop = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=0.0,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c in ((1, "repos", 0.0), (13, "degager", 1.4),
                         (25, "contacter", 1.0)))
    PROFILS["_essai_trop"] = trop
    try:
        scenario("_essai_trop", reperes, arrivee, os_arrivee)
        fautes.append("une part de 1,4 aurait dû lever : elle dépasse la pose "
                      "d'arrivée au milieu du geste")
    except ValueError as _e:
        if "la part « fermeture »" not in str(_e):
            fautes.append(f"la part hors domaine a levé pour une autre raison "
                          f"que la sienne : {_e}")
    finally:
        del PROFILS["_essai_trop"]

    # Le domaine des DÉTOURS est une garde distincte, et elle n'était éprouvée
    # par rien : le coefficient dit QUELLE FRACTION du détour est engagée, le
    # signe et l'ampleur vivent dans `DETOURS`. Un coefficient de 1,4 sortirait
    # le pouce de 31° là où l'appelant en a mesuré 22.
    trop_detour = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=d,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c, d in ((1, "repos", 0.0, 0.0),
                            (13, "degager", 0.5, 1.4),
                            (25, "contacter", 1.0, 0.0)))
    PROFILS["_essai_trop_detour"] = trop_detour
    try:
        scenario("_essai_trop_detour", reperes, arrivee, os_arrivee)
        fautes.append("un coefficient de détour de 1,4 aurait dû lever : c'est "
                      "DETOURS qui porte les degrés, pas le tableau")
    except ValueError as _e:
        if "le détour « pouce_dehors »" not in str(_e):
            fautes.append(f"le détour hors domaine a levé pour une autre "
                          f"raison que la sienne : {_e}")
    finally:
        del PROFILS["_essai_trop_detour"]

    # ═══ L'ORDRE DU §11 EST LA RAISON D'ÊTRE DE CE FICHIER ═══
    # « Une doctrine écrite dans un commentaire ne protège de rien, une
    # doctrine qui lève protège de tout ce qu'elle nomme », dit l'en-tête. Elle
    # ne protégeait de rien : ni l'ordre des phases ni le départ au repos
    # n'étaient éprouvés. On contacte avant d'avoir contourné — la faute même
    # que le module existe pour interdire.
    desordre = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=0.0,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c in ((1, "repos", 0.0), (13, "contacter", 0.5),
                         (25, "contourner", 1.0)))
    PROFILS["_essai_desordre"] = desordre
    try:
        scenario("_essai_desordre", reperes, arrivee, os_arrivee)
        fautes.append("contacter AVANT contourner aurait dû lever : c'est "
                      "l'ordre du §11 qui donne son sens à ce module")
    except ValueError as _e:
        if "ne respectent pas l'ordre" not in str(_e):
            fautes.append(f"le désordre des phases a levé pour une autre "
                          f"raison que la sienne : {_e}")
    finally:
        del PROFILS["_essai_desordre"]

    # Et une transition Neutral→… qui ne commencerait pas par « repos ».
    sans_repos = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=0.0,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c in ((1, "degager", 0.0), (13, "creuser", 0.5),
                         (25, "contacter", 1.0)))
    PROFILS["_essai_sans_repos"] = sans_repos
    try:
        scenario("_essai_sans_repos", reperes, arrivee, os_arrivee)
        fautes.append("un profil qui ne commence pas par « repos » aurait dû "
                      "lever : l'action porterait un nom qui ment")
    except ValueError as _e:
        if "part du repos" not in str(_e):
            fautes.append(f"l'absence de repos a levé pour une autre raison "
                          f"que la sienne : {_e}")
    finally:
        del PROFILS["_essai_sans_repos"]

    # ═══ LA DERNIÈRE LIGNE DU PROFIL DOIT LIVRER LA POSE VALIDÉE ═══
    # Le départ était contrôlé (« l'image 1 n'est pas le repos »), l'arrivée ne
    # l'était pas. Un profil dont la dernière ligne porte 0,98 livrait une pose
    # qui n'est PAS celle que l'optimiseur a retenue, sans un mot — et le jour
    # où le rig portera `PSD_PinkyThumb`, tout profil dont la dernière ligne
    # porte `correctif=0.00` l'aurait livré à zéro dans une pose validée à 1,0.
    # C'est la « signature Iris » : un champ rempli que rien ne relit à
    # l'arrivée. On éprouve la garde plutôt que de la croire.
    # La garde a DEUX branches — les propriétés et les voies d'os — et une
    # seule contre-épreuve les couvrait toutes les deux à la fois : en tuant la
    # branche des propriétés, l'essai échouait quand même, par la branche des
    # os. Un mutant survivant à moitié est un mutant qui survivra en entier le
    # jour où l'autre branche bougera. Une contre-épreuve par branche, donc.
    #
    # Branche « propriétés » : dernière ligne à 0,98, et AUCUNE correction FK
    # d'arrivée — les seules voies d'os présentes sont alors des détours, qui
    # reviennent bien à zéro. Seule la branche des propriétés peut lever.
    ampute = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=d,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c, d in ((1, "repos", 0.00, 0.0),
                            (13, "degager", 0.50, 1.0),
                            (25, "contacter", 0.98, 0.0)))
    PROFILS["_essai_ampute"] = ampute
    try:
        scenario("_essai_ampute", reperes, arrivee, {})
        fautes.append("une dernière ligne à 0,98 aurait dû lever : l'action "
                      "finirait sur une pose que l'optimiseur n'a pas validée")
    except ValueError as _e:
        if "au lieu de la valeur validée" not in str(_e):
            fautes.append(f"l'arrivée amputée a levé pour une autre raison que "
                          f"la sienne : {_e}")
    finally:
        del PROFILS["_essai_ampute"]

    # Branche « voies d'os » : toutes les parts à 1,00 — les propriétés
    # arrivent donc EXACTEMENT sur la pose validée — mais un détour resté à
    # 0,30 sur la dernière ligne. Un détour qui ne revient pas à zéro n'est
    # plus un détour : c'est une déformation permanente de la pose validée,
    # invisible sur toutes les propriétés. Seule la branche des os peut lever.
    reste = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=c, creux=c, ecartement=c,
                      detente=c, correctif=0.0, pouce_dehors=d,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c, d in ((1, "repos", 0.00, 0.0),
                            (13, "degager", 0.50, 1.0),
                            (25, "contacter", 1.00, 0.30)))
    PROFILS["_essai_detour_reste"] = reste
    try:
        scenario("_essai_detour_reste", reperes, arrivee, os_arrivee)
        fautes.append("un détour resté à 0,30 sur la dernière ligne aurait dû "
                      "lever : il déforme la pose validée sans toucher une "
                      "seule propriété")
    except ValueError as _e:
        if "ne revient pas à zéro" not in str(_e):
            fautes.append(f"le détour résiduel a levé pour une autre raison "
                          f"que la sienne : {_e}")
    finally:
        del PROFILS["_essai_detour_reste"]

    # ═══ L'IMAGE 1 EST LE REPOS — LA PROMESSE DU NOM `Neutral_to_…` ═══
    # Cette garde-là n'était éprouvée par RIEN : on pouvait la supprimer, ou
    # n'en supprimer qu'une moitié, sans que l'auto-contrôle bronche (vérifié
    # par mutation). C'est pourtant elle qui tient tout le reste : si l'image 1
    # n'est pas le repos, l'action porte un nom qui ment, et le vérificateur
    # mesure un geste qui ne part pas d'où il croit. `_verifier_profil` exige
    # la PHASE « repos » sur la première ligne, jamais que ses coefficients
    # soient nuls — les deux essais ci-dessous passent donc bien par la garde
    # de `scenario()`, et par elle seule.
    #
    # Moitié « propriétés » : une part non nulle sur la ligne de repos.
    faux_repos = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=0.0, creux=0.0, ecartement=0.0,
                      detente=0.0, correctif=0.0, pouce_dehors=d,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c, d in ((1, "repos", 0.10, 0.0),
                            (13, "degager", 0.50, 1.0),
                            (25, "contacter", 1.00, 0.0)))
    PROFILS["_essai_faux_repos"] = faux_repos
    try:
        scenario("_essai_faux_repos", reperes, arrivee, {})
        fautes.append("une part de 0,10 sur la ligne de repos aurait dû "
                      "lever : l'image 1 ne serait plus le repos")
    except ValueError as _e:
        if "l'image 1 n'est pas le repos" not in str(_e):
            fautes.append(f"le faux repos a levé pour une autre raison que la "
                          f"sienne : {_e}")
    finally:
        del PROFILS["_essai_faux_repos"]

    # Moitié « voies d'os » : toutes les parts nulles sur la ligne de repos —
    # les propriétés y valent donc bien zéro — mais un DÉTOUR déjà engagé.
    # Le pouce serait écarté dès l'image 1 : une main qui ne part pas du neutre.
    faux_repos_os = tuple(
        _etape_profil(f, ph, fermeture=c, pouce=0.0, creux=0.0, ecartement=0.0,
                      detente=0.0, correctif=0.0, pouce_dehors=d,
                      pouce_contourne=0.0, index_s_ecarte=0.0,
                      auriculaire_remonte=0.0)
        for f, ph, c, d in ((1, "repos", 0.00, 0.25),
                            (13, "degager", 0.50, 1.00),
                            (25, "contacter", 1.00, 0.00)))
    PROFILS["_essai_faux_repos_os"] = faux_repos_os
    try:
        scenario("_essai_faux_repos_os", reperes, arrivee, {})
        fautes.append("un détour déjà engagé à l'image 1 aurait dû lever : "
                      "les propriétés sont à zéro, mais le pouce est écarté")
    except ValueError as _e:
        if "l'image 1 n'est pas le repos" not in str(_e):
            fautes.append(f"le faux repos d'os a levé pour une autre raison "
                          f"que la sienne : {_e}")
    finally:
        del PROFILS["_essai_faux_repos_os"]

    # ═══ `completer_etapes` N'ÉTAIT EXERCÉE PAR RIEN ═══
    # Le préambule de cet auto-contrôle dit : « tout ce qui peut échouer sans
    # Blender doit échouer ici ». `completer_etapes` est entièrement calculable
    # hors de Blender et n'était appelée nulle part — ni sa règle d'or (un
    # canal absent d'un BORD lève, parce qu'on n'a rien pour l'interpoler et
    # que le compléter par 0,0 fabriquerait une mesure), ni son arithmétique.
    _rempli = completer_etapes([(1, {"a": 0.0, "b": 0.0}, {}),
                                (13, {"a": 0.5}, {}),
                                (25, {"a": 1.0, "b": 1.0}, {})])
    # b vaut 0 à l'image 1 et 1 à l'image 25 : à l'image 13, (13−1)/24 = 0,5.
    if abs(_rempli[1][1]["b"] - 0.5) > 1e-12:
        fautes.append(f"completer_etapes interpole b à {_rempli[1][1]['b']} au "
                      "lieu de 0,5")
    try:
        completer_etapes([(1, {"a": 0.0}, {}),
                          (13, {"a": 0.5, "b": 0.2}, {}),
                          (25, {"a": 1.0}, {})])
        fautes.append("un canal absent des DEUX bords aurait dû lever : le "
                      "compléter par 0,0 fabriquerait une mesure")
    except KeyError:
        pass

    # ═══ DEUX CLÉS D'ARRIVÉE QUI RETOMBENT SUR LA MÊME VOIE ═══
    # `int(cle[1])` ramène 0 et 0,4 sur le même index d'euler : deux entrées
    # distinctes du dictionnaire de l'appelant, une seule voie à l'arrivée. La
    # seconde écrasait la première en silence — la règle 7 (« jamais deux
    # écritures sur le même index ») déplacée du rig vers le tableau.
    try:
        scenario("Hand_Fist", reperes, arrivee,
                 {("CTRL_thumb_meta.L", 0): -7.5,
                  ("CTRL_thumb_meta.L", 0.4): -3.0})
        fautes.append("deux clés d'os_arrivee ramenées au même index d'euler "
                      "auraient dû lever : la seconde écrase la première")
    except ValueError as _e:
        if "écraserait la première" not in str(_e):
            fautes.append(f"la collision de voies d'os a levé pour une autre "
                          f"raison que la sienne : {_e}")

    if fautes:
        print("\n".join("ÉCHEC · " + f for f in fautes))
        return 1
    print("Auto-contrôle du tableau des scénarios : tout passe.")
    return 0


if __name__ == "__main__":
    sys.exit(_auto_controle())
