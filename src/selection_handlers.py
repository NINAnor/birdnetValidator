"""Selection Handlers.

Manages data loading, confidence threshold filtering,
and species selection. Supports local paths and S3 URIs.
"""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from data_processor import get_unique_species, process_local_directories
from s3_utils import is_s3_path, list_s3_files, read_s3_text
from utils import LANGUAGE_OPTIONS, translate_species_name

VALIDATIONS_PREFIX = "birdnet_validations_"


def _get_validations_filename(annotator):
    """Return the CSV filename for a given annotator."""
    return f"{VALIDATIONS_PREFIX}{annotator}.csv"


def _load_existing_validations(output_dir, annotator):
    """Load validations from all annotators in the output directory.

    Populates local_validated_clips with clips validated by ANY annotator,
    but only loads the current annotator's records into local_validations.
    """
    all_validated = set()
    own_records = []

    if is_s3_path(output_dir):
        all_files = list_s3_files(output_dir, extension=".csv")
        csv_files = [
            f for f in all_files
            if f.split("/")[-1].startswith(VALIDATIONS_PREFIX)
        ]
        for csv_uri in csv_files:
            text = read_s3_text(csv_uri)
            df = pd.read_csv(io.StringIO(text))
            path_col = "filepath" if "filepath" in df.columns else "filename"
            is_own = csv_uri.split("/")[-1] == _get_validations_filename(annotator)
            if is_own:
                own_records = df.to_dict("records")
                all_validated.update(
                    (row[path_col], row["start_time"]) for _, row in df.iterrows()
                )
            else:
                for _, row in df.iterrows():
                    if not row.get("peer_review", False):
                        all_validated.add((row[path_col], row["start_time"]))
    else:
        output_path = Path(output_dir)
        for csv_path in output_path.glob(f"{VALIDATIONS_PREFIX}*.csv"):
            df = pd.read_csv(csv_path)
            path_col = "filepath" if "filepath" in df.columns else "filename"
            is_own = csv_path.name == _get_validations_filename(annotator)
            if is_own:
                own_records = df.to_dict("records")
                all_validated.update(
                    (row[path_col], row["start_time"]) for _, row in df.iterrows()
                )
            else:
                for _, row in df.iterrows():
                    if not row.get("peer_review", False):
                        all_validated.add((row[path_col], row["start_time"]))

    st.session_state.local_validated_clips = all_validated
    st.session_state.local_validations = own_records


def render_local_data_loader():
    """Load data from directories configured in CONFIG.yaml.

    Returns True if data has been loaded successfully.
    """
    from config import AUDIO_DIR, OUTPUT_DIR, RESULTS_DIR

    # Annotator name (must be set before data loads)
    annotator = st.sidebar.text_input(
        "👤 Your name",
        value=st.session_state.get("annotator_name", ""),
        placeholder="e.g. benjamin",
        help="Used to separate your validations from other annotators",
    )
    if not annotator or not annotator.strip():
        st.sidebar.warning("⚠️ Enter your name to start validating.")
        return False
    annotator = annotator.strip().lower().replace(" ", "_")
    st.session_state.annotator_name = annotator

    if not AUDIO_DIR or not RESULTS_DIR or not OUTPUT_DIR:
        st.sidebar.error(
            "❌ Missing paths in `CONFIG.yaml` file.\n\n"
            "Set `audio_dir`, `results_dir`, and `output_dir`."
        )
        return False

    audio_dir = AUDIO_DIR
    results_dir = RESULTS_DIR
    output_dir = OUTPUT_DIR

    # Validate local paths (S3 paths are validated when accessed)
    if not is_s3_path(audio_dir) and not Path(audio_dir).is_dir():
        st.sidebar.error(f"❌ Directory not found: `{audio_dir}`")
        return False

    if not is_s3_path(results_dir) and not Path(results_dir).is_dir():
        st.sidebar.error(f"❌ Directory not found: `{results_dir}`")
        return False

    if not is_s3_path(output_dir):
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    st.session_state.local_output_dir = output_dir

    # Only reprocess if paths changed
    current_key = (audio_dir, results_dir)
    if (
        "local_path_key" not in st.session_state
        or st.session_state.local_path_key != current_key
    ):
        with st.spinner("Loading data..."):
            data = process_local_directories(audio_dir, results_dir)

        if not data["clips"]:
            st.sidebar.error("❌ No valid BirdNET detections found.")
            st.sidebar.info(
                "Make sure the directories contain:\n"
                "- Audio files (.wav, .flac, .mp3, .ogg)\n"
                "- BirdNET result files (.txt, tab-separated)"
            )
            return False

        st.session_state.local_path_key = current_key
        st.session_state.local_data = data
        st.session_state.local_clips = data["clips"]
        st.session_state.local_current_clip = None
        st.session_state.local_validated_clips = set()
        st.session_state.local_validations = []

        # Restore previous validations from output dir
        _load_existing_validations(output_dir, annotator)
        st.session_state.local_annotator_key = annotator

    # Reload validations if annotator changed
    elif st.session_state.get("local_annotator_key") != annotator:
        st.session_state.local_current_clip = None
        _load_existing_validations(output_dir, annotator)
        st.session_state.local_annotator_key = annotator

    st.sidebar.success(
        f"✅ Loaded **{st.session_state.local_data['total_clips']}** clips"
    )
    return True


def render_language_selector():
    """Render language selector in the sidebar."""
    language = st.sidebar.selectbox(
        "🌐 Language",
        options=list(LANGUAGE_OPTIONS.keys()),
        format_func=lambda k: LANGUAGE_OPTIONS[k],
        index=0,
        help="Choose the language for species names",
    )
    return language


def render_local_confidence_filter():
    """Render confidence range slider."""
    confidence_range = st.sidebar.slider(
        "🎯 Confidence range",
        min_value=0.0,
        max_value=1.0,
        value=(0.1, 1.0),
        step=0.05,
        help="Only show clips with at least one detection within this confidence range",
    )
    return confidence_range


def render_local_species_filter(selections):
    """Render species filter multiselect.

    Returns list of selected species (English) or None for all species.
    """
    st.sidebar.markdown("---")

    filter_enabled = st.sidebar.checkbox(
        "🐦 Filter by species",
        value=False,
        help="Enable to select specific species to validate",
    )

    if not filter_enabled:
        return None

    clips = st.session_state.get("local_clips", [])
    if not clips:
        return None

    available_species = get_unique_species(clips)
    language = selections.get("language", "en_uk")

    display_names = [
        translate_species_name(s, language) for s in available_species
    ]
    display_to_english = dict(zip(display_names, available_species, strict=False))

    selected_display = st.sidebar.multiselect(
        "Select species:",
        options=sorted(display_names),
        default=[],
        placeholder="Select species...",
    )

    if selected_display:
        selected = [display_to_english[d] for d in selected_display]
        st.sidebar.success(f"✅ Filtering to {len(selected)} species")
        return selected

    st.sidebar.warning("⚠️ Select at least one species or disable filter")
    return None


def get_local_user_selections():
    """Orchestrate all local mode sidebar selections.

    Returns dict with confidence_threshold and species_filter, or None.
    """
    data_ready = render_local_data_loader()

    if not data_ready:
        return None

    confidence_range = render_local_confidence_filter()
    language = render_language_selector()

    selections = {
        "confidence_range": confidence_range,
        "language": language,
    }

    species_filter = render_local_species_filter(selections)
    selections["species_filter"] = species_filter

    return selections
