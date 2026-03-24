"""Local Mode Session Management."""

import uuid

import streamlit as st


def initialize_local_session():
    """Initialize local mode session state variables."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]

    defaults = {
        "local_current_clip": None,
        "local_path_key": None,
        "local_data": None,
        "local_clips": [],
        "local_validated_clips": set(),
        "local_validations": [],
        "local_form_key": 0,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _get_filtered_clips(selections):
    """Get clips filtered by confidence threshold and species selection."""
    clips = st.session_state.get("local_clips", [])

    confidence_range = selections.get("confidence_range", (0.0, 1.0))
    species_filter = selections.get("species_filter")

    filtered = []
    for clip in clips:
        # At least one detection must fall within the confidence range
        max_confidence = (
            max(clip["confidence_array"]) if clip["confidence_array"] else 0
        )
        if max_confidence < confidence_range[0] or max_confidence > confidence_range[1]:
            continue

        # If species filter is set, at least one detected species must match
        if species_filter:
            if not any(species in species_filter for species in clip["species_array"]):
                continue

        filtered.append(clip)

    return filtered


def get_or_load_local_clip(selections):
    """Get the current clip or load the next unvalidated one.

    Returns clip dict or {"all_validated": True} if no clips remain.
    """
    filtered_clips = _get_filtered_clips(selections)
    validated = st.session_state.get("local_validated_clips", set())
    skipped = st.session_state.get("local_skipped_clips", set())

    unvalidated = [
        clip
        for clip in filtered_clips
        if (clip["filename"], clip["start_time"]) not in validated
    ]

    if not unvalidated:
        return {
            "all_validated": True,
            "total_clips": len(filtered_clips),
        }

    # Return current clip if it's still valid
    current = st.session_state.get("local_current_clip")
    total_filtered = len(filtered_clips)
    validated_count = total_filtered - len(unvalidated)

    if current and not current.get("all_validated"):
        if (current["filename"], current["start_time"]) not in validated:
            current["remaining"] = len(unvalidated)
            current["total_filtered"] = total_filtered
            current["validated_count"] = validated_count
            return current

    # Prefer unskipped clips; fall back to skipped ones when all others are done
    unskipped = [
        clip
        for clip in unvalidated
        if (clip["filename"], clip["start_time"]) not in skipped
    ]
    if unskipped:
        next_clip = unskipped[0]
    else:
        # All remaining clips were skipped — reset skips and cycle back
        st.session_state.local_skipped_clips = set()
        next_clip = unvalidated[0]

    next_clip["all_validated"] = False
    next_clip["remaining"] = len(unvalidated)
    next_clip["total_filtered"] = total_filtered
    next_clip["validated_count"] = validated_count
    st.session_state.local_current_clip = next_clip
    return next_clip
