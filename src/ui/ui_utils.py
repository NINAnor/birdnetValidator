"""Shared UI Components."""

from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st


def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="TABMON Listening Lab",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="🐦",
    )


def render_sidebar_logo():
    """Render the TABMON logo in the sidebar."""
    logo_path = Path("/app/assets/tabmon_logo.png")
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
def _generate_spectrogram_image(s3_url, start_time):
    """Generate spectrogram as PNG bytes (cached by URL + start_time)."""
    import io

    from utils import extract_clip

    clip = extract_clip(s3_url, start_time)
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
    plt.colorbar(im, ax=ax, label="Intensity (dB)")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_spectrogram(s3_url, start_time, expanded=False):
    """Render audio spectrogram."""
    with st.expander("📊 Spectrogram", expanded=expanded):
        img_bytes = _generate_spectrogram_image(s3_url, start_time)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
        else:
            st.warning("Could not generate spectrogram")


def render_audio_player(clip):
    """Render audio player widget."""
    st.audio(clip, format="audio/wav", sample_rate=48000)


def _parse_recording_datetime(filename):
    """Parse recording datetime from filename like 2025-02-09T01_54_51.065Z."""
    import re

    match = re.search(r"(\d{4}-\d{2}-\d{2})T(\d{2}_\d{2}_\d{2})", filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2).replace("_", ":")
        return f"{date_str} {time_str}"
    return None


def _get_site_info(deployment_id):
    """Look up site name and cluster from deployment_id.

    Extracts the device_id (last segment after '_') from deployment_id
    and maps it to site/cluster info via site_info.csv.

    Returns (site_name, cluster) tuple.
    """
    from database.queries import get_device_site_map

    device_site_map = get_device_site_map()
    if not device_site_map:
        return deployment_id, None

    # Extract device_id: last segment of deployment_id (e.g. 3b425ce9)
    device_id = (
        deployment_id.rsplit("_", 1)[-1] if "_" in deployment_id else deployment_id
    )

    info = device_site_map.get(device_id)
    if info:
        return info["site"], info["cluster"]
    return deployment_id, None


def render_clip_metadata(result):
    """Render clip metadata including filename, site and detection time."""
    filename = result.get("filename", "").split("/")[-1]
    deployment_id = result.get("deployment_id", "")
    start_time = result.get("start_time", "")

    recording_dt = _parse_recording_datetime(filename)
    if recording_dt and start_time is not None:
        from datetime import datetime, timedelta

        try:
            base_dt = datetime.strptime(recording_dt, "%Y-%m-%d %H:%M:%S")
            detection_dt = base_dt + timedelta(seconds=float(start_time))
            detection_str = detection_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            detection_str = recording_dt
    else:
        detection_str = None

    if deployment_id:
        site_name, cluster = _get_site_info(deployment_id)
        st.markdown(f"**📍 Site:** `{site_name}`")
        if cluster:
            st.markdown(f"**🏘️ Cluster:** `{cluster}`")
    if detection_str:
        st.markdown(f"**🔊 Detection time:** `{detection_str}`")


def clear_cache_functions(*functions):
    """Clear cache for multiple functions."""
    for func in functions:
        if hasattr(func, "clear"):
            func.clear()
