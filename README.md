# FinSight AI

Plateforme d'analyse financière de grandes entreprises cotées, construite à partir de données publiques : les rapports déposés à la **SEC** (États-Unis, format XBRL us-gaap) et les rapports déposés à l'**AMF** (France, format ESEF / IFRS, iXBRL). Un pipeline de données récupère les états financiers, les nettoie, calcule des indicateurs, contrôle leur qualité, puis les présente dans une interface web et un assistant.

> **Projet pédagogique.** Les indicateurs présentés ne constituent pas un conseil en investissement.

## Ce que fait le projet

- **Collecte** :
  - sociétés américaines à partir de leur ticker (ex. `MSFT`), via l'API de la SEC ;
  - sociétés du CAC 40 déposées à l'AMF (34 sociétés), via l'API info-financière de l'AMF.
- **Nettoyage** : ne garde que les rapports annuels, supprime les doublons entre exercices, garde la version la plus récente de chaque exercice (retraitements).
- **Indicateurs** : marge nette, ROE, ROA, passif sur capitaux propres, croissance du chiffre d'affaires, current ratio, free cash flow.
- **Devises** : montants en dollars ou en euros, au choix dans l'interface. Conversion au taux moyen annuel de la BCE, dans les deux sens.
- **Contrôles de qualité** : signalent les exercices manquants, les données absentes et les valeurs inhabituelles, sans les corriger.
- **Interface web** : tableau, graphiques, comparaison entre entreprises, mode sombre.
- **Assistant** : répond à des questions en français à partir de la base. Il ne génère jamais de SQL : il choisit parmi des requêtes autorisées.

## Architecture

```
SEC EDGAR (API)                              AMF (API info-financière, rapports ESEF)
     │                                              │
     ▼                                              ▼
bronze   data/bronze/          JSON brut      data/bronze/esef/   faits iXBRL bruts
     │  transform/silver.py                          │  transform/silver_esef.py
     ▼                                              ▼
silver   data/silver/CIK<cik>.csv             data/silver/CIK<ISIN>.csv
     └──────────────────────┬──────────────────────┘
                            │  transform/gold.py  (indicateurs, devise d'origine)
                            ▼
gold     data/gold/indicateurs.csv
     │  transform/qualite.py          transform/stockage.py
     ▼                                  ▼
qualité  anomalies          SQLite  data/finsight.db
                                        │
                  ┌─────────────────────┴────────────────────┐
                  ▼                                          ▼
          app.py (Streamlit)                 assistant/ (requêtes autorisées)
          interface web, devise choisie      + modèle local Ollama ou repli sans modèle
```

## Installation

Prérequis : Python 3.12, et une installation d'Anaconda ou de Miniconda.

```bash
conda create -n finsight python=3.12 -y
conda activate finsight
pip install -r requirements.txt
```

La SEC demande un contact dans chaque requête. Définissez-le dans une variable d'environnement, jamais dans le code :

```bash
setx SEC_USER_AGENT "Prénom Nom votre-adresse@exemple.com"
```

Fermez puis rouvrez le terminal après cette commande.

## Utilisation

Depuis la racine du dépôt, avec l'environnement `finsight` actif :

```bash
# 1. Sociétés américaines (SEC) : collecter et nettoyer
python run_pipeline.py MSFT AAPL GOOGL AMZN NVDA META

# 2. Sociétés françaises (AMF, ESEF) : collecter les rapports annuels du CAC 40
python run_esef.py

# 3. Calculer les indicateurs, contrôler la qualité, stocker dans SQLite
python -m transform.gold
python -m transform.qualite
python -m transform.stockage

# 4. Lancer l'interface web
streamlit run app.py

# 5. Poser une question à l'assistant (nécessite Ollama avec le modèle qwen2.5:3b)
python -m assistant.agent_local "Comment a évolué la marge nette d'Apple ?"
```

