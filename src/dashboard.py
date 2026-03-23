"""BirdNET Validator - Local Mode Application."""

import streamlit as st

from local.selection_handlers import get_local_user_selections
from local.session_manager import get_or_load_local_clip, initialize_local_session
from local.ui_components import (
    render_local_clip_section,
    render_local_download_button,
    render_local_empty_placeholder,
    render_local_help_section,
    render_local_page_header,
)
from local.validation_handlers import render_local_validation_form
from ui.ui_utils import setup_page_config


def main():
    """Main application entry point."""
    setup_page_config()
    initialize_local_session()
    render_local_page_header()
    render_local_help_section()

    selections = get_local_user_selections()

    if selections is None:
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.container(border=True).info(
                "📁 Set AUDIO_DIR, RESULTS_DIR, and OUTPUT_DIR in your .env file, then restart the app."
            )
        with col2:
            render_local_empty_placeholder()
        return

    st.markdown("---")
    result = get_or_load_local_clip(selections)

    col1, col2 = st.columns([1, 1])
    with col1:
        clip_loaded = render_local_clip_section(result, selections)
    with col2:
        if result and not result.get("all_validated") and clip_loaded:
            render_local_validation_form(result, selections)
        elif result and result.get("all_validated"):
            with st.container(border=True):
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
