# BirdNET Validator

A Streamlit web application for validating bird species detections made by [BirdNET](https://birdnet.cornell.edu/). Point it at your audio files and BirdNET results, then listen to each detection and confirm or reject species identifications.

## Features

- **Local-first** — no cloud services required, everything runs on your machine
- **Simple setup** — just paste your folder paths in the sidebar
- **Audio player & spectrogram** — listen to clips and visually inspect detections
- **Confidence & species filters** — focus on the detections that matter
- **Validation form** — confirm species, flag noise, rate your confidence
- **CSV export** — download all your validations as a CSV file

## Getting Started

### 1. Install dependencies

```bash
uv sync
```

### 2. Run the app

```bash
uv run streamlit run src/dashboard.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### 3. Validate

1. Enter your audio files and BirdNET results folder paths in the sidebar
2. Adjust confidence threshold and species filters as needed
3. Listen to each clip, check the spectrogram, and submit your validation
4. Download your results as CSV when done

## Expected Data Format

- **Audio files:** `.wav`, `.flac`, `.mp3`, `.ogg`
- **BirdNET results:** tab-separated `.txt` files with columns including `Begin Time (s)`, `Common Name`, `Confidence`, `Begin Path`

## Contact

For questions or contributions, please contact [benjamin.cretois@nina.no](mailto:benjamin.cretois@nina.no). Feel free to open issues or pull requests.
