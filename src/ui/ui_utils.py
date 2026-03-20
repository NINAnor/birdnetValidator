"""Shared UI Components."""

import io
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st


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
    logo_path = Path("/app/assets/logo.png")
    if logo_path.exists():
        st.sidebar.image(logo_path, width=300)
        st.sidebar.markdown("---")


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
    from utils import extract_clip

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
