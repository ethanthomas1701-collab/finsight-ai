"""Tests du connecteur SEC, sans appel réseau.

Lancer depuis la racine du dépôt :
    python -m pytest
"""

import pytest

from ingestion.sec_connector import (
    SecConnectorError,
    get_user_agent,
    normaliser_cik,
    trouver_cik,
)


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


# --- trouver_cik ----------------------------------------------------------

# Petite table inventée, au même format que company_tickers.json de la SEC.
TABLE_TEST = {
    "0": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}


def test_trouver_cik_renvoie_le_cik_sur_10_chiffres():
    assert trouver_cik("MSFT", TABLE_TEST) == "0000789019"


def test_trouver_cik_accepte_les_minuscules():
    assert trouver_cik("aapl", TABLE_TEST) == "0000320193"


def test_trouver_cik_retire_les_espaces():
    assert trouver_cik("  msft ", TABLE_TEST) == "0000789019"


def test_trouver_cik_erreur_si_ticker_inconnu():
    with pytest.raises(SecConnectorError, match="Ticker inconnu"):
        trouver_cik("XYZ", TABLE_TEST)
