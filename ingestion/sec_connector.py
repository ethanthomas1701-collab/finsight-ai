"""Connecteur SEC EDGAR : récupère les données financières brutes d'une entreprise.

Couche « bronze » : on sauvegarde la réponse telle quelle, sans transformation,
avec la date d'ingestion. Le nettoyage viendra plus tard (couche « silver »).

Utilisation (depuis la racine du dépôt), avec un ou plusieurs tickers ou CIK :
    python -m ingestion.sec_connector MSFT
    python -m ingestion.sec_connector MSFT AAPL GOOGL
    python -m ingestion.sec_connector 0000789019
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
BRONZE_DIR = Path("data/bronze")
TIMEOUT_SECONDES = 30
PAUSE_SECONDES = 0.2  # la SEC limite à 10 requêtes par seconde

logger = logging.getLogger(__name__)


class SecConnectorError(Exception):
    """Erreur levée quand la récupération des données SEC échoue."""


def get_user_agent():
    """Lit le contact exigé par la SEC dans la variable d'environnement SEC_USER_AGENT."""
    user_agent = os.environ.get("SEC_USER_AGENT")
    if not user_agent:
        raise SecConnectorError(
            "Variable SEC_USER_AGENT absente. Exemple : "
            '$env:SEC_USER_AGENT = "Prénom Nom contact@exemple.com"'
        )
    return user_agent


def normaliser_cik(cik):
    """Met le CIK sur 10 chiffres (ex. 789019 -> 0000789019)."""
    cik = str(cik).strip()
    if not cik.isdigit() or len(cik) > 10:
        raise SecConnectorError(f"CIK invalide : {cik!r} (10 chiffres maximum)")
    return cik.zfill(10)


def get_json(url, message_404):
    """Fait un GET vers la SEC et renvoie le JSON. Toute erreur devient une SecConnectorError."""
    headers = {"User-Agent": get_user_agent()}

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDES)
        response.raise_for_status()
    except requests.Timeout as e:
        raise SecConnectorError(f"La SEC n'a pas répondu en {TIMEOUT_SECONDES} s") from e
    except requests.HTTPError as e:
        code = e.response.status_code
        if code == 404:
            raise SecConnectorError(message_404) from e
        raise SecConnectorError(f"Erreur HTTP {code} pour {url}") from e
    except requests.RequestException as e:
        raise SecConnectorError(f"Échec réseau : {e}") from e

    try:
        return response.json()
    except ValueError as e:
        raise SecConnectorError("La réponse de la SEC n'est pas du JSON valide") from e


def fetch_company_tickers():
    """Télécharge la table ticker -> CIK publiée par la SEC."""
    table = get_json(TICKERS_URL, "Table des tickers introuvable sur le site de la SEC")
    if not isinstance(table, dict) or not table:
        raise SecConnectorError("Table des tickers vide ou mal formée")
    return table


def trouver_cik(ticker, table):
    """Cherche un ticker dans la table de la SEC et renvoie son CIK sur 10 chiffres.

    La table a la forme {"0": {"cik_str": 789019, "ticker": "MSFT", "title": "..."}, ...}.
    Fonction sans réseau : facile à tester.
    """
    ticker = str(ticker).strip().upper()
    for entreprise in table.values():
        if entreprise.get("ticker", "").upper() == ticker:
            return normaliser_cik(entreprise["cik_str"])
    raise SecConnectorError(f"Ticker inconnu : {ticker!r}")


def ticker_vers_cik(ticker):
    """Télécharge la table de la SEC puis renvoie le CIK du ticker."""
    return trouver_cik(ticker, fetch_company_tickers())


def fetch_company_facts(cik):
    """Appelle l'API SEC et renvoie la réponse JSON sous forme de dictionnaire."""
    url = BASE_URL.format(cik=normaliser_cik(cik))
    data = get_json(url, f"Aucune donnée pour le CIK {cik}")

    if "facts" not in data or "entityName" not in data:
        raise SecConnectorError("Réponse inattendue : clés 'facts' ou 'entityName' manquantes")
    return data


def save_raw(data, cik, dossier=BRONZE_DIR):
    """Sauvegarde la réponse brute avec la date d'ingestion. Renvoie le chemin du fichier."""
    maintenant = datetime.now(timezone.utc)
    enveloppe = {
        "ingested_at": maintenant.isoformat(),
        "source": BASE_URL.format(cik=normaliser_cik(cik)),
        "data": data,
    }
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"CIK{normaliser_cik(cik)}_{maintenant:%Y%m%d}.json"
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(enveloppe, f)
    return chemin


def resoudre_cik(argument, table):
    """Renvoie le CIK sur 10 chiffres d'un argument : un CIK (que des chiffres) ou un ticker.

    Fonction sans réseau : la table des tickers est passée en paramètre.
    """
    argument = str(argument).strip()
    if argument.isdigit():
        return normaliser_cik(argument)
    return trouver_cik(argument, table)


def ingerer_entreprise(cik):
    """Récupère puis sauvegarde les données brutes d'une entreprise. Renvoie le chemin du fichier."""
    data = fetch_company_facts(cik)
    chemin = save_raw(data, cik)
    logger.info("%s : données brutes sauvegardées dans %s", data["entityName"], chemin)
    return chemin


def main(arguments):
    """Ingère plusieurs entreprises (tickers ou CIK). Renvoie la liste des arguments en échec.

    Une erreur sur une entreprise n'arrête pas les suivantes.
    """
    table = None
    if any(not str(a).strip().isdigit() for a in arguments):
        table = fetch_company_tickers()  # téléchargée une seule fois pour tous les tickers

    echecs = []
    for i, argument in enumerate(arguments):
        if i > 0:
            time.sleep(PAUSE_SECONDES)
        try:
            cik = resoudre_cik(argument, table)
            ingerer_entreprise(cik)
        except SecConnectorError as e:
            logger.error("%s : %s", argument, e)
            echecs.append(argument)
    return echecs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print("Usage : python -m ingestion.sec_connector <TICKER ou CIK> [<TICKER ou CIK> ...]")
        sys.exit(1)
    try:
        echecs = main(sys.argv[1:])
    except SecConnectorError as e:
        logger.error(e)
        sys.exit(1)
    reussites = len(sys.argv) - 1 - len(echecs)
    logger.info("Terminé : %d réussite(s), %d échec(s)", reussites, len(echecs))
    if echecs:
        logger.error("En échec : %s", ", ".join(echecs))
        sys.exit(1)
