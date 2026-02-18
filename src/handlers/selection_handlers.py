"""Expert Mode Selection Handlers.
Manages dataset selection, user authentication, species filtering and language selection.
"""

import streamlit as st

from config import EXPERT_DATASETS_FOLDER, LANGUAGE_MAPPING
from database.queries import (
    check_user_has_annotations,
    get_species_for_user,
    list_available_datasets,
)
from ui.ui_utils import render_sidebar_logo
from utils import get_species_display_names


def render_dataset_selection():
    """Render dataset selection dropdown.
    Returns (is_selected, dataset_path).
    """
    render_sidebar_logo()
    st.sidebar.header("📊 Select Annotation Dataset")

    if (
        "expert_selected_dataset" in st.session_state
        and st.session_state.expert_selected_dataset
    ):
        dataset_name = st.session_state.expert_selected_dataset.split("/")[-1]
        st.sidebar.success(f"✅ Dataset: **{dataset_name}**")

        if st.sidebar.button("🔄 Change Dataset"):
            st.session_state.expert_selected_dataset = None
            st.session_state.expert_authenticated = False
            st.session_state.expert_user_id = None
            st.rerun()

        return True, st.session_state.expert_selected_dataset

    # Load available datasets
    with st.spinner("Loading available datasets..."):
        datasets = list_available_datasets()

    if not datasets:
        st.sidebar.error("❌ No annotation datasets found")
        st.sidebar.info(f"Looking in: {EXPERT_DATASETS_FOLDER}")
        return False, None

    # Display dataset selection
    dataset_options = {ds["name"]: ds["path"] for ds in datasets}

    selected_name = st.sidebar.selectbox(
        "Choose a dataset:",
        options=list(dataset_options.keys()),
        help="Select the annotation dataset you want to work on",
    )

    if st.sidebar.button("📂 Select Dataset", type="primary"):
        selected_path = dataset_options[selected_name]
        st.session_state.expert_selected_dataset = selected_path
        st.rerun()

    return False, None


def render_pro_authentication():
    """Render authentication form for Expert mode.
    Returns (is_authenticated, user_id).
    """
    st.sidebar.markdown("---")
    st.sidebar.header("🔐 Expert Mode Authentication")

    if (
        "expert_authenticated" in st.session_state
        and st.session_state.expert_authenticated
    ):
        user_id = st.session_state.expert_user_id
        st.sidebar.success(f"✅ Authenticated as: **{user_id}**")

        if st.sidebar.button("🚪 Logout"):
            st.session_state.expert_authenticated = False
            st.session_state.expert_user_id = None
            st.rerun()

        return True, user_id

    user_id = st.sidebar.text_input(
        "Enter Your User ID",
        help="Enter the user ID assigned to you for annotation tasks",
        placeholder="e.g., user001",
    )

    if st.sidebar.button("🔓 Login", type="primary"):
        if not user_id or not user_id.strip():
            st.sidebar.error("❌ Please enter a user ID.")
            return False, None

        user_id = user_id.strip()

        # Check if user has any assigned annotations
        if check_user_has_annotations(user_id):
            st.session_state.expert_authenticated = True
            st.session_state.expert_user_id = user_id
            st.rerun()
        else:
            st.sidebar.error(f"❌ No annotations found for user ID: {user_id}")
            return False, None

    st.sidebar.info("Please enter your user ID to continue")
    return False, None


def render_species_filter(user_id, dataset_path, language_code):
    """Render species filter selection.

    Args:
        user_id: User ID
        dataset_path: Path to the dataset
        language_code: Language code for species name display

    Returns list of selected species (scientific names), or None for all species.
    """
    st.sidebar.markdown("---")
    st.sidebar.header("🐦 Species Filter")

    # Get available species for this user
    available_species = get_species_for_user(user_id, dataset_path)

    if not available_species:
        st.sidebar.warning("No species found in dataset")
        return None

    # Option to filter or annotate all
    filter_enabled = st.sidebar.checkbox(
        "Filter by species",
        value=False,
        help="Enable to select specific species to annotate",
    )

    if not filter_enabled:
        st.sidebar.info(f"📊 Annotating all {len(available_species)} species")
        return None

    # Get display names for species in selected language
    display_name_map = get_species_display_names(available_species, language_code)
    # display_name_map is {display_name: scientific_name}
    display_options = sorted(display_name_map.keys())

    # Multi-select for species (shows display names)
    selected_display_names = st.sidebar.multiselect(
        "Select species to annotate:",
        options=display_options,
        default=[],
        help="Choose which species you want to focus on",
        placeholder="Select species...",
    )

    if selected_display_names:
        # Convert display names back to scientific names
        selected_species = [display_name_map[dn] for dn in selected_display_names]
        st.sidebar.success(f"✅ Filtering to {len(selected_species)} species")
        return selected_species
    else:
        st.sidebar.warning("⚠️ Select at least one species or disable filter")
        return None


def get_pro_user_selections():
    """Get user selections for Expert mode.
    Returns dict with dataset, user_id, species_filter and language_code, or None.
    """
    # Step 1: Dataset selection
    is_dataset_selected, dataset_path = render_dataset_selection()

    if not is_dataset_selected:
        return None

    # Step 2: User authentication
    is_authenticated, user_id = render_pro_authentication()

    if not is_authenticated:
        return None

    st.sidebar.markdown("---")
    st.sidebar.info(f"👤 **User:** {user_id}")

    # Step 3: Language selection (before species filter so it affects display)
    selected_language = st.sidebar.selectbox(
        "Species Name Language",
        options=["Scientific Names"] + list(LANGUAGE_MAPPING.keys()),
        help="Choose the language for species names",
    )

    language_code = (
        "Scientific_Name"
        if selected_language == "Scientific Names"
        else LANGUAGE_MAPPING[selected_language]
    )

    # Step 4: Species filter (optional, uses selected language)
    species_filter = render_species_filter(user_id, dataset_path, language_code)

    return {
        "dataset_path": dataset_path,
        "user_id": user_id,
        "species_filter": species_filter,
        "confidence_threshold": 0.0,
        "language_code": language_code,
    }
