"""Tests de l'assistant local avec un faux appel à Ollama : aucun réseau, aucun modèle requis."""

import sqlite3

import pandas as pd
import pytest

from assistant.agent_local import outils_ollama, repondre_local


@pytest.fixture
def base(tmp_path):
    chemin = tmp_path / "finsight.db"
    df = pd.DataFrame(
        {"entreprise": ["A CORP", "A CORP"], "annee": [2024, 2025], "marge_nette": [0.2, 0.3]}
    )
    with sqlite3.connect(chemin) as connexion:
        df.to_sql("gold_indicateurs", connexion, index=False)
    return chemin


def test_les_outils_sont_au_format_ollama():
    outils = outils_ollama()
    noms = {o["function"]["name"] for o in outils}
    assert noms == {"evolution", "comparer"}
    assert all(o["type"] == "function" for o in outils)


def test_reponse_directe_sans_outil(base):
    def faux_appel(messages, modele):
        return {"role": "assistant", "content": "Bonjour."}

    assert repondre_local("Salut", appel=faux_appel, base=base) == "Bonjour."


def test_le_modele_appelle_un_outil_puis_repond(base):
    etapes = iter(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "evolution",
                            "arguments": {"entreprise": "A CORP", "indicateur": "marge_nette"},
                        }
                    }
                ],
            },
            {"role": "assistant", "content": "La marge passe de 20 % à 30 %."},
        ]
    )
    messages_vus = []

    def faux_appel(messages, modele):
        messages_vus.append(list(messages))
        return next(etapes)

    resultat = repondre_local("Marge de A CORP ?", appel=faux_appel, base=base)

    assert resultat == "La marge passe de 20 % à 30 %."
    # Le second appel doit contenir la réponse de l'outil, au rôle « tool ».
    dernier = messages_vus[1][-1]
    assert dernier["role"] == "tool"
    assert "2025" in dernier["content"]


def test_un_indicateur_invente_par_le_modele_est_refuse(base):
    etapes = iter(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "evolution", "arguments": {"entreprise": "A CORP", "indicateur": "inventé"}}}
                ],
            },
            {"role": "assistant", "content": "Je ne peux pas répondre."},
        ]
    )
    messages_vus = []

    def faux_appel(messages, modele):
        messages_vus.append(list(messages))
        return next(etapes)

    repondre_local("?", appel=faux_appel, base=base)
    assert messages_vus[1][-1]["content"].startswith("Requête refusée")


def test_reponse_vide_rend_les_donnees_obtenues(base):
    etapes = iter(
        [
            {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "evolution", "arguments": {"entreprise": "A CORP", "indicateur": "marge_nette"}}}]},
            {"role": "assistant", "content": ""},
        ]
    )

    def faux_appel(messages, modele):
        return next(etapes)

    resultat = repondre_local("?", appel=faux_appel, base=base)
    assert "Données obtenues" in resultat
    assert "2025" in resultat


def test_repli_sans_modele_quand_le_modele_ne_repond_pas(base):
    from assistant.agent_local import deviner_requete

    assert deviner_requete("Le free cash flow a-t-il augmenté ?", base) is None  # aucune entreprise nommée
    assert deviner_requete("Marge nette de a corp ?", base) == ("A CORP", "marge_nette")

    def faux_appel(messages, modele):
        return {"role": "assistant", "content": ""}

    resultat = repondre_local("Marge nette de a corp ?", appel=faux_appel, base=base)
    assert "marge_nette" in resultat
    assert "2025" in resultat
