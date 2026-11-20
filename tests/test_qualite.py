"""Tests des contrôles de qualité, sur de petits tableaux gold écrits à la main. Sans réseau."""

import numpy as np
import pandas as pd

from transform.qualite import controler


def ligne(annee, **valeurs):
    base = {
        "entreprise": "A CORP",
        "annee": annee,
        "chiffre_affaires": 1000.0,
        "resultat_net": 100.0,
        "total_actif": 5000.0,
        "total_passif": 3000.0,
        "marge_nette": 0.1,
        "croissance_ca": 0.05,
        "current_ratio": 1.5,
    }
    base.update(valeurs)
    return base


def controles(df):
    return set(controler(pd.DataFrame(df))["controle"])


def test_un_tableau_sain_ne_signale_rien():
    assert controles([ligne(2024), ligne(2025)]) == set()


def test_detecte_un_exercice_manquant():
    assert "exercice_manquant" in controles([ligne(2023), ligne(2025)])


def test_detecte_une_donnee_manquante():
    assert "donnee_manquante" in controles([ligne(2025, resultat_net=np.nan)])


def test_detecte_une_marge_aberrante():
    assert "marge_aberrante" in controles([ligne(2025, marge_nette=1.5)])


def test_detecte_des_capitaux_negatifs():
    assert "capitaux_negatifs" in controles([ligne(2025, total_passif=6000.0)])


def test_detecte_une_croissance_aberrante():
    assert "croissance_aberrante" in controles([ligne(2025, croissance_ca=-1.4)])


def test_detecte_un_current_ratio_extreme():
    assert "current_ratio_extreme" in controles([ligne(2025, current_ratio=25.0)])
