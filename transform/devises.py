"""Conversion des montants entre dollar (USD) et euro (EUR).

Taux : moyenne annuelle publiée par la BCE (dollars pour un euro), fichier
donnees_publiques/taux_change.csv. Une même moyenne annuelle sert à tous les montants de
l'exercice, bilan compris : c'est une approximation, à mentionner dans l'interface.
Les ratios (marge, ROE, current ratio...) ne dépendent pas de la devise et ne sont pas convertis.
"""

from pathlib import Path

import pandas as pd

CHEMIN_TAUX = Path("donnees_publiques/taux_change.csv")
DEVISES = ("USD", "EUR")
SYMBOLES = {"USD": "$", "EUR": "€"}
# Colonnes de la couche gold qui sont des montants (et donc à convertir).
COLONNES_MONTANTS = [
    "chiffre_affaires", "resultat_net", "total_actif", "total_passif", "capitaux_propres",
    "actif_courant", "passif_courant", "flux_operationnel", "investissements", "free_cash_flow",
]


def charger_taux(chemin=CHEMIN_TAUX):
    """Renvoie un dictionnaire {année: dollars pour un euro}."""
    table = pd.read_csv(chemin)
    return dict(zip(table["annee"].astype(int), table["taux_usd_par_eur"].astype(float)))


def convertir_montant(valeur, de, vers, annee, taux):
    """Convertit un montant d'une devise à une autre, au taux moyen de l'année."""
    if pd.isna(valeur) or de == vers:
        return valeur
    if annee not in taux:
        raise KeyError(f"pas de taux de change pour {annee}")
    if de == "USD" and vers == "EUR":
        return valeur / taux[annee]
    if de == "EUR" and vers == "USD":
        return valeur * taux[annee]
    raise ValueError(f"conversion non prise en charge : {de} -> {vers}")


def convertir_tableau(df, vers, taux):
    """Convertit les montants d'un tableau d'indicateurs vers la devise demandée.

    Le tableau doit avoir une colonne 'devise' (devise d'origine de chaque ligne) et 'annee'.
    Les colonnes qui ne sont pas des montants restent inchangées.
    """
    converti = df.copy()
    for colonne in COLONNES_MONTANTS:
        if colonne not in converti.columns:
            continue
        converti[colonne] = [
            convertir_montant(valeur, de, vers, int(annee), taux)
            for valeur, de, annee in zip(converti[colonne], converti["devise"], converti["annee"])
        ]
    converti["devise"] = vers
    return converti
