"""Tests du pipeline complet, sans réseau : on fabrique une fausse réponse SEC."""

from ingestion.sec_connector import save_raw
from run_pipeline import construire_silver_depuis_bronze


def valeur(fin, val, debut=None):
    """Une valeur publiée dans un 10-K, comme dans la réponse de la SEC."""
    v = {"end": fin, "val": val, "form": "10-K", "filed": "2025-07-30"}
    if debut:
        v["start"] = debut
    return v


def fausse_reponse():
    return {
        "cik": 789019,
        "entityName": "TEST CORP",
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [valeur("2025-06-30", 1000, "2024-07-01")]}},
                "NetIncomeLoss": {"units": {"USD": [valeur("2025-06-30", 100, "2024-07-01")]}},
                "Assets": {"units": {"USD": [valeur("2025-06-30", 5000)]}},
                "Liabilities": {"units": {"USD": [valeur("2025-06-30", 3000)]}},
            }
        },
    }


def test_construit_un_csv_silver_depuis_le_bronze(tmp_path):
    bronze = tmp_path / "bronze"
    silver = tmp_path / "silver"
    save_raw(fausse_reponse(), 789019, dossier=bronze)

    sorties = construire_silver_depuis_bronze(bronze, silver)

    assert len(sorties) == 1
    contenu = sorties[0].read_text(encoding="utf-8")
    assert "TEST CORP" in contenu
    assert "1000" in contenu  # chiffre d'affaires de l'exercice
