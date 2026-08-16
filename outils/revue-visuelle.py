#!/usr/bin/env python3
"""
LA REVUE VISUELLE — mesurer ce qu'une image montre, avant de la noter (§13).

Sacha a tranché : c'est moi qui note et j'argumente. Mais une note posée à l'œil
sur soixante images est une impression, pas une revue — et mon œil a déjà été
pris en défaut sur ce projet.

Cet outil ne remplace pas le jugement : il fournit les grandeurs SUR
LESQUELLES juger, image par image, pour que la note se rattache à quelque chose
qu'un tiers peut recompter. Ce qu'il mesure :

  · l'écrêtage et le bouchage — une image brûlée ou noire ne se juge pas ;
  · l'amplitude de luminance — c'est ELLE qui a condamné
    `gros-plan-Hand_Pinky_Thumb-pouce.png` au chat 1, à 14,9/255 contre 41,8
    ailleurs, et l'écrêtage ne l'aurait jamais vue : une image plate n'est ni
    brûlée ni bouchée, elle est illisible ;
  · la part de sujet dans le cadre — un cadrage qui perd la main dans un coin
    rend une image vraie et inutilisable ;
  · le contraste LOCAL — une image peut avoir une belle amplitude globale et
    n'avoir aucun relief là où il faut juger. C'est la différence entre « on
    voit la main » et « on voit les jointures ».

    python3 outils/revue-visuelle.py DOSSIER [sortie.json]
"""
import json
import os
import sys

try:
    import numpy as np
    from PIL import Image
except Exception as _e:                                       # noqa: BLE001
    print(f"revue-visuelle exige numpy et PIL : {_e}")
    raise SystemExit(2)

SEUIL_ECRETAGE_PCT = 2.0
SEUIL_AMPLITUDE = 0.10
SEUIL_SUJET_PCT = 4.0
SEUIL_RELIEF_LOCAL = 0.020


def _luminance(chemin):
    im = Image.open(chemin)
    a = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
    rvb, alpha = a[..., :3], a[..., 3]
    lum = 0.2126 * rvb[..., 0] + 0.7152 * rvb[..., 1] + 0.0722 * rvb[..., 2]
    return lum, alpha


def _relief_local(lum, masque, pas=16):
    """L'écart-type moyen des tuiles de sujet.

    ═══ UNE AMPLITUDE GLOBALE NE DIT RIEN DU RELIEF ═══
    Une image mi-noire mi-blanche a une amplitude parfaite et aucun modelé. On
    découpe donc en tuiles et on regarde si CHAQUE morceau porte du détail : ce
    qu'on juge sur un rig, ce sont les jointures et les plis, pas la
    silhouette.
    """
    h, w = lum.shape
    valeurs = []
    for y in range(0, h - pas, pas):
        for x in range(0, w - pas, pas):
            tuile_m = masque[y:y + pas, x:x + pas]
            if tuile_m.mean() < 0.6:          # tuile majoritairement hors sujet
                continue
            valeurs.append(float(lum[y:y + pas, x:x + pas].std()))
    if not valeurs:
        return None
    return float(np.mean(valeurs))


def mesurer(chemin):
    lum, alpha = _luminance(chemin)
    masque = alpha > 0.5
    n = int(masque.sum())
    if n == 0:
        # ═══ UNE IMAGE SANS SUJET N'EST PAS UNE IMAGE À ZÉRO ═══
        # Rendre des zéros ici les ferait entrer dans les moyennes et tirer la
        # note vers le bas comme si l'image était mauvaise. Elle est ABSENTE,
        # ce qui est un autre problème et se corrige ailleurs.
        return {"fichier": os.path.basename(chemin), "sujet_pct": 0.0,
                "verdict": "AUCUN SUJET — le masque alpha est vide"}
    l = lum[masque]
    return {
        "fichier": os.path.basename(chemin),
        "sujet_pct": round(100.0 * n / lum.size, 2),
        "ecretage_pct": round(100.0 * float((l >= 0.99).sum()) / n, 4),
        "bouchage_pct": round(100.0 * float((l <= 0.02).sum()) / n, 4),
        "luminance_moyenne": round(float(l.mean()), 4),
        "luminance_max": round(float(l.max()), 4),
        "amplitude": round(float(l.max() - l.mean()), 4),
        "relief_local": (round(_relief_local(lum, masque), 4)
                         if _relief_local(lum, masque) is not None else None),
    }


