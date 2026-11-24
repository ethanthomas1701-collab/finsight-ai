"""Tests de la conversion dollar / euro, sans réseau."""

import pandas as pd
import pytest

from transform.devises import convertir_montant, convertir_tableau

TAUX = {2024: 1.25, 2025: 1.10}  # dollars pour un euro


def test_euro_vers_dollar_multiplie_par_le_taux():
    assert convertir_montant(100.0, "EUR", "USD", 2024, TAUX) == pytest.approx(125.0)


def test_dollar_vers_euro_divise_par_le_taux():
    assert convertir_montant(125.0, "USD", "EUR", 2024, TAUX) == pytest.approx(100.0)


def test_aller_retour_redonne_la_valeur_initiale():
    aller = convertir_montant(84.7, "EUR", "USD", 2025, TAUX)
    retour = convertir_montant(aller, "USD", "EUR", 2025, TAUX)
    assert retour == pytest.approx(84.7)


def test_meme_devise_ne_change_rien():
    assert convertir_montant(50.0, "USD", "USD", 2030, TAUX) == 50.0


def test_valeur_manquante_reste_manquante():
    assert pd.isna(convertir_montant(float("nan"), "EUR", "USD", 2024, TAUX))


def test_annee_sans_taux_leve_une_erreur_claire():
    with pytest.raises(KeyError):
        convertir_montant(1.0, "EUR", "USD", 1999, TAUX)


def test_tableau_convertit_montants_mais_pas_les_ratios():
    df = pd.DataFrame({
        "annee": [2024, 2025],
        "devise": ["EUR", "EUR"],
        "chiffre_affaires": [100.0, 200.0],
        "marge_nette": [0.15, 0.20],
    })
    converti = convertir_tableau(df, "USD", TAUX)
    assert list(converti["chiffre_affaires"]) == pytest.approx([125.0, 220.0])
    assert list(converti["marge_nette"]) == [0.15, 0.20]
    assert set(converti["devise"]) == {"USD"}
