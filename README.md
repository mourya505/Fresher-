# FresherRadar India
Live tool that collects 200+ fresher/internship posts in India from public APIs, de-duplicates them,
tags each by **role** and **city** with an LLM (Groq llama-3.1-8b, rule-based fallback), and shows them in a searchable Streamlit page that refreshes daily.

## Pipeline
Sources (Adzuna, Greenhouse, Lever, Remotive APIs - no HTML scraping) -> India + fresher filter -> dedupe (URL + company/title fuzzy match) -> LLM tagging -> SQLite (`jobs.db`) -> Streamlit.

## Run
    pip install -r requirements.txt
    export ADZUNA_APP_ID=... ADZUNA_APP_KEY=... GROQ_API_KEY=...
    python pipeline.py && streamlit run app.py

## Daily auto-refresh
`.github/workflows/refresh.yml` runs at 06:00 IST, commits `jobs.db`; Streamlit Cloud redeploys on commit.
The app also self-refreshes if data is older than 24h. Add the 3 keys as GitHub repo secrets (and Streamlit secrets/env).
