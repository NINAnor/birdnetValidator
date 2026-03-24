# BirdNET Validator

A Streamlit web application for **validating** bird species detections made by [BirdNET](https://birdnet.cornell.edu/) or [PERCH](https://github.com/google-research/perch). This is **not** a detection tool — you must first run **BirdNET** or other model with similar output on your audio recordings to produce result files. Once you have those results, point this app at your audio and result directories (locally or on S3), then listen to each detection and confirm or reject species identifications.

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

## Suggested Workflow

How you validate depends on your research question. Below are two common strategies and advice for teams.

### Goal 1: Species richness (presence/absence)

If you want to know **which species are present** at a site, you don't need to validate every detection — focus on high-confidence ones and confirm a subset per species.

1. Set the **confidence range** to a high lower bound (e.g. 0.7–1.0)
2. Use the **species filter** to work through one species at a time
3. Validate **~20–30 clips per species** — enough to confirm that the species is genuinely present at the site
4. If most detections for a species are false positives, raise the threshold; if they are all correct, you can trust BirdNET for that species at that confidence level

### Goal 2: Calibration curve (precision by confidence bin)

If you want to **quantify BirdNET's accuracy** for each species — i.e. determine the confidence threshold at which precision reaches an acceptable level (e.g. 90%) — you need to sample across the full confidence range.

1. Divide the confidence range into bins (e.g. 0.1–0.2, 0.2–0.3, …, 0.9–1.0)
2. For each bin, set the **confidence range** slider accordingly
3. Validate **~30–50 clips per bin per species** — this gives you a reliable estimate of precision at each confidence level
4. After validation, compute precision per bin: `true positives / (true positives + false positives)`
5. Plot confidence vs. precision to find the threshold where accuracy meets your requirements

### Working with multiple annotators

The app supports multiple annotators out of the box — each person enters their name in the sidebar, and validations are saved to separate files (`birdnet_validations_{name}.csv`). Clips validated by any annotator are skipped for everyone.

To divide the workload efficiently:

- **Split by species** — assign each annotator a subset of species using the species filter. This avoids overlap and works well when annotators have different taxonomic expertise
- **Split by confidence bin** — one annotator handles 0.1–0.5, another 0.5–1.0. Useful for calibration workflows where you need even coverage across bins
- **Redundant annotation** — for inter-annotator agreement analysis, have 2+ annotators validate the same clips. The `annotator` column in the output lets you compare their assessments. To enable this, each annotator's validated clips won't be skipped for the others — they need to point to separate output directories or you can clear and re-scan as needed

## Docker

```bash
docker compose up --build
```

## Contact

For questions or contributions, please contact [benjamin.cretois@nina.no](mailto:benjamin.cretois@nina.no). Feel free to open issues or pull requests.
