"""Interface FinSight AI : indicateurs financiers d'une entreprise, en tableau et en graphiques.

Lancement (depuis la racine du dépôt, environnement finsight actif) :
    streamlit run app.py

Les données viennent de data/gold/indicateurs.csv (produit par transform.gold). Si ce fichier
n'existe pas (par exemple sur le site publié), l'application lit la copie publique dans
donnees_publiques/indicateurs.csv.
Projet pédagogique : ces indicateurs ne constituent pas un conseil en investissement.
"""

import html
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

GOLD = Path("data/gold/indicateurs.csv")
GOLD_PUBLIC = Path("donnees_publiques/indicateurs.csv")
MILLIARD = 1e9
NOMBRE_D_EXERCICES_AFFICHES = 10

# Palette catégorielle validée (skill dataviz, référence palette.md), mode clair.
# L'ordre est fixe : une entreprise garde la même couleur quel que soit le filtre.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ENCRE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"
GRIS_DISCRET = "#898781"
GRILLE = "#e1e0d9"
AXE = "#c3c2b7"
VERT_TEXTE = "#006300"  # variation favorable, texte
ROUGE_TEXTE = "#d03b3b"  # variation défavorable, texte


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

# Définitions courtes, affichées pour les lecteurs qui découvrent ces ratios.
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


def tableau_entreprise_brute(gold, entreprises):
    """Lignes de plusieurs entreprises avec les unités d'affichage, sans les filtrer une à une."""
    morceaux = [tableau_entreprise(gold, nom).assign(entreprise=nom) for nom in entreprises]
    return pd.concat(morceaux, ignore_index=True)


def comparer(gold, entreprises, indicateur):
    """Tableau années x entreprises pour comparer un indicateur (unités d'affichage)."""
    df = tableau_entreprise_brute(gold, entreprises)
    return df.pivot(index="annee", columns="entreprise", values=indicateur).sort_index()


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


def couleurs_entreprises(gold):
    """Attribue une couleur fixe à chaque entreprise, dans l'ordre alphabétique."""
    noms = sorted(gold["entreprise"].unique())
    return {nom: PALETTE[i] if i < len(PALETTE) else GRIS_DISCRET for i, nom in enumerate(noms)}


def habiller(graphique):
    """Style commun : fond transparent, grille discrète, texte lisible."""
    return (
        graphique.configure_view(stroke=None)
        .configure_axis(
            labelColor=ENCRE_SECONDAIRE, titleColor=ENCRE_SECONDAIRE, gridColor=GRILLE,
            domainColor=AXE, tickColor=AXE, labelFont="sans-serif", titleFont="sans-serif",
        )
        .configure_legend(labelColor=ENCRE_SECONDAIRE, titleColor=ENCRE_SECONDAIRE, labelFont="sans-serif")
        .configure_mark(color=PALETTE[0])
    )


def graphique_lignes(df, colonnes, unite, couleurs):
    """Lignes par exercice, info-bulle au survol et repère vertical qui suit l'année."""
    # Vega-Lite lit les noms de colonnes comme des chemins : on utilise des noms sûrs (s0, s1...).
    noms_sur = {c: f"s{i}" for i, c in enumerate(colonnes)}
    d = df[["annee", *colonnes]].rename(columns=noms_sur)
    long = d.melt(id_vars="annee", value_vars=list(noms_sur.values()), var_name="serie", value_name="valeur")
    libelle = {v: k for k, v in noms_sur.items()}
    long["indicateur"] = long["serie"].map(libelle)
    long = long.dropna(subset=["valeur"])
    echelle = alt.Scale(domain=colonnes, range=[couleurs[c] for c in colonnes])
    survol = alt.selection_point(fields=["annee"], on="pointerover", nearest=True, empty=False, clear="pointerout")
    base = alt.Chart(long).encode(
        x=alt.X("annee:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("valeur:Q", title=unite),
        color=alt.Color("indicateur:N", scale=echelle, legend=alt.Legend(orient="top", title=None)),
    )
    lignes = base.mark_line(strokeWidth=2.5)
    points = base.mark_circle(size=90).encode(opacity=alt.condition(survol, alt.value(1), alt.value(0)))
    repere = (
        alt.Chart(long).mark_rule(strokeWidth=1, color=GRIS_DISCRET)
        .encode(x="annee:O", opacity=alt.condition(survol, alt.value(0.8), alt.value(0)))
        .transform_filter(survol)
    )
    # Bande transparente par exercice : l'info-bulle liste toutes les séries à cette année.
    large = d
    info = [alt.Tooltip("annee:O", title="Exercice")] + [
        alt.Tooltip(field=noms_sur[c], type="quantitative", title=c, format=",.1f") for c in colonnes
    ]
    bande = (
        alt.Chart(large).mark_bar(opacity=0)
        .encode(x=alt.X("annee:O"), tooltip=info)
    )
    couche = alt.layer(lignes, points, repere, bande).add_params(survol)
    return habiller(couche.properties(height=320))


def graphique_barres(df, colonne, unite, couleur):
    """Barres par exercice, info-bulle au survol, extrémités arrondies."""
    d = df[["annee", colonne]].rename(columns={colonne: "valeur"})
    base = alt.Chart(d).encode(
        x=alt.X("annee:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("valeur:Q", title=unite),
        tooltip=[alt.Tooltip("annee:O", title="Exercice"),
                 alt.Tooltip("valeur:Q", title=unite, format=",.1f")],
    )
    barres = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=couleur)
    return habiller(barres.properties(height=320))


def graphique_comparaison(gold, entreprises, indicateur, couleurs):
    """Plusieurs entreprises ; cliquer une entreprise dans la légende isole sa courbe."""
    df = comparer(gold, entreprises, indicateur).reset_index().melt(
        id_vars="annee", var_name="entreprise", value_name="valeur"
    ).dropna(subset=["valeur"])
    selection = alt.selection_point(fields=["entreprise"], bind="legend")
    echelle = alt.Scale(domain=list(entreprises), range=[couleurs[n] for n in entreprises])
    graphique = (
        alt.Chart(df)
        .mark_line(strokeWidth=2.5, point=True)
        .encode(
            x=alt.X("annee:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("valeur:Q", title=indicateur),
            color=alt.Color("entreprise:N", scale=echelle, legend=alt.Legend(orient="top", title=None)),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.12)),
            tooltip=[alt.Tooltip("annee:O", title="Exercice"), alt.Tooltip("entreprise:N", title="Entreprise"),
                     alt.Tooltip("valeur:Q", title=indicateur, format=",.1f")],
        )
        .add_params(selection)
    )
    return habiller(graphique.properties(height=360))


