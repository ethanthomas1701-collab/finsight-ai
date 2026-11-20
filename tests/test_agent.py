"""Tests de l'assistant avec un faux client Claude : aucun appel réseau, aucune clé nécessaire."""

import sqlite3
from types import SimpleNamespace

import pandas as pd
import pytest

from assistant.agent import executer_outil, repondre


@pytest.fixture
def base(tmp_path):
    chemin = tmp_path / "finsight.db"
    df = pd.DataFrame(
        {
            "entreprise": ["A CORP", "A CORP"],
            "annee": [2024, 2025],
            "marge_nette": [0.2, 0.3],
        }
    )
    with sqlite3.connect(chemin) as connexion:
        df.to_sql("gold_indicateurs", connexion, index=False)
    return chemin


class FauxClient:
    """Imite client.messages.create : renvoie les réponses préparées, dans l'ordre."""

    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.appels = []
        self.messages = self

    def create(self, **kwargs):
        self.appels.append(kwargs)
        return self.reponses.pop(0)


def texte(contenu):
    return SimpleNamespace(type="text", text=contenu)


def outil(nom, arguments, identifiant="t1"):
    return SimpleNamespace(type="tool_use", name=nom, input=arguments, id=identifiant)


def reponse(stop_reason, contenu):
    return SimpleNamespace(stop_reason=stop_reason, content=contenu)


def test_un_outil_autorise_renvoie_les_donnees(base):
    resultat = executer_outil("evolution", {"entreprise": "A CORP", "indicateur": "marge_nette"}, base)
    assert '"annee":2024' in resultat


def test_un_indicateur_non_autorise_est_refuse(base):
    resultat = executer_outil("evolution", {"entreprise": "A CORP", "indicateur": "xyz"}, base)
    assert resultat.startswith("Requête refusée")


def test_un_outil_inconnu_est_refuse(base):
    assert executer_outil("drop_table", {}, base).startswith("Outil inconnu")


def test_reponse_directe_sans_outil(base):
    client = FauxClient([reponse("end_turn", [texte("Bonjour.")])])
    assert repondre("Salut", client=client, base=base) == "Bonjour."


def test_le_modele_appelle_un_outil_puis_repond(base):
    client = FauxClient(
        [
            reponse("tool_use", [outil("evolution", {"entreprise": "A CORP", "indicateur": "marge_nette"})]),
            reponse("end_turn", [texte("La marge passe de 20 % à 30 %.")]),
        ]
    )
    assert repondre("Marge de A CORP ?", client=client, base=base) == "La marge passe de 20 % à 30 %."
    # Le second appel doit contenir le résultat de l'outil.
    dernier_message = client.appels[1]["messages"][-1]
    assert dernier_message["content"][0]["type"] == "tool_result"
    assert "2025" in dernier_message["content"][0]["content"]
