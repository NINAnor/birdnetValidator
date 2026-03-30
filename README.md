# 🐦 BirdNET Validator

> **Listen. Verify. Trust your data.**

A Streamlit web app for **validating** bird species detections made by [BirdNET](https://github.com/birdnet-team/BirdNET-Analyzer) or any model with a compatible output (see [Expected Data Format](#-expected-data-format)). This is **not** a detection tool — run BirdNET first, then use this app to listen to each detection and confirm or reject species identifications.

<p align="center">
  <img src="assets/screenshot_app.png" width="400" alt="Screenshot">
</p>

---

## ✨ Key Features

| | Feature | Description |
|---|---------|-------------|
| 📂 | **Local & S3 support** | Read audio and results from local directories or any S3-compatible storage |
| 🎧 | **Audio player & spectrogram** | Listen to clips and visually inspect detections with a dark-mode–aware spectrogram |
| 🔍 | **Confidence & species filters** | Focus on the detections that matter with adjustable confidence range and species selection |
| 🌍 | **20 languages** | View species names in your language — Arabic, Chinese, Danish, Dutch, English, French, German, Italian, Japanese, Korean, Norwegian, Polish, Portuguese, Brazilian Portuguese, Russian, Spanish, Swedish, Thai, Turkish, and Ukrainian |
| ℹ️ | **Species info links** | Quick links to Wikipedia and Xeno-Canto for each detected species |
| ✅ | **Validation form** | Confirm species, add missed species, tag background sounds, rate your confidence |
| 💾 | **Auto-save & resume** | Validations save automatically to CSV — previously validated clips are skipped on restart |
| 👥 | **Multi-annotator** | Each annotator gets their own file; clips validated by anyone are skipped for everyone |
| 🔄 | **Peer review** | Flag uncertain clips so other annotators can provide a second opinion |
| 🐳 | **Docker-ready** | Deploy on a shared server so your team can validate from their browser |

---

## 🚀 Getting Started

### Option A: One-line install (recommended)

> **Never used Python before? No problem!** Follow the steps below.

#### Step 1: Install Python

Download and install Python from [python.org](https://www.python.org/downloads/) (version 3.10 or newer).

- **Windows:** Download the installer, run it, and **check the box "Add Python to PATH"** before clicking Install
- **Mac:** Download the macOS installer and follow the prompts
- **Linux:** Python is usually pre-installed. Check with `python3 --version`

#### Step 2: Install the app

Open a terminal (or Command Prompt on Windows) and run:

```bash
pip install git+https://github.com/NINAnor/birdnetValidator.git
```

This installs everything you need. It may take a minute or two.

#### Step 3: Launch!

In the same terminal, run:

```bash
birdnet-validator \
    --audio-dir /path/to/your/audio \
    --results-dir /path/to/your/birdnet/results \
    --output-dir /path/to/your/output
```

Replace the paths with your actual directories. The app opens in your browser automatically. 🎉

> **Windows tip:** Use backslashes in paths and put the whole command on one line:
> ```
> birdnet-validator --audio-dir C:\Users\me\audio --results-dir C:\Users\me\results --output-dir C:\Users\me\output
> ```

You can also use it from a Python script:

```python
import birdnet_validator

birdnet_validator.run(
    audio_dir="/path/to/audio",
    results_dir="/path/to/results",
    output_dir="/path/to/output",
)
```

<details>
<summary>☁️ Using S3 paths? (click to expand)</summary>

Pass your S3 credentials as extra arguments:

```python
birdnet_validator.run(
    audio_dir="s3://my-bucket/audio",
    results_dir="s3://my-bucket/results",
    output_dir="s3://my-bucket/output",
    s3_endpoint_url="https://your-s3-endpoint.com",
    s3_access_key="your-access-key",
    s3_secret_key="your-secret-key",
)
```

Or via CLI:

```bash
birdnet-validator \
    --audio-dir s3://my-bucket/audio \
    --results-dir s3://my-bucket/results \
    --output-dir s3://my-bucket/output \
    --s3-endpoint-url https://your-s3-endpoint.com \
    --s3-access-key your-access-key \
    --s3-secret-key your-secret-key
```

</details>

### Option B: From source (for developers)

```bash
git clone https://github.com/NINAnor/birdnetValidator.git
cd birdnetValidator
uv sync
cp .env.example .env   # edit with your paths
uv run streamlit run src/dashboard.py
```

### 🎯 Validating

1. Enter your name in the sidebar
2. Adjust confidence threshold and species filters
3. Listen to each clip, inspect the spectrogram, and submit your validation
4. Validations are saved automatically to `birdnet_validations_{name}.csv` in your output directory
5. Use the **📥 Download** button to grab all results as CSV at any time

---

## 📋 Expected Data Format

### Audio files

`.wav`, `.flac`, `.mp3`, `.ogg` — any format supported by librosa.

### Detection result files

Tab-separated `.txt` files with **at least** these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `Begin Time (s)` | Detection start time in seconds | `12.0` |
| `End Time (s)` | Detection end time in seconds | `15.0` |
| `Common Name` | Species common name (English) | `Eurasian Blackbird` |
| `Species Code` | Short species code | `eurbla1` |
| `Confidence` | Model confidence score (0.0–1.0) | `0.87` |
| `Begin Path` | Path to the source audio file | `/data/audio/site1/recording.wav` |

This is the default output of [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer), but **any classifier producing tab-separated `.txt` files with these columns will work**. Rows where `Common Name` is `nocall` are automatically ignored.

<details>
<summary>📄 Example file (click to expand)</summary>

```
Selection	View	Channel	Begin Time (s)	End Time (s)	Low Freq (Hz)	High Freq (Hz)	Common Name	Species Code	Confidence	Begin Path	File Offset (s)
1	Spectrogram 1	1	0.0	3.0	0	15000	Eurasian Blackbird	eurbla1	0.87	/data/audio/rec.wav	0.0
2	Spectrogram 1	1	3.0	6.0	0	15000	Common Chaffinch	comcha	0.42	/data/audio/rec.wav	3.0
```

> Extra columns (`Selection`, `View`, `Channel`, etc.) are ignored — only the six required columns matter.

</details>

---

## 🧪 Suggested Workflows

### Goal 1: Species richness (presence/absence)

If you want to know **which species are present** at a site:

1. Set **confidence range** to a high lower bound (e.g. 0.7–1.0)
2. Use the **species filter** to work through one species at a time
3. Validate **~20–30 clips per species** to confirm genuine presence
4. If most detections are false positives → raise the threshold

### Goal 2: Calibration curve (precision by confidence bin)

If you want to **quantify BirdNET's accuracy** per species:

1. Divide the confidence range into bins (0.1–0.2, 0.2–0.3, …, 0.9–1.0)
2. Validate **~30–50 clips per bin per species**
3. Compute precision per bin: `TP / (TP + FP)`
4. Plot confidence vs. precision to find your optimal threshold

### 👥 Working with multiple annotators

Each annotator enters their name in the sidebar — validations save to separate files (`birdnet_validations_{name}.csv`). Clips validated by any annotator are skipped for everyone.

**🔄 Peer review:** Unsure about a clip? Tick "Request peer review" before submitting. The clip is saved to your file but remains visible to other annotators for a second opinion.

**Dividing the workload:**

- **Split by species** — assign each annotator a subset via the species filter
- **Split by confidence bin** — one annotator handles 0.1–0.5, another 0.5–1.0
- **Redundant annotation** — for inter-annotator agreement, have 2+ annotators validate the same clips using separate output directories

---

## 🐳 Docker

Deploy on a shared server so your team can validate from their browser:

```bash
docker compose up --build
```

Set your paths in `.env` (see `.env.example`). See `docker-compose.yml` for details.

---

## 📬 Contact

Questions or contributions? Contact [benjamin.cretois@nina.no](mailto:benjamin.cretois@nina.no) or open an issue / pull request.
