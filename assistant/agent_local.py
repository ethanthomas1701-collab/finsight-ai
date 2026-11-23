"""Assistant FinSight avec un modèle local (Ollama) : gratuit, sans clé API, rien ne quitte le PC.

Même principe que assistant/agent.py : le modèle ne produit jamais de SQL. Il appelle deux outils
(evolution, comparer), et chaque appel passe par assistant/requetes.py.

Prérequis : Ollama lancé, avec le modèle installé (par défaut qwen2.5:3b).

Utilisation (depuis la racine du dépôt, après python -m transform.stockage) :
    python -m assistant.agent_local "Comment a évolué la marge nette de Microsoft ?"
"""

import json
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


def repondre_local(question, appel=appel_ollama, base=requetes.BASE, modele=MODELE):
    """Pose une question à l'assistant local. `appel` peut être remplacé pour les tests."""
    messages = [
        {"role": "system", "content": SYSTEME},
        {"role": "user", "content": question},
    ]
    for _ in range(MAX_TOURS):
        message = appel(messages, modele)
        appels = message.get("tool_calls") or []
        if not appels:
            return (message.get("content") or "").strip()

        messages.append(message)
        for appel_outil in appels:
            fonction = appel_outil["function"]
            arguments = fonction.get("arguments") or {}
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            messages.append(
                {
                    "role": "tool",
                    "content": executer_outil(fonction["name"], arguments, base),
                }
            )
    return "Je n'ai pas pu terminer la réponse dans le nombre de tours prévu."


def main():
    if len(sys.argv) < 2:
        print('Usage : python -m assistant.agent_local "votre question"')
        return 1
    print(repondre_local(" ".join(sys.argv[1:])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
