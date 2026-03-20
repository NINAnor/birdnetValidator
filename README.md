# BirdNET Validator

A Streamlit web application for validating bird species detections made by [BirdNET](https://birdnet.cornell.edu/). Upload a ZIP file containing your audio recordings and BirdNET result files, then listen to each detection and confirm or reject species identifications.

## Features

- **Local-first** — no cloud services required, everything runs on your machine
- **ZIP upload** — bundle your audio files and BirdNET `.txt` results into a single ZIP
- **Audio player & spectrogram** — listen to clips and visually inspect detections
- **Confidence & species filters** — focus on the detections that matter
- **Validation form** — confirm species, flag noise, rate your confidence
- **CSV export** — download all your validations as a CSV file

## Getting Started

### 1. Prepare your data

Create a ZIP file containing:

- **Audio files** (`.wav`, `.flac`, `.mp3`, `.ogg`)
- **BirdNET result files** (`.txt`, tab-separated) — the standard output format from BirdNET Analyzer

The result files must contain at least these columns: `Begin Time (s)`, `Common Name`, `Confidence`, `Begin Path`.

### 2. Run the app

```bash
docker compose up --build
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### 3. Validate

1. Upload your ZIP file via the sidebar
2. Adjust confidence threshold and species filters as needed
3. Listen to each clip, check the spectrogram, and submit your validation
4. Download your results as CSV when done

## Development

If you want to run outside Docker:

```bash
uv run streamlit run src/dashboard.py --server.maxUploadSize 1024
```

## Contact

For questions or contributions, please contact [benjamin.cretois@nina.no](mailto:benjamin.cretois@nina.no). Feel free to open issues or pull requests.
