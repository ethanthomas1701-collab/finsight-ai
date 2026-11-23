# FinSight AI

Plateforme d'analyse financière des grandes entreprises cotées, construite à partir des données publiques de la SEC (EDGAR). Un pipeline de données récupère les états financiers, les nettoie, calcule des indicateurs, contrôle leur qualité, puis les présente dans une interface web et un assistant.

> **Projet pédagogique.** Les indicateurs présentés ne constituent pas un conseil en investissement.

## Ce que fait le projet

- **Collecte** : récupère les données brutes d'une entreprise à partir de son ticker (ex. `MSFT`), via l'API officielle de la SEC.
- **Nettoyage** : ne garde que les rapports annuels (10-K), supprime les doublons entre exercices, et choisit le bon nom de poste comptable selon les années.
- **Indicateurs** : marge nette, ROE, ROA, endettement, croissance du chiffre d'affaires, current ratio, free cash flow.
- **Contrôles de qualité** : signale les exercices manquants, les données absentes et les valeurs inhabituelles, sans les corriger.
- **Interface web** : tableau, graphiques et comparaison entre entreprises.
- **Assistant** : répond à des questions en français à partir de la base. Il ne génère jamais de SQL : il choisit parmi des requêtes autorisées.

## Architecture

```
SEC EDGAR (API)
     │
     ▼
bronze   data/bronze/      JSON brut, sans transformation, daté
     │  transform/silver.py
     ▼
silver   data/silver/      un tableau annuel propre par entreprise
     │  transform/gold.py
     ▼
gold     data/gold/        indicateurs financiers
     │  transform/qualite.py          transform/stockage.py
     ▼                                  ▼
qualité  anomalies          SQLite  data/finsight.db
                                        │
                  ┌─────────────────────┴──────────────────┐
                  ▼                                        ▼
          app.py (Streamlit)                 assistant/ (requêtes autorisées)
          interface web                      + modèle local Ollama ou repli sans modèle
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
# 1. Collecter et nettoyer les données (une ou plusieurs entreprises)
python run_pipeline.py MSFT AAPL GOOGL AMZN NVDA META

# 2. Calculer les indicateurs, contrôler la qualité, stocker dans SQLite
python -m transform.gold
python -m transform.qualite
python -m transform.stockage

# 3. Lancer l'interface web
streamlit run app.py

# 4. Poser une question à l'assistant (nécessite Ollama avec le modèle qwen2.5:3b)
python -m assistant.agent_local "Comment a évolué la marge nette d'Apple ?"
```

Le site publié utilise les tableaux du dossier `donnees_publiques/`, qui sont des données dérivées de sources publiques.

## Tests

```bash
python -m pytest -v
```

Les tests ne font aucun appel réseau : les données de la SEC sont simulées.

## Structure du dépôt

| Dossier | Contenu |
|---|---|
| `ingestion/` | Connecteur SEC : récupération et sauvegarde brute |
| `transform/` | Couches silver, gold, contrôles de qualité et stockage SQLite |
| `assistant/` | Requêtes autorisées et assistant (modèle local ou repli sans modèle) |
| `app.py` | Interface Streamlit |
| `tests/` | Tests `pytest` |
| `donnees_publiques/` | Tableaux finaux publiés avec le site |

## Choix techniques

- **Pourquoi garder la donnée brute ?** Pour pouvoir rejouer les transformations sans rappeler la SEC, et pour retrouver la source d'un chiffre.
- **Pourquoi plusieurs noms de concepts ?** Les entreprises ne publient pas toujours le même poste sous le même nom. Le chiffre d'affaires de Microsoft n'a pas le même nom selon les années, par exemple.
- **Pourquoi un assistant qui ne génère pas de SQL ?** Un modèle de langage peut inventer une requête incorrecte ou dangereuse. Ici, il ne fait que choisir une question parmi une liste fixe.
- **Pourquoi signaler les anomalies sans les corriger ?** Une valeur inhabituelle est souvent réelle : NVIDIA a bien vu son chiffre d'affaires doubler en 2024. Le contrôle sert à la vérifier, pas à la masquer.

## Limites

- Le périmètre se limite aux entreprises américaines publiant à la SEC, et aux données présentes dans leurs rapports.
- Les premiers exercices n'ont pas toujours de bilan complet (total actif ou passif absent).
- Le total passif est déduit de l'identité du bilan lorsque le poste direct manque. Cette déduction inclut les intérêts minoritaires.
- Les cours de bourse ne sont pas inclus : ils ne proviennent pas d'EDGAR.
- L'assistant local répond moins bien qu'un grand modèle, et peut parfois ne rien répondre. Un repli sans modèle prend alors le relais pour les questions simples.

## Feuille de route

- [x] Collecte et nettoyage (phase 1)
- [x] Indicateurs et interface web (phase 2)
- [x] Contrôles de qualité et stockage SQLite (phase 3)
- [x] Assistant avec requêtes autorisées (phase 4, sans API payante)
- [ ] Option assistant avec un modèle Claude payant
- [ ] RAG sur les rapports annuels en PDF
- [ ] Démonstration vidéo et déploiement public

## Auteur

Projet réalisé par Ethan Thomas, dans le cadre de ma préparation à une alternance en data engineering et intelligence artificielle.