def carte_kpi(titre, valeur, variation, unite, couleur):
    """Carte d'indicateur : valeur, variation avec icône et libellé (jamais la couleur seule)."""
    if variation is None:
        delta = '<span class="delta neutre">Pas d\'exercice précédent</span>'
    elif variation >= 0:
        delta = f'<span class="delta hausse">▲ hausse de {html.escape(formater(variation))} {html.escape(unite)}</span>'
    else:
        delta = f'<span class="delta baisse">▼ baisse de {html.escape(formater(-variation))} {html.escape(unite)}</span>'
    return f"""
    <div class="carte" style="--couleur:{couleur}">
        <div class="carte-titre">{html.escape(titre)}</div>
        <div class="carte-valeur">{html.escape(valeur)}</div>
        {delta}
    </div>"""


STYLE = """
<style>
  .entete {
    background: #2a78d6; color: #ffffff; border-radius: 18px; padding: 28px 32px; margin-bottom: 8px;
  }
  .entete h1 { color: #ffffff; margin: 0 0 6px 0; font-size: 2.6rem; }
  .entete p { margin: 0; font-size: 1.05rem; opacity: 0.95; }
  .chips { margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }
  .chip {
    background: #ffffff; color: #0b0b0b; border-radius: 999px; padding: 4px 12px;
    font-size: 0.85rem; font-weight: 600;
  }
  .cartes { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 12px 0 8px 0; }
  .carte {
    border-radius: 16px; padding: 18px 20px; background: color-mix(in srgb, var(--couleur) 10%, transparent);
    border-left: 6px solid var(--couleur);
  }
  .carte-titre { font-size: 0.9rem; font-weight: 600; opacity: 0.8; }
  .carte-valeur { font-size: 2rem; font-weight: 800; margin: 4px 0; }
  .delta { font-size: 0.9rem; font-weight: 600; }
  .delta.hausse { color: #006300; }
  .delta.baisse { color: #d03b3b; }
  .delta.neutre { opacity: 0.7; }
  @media (max-width: 800px) { .cartes { grid-template-columns: repeat(2, 1fr); } }
</style>
"""


