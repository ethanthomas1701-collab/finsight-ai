"""Tests du connecteur ESEF, sans réseau : lecture d'un extrait iXBRL construit à la main."""

import io
import zipfile
from datetime import date

import pandas as pd
import pytest

from ingestion.esef_connector import (
    EsefError,
    extraire_faits,
    lire_contextes,
    rapport_xhtml,
    valeur_numerique,
)

EXTRAIT = """
<html><body>
<ix:header><ix:resources>
<xbrli:context id="ctx-1"><xbrli:entity><xbrli:identifier scheme="x">ID</xbrli:identifier></xbrli:entity>
<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period></xbrli:context>
<xbrli:context id="ctx-4"><xbrli:entity><xbrli:identifier scheme="x">ID</xbrli:identifier></xbrli:entity>
<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period></xbrli:context>
<xbrli:context id="ctx-seg"><xbrli:entity><xbrli:identifier scheme="x">ID</xbrli:identifier>
<xbrli:segment><xbrldi:explicitMember dimension="ifrs-full:SegmentsAxis">LVM:Mode</xbrldi:explicitMember></xbrli:segment>
</xbrli:entity>
<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period></xbrli:context>
</ix:resources></ix:header>
<p>Chiffre d'affaires : <ix:nonFraction format="ixt:num-comma-decimal" decimals="-6" scale="6" name="ifrs-full:Revenue" contextRef="ctx-1" unitRef="eur">84 683</ix:nonFraction></p>
<p>Résultat : <ix:nonFraction format="ixt:num-comma-decimal" decimals="-6" scale="6" sign="-" name="ifrs-full:ProfitLoss" contextRef="ctx-1" unitRef="eur">12<span> 958</span></ix:nonFraction></p>
<p>Actifs : <ix:nonFraction format="ixt:num-comma-decimal" decimals="-6" scale="6" name="ifrs-full:Assets" contextRef="ctx-4" unitRef="eur">149 190</ix:nonFraction></p>
<p>Détail par mode : <ix:nonFraction format="ixt:num-comma-decimal" decimals="-6" scale="6" name="ifrs-full:Revenue" contextRef="ctx-seg" unitRef="eur">12 000</ix:nonFraction></p>
<p>Autre : <ix:nonFraction format="ixt:num-comma-decimal" scale="0" name="LVM:Interne" contextRef="ctx-1" unitRef="eur">5</ix:nonFraction></p>
</body></html>
"""


def test_lit_les_periodes_et_repere_les_dimensions():
    contextes = lire_contextes(EXTRAIT)
    assert contextes["ctx-1"] == {"debut": date(2024, 1, 1), "fin": date(2024, 12, 31), "dimensions": False}
    assert contextes["ctx-4"]["debut"] is None
    assert contextes["ctx-4"]["fin"] == date(2024, 12, 31)
    assert contextes["ctx-seg"]["dimensions"] is True


def test_convertit_separateur_milliers_et_echelle():
    assert valeur_numerique({"format": "ixt:num-comma-decimal", "scale": "6"}, "84 683") == pytest.approx(84_683e6)


def test_applique_le_signe_et_ignore_les_balises_internes():
    attributs = {"format": "ixt:num-comma-decimal", "scale": "6", "sign": "-"}
    assert valeur_numerique(attributs, "12<span> 958</span>") == pytest.approx(-12_958e6)


def test_lit_les_attributs_entre_apostrophes():
    texte = (
        "<xbrli:context id='c1'><xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>"
        "<xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period></xbrli:context>"
        "<ix:nonFraction id='t1' name='ifrs-full:Revenue' contextRef='c1' unitRef='u' decimals='-5' "
        "format='ixt:num-comma-decimal' scale='6'>12 500</ix:nonFraction>"
    )
    faits = extraire_faits(texte)
    assert faits.loc[0, "concept"] == "Revenue"
    assert faits.loc[0, "valeur"] == pytest.approx(12_500e6)


def test_decode_les_entites_html_des_espaces():
    assert valeur_numerique({"format": "ixt:num-comma-decimal", "scale": "6"}, "1&#xa0;237") == pytest.approx(1_237e6)


def test_format_zero_donne_zero():
    assert valeur_numerique({"format": "ixt:fixed-zero", "scale": "6"}, "-") == 0.0


def test_extrait_seulement_les_faits_ifrs_consolides():
    faits = extraire_faits(EXTRAIT)
    assert set(faits["concept"]) == {"Revenue", "ProfitLoss", "Assets"}
    revenu = faits[faits["concept"] == "Revenue"].iloc[0]
    assert revenu["valeur"] == pytest.approx(84_683e6)
    assert revenu["debut"] == date(2024, 1, 1)
    assert revenu["fin"] == date(2024, 12, 31)
    resultat = faits[faits["concept"] == "ProfitLoss"].iloc[0]
    assert resultat["valeur"] == pytest.approx(-12_958e6)
    actif = faits[faits["concept"] == "Assets"].iloc[0]
    assert pd.isna(actif["debut"])  # bilan : instant, pas de date de début


def test_rapport_xhtml_lit_le_rapport_dans_l_archive():
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("pkg/reports/rapport.xhtml", EXTRAIT)
        archive.writestr("pkg/META-INF/catalog.xml", "<catalog/>")
    assert "ifrs-full:Revenue" in rapport_xhtml(tampon.getvalue())


def test_archive_illisible_leve_une_erreur_propre():
    with pytest.raises(EsefError):
        rapport_xhtml(b"ceci n'est pas une archive")
