"""Tests du connecteur SEC, sans appel réseau.

Lancer depuis la racine du dépôt :
    python -m pytest
"""

import pytest

from ingestion.sec_connector import SecConnectorError, get_user_agent, normaliser_cik


# --- normaliser_cik -------------------------------------------------------

def test_normaliser_cik_complete_avec_des_zeros():
    assert normaliser_cik("789019") == "0000789019"


def test_normaliser_cik_accepte_un_entier():
    assert normaliser_cik(789019) == "0000789019"


def test_normaliser_cik_retire_les_espaces():
    assert normaliser_cik("  789019 ") == "0000789019"


def test_normaliser_cik_laisse_un_cik_deja_complet():
    assert normaliser_cik("0000789019") == "0000789019"


@pytest.mark.parametrize("cik_invalide", ["abc", "12a45", "", "12345678901"])
def test_normaliser_cik_refuse_les_cik_invalides(cik_invalide):
    with pytest.raises(SecConnectorError):
        normaliser_cik(cik_invalide)


# --- get_user_agent -------------------------------------------------------

def test_get_user_agent_renvoie_la_variable(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Test Exemple test@exemple.com")
    assert get_user_agent() == "Test Exemple test@exemple.com"


def test_get_user_agent_erreur_si_variable_absente(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(SecConnectorError, match="SEC_USER_AGENT"):
        get_user_agent()


def test_get_user_agent_erreur_si_variable_vide(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "")
    with pytest.raises(SecConnectorError):
        get_user_agent()
