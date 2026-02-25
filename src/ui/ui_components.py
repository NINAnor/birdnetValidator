"""Expert Mode UI Components."""

import os

import streamlit as st

from ui.ui_utils import (
    clear_cache_functions,
    render_all_validated_message,
    render_audio_player,
    render_clip_metadata,
    render_spectrogram,
)


def render_pro_page_header():
    """Render the Expert mode page header."""
    st.title("🎓 TABMON Listening Lab - for Experts!", text_alignment="center")
    st.markdown(
        "Welcome to the Expert annotation mode. "
        "You have been assigned specific clips "
        "to annotate with detailed species identification. "
        "Please carefully listen to each clip and select "
        "all species you can identify."
        "**Note that the app initialization may take a minute or two.**",
        text_alignment="center",
    )


def render_pro_help_section():
    """Render Expert mode help information."""
    with st.expander("ℹ️ Instructions", expanded=False):
        st.markdown("""### 📖 How to use this annotation platform

**Annotation Process:**
1. **Login** with your assigned User ID
2. **Listen** to the assigned audio clip
3. **Select all species** you can identify from the checklist
4. **Add additional species** not in the list if needed
5. **Rate your confidence** and audio quality
6. **Submit** your annotations

**Tips for Better Annotations:**
- 🎧 Use good quality headphones
- 🔊 Listen to the entire clip, sometimes multiple times
- 🔍 Check the spectrogram for visual confirmation
- 📝 Add notes about uncertainties or background noise
""")

        st.markdown("""### 🎯 Quality Guidelines

- **High Confidence:** Clear vocalization, easily identifiable
- **Moderate Confidence:** Recognizable but with some uncertainty
- **Low Confidence:** Difficult to identify, background noise, or distant calls
""")


def render_pro_clip_section(result, selections):
    """
    Render the Expert mode audio clip section.

    Args:
        result: Dictionary containing clip information
        selections: Dictionary containing user selections

    Returns:
        bool: True if clip was loaded successfully, False otherwise
    """
    from utils import extract_clip

    if not result:
        st.warning(f"No clips assigned for user {selections['user_id']}")
        return False

    if result.get("all_validated"):
        render_all_validated_message(
            mode_name="assigned clips",
            total_clips=result["total_clips"],
            extra_message=(
                "Your annotation work is complete. Thank you for your contribution!"
            ),
        )
        return False

    with st.container(border=True):
        st.markdown("### 🎵 Audio Clip")

        filepath = result["filename"].replace("bugg_RpiID", "bugg_RPiID")
        full_path = f"s3://{os.getenv('S3_BUCKET')}/{filepath}"
        clip = extract_clip(full_path, result["start_time"])

        render_clip_metadata(result)
        render_audio_player(clip)
        render_spectrogram(full_path, result["start_time"], expanded=True)
        render_pro_load_new_button()

    # Prefetch the next clip's audio and spectrogram into cache
    _prefetch_next_clip_audio()

    return True


def _prefetch_next_clip_audio():
    """Prefetch the next clip's audio and spectrogram into cache."""
    from ui.ui_utils import _generate_spectrogram_image
    from utils import extract_clip

    clip_queue = st.session_state.get("expert_clip_queue", [])
    if clip_queue:
        next_clip = clip_queue[0]
        if not next_clip.get("all_validated"):
            filepath = next_clip["filename"].replace("bugg_RpiID", "bugg_RPiID")
            full_path = f"s3://{os.getenv('S3_BUCKET')}/{filepath}"
            # Warm caches for the next clip
            extract_clip(full_path, next_clip["start_time"])
            _generate_spectrogram_image(full_path, next_clip["start_time"])


def render_pro_load_new_button():
    """Render the load new detection button for Expert mode."""
    if st.button("🔄 Load Next Clip", help="Get the next assigned clip to annotate"):
        # Add current clip to skipped set so it won't be shown again
        current_clip = st.session_state.get("expert_current_clip")
        if current_clip and not current_clip.get("all_validated"):
            filename = current_clip.get("filename")
            start_time = current_clip.get("start_time")
            if filename and start_time is not None:
                if "expert_skipped_clips_session" not in st.session_state:
                    st.session_state.expert_skipped_clips_session = set()
                st.session_state.expert_skipped_clips_session.add(
                    (filename, start_time)
                )

        st.session_state.expert_current_clip = None

        # Increment form key to reset validation form fields
        st.session_state.expert_form_key = (
            st.session_state.get("expert_form_key", 0) + 1
        )

        from database.queries import (
            get_assigned_clips_for_user,
            get_remaining_pro_clips_count,
            get_validated_pro_clips,
        )

        clear_cache_functions(
            get_validated_pro_clips,
            get_assigned_clips_for_user,
            get_remaining_pro_clips_count,
        )
        st.rerun()


def render_pro_empty_validation_placeholder():
    """Render placeholder when no Expert validation form should be shown."""
    with st.container(border=True):
        st.markdown("### 🎯 Expert Validation")
        st.info("Please login with your User ID to access your assigned clips.")


def render_pro_all_validated_placeholder():
    """Render message when all Expert clips have been validated."""
    with st.container(border=True):
        st.markdown("### 🎯 Expert Validation")
        st.success("🎉 All assigned clips have been annotated! Great work!")
