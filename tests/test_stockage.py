"""Tests du stockage SQLite, dans un dossier temporaire. Sans réseau."""

import sqlite3

import pandas as pd

from transform.stockage import ecrire_tables


def test_ecrit_les_tables_et_les_relit(tmp_path):
    base = tmp_path / "finsight.db"
    tables = {"gold_indicateurs": pd.DataFrame({"entreprise": ["A", "B"], "annee": [2024, 2025]})}

    comptes = ecrire_tables(tables, base)

    assert comptes == {"gold_indicateurs": 2}
    with sqlite3.connect(base) as connexion:
        relu = pd.read_sql("SELECT * FROM gold_indicateurs", connexion)
    assert list(relu["entreprise"]) == ["A", "B"]


def test_remplace_une_table_existante(tmp_path):
    base = tmp_path / "finsight.db"
    ecrire_tables({"t": pd.DataFrame({"x": [1, 2, 3]})}, base)
    ecrire_tables({"t": pd.DataFrame({"x": [9]})}, base)  # la nouvelle version remplace l'ancienne

    with sqlite3.connect(base) as connexion:
        relu = pd.read_sql("SELECT * FROM t", connexion)
    assert list(relu["x"]) == [9]