def main():
    st.set_page_config(page_title="FinSight AI", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="entete">
          <h1>FinSight AI</h1>
          <p>Les indicateurs financiers annuels d'une entreprise, calculés à partir de ses rapports
          officiels déposés à la SEC. Projet pédagogique : ce n'est pas un conseil en investissement.</p>
          <div class="chips">
            <span class="chip">Source : SEC EDGAR</span>
            <span class="chip">Rapports annuels 10-K</span>
            <span class="chip">6 entreprises</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
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
    entreprises = sorted(gold["entreprise"].unique())
    couleurs = couleurs_entreprises(gold)

    # Filtres : une seule rangée, au-dessus de tout le contenu.
    col_entreprise, col_periode, col_tableau = st.columns([2, 3, 1])
    with col_entreprise:
        entreprise = st.selectbox("Entreprise", entreprises)
    annees = sorted(gold.loc[gold["entreprise"] == entreprise, "annee"].unique())
    with col_periode:
        if len(annees) > 1:
            lo, hi = st.select_slider("Période", options=annees, value=(annees[0], annees[-1]))
        else:
            lo = hi = annees[0]
            st.caption(f"Un seul exercice disponible : {annees[0]}")
    with col_tableau:
        afficher_tableau = st.toggle("Voir le tableau", value=False)

    periode = gold[(gold["annee"] >= lo) & (gold["annee"] <= hi)]
    df = tableau_entreprise(periode, entreprise)
    if df.empty:
        st.info("Aucun exercice disponible pour cette entreprise sur cette période.")
        st.stop()

    derniere = df.iloc[-1]
    precedente = df.iloc[-2] if len(df) > 1 else None
    st.subheader(f"{entreprise} · exercice {int(derniere['annee'])}")
    st.caption("Variation par rapport à l'exercice précédent")
    cartes = [
        ("Chiffre d'affaires", "Chiffre d'affaires (Md$)", "Md$", PALETTE[0], "Md$"),
        ("Marge nette", "Marge nette (%)", "%", PALETTE[1], "%"),
        ("ROE", "ROE (%)", "%", PALETTE[2], "%"),
        ("Free cash flow", "Free cash flow (Md$)", "Md$", PALETTE[3], "Md$"),
    ]
    blocs = []
    for titre, cle, unite, couleur, _ in cartes:
        variation = ecart(derniere[cle], precedente[cle] if precedente is not None else None)
        valeur = f"{formater(derniere[cle])} {unite}"
        blocs.append(carte_kpi(titre, valeur, variation, unite, couleur))
    st.markdown(f'<div class="cartes">{"".join(blocs)}</div>', unsafe_allow_html=True)

    onglet_croissance, onglet_rentabilite, onglet_tresorerie, onglet_solidite, onglet_comparer = st.tabs(
        ["Croissance", "Rentabilité", "Trésorerie", "Solidité", "Comparer"]
    )
    with onglet_croissance:
        st.caption("Chiffre d'affaires et résultat net, en milliards de dollars. Survolez un exercice.")
        st.altair_chart(
            graphique_lignes(df.set_index("annee").reset_index(), ["Chiffre d'affaires (Md$)", "Résultat net (Md$)"],
                             "Md$", {"Chiffre d'affaires (Md$)": PALETTE[0], "Résultat net (Md$)": PALETTE[1]}),
            width="stretch",
        )
    with onglet_rentabilite:
        st.caption("Marge nette, ROE et ROA, en pourcentage.")
        st.altair_chart(
            graphique_lignes(df, ["Marge nette (%)", "ROE (%)", "ROA (%)"], "%",
                             {"Marge nette (%)": PALETTE[0], "ROE (%)": PALETTE[1], "ROA (%)": PALETTE[2]}),
            width="stretch",
        )
    with onglet_tresorerie:
        st.caption("Free cash flow par exercice, en milliards de dollars.")
        st.altair_chart(graphique_barres(df, "Free cash flow (Md$)", "Md$", couleurs[entreprise]), width="stretch")
    with onglet_solidite:
        st.caption("Deux ratios distincts, chacun dans son propre graphique.")
        gauche, droite = st.columns(2)
        with gauche:
            st.markdown("**Current ratio (x)**")
            st.altair_chart(graphique_barres(df, "Current ratio (x)", "x", PALETTE[2]), width="stretch")
        with droite:
            st.markdown("**Passif / capitaux propres (x)**")
            st.altair_chart(graphique_barres(df, "Passif / capitaux propres (x)", "x", PALETTE[4]), width="stretch")
    with onglet_comparer:
        choix = st.multiselect("Entreprises à comparer", entreprises, default=entreprises[:3])
        indicateur = st.selectbox(
            "Indicateur",
            [LIBELLES[c] for c in ["chiffre_affaires", *EN_POURCENTS, "current_ratio"]],
        )
        st.caption("Cliquez sur un nom dans la légende pour isoler une entreprise.")
        if choix:
            st.altair_chart(graphique_comparaison(periode, choix, indicateur, couleurs), width="stretch")
        else:
            st.info("Choisissez au moins une entreprise.")

    if afficher_tableau:
        st.subheader("Tableau des indicateurs")
        st.dataframe(tableau_lisible(df), width="stretch")
        st.caption(
            "Montants en milliards de dollars (Md$), taux en pourcentage, ratios sans unité (x). "
            "Un tiret signale une donnée absente dans le rapport."
        )

    with st.expander("Comprendre les indicateurs"):
        st.markdown("\n".join(f"- **{nom}** : {definition}" for nom, definition in DEFINITIONS))


if __name__ == "__main__":
    main()
