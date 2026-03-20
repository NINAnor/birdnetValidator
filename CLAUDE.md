# Project

Streamlit application for validating bird species detections made by BirdNET v2.4. Users listen to audio clips from S3 and confirm or reject species identifications.

## Running

```bash
docker compose up --build
```

## Architecture

- **Entrypoint:** `src/dashboard.py` — orchestrates all modules
- **`config.py`** — env vars, S3 paths, language mapping
- **`queries.py`** — DuckDB queries against S3 parquet files (countries, sites, species, clips)
- **`selection_handlers.py`** — sidebar controls (country/site/species selectors with random init)
- **`session_manager.py`** — Streamlit session state and clip loading
- **`ui_components.py`** — page layout, audio player, spectrogram, buttons
- **`validation_handlers.py`** — validation form (radio, multiselect species, confidence)
- **`utils.py`** — S3 file operations (boto3), audio extraction (librosa), species translations
- **`assets/birdnet_multilingual.csv`** — species name translations for multiselect and display

## Code style

- PREFER top-level imports over local imports or fully qualified names
- PREFER using  `_get_s3_client()` helper in `utils.py` so you don't duplicate boto3 setup
- PREFER using duckdb over polar or pandas for filtering the dataset
- ALWAYS use polar over pandas 
- AVOID shortening variable names e.g., use `version` instead of `ver`, and `requires_python` instead of `rp`

## Branches

- `main` — citizen science / public mode
- `pro_version` — expert annotation mode with assigned clips and detailed checklist

## Important Notes

- When running a python script use `uv run python`
- ALWAYS start your answers with "Let's gooo 🚀"
- NEVER, EVER commit .env files
- If an idea is stupid, say "whatever bro"