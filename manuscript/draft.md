# BirdValidator: a lightweight web application for validating automated bird species detections from passive acoustic monitoring data

## Abstract

Passive acoustic monitoring (PAM) combined with deep learning classifiers such as BirdNET has become a standard approach for surveying bird communities at scale. However, automated detections require human validation before they can be used in ecological analyses — a step that remains bottlenecked by the complexity of existing annotation tools. We present BirdValidator, an open-source Streamlit web application designed specifically for efficient, structured validation of classifier outputs. The application supports both local and cloud-based (S3) workflows, enables collaborative annotation by multiple users, and provides built-in filtering by confidence score and species to support different validation strategies. We describe three suggested workflows with case studies: (1) validating species presence for species richness estimation, (2) building confidence calibration curves for determining species-specific thresholds, and (3) curating training datasets for machine learning models. BirdValidator bridges the gap between raw model outputs and analysis-ready datasets, helping researchers move from "EBV-usable" to "EBV-ready" biodiversity data.

**Keywords:** passive acoustic monitoring, bioacoustics, annotation tool, BirdNET, species validation, Essential Biodiversity Variables

---

## 1. Introduction

Passive acoustic monitoring has emerged as a cost-effective, non-invasive method for surveying biodiversity across broad spatial and temporal scales (Sugai et al., 2019). The deployment of autonomous recording units, combined with deep learning classifiers such as BirdNET (Kahl et al., 2021) and PERCH (Ghani et al., 2023), now enables the automated detection and identification of bird species from thousands of hours of audio recordings. These tools have dramatically reduced the time needed to process acoustic data, making continental-scale monitoring feasible (Pérez-Granados & Schuchmann, 2023).

Yet automated classifiers are imperfect. False positive rates vary across species, habitats, and confidence thresholds (Wood et al., 2024), and naïve use of raw model outputs can lead to biased estimates of species richness, occupancy, or abundance. Human validation of a representative subset of detections is therefore essential for any rigorous ecological analysis — whether the goal is to confirm species presence at a site, to calibrate model confidence scores against true precision, or to curate training data for fine-tuning classifiers.

Despite this need, the tools available for validating classifier outputs remain poorly suited to the task. General-purpose audio annotation software such as Raven Pro (K. Lisa Yang Center for Conservation Bioacoustics, 2024) and Audacity are powerful but complex: they require users to navigate full spectrograms, manually locate detection windows, and manage annotations in separate spreadsheet files. This creates a steep learning curve for ecologists who are not trained bioacousticians and imposes a significant time cost even for experienced users. More critically, these tools were designed for manual annotation from scratch, not for the specific workflow of reviewing and validating automated detections.

Here we present BirdValidator, an open-source web application purpose-built for validating automated bird species detections. The application takes as input any set of detection result files in BirdNET's standard tab-separated format and the corresponding audio recordings, and presents each detection to the user as a short audio clip with spectrogram, confidence score, and a structured validation form. The design prioritises speed and simplicity: a typical detection can be validated in under 10 seconds. The application supports collaborative annotation by multiple users, works with both local files and S3-compatible cloud storage, and provides filtering tools that enable different validation strategies depending on the research question.

---

## 2. Application description

### 2.1. Overview and design philosophy

BirdValidator is built with Streamlit, a Python web framework that requires no front-end development and runs in any modern web browser. This design choice means that the application can be run locally on a researcher's laptop, deployed on a shared server for team-based annotation, or containerised with Docker for production deployment — all without requiring users to install specialised software beyond python and a web browser.

The application follows a single-page layout with two main panels (Figure 1). The left panel displays the audio clip, spectrogram, and navigation controls. The right panel contains the validation form. A sidebar provides data loading, annotator identification, language selection, and filtering controls.

### 2.2. Input data

BirdValidator accepts two types of input, configured via environment variables:

**Audio files** in any standard format supported by librosa (`.wav`, `.flac`, `.mp3`, `.ogg`), stored in a local directory or an S3 bucket.

**Detection result files** as tab-separated `.txt` files containing, at minimum, the following columns:

| Column | Description |
|--------|-------------|
| `Begin Time (s)` | Detection start time in the audio file |
| `End Time (s)` | Detection end time |
| `Common Name` | Species common name |
| `Species Code` | Short species identifier |
| `Confidence` | Model confidence score (0.0–1.0) |
| `Begin Path` | Path to the source audio file |

This format is the default output of BirdNET-Analyzer (Kahl et al., 2021), but any classifier producing tab-separated files with these columns is compatible. Detections labelled `nocall` are automatically excluded.

Importantly, BirdValidator natively supports **multilabel** detections. BirdNET and similar classifiers can assign multiple species to the same time segment — for example, when two birds vocalise simultaneously. BirdValidator groups all detections sharing the same audio file and start time into a single clip, presenting all candidate species together with their respective confidence scores. The annotator can then confirm any combination of the detected species, reject all of them, or add species that the classifier missed. This multilabel handling is critical for acoustic monitoring in species-rich environments where overlapping vocalisations are common.

### 2.3. Audio clip presentation

For each detection, BirdValidator extracts a short audio clip centred on the detection window. The default view presents 1 second of context before and 1 second after the 3-second BirdNET detection window (5 seconds total). An adjustable slider allows the user to extend the context up to 5 seconds on each side (13 seconds total), which can be helpful for species with longer vocalisations or when background context aids identification.

The spectrogram is displayed with a frequency range of 0–12 kHz and red dashed lines marking the boundaries of the model's detection window, clearly delineating the audio region the classifier analysed from the surrounding context.

### 2.4. Validation form

The validation form is structured to capture rich annotation data efficiently:

1. **Species confirmation.** Checkboxes for each species detected by the classifier at the given time point, sorted by confidence score in descending order. Because classifiers like BirdNET are multilabel — multiple species can be detected in the same audio segment — all co-occurring detections are presented together. The annotator selects which species they can actually hear, confirming any subset of the detections. A "none of the above" option is provided for clips where no focal species is audible.

2. **Additional species.** A searchable multiselect field for adding species present in the audio but missed by the classifier. The autocomplete list draws from a multilingual database of over 6,500 bird species.

3. **Environmental sounds.** Checkboxes for common sound categories (rain, wind, traffic, human voices, insects, etc.) that characterise the acoustic environment and may be useful for understanding false positive patterns.

4. **Free-text comments.** An open text field for noting unusual circumstances (e.g., "faint call in background", "multiple individuals calling").

5. **Annotator confidence.** A required rating (Low / Moderate / High) reflecting the annotator's certainty in their own assessment.

Species names can be displayed in five languages (English, French, Spanish, Dutch, Norwegian) via a language selector in the sidebar, supporting international research teams.

### 2.5. Filtering and navigation

Two sidebar controls allow users to focus their validation effort:

- **Confidence range slider** (0.0–1.0, step 0.05): only shows detections where the maximum confidence score falls within the selected range. This enables targeted validation of specific confidence tiers.
- **Species filter**: a multiselect dropdown to restrict validation to one or more focal species.

A "Skip" button allows the annotator to pass on uncertain clips and return to them later — skipped clips cycle back after all other clips in the current filter have been addressed.

### 2.6. Output format and persistence

Each validation is saved as a row in a per-annotator CSV file (`birdnet_validations_{annotator}.csv`) containing the original detection metadata, the annotator's species identifications, environmental sound annotations, confidence rating, comments, annotator name, and timestamp. Validations are written to disk (or S3) after each submission, ensuring no data loss. A download button merges all annotators' files into a single CSV for analysis.

### 2.7. Multi-annotator support

Each user enters their name in the sidebar, creating a personal validation file. On startup, the application scans all existing validation files in the output directory and marks previously-validated clips as complete for all users. This prevents duplicate work when multiple annotators share the same dataset. Workload can be divided by assigning different species or confidence bins to different annotators via the sidebar filters.

### 2.8. Deployment options

BirdValidator can be deployed in three ways:

- **Local execution:** `uv run streamlit run src/dashboard.py` — suitable for individual use.
- **Docker container:** `docker compose up --build` — suitable for shared server deployment where multiple annotators access the application via their web browser. The `.env` file is passed to the container for configuration.
- **Cloud storage:** all three directories (audio, results, output) can point to S3-compatible storage, enabling validation of datasets that are too large to store locally.

---

## 3. Suggested workflows

The flexibility of BirdValidator's filtering tools supports several distinct validation strategies, depending on the research question. We describe three common workflows below.

### 3.1. Workflow 1: Validating species presence for species richness estimation

**Goal:** Confirm which species detected by the classifier are genuinely present at a site.

**Strategy:** Focus on high-confidence detections and validate a small but sufficient subset per species. Set the confidence range slider to a high lower bound (e.g., 0.70–1.00). Use the species filter to work through one species at a time. Validating 20–30 clips per species is typically sufficient to confirm presence, as even a small number of true positives among high-confidence detections provides strong evidence that the species is present. If most detections for a given species are false positives even at high confidence, the species can be flagged as unreliably detected by the classifier at the site.

This approach minimises validation effort while producing a defensible species list. The resulting data can be used to derive species richness estimates and site-level species inventories.

**Case study:** [To be completed with empirical example — e.g., validation of BirdNET detections across N sites in a PAM network, comparing validated species richness against expert survey data.]

### 3.2. Workflow 2: Building confidence calibration curves

**Goal:** Determine the confidence threshold at which the classifier achieves a target precision (e.g., 90%) for each species.

**Strategy:** Divide the confidence range into bins (e.g., 0.10–0.20, 0.20–0.30, ..., 0.90–1.00) and validate 30–50 clips per bin per species. For each bin, set the confidence range slider accordingly. After validation, compute precision per bin as: $\text{precision} = \frac{\text{true positives}}{\text{true positives} + \text{false positives}}$. Plot confidence versus precision for each species to identify the threshold where precision meets the target.

