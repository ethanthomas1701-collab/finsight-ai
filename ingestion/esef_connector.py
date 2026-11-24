"""Connecteur ESEF : rapports annuels des sociétés cotées en France (AMF), format iXBRL.

Chaîne :
1. l'API info-financière de l'AMF liste les dépôts d'une société (par ISIN) ;
2. on garde les documents annuels (archive .zip ou .xbri) ;
3. on lit le rapport XHTML balisé en iXBRL et on extrait les faits chiffrés IFRS.

Les données sont brutes : aucune correspondance d'indicateurs ici (c'est le rôle de transform/).
"""

import html
import logging
import re
import time
import zipfile
from datetime import date
from io import BytesIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)

API_DEPOTS = "https://www.info-financiere.gouv.fr/api/explore/v2.1/catalog/datasets/flux-amf-new-prod/records"
DELAI = 60  # secondes
NOMBRE_MAX_DEPOTS = 100
EXTENSIONS_ANNUELLES = (".zip", ".xbri")

# Les attributs peuvent être entre guillemets doubles ou simples selon l'éditeur du rapport.
_RE_CONTEXTE = re.compile(r"<xbrli:context\s+id=([\"'])(.*?)\1\s*>(.*?)</xbrli:context>", re.S)
_RE_FAIT = re.compile(r"<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>", re.S)
_RE_ATTR = re.compile(r"([\w:.-]+)=([\"'])(.*?)\2")
_RE_BALISE = re.compile(r"<[^>]+>")


class EsefError(Exception):
    """Erreur de lecture d'un rapport ESEF ou de l'API de l'AMF."""


def _get(url, **options):
    """GET avec trois tentatives espacées, pour surmonter une coupure réseau passagère."""
    derniere_erreur = None
    for essai in range(1, 4):
        try:
            reponse = requests.get(url, timeout=DELAI, **options)
            reponse.raise_for_status()
            return reponse
        except requests.RequestException as erreur:
            derniere_erreur = erreur
            logger.warning("essai %d échoué (%s), nouvel essai", essai, erreur)
            time.sleep(10 * essai)
    raise EsefError(f"réseau indisponible après 3 essais : {derniere_erreur}")


def trouver_depots_annuels(isin):
    """Renvoie les dépôts annuels (rapports financiers) d'une société, du plus récent au plus ancien."""
    if not isin:
        raise EsefError("ISIN manquant")
    where = (
        f'identificationsociete_iso_cd_isi="{isin}" AND '
        '(informationdeposee_inf_tit_inf like "%universel%" OR informationdeposee_inf_tit_inf like "%annuel%" '
        'OR informationdeposee_inf_tit_inf like "%universal%")'
    )
    reponse = _get(
        API_DEPOTS,
        params={"where": where, "limit": NOMBRE_MAX_DEPOTS, "order_by": "uin_dat_amf desc",
                "select": "uin_dat_amf,informationdeposee_inf_tit_inf,url_de_recuperation"},
    )

    depots = []
    for enregistrement in reponse.json().get("results", []):
        url = enregistrement.get("url_de_recuperation") or ""
        if url.lower().endswith(EXTENSIONS_ANNUELLES):
            depots.append({
                "date_depot": enregistrement.get("uin_dat_amf"),
                "titre": enregistrement.get("informationdeposee_inf_tit_inf"),
                "url": url,
            })
    return depots


def telecharger(url):
    """Télécharge un document et renvoie son contenu brut."""
    return _get(url).content


def rapport_xhtml(contenu_archive):
    """Extrait le rapport XHTML principal d'une archive ESEF (.zip ou .xbri)."""
    try:
        with zipfile.ZipFile(BytesIO(contenu_archive)) as archive:
            candidats = [n for n in archive.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))
                         and "/reports/" in "/" + n.lower()]
            if not candidats:
                candidats = [n for n in archive.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))]
            if not candidats:
                raise EsefError("aucun rapport XHTML dans l'archive")
            return archive.read(max(candidats, key=lambda n: archive.getinfo(n).file_size)).decode("utf-8", "replace")
    except zipfile.BadZipFile as erreur:
        raise EsefError("archive ESEF illisible") from erreur


