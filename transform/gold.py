"""Couche gold : indicateurs financiers calculés à partir du tableau silver.

Pour chaque entreprise et chaque exercice :
- capitaux propres = total actif - total passif ;
- marge nette = résultat net / chiffre d'affaires ;
- ROE = résultat net / capitaux propres ; ROA = résultat net / total actif ;
- dette sur capitaux propres = total passif / capitaux propres ;
- croissance du CA = CA de l'exercice / CA de l'exercice précédent - 1
  (seulement si l'exercice précédent existe, donc sans trou d'année).

Un indicateur reste vide (NaN) si une donnée de son calcul manque.

Utilisation (depuis la racine du dépôt, après python -m transform.silver) :
    python -m transform.gold
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")


def diviser(numerateur, denominateur):
    """numerateur / denominateur, avec NaN si le dénominateur vaut 0 ou manque."""
    return numerateur / denominateur.where(denominateur != 0)


def calculer_indicateurs(df):
    """Ajoute les indicateurs à un tableau silver d'une entreprise."""
    df = df.sort_values("date_fin").copy()
    df["capitaux_propres"] = df["total_actif"] - df["total_passif"]
    df["marge_nette"] = diviser(df["resultat_net"], df["chiffre_affaires"])
    df["roe"] = diviser(df["resultat_net"], df["capitaux_propres"])
    df["roa"] = diviser(df["resultat_net"], df["total_actif"])
    df["dette_sur_capitaux_propres"] = diviser(df["total_passif"], df["capitaux_propres"])

    ca_precedent = df["chiffre_affaires"].shift(1)
    exercice_consecutif = df["annee"].diff() == 1
    croissance = df["chiffre_affaires"] / ca_precedent.where(ca_precedent != 0) - 1
    df["croissance_ca"] = croissance.where(exercice_consecutif)
    return df


def construire_gold(dossier_silver=SILVER_DIR, dossier_gold=GOLD_DIR):
    """Lit les CSV silver, calcule les indicateurs et écrit data/gold/indicateurs.csv."""
    fichiers = sorted(Path(dossier_silver).glob("CIK*.csv"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun CSV silver dans {dossier_silver}. Lancer transform.silver.")
    tableaux = [calculer_indicateurs(pd.read_csv(f)) for f in fichiers]
    gold = pd.concat(tableaux, ignore_index=True)

    dossier_gold = Path(dossier_gold)
    dossier_gold.mkdir(parents=True, exist_ok=True)
    chemin = dossier_gold / "indicateurs.csv"
    gold.to_csv(chemin, index=False)
    logger.info("%d lignes d'indicateurs -> %s", len(gold), chemin)
    return chemin


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    construire_gold()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
