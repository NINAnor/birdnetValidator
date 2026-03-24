"""UI Components — page layout, audio player, spectrogram, navigation."""

import io
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

from utils import extract_clip


# ---------------------------------------------------------------------------
# Page config & logo
# ---------------------------------------------------------------------------


def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="BirdNET Validator",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="🐦",
    )


def render_sidebar_logo():
    """Render the TABMON logo in the sidebar."""
    logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=300)
        st.sidebar.markdown("---")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def render_all_validated_message(mode_name, total_clips, extra_message=""):
    """Render success message when all clips are validated."""
    st.success(
        f"🎉 Congratulations! All {total_clips} {mode_name} have been validated!"
    )
    st.info(f"✅ {extra_message}" if extra_message else "✅ All validations complete!")
    st.balloons()


@st.cache_data(show_spinner=False)
def _generate_spectrogram_image(file_path, start_time):
    """Generate spectrogram as PNG bytes (cached by path + start_time)."""
    clip = extract_clip(file_path, start_time)
    if clip is None:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))
    Pxx, freqs, bins, im = ax.specgram(
        clip,
        Fs=48000,
        NFFT=1024,
        noverlap=512,
        cmap="viridis",
        vmin=-120,
    )
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Time (s)")
    ax.set_ylim(0, 12000)

    # Mark the 3s BirdNET detection window (1s to 4s in the 5s clip)
    ax.axvline(x=1.0, color="red", linestyle="--", linewidth=1.5, alpha=0.8)
    ax.axvline(x=4.0, color="red", linestyle="--", linewidth=1.5, alpha=0.8)

    plt.colorbar(im, ax=ax, label="Intensity (dB)")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_spectrogram(file_path, start_time, expanded=False):
    """Render audio spectrogram."""
    with st.expander("📊 Spectrogram", expanded=expanded):
        img_bytes = _generate_spectrogram_image(file_path, start_time)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
            st.caption(
                "🔴 Red lines mark the 3-second BirdNET detection. "
                "Focus your validation there — the surrounding audio "
                "is for context only."
            )
        else:
            st.warning("Could not generate spectrogram")


def render_audio_player(clip):
    """Render audio player widget."""
    st.audio(clip, format="audio/wav", sample_rate=48000)


# ---------------------------------------------------------------------------
# Page sections
# ---------------------------------------------------------------------------


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
