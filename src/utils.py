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
    "ar": "العربية (Arabic)",
    "da": "Dansk (Danish)",
    "de": "Deutsch (German)",
    "es": "Español (Spanish)",
    "fr": "Français (French)",
    "it": "Italiano (Italian)",
    "ja": "日本語 (Japanese)",
    "ko": "한국어 (Korean)",
    "nl": "Nederlands (Dutch)",
    "no": "Norsk (Norwegian)",
    "pl": "Polski (Polish)",
    "pt": "Português (Portuguese)",
    "pt_br": "Português brasileiro (Brazilian Portuguese)",
    "ru": "Русский (Russian)",
    "sv": "Svenska (Swedish)",
    "th": "ไทย (Thai)",
    "tr": "Türkçe (Turkish)",
    "uk": "Українська (Ukrainian)",
    "zh": "中文 (Chinese)",
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


@st.cache_data
def _build_scientific_name_map():
    """Build a dict mapping en_uk names to scientific names."""
    df = load_species_translations()
    return dict(zip(df["en_uk"], df["Scientific_Name"], strict=False))


def get_scientific_name(common_name):
    """Get the scientific name for an English common name."""
    mapping = _build_scientific_name_map()
    return mapping.get(common_name)


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

        duration = len(audio_data) / sr
        clip_start = max(0.0, start_time - context_before)
        clip_end = min(duration, start_time + context_after)

        start_sample = int(clip_start * sr)
        end_sample = int(clip_end * sr)

        clip = audio_data[start_sample:end_sample]
        if len(clip) < sr // 10:  # less than 0.1s — too short
            st.warning("Audio clip too short at this position")
            return None
        return clip
    except Exception as e:
        st.error(f"Error loading audio file: {e}")
        return None
