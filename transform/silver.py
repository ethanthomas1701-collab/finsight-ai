"""Couche silver : des fichiers bronze (JSON brut SEC) vers un tableau annuel propre.

Pour chaque entreprise, on garde une ligne par exercice fiscal avec :
chiffre d'affaires, résultat net, total actif, total passif.

Règles de nettoyage (constatées avec explore.py) :
- seulement les valeurs des rapports annuels (form 10-K) ;
- pour les flux (CA, résultat net), seulement les périodes d'environ un an,
  car les 10-K contiennent aussi des trimestres ;
- les 10-K répètent les années passées : pour une même date de fin, on garde
  la valeur publiée le plus récemment (elle intègre les corrections) ;
- le nom du CA change selon les années : on prend le premier concept
  disponible dans l'ordre de priorité.

Utilisation (depuis la racine du dépôt) :
    python -m transform.silver
"""

import logging
from pathlib import Path

import pandas as pd

from explore import charger_bronze, dernier_fichier_par_cik

logger = logging.getLogger(__name__)

BRONZE_DIR = Path("data/bronze")
SILVER_DIR = Path("data/silver")

# Indicateur -> (concepts par ordre de priorité, est-ce un flux sur une période ?)
INDICATEURS = {
    "chiffre_affaires": (
        [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
        ],
        True,
    ),
    "resultat_net": (["NetIncomeLoss"], True),
    "total_actif": (["Assets"], False),
    "total_passif": (["Liabilities"], False),
}

# Un exercice fiscal dure 52 ou 53 semaines (364 ou 371 jours) : marge large.
DUREE_ANNUELLE_MIN = 350
DUREE_ANNUELLE_MAX = 380


def extraire_valeurs(us_gaap, concept):
    """Renvoie les valeurs en USD d'un concept sous forme de DataFrame.

    Colonnes : start (absente pour un stock comme l'actif), end, val, form, filed.
    DataFrame vide si l'entreprise n'utilise pas ce concept.
    """
    valeurs = us_gaap.get(concept, {}).get("units", {}).get("USD", [])
    df = pd.DataFrame(valeurs)
    if df.empty:
        return pd.DataFrame(columns=["start", "end", "val", "form", "filed"])
    if "start" not in df.columns:
        df["start"] = None
    return df[["start", "end", "val", "form", "filed"]]


def filtrer_annuels(df, est_un_flux):
    """Garde les valeurs des 10-K et, pour un flux, les périodes d'environ un an."""
    df = df[df["form"] == "10-K"].copy()
    if est_un_flux:
        duree = (pd.to_datetime(df["end"]) - pd.to_datetime(df["start"])).dt.days
        df = df[duree.between(DUREE_ANNUELLE_MIN, DUREE_ANNUELLE_MAX)]
    return df


def dedoublonner(df):
    """Une seule valeur par date de fin : celle publiée le plus récemment."""
    df = df.sort_values("filed")
    return df.drop_duplicates(subset="end", keep="last")


def serie_indicateur(us_gaap, concepts, est_un_flux):
    """Série (index = date de fin) d'un indicateur, en combinant ses concepts.

    Pour chaque date de fin, le premier concept de la liste qui a une valeur l'emporte.
    """
    resultat = pd.Series(dtype="float64")
    for concept in concepts:
        df = dedoublonner(filtrer_annuels(extraire_valeurs(us_gaap, concept), est_un_flux))
        serie = df.set_index("end")["val"].astype("float64")
        # combine_first : garde les valeurs déjà trouvées, complète les dates manquantes.
        resultat = serie if resultat.empty else resultat.combine_first(serie)
    return resultat


def construire_silver(data):
    """Construit le tableau annuel d'une entreprise à partir d'une réponse SEC."""
    us_gaap = data["facts"].get("us-gaap", {})
    colonnes = {
        nom: serie_indicateur(us_gaap, concepts, est_un_flux)
        for nom, (concepts, est_un_flux) in INDICATEURS.items()
    }
    df = pd.DataFrame(colonnes)
    df.index.name = "date_fin"
    df = df.reset_index().sort_values("date_fin")
    # On ne garde que les exercices où le CA ou le résultat net est connu : les
    # bilans seuls (date de fin d'un exercice précédent) n'apportent rien ici.
    df = df.dropna(subset=["chiffre_affaires", "resultat_net"], how="all")
    df.insert(0, "annee", pd.to_datetime(df["date_fin"]).dt.year)
    df.insert(0, "entreprise", data["entityName"])
    df.insert(0, "cik", int(data["cik"]))
    return df.reset_index(drop=True)


def sauvegarder_silver(df, cik, dossier=SILVER_DIR):
    """Écrit le tableau dans data/silver/CIK<cik>.csv et renvoie le chemin."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"CIK{int(cik):010d}.csv"
    df.to_csv(chemin, index=False)
    return chemin


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    chemins = dernier_fichier_par_cik(BRONZE_DIR.glob("CIK*.json"))
    if not chemins:
        logger.error("Aucun fichier CIK*.json dans %s. Lancer d'abord l'ingestion.", BRONZE_DIR)
        return 1
    for chemin in chemins:
        data = charger_bronze(chemin)
        df = construire_silver(data)
        sortie = sauvegarder_silver(df, data["cik"])
        logger.info("%s : %d exercices -> %s", data["entityName"], len(df), sortie)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
