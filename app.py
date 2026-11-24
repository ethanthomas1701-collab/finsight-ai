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
NOMBRE_D_EXERCICES_AFFICHES = 10


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
    # Le calcul est total passif / capitaux propres : le libellé le dit tel quel.
    "dette_sur_capitaux_propres": "Passif / capitaux propres (x)",
    "current_ratio": "Current ratio (x)",
    "croissance_ca": "Croissance du CA (%)",
}
EN_MILLIARDS = ["chiffre_affaires", "resultat_net", "total_actif", "total_passif", "free_cash_flow"]
EN_POURCENTS = ["marge_nette", "roe", "roa", "croissance_ca"]

# Définitions courtes, affichées sous le tableau pour les lecteurs qui découvrent ces ratios.
DEFINITIONS = [
    ("Marge nette", "résultat net divisé par le chiffre d'affaires : la part des ventes qui reste en bénéfice."),
    ("ROE", "résultat net divisé par les capitaux propres : la rentabilité pour les actionnaires."),
    ("ROA", "résultat net divisé par le total de l'actif : la rentabilité de l'ensemble des moyens."),
    ("Passif / capitaux propres", "total du passif divisé par les capitaux propres : plus il est élevé, plus l'entreprise dépend de ses créanciers."),
    ("Current ratio", "actif courant divisé par passif courant : la capacité à régler les dettes à moins d'un an."),
    ("Free cash flow", "flux de trésorerie d'exploitation moins les investissements : l'argent réellement dégagé sur l'exercice."),
    ("Croissance du CA", "variation du chiffre d'affaires par rapport à l'exercice précédent."),
]


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


def formater(valeur, decimales=1):
    """Nombre au format français (virgule, espace des milliers), ou un tiret si la donnée manque."""
    if pd.isna(valeur):
        return "—"
    texte = f"{valeur:,.{decimales}f}"
    return texte.replace(",", "_").replace(".", ",").replace("_", " ")


def ecart(actuel, precedent):
    """Différence entre deux exercices, ou None si l'un des deux manque."""
    if precedent is None or pd.isna(actuel) or pd.isna(precedent):
        return None
    return actuel - precedent


def tableau_lisible(df, nombre=NOMBRE_D_EXERCICES_AFFICHES):
    """Indicateurs en lignes, exercices récents en colonnes, valeurs déjà mises en forme."""
    recent = df.tail(nombre)
    lignes = {}
    for colonne in recent.columns[1:]:
        decimales = 2 if "(x)" in colonne else 1
        lignes[colonne] = [formater(valeur, decimales) for valeur in recent[colonne]]
    tableau = pd.DataFrame(lignes, index=[str(annee) for annee in recent["annee"]]).T
    return tableau.rename_axis("Indicateur")


def main():
    st.set_page_config(page_title="FinSight AI", layout="wide")
    st.title("FinSight AI")
    st.write(
        "Les indicateurs financiers annuels d'une entreprise, calculés à partir de ses "
        "rapports officiels déposés à la SEC."
    )
    st.caption("Projet pédagogique. Ce n'est pas un conseil en investissement.")

    fichier = chemin_donnees()
    if fichier is None:
        st.error(
            "Pas encore de données. Dans le terminal, depuis la racine du dépôt : "
            "python run_pipeline.py MSFT AAPL GOOGL, puis python -m transform.silver, "
            "puis python -m transform.gold."
        )
        st.stop()

    gold = pd.read_csv(fichier)
    entreprises = sorted(gold["entreprise"].unique())
    entreprise = st.selectbox("Entreprise", entreprises)
    df = tableau_entreprise(gold, entreprise)
    if df.empty:
        st.info("Aucun exercice disponible pour cette entreprise.")
        st.stop()

    derniere = df.iloc[-1]
    precedente = df.iloc[-2] if len(df) > 1 else None
    st.subheader(f"Dernier exercice : {int(derniere['annee'])}")
    st.caption("Variations par rapport à l'exercice précédent")
    indicateurs_cles = [
        ("Chiffre d'affaires", "Chiffre d'affaires (Md$)", "Md$"),
        ("Marge nette", "Marge nette (%)", "%"),
        ("ROE", "ROE (%)", "%"),
        ("Free cash flow", "Free cash flow (Md$)", "Md$"),
    ]
    for colonne, (titre, cle, unite) in zip(st.columns(4), indicateurs_cles):
        variation = ecart(derniere[cle], precedente[cle] if precedente is not None else None)
        delta = None
        if variation is not None:
            signe = "+" if variation > 0 else ""
            delta = f"{signe}{formater(variation)} {unite}"
        colonne.metric(titre, f"{formater(derniere[cle])} {unite}", delta)

    st.subheader(f"Les {NOMBRE_D_EXERCICES_AFFICHES} derniers exercices")
    st.dataframe(tableau_lisible(df), width="stretch")
    st.caption(
        "Montants en milliards de dollars (Md$), taux en pourcentage, ratios sans unité (x). "
        "Un tiret signale une donnée absente dans le rapport."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Chiffre d'affaires et résultat net")
        st.caption("Milliards de dollars, par exercice")
        st.line_chart(df.set_index("annee")[["Chiffre d'affaires (Md$)", "Résultat net (Md$)"]])
    with col2:
        st.subheader("Rentabilité")
        st.caption("Marge nette et ROE, en pourcentage")
        st.line_chart(df.set_index("annee")[["Marge nette (%)", "ROE (%)"]])

    with st.expander("Comprendre les indicateurs"):
        st.markdown("\n".join(f"- **{nom}** : {definition}" for nom, definition in DEFINITIONS))

    st.subheader("Comparer des entreprises")
    choix = st.multiselect("Entreprises", entreprises, default=entreprises[:3])
    indicateur = st.selectbox(
        "Indicateur",
        [LIBELLES[c] for c in ["chiffre_affaires", *EN_POURCENTS, "current_ratio"]],
    )
    if choix:
        st.line_chart(comparer(gold, choix, indicateur))
    else:
        st.info("Choisissez au moins une entreprise.")


if __name__ == "__main__":
    main()
