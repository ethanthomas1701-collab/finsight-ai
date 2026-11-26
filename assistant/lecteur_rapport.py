"""Lecteur de rapports annuels : répond à une question à partir d'un rapport ESEF, avec citation.

Chaîne (tout en local) :
1. texte du rapport XHTML, découpé en passages rattachés à leur section ;
2. recherche lexicale BM25 des passages qui répondent à la question ;
3. le modèle local (Ollama) rédige une réponse à partir de ces seuls passages, en citant la section.

Projet pédagogique : une réponse ne constitue pas un conseil en investissement.
"""

import html
import json
import math
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

URL_OLLAMA = "http://localhost:11434/api/chat"
MODELE = "qwen2.5:3b"
DELAI = 300
MOTS_PAR_PASSAGE = 220
NOMBRE_PASSAGES = 6  # 10 passages dégradent le modèle 3B (mesuré : 5/10 contre 8/10)
ABSENT = "Information absente du rapport."

MOTS_VIDES = set("""
le la les un une des du de d l et ou en au aux a à est sont sur par pour dans qui que quoi
ce cet cette ces il elle ils elles on se sa son ses leur leurs pas ne plus qu avec sans
the of and to in for is are on by an as at be this that with from
""".split())

_RE_BLOC = re.compile(r"<(h[1-6]|p|div|td|li)\b([^>]*)>(.*?)</\1>", re.S | re.I)
_RE_GRAS_STYLE = re.compile(r"font-weight:\s*(?:600|700|bold)", re.I)
_RE_BALISE = re.compile(r"<[^>]+>")
_RE_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
# Dans les rapports ESEF, un titre n'est pas une balise h1-h6 : c'est un bloc court tout en gras.
_RE_GRAS = re.compile(r"<span[^>]*font-weight:\s*(?:600|700|bold)[^>]*>(.*?)</span>", re.S | re.I)


def _est_titre(attributs, contenu, texte):
    """Vrai si le bloc est court et entièrement en gras (titre de section ESEF)."""
    if len(texte) > 120 or len(texte) < 4:
        return False
    if _RE_GRAS_STYLE.search(attributs):  # gras porté par le paragraphe lui-même
        return True
    if not _RE_GRAS.search(contenu):  # gras porté par des spans
        return False
    reste = _RE_GRAS.sub(" ", contenu)
    return not _texte_propre(reste)


def _texte_propre(brut):
    texte = html.unescape(_RE_BALISE.sub(" ", brut))
    return re.sub(r"\s+", " ", texte.replace("\xa0", " ")).strip()


def extraire_sections(xhtml):
    """Renvoie une liste de (section, texte) : chaque bloc de texte porte le titre qui le précède."""
    xhtml = _RE_SCRIPT.sub(" ", xhtml)
    section = "Introduction"
    blocs = []
    for balise, attributs, contenu in _RE_BLOC.findall(xhtml):
        texte = _texte_propre(contenu)
        if len(texte) < 3:
            continue
        if balise.lower().startswith("h") or _est_titre(attributs, contenu, texte):
            section = texte[:120]
            continue
        blocs.append((section, texte))
    return blocs


def decouper(blocs, mots_max=MOTS_PAR_PASSAGE):
    """Regroupe les blocs en passages d'environ `mots_max` mots, sans mélanger deux sections."""
    passages = []
    section_courante, morceaux, nb_mots = None, [], 0

    def vider():
        if morceaux:
            passages.append({"section": section_courante, "texte": " ".join(morceaux)})

    for section, texte in blocs:
        if section != section_courante or nb_mots >= mots_max:
            vider()
            section_courante, morceaux, nb_mots = section, [], 0
        morceaux.append(texte)
        nb_mots += len(texte.split())
    vider()
    for i, passage in enumerate(passages):
        passage["id"] = i
    return passages


def _jetons(texte):
    """Mots en minuscules, sans accents ni mots vides."""
    sans_accents = unicodedata.normalize("NFKD", texte.lower())
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    return [m for m in re.findall(r"[a-z0-9]+", sans_accents) if m not in MOTS_VIDES and len(m) > 1]


def rechercher(question, passages, k=NOMBRE_PASSAGES):
    """Classe les passages par BM25 pour la question ; renvoie les k meilleurs avec leur score."""
    termes = set(_jetons(question))
    if not termes or not passages:
        return []
    # Le titre de section compte double : « Facteurs de risques » doit peser plus qu'un mot isolé.
    docs = [_jetons(p["texte"]) + 2 * _jetons(p["section"]) for p in passages]
    n = len(docs)
    longueur_moyenne = sum(len(d) for d in docs) / n
    freq_doc = [Counter(d) for d in docs]
    df = Counter(t for d in docs for t in set(d))
    k1, b = 1.5, 0.75
    scores = []
    for i, freq in enumerate(freq_doc):
        s = 0.0
        for t in termes:
            if t not in freq:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            f = freq[t]
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(docs[i]) / longueur_moyenne))
        scores.append(s)
    classes = sorted(range(n), key=lambda i: scores[i], reverse=True)
    return [dict(passages[i], score=scores[i]) for i in classes[:k] if scores[i] > 0]


