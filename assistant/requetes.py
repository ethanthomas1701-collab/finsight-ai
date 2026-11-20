"""Requêtes contrôlées pour l'assistant financier : lecture seule, colonnes autorisées.

Principe de sécurité : le modèle de langage ne génère jamais de SQL. Il choisit une question
parmi celles prévues ici, avec une entreprise et un indicateur de la liste autorisée.
La base est ouverte en lecture seule.

Ce module ne dépend d'aucune API externe : il peut être testé et utilisé seul.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

BASE = Path("data/finsight.db")
TABLE = "gold_indicateurs"

INDICATEURS_AUTORISES = {
    "chiffre_affaires",
    "resultat_net",
    "total_actif",
    "total_passif",
    "free_cash_flow",
    "marge_nette",
    "roe",
    "roa",
    "dette_sur_capitaux_propres",
    "current_ratio",
    "croissance_ca",
}


class RequeteRefusee(ValueError):
    """Levée quand une demande sort du cadre autorisé (indicateur ou entreprise inconnus)."""


def connexion_lecture(base=BASE):
    """Ouvre la base SQLite en lecture seule. Erreur claire si elle n'existe pas."""
    chemin = Path(base)
    if not chemin.exists():
        raise FileNotFoundError(f"Base absente : {chemin}. Lancer python -m transform.stockage.")
    return sqlite3.connect(f"file:{chemin.as_posix()}?mode=ro", uri=True)


def verifier_indicateur(indicateur):
    if indicateur not in INDICATEURS_AUTORISES:
        raise RequeteRefusee(f"Indicateur non autorisé : {indicateur!r}")


def evolution(entreprise, indicateur, base=BASE):
    """Valeurs d'un indicateur, par exercice, pour une entreprise (requête fixe, paramétrée)."""
    verifier_indicateur(indicateur)
    sql = f"SELECT annee, {indicateur} FROM {TABLE} WHERE entreprise = ? ORDER BY annee"
    with closing(connexion_lecture(base)) as connexion:
        df = pd.read_sql(sql, connexion, params=(entreprise,))
    if df.empty:
        raise RequeteRefusee(f"Entreprise inconnue : {entreprise!r}")
    return df


def comparer(entreprises, indicateur, annee, base=BASE):
    """Valeur d'un indicateur pour plusieurs entreprises, une année donnée."""
    verifier_indicateur(indicateur)
    marques = ", ".join("?" for _ in entreprises)
    sql = (
        f"SELECT entreprise, {indicateur} FROM {TABLE} "
        f"WHERE annee = ? AND entreprise IN ({marques}) ORDER BY entreprise"
    )
    with closing(connexion_lecture(base)) as connexion:
        return pd.read_sql(sql, connexion, params=(annee, *entreprises))


MONTANTS = {"chiffre_affaires", "resultat_net", "total_actif", "total_passif", "free_cash_flow"}
POURCENTAGES = {"marge_nette", "roe", "roa", "croissance_ca"}


def formater(indicateur, valeur):
    """Affiche une valeur dans l'unité attendue : milliards de dollars, %, ou ratio."""
    if indicateur in MONTANTS:
        return f"{valeur / 1e9:,.1f} Md$".replace(",", " ")
    if indicateur in POURCENTAGES:
        return f"{valeur:.1%}"
    return f"{valeur:.2f}"


def phrase_evolution(df, entreprise, indicateur):
    """Une réponse en français, avec les chiffres et les années. Signale les trous."""
    valides = df.dropna(subset=[indicateur])
    if len(valides) < 2:
        return (
            f"Données insuffisantes pour décrire l'évolution de {indicateur} pour {entreprise} "
            f"({len(valides)} exercice(s) disponible(s))."
        )
    debut, fin = valides.iloc[0], valides.iloc[-1]
    variation = (fin[indicateur] - debut[indicateur]) / abs(debut[indicateur])
    sens = "augmente" if variation > 0 else "diminue"
    phrase = (
        f"Pour {entreprise}, {indicateur} {sens} de {formater(indicateur, debut[indicateur])} "
        f"en {int(debut['annee'])} à {formater(indicateur, fin[indicateur])} en {int(fin['annee'])} "
        f"(variation de {variation:+.0%})."
    )
    manquantes = df[df[indicateur].isna()]["annee"].astype(int).tolist()
    if manquantes:
        phrase += f" Valeurs absentes pour : {', '.join(map(str, manquantes))}."
    return phrase
