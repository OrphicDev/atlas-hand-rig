"""
LA JACOBIENNE NUMÉRIQUE — sculpter sans sculpter (§7.7).

═══ LE PROBLÈME QUE CE MODULE RÉSOUT ═══

On veut qu'un sommet du thénar recule de 0,4 mm DANS LA POSE. Mais une shape
key ne s'écrit pas dans la pose : elle s'écrit sur le Basis, au repos, et
l'armature la transporte ensuite. Or l'armature ne transporte pas un vecteur à
l'identique — elle le fait tourner, l'étire, et le mélange selon les poids du
sommet. Un delta de 0,4 mm écrit au repos peut devenir 0,9 mm dans une
direction voisine une fois posé.

Écrire naïvement le déplacement voulu dans la key produit donc autre chose que
ce qu'on voulait, et l'écart est invisible : la forme change, elle ne plante
pas. C'est la faute que ce dépôt commet à chaque étage — un résultat crédible
et faux.

On MESURE donc la transformation. Pour chaque sommet, on bouge sa clé de
epsilon sur X, on relit sa position posée, et la différence donne une colonne
de la jacobienne. Trois colonnes, une matrice 3×3, qu'on inverse pour convertir
« ce que je veux dans la pose » en « ce que je dois écrire au repos ».

═══ CE QUI EST DÉLIBÉRÉMENT BRIDÉ ═══

  · 50 % du delta calculé par ronde. La jacobienne est locale : elle vaut pour
    un petit déplacement, pas pour le déplacement entier. Appliquer 100 %
    reviendrait à extrapoler une dérivée loin de son point ;
  · 0,75 mm par ronde et 3 mm au total. Au-delà, on ne corrige plus un défaut
    de déformation, on resculpte la main — et le cahier l'interdit : « si le
    correctif doit déplacer la forme de plus de 3 mm, élargis le masque ou
    reprends les poids » ;
  · le Corrective Smooth doit être DÉSACTIVÉ pendant la mesure. Un lissage
    dépendant des voisins rend la réponse non locale, et la jacobienne
    par-sommet cesse d'être une jacobienne.
"""
import math
import sys

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

EPSILON_M = 0.0001          # 0,1 mm — assez grand pour sortir du bruit,
                            # assez petit pour rester dans le linéaire
FRACTION_PAR_RONDE = 0.50
PLAFOND_RONDE_M = 0.00075
PLAFOND_TOTAL_M = 0.0030
RONDES_MAX = 8


def _exiger(condition, message):
    if not condition:
        raise RuntimeError(message)


