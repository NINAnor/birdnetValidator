"""Utility functions — audio extraction, species translations."""

import io

import librosa
import pandas as pd
import streamlit as st

from config import BIRDNET_MULTILINGUAL_PATH
from s3_utils import is_s3_path, read_s3_bytes


@st.cache_data
def load_species_translations():
    """Load the multilingual species name translations."""
    return pd.read_csv(BIRDNET_MULTILINGUAL_PATH)


LANGUAGE_OPTIONS = {
    "en_uk": "English",
    "fr": "Français",
    "es": "Español",
    "nl": "Nederlands",
    "no": "Norsk",
}


@st.cache_data
def _build_translation_map(language):
    """Build a dict mapping en_uk names to the target language."""
    df = load_species_translations()
    if language == "en_uk" or language not in df.columns:
        return {}
    return dict(zip(df["en_uk"], df[language], strict=False))


def translate_species_name(name, language):
    """Translate an English species name to the chosen language.

    Returns the original name if no translation is available.
    """
    if language == "en_uk":
        return name
    mapping = _build_translation_map(language)
    return mapping.get(name, name)


@st.cache_data(ttl=600, show_spinner=False)
def extract_clip(file_path, start_time, context_before=1, context_after=4, sr=48000):
    """Extract audio clip around a detection start time.

    The BirdNET detection window is 3 seconds (start_time to start_time + 3).
    context_before and context_after are measured from the detection start.
    Default: 1s before + 4s after = 5s total (detection at 1s–4s).

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

        start_sample = max(0, int((start_time - context_before) * sr))
        end_sample = int((start_time + context_after) * sr)
        return audio_data[start_sample:end_sample]
    except Exception as e:
        st.error(f"Error loading audio file: {e}")
        return None
