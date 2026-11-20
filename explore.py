"""Exploration des fichiers bronze : quels concepts us-gaap chaque entreprise utilise-t-elle ?

Lit les fichiers de data/bronze/ (aucun appel réseau) et affiche, pour chaque
indicateur, les concepts candidats présents, le nombre de valeurs annuelles (10-K)
et les années couvertes. Sert à choisir les noms à extraire dans la couche silver.

Utilisation (depuis la racine du dépôt) :
    python explore.py
"""

import json
from pathlib import Path

BRONZE_DIR = Path("data/bronze")

# Pour chaque indicateur, les noms de concepts us-gaap possibles.
CANDIDATS = {
    "Chiffre d'affaires": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "Résultat net": ["NetIncomeLoss"],
    "Total actif": ["Assets"],
    "Total passif": ["Liabilities"],
}


def dernier_fichier_par_cik(chemins):
    """Garde, pour chaque CIK, le fichier le plus récent (nom CIK<cik>_<AAAAMMJJ>.json)."""
    derniers = {}
    for chemin in sorted(Path(c) for c in chemins):
        cik = chemin.stem.split("_")[0]
        derniers[cik] = chemin  # trié par nom, donc le dernier écrase les plus anciens
    return list(derniers.values())


def charger_bronze(chemin):
    """Lit un fichier bronze et renvoie la réponse SEC (sans l'enveloppe)."""
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)["data"]


def resumer_concept(us_gaap, concept):
    """Résume un concept : nombre de valeurs annuelles en USD et années couvertes.

    Renvoie None si l'entreprise n'utilise pas ce concept.
    """
    if concept not in us_gaap:
        return None
    valeurs = us_gaap[concept].get("units", {}).get("USD", [])
    annuelles = [v for v in valeurs if v.get("form") == "10-K"]
    annees = sorted({int(v["end"][:4]) for v in annuelles})
    return {
        "nb_valeurs": len(annuelles),
        "premiere_annee": annees[0] if annees else None,
        "derniere_annee": annees[-1] if annees else None,
    }


def afficher_resume(data):
    """Affiche, pour une entreprise, les concepts trouvés pour chaque indicateur."""
    us_gaap = data["facts"].get("us-gaap", {})
    print(f"\n=== {data['entityName']} ({len(us_gaap)} concepts us-gaap) ===")
    for indicateur, concepts in CANDIDATS.items():
        print(f"  {indicateur} :")
        for concept in concepts:
            resume = resumer_concept(us_gaap, concept)
            if resume is None:
                print(f"    - {concept} : absent")
            else:
                print(
                    f"    - {concept} : {resume['nb_valeurs']} valeurs 10-K, "
                    f"{resume['premiere_annee']} -> {resume['derniere_annee']}"
                )


def main():
    chemins = dernier_fichier_par_cik(BRONZE_DIR.glob("CIK*.json"))
    if not chemins:
        print(f"Aucun fichier CIK*.json dans {BRONZE_DIR}. Lancer d'abord l'ingestion.")
        return
    for chemin in chemins:
        afficher_resume(charger_bronze(chemin))


if __name__ == "__main__":
    main()
