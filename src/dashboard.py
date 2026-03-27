"""BirdNET Validator — main application."""

import streamlit as st

from selection_handlers import get_local_user_selections
from session_manager import get_or_load_local_clip, initialize_local_session
from ui_components import (
    render_local_clip_section,
    render_local_download_button,
    render_local_empty_placeholder,
    render_welcome_dialog,
    setup_page_config,
)
from validation_handlers import render_local_validation_form


def main():
    """Main application entry point."""
    setup_page_config()
    initialize_local_session()
    render_welcome_dialog()

    selections = get_local_user_selections()

    if selections is None:
        st.info("👤 Enter your name in the sidebar to start validating.")
        return

    st.markdown("---")
    result = get_or_load_local_clip(selections)

    # Progress bar
    if result and not result.get("all_validated"):
        validated_count = result.get("validated_count", 0)
        total_filtered = result.get("total_filtered", 1)
        st.progress(
            validated_count / total_filtered,
            text=f"📊 {validated_count} / {total_filtered} clips validated",
        )

    col1, col2 = st.columns([1, 1])
    with col1:
        clip_loaded = render_local_clip_section(result, selections)
    with col2:
        if result and not result.get("all_validated") and clip_loaded:
            render_local_validation_form(result, selections)
        elif result and result.get("all_validated"):
            st.markdown("### 🎯 Validation")
            st.success("🎉 All clips validated!")
            render_local_download_button()
        else:
            render_local_empty_placeholder()

    # Always show download button in sidebar if there are validations
    if st.session_state.get("local_validations"):
        st.sidebar.markdown("---")
        with st.sidebar:
            render_local_download_button()


if __name__ == "__main__":
    main()
