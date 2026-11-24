"""Tests de la couche silver ESEF, sur des faits construits à la main (sans réseau)."""

from datetime import date

import pandas as pd

from transform.silver_esef import construire_silver_esef


def faits_exemple():
    lignes = [
        # Flux de l'exercice 2024 (365 jours)
        {"concept": "Revenue", "debut": date(2024, 1, 1), "fin": date(2024, 12, 31), "valeur": 100.0},
        {"concept": "ProfitLossAttributableToOwnersOfParent", "debut": date(2024, 1, 1), "fin": date(2024, 12, 31), "valeur": 10.0},
        {"concept": "CashFlowsFromUsedInOperatingActivities", "debut": date(2024, 1, 1), "fin": date(2024, 12, 31), "valeur": 15.0},
        # Bilan au 31/12/2024 (instant)
        {"concept": "Assets", "debut": None, "fin": date(2024, 12, 31), "valeur": 200.0},
        {"concept": "CurrentAssets", "debut": None, "fin": date(2024, 12, 31), "valeur": 80.0},
        {"concept": "CurrentLiabilities", "debut": None, "fin": date(2024, 12, 31), "valeur": 40.0},
        {"concept": "EquityAndLiabilities", "debut": None, "fin": date(2024, 12, 31), "valeur": 200.0},
        {"concept": "Equity", "debut": None, "fin": date(2024, 12, 31), "valeur": 90.0},
        # Un trimestre (92 jours) : ne doit pas servir de chiffre annuel
        {"concept": "Revenue", "debut": date(2024, 10, 1), "fin": date(2024, 12, 31), "valeur": 30.0},
    ]
    return pd.DataFrame(lignes, columns=["concept", "debut", "fin", "valeur"])


def test_lit_les_exercices_annuels_et_ignore_les_trimestres():
    tableau = construire_silver_esef(faits_exemple(), "FR0000000000", "EXEMPLE")
    assert list(tableau["annee"]) == [2024]
    assert tableau.loc[0, "chiffre_affaires"] == 100.0


def test_deduit_le_total_passif_de_l_identite_du_bilan():
    tableau = construire_silver_esef(faits_exemple(), "FR0000000000", "EXEMPLE")
    assert tableau.loc[0, "total_passif"] == 110.0  # 200 - 90
    assert tableau.loc[0, "total_actif"] == 200.0


def test_format_identique_a_la_couche_us_et_flux_non_calcule():
    tableau = construire_silver_esef(faits_exemple(), "FR0000000000", "EXEMPLE")
    assert list(tableau.columns) == [
        "cik", "entreprise", "annee", "date_fin", "chiffre_affaires", "resultat_net",
        "total_actif", "total_passif", "actif_courant", "passif_courant",
        "flux_operationnel", "investissements", "devise",
    ]
    assert tableau["investissements"].isna().all()
    assert (tableau["devise"] == "EUR").all()
    assert tableau.loc[0, "cik"] == "FR0000000000"
