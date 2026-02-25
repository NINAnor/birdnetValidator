"""
Validation Handlers for the TABMON Listening Lab dashboard.

This module handles the validation form rendering, user input collection,
and submission of validation responses.
"""

import pandas as pd
import streamlit as st

from queries import get_all_clips_for_species, get_remaining_clips_count
from utils import save_validation_response


def render_validation_form(result, selections):
    """
    Render the validation form and handle submission.

    Args:
        result: Dictionary containing clip information
        selections: Dictionary containing user selections
    """
    with st.container(border=True):
        st.markdown("### 🎯 Validation")

        # Show remaining clips count with progress bar
        remaining_clips = get_remaining_clips_count(
            selections["country"],
            selections["device"],
            selections["species"],
            selections["confidence_threshold"],
        )
        _, total_clips = get_all_clips_for_species(
            selections["country"],
            selections["device"],
            selections["species"],
            selections["confidence_threshold"],
        )
        validated_count = max(0, total_clips - remaining_clips)

        if total_clips > 0:
            progress = validated_count / total_clips
            st.progress(progress)
            st.caption(
                f"✅ {validated_count}/{total_clips} clips validated "
                f"({remaining_clips} remaining)"
            )
        if remaining_clips <= 0:
            st.success("🎉 All clips validated for these parameters!")

        # Session counter
        session_count = st.session_state.get("session_validation_count", 0)
        if session_count > 0:
            st.caption(
                f"🏆 You've validated **{session_count}** clip"
                f"{'s' if session_count != 1 else ''} this session!"
            )

        with st.form("validation_form"):
            st.markdown(f"#### Is this detection a {selections['species_display']}?")

            # Reference links for the species
            species_wiki_name = selections["species"].replace(" ", "_")
            wiki_url = f"https://en.wikipedia.org/wiki/{species_wiki_name}"
            xc_query = selections["species"].replace(" ", "+")
            xc_url = f"https://xeno-canto.org/explore?query={xc_query}"
            st.markdown(
                f"ℹ️ [Wikipedia]({wiki_url}) · 🔊 [Listen on xeno-canto]({xc_url})",
            )

            validation_response = st.radio(
                "**Your answer:**",
                options=["Yes", "No", "Unsure"],
                index=None,
                horizontal=True,
                help="Help us validate the accuracy of our species detection models!",
            )

            user_validation = st.text_input(
                "**If no, What did you detect instead?**",
                placeholder="e.g., different species, noise, silence, etc.",
                help="Please describe what you actually heard in this audio clip",
            )

            user_confidence = st.radio(
                "**How confident are you in your answer?**",
                options=["Low", "Moderate", "High"],
                index=None,
                horizontal=True,
                help="Rate your confidence in the validation above",
            )

            user_comments = st.text_area(
                "**💬 Comments (optional)**",
                placeholder=(
                    "E.g., 'Faint call in background', 'Multiple species present'..."
                ),
                height=80,
                help="Any additional observations about the clip",
            )

            submitted = st.form_submit_button(
                "✅ Submit Validation", type="primary", use_container_width=True
            )

        if submitted:
            _handle_validation_submission(
                result,
                selections,
                validation_response,
                user_validation,
                user_confidence,
                user_comments,
            )


def _handle_validation_submission(
    result,
    selections,
    validation_response,
    user_validation,
    user_confidence,
    user_comments,
):
    """Handle validation form submission."""
    if validation_response and user_confidence:
        validation_data = {
            "filename": result["filename"],
            "country": selections["country"],
            "site": selections["site_name"],
            "device_id": selections["device"],
            "species": selections["species"],
            "start_time": result["start_time"],
            "confidence": result["confidence"],
            "validation_response": validation_response,
            "user_validation": user_validation,
            "user_confidence": user_confidence,
            "user_comments": user_comments,
            "timestamp": pd.Timestamp.now(),
        }

        save_validation_response(validation_data)

        # Track session progress
        st.session_state.session_validation_count = (
            st.session_state.get("session_validation_count", 0) + 1
        )

        # Clear current clip so the next rerun loads a fresh one
        st.session_state.current_clip = None

        st.toast("✅ Validation saved! Loading next clip...")
        st.rerun()
    else:
        st.error("Please answer both questions before submitting.")
