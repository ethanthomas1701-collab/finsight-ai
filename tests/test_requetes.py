"""Tests des requêtes contrôlées de l'assistant, sur une base SQLite temporaire. Sans réseau."""

import sqlite3

import pandas as pd
import pytest

from assistant.requetes import (
    RequeteRefusee,
    comparer,
    evolution,
    phrase_evolution,
)


@pytest.fixture
def base(tmp_path):
    chemin = tmp_path / "finsight.db"
    df = pd.DataFrame(
        {
            "entreprise": ["A CORP", "A CORP", "A CORP", "B CORP", "B CORP"],
            "annee": [2023, 2024, 2025, 2024, 2025],
            "chiffre_affaires": [1e11, None, 1.2e11, 5e10, 6e10],
            "marge_nette": [0.2, 0.25, 0.3, 0.1, 0.12],
        }
    )
    with sqlite3.connect(chemin) as connexion:
        df.to_sql("gold_indicateurs", connexion, index=False)
    return chemin


def test_evolution_renvoie_les_exercices_dans_l_ordre(base):
    df = evolution("A CORP", "marge_nette", base)
    assert list(df["annee"]) == [2023, 2024, 2025]


def test_indicateur_hors_liste_est_refuse(base):
    with pytest.raises(RequeteRefusee):
        evolution("A CORP", "marge_nette; DROP TABLE gold_indicateurs", base)


def test_entreprise_inconnue_est_refusee(base):
    with pytest.raises(RequeteRefusee):
        evolution("ZZZ", "marge_nette", base)


def test_la_base_est_en_lecture_seule(base):
    # Une écriture doit échouer : l'assistant ne peut rien modifier.
    from assistant.requetes import connexion_lecture

    with pytest.raises(sqlite3.OperationalError):
        with connexion_lecture(base) as connexion:
            connexion.execute("DELETE FROM gold_indicateurs")


def test_comparaison_une_annee(base):
    df = comparer(["A CORP", "B CORP"], "marge_nette", 2025, base)
    assert dict(zip(df["entreprise"], df["marge_nette"])) == pytest.approx({"A CORP": 0.3, "B CORP": 0.12})


def test_phrase_avec_variation_et_trous(base):
    df = evolution("A CORP", "chiffre_affaires", base)
    phrase = phrase_evolution(df, "A CORP", "chiffre_affaires")
    assert "augmente" in phrase
    assert "2024" in phrase  # l'exercice manquant est signalé
    assert "+20%" in phrase


def test_phrase_signale_les_donnees_insuffisantes(base):
    df = evolution("B CORP", "marge_nette", base).iloc[[0]]  # un seul exercice
    assert "insuffisantes" in phrase_evolution(df, "B CORP", "marge_nette")


def test_les_montants_sont_affiches_en_milliards(base):
    from assistant.requetes import formater

    assert formater("chiffre_affaires", 1.2e11) == "120.0 Md$"
    assert formater("marge_nette", 0.3) == "30.0%"
    assert formater("current_ratio", 1.35) == "1.35"
