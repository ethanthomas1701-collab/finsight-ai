"""Assistant FinSight avec un modèle local (Ollama) : gratuit, sans clé API, rien ne quitte le PC.

Même principe que assistant/agent.py : le modèle ne produit jamais de SQL. Il appelle deux outils
(evolution, comparer), et chaque appel passe par assistant/requetes.py.

Prérequis : Ollama lancé, avec le modèle installé (par défaut qwen2.5:3b).

Utilisation (depuis la racine du dépôt, après python -m transform.stockage) :
    python -m assistant.agent_local "Comment a évolué la marge nette de Microsoft ?"
"""

import json
import re
import sys
import urllib.request

from assistant import requetes
from assistant.agent import OUTILS as OUTILS_CLAUDE
from assistant.agent import SYSTEME, executer_outil

URL_OLLAMA = "http://localhost:11434/api/chat"
MODELE = "qwen2.5:3b"
MAX_TOURS = 4
DELAI_SECONDES = 900  # le premier chargement du modèle sur le processeur peut être long


def outils_ollama():
    """Même liste d'outils que pour Claude, au format attendu par Ollama."""
    return [
        {
            "type": "function",
            "function": {
                "name": outil["name"],
                "description": outil["description"],
                "parameters": outil["input_schema"],
            },
        }
        for outil in OUTILS_CLAUDE
    ]


def appel_ollama(messages, modele=MODELE, url=URL_OLLAMA):
    """Envoie la conversation à Ollama et renvoie le message de réponse (dictionnaire)."""
    corps = json.dumps(
        {
            "model": modele,
            "messages": messages,
            "tools": outils_ollama(),
            "stream": False,
        }
    ).encode("utf-8")
    requete = urllib.request.Request(url, data=corps, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=DELAI_SECONDES) as reponse:
        return json.loads(reponse.read().decode("utf-8"))["message"]


# Expressions courantes -> indicateur de la base.
MOTS_INDICATEURS = [
    ("free cash flow", "free_cash_flow"),
    ("cash-flow", "free_cash_flow"),
    ("marge nette", "marge_nette"),
    ("chiffre d'affaires", "chiffre_affaires"),
    ("résultat net", "resultat_net"),
    ("total actif", "total_actif"),
    ("total passif", "total_passif"),
    ("current ratio", "current_ratio"),
    ("roe", "roe"),
    ("roa", "roa"),
    ("endettement", "dette_sur_capitaux_propres"),
    ("croissance", "croissance_ca"),
]


def deviner_requete(question, base=requetes.BASE):
    """Repère l'entreprise et l'indicateur d'une question, sans modèle. Renvoie (nom, indicateur) ou None."""
    texte = question.casefold()
    indicateur = next((cle for mot, cle in MOTS_INDICATEURS if mot in texte), None)
    entreprises = []
    for nom in requetes.entreprises_connues(base):
        # Le nom complet, ou son premier mot s'il est assez long pour ne pas être un mot courant.
        premier = re.sub(r"[^\w]", " ", nom).split()[0].casefold()  # « AMAZON.COM, INC. » -> « amazon »
        candidats = [nom.casefold()]
        if len(premier) >= 4:
            candidats.append(premier)
        if any(re.search(rf"\b{re.escape(c)}\b", texte) for c in candidats):
            entreprises.append(nom)
    for alias, cible in requetes.ALIAS.items():
        if alias in texte:
            entreprises += [n for n in requetes.entreprises_connues(base) if cible in n.casefold()]
    if indicateur is None or len(set(entreprises)) != 1:
        return None
    return sorted(set(entreprises))[0], indicateur


def repondre_sans_modele(question, base=requetes.BASE):
    """Réponse de secours, sans modèle : données et phrase construites à partir de la base."""
    requete = deviner_requete(question, base)
    if requete is None:
        return None
    entreprise, indicateur = requete
    df = requetes.evolution(entreprise, indicateur, base)
    return requetes.phrase_evolution(df, entreprise, indicateur)


def repondre_local(question, appel=appel_ollama, base=requetes.BASE, modele=MODELE):
    """Pose une question à l'assistant local. `appel` peut être remplacé pour les tests."""
    messages = [
        {"role": "system", "content": SYSTEME},
        {"role": "user", "content": question},
    ]
    dernier_resultat = None
    for _ in range(MAX_TOURS):
        message = appel(messages, modele)
        appels = message.get("tool_calls") or []
        if not appels:
            texte = (message.get("content") or "").strip()
            if texte:
                return texte
            # Le modèle n'a rien rédigé : on rend au moins les données obtenues, sans les inventer.
            if dernier_resultat is not None:
                return f"Réponse du modèle vide. Données obtenues : {dernier_resultat}"
            secours = repondre_sans_modele(question, base)
            if secours:
                return secours + " (réponse construite directement à partir de la base)"
            return "Réponse du modèle vide. Reformulez la question avec un nom d'entreprise précis."

        messages.append(message)
        for appel_outil in appels:
            fonction = appel_outil["function"]
            arguments = fonction.get("arguments") or {}
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            dernier_resultat = executer_outil(fonction["name"], arguments, base)
            messages.append({"role": "tool", "content": dernier_resultat})
    return "Je n'ai pas pu terminer la réponse dans le nombre de tours prévu."


def main():
    if len(sys.argv) < 2:
        print('Usage : python -m assistant.agent_local "votre question"')
        return 1
    print(repondre_local(" ".join(sys.argv[1:])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