def construire_prompt(question, extraits):
    blocs = "\n\n".join(f"[Section : {e['section']}]\n{e['texte']}" for e in extraits)
    consignes = (
        "Tu réponds en français, à partir des extraits du rapport annuel ci-dessous, et uniquement à partir d'eux.\n"
        "Cite la section entre crochets à la fin de chaque affirmation, par exemple [Section : Résultats].\n"
        f"Si les extraits ne permettent pas de répondre, réponds exactement : « {ABSENT} »\n"
        "Ne donne aucun conseil d'investissement. Réponds en quelques phrases."
    )
    return f"{consignes}\n\nExtraits :\n{blocs}\n\nQuestion : {question}"


def appeler_ollama(message, modele=MODELE, url=URL_OLLAMA):
    corps = json.dumps({
        "model": modele,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    requete = urllib.request.Request(url, data=corps, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            return json.loads(reponse.read().decode("utf-8"))["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as erreur:
        raise RuntimeError(f"Ollama indisponible ou réponse invalide : {erreur}") from erreur


_RE_CHIFFRE = re.compile(r"\d[\d\s  .,]*\d|\d")
_RE_CITATION_MODELE = re.compile(r"\s*\[Section[^\]]*\]")


def _chiffres(texte):
    """Nombres d'un texte, sans séparateurs (« 80 807 » et « 80807 » donnent la même valeur)."""
    return {re.sub(r"[\s  .,]", "", m) for m in _RE_CHIFFRE.findall(texte)}


def sections_sources(reponse, extraits):
    """Sections où figurent les chiffres de la réponse. La source est ainsi vérifiable, pas rédigée."""
    chiffres = _chiffres(reponse)
    retenues = [e["section"] for e in extraits if chiffres & _chiffres(e["texte"])]
    if not retenues:  # réponse sans chiffre : on cite les passages retenus par la recherche
        retenues = [e["section"] for e in extraits]
    return sorted(set(retenues))


NON_VERIFIE = "Réponse non vérifiable : un chiffre cité n'apparaît pas dans les passages du rapport."


def chiffres_non_sources(reponse, extraits, question=""):
    """Chiffres de la réponse qui n'apparaissent dans aucun passage retrouvé.

    Les chiffres repris de la question (par exemple « 2025 ») ne sont pas contrôlés : ils ne viennent
    pas du modèle. Les nombres d'un seul chiffre sont ignorés (trop de faux positifs).
    """
    dans_les_passages = _chiffres(" ".join(e["texte"] for e in extraits))
    dans_la_question = _chiffres(question)
    return {c for c in _chiffres(reponse)
            if len(c) >= 2 and c not in dans_les_passages and c not in dans_la_question}


MODELE_CLAUDE = "claude-haiku-5-5"


def appeler_claude(message, modele=MODELE_CLAUDE):
    """Rédaction par l'API Claude. Nécessite ANTHROPIC_API_KEY ; le SDK la lit dans l'environnement."""
    import anthropic

    client = anthropic.Anthropic()
    reponse = client.messages.create(
        model=modele,
        max_tokens=600,
        temperature=0,
        messages=[{"role": "user", "content": message}],
    )
    return "".join(bloc.text for bloc in reponse.content if getattr(bloc, "type", "") == "text").strip()


def moteur_par_defaut():
    """Claude si une clé est configurée et si LECTEUR_MOTEUR ne force pas Ollama, sinon Ollama."""
    import os

    if os.environ.get("LECTEUR_MOTEUR", "").lower() == "ollama":
        return appeler_ollama
    if os.environ.get("ANTHROPIC_API_KEY"):
        return appeler_claude
    return appeler_ollama


def repondre(question, passages, appel=None):
    """Répond à la question à partir des passages. `appel` est injectable pour les tests.

    Garde-fou : une réponse qui cite un chiffre absent des passages est refusée, plutôt que
    transmise comme si elle était vérifiée.
    """
    appel = appel or moteur_par_defaut()
    extraits = rechercher(question, passages)
    if not extraits:
        return {"reponse": ABSENT, "sources": []}
    brute = appel(construire_prompt(question, extraits))
    reponse = _RE_CITATION_MODELE.sub("", brute).strip()
    if reponse == ABSENT:
        return {"reponse": ABSENT, "sources": []}
    if chiffres_non_sources(reponse, extraits, question):
        return {"reponse": NON_VERIFIE, "sources": []}
    return {"reponse": reponse, "sources": sections_sources(reponse, extraits)}


def charger_passages(cache):
    return json.loads(Path(cache).read_text(encoding="utf-8"))


def main():
    if len(sys.argv) < 2:
        print('Usage : python -m assistant.lecteur_rapport "votre question"')
        return
    passages = charger_passages("data/rapports/lvmh-2025.json")
    resultat = repondre(" ".join(sys.argv[1:]), passages)
    print(resultat["reponse"])
    if resultat["sources"]:
        print("\nSections consultées :", " ; ".join(resultat["sources"]))


if __name__ == "__main__":
    main()
