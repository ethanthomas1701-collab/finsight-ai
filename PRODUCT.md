# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Recruteurs et lecteurs du portfolio de Ethan Thomas. Ils ouvrent le site en quelques minutes, par curiosité ou dans le cadre d'une candidature, pour juger la qualité technique du projet et sa clarté. Ils lisent peu de chiffres à la fois, mais attendent qu'ils soient exacts et vérifiables.

## Product Purpose

FinSight AI présente des indicateurs financiers annuels d'entreprises cotées, calculés à partir de données officielles : rapports déposés à la SEC (États-Unis) et à l'AMF (France, format ESEF). Le projet sert de démonstration de compétences en data engineering : collecte, nettoyage, calcul d'indicateurs, contrôle qualité, interface web et assistant.

Succès : un recruteur comprend en moins de deux minutes ce que fait le projet, peut vérifier un chiffre, et voit que le travail est sérieux.

## Positioning

Chaque chiffre est vérifiable : il vient d'un rapport officiel (SEC ou AMF), le calcul de chaque indicateur est documenté, et les anomalies sont signalées sans être masquées. Un concurrent ne peut pas copier ce positionnement sans publier lui aussi ses sources et ses contrôles.

## Operating Context

- Le site public est hébergé sur Streamlit Community Cloud et lit les tableaux publiés dans `donnees_publiques/`.
- Le code est public sur GitHub : un recruteur peut lire le dépôt, le README et les tests.
- Les données brutes et les couches intermédiaires restent en local (`data/`, non versionné).
- Un assistant en langage naturel fonctionne en local avec Ollama ; il n'est pas disponible sur le site public.

## Capabilities and Constraints

- Sociétés américaines (SEC, XBRL us-gaap) et 34 sociétés du CAC 40 déposées à l'AMF (ESEF / IFRS).
- Indicateurs : marge nette, ROE, ROA, passif sur capitaux propres, croissance du chiffre d'affaires, current ratio, free cash flow.
- Devises : montants en dollars ou en euros, conversion au taux moyen annuel de la BCE.
- Limites connues et affichées : pas de free cash flow pour les sociétés françaises ; pas de chiffre d'affaires pour les banques et assurances ; six sociétés exclues car elles déposent aux Pays-Bas ou au Luxembourg.
- Terminologie : « Md$ » ou « Md€ » pour les montants, « % » pour les taux, « x » pour les ratios sans unité.
- Pas d'assistant payant pour l'instant ; l'option Claude payante est une piste future.
- Décision non tranchée : la composition du CAC 40 vient d'un article du 27/10/2026 et n'a pas été vérifiée sur Euronext.

## Brand Commitments

- Nom : FinSight AI.
- Mention obligatoire : « Projet pédagogique. Ce n'est pas un conseil en investissement. » Elle doit apparaître sur toute page présentant des indicateurs.
- Aucun chiffre ne doit être inventé ni arrondi de façon trompeuse ; les valeurs manquantes s'affichent comme absentes, pas comme zéro.

## Evidence on Hand

- Code, tests (96) et README publics sur GitHub : https://github.com/ethanthomas1701-collab/finsight-ai
- Site en ligne : https://finsight-ai-kk4oydvx53venocvf2ebsw.streamlit.app/
- Tableaux publiés : `donnees_publiques/indicateurs.csv`, `donnees_publiques/qualite.csv`, `donnees_publiques/taux_change.csv`.
- Absences à ne pas combler : pas de témoignage, pas de client, pas de chiffre de fréquentation, pas de benchmark de marché.

## Product Principles

- Montrer la source : chaque indicateur doit pouvoir être relié à un rapport officiel.
- Ne rien masquer : une anomalie ou une donnée absente est signalée, jamais corrigée en silence.
- Expliquer avant de chiffrer : les ratios portent une définition accessible à qui découvre la finance.
- Être honnête sur le périmètre : les limites sont affichées sur le site, pas seulement dans le README.
