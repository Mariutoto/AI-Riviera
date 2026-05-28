# AI Riviera

Chatbot local pour interroger les documents communaux récupérés depuis le site de La Tour-de-Peilz.

## Lancer le chatbot

```powershell
python -m pip install -r requirements.txt
python -m app.ingest
python -m streamlit run app/ui.py
```

L'application répond déjà avec les passages les plus pertinents et leurs sources.

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

## Données

Les documents sont rangés ici:

```text
documents/la-tour-de-peilz/
  2025/
  2026/
```

L'index local est créé ici:

```text
data/index/chunks.jsonl
```

Les PDF ne sont pas versionnés dans Git pour éviter un dépôt trop lourd. Les fichiers texte et métadonnées peuvent être gardés pour la démo; les PDF peuvent être recréés avec le scraper:

```powershell
python scrape-la-tour-de-peilz/scrape_2025_2026.py
```
