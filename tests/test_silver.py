"""Tests de la couche silver, sans fichier ni réseau."""

import pandas as pd

from transform.silver import (
    construire_silver,
    dedoublonner,
    extraire_valeurs,
    filtrer_annuels,
    sauvegarder_silver,
    serie_indicateur,
)


def fait(end, val, form="10-K", filed="2024-08-01", start=None):
    """Fabrique une valeur au format de la SEC."""
    valeur = {"end": end, "val": val, "form": form, "filed": filed}
    if start is not None:
        valeur["start"] = start
    return valeur


def concept(*valeurs):
    return {"units": {"USD": list(valeurs)}}


def test_extraire_valeurs_concept_absent_donne_un_tableau_vide():
    df = extraire_valeurs({}, "Revenues")
    assert df.empty
    assert list(df.columns) == ["start", "end", "val", "form", "filed"]


def test_extraire_valeurs_stock_sans_start():
    df = extraire_valeurs({"Assets": concept(fait("2024-06-30", 100))}, "Assets")
    assert df.loc[0, "val"] == 100
    assert df.loc[0, "start"] is None


def test_filtrer_annuels_retire_10q_et_trimestres():
    df = pd.DataFrame([
        fait("2024-06-30", 400, start="2023-07-01"),               # un an : gardé
        fait("2024-06-30", 100, start="2024-04-01"),               # trimestre dans un 10-K
        fait("2024-03-31", 300, form="10-Q", start="2023-07-01"),  # 10-Q
    ])
    garde = filtrer_annuels(df, est_un_flux=True)
    assert garde["val"].tolist() == [400]


def test_filtrer_annuels_stock_ne_regarde_pas_la_duree():
    df = pd.DataFrame([fait("2024-06-30", 100), fait("2024-03-31", 90, form="10-Q")])
    df["start"] = None
    assert filtrer_annuels(df, est_un_flux=False)["val"].tolist() == [100]


def test_dedoublonner_garde_la_publication_la_plus_recente():
    df = pd.DataFrame([
        fait("2023-06-30", 95, filed="2024-08-01"),   # valeur corrigée l'année suivante
        fait("2023-06-30", 90, filed="2023-08-01"),
        fait("2024-06-30", 120, filed="2024-08-01"),
    ])
    garde = dedoublonner(df).sort_values("end")
    assert garde["val"].tolist() == [95, 120]


def test_serie_indicateur_priorite_des_concepts():
    us_gaap = {
        "Revenues": concept(fait("2024-06-30", 200, start="2023-07-01")),
        "SalesRevenueNet": concept(
            fait("2016-06-30", 80, start="2015-07-01"),
            fait("2024-06-30", 999, start="2023-07-01"),  # ignoré : Revenues prioritaire
        ),
    }
    serie = serie_indicateur(us_gaap, ["Revenues", "SalesRevenueNet"], est_un_flux=True)
    assert serie.to_dict() == {"2016-06-30": 80.0, "2024-06-30": 200.0}


def test_construire_silver_une_ligne_par_exercice():
    data = {
        "cik": 789019,
        "entityName": "TEST CORP",
        "facts": {"us-gaap": {
            "Revenues": concept(fait("2024-06-30", 200, start="2023-07-01")),
            "NetIncomeLoss": concept(fait("2024-06-30", 50, start="2023-07-01")),
            "Assets": concept(fait("2023-06-30", 900), fait("2024-06-30", 1000)),
            "Liabilities": concept(fait("2024-06-30", 400)),
        }},
    }
    df = construire_silver(data)
    # 2023-06-30 n'a qu'un bilan, sans CA ni résultat : la ligne est retirée.
    assert len(df) == 1
    ligne = df.iloc[0]
    assert ligne["entreprise"] == "TEST CORP"
    assert ligne["annee"] == 2024
    assert ligne["chiffre_affaires"] == 200
    assert ligne["total_passif"] == 400


def test_sauvegarder_silver_nomme_le_fichier_avec_le_cik(tmp_path):
    df = pd.DataFrame({"annee": [2024]})
    chemin = sauvegarder_silver(df, 789019, dossier=tmp_path)
    assert chemin.name == "CIK0000789019.csv"
    assert pd.read_csv(chemin)["annee"].tolist() == [2024]