This workflow produces species-specific calibration curves that account for variation in classifier performance across species, which can vary substantially (Wood et al., 2024). The resulting thresholds can be applied to the full dataset to produce filtered detection lists with known precision guarantees.

**Case study:** [To be completed with empirical example — e.g., calibration curves for N species showing how precision varies with confidence threshold, and the resulting species-specific thresholds at 90% precision.]

### 3.3. Workflow 3: Curating training data for machine learning

**Goal:** Create a validated dataset for training or fine-tuning acoustic classifiers.

**Strategy:** Sample detections from intermediate confidence ranges where the classifier is uncertain — these are the most informative examples for model improvement. Set the confidence range to 0.30–0.70 (or similar, depending on the classifier) and validate all clips within this range. The resulting dataset, containing both confirmed true positives and confirmed false positives with environmental context annotations, can be used to retrain or fine-tune classifiers, following the active learning approach described by Bernard et al. (2026).

The environmental sound annotations (rain, wind, traffic, etc.) captured by BirdValidator's form are particularly valuable for this workflow, as they characterise the acoustic conditions under which false positives occur and can inform data augmentation strategies.

**Case study:** [To be completed with empirical example — e.g., fine-tuning BirdNET on validated data from BirdValidator, showing improvement in precision for focal species.]

---

## 4. Discussion

### 4.1. Efficient collaborative validation

A key advantage of BirdValidator's multi-annotator architecture is the ability to distribute validation work across a team without coordination overhead. The recommended approach is to divide the workload along two axes:

- **By species:** Assign each annotator a subset of species matching their taxonomic expertise. An annotator familiar with warblers validates warbler detections; another handles raptors. The species filter in the sidebar makes this straightforward.
- **By confidence bin:** For calibration workflows, each annotator can be assigned a different confidence range (e.g., one person handles 0.10–0.50, another 0.50–1.00), ensuring even coverage across the confidence spectrum.

For studies requiring inter-annotator agreement analysis, two or more annotators can independently validate the same clips by using separate output directories. The `annotator` column in the output CSV enables direct comparison of assessments.

### 4.2. From EBV-usable to EBV-ready biodiversity data

Passive acoustic monitoring data, once processed by automated classifiers, can be considered "EBV-usable" — it contains information relevant to Essential Biodiversity Variables (species populations, community composition) but requires further processing to meet quality standards for biodiversity assessments (Kissling et al., 2026). The validation step is what transforms these data from EBV-usable to "EBV-ready": validated detection lists with known error rates and confidence thresholds provide the quality guarantees needed for inclusion in biodiversity monitoring frameworks and reporting.

BirdValidator is designed to make this transformation practical at scale. By structuring the validation process around reusable confidence thresholds and species-specific calibration curves, validated data from one site or season can inform the processing of data from other sites, building cumulative knowledge about classifier performance that improves efficiency over time.

### 4.3. Limitations and future directions

The current version of BirdValidator is designed for BirdNET-format outputs, though any classifier producing the same tab-separated format is supported. Future versions could support additional formats (e.g., Raven selection tables) or allow custom column mapping. The application does not currently support annotation from scratch (i.e., without pre-existing model detections); it is strictly a validation tool. Integration with active learning pipelines — where the application prioritises clips that are most informative for model improvement — is a natural extension.

---

## 5. Conclusion

BirdValidator fills a practical gap in the passive acoustic monitoring workflow: the need for fast, structured, collaborative validation of automated species detections. By providing purpose-built filtering tools, a streamlined validation form, and multi-annotator support, the application enables researchers to implement rigorous validation strategies — from quick species presence checks to comprehensive calibration studies — with minimal overhead. The tool is open-source, requires no specialised software for end users, and scales from a single laptop to cloud-deployed team workflows.

**Availability:** BirdValidator is available at https://github.com/NINAnor/birdnetValidator under a GPL-3.0 licence.

---

## References

Bernard, A., et al. (2026). [Training reference for active learning with validated PAM data.]

Ghani, B., et al. (2023). Global birdsong embeddings enable superior transfer learning for bioacoustic classification. *Scientific Reports*, 13, 22876.

Kahl, S., et al. (2021). BirdNET: A deep learning solution for avian diversity monitoring. *Ecological Informatics*, 61, 101236.

K. Lisa Yang Center for Conservation Bioacoustics. (2024). *Raven Pro: Interactive Sound Analysis Software*. The Cornell Lab of Ornithology.

Kissling, W.D., et al. (2026). [EBV-usable to EBV-ready reference.]

Pérez-Granados, C., & Schuchmann, K.-L. (2023). BirdNET: applications, performance, and limitations. *Ibis*, 165, 1123–1136.

Sugai, L.S.M., et al. (2019). Terrestrial passive acoustic monitoring: review and perspectives. *BioScience*, 69, 15–25.

Wood, C.M., et al. (2024). Perils and pitfalls of automated bird sound identification. *The Condor: Ornithological Applications*, 126, duae005.
