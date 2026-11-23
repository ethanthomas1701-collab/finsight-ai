"""Interface FinSight AI : indicateurs financiers d'une entreprise, en tableau et en graphiques.

Lancement (depuis la racine du dépôt, environnement finsight actif) :
    streamlit run app.py

Les données viennent de data/gold/indicateurs.csv (produit par transform.gold). Si ce fichier
n'existe pas (par exemple sur le site publié), l'application lit la copie publique dans
donnees_publiques/indicateurs.csv.
Projet pédagogique : ces indicateurs ne constituent pas un conseil en investissement.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

GOLD = Path("data/gold/indicateurs.csv")
GOLD_PUBLIC = Path("donnees_publiques/indicateurs.csv")
MILLIARD = 1e9


def chemin_donnees():
    """Renvoie le fichier d'indicateurs à utiliser : local d'abord, public ensuite."""
    for chemin in (GOLD, GOLD_PUBLIC):
        if chemin.exists():
            return chemin
    return None

# Colonnes du tableau gold -> libellés affichés.
LIBELLES = {
    "chiffre_affaires": "Chiffre d'affaires (Md$)",
    "resultat_net": "Résultat net (Md$)",
    "total_actif": "Total actif (Md$)",
    "total_passif": "Total passif (Md$)",
    "free_cash_flow": "Free cash flow (Md$)",
    "marge_nette": "Marge nette (%)",
    "roe": "ROE (%)",
    "roa": "ROA (%)",
    "dette_sur_capitaux_propres": "Dette / capitaux propres (x)",
    "current_ratio": "Current ratio (x)",
    "croissance_ca": "Croissance du CA (%)",
}
EN_MILLIARDS = ["chiffre_affaires", "resultat_net", "total_actif", "total_passif", "free_cash_flow"]
EN_POURCENTS = ["marge_nette", "roe", "roa", "croissance_ca"]


def tableau_entreprise(gold, entreprise):
    """Renvoie les indicateurs d'une entreprise, par exercice, avec unités lisibles."""
    df = gold[gold["entreprise"] == entreprise].sort_values("annee").copy()
    for colonne in EN_MILLIARDS:
        df[colonne] = df[colonne] / MILLIARD
    for colonne in EN_POURCENTS:
        df[colonne] = df[colonne] * 100
    return df[["annee", *LIBELLES]].rename(columns=LIBELLES).reset_index(drop=True)


def comparer(gold, entreprises, indicateur):
    """Tableau années x entreprises pour comparer un indicateur (unités d'affichage)."""
    df = tableau_entreprise_brute(gold, entreprises)
    return df.pivot(index="annee", columns="entreprise", values=indicateur).sort_index()


def tableau_entreprise_brute(gold, entreprises):
    """Lignes de plusieurs entreprises avec les unités d'affichage, sans les filtrer une à une."""
    morceaux = [tableau_entreprise(gold, nom).assign(entreprise=nom) for nom in entreprises]
    return pd.concat(morceaux, ignore_index=True)


def main():
    st.set_page_config(page_title="FinSight AI", layout="wide")
    st.title("FinSight AI")
    st.caption(
        "Projet pédagogique à partir des données publiques de la SEC EDGAR. "
        "Ce n'est pas un conseil en investissement."
    )

    fichier = chemin_donnees()
    if fichier is None:
        st.error(
            "Pas encore de données. Dans le terminal, depuis la racine du dépôt : "
            "python run_pipeline.py MSFT AAPL GOOGL, puis python -m transform.silver, "
            "puis python -m transform.gold."
        )
        st.stop()

    gold = pd.read_csv(fichier)
    entreprise = st.selectbox("Entreprise", sorted(gold["entreprise"].unique()))
    df = tableau_entreprise(gold, entreprise)

    st.subheader("Indicateurs par exercice")
    st.dataframe(df.set_index("annee"), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Chiffre d'affaires et résultat net (Md$)")
        st.line_chart(df.set_index("annee")[["Chiffre d'affaires (Md$)", "Résultat net (Md$)"]])
        st.subheader("Marge nette et ROE (%)")
        st.line_chart(df.set_index("annee")[["Marge nette (%)", "ROE (%)"]])
    with col2:
        st.subheader("Free cash flow (Md$)")
        st.line_chart(df.set_index("annee")[["Free cash flow (Md$)"]])
        st.subheader("Liquidité et endettement")
        st.line_chart(df.set_index("annee")[["Current ratio (x)", "Dette / capitaux propres (x)"]])

    st.subheader("Comparaison entre entreprises")
    choix = st.multiselect(
        "Entreprises à comparer",
        sorted(gold["entreprise"].unique()),
        default=sorted(gold["entreprise"].unique())[:3],
    )
    indicateur = st.selectbox("Indicateur", [LIBELLES[c] for c in EN_POURCENTS + ["current_ratio"]])
    if choix:
        st.line_chart(comparer(gold, choix, indicateur))


if __name__ == "__main__":
    main()