def juger(m):
    """Les défauts d'UNE image, nommés. Pas une note — des faits."""
    if m.get("verdict"):
        return [m["verdict"]]
    d = []
    if m["ecretage_pct"] > SEUIL_ECRETAGE_PCT:
        d.append(f"écrêtée à {m['ecretage_pct']:.2f} %")
    if m["sujet_pct"] < SEUIL_SUJET_PCT:
        d.append(f"sujet trop petit dans le cadre ({m['sujet_pct']:.1f} %)")
    if m["amplitude"] < SEUIL_AMPLITUDE:
        d.append(f"amplitude de luminance {m['amplitude']:.3f} — image plate")
    if m["relief_local"] is not None and m["relief_local"] < SEUIL_RELIEF_LOCAL:
        d.append(f"relief local {m['relief_local']:.3f} — aucun modelé "
                 f"là où il faut juger")
    return d


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    dossier = argv[0]
    sortie = argv[1] if len(argv) > 1 else None
    if not os.path.isdir(dossier):
        print(f"dossier introuvable : {dossier}")
        return 2
    images = []
    for racine, _d, fichiers in os.walk(dossier):
        for f in sorted(fichiers):
            if f.lower().endswith(".png"):
                images.append(os.path.join(racine, f))
    if not images:
        print(f"aucune image dans {dossier} — une revue sans image ne se rend "
              f"pas, elle se signale")
        return 2

    mesures, fautives = [], {}
    for chemin in images:
        m = mesurer(chemin)
        mesures.append(m)
        d = juger(m)
        if d:
            fautives[os.path.relpath(chemin, dossier)] = d

    print(f"{len(images)} image(s) mesurée(s) dans {dossier}\n")
    print(f"{'image':44s} {'sujet%':>7s} {'écrêt%':>7s} {'ampl':>6s} {'relief':>7s}")
    for m in mesures:
        if m.get("verdict"):
            print(f"{m['fichier'][:44]:44s} {'—':>7s} {'—':>7s} {'—':>6s} {'—':>7s}")
            continue
        print(f"{m['fichier'][:44]:44s} {m['sujet_pct']:7.2f} "
              f"{m['ecretage_pct']:7.3f} {m['amplitude']:6.3f} "
              f"{m['relief_local'] if m['relief_local'] is not None else 0:7.3f}")

    print(f"\nImages portant au moins un défaut mesuré : {len(fautives)} "
          f"sur {len(images)}")
    for nom, defauts in sorted(fautives.items()):
        print(f"  ✗ {nom}")
        for x in defauts:
            print(f"      · {x}")

    resultat = {"dossier": dossier, "images": len(images),
                "mesures": mesures, "fautives": fautives,
                "seuils": {"ecretage_pct": SEUIL_ECRETAGE_PCT,
                           "amplitude": SEUIL_AMPLITUDE,
                           "sujet_pct": SEUIL_SUJET_PCT,
                           "relief_local": SEUIL_RELIEF_LOCAL}}
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=1)
        print(f"\nécrit : {sortie}")

    # ═══ CET OUTIL NE DONNE PAS DE NOTE ═══
    # Il rend les faits sur lesquels une note s'appuie. Une note qu'un
    # programme calcule serait une moyenne pondérée déguisée en jugement, et
    # personne ne pourrait la contester utilement.
    print("\nCet outil ne note pas : il mesure ce qu'une image montre. "
          "La note s'écrit à la main, en s'appuyant sur ces chiffres.")
    return 2 if fautives else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
