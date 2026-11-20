"""Tests de la préparation des données de l'interface, sans lancer Streamlit."""

import pandas as pd
import pytest

from app import tableau_entreprise


def gold_exemple():
    return pd.DataFrame(
        {
            "entreprise": ["B CORP", "A CORP", "A CORP"],
            "annee": [2025, 2025, 2024],
            "chiffre_affaires": [2e11, 1e11, 9e10],
            "resultat_net": [4e10, 2e10, 1e10],
            "total_actif": [5e11, 4e11, 3.5e11],
            "total_passif": [3e11, 2e11, 1.8e11],
            "free_cash_flow": [3e10, 1.5e10, 1e10],
            "marge_nette": [0.2, 0.2, 0.111],
            "roe": [0.1, 0.1, 0.09],
            "roa": [0.08, 0.05, 0.03],
            "dette_sur_capitaux_propres": [1.5, 1.0, 1.2],
            "current_ratio": [1.3, 1.1, 1.0],
            "croissance_ca": [0.2, None, None],
        }
    )


def test_ne_garde_que_l_entreprise_demandee_et_trie_par_annee():
    df = tableau_entreprise(gold_exemple(), "A CORP")
    assert list(df["annee"]) == [2024, 2025]


def test_convertit_les_montants_en_milliards_et_les_taux_en_pourcentages():
    df = tableau_entreprise(gold_exemple(), "A CORP")
    ligne = df[df["annee"] == 2025].iloc[0]
    assert ligne["Chiffre d'affaires (Md$)"] == pytest.approx(100.0)
    assert ligne["Marge nette (%)"] == pytest.approx(20.0)
    assert ligne["Current ratio (x)"] == pytest.approx(1.1)  # les ratios restent en unité brute


def test_les_libelles_sont_en_francais():
    df = tableau_entreprise(gold_exemple(), "A CORP")
    assert "Free cash flow (Md$)" in df.columns
    assert "annee" in df.columns


def test_l_interface_se_lance_sans_erreur():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    chemin_app = Path(__file__).resolve().parent.parent / "app.py"
    appli = AppTest.from_file(str(chemin_app)).run(timeout=60)
    assert not appli.exception
