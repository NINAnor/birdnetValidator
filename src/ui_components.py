"""UI Components — page layout, audio player, spectrogram, navigation."""

import io
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from config import ASSETS_DIR
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
def _is_dark_theme():
    """Detect whether Streamlit is using a dark theme."""
    try:
        base = st.get_option("theme.base")
        if base:
            return base == "dark"
        bg = st.get_option("theme.backgroundColor")
        if bg:
            # Parse hex and check luminance
            r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
            return (0.299 * r + 0.587 * g + 0.114 * b) < 128
    except Exception:
        pass
    # Default to dark (Streamlit's default)
    return True


def _generate_spectrogram_image(file_path, start_time, context_before=1, context_after=4):
    """Generate spectrogram as PNG bytes."""
    clip = extract_clip(file_path, start_time, context_before, context_after)
    if clip is None:
        return None

    dark = _is_dark_theme()

    if dark:
        bg_color = "#0e1117"
        text_color = "#c0c0c0"
        spine_color = "#333333"
        line_color = "cyan"
        cmap = "magma"
    else:
        bg_color = "#f0ece4"
        text_color = "#333333"
        spine_color = "#aaaaaa"
        line_color = "#d62728"
        cmap = "magma"

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    _, _, _, im = ax.specgram(
        clip,
        Fs=48000,
        NFFT=1024,
        noverlap=512,
        cmap=cmap,
        vmin=-120,
    )
    ax.set_ylabel("Frequency (Hz)", color=text_color)
    ax.set_xlabel("Time (s)", color=text_color)
    ax.set_ylim(0, 12000)
    ax.tick_params(colors=text_color)
    for spine in ax.spines.values():
        spine.set_color(spine_color)

    # Mark the 3s BirdNET detection window
    detection_start = context_before
    detection_end = context_before + 3
    ax.axvline(x=detection_start, color=line_color, linestyle="--", linewidth=1.5, alpha=0.8)
    ax.axvline(x=detection_end, color=line_color, linestyle="--", linewidth=1.5, alpha=0.8)

    cbar = plt.colorbar(im, ax=ax, label="Intensity (dB)")
    cbar.ax.yaxis.set_tick_params(color=text_color)
    cbar.ax.yaxis.label.set_color(text_color)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=text_color)
    cbar.outline.set_edgecolor(spine_color)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_spectrogram(file_path, start_time, context_before=1, context_after=4, expanded=False):
    """Render audio spectrogram."""
    with st.expander("📊 Spectrogram", expanded=expanded):
        img_bytes = _generate_spectrogram_image(file_path, start_time, context_before, context_after)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
            line_label = "Cyan" if _is_dark_theme() else "Red"
            st.caption(
                f"🔵 {line_label} lines mark the 3-second BirdNET detection. "
                "Focus your validation there — the surrounding audio "
                "is for context only."
            )
        else:
            st.warning("Could not generate spectrogram")


def render_audio_player(clip):
    """Render audio player widget."""
    if clip is None:
        st.warning("No audio available for this clip")
        return
    st.audio(clip, format="audio/wav", sample_rate=48000)


# ---------------------------------------------------------------------------
# Page sections
# ---------------------------------------------------------------------------


@st.dialog(" ", width="small")
def _show_welcome_dialog():
    """Show welcome dialog with logo and instructions."""
    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(str(logo_path), use_container_width=True)

    st.markdown("""
<h3 style="text-align: center;">Welcome to BirdNET Validator!</h3>

<div style="text-align: center;">

🎧 **Listen** to each audio clip and inspect the spectrogram

✅ **Select** which species you can actually hear

➕ **Add** any species missed by the classifier

📝 Optionally tag background sounds and leave comments

🎯 **Rate** your confidence and **submit**

📥 **Download** your results as CSV when done

<br>

*Use the sidebar to adjust confidence range, language, and species filters.*

</div>
""", unsafe_allow_html=True)

    if st.button("Let's go! 🚀", type="primary", use_container_width=True):
        st.session_state.welcome_dismissed = True
        st.rerun()


def render_welcome_dialog():
    """Show welcome dialog on first visit."""
    if not st.session_state.get("welcome_dismissed", False):
        _show_welcome_dialog()


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

    st.markdown("### 🎵 Audio Clip")

    with st.container(border=True):
        filepath = result["filename"]

        audio_basename = result.get(
            "audio_basename", filepath.split("/")[-1]
        )
        st.markdown(f"**📁 File:** `{audio_basename}`")
        st.markdown(
            f"**⏱️ Detection time:** "
            f"`{result['start_time']}s - {result['end_time']}s`"
        )

        # Context duration slider
        context_seconds = st.slider(
            "🔍 Context around detection (seconds)",
            min_value=1,
            max_value=5,
            value=1,
            step=1,
            help="Extra seconds of audio before and after the 3s BirdNET detection",
        )
        context_before = context_seconds
        context_after = context_seconds + 3  # detection is 3s

        clip = extract_clip(filepath, result["start_time"], context_before, context_after)
        render_audio_player(clip)
        render_spectrogram(filepath, result["start_time"], context_before, context_after, expanded=True)

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
    """Render download button for all validation results (all annotators)."""
    from s3_utils import is_s3_path, list_s3_files, read_s3_text
    from selection_handlers import VALIDATIONS_PREFIX

    output_dir = st.session_state.get("local_output_dir")
    if not output_dir:
        return

    all_dfs = []
    if is_s3_path(output_dir):
        all_files = list_s3_files(output_dir, extension=".csv")
        csv_files = [
            f for f in all_files
            if f.split("/")[-1].startswith(VALIDATIONS_PREFIX)
        ]
        for csv_uri in csv_files:
            text = read_s3_text(csv_uri)
            all_dfs.append(pd.read_csv(io.StringIO(text)))
    else:
        for csv_path in Path(output_dir).glob(f"{VALIDATIONS_PREFIX}*.csv"):
            all_dfs.append(pd.read_csv(csv_path))

    if not all_dfs:
        return

    merged = pd.concat(all_dfs, ignore_index=True)
    csv = merged.to_csv(index=False)
    st.download_button(
        label=f"📥 Download All Validations ({len(merged)} clips)",
        data=csv,
        file_name="birdnet_validations_all.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_local_empty_placeholder():
    """Render placeholder when no clip is loaded."""
    st.info("👤 Enter your name in the sidebar to start validating.")
