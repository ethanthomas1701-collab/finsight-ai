"""Tests des indicateurs gold, sur de petits tableaux silver écrits à la main. Sans réseau."""

import pandas as pd
import pytest

from transform.gold import calculer_indicateurs


COLONNES_OPTIONNELLES = ["actif_courant", "passif_courant", "flux_operationnel", "investissements"]


def tableau(**colonnes):
    """Tableau de test. Les colonnes récentes absentes valent NaN par défaut."""
    df = pd.DataFrame(colonnes)
    for nom in COLONNES_OPTIONNELLES:
        if nom not in df:
            df[nom] = float("nan")
    return df


def test_current_ratio_et_free_cash_flow():
    df = tableau(
        date_fin=["2025-06-30"],
        annee=[2025],
        chiffre_affaires=[1000.0],
        resultat_net=[100.0],
        total_actif=[5000.0],
        total_passif=[3000.0],
        actif_courant=[2000.0],
        passif_courant=[1000.0],
        flux_operationnel=[400.0],
        investissements=[150.0],
    )
    ligne = calculer_indicateurs(df).iloc[0]
    assert ligne["current_ratio"] == pytest.approx(2.0)
    assert ligne["free_cash_flow"] == pytest.approx(250.0)


def test_marge_roe_roa_et_dette_sur_une_ligne():
    df = tableau(
        date_fin=["2025-06-30"],
        annee=[2025],
        chiffre_affaires=[1000.0],
        resultat_net=[100.0],
        total_actif=[5000.0],
        total_passif=[3000.0],
    )
    ligne = calculer_indicateurs(df).iloc[0]
    assert ligne["capitaux_propres"] == pytest.approx(2000.0)
    assert ligne["marge_nette"] == pytest.approx(0.10)
    assert ligne["roe"] == pytest.approx(0.05)
    assert ligne["roa"] == pytest.approx(0.02)
    assert ligne["dette_sur_capitaux_propres"] == pytest.approx(1.5)


def test_croissance_du_ca_sur_exercices_consecutifs():
    df = tableau(
        date_fin=["2024-06-30", "2025-06-30"],
        annee=[2024, 2025],
        chiffre_affaires=[1000.0, 1100.0],
        resultat_net=[100.0, 110.0],
        total_actif=[5000.0, 5000.0],
        total_passif=[3000.0, 3000.0],
    )
    resultat = calculer_indicateurs(df)
    assert pd.isna(resultat.iloc[0]["croissance_ca"])  # pas d'exercice précédent
    assert resultat.iloc[1]["croissance_ca"] == pytest.approx(0.10)


def test_pas_de_croissance_quand_une_annee_manque():
    df = tableau(
        date_fin=["2023-06-30", "2025-06-30"],
        annee=[2023, 2025],
        chiffre_affaires=[1000.0, 1100.0],
        resultat_net=[100.0, 110.0],
        total_actif=[5000.0, 5000.0],
        total_passif=[3000.0, 3000.0],
    )
    assert pd.isna(calculer_indicateurs(df).iloc[1]["croissance_ca"])


def test_division_par_zero_donne_un_vide():
    df = tableau(
        date_fin=["2025-06-30"],
        annee=[2025],
        chiffre_affaires=[0.0],
        resultat_net=[100.0],
        total_actif=[5000.0],
        total_passif=[5000.0],  # capitaux propres nuls
    )
    ligne = calculer_indicateurs(df).iloc[0]
    assert pd.isna(ligne["marge_nette"])
    assert pd.isna(ligne["roe"])
