"""Interface FinSight AI : indicateurs financiers d'une entreprise, en tableau et en graphiques.

Lancement (depuis la racine du dépôt, environnement finsight actif) :
    streamlit run app.py

Les données viennent de data/gold/indicateurs.csv (produit par transform.gold). Si ce fichier
n'existe pas (par exemple sur le site publié), l'application lit la copie publique dans
donnees_publiques/indicateurs.csv. Les taux de change viennent de donnees_publiques/taux_change.csv.
Projet pédagogique : ces indicateurs ne constituent pas un conseil en investissement.
"""

import html
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from transform.devises import CHEMIN_TAUX, DEVISES, SYMBOLES, charger_taux, convertir_tableau

GOLD = Path("data/gold/indicateurs.csv")
GOLD_PUBLIC = Path("donnees_publiques/indicateurs.csv")
MILLIARD = 1e9
NOMBRE_D_EXERCICES_AFFICHES = 10

# Palettes catégorielles validées (skill dataviz, référence palette.md).
# L'ordre est fixe : une entreprise garde la même couleur quel que soit le filtre.
PALETTE_CLAIR = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
PALETTE_SOMBRE = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"]
GRIS_DISCRET = "#898781"

# Couleurs de texte et de fond, par mode.
MODES = {
    False: {"encre": "#0b0b0b", "encre_secondaire": "#52514e", "grille": "#e1e0d9", "axe": "#c3c2b7",
            "fond": "#fbf6ec", "palette": PALETTE_CLAIR, "vert": "#006300", "rouge": "#d03b3b"},
    True: {"encre": "#f0efec", "encre_secondaire": "#c3c2b7", "grille": "#2c2c2a", "axe": "#383835",
           "fond": "#1a1a19", "palette": PALETTE_SOMBRE, "vert": "#0ca30c", "rouge": "#e66767"},
}


def chemin_donnees():
    """Renvoie le fichier d'indicateurs à utiliser : local d'abord, public ensuite."""
    for chemin in (GOLD, GOLD_PUBLIC):
        if chemin.exists():
            return chemin
    return None


def libelles(symbole):
    """Libellés des colonnes, avec le symbole de la devise dans les montants (Md$ ou Md€)."""
    return {
        "chiffre_affaires": f"Chiffre d'affaires (Md{symbole})",
        "resultat_net": f"Résultat net (Md{symbole})",
        "total_actif": f"Total actif (Md{symbole})",
        "total_passif": f"Total passif (Md{symbole})",
        "free_cash_flow": f"Free cash flow (Md{symbole})",
        "marge_nette": "Marge nette (%)",
        "roe": "ROE (%)",
        "roa": "ROA (%)",
        # Le calcul est total passif / capitaux propres : le libellé le dit tel quel.
        "dette_sur_capitaux_propres": "Passif / capitaux propres (x)",
        "current_ratio": "Current ratio (x)",
        "croissance_ca": "Croissance du CA (%)",
    }


# Libellés en dollars, pour les appels qui ne précisent pas de devise.
LIBELLES = libelles("$")
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


def tableau_entreprise(gold, entreprise, devise="USD", taux=None):
    """Indicateurs d'une entreprise, par exercice, en milliards et en pourcentages, dans la devise demandée.

    Les montants sont convertis depuis la devise d'origine de la société (colonne 'devise' ; USD si absente).
    """
    df = gold[gold["entreprise"] == entreprise].sort_values("annee").copy()
    if "devise" not in df.columns:
        df["devise"] = "USD"
    if (df["devise"] != devise).any():
        df = convertir_tableau(df, devise, taux if taux is not None else charger_taux())
    for colonne in EN_MILLIARDS:
        df[colonne] = df[colonne] / MILLIARD
    for colonne in EN_POURCENTS:
        df[colonne] = df[colonne] * 100
    renommage = libelles(SYMBOLES[devise])
    return df[["annee", *renommage]].rename(columns=renommage).reset_index(drop=True)


