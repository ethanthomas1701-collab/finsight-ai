"""Évaluation du lecteur de rapports sur le rapport LVMH 2025 : dix questions, réponses vérifiées à la main.

Lancement (Ollama lancé, depuis la racine du dépôt) :
    python -m assistant.evaluation_lecteur

Une question est réussie si la réponse contient le texte attendu (ou, pour une question hors sujet,
si le lecteur répond « Information absente du rapport »).
"""

import json
from pathlib import Path

from assistant.lecteur_rapport import ABSENT, charger_passages, repondre

PASSAGES = Path("data/rapports/lvmh-2025.json")

# (question, texte attendu dans la réponse, source attendue dans le rapport)
QUESTIONS = [
    ("Quel est le résultat net part du groupe de LVMH en 2025 ?", "10 878", "Résultat net, part du Groupe"),
    ("Quel est le nombre de boutiques du groupe ?", "6 283", "Chiffres clés (au 31 décembre 2025)"),
    ("Quel est le montant du dividende proposé pour 2025 ?", "13,00", "Dette financière nette et capitaux propres"),
    ("Qui est le président-directeur général de LVMH ?", "Bernard Arnault", "Organes de direction"),
    ("Quel est le chiffre d'affaires de LVMH en 2025 ?", "80", "Chiffres clés (au 31 décembre 2025)"),
    ("Combien de collaborateurs LVMH compte-t-il fin 2025 ?", "211 552", "Chiffres clés (au 31 décembre 2025)"),
    ("Quel est le montant de l'acompte sur dividende versé en décembre 2025 ?", "5,50", "Dette financière nette et capitaux propres"),
    ("Quelle est la date de l'assemblée générale 2026 ?", "23 avril 2026", "Censeurs"),
    ("Quel est le montant du solde de dividende versé le 28 avril 2025 ?", "7,50", "Dividende"),
    ("Quel sera le cours de l'action LVMH demain ?", ABSENT, None),
]


def evaluer(passages=None):
    passages = passages if passages is not None else charger_passages(PASSAGES)
    lignes = []
    for question, attendu, _source in QUESTIONS:
        resultat = repondre(question, passages)
        reponse = resultat["reponse"]
        reussi = attendu in reponse
        lignes.append({"question": question, "attendu": attendu, "reussi": reussi,
                       "reponse": reponse, "sources": resultat["sources"]})
    return lignes


def main():
    lignes = evaluer()
    reussies = sum(1 for l in lignes if l["reussi"])
    for l in lignes:
        statut = "OK " if l["reussi"] else "KO "
        print(f"{statut}{l['question']}\n    attendu : {l['attendu']}\n    réponse : {l['reponse'][:200]}")
    print(f"\nRésultat : {reussies}/{len(lignes)} réussies")
    Path("data/rapports/evaluation_lecteur.json").write_text(
        json.dumps(lignes, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
