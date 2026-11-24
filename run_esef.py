"""Lance le connecteur ESEF sur les sociétés du CAC 40 cotées en France (rapports déposés à l'AMF).

Usage (depuis la racine du dépôt, environnement finsight actif) :
    python run_esef.py

Pour chaque société : téléchargement des rapports annuels, lecture iXBRL, couche silver.
Les sociétés dont les rapports ne sont pas déposés à l'AMF (Airbus, STMicroelectronics, Stellantis,
Euronext, ArcelorMittal, Eurofins) sont exclues : elles déposent aux Pays-Bas ou au Luxembourg.
"""

import logging
from pathlib import Path

from ingestion.esef_connector import EsefError, extraire_societe
from transform.silver_esef import construire_silver_esef, sauvegarder_silver_esef

logger = logging.getLogger("run_esef")

# Composition du CAC 40 selon l'article de référence du 27/10/2026 (ISIN non vérifiés sur Euronext).
CAC40 = [
    ("Schneider Electric", "FR0000121972"), ("TotalEnergies", "FR0000120271"),
    ("Air Liquide", "FR0000120073"), ("Safran", "FR0000073272"), ("BNP Paribas", "FR0000131104"),
    ("LVMH", "FR0000121014"), ("L'Oréal", "FR0000120321"), ("Sanofi", "FR0000120578"),
    ("AXA", "FR0000120628"), ("Vinci", "FR0000125486"), ("EssilorLuxottica", "FR0000121667"),
    ("Société Générale", "FR0000130809"), ("Engie", "FR0010208488"), ("Hermès International", "FR0000052292"),
    ("Danone", "FR0000120644"), ("Legrand", "FR0010307819"), ("Saint-Gobain", "FR0000125007"),
    ("Orange", "FR0000133308"), ("Michelin", "FR001400AJ45"), ("Publicis Groupe", "FR0000130577"),
    ("Thales", "FR0000121329"), ("Veolia Environnement", "FR0000124141"), ("Kering", "FR0000121485"),
    ("Capgemini", "FR0000125338"), ("Crédit Agricole", "FR0000045072"), ("Dassault Systèmes", "FR0014003TT8"),
    ("Pernod Ricard", "FR0000120693"), ("Carrefour", "FR0000120172"),
    ("Unibail-Rodamco-Westfield", "FR0013326246"), ("Bureau Veritas", "FR0006174348"),
    ("Bouygues", "FR0000120503"), ("Accor", "FR0000120404"), ("Eiffage", "FR0000130452"),
    ("Renault", "FR0000131906"),
]
DOSSIER_BRONZE = Path("data/bronze/esef")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    DOSSIER_BRONZE.mkdir(parents=True, exist_ok=True)
    echecs = []
    for nom, isin in CAC40:
        try:
            faits = extraire_societe(isin)
            faits.to_csv(DOSSIER_BRONZE / f"{isin}.csv", index=False)
            tableau = construire_silver_esef(faits, isin, nom)
            sauvegarder_silver_esef(tableau, isin)
            logger.info("%s : %d exercices", nom, len(tableau))
        except EsefError as erreur:
            echecs.append((nom, str(erreur)))
            logger.warning("%s : échec (%s)", nom, erreur)
    print(f"Terminé : {len(CAC40) - len(echecs)} réussite(s), {len(echecs)} échec(s).")
    for nom, detail in echecs:
        print(f"  - {nom} : {detail}")


if __name__ == "__main__":
    main()
