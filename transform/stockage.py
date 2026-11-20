"""Stockage SQLite : charge les couches silver, gold et qualité dans une base locale.

La base data/finsight.db est un simple fichier, sans serveur à installer.
Chaque exécution remplace les tables : la base reflète toujours les derniers CSV.

Tables :
- silver_exercices : tableau annuel propre, une ligne par entreprise et par exercice ;
- gold_indicateurs : les indicateurs calculés ;
- qualite_anomalies : les anomalies détectées par les contrôles.

Utilisation (depuis la racine du dépôt, après les couches silver, gold et qualité) :
    python -m transform.stockage
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SILVER_DIR = Path("data/silver")
GOLD_CSV = Path("data/gold/indicateurs.csv")
QUALITE_CSV = Path("data/gold/qualite.csv")
BASE = Path("data/finsight.db")


def charger_silver(dossier=SILVER_DIR):
    """Concatène tous les CSV silver (une entreprise par fichier)."""
    fichiers = sorted(Path(dossier).glob("CIK*.csv"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun CSV silver dans {dossier}. Lancer transform.silver.")
    return pd.concat((pd.read_csv(f) for f in fichiers), ignore_index=True)


def ecrire_tables(tables, base=BASE):
    """Écrit les DataFrame dans la base SQLite, en remplaçant les tables existantes.

    tables : dictionnaire {nom_de_table: DataFrame}. Renvoie le nombre de lignes par table.
    """
    base = Path(base)
    base.parent.mkdir(parents=True, exist_ok=True)
    comptes = {}
    with sqlite3.connect(base) as connexion:
        for nom, df in tables.items():
            df.to_sql(nom, connexion, if_exists="replace", index=False)
            comptes[nom] = len(df)
    return comptes


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not GOLD_CSV.exists() or not QUALITE_CSV.exists():
        logger.error("Il manque des fichiers gold ou qualité. Lancer transform.gold puis transform.qualite.")
        return 1
    tables = {
        "silver_exercices": charger_silver(),
        "gold_indicateurs": pd.read_csv(GOLD_CSV),
        "qualite_anomalies": pd.read_csv(QUALITE_CSV),
    }
    comptes = ecrire_tables(tables)
    for nom, n in comptes.items():
        logger.info("%s : %d lignes", nom, n)
    logger.info("Base écrite : %s", BASE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
