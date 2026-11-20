"""Contrôles de qualité sur la couche gold : ce qui manque ou semble anormal.

Chaque contrôle produit une ligne d'anomalie (entreprise, année, contrôle, détail).
Un contrôle ne corrige rien : il signale, pour qu'on vérifie la source avant de conclure.

Contrôles :
- exercice_manquant : une année absente dans la suite des exercices d'une entreprise ;
- donnee_manquante : chiffre d'affaires, résultat net, actif ou passif absent ;
- marge_aberrante : marge nette au-delà de -100 % ou +100 % ;
- capitaux_negatifs : passif supérieur à l'actif (capitaux propres négatifs) ;
- croissance_aberrante : croissance du CA au-delà de +/-100 % d'un exercice à l'autre ;
- current_ratio_extreme : current ratio au-dessus de 10 ou en dessous de 0,1.

Utilisation (depuis la racine du dépôt, après python -m transform.gold) :
    python -m transform.qualite
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

GOLD_CSV = Path("data/gold/indicateurs.csv")
QUALITE_CSV = Path("data/gold/qualite.csv")

CHAMPS_OBLIGATOIRES = ["chiffre_affaires", "resultat_net", "total_actif", "total_passif"]


def anomalie(ligne, controle, detail):
    return {
        "entreprise": ligne["entreprise"],
        "annee": ligne["annee"],
        "controle": controle,
        "detail": detail,
    }


def controler_entreprise(df):
    """Renvoie la liste des anomalies d'une entreprise (lignes triées par année)."""
    df = df.sort_values("annee").reset_index(drop=True)
    anomalies = []

    annees = list(df["annee"])
    for precedente, suivante in zip(annees, annees[1:]):
        for manquante in range(precedente + 1, suivante):
            trou = {"entreprise": df["entreprise"].iloc[0], "annee": manquante}
            anomalies.append(anomalie(trou, "exercice_manquant", f"année {manquante} absente"))

    for _, ligne in df.iterrows():
        manquants = [c for c in CHAMPS_OBLIGATOIRES if pd.isna(ligne[c])]
        if manquants:
            anomalies.append(anomalie(ligne, "donnee_manquante", ", ".join(manquants)))

        marge = ligne["marge_nette"]
        if pd.notna(marge) and abs(marge) > 1:
            anomalies.append(anomalie(ligne, "marge_aberrante", f"marge nette {marge:.0%}"))

        if pd.notna(ligne["total_actif"]) and pd.notna(ligne["total_passif"]):
            if ligne["total_passif"] > ligne["total_actif"]:
                anomalies.append(anomalie(ligne, "capitaux_negatifs", "passif supérieur à l'actif"))

        croissance = ligne["croissance_ca"]
        if pd.notna(croissance) and abs(croissance) > 1:
            anomalies.append(anomalie(ligne, "croissance_aberrante", f"CA {croissance:+.0%}"))

        ratio = ligne["current_ratio"]
        if pd.notna(ratio) and (ratio > 10 or ratio < 0.1):
            anomalies.append(anomalie(ligne, "current_ratio_extreme", f"current ratio {ratio:.2f}"))
    return anomalies


def controler(gold):
    """Contrôle toutes les entreprises du tableau gold. Renvoie un DataFrame d'anomalies."""
    anomalies = []
    for _, df in gold.groupby("entreprise"):
        anomalies += controler_entreprise(df)
    return pd.DataFrame(anomalies, columns=["entreprise", "annee", "controle", "detail"])


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not GOLD_CSV.exists():
        logger.error("Pas de %s. Lancer d'abord python -m transform.gold.", GOLD_CSV)
        return 1
    anomalies = controler(pd.read_csv(GOLD_CSV))
    QUALITE_CSV.parent.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(QUALITE_CSV, index=False)
    logger.info("%d anomalie(s) -> %s", len(anomalies), QUALITE_CSV)
    if not anomalies.empty:
        logger.info("Par contrôle :\n%s", anomalies["controle"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
