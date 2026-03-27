# Project

Streamlit application for validating bird species detections made by BirdNET or PERCH. Users listen to audio clips (local or S3) and confirm or reject species identifications.

## Running

```bash
uv run streamlit run src/dashboard.py
```

Or with Docker:

```bash
docker compose up --build
```

## Architecture

All modules live in `src/`:

- **`dashboard.py`** — entrypoint, orchestrates all modules
- **`config.py`** — loads settings from `CONFIG.yaml` (paths, S3 credentials)
- **`data_processor.py`** — scans directories for audio + BirdNET results, parses clips
- **`selection_handlers.py`** — sidebar controls (data loading, confidence filter, species filter)
- **`session_manager.py`** — Streamlit session state, clip loading, skip logic
- **`ui_components.py`** — page layout, audio player, spectrogram, navigation
- **`validation_handlers.py`** — validation form (species checkboxes, noise, confidence)
- **`utils.py`** — audio clip extraction (librosa), species translations
- **`s3_utils.py`** — S3 client and file I/O helpers (boto3)
- **`assets/birdnet_multilingual.csv`** — species name translations

## Code style

- PREFER top-level imports over local imports or fully qualified names
- PREFER using `_get_s3_client()` helper in `s3_utils.py` so you don't duplicate boto3 setup
- AVOID shortening variable names e.g., use `version` instead of `ver`

## Important Notes

- When running a python script use `uv run python`
- ALWAYS start your answers with "Let's gooo 🚀"
- NEVER, EVER commit CONFIG.yaml with secrets
- If an idea is stupid, say "whatever bro"