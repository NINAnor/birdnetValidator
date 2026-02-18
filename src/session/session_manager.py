"""Expert Mode Session Management."""

import streamlit as st

from database.queries import get_random_assigned_clip
from session.session_utils import (
    check_params_changed,
    init_base_session,
    init_state_vars,
)


def initialize_pro_session():
    """Initialize Expert mode session state variables."""
    init_base_session()
    init_state_vars(
        "expert_",
        {
            "current_clip": None,
            "clip_params": None,
            "authenticated": False,
            "user_id": None,
            "selected_dataset": None,
            "validated_clips_session": set(),
            "remaining_count": None,
        },
    )


def clear_pro_clip_state():
    """Clear all Expert mode clip-related state and caches."""
    st.session_state.expert_current_clip = None
    st.session_state.expert_clip_params = None
    st.session_state.expert_validated_clips_session = set()
    st.session_state.expert_remaining_count = None

    from database.queries import get_remaining_pro_clips_count, get_validated_pro_clips

    get_validated_pro_clips.clear()
    get_remaining_pro_clips_count.clear()


def get_or_load_pro_clip(selections):
    """Get current Expert clip or load a new one if needed."""
    initialize_pro_session()

    # Include dataset_path, user_id, species_filter and language_code in params
    species_filter = selections.get("species_filter")
    species_filter_key = tuple(species_filter) if species_filter else None
    current_params = (
        selections["dataset_path"],
        selections["user_id"],
        species_filter_key,
        selections.get("language_code", "Scientific_Name"),
    )

    # If parameters changed, clear and reload
    if check_params_changed("expert_clip_params", current_params):
        clear_pro_clip_state()
        st.session_state.expert_clip_params = current_params

    # If current clip is None, get new clip
    if st.session_state.expert_current_clip is None:
        # Initialize remaining count on first load
        if st.session_state.expert_remaining_count is None:
            from database.queries import get_remaining_pro_clips_count

            st.session_state.expert_remaining_count = get_remaining_pro_clips_count(
                selections["user_id"],
                selections["dataset_path"],
                species_filter,
            )

        st.session_state.expert_current_clip = get_random_assigned_clip(
            selections["user_id"],
            selections["dataset_path"],
            species_filter,
        )

    return st.session_state.expert_current_clip
