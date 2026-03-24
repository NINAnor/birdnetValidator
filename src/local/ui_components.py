"""Local Mode UI Components."""

import streamlit as st

from ui.ui_utils import (
    render_all_validated_message,
    render_audio_player,
    render_spectrogram,
)


def render_local_page_header():
    """Render local mode page header."""
    st.title("🐦 BirdNET Validator", text_alignment="center")
    st.markdown(
        "Validate bird species detections from BirdNET.",
        text_alignment="center",
    )


def render_local_help_section():
    """Render local mode help information."""
    with st.expander("ℹ️ Instructions", expanded=False):
        st.markdown("""### 📖 How to use

**Getting Started:**
1. Copy `.env.example` to `.env` and set your three directory paths (local or `s3://`)
2. For S3, also set `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY`
3. Run the app with `uv run streamlit run src/dashboard.py`
4. **Adjust** the confidence threshold and species filters in the sidebar

**Validation Process:**
1. **Listen** to each audio clip
2. **Select** which species you can actually hear from the BirdNET detections
3. **Add** any additional species not detected by BirdNET
4. **Rate** your confidence and submit
5. **Download** your validation results as CSV when done

**Expected File Format:**
- Audio files: `.wav`, `.flac`, `.mp3`, `.ogg`
- BirdNET results: tab-separated `.txt` files with columns including \
`Begin Time (s)`, `Common Name`, `Confidence`, `Begin Path`
""")


def render_local_clip_section(result, selections):
    """Render the local mode audio clip section.

    Returns True if clip was loaded successfully.
    """
    from utils import extract_clip

    if not result:
        st.warning("No clips to validate")
        return False

    if result.get("all_validated"):
        render_all_validated_message(
            mode_name="clips",
            total_clips=result["total_clips"],
            extra_message="All detections have been validated!",
        )
        return False

    with st.container(border=True):
        st.markdown("### 🎵 Audio Clip")

        filepath = result["filename"]
        clip = extract_clip(filepath, result["start_time"])

        audio_basename = result.get(
            "audio_basename", filepath.split("/")[-1]
        )
        st.markdown(f"**📁 File:** `{audio_basename}`")
        st.markdown(
            f"**⏱️ Detection time:** "
            f"`{result['start_time']}s - {result['end_time']}s`"
        )

        validated_count = result.get("validated_count")
        total_filtered = result.get("total_filtered")
        if total_filtered is not None:
            st.markdown(f"**📊 Progress:** `{validated_count}` / `{total_filtered}` clips validated")

        render_audio_player(clip)
        render_spectrogram(filepath, result["start_time"], expanded=True)
        _render_local_navigation_button()

    return True


def _render_local_navigation_button():
    """Render skip/next clip button."""
    if st.button(
        "🔄 Skip / Load Next Clip",
        help="Skip this clip for now — it will come back after the others",
    ):
        current_clip = st.session_state.get("local_current_clip")
        if current_clip and not current_clip.get("all_validated"):
            if "local_skipped_clips" not in st.session_state:
                st.session_state.local_skipped_clips = set()
            st.session_state.local_skipped_clips.add(
                (current_clip["filename"], current_clip["start_time"])
            )

        st.session_state.local_current_clip = None
        st.session_state.local_form_key = (
            st.session_state.get("local_form_key", 0) + 1
        )
        st.rerun()


def render_local_download_button():
    """Render download button for validation results CSV."""
    import pandas as pd

    validations = st.session_state.get("local_validations", [])
    if not validations:
        return

    df = pd.DataFrame(validations)
    csv = df.to_csv(index=False)
    st.download_button(
        label=f"📥 Download Validations ({len(validations)} clips)",
        data=csv,
        file_name="birdnet_validations.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_local_empty_placeholder():
    """Render placeholder when no clip is loaded."""
    with st.container(border=True):
        st.markdown("### 🎯 Validation")
        st.info("📁 Set AUDIO_DIR, RESULTS_DIR, and OUTPUT_DIR in your .env file (local paths or s3:// URIs).")
