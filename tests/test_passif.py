"""Tests du total passif : direct s'il existe, sinon déduit de l'identité du bilan. Sans réseau."""

from transform.silver import serie_passif


def valeur(fin, val):
    return {"end": fin, "val": val, "form": "10-K", "filed": "2010-07-30"}


def test_passif_direct_quand_le_concept_existe():
    us_gaap = {
        "Liabilities": {"units": {"USD": [valeur("2012-06-30", 300)]}},
        "LiabilitiesAndStockholdersEquity": {"units": {"USD": [valeur("2012-06-30", 1000)]}},
        "StockholdersEquity": {"units": {"USD": [valeur("2012-06-30", 700)]}},
    }
    assert serie_passif(us_gaap)["2012-06-30"] == 300


def test_passif_deduit_quand_le_concept_direct_manque():
    # Cas des anciens rapports : pas de 'Liabilities', mais total et capitaux propres connus.
    us_gaap = {
        "LiabilitiesAndStockholdersEquity": {"units": {"USD": [valeur("2009-06-30", 1000)]}},
        "StockholdersEquity": {"units": {"USD": [valeur("2009-06-30", 700)]}},
    }
    assert serie_passif(us_gaap)["2009-06-30"] == 300
