"""Interface FinSight AI : indicateurs financiers d'une entreprise, en tableau et en graphiques.

Lancement (depuis la racine du dépôt, environnement finsight actif) :
    streamlit run app.py

Les données viennent de data/gold/indicateurs.csv (produit par transform.gold).
Projet pédagogique : ces indicateurs ne constituent pas un conseil en investissement.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

GOLD = Path("data/gold/indicateurs.csv")
MILLIARD = 1e9

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


def main():
    st.set_page_config(page_title="FinSight AI", layout="wide")
    st.title("FinSight AI")
    st.caption(
        "Projet pédagogique à partir des données publiques de la SEC EDGAR. "
        "Ce n'est pas un conseil en investissement."
    )

    if not GOLD.exists():
        st.error(
            "Pas encore de données. Dans le terminal, depuis la racine du dépôt : "
            "python run_pipeline.py MSFT AAPL GOOGL, puis python -m transform.silver, "
            "puis python -m transform.gold."
        )
        st.stop()

    gold = pd.read_csv(GOLD)
    entreprise = st.selectbox("Entreprise", sorted(gold["entreprise"].unique()))
    df = tableau_entreprise(gold, entreprise)

    st.subheader("Indicateurs par exercice")
    st.dataframe(df.set_index("annee"), use_container_width=True)

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


if __name__ == "__main__":
    main()
