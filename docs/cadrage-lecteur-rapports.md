# Cadrage : lecteur de rapports annuels

## Idée

L'utilisateur pose une question sur le rapport annuel d'une société cotée et obtient une réponse rédigée, avec la section du rapport qui la fonde. Exemple : « Quels risques Renault cite-t-il pour 2025 ? ».

Public : étudiants, jeunes diplômés, petits investisseurs qui lisent un rapport sans avoir le temps de tout parcourir.

## Ce qui existe déjà

- Connecteur AMF (`ingestion/esef_connector.py`) : téléchargement des rapports ESEF (archive contenant un XHTML iXBRL).
- Lecture des chiffres iXBRL, déjà testée sur LVMH.
- Interface Streamlit et principe « le modèle ne fait que rédiger à partir d'éléments fournis » (déjà appliqué dans l'assistant).

## Périmètre du premier jalon (MVP)

Un seul rapport : LVMH, exercice 2025. Objectif : vérifier qu'une question simple reçoit une réponse juste, sourcée, sans inventer.

1. **Extraction du texte** : retirer les balises du XHTML, garder les titres pour nommer les sections.
2. **Découpage** : des passages d'environ 300 mots, chacun rattaché à sa section.
3. **Recherche** : retrouver les passages les plus proches de la question (méthode lexicale d'abord, TF-IDF ou BM25 ; des embeddings seulement si la recherche lexicale échoue).
4. **Réponse** : le modèle reçoit uniquement les passages retrouvés et doit citer leur section. Sans passage pertinent, il répond « information absente du rapport ».
5. **Vérification** : une liste de dix questions de test, avec la réponse attendue vérifiée à la main dans le rapport.

## Hors périmètre (pour l'instant)

- Plusieurs rapports ou plusieurs sociétés ; comptes utilisateurs ; paiement ; hébergement public.
- Questions qui demandent un avis (« faut-il acheter ? ») : refus explicite, pas de réponse.
- Traduction ou tableaux complexes des rapports.

## Critères de réussite du MVP

- Sur les dix questions de test, au moins huit réponses justes et sourcées.
- Aucune réponse qui cite une section inexistante.
- Une question hors sujet reçoit un refus ou « information absente », pas une réponse inventée.

## Choix à trancher

1. **Modèle de rédaction** : local (Ollama, déjà installé, mais qwen2.5:3b rédige peu bien en français sur de longs passages) ou Claude payant (meilleure qualité, coût par question, à prévoir dans la feuille de route).
2. **Calendrier** : votre `CLAUDE.md` prévoit pas de travail sur FinSight pendant les examens (12 décembre et janvier). Le MVP peut être lancé avant le 11 décembre en version réduite, ou reporté à janvier.

## Risques

- Qualité du modèle local en français (voir le choix 1).
- Longueur des rapports : un XHTML fait plusieurs millions de caractères ; il faut un découpage propre, sinon les passages sont trop gros ou mal rattachés.
- Responsabilité : une réponse sur un rapport peut être lue comme un conseil ; la mention « projet pédagogique » doit rester visible.