def tableau_entreprise_brute(gold, entreprises, devise="USD", taux=None):
    """Lignes de plusieurs entreprises avec les unités d'affichage, sans les filtrer une à une."""
    morceaux = [tableau_entreprise(gold, nom, devise, taux).assign(entreprise=nom) for nom in entreprises]
    return pd.concat(morceaux, ignore_index=True)


def comparer(gold, entreprises, indicateur, devise="USD", taux=None):
    """Tableau années x entreprises pour comparer un indicateur (unités d'affichage)."""
    df = tableau_entreprise_brute(gold, entreprises, devise, taux)
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


def couleurs_entreprises(gold, sombre=False):
    """Attribue une couleur fixe à chaque entreprise, dans l'ordre alphabétique."""
    palette = MODES[sombre]["palette"]
    noms = sorted(gold["entreprise"].unique())
    return {nom: palette[i] if i < len(palette) else GRIS_DISCRET for i, nom in enumerate(noms)}


def habiller(graphique, sombre=False):
    """Style commun : fond transparent, grille discrète, texte lisible dans le mode choisi."""
    m = MODES[sombre]
    return (
        graphique.configure(background=m["fond"])
        .configure_view(stroke=None, fill=m["fond"] if sombre else None)
        # Axe horizontal : pas de trait ni de graduation, pas de grille verticale.
        .configure_axisX(
            domain=False, ticks=False, grid=False, labelPadding=10,
            labelColor=m["encre_secondaire"], titleColor=m["encre_secondaire"], labelFont="sans-serif",
        )
        # Axe vertical : grille horizontale très discrète, sans trait d'axe.
        .configure_axisY(
            domain=False, ticks=False, grid=True, gridColor=m["grille"], gridOpacity=0.5,
            labelPadding=10, labelColor=m["encre_secondaire"], titleColor=m["encre_secondaire"],
            labelFont="sans-serif",
        )
        .configure_legend(labelColor=m["encre_secondaire"], titleColor=m["encre_secondaire"], labelFont="sans-serif")
        .configure_mark(color=m["palette"][0])
    )


def libelle_court(libelle):
    """« Chiffre d'affaires (Md$) » -> « Chiffre d'affaires » : l'unité est dans le sous-titre."""
    return re.sub(r"\s*\((?:Md\S*|%|x)\)\s*$", "", libelle)


def axe_annees():
    """Une étiquette d'année sur trois, pour ne pas surcharger l'axe horizontal."""
    return alt.Axis(labelAngle=0, title=None, labelExpr="toNumber(datum.label) % 3 == 0 ? datum.label : ''")


def graphique_lignes(df, colonnes, unite, couleurs, sombre=False):
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
    # Pas de légende : chaque courbe porte son nom à sa dernière valeur.
    long["libelle"] = long["indicateur"].map(libelle_court)
    base = alt.Chart(long).encode(
        x=alt.X("annee:O", axis=axe_annees()),
        y=alt.Y("valeur:Q", title=None, axis=alt.Axis(format=",.0f")),
        color=alt.Color("indicateur:N", scale=echelle, legend=None),
    )
    lignes = base.mark_line(strokeWidth=2.2)
    points = base.mark_circle(size=70).encode(opacity=alt.condition(survol, alt.value(1), alt.value(0)))
    derniers = long.sort_values("annee").groupby("indicateur", as_index=False).tail(1)
    etiquettes = (
        alt.Chart(derniers)
        .mark_text(align="left", dx=10, fontWeight=600, fontSize=13)
        .encode(x=alt.X("annee:O"), y=alt.Y("valeur:Q"), text="libelle:N",
                color=alt.Color("indicateur:N", scale=echelle, legend=None))
    )
    repere = (
        alt.Chart(long).mark_rule(strokeWidth=1, color=GRIS_DISCRET)
        .encode(x="annee:O", opacity=alt.condition(survol, alt.value(0.8), alt.value(0)))
        .transform_filter(survol)
    )
    # Bande transparente par exercice : l'info-bulle liste toutes les séries à cette année.
    info = [alt.Tooltip("annee:O", title="Exercice")] + [
        alt.Tooltip(field=noms_sur[c], type="quantitative", title=c, format=",.1f") for c in colonnes
    ]
    bande = alt.Chart(d).mark_bar(opacity=0).encode(x=alt.X("annee:O"), tooltip=info)
    couche = alt.layer(lignes, points, repere, etiquettes, bande).add_params(survol)
    # Marge à droite pour que les étiquettes de fin de courbe tiennent dans le cadre.
    return habiller(couche.properties(height=320, padding={"left": 8, "right": 170, "top": 8, "bottom": 8}), sombre)


