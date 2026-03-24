"""Utility functions for BirdNET Validator."""

import io
import tempfile

import librosa
import pandas as pd
import streamlit as st

from config import BIRDNET_MULTILINGUAL_PATH
from s3_utils import is_s3_path, read_s3_bytes


@st.cache_data
def load_species_translations():
    """Load the multilingual species name translations."""
    return pd.read_csv(BIRDNET_MULTILINGUAL_PATH)


@st.cache_data(ttl=600, show_spinner=False)
def extract_clip(file_path, start_time, sr=48000):
    """Extract 5-second audio clip (1s before + 4s after detection start).

    Supports both local file paths and S3 URIs.
    """
    if not file_path:
        st.error("No audio file path provided")
        return None

    try:
        if is_s3_path(file_path):
            audio_bytes = read_s3_bytes(file_path)
            audio_data, _ = librosa.load(
                io.BytesIO(audio_bytes), sr=sr, mono=True
            )
        else:
            audio_data, _ = librosa.load(file_path, sr=sr, mono=True)

        start_sample = max(0, int((start_time - 1) * sr))
        end_sample = int((start_time + 4) * sr)
        return audio_data[start_sample:end_sample]
    except Exception as e:
        st.error(f"Error loading audio file: {e}")
        return None
