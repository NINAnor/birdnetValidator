"""Utility functions for annotation sampling operations."""

import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


def get_duckdb_s3_connection():
    """Create a DuckDB connection configured for S3 access."""
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")

    s3_endpoint = (
        os.getenv("S3_ENDPOINT", "").replace("https://", "").replace("http://", "")
    )

    con.execute("SET s3_region='us-east-1';")
    con.execute(f"SET s3_access_key_id='{os.getenv('S3_ACCESS_KEY_ID')}';")
    con.execute(f"SET s3_secret_access_key='{os.getenv('S3_SECRET_ACCESS_KEY')}';")
    con.execute(f"SET s3_endpoint='{s3_endpoint}';")
    con.execute("SET s3_use_ssl=true;")
    con.execute("SET s3_url_style='path';")

    return con


def create_confidence_bins(confidence_values, bin_size=0.1):
    """Create confidence bin labels for given confidence values."""
    bins = np.arange(0, 1 + bin_size, bin_size)
    bin_labels = [f"{bins[i]:.1f}-{bins[i + 1]:.1f}" for i in range(len(bins) - 1)]
    return pd.cut(confidence_values, bins=bins, labels=bin_labels, include_lowest=True)


def extract_target_species_confidence(df, target_species):
    """
    Extract maximum confidence of target species from segments.

    Returns list of dicts with segment_idx and target_max_confidence.
    """
    segments_with_conf = []

    for idx, row in df.iterrows():
        species_list = row["scientific name"]
        confidence_list = row["confidence"]

        # Handle string representations
        if isinstance(species_list, str):
            import ast

            species_list = ast.literal_eval(species_list)
            confidence_list = ast.literal_eval(confidence_list)

        # Find max confidence among target species
        target_confidences = [
            float(confidence_list[i])
            for i, species in enumerate(species_list)
            if species in target_species and i < len(confidence_list)
        ]

        if target_confidences:
            segments_with_conf.append(
                {"segment_idx": idx, "target_max_confidence": max(target_confidences)}
            )

    return segments_with_conf


def assign_user_ids(df, user_ids):
    """Distribute clips evenly among user IDs in round-robin fashion."""
    if not user_ids:
        df["userID"] = "default_user"
        return df

    # Shuffle and assign in round-robin
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df["userID"] = [user_ids[i % len(user_ids)] for i in range(len(df))]

    return df


def count_unique_species(df):
    """Count unique species across all segments in the dataframe."""
    all_unique_species = set()

    for species_array in df["scientific name"]:
        if isinstance(species_array, list | np.ndarray):
            all_unique_species.update(species_array)
        elif isinstance(species_array, str):
            import ast

            species_list = ast.literal_eval(species_array)
            all_unique_species.update(species_list)

    return len(all_unique_species)