def lire_contextes(texte):
    """Associe chaque identifiant de contexte à sa période et indique s'il porte une dimension.

    Une dimension (segment, zone géographique, activité...) signale un détail, pas le total consolidé.
    """
    contextes = {}
    for _guillemet, identifiant, corps in _RE_CONTEXTE.findall(texte):
        debut = re.search(r"<xbrli:startDate>([^<]+)</xbrli:startDate>", corps)
        fin = re.search(r"<xbrli:endDate>([^<]+)</xbrli:endDate>", corps)
        instant = re.search(r"<xbrli:instant>([^<]+)</xbrli:instant>", corps)
        contextes[identifiant] = {
            "debut": date.fromisoformat(debut.group(1).strip()) if debut else None,
            "fin": date.fromisoformat((fin or instant).group(1).strip()) if (fin or instant) else None,
            "dimensions": "explicitMember" in corps or "typedMember" in corps,
        }
    return contextes


def valeur_numerique(attributs, texte):
    """Convertit le texte balisé en nombre, en tenant compte du format, de l'échelle et du signe."""
    brut = html.unescape(_RE_BALISE.sub("", texte)).strip()  # &#xa0; -> espace insécable
    if attributs.get("format", "").endswith("zero") or brut in ("-", "—", ""):
        valeur = 0.0
    else:
        separateur_decimal = "," if "comma-decimal" in attributs.get("format", "") else "."
        propre = re.sub(r"[\s  ]", "", brut)
        if separateur_decimal == ",":
            propre = propre.replace(".", "").replace(",", ".")
        else:
            propre = propre.replace(",", "")
        valeur = float(propre)
    echelle = int(attributs.get("scale", "0") or 0)
    valeur *= 10 ** echelle
    if attributs.get("sign") == "-":
        valeur = -valeur
    return valeur


def extraire_faits(texte, prefixe="ifrs-full"):
    """Renvoie les faits chiffrés consolidés (sans dimension) du préfixe donné, sous forme de DataFrame."""
    contextes = lire_contextes(texte)
    lignes = []
    for attributs_brut, corps in _RE_FAIT.findall(texte):
        attributs = {nom: valeur for nom, _guillemet, valeur in _RE_ATTR.findall(attributs_brut)}
        concept = attributs.get("name", "")
        if not concept.startswith(prefixe + ":"):
            continue
        contexte = contextes.get(attributs.get("contextRef", ""))
        if contexte is None or contexte["dimensions"] or contexte["fin"] is None:
            continue
        try:
            valeur = valeur_numerique(attributs, corps)
        except ValueError:
            logger.warning("valeur non lisible pour %s : %r", concept, corps[:40])
            continue
        lignes.append({
            "concept": concept.split(":", 1)[1],
            "debut": contexte["debut"],
            "fin": contexte["fin"],
            "valeur": valeur,
            "unite": attributs.get("unitRef", ""),
        })
    faits = pd.DataFrame(lignes, columns=["concept", "debut", "fin", "valeur", "unite"])
    return faits.drop_duplicates(subset=["concept", "debut", "fin"]).reset_index(drop=True)


def extraire_societe(isin, nombre_max=None):
    """Télécharge et lit les rapports annuels d'une société. Renvoie les faits empilés, une colonne 'depot'."""
    depots = trouver_depots_annuels(isin)
    if nombre_max is not None:
        depots = depots[:nombre_max]
    morceaux = []
    for depot in depots:
        try:
            texte = rapport_xhtml(telecharger(depot["url"]))
            faits = extraire_faits(texte)
        except EsefError as erreur:
            logger.warning("dépôt ignoré (%s) : %s", depot["url"], erreur)
            continue
        if faits.empty:
            logger.warning("aucun fait IFRS lisible dans %s", depot["url"])
            continue
        faits["depot"] = depot["url"].rsplit("/", 1)[-1]
        morceaux.append(faits)
    if not morceaux:
        raise EsefError(f"aucun rapport annuel lisible pour {isin}")
    # Les dépôts arrivent du plus récent au plus ancien : on garde la première valeur trouvée
    # pour chaque (concept, période), c'est-à-dire la version retraitée la plus récente.
    empile = pd.concat(morceaux, ignore_index=True)
    return empile.drop_duplicates(subset=["concept", "debut", "fin"], keep="first").reset_index(drop=True)
