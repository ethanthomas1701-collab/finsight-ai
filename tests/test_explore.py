"""Tests de explore.py, sans fichier ni réseau."""

from pathlib import Path

from explore import dernier_fichier_par_cik, resumer_concept

# Petit extrait inventé, au même format que facts["us-gaap"] de la SEC.
US_GAAP_TEST = {
    "Assets": {
        "units": {
            "USD": [
                {"end": "2023-06-30", "val": 100, "form": "10-K"},
                {"end": "2024-06-30", "val": 120, "form": "10-K"},
                {"end": "2024-09-30", "val": 125, "form": "10-Q"},  # trimestriel : ignoré
            ]
        }
    },
    "Liabilities": {"units": {"USD": [{"end": "2024-09-30", "val": 50, "form": "10-Q"}]}},
}


def test_resumer_concept_compte_les_valeurs_annuelles():
    assert resumer_concept(US_GAAP_TEST, "Assets") == {
        "nb_valeurs": 2,
        "premiere_annee": 2023,
        "derniere_annee": 2024,
    }


def test_resumer_concept_renvoie_none_si_absent():
    assert resumer_concept(US_GAAP_TEST, "Revenues") is None


def test_resumer_concept_sans_valeur_annuelle():
    assert resumer_concept(US_GAAP_TEST, "Liabilities") == {
        "nb_valeurs": 0,
        "premiere_annee": None,
        "derniere_annee": None,
    }


def test_dernier_fichier_par_cik_garde_le_plus_recent():
    chemins = [
        "data/bronze/CIK0000789019_20261120.json",
        "data/bronze/CIK0000320193_20261120.json",
        "data/bronze/CIK0000789019_20261119.json",
    ]
    assert dernier_fichier_par_cik(chemins) == [
        Path("data/bronze/CIK0000320193_20261120.json"),
        Path("data/bronze/CIK0000789019_20261120.json"),
    ]
