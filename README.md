# BirdNET Validator

A Streamlit web application for **validating** bird species detections made by [BirdNET](https://birdnet.cornell.edu/) or [PERCH](https://github.com/google-research/perch). This is **not** a detection tool — you must first run BirdNET or PERCH on your audio recordings to produce result files. Once you have those results, point this app at your audio and result directories (locally or on S3), then listen to each detection and confirm or reject species identifications.

## Features

- **Local & S3 support** — read audio and results from local directories or S3-compatible storage
- **Audio player & spectrogram** — listen to clips and visually inspect detections
- **Confidence & species filters** — focus on the detections that matter
- **Validation form** — confirm species, flag noise, rate your confidence
- **Auto-save** — validations are saved automatically to a CSV in your output directory
- **Resume support** — previously validated clips are skipped on restart

## Getting Started

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure paths

Copy the example environment file and edit it with your paths:

```bash
cp .env.example .env
```

Set the three required directories in `.env`:

```dotenv
AUDIO_DIR=/path/to/your/audio/files
RESULTS_DIR=/path/to/your/birdnet/results
OUTPUT_DIR=/path/to/output
```

Paths can be local directories or S3 URIs (e.g. `s3://my-bucket/audio`). When using S3 paths, also fill in the S3 credentials:

```dotenv
S3_ENDPOINT_URL=https://your-s3-endpoint.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

### 3. Run the app

```bash
uv run streamlit run src/dashboard.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### 4. Validate

1. Adjust confidence threshold and species filters in the sidebar
2. Listen to each clip, check the spectrogram, and submit your validation
3. Validations are saved automatically to `birdnet_validations.csv` in your output directory
4. Use the download button to grab the CSV at any time

## Expected Data Format

- **Audio files:** `.wav`, `.flac`, `.mp3`, `.ogg`
- **BirdNET results:** tab-separated `.txt` files with columns including `Begin Time (s)`, `Common Name`, `Confidence`, `Begin Path`

## Docker

```bash
docker compose up --build
```

## Contact

For questions or contributions, please contact [benjamin.cretois@nina.no](mailto:benjamin.cretois@nina.no). Feel free to open issues or pull requests.
