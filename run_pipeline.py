"""Pipeline complet : ingestion (bronze) puis couche silver, en une seule commande.

Utilisation (depuis la racine du dépôt) :
    python run_pipeline.py MSFT
    python run_pipeline.py MSFT AAPL GOOGL
"""

import logging
import sys
from pathlib import Path

from explore import charger_bronze, dernier_fichier_par_cik
from ingestion.sec_connector import BRONZE_DIR, SecConnectorError
from ingestion.sec_connector import main as ingerer
from transform.silver import construire_silver, sauvegarder_silver

SILVER_DIR = Path("data/silver")

logger = logging.getLogger(__name__)


def construire_silver_depuis_bronze(bronze_dir=BRONZE_DIR, silver_dir=SILVER_DIR):
    """Écrit un CSV silver pour chaque entreprise bronze (la version la plus récente).

    Renvoie la liste des fichiers CSV écrits.
    """
    sorties = []
    for chemin in dernier_fichier_par_cik(Path(bronze_dir).glob("CIK*.json")):
        data = charger_bronze(chemin)
        df = construire_silver(data)
        sortie = sauvegarder_silver(df, data["cik"], silver_dir)
        logger.info("%s : %d exercices -> %s", data["entityName"], len(df), sortie)
        sorties.append(sortie)
    return sorties


def main(arguments):
    """Ingère les entreprises demandées, puis construit la couche silver. Renvoie les échecs."""
    echecs = ingerer(arguments)
    construire_silver_depuis_bronze()
    return echecs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print("Usage : python run_pipeline.py <TICKER ou CIK> [<TICKER ou CIK> ...]")
        sys.exit(1)
    try:
        echecs = main(sys.argv[1:])
    except SecConnectorError as e:
        logger.error(e)
        sys.exit(1)
    if echecs:
        logger.error("En échec : %s", ", ".join(echecs))
        sys.exit(1)
