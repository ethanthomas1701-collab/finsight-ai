"""Assistant FinSight : un modèle Claude choisit une requête autorisée et rédige la réponse.

Principe de sécurité : le modèle ne voit ni ne produit de SQL. Il dispose de deux outils,
et chaque appel passe par assistant/requetes.py (liste blanche, base en lecture seule).

Prérequis : la variable d'environnement ANTHROPIC_API_KEY. Ne jamais écrire la clé dans le code.

Utilisation (depuis la racine du dépôt, après python -m transform.stockage) :
    python -m assistant.agent "Comment a évolué la marge nette de Microsoft ?"
"""

import sys

from assistant import requetes
from assistant.requetes import INDICATEURS_AUTORISES, RequeteRefusee

MODELE = "claude-haiku-5-5"
MAX_TOKENS = 1024
MAX_TOURS = 4  # garde-fou : nombre maximal d'allers-retours avec les outils

SYSTEME = (
    "Tu es l'assistant de FinSight AI, un projet pédagogique d'analyse financière "
    "à partir des données publiques de la SEC. Réponds en français. "
    "Appuie-toi uniquement sur les résultats des outils : n'invente aucun chiffre. "
    "Si les données sont absentes ou insuffisantes, dis-le. "
    "Ne donne jamais de conseil en investissement."
)

OUTILS = [
    {
        "name": "evolution",
        "description": "Valeurs d'un indicateur, exercice par exercice, pour une entreprise.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entreprise": {"type": "string", "description": "Nom exact de l'entreprise"},
                "indicateur": {"type": "string", "enum": sorted(INDICATEURS_AUTORISES)},
            },
            "required": ["entreprise", "indicateur"],
        },
    },
    {
        "name": "comparer",
        "description": "Valeur d'un indicateur pour plusieurs entreprises, une année donnée.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entreprises": {"type": "array", "items": {"type": "string"}},
                "indicateur": {"type": "string", "enum": sorted(INDICATEURS_AUTORISES)},
                "annee": {"type": "integer"},
            },
            "required": ["entreprises", "indicateur", "annee"],
        },
    },
]


def executer_outil(nom, arguments, base=requetes.BASE):
    """Exécute un outil autorisé. Renvoie du texte pour le modèle, même en cas de refus."""
    try:
        if nom == "evolution":
            df = requetes.evolution(arguments["entreprise"], arguments["indicateur"], base)
        elif nom == "comparer":
            df = requetes.comparer(
                arguments["entreprises"], arguments["indicateur"], int(arguments["annee"]), base
            )
        else:
            return f"Outil inconnu : {nom}"
    except (RequeteRefusee, KeyError, TypeError, ValueError) as e:
        return f"Requête refusée : {e}"
    return df.to_json(orient="records", force_ascii=False)


def texte_de(reponse):
    return "".join(bloc.text for bloc in reponse.content if bloc.type == "text").strip()


def repondre(question, client=None, base=requetes.BASE):
    """Pose une question à l'assistant et renvoie sa réponse en texte."""
    if client is None:
        import anthropic  # importé ici pour que les tests n'aient pas besoin du réseau

        client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement

    messages = [{"role": "user", "content": question}]
    for _ in range(MAX_TOURS):
        reponse = client.messages.create(
            model=MODELE,
            max_tokens=MAX_TOKENS,
            system=SYSTEME,
            tools=OUTILS,
            messages=messages,
        )
        if reponse.stop_reason != "tool_use":
            return texte_de(reponse)

        messages.append({"role": "assistant", "content": reponse.content})
        resultats = [
            {
                "type": "tool_result",
                "tool_use_id": bloc.id,
                "content": executer_outil(bloc.name, bloc.input, base),
            }
            for bloc in reponse.content
            if bloc.type == "tool_use"
        ]
        messages.append({"role": "user", "content": resultats})
    return "Je n'ai pas pu terminer la réponse dans le nombre de tours prévu."


def main():
    if len(sys.argv) < 2:
        print('Usage : python -m assistant.agent "votre question"')
        return 1
    print(repondre(" ".join(sys.argv[1:])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