def graphique_barres(df, colonne, unite, couleur, sombre=False):
    """Barres par exercice, info-bulle au survol, extrémités arrondies."""
    d = df[["annee", colonne]].rename(columns={colonne: "valeur"})
    base = alt.Chart(d).encode(
        x=alt.X("annee:O", axis=axe_annees()),
        y=alt.Y("valeur:Q", title=None, axis=alt.Axis(format=",.1f")),
        tooltip=[alt.Tooltip("annee:O", title="Exercice"),
                 alt.Tooltip("valeur:Q", title=unite, format=",.1f")],
    )
    barres = base.mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color=couleur, opacity=0.9)
    return habiller(barres.properties(height=320), sombre)


def graphique_comparaison(gold, entreprises, indicateur, couleurs, sombre=False, devise="USD", taux=None):
    """Plusieurs entreprises ; cliquer une entreprise dans la légende isole sa courbe."""
    df = comparer(gold, entreprises, indicateur, devise, taux).reset_index().melt(
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
    return habiller(graphique.properties(height=360), sombre)


def carte_kpi(titre, valeur, variation, unite, couleur, sombre=False, manquant=False):
    """Carte d'indicateur : valeur, variation avec icône et libellé (jamais la couleur seule)."""
    if manquant:
        delta = '<span class="delta neutre">Donnée non disponible</span>'
    elif variation is None:
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
  .carte-valeur { font-size: 1.7rem; font-weight: 800; margin: 4px 0; white-space: nowrap; }
  .delta { font-size: 0.9rem; font-weight: 600; }
  .delta.hausse { color: var(--vert, #006300); }
  .delta.baisse { color: var(--rouge, #d03b3b); }
  .delta.neutre { opacity: 0.7; }
  @media (max-width: 800px) { .cartes { grid-template-columns: repeat(2, 1fr); } }
</style>
"""


def style_sombre(m):
    """Surcharge du thème clair : fond, texte et couleurs de l'application en mode sombre."""
    return f"""
<style>
  .stApp, [data-testid="stHeader"] {{ background-color: {m['fond']}; color: {m['encre']}; }}
  .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp span, .stApp li {{ color: {m['encre']}; }}
  .stApp [data-testid="stCaptionContainer"] p {{ color: {m['encre_secondaire']}; }}
  .stApp .stTabs [data-baseweb="tab"] {{ color: {m['encre_secondaire']}; }}
  .stApp .stTabs [aria-selected="true"] {{ color: {m['encre']}; }}
  .stApp [data-testid="stExpander"] {{ background-color: #242422; border-color: {m['grille']}; }}
  .stApp .chip {{ background: #242422; color: {m['encre']}; }}
  .stApp [data-testid="stSelectbox"] div, .stApp [data-testid="stMultiSelect"] div, .stApp [data-baseweb="select"] div {{ background-color: #242422 !important; color: {m['encre']} !important; }}
  .stApp [data-testid="stSelectbox"] input, .stApp [data-testid="stMultiSelect"] input {{ background-color: transparent !important; color: {m['encre']} !important; }}
  .stApp [data-baseweb="select"] svg {{ fill: {m['encre']} !important; }}
  .stApp [data-baseweb="tag"] {{ background-color: #3987e5; }}
  .stApp [data-baseweb="popover"] li, .stApp [data-baseweb="menu"] {{ background-color: #242422; color: {m['encre']}; }}
  :root {{ --vert: {m['vert']}; --rouge: {m['rouge']}; }}
</style>
"""


@st.cache_data
def taux_de_change():
    """Taux moyens annuels EUR/USD (lus une seule fois par session)."""
    return charger_taux(CHEMIN_TAUX)


def main():
    st.set_page_config(page_title="FinSight AI", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)

    fichier = chemin_donnees()
    if fichier is None:
        st.error(
            "Pas encore de données. Dans le terminal, depuis la racine du dépôt : "
            "python run_pipeline.py MSFT AAPL GOOGL, puis python -m transform.silver, "
            "puis python -m transform.gold."
        )
        st.stop()

    gold = pd.read_csv(fichier)
    if "devise" not in gold.columns:
        gold["devise"] = "USD"
    entreprises = sorted(gold["entreprise"].unique())

    # Filtres et affichage : une seule rangée, au-dessus de tout le contenu.
    col_entreprise, col_periode, col_devise, col_tableau, col_sombre = st.columns([2.0, 2.4, 1.1, 1.8, 1.7])
    with col_entreprise:
        entreprise = st.selectbox("Entreprise", entreprises)
    annees = sorted(gold.loc[gold["entreprise"] == entreprise, "annee"].unique())
    with col_periode:
        if len(annees) > 1:
            lo, hi = st.select_slider("Période", options=annees, value=(annees[0], annees[-1]))
        else:
            lo = hi = annees[0]
            st.caption(f"Un seul exercice disponible : {annees[0]}")
    with col_devise:
        devise = st.selectbox("Devise", list(DEVISES), format_func=lambda d: f"{d} ({SYMBOLES[d]})")
    with col_tableau:
        afficher_tableau = st.toggle("Voir le tableau", value=False)
    with col_sombre:
        sombre = st.toggle("Mode sombre", value=False)

    m = MODES[sombre]
    couleurs = couleurs_entreprises(gold, sombre)
    pal = m["palette"]
    sym = SYMBOLES[devise]
    L = libelles(sym)
    taux = taux_de_change()
    if sombre:
        st.markdown(style_sombre(m), unsafe_allow_html=True)
    st.markdown(
        """
        <div class="entete">
          <h1>FinSight AI</h1>
          <p>Les indicateurs financiers annuels d'une entreprise, calculés à partir de ses rapports
          officiels (SEC pour les États-Unis, AMF pour la France). Projet pédagogique : ce n'est pas un conseil en investissement.</p>
          <div class="chips">
            <span class="chip">Sources : SEC EDGAR et AMF (ESEF)</span>
            <span class="chip">Rapports annuels 10-K et ESEF</span>
            <span class="chip">Montants en {devise} (taux moyens BCE)</span>
          </div>
        </div>
        """.replace("{devise}", devise),
        unsafe_allow_html=True,
    )

    periode = gold[(gold["annee"] >= lo) & (gold["annee"] <= hi)]
    df = tableau_entreprise(periode, entreprise, devise, taux)
    if df.empty:
        st.info("Aucun exercice disponible pour cette entreprise sur cette période.")
        st.stop()

    origine = gold.loc[gold["entreprise"] == entreprise, "devise"].iloc[0]
    derniere = df.iloc[-1]
    precedente = df.iloc[-2] if len(df) > 1 else None
    st.subheader(f"{entreprise} · exercice {int(derniere['annee'])}")
    if origine != devise:
        st.caption(
            f"Montants convertis de {origine} vers {devise} au taux moyen annuel de la BCE. "
            "Les ratios ne changent pas avec la devise."
        )
    else:
        st.caption("Variation par rapport à l'exercice précédent")
    cartes = [
        ("Chiffre d'affaires", L["chiffre_affaires"], f"Md{sym}", pal[0]),
        ("Marge nette", L["marge_nette"], "%", pal[1]),
        ("ROE", L["roe"], "%", pal[2]),
        ("Free cash flow", L["free_cash_flow"], f"Md{sym}", pal[3]),
    ]
    blocs = []
    for titre, cle, unite, couleur in cartes:
        variation = ecart(derniere[cle], precedente[cle] if precedente is not None else None)
        valeur = f"{formater(derniere[cle])} {unite}"
        blocs.append(carte_kpi(titre, valeur, variation, unite, couleur, sombre,
                               manquant=pd.isna(derniere[cle])))
    st.markdown(f'<div class="cartes">{"".join(blocs)}</div>', unsafe_allow_html=True)

    onglet_croissance, onglet_rentabilite, onglet_tresorerie, onglet_solidite, onglet_comparer = st.tabs(
        ["Croissance", "Rentabilité", "Trésorerie", "Solidité", "Comparer"]
    )
    with onglet_croissance:
        st.caption(f"Chiffre d'affaires et résultat net, en milliards de {devise}. Survolez un exercice.")
        st.altair_chart(
            graphique_lignes(df, [L["chiffre_affaires"], L["resultat_net"]], f"Md{sym}",
                             {L["chiffre_affaires"]: pal[0], L["resultat_net"]: pal[1]}, sombre),
            width="stretch",
        )
    with onglet_rentabilite:
        st.caption("Marge nette, ROE et ROA, en pourcentage.")
        st.altair_chart(
            graphique_lignes(df, [L["marge_nette"], L["roe"], L["roa"]], "%",
                             {L["marge_nette"]: pal[0], L["roe"]: pal[1], L["roa"]: pal[2]}, sombre),
            width="stretch",
        )
    with onglet_tresorerie:
        st.caption(f"Free cash flow par exercice, en milliards de {devise}. Vide pour les sociétés françaises (voir la documentation).")
        st.altair_chart(graphique_barres(df, L["free_cash_flow"], f"Md{sym}", couleurs[entreprise], sombre),
                        width="stretch")
    with onglet_solidite:
        st.caption("Deux ratios distincts, chacun dans son propre graphique.")
        gauche, droite = st.columns(2)
        with gauche:
            st.markdown(f"**{L['current_ratio']}**")
            st.altair_chart(graphique_barres(df, L["current_ratio"], "x", pal[2], sombre), width="stretch")
        with droite:
            st.markdown(f"**{L['dette_sur_capitaux_propres']}**")
            st.altair_chart(graphique_barres(df, L["dette_sur_capitaux_propres"], "x", pal[4], sombre),
                            width="stretch")
    with onglet_comparer:
        choix = st.multiselect("Entreprises à comparer", entreprises, default=entreprises[:3])
        indicateur = st.selectbox(
            "Indicateur",
            [L[c] for c in ["chiffre_affaires", *EN_POURCENTS, "current_ratio"]],
        )
        st.caption("Cliquez sur un nom dans la légende pour isoler une entreprise.")
        if choix:
            st.altair_chart(
                graphique_comparaison(periode, choix, indicateur, couleurs, sombre, devise, taux),
                width="stretch",
            )
        else:
            st.info("Choisissez au moins une entreprise.")

    if afficher_tableau:
        st.subheader("Tableau des indicateurs")
        tableau = tableau_lisible(df)
        if sombre:
            tableau = tableau.style.set_properties(**{"background-color": "#242422", "color": m["encre"]})
        st.dataframe(tableau, width="stretch")
        st.caption(
            f"Montants en milliards de {devise} (Md{sym}), taux en pourcentage, ratios sans unité (x). "
            "Un tiret signale une donnée absente dans le rapport."
        )

    with st.expander("Comprendre les indicateurs"):
        st.markdown("\n".join(f"- **{nom}** : {definition}" for nom, definition in DEFINITIONS))


if __name__ == "__main__":
    main()
