"""Local Mode Selection Handlers.

Manages zip file upload, confidence threshold filtering,
and species selection for local validation mode.
"""

import streamlit as st

from local.data_processor import get_unique_species, process_uploaded_zip
from ui.ui_utils import render_sidebar_logo


def render_local_upload():
    """Render zip file uploader in sidebar.

    Returns True if data has been uploaded and processed.
    """
    render_sidebar_logo()
    st.sidebar.header("📁 Upload Data")

    uploaded_file = st.sidebar.file_uploader(
        "Upload a ZIP file with audio files and BirdNET results",
        type=["zip"],
        help=(
            "The ZIP should contain audio files (.wav, .flac, .mp3, .ogg) "
            "and BirdNET result files (.txt, tab-separated)"
        ),
    )

    if uploaded_file is None:
        return False

    # Only reprocess if a different file was uploaded
    if (
        "local_uploaded_filename" not in st.session_state
        or st.session_state.local_uploaded_filename != uploaded_file.name
    ):
        with st.spinner("Processing uploaded data..."):
            data = process_uploaded_zip(uploaded_file)

        if not data["clips"]:
            st.sidebar.error(
                "❌ No valid BirdNET detections found in the ZIP file."
            )
            st.sidebar.info(
                "Make sure the ZIP contains:\n"
                "- Audio files (.wav, .flac, .mp3, .ogg)\n"
                "- BirdNET result files (.txt, tab-separated)"
            )
            return False

        st.session_state.local_uploaded_filename = uploaded_file.name
        st.session_state.local_data = data
        st.session_state.local_clips = data["clips"]
        st.session_state.local_current_clip = None
        st.session_state.local_validated_clips = set()
        st.session_state.local_validations = []
        st.rerun()

    st.sidebar.success(
        f"✅ Loaded **{st.session_state.local_data['total_clips']}** clips"
    )
    return True


def render_local_confidence_filter():
    """Render minimum confidence threshold slider."""
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Confidence Filter")

    threshold = st.sidebar.slider(
        "Minimum BirdNET confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.05,
        help="Only show clips with at least one detection above this confidence",
    )
    return threshold


def render_local_species_filter():
    """Render species filter multiselect.

    Returns list of selected species or None for all species.
    """
    st.sidebar.markdown("---")
    st.sidebar.header("🐦 Species Filter")

    clips = st.session_state.get("local_clips", [])
    if not clips:
        return None

    available_species = get_unique_species(clips)

    filter_enabled = st.sidebar.checkbox(
        "Filter by species",
        value=False,
        help="Enable to select specific species to validate",
    )

    if not filter_enabled:
        st.sidebar.info(f"📊 Showing all {len(available_species)} species")
        return None

    selected = st.sidebar.multiselect(
        "Select species:",
        options=available_species,
        default=[],
        placeholder="Select species...",
    )

    if selected:
        st.sidebar.success(f"✅ Filtering to {len(selected)} species")
        return selected

    st.sidebar.warning("⚠️ Select at least one species or disable filter")
    return None


def get_local_user_selections():
    """Orchestrate all local mode sidebar selections.

    Returns dict with confidence_threshold and species_filter, or None.
    """
    is_uploaded = render_local_upload()

    if not is_uploaded:
        return None

    confidence_threshold = render_local_confidence_filter()
    species_filter = render_local_species_filter()

    return {
        "confidence_threshold": confidence_threshold,
        "species_filter": species_filter,
    }
