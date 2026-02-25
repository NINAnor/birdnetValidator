"""Shared utility functions for Expert mode."""

import tempfile
from pathlib import Path

import boto3
import librosa
import pandas as pd
import streamlit as st
from botocore.client import Config

from config import (
    BIRDNET_MULTILINGUAL_PATH,
    S3_ACCESS_KEY_ID,
    S3_ENDPOINT,
    S3_SECRET_ACCESS_KEY,
)


@st.cache_data
def load_species_translations():
    """Load the multilingual species name translations"""
    return pd.read_csv(BIRDNET_MULTILINGUAL_PATH)


def get_species_display_names(species_list, language_code):
    """Convert scientific names to display names in selected language."""
    if language_code == "Scientific_Name":
        return {species: species for species in species_list}

    translations_df = load_species_translations()
    species_map = {}

    for species in species_list:
        translation_row = translations_df[translations_df["Scientific_Name"] == species]
        translated_name = species  # Default fallback

        if not translation_row.empty and language_code in translation_row.columns:
            trans = translation_row[language_code].iloc[0]
            if pd.notna(trans):
                translated_name = trans

        species_map[translated_name] = species

    return species_map


@st.cache_data(ttl=600, show_spinner=False)
def extract_clip(s3_url, start_time, sr=48000):
    """Extract 9-second audio clip from S3 (3s before + 6s after detection)."""
    if not s3_url:
        st.error("Could not find audio file in S3")
        return None

    s3_client = boto3.client(
        "s3",
        endpoint_url=f"https://{S3_ENDPOINT}",
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )

    bucket, key = s3_url.replace("s3://", "").split("/", 1)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        try:
            s3_client.download_file(bucket, key, temp_file.name)
            audio_data, _ = librosa.load(temp_file.name, sr=sr, mono=True)
            start_sample = int((start_time - 1) * sr)
            end_sample = int((start_time + 4) * sr)
            return audio_data[start_sample:end_sample]
        finally:
            Path(temp_file.name).unlink()


def save_pro_validation_response(validation_data):
    """
    Save Expert mode validation to session-specific file.
    Expert validations include multiple species in a list format.
    """
    from config import EXPERT_VALIDATIONS_PREFIX, S3_BUCKET

    session_id = st.session_state.session_id

    # Get dataset name from session state
    dataset_path = st.session_state.get("expert_selected_dataset", "")
    dataset_name = (
        dataset_path.split("/")[-1].replace(".parquet", "")
        if dataset_path
        else "unknown"
    )

    # Configure boto3 for S3 access
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"https://{S3_ENDPOINT}",
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )

    bucket = S3_BUCKET

    key = f"{EXPERT_VALIDATIONS_PREFIX}/{dataset_name}_session_{session_id}.csv"

    # Convert arrays to pipe-separated strings for clean CSV storage
    def list_to_string(value):
        return (
            "|".join(str(item) for item in value) if isinstance(value, list) else value
        )

    validation_data_copy = {
        **validation_data,
        "identified_species": list_to_string(validation_data.get("identified_species")),
        "birdnet_species_detected": list_to_string(
            validation_data.get("birdnet_species_detected")
        ),
        "birdnet_confidences": list_to_string(
            validation_data.get("birdnet_confidences")
        ),
    }

    validation_df = pd.DataFrame([validation_data_copy])

    def save_to_s3(df, bucket, key):
        """Helper to save DataFrame to S3."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".csv", delete=False
        ) as temp_file:
            try:
                df.to_csv(temp_file.name, index=False)
                s3_client.upload_file(temp_file.name, bucket, key)
            finally:
                Path(temp_file.name).unlink()

    try:
        # Append to existing file or create new one
        try:
            s3_client.head_object(Bucket=bucket, Key=key)
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".csv", delete=False
            ) as temp_file:
                try:
                    s3_client.download_file(bucket, key, temp_file.name)
                    existing_df = pd.read_csv(temp_file.name)
                    combined_df = pd.concat(
                        [existing_df, validation_df], ignore_index=True
                    )
                    save_to_s3(combined_df, bucket, key)
                finally:
                    Path(temp_file.name).unlink()
        except Exception:
            save_to_s3(validation_df, bucket, key)

        # Track in session state and update counter
        if "expert_validated_clips_session" not in st.session_state:
            st.session_state.expert_validated_clips_session = set()

        clip_key = (validation_data["filename"], validation_data["start_time"])
        st.session_state.expert_validated_clips_session.add(clip_key)

        if (
            "expert_remaining_count" in st.session_state
            and st.session_state.expert_remaining_count is not None
        ):
            st.session_state.expert_remaining_count = max(
                0, st.session_state.expert_remaining_count - 1
            )

        from database.queries import get_remaining_pro_clips_count

        get_remaining_pro_clips_count.clear()
        return True
    except Exception as e:
        st.error(f"Error saving Expert validation: {e}")
        return False