def _det3(m):
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def inverser3(m, seuil=1e-12):
    """L'inverse d'une 3×3, ou None si elle est singulière.

    ═══ UNE MATRICE SINGULIÈRE N'EST PAS UNE ERREUR, C'EST UN FAIT ═══
    Un sommet dont les trois colonnes sont colinéaires est un sommet que
    l'armature écrase sur un plan ou une droite — typiquement au cœur d'un pli.
    On ne peut PAS y convertir un déplacement voulu, et forcer une
    pseudo-inverse y produirait un delta énorme dans la direction la moins
    contrainte. On rend None, et l'appelant saute ce sommet en le comptant.
    """
    det = _det3(m)
    if abs(det) < seuil:
        return None
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
            [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
            [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]


def appliquer3(m, v):
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


def borner(vecteur, plafond):
    n = math.sqrt(sum(x * x for x in vecteur))
    if n <= plafond or n < 1e-15:
        return vecteur
    k = plafond / n
    return tuple(x * k for x in vecteur)


def jacobiennes_par_sommet(indices, poser_key, lire_positions,
                           epsilon=EPSILON_M):
    """{indice: matrice 3×3} — la réponse MESURÉE de chaque sommet.

    `poser_key(deltas)` écrit `{indice: (dx, dy, dz)}` dans la clé temporaire
    puis rafraîchit ; `lire_positions()` rend `{indice: (x, y, z)}` posées.

    Les trois colonnes sont mesurées EN UNE FOIS chacune, tous sommets
    ensemble : trois évaluations du maillage au lieu de trois par sommet.

    ═══ LA CONTRE-ÉPREUVE EST OBLIGATOIRE ═══
    Si aucune colonne ne bouge, on ne mesure pas une jacobienne — on mesure une
    clé qui n'atteint pas le maillage, et toutes les matrices seraient nulles
    donc singulières, donc « aucun sommet corrigible » : un verdict parfaitement
    cohérent et parfaitement faux.
    """
    _exiger(indices, "aucun sommet à éprouver")
    poser_key({})
    base = lire_positions()
    colonnes = []
    for axe in range(3):
        d = [0.0, 0.0, 0.0]
        d[axe] = epsilon
        poser_key({i: tuple(d) for i in indices})
        pose = lire_positions()
        colonnes.append({i: tuple((pose[i][k] - base[i][k]) / epsilon
                                  for k in range(3)) for i in indices})
    poser_key({})

    bouge = max(
        max(abs(x) for x in colonnes[a][i]) for a in range(3) for i in indices)
    _exiger(bouge > 1e-3,
            "aucune colonne de la jacobienne ne bouge : la clé temporaire "
            "n'atteint pas le maillage évalué, et toutes les matrices "
            "sortiraient singulières — un « aucun sommet corrigible » "
            "parfaitement cohérent et parfaitement faux")

    return {i: [[colonnes[0][i][r], colonnes[1][i][r], colonnes[2][i][r]]
                for r in range(3)] for i in indices}


def deltas_pour_deplacement(voulus, jacs, plafond_ronde=PLAFOND_RONDE_M,
                            fraction=FRACTION_PAR_RONDE):
    """`{indice: delta_de_clé}` pour obtenir `voulus` DANS LA POSE.

    Rend aussi la liste des sommets écartés parce que leur jacobienne est
    singulière : les taire donnerait un correctif qui ne corrige pas une partie
    de la zone, sans que rien ne le dise.
    """
    out, singuliers = {}, []
    for i, v in voulus.items():
        j = jacs.get(i)
        if j is None:
            singuliers.append(i)
            continue
        inv = inverser3(j)
        if inv is None:
            singuliers.append(i)
            continue
        d = appliquer3(inv, v)
        d = tuple(x * fraction for x in d)
        out[i] = borner(d, plafond_ronde)
    return out, singuliers


def diffuser(deltas, adjacence, anneaux=3):
    """Étale les deltas sur quelques anneaux d'arêtes, avec un fondu.

    Un delta appliqué à un sommet isolé fait une pointe, pas un glissement de
    chair. On le diffuse par la SURFACE — jamais par une sphère euclidienne,
    qui attraperait la peau d'en face d'un doigt replié.
    """
    _exiger(anneaux >= 1, "diffuser sur zéro anneau ne diffuse rien")
    courant = {i: (1.0, d) for i, d in deltas.items()}
    total = {i: [d[0], d[1], d[2]] for i, d in deltas.items()}
    vus = set(deltas)
    for tour in range(1, anneaux + 1):
        poids = 1.0 - tour / (anneaux + 1.0)
        suivant = {}
        for i, (_p, d) in courant.items():
            for j in adjacence.get(i, ()):
                if j in vus:
                    continue
                suivant.setdefault(j, [0.0, 0.0, 0.0])
                for k in range(3):
                    suivant[j][k] += d[k] * poids
        for j, d in suivant.items():
            vus.add(j)
            total[j] = d
        courant = {j: (poids, tuple(d)) for j, d in suivant.items()}
        if not courant:
            break
    return {i: tuple(d) for i, d in total.items()}


if __name__ == "__main__":
    fautes = []

    def leve(fn, quoi):
        try:
            fn()
        except Exception:
            return
        fautes.append(f"{quoi} : aurait dû lever")

    # L'inverse d'une identité est une identité.
    _id = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
    assert inverser3(_id) == _id

    # Une matrice singulière rend None, elle ne rend pas une pseudo-inverse.
    assert inverser3([[1, 2, 3], [2, 4, 6], [1, 1, 1]]) is None

    # Le plafond borne la NORME, il ne tronque pas les composantes une à une :
    # tronquer par composante changerait la DIRECTION du déplacement.
    _b = borner((3.0, 4.0, 0.0), 1.0)
    assert abs(math.sqrt(sum(x * x for x in _b)) - 1.0) < 1e-12
    assert abs(_b[0] / _b[1] - 0.75) < 1e-12, "la direction doit être conservée"

    # Un sommet singulier est ÉCARTÉ et COMPTÉ, jamais corrigé au hasard.
    _d, _s = deltas_pour_deplacement(
        {1: (0.001, 0, 0), 2: (0.001, 0, 0)},
        {1: _id, 2: [[1, 2, 3], [2, 4, 6], [1, 1, 1]]})
    assert 2 in _s and 1 in _d, "le singulier doit être écarté et signalé"
    assert abs(_d[1][0] - 0.0005) < 1e-12, "la fraction de 50 % doit s'appliquer"

    # La diffusion atteint les voisins et décroît.
    _adj = {1: {2}, 2: {1, 3}, 3: {2}}
    _dif = diffuser({1: (0.001, 0, 0)}, _adj, anneaux=2)
    assert 2 in _dif and 3 in _dif, "la diffusion doit atteindre les voisins"
    assert abs(_dif[2][0]) > abs(_dif[3][0]), "elle doit DÉCROÎTRE avec la distance"

    # La contre-épreuve de la jacobienne doit tomber quand rien ne bouge.
    leve(lambda: jacobiennes_par_sommet(
        [1], lambda _d: None, lambda: {1: (0.0, 0.0, 0.0)}),
        "une clé qui n'atteint pas le maillage")
    leve(lambda: jacobiennes_par_sommet([], lambda _d: None, lambda: {}),
         "aucun sommet à éprouver")
    leve(lambda: diffuser({1: (0, 0, 0)}, {}, anneaux=0),
         "diffuser sur zéro anneau")

    if fautes:
        print("AUTOTEST JACOBIENNE — FAUTES :")
        for f in fautes:
            print("  ·", f)
        sys.exit(2)
    print("AUTOTEST JACOBIENNE — tout passe, 3 refus exercés.")
