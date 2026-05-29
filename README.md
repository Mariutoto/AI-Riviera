# AI Riviera

Prototype de chatbot pour interroger les documents communaux de La Tour-de-Peilz.

## Lancer le chatbot

```powershell
python -m pip install -r requirements.txt
python -m app.ingest
python -m streamlit run app/ui.py
```

L'application répond avec les passages les plus pertinents et leurs sources. Si une clé Mistral ou OpenAI est configurée, elle génère aussi une synthèse en français à partir des extraits retrouvés.

## Options LLM

Sans clé API, l'app affiche les meilleurs extraits trouvés.

Avec Mistral:

```powershell
$env:LLM_PROVIDER="mistral"
$env:MISTRAL_API_KEY="ta-cle"
$env:MISTRAL_MODEL="mistral-small-latest"
python -m streamlit run app/ui.py
```

Avec OpenAI:

```powershell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="ta-cle"
python -m streamlit run app/ui.py
```

Avec `LLM_PROVIDER="auto"`, l'app essaie Mistral si `MISTRAL_API_KEY` existe, puis OpenAI si `OPENAI_API_KEY` existe.

## Données intégrées

Source principale: site officiel de La Tour-de-Peilz.

Couverture actuelle:

- Conseil communal, rubriques institutionnelles: admissions, bureau du conseil communal, compétences, liste des membres par parti, règlement du Conseil communal.
- Ordres du jour, législature 2021-2026: séances du 15 septembre 2021 au 6 mai 2026, soit 34 séances indexées.
- Procès-verbaux, législature 2021-2026: PV01 du 16 juin 2021 à PV34 du 25 mars 2026.
- Motions, postulats, interpellations et réponses: rubrique officielle `motions-postulats`, années 2021 à 2026, soit 99 PDF indexés depuis la page dédiée.
- Documents liés depuis les ordres du jour 2021-2026: préavis, rapports, communications municipales, motions, postulats, interpellations et réponses lorsque les PDF sont liés depuis les séances.
- Collecte directe 2025-2026: motions/postulats/interpellations, préavis municipaux, communications municipales, informations diverses, budgets, ordres du jour et procès-verbaux.

Limites volontaires:

- La séance du 24 juin 2026 n'est pas indexée, car elle est future au moment de la collecte du 29 mai 2026.
- La séance du 30 juin 2021 n'est pas incluse dans les ordres du jour 2021-2026, car elle apparaît dans l'onglet `Législature 2016-2021`.
- La page `motions-postulats.php` est structurée par années et non par onglets de législature; l'import prend les rubriques 2021 à 2026. Certains PDF peuvent avoir une année de fichier différente de l'année affichée sur la page, par exemple lorsqu'une réponse est publiée l'année suivante.
- Les PDF ne sont pas versionnés dans Git pour éviter un dépôt trop lourd. Le dépôt garde les textes extraits et les métadonnées JSON.

## Structure

```text
documents/la-tour-de-peilz/
  2021/
  2022/
  2023/
  2024/
  2025/
  2026/
  institutionnel/

data/sessions/la-tour-de-peilz/
data/proces-verbaux/la-tour-de-peilz/
data/institutionnel/la-tour-de-peilz/
data/index/
```

L'index local est créé ici:

```text
data/index/chunks.jsonl
```

## Scrapers utiles

```powershell
python scrape-la-tour-de-peilz/scrape_ordres_du_jour_2025_2026.py
python scrape-la-tour-de-peilz/scrape_proces_verbaux_2021_2026.py
python scrape-la-tour-de-peilz/scrape_motions_postulats_2021_2026.py
python scrape-la-tour-de-peilz/scrape_conseil_communal_institutionnel.py
python scrape-la-tour-de-peilz/clean_existing_text_data.py
python -m app.ingest
```

Le nom `scrape_ordres_du_jour_2025_2026.py` est historique; il couvre maintenant les ordres du jour de la législature 2021-2026.