**Site en ligne** : [finsight-ai-kk4oydvx53venocvf2ebsw.streamlit.app](https://finsight-ai-kk4oydvx53venocvf2ebsw.streamlit.app/). Il utilise les tableaux du dossier `donnees_publiques/` (indicateurs, qualité, taux de change), qui sont des données dérivées de sources publiques. L'assistant en langage naturel n'y est pas disponible : il tourne en local avec Ollama.

## Tests

```bash
python -m pytest -v
```

Les tests ne font aucun appel réseau : les données de la SEC et de l'AMF sont simulées ou construites à la main.

## Structure du dépôt

| Dossier ou fichier | Contenu |
|---|---|
| `ingestion/sec_connector.py` | Connecteur SEC : récupération et sauvegarde brute |
| `ingestion/esef_connector.py` | Connecteur AMF : rapports annuels ESEF et lecture iXBRL |
| `transform/` | Couches silver (SEC et IFRS), gold, devises, contrôles de qualité, stockage SQLite |
| `assistant/` | Requêtes autorisées et assistant (modèle local ou repli sans modèle) |
| `run_pipeline.py` | Collecte et couche silver pour les sociétés américaines |
| `run_esef.py` | Collecte et couche silver pour les sociétés du CAC 40 |
| `app.py` | Interface Streamlit |
| `tests/` | Tests `pytest` (96 tests) |
| `donnees_publiques/` | Tableaux finaux publiés avec le site, et taux de change BCE |

## Choix techniques

- **Pourquoi garder la donnée brute ?** Pour pouvoir rejouer les transformations sans rappeler la SEC ou l'AMF, et pour retrouver la source d'un chiffre.
- **Pourquoi plusieurs noms de concepts ?** Les entreprises ne publient pas toujours le même poste sous le même nom. Le chiffre d'affaires de Microsoft n'a pas le même nom selon les années, et les sociétés françaises utilisent les normes IFRS, dont les noms diffèrent de ceux des États-Unis.
- **Pourquoi un fichier `CIK<ISIN>.csv` pour les sociétés françaises ?** Il suit la convention des sociétés américaines, pour que la couche gold traite les deux pays de la même façon.
- **Pourquoi un taux moyen annuel pour toute la devise ?** C'est simple et public (taux BCE). Une approche plus fine utiliserait le taux de clôture pour le bilan : c'est une amélioration possible.
- **Pourquoi un assistant qui ne génère pas de SQL ?** Un modèle de langage peut inventer une requête incorrecte ou dangereuse. Ici, il ne fait que choisir une question parmi une liste fixe.
- **Pourquoi signaler les anomalies sans les corriger ?** Une valeur inhabituelle est souvent réelle : NVIDIA a bien vu son chiffre d'affaires doubler en 2024. Le contrôle sert à la vérifier, pas à la masquer.

## Limites

- **Périmètre** : les sociétés américaines (SEC) et les sociétés du CAC 40 déposées à l'AMF. Airbus, STMicroelectronics, Stellantis, Euronext, ArcelorMittal et Eurofins déposent aux Pays-Bas ou au Luxembourg : elles sont exclues.
- **Composition du CAC 40** : la liste vient d'un article de référence (27/10/2026), pas directement d'Euronext, dont la page est protégée. Les ISIN n'ont pas été vérifiés sur Euronext.
- **Historique** : l'ESEF s'applique depuis l'exercice 2020, donc les sociétés françaises ont 5 à 8 exercices, contre près de 20 pour les sociétés américaines.
- **Free cash flow absent pour les sociétés françaises** : il n'existe pas de concept IFRS fiable pour les investissements.
- **Chiffre d'affaires absent** pour les banques, les assurances et quelques autres sociétés (Sanofi, Unibail-Rodamco-Westfield) : elles n'ont pas de poste de chiffre d'affaires standard.
- **Devises** : les montants sont convertis au taux moyen annuel de la BCE. Les ratios ne changent pas.
- **Premiers exercices** : pour certaines sociétés américaines, le bilan est incomplet (total actif ou passif absent).
- **Passif déduit** : lorsque le poste direct manque, le total passif est déduit de l'identité du bilan. Cette déduction inclut les intérêts minoritaires.
- **Cours de bourse** : non inclus, ils ne proviennent ni de la SEC ni de l'AMF.
- **Assistant** : le modèle local répond moins bien qu'un grand modèle, et peut ne rien répondre. Un repli sans modèle prend alors le relais pour les questions simples.

## Feuille de route

- [x] Collecte et nettoyage, sociétés américaines (phase 1)
- [x] Indicateurs et interface web (phase 2)
- [x] Contrôles de qualité et stockage SQLite (phase 3)
- [x] Assistant avec requêtes autorisées (phase 4, sans API payante)
- [x] Sociétés du CAC 40 déposées à l'AMF (lecture ESEF / IFRS)
- [x] Conversion dollar / euro avec choix de la devise
- [ ] Option assistant avec un modèle Claude payant
- [ ] RAG sur les rapports annuels en PDF
- [ ] Vérification des ISIN et de la composition du CAC 40 sur Euronext
- [ ] Démonstration vidéo et déploiement public

## Auteur

Projet réalisé par Ethan Thomas, dans le cadre de ma préparation à une alternance en data engineering et intelligence artificielle.
