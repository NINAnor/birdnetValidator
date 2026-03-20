"""Local Mode Validation Handlers."""

import pandas as pd
import streamlit as st

from utils import load_species_translations


@st.cache_data
def _get_all_species_list_local():
    """Get all species English common names for autocomplete."""
    translations_df = load_species_translations()
    return sorted(translations_df["en_uk"].dropna().tolist())


def render_local_validation_form(result, selections):
    """Render the validation form for local mode."""
    with st.container(border=True):
        st.markdown("### 🎯 Validation")

        remaining = result.get("remaining", 0)
        if remaining:
            st.info(f"📊 **{remaining}** clips remaining")

        form_key = st.session_state.get("local_form_key", 0)

        with st.form(f"local_validation_form_{form_key}"):
            st.markdown("#### Species detected by BirdNET:")
            st.markdown("**Select which species you can actually hear:**")
            st.markdown("---")

            species_list = result.get("species_array", [])
            confidence_list = result.get("confidence_array", [])

            # Sort by confidence descending
            species_data = sorted(
                zip(species_list, confidence_list, strict=False),
                key=lambda x: x[1],
                reverse=True,
            )

            selected_species = []
            for index, (species, confidence) in enumerate(species_data):
                if st.checkbox(
                    f"{species} (BirdNET conf: {confidence:.2f})",
                    key=f"local_species_{index}_{form_key}",
                ):
                    selected_species.append(species)

            none_of_above = st.checkbox(
                "❌ None of the above species are present",
                key=f"local_none_{form_key}",
                help=(
                    "Check this if you cannot hear any "
                    "of the species listed above"
                ),
            )
            if none_of_above:
                selected_species = ["NONE_DETECTED"]

            st.markdown("---")

            # Additional species not in BirdNET predictions
            all_species = _get_all_species_list_local()
            other_species = st.multiselect(
                "**Other species not listed above:**",
                options=all_species,
                default=[],
                placeholder="Start typing to search...",
                key=f"local_other_{form_key}",
            )

            st.markdown("---")

            # Noise/sound environment checkboxes
            st.markdown("#### 📝 Additional sounds")
            user_notes = []
            noise_classes = [
                "Loud foreground noise",
                "Rain",
                "Wind",
                "Dog/Bark",
                "Insect/Cricket",
                "Amphibian / Frogs",
                "Construction",
                "Human Voices",
                "Traffic/Car",
                "Aircraft",
                "Water/Waves",
            ]
            mid = (len(noise_classes) + 1) // 2
            noise_col1, noise_col2 = st.columns(2)
            with noise_col1:
                for noise in noise_classes[:mid]:
                    if st.checkbox(noise, key=f"local_{noise}_{form_key}"):
                        user_notes.append(noise)
            with noise_col2:
                for noise in noise_classes[mid:]:
                    if st.checkbox(noise, key=f"local_{noise}_{form_key}"):
                        user_notes.append(noise)

            st.markdown("---")

            # Free-text comments
            st.markdown("#### 💬 Comments")
            user_comments = st.text_area(
                "Additional comments:",
                placeholder=(
                    "E.g., 'Faint call in background', "
                    "'Multiple individuals', "
                    "'Uncertain due to noise'..."
                ),
                height=100,
                key=f"local_comments_{form_key}",
            )

            # Confidence rating
            user_confidence = st.radio(
                "**How confident are you in your annotations?**",
                options=["Low", "Moderate", "High"],
                index=None,
                horizontal=True,
                help="Rate your overall confidence in the species identifications",
            )

            submitted = st.form_submit_button(
                "✅ Submit Validation",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                _handle_local_submission(
                    result,
                    selected_species,
                    other_species,
                    user_notes,
                    user_confidence,
                    user_comments,
                )


def _handle_local_submission(
    result,
    selected_species,
    other_species,
    user_notes,
    user_confidence,
    user_comments,
):
    """Handle local validation form submission."""
    if not user_confidence:
        st.error("Please rate your confidence before submitting.")
        return

    all_identified = selected_species + other_species

    def list_to_string(value):
        if isinstance(value, list):
            return "|".join(str(item) for item in value)
        return value

    validation = {
        "filename": result.get("audio_basename", result["filename"]),
        "start_time": result["start_time"],
        "end_time": result["end_time"],
        "birdnet_species": list_to_string(result.get("species_array", [])),
        "birdnet_confidences": list_to_string(
            result.get("confidence_array", [])
        ),
        "identified_species": list_to_string(all_identified),
        "species_count": len(all_identified),
        "user_confidence": user_confidence,
        "user_notes": list_to_string(user_notes),
        "user_comments": user_comments,
        "timestamp": pd.Timestamp.now().isoformat(),
    }

    # Save to session state
    if "local_validations" not in st.session_state:
        st.session_state.local_validations = []
    st.session_state.local_validations.append(validation)

    # Mark clip as validated
    if "local_validated_clips" not in st.session_state:
        st.session_state.local_validated_clips = set()
    st.session_state.local_validated_clips.add(
        (result["filename"], result["start_time"])
    )

    # Clear current clip and increment form key
    st.session_state.local_current_clip = None
    st.session_state.local_form_key = (
        st.session_state.get("local_form_key", 0) + 1
    )

    st.toast("✅ Validation saved! Loading next clip...")
    st.rerun()
