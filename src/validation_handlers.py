"""Validation Handlers."""

from pathlib import Path

import pandas as pd
import streamlit as st

from selection_handlers import VALIDATIONS_PREFIX, _get_validations_filename
from s3_utils import is_s3_path, write_s3_text
from gbif_utils import search_species_for_searchbox
from streamlit_searchbox import st_searchbox
from utils import get_scientific_name, translate_species_name


def render_local_validation_form(result, selections):
    """Render the validation form for local mode."""
    st.markdown("### 🎯 Validation")

    form_key = st.session_state.get("local_form_key", 0)

    # Custom label management — outside the form so Enter doesn't submit
    if "custom_label_options" not in st.session_state:
        st.session_state.custom_label_options = []

    # GBIF species search — outside the form so Enter triggers search, not submit
    if "gbif_selected_species" not in st.session_state:
        st.session_state.gbif_selected_species = {}  # {scientific_name: display}

    # Wrap everything in one bordered container
    with st.container(border=True):

        st.markdown("#### Species detected by BirdNET:")
        st.markdown("**Select which species you can actually hear:**")
        st.markdown("---")

        species_list = result.get("species_array", [])
        confidence_list = result.get("confidence_array", [])
        language = selections.get("language", "en_uk")

        # Sort by confidence descending
        species_data = sorted(
            zip(species_list, confidence_list, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )

        selected_species = []
        for index, (species, confidence) in enumerate(species_data):
            display_name = translate_species_name(species, language)
            if st.checkbox(
                f"{display_name} (BirdNET conf: {confidence:.2f})",
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

        peer_review = st.checkbox(
            "🔄 Request peer review",
            key=f"local_peer_review_{form_key}",
            help=(
                "Check this if you are unsure and want "
                "other annotators to also validate this clip"
            ),
        )

        st.markdown("---")

        # Species info links
        with st.expander("ℹ️ More info on the species", expanded=False, key=f"exp_info_{form_key}"):
            for species_name in species_list:
                scientific = get_scientific_name(species_name)
                links = []
                if scientific:
                    wiki_name = scientific.replace(" ", "_")
                    xc_name = scientific.replace(" ", "-")
                    links.append(f"[Wikipedia](https://en.wikipedia.org/wiki/{wiki_name})")
                    links.append(f"[Xeno-Canto](https://xeno-canto.org/species/{xc_name})")
                label = f"**{species_name}**"
                if scientific:
                    label += f" (*{scientific}*)"
                if links:
                    label += f" — {' · '.join(links)}"
                st.markdown(label)

        # GBIF species search with autocomplete dropdown
        with st.expander("🐦 Other species not listed above", expanded=False, key=f"exp_other_{form_key}"):
            st.caption("Search any species by common or scientific name (powered by GBIF)")
            selected = st_searchbox(
                search_species_for_searchbox,
                placeholder="e.g. Great Tit, Parus major, Red Fox...",
                clear_on_submit=True,
                rerun_scope="fragment",
                key=f"local_gbif_searchbox_{form_key}",
            )
            if selected and selected not in st.session_state.gbif_selected_species:
                # selected is the scientific_name (second tuple element)
                # Re-fetch display name
                st.session_state.gbif_selected_species[selected] = selected
                st.rerun()

            if st.session_state.gbif_selected_species:
                st.markdown("**Selected species:**")
                to_remove = []
                for sci_name in list(st.session_state.gbif_selected_species):
                    col1, col2 = st.columns([5, 1])
                    col1.markdown(f"✅ {sci_name}")
                    if col2.button("❌", key=f"gbif_rm_{sci_name}_{form_key}"):
                        to_remove.append(sci_name)
                if to_remove:
                    for name in to_remove:
                        del st.session_state.gbif_selected_species[name]
                    st.rerun()

        other_species = list(st.session_state.get("gbif_selected_species", {}).keys())

        # Noise/sound environment
        with st.expander("📝 Additional sounds", expanded=False, key=f"exp_noise_{form_key}"):
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
                "Other",
            ]
            user_notes = st.multiselect(
                "Select sounds heard in the clip...",
                options=noise_classes,
                default=[],
                placeholder="Select sounds heard in the clip...",
                key=f"local_noise_{form_key}",
                label_visibility="collapsed",
            )

        # Custom labels management + selection
        custom_labels = []
        if st.session_state.custom_label_options:
            with st.expander("🏷️ Custom labels", expanded=False, key=f"exp_labels_{form_key}"):
                custom_labels = st.multiselect(
                    "Select labels for this clip:",
                    options=sorted(st.session_state.custom_label_options),
                    default=[],
                    placeholder="Select labels...",
                    key=f"local_labels_{form_key}",
                    label_visibility="collapsed",
                )

        with st.expander("🏷️ Manage custom labels", expanded=False, key=f"exp_manage_labels_{form_key}"):
            st.caption("Create labels like *male*, *female*, *call*, *song*, *juvenile*... "
                       "They'll appear above for every clip.")
            new_label = st.text_input(
                "Add a new label:",
                placeholder="Type a label and press Enter...",
                key=f"local_new_label_{form_key}",
            )
            if new_label:
                label_clean = new_label.strip()
                if label_clean and label_clean not in st.session_state.custom_label_options:
                    st.session_state.custom_label_options.append(label_clean)
                    st.rerun()

            if st.session_state.custom_label_options:
                st.markdown("**Current labels:** " + ", ".join(
                    f"`{l}`" for l in sorted(st.session_state.custom_label_options)
                ))

        # Free-text comments
        with st.expander("💬 Comments", expanded=False, key=f"exp_comments_{form_key}"):
            user_comments = st.text_area(
                "Additional comments:",
                placeholder=(
                    "E.g., 'Faint call in background', "
                    "'Multiple individuals', "
                    "'Uncertain due to noise'..."
                ),
                height=80,
                key=f"local_comments_{form_key}",
                label_visibility="collapsed",
            )

        # Confidence rating
        user_confidence = st.radio(
            "**How confident are you in your annotations?**",
            options=["Low", "Moderate", "High"],
            index=None,
            horizontal=True,
            help="Rate your overall confidence in the species identifications",
        )

        submitted = st.button(
            "✅ Submit Validation",
            type="primary",
            use_container_width=True,
            key=f"local_submit_{form_key}",
        )

        if submitted:
            _handle_local_submission(
                result,
                selected_species,
                other_species,
                user_notes,
                user_confidence,
                user_comments,
                peer_review,
                custom_labels,
            )


def _handle_local_submission(
    result,
    selected_species,
    other_species,
    user_notes,
    user_confidence,
    user_comments,
    peer_review,
    custom_labels,
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
        "filepath": result["filename"],
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
        "annotator": st.session_state.get("annotator_name", "unknown"),
        "peer_review": peer_review,
        "custom_labels": list_to_string(custom_labels),
        "timestamp": pd.Timestamp.now().isoformat(),
    }

    # Save to session state
    if "local_validations" not in st.session_state:
        st.session_state.local_validations = []
    st.session_state.local_validations.append(validation)

    # Persist to disk or S3
    output_dir = st.session_state.get("local_output_dir")
    annotator = st.session_state.get("annotator_name", "unknown")
    if output_dir:
        csv_data = pd.DataFrame(st.session_state.local_validations).to_csv(
            index=False
        )
        filename = _get_validations_filename(annotator)
        if is_s3_path(output_dir):
            s3_uri = output_dir.rstrip("/") + "/" + filename
            write_s3_text(s3_uri, csv_data)
        else:
            csv_path = Path(output_dir) / filename
            csv_path.write_text(csv_data)

    # Mark clip as validated
    if "local_validated_clips" not in st.session_state:
        st.session_state.local_validated_clips = set()
    st.session_state.local_validated_clips.add(
        (result["filename"], result["start_time"])
    )

    # Clear current clip, GBIF selection, and increment form key
    st.session_state.local_current_clip = None
    st.session_state.gbif_selected_species = {}
    st.session_state.local_form_key = (
        st.session_state.get("local_form_key", 0) + 1
    )

    st.toast("✅ Validation saved! Loading next clip...")
    st.rerun()
