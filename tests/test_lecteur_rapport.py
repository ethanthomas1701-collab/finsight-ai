"""Tests du lecteur de rapports, sans réseau ni Ollama (le modèle est simulé)."""

from assistant.lecteur_rapport import (
    ABSENT,
    decouper,
    extraire_sections,
    rechercher,
    repondre,
    sections_sources,
)

XHTML = """
<html><body>
<p>Introduction générale du rapport.</p>
<p style="font-weight:700;">Facteurs de risques</p>
<p>Le groupe est exposé au risque de change sur ses ventes en dollars.</p>
<p>Le risque fiscal dépend des réglementations de chaque pays.</p>
<p style="font-weight:700;">Dividende</p>
<p>Le dividende proposé est de 13,00 euros par action au titre de 2025.</p>
</body></html>
"""


def test_detecte_les_titres_en_gras_et_rattache_les_blocs():
    blocs = extraire_sections(XHTML)
    sections = {s for s, _ in blocs}
    assert "Facteurs de risques" in sections
    assert "Dividende" in sections
    assert ("Dividende", "Le dividende proposé est de 13,00 euros par action au titre de 2025.") in blocs


def test_decoupe_sans_melanger_deux_sections():
    passages = decouper(extraire_sections(XHTML), mots_max=500)
    for passage in passages:
        assert passage["section"] in {"Introduction", "Facteurs de risques", "Dividende"}
    assert [p["id"] for p in passages] == list(range(len(passages)))


def test_recherche_privilegie_le_passage_qui_repond():
    passages = decouper(extraire_sections(XHTML), mots_max=500)
    meilleur = rechercher("Quel est le dividende proposé ?", passages, k=1)[0]
    assert meilleur["section"] == "Dividende"


def test_question_sans_rapport_renvoie_absent_sans_appeler_le_modele():
    passages = decouper(extraire_sections(XHTML), mots_max=500)
    appels = []
    resultat = repondre("Quel est le cours de bourse de demain ?", passages, appel=lambda m: appels.append(m) or "x")
    assert resultat["reponse"] == ABSENT
    assert appels == []


def test_source_deterministe_selon_le_chiffre_de_la_reponse():
    passages = decouper(extraire_sections(XHTML), mots_max=500)
    extraits = rechercher("dividende 13,00 euros", passages)
    sources = sections_sources("Le dividende est de 13,00 euros.", extraits)
    assert sources == ["Dividende"]


def test_retire_la_citation_inventee_par_le_modele():
    passages = decouper(extraire_sections(XHTML), mots_max=500)
    resultat = repondre(
        "Quel est le dividende ?",
        passages,
        appel=lambda m: "Le dividende est de 13,00 euros. [Section : Inventée]",
    )
    assert "Inventée" not in resultat["reponse"]
    assert resultat["sources"] == ["Dividende"]
