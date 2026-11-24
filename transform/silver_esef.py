"""Couche silver pour les sociétés françaises (ESEF / IFRS).

Même schéma que transform/silver.py, pour que transform/gold.py calcule les indicateurs
sans changement. Correspondance IFRS -> colonnes silver, avec les écarts assumés :

- chiffre_affaires       : Revenue
- resultat_net           : ProfitLossAttributableToOwnersOfParent (part du groupe, comme NetIncomeLoss)
- total_actif            : Assets
- total_passif           : EquityAndLiabilities - Equity (IFRS ne publie pas de total « passif »)
- actif_courant          : CurrentAssets
- passif_courant         : CurrentLiabilities
- flux_operationnel      : CashFlowsFromUsedInOperatingActivities
- investissements        : NON CALCULÉ (pas de concept standard IFRS ; le flux d'investissement
                           total mélange acquisitions et placements, donc le free cash flow
                           n'est pas fiable pour ces sociétés et reste vide)
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SILVER_DIR = Path("data/silver")
COLONNES = ["cik", "entreprise", "annee", "date_fin", "chiffre_affaires", "resultat_net",
            "total_actif", "total_passif", "actif_courant", "passif_courant",
            "flux_operationnel", "investissements"]
# Concepts IFRS à lire pour chaque colonne ; (concepts, est_un_flux)
CORRESPONDANCE = {
    "chiffre_affaires": (["Revenue"], True),
    "resultat_net": (["ProfitLossAttributableToOwnersOfParent"], True),
    "total_actif": (["Assets"], False),
    "actif_courant": (["CurrentAssets"], False),
    "passif_courant": (["CurrentLiabilities"], False),
    "flux_operationnel": (["CashFlowsFromUsedInOperatingActivities"], True),
}


def _serie(faits, concepts, est_un_flux):
    """Valeur par date de fin, pour un concept IFRS. Les flux doivent couvrir un exercice complet."""
    lignes = faits[faits["concept"].isin(concepts)].copy()
    if est_un_flux:
        duree = (pd.to_datetime(lignes["fin"]) - pd.to_datetime(lignes["debut"])).dt.days
        lignes = lignes[duree.between(350, 380)]
    else:
        lignes = lignes[lignes["debut"].isna()]
    if lignes.empty:
        return pd.Series(dtype="float64")
    return lignes.drop_duplicates(subset=["fin"], keep="first").set_index("fin")["valeur"].astype("float64")


def construire_silver_esef(faits, isin, nom):
    """Transforme les faits iXBRL d'une société en tableau annuel au schéma silver."""
    sorties = {}
    for colonne, (concepts, est_un_flux) in CORRESPONDANCE.items():
        sorties[colonne] = _serie(faits, concepts, est_un_flux)

    # Total passif déduit de l'identité du bilan, aligné sur la date de fin.
    passif_et_capitaux = _serie(faits, ["EquityAndLiabilities"], False)
    capitaux = _serie(faits, ["Equity"], False)
    sorties["total_passif"] = passif_et_capitaux - capitaux

    tableau = pd.DataFrame(sorties)
    tableau = tableau.dropna(subset=["chiffre_affaires", "resultat_net"], how="all")
    tableau = tableau.reset_index().rename(columns={"index": "date_fin", "fin": "date_fin"})
    tableau["date_fin"] = pd.to_datetime(tableau["date_fin"]).dt.date.astype(str)
    tableau["annee"] = pd.to_datetime(tableau["date_fin"]).dt.year
    tableau["investissements"] = float("nan")
    tableau.insert(0, "entreprise", nom)
    tableau.insert(0, "cik", isin)
    return tableau[COLONNES].sort_values("annee").reset_index(drop=True)


def sauvegarder_silver_esef(tableau, isin, dossier=SILVER_DIR):
    """Écrit data/silver/CIK<ISIN>.csv (le préfixe CIK permet à transform.gold de le lire)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"CIK{isin}.csv"
    tableau.to_csv(chemin, index=False)
    logger.info("%d exercices -> %s", len(tableau), chemin)
    return chemin
