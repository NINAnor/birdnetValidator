"""Utility functions for annotation sampling operations."""

import ast
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


def _parse_arrays(species_list, confidence_list):
    """Parse species/confidence arrays, handling string representations."""
    if isinstance(species_list, str):
        species_list = ast.literal_eval(species_list)
        confidence_list = ast.literal_eval(confidence_list)
    return species_list, confidence_list


def extract_species_confidence(df, target_species, per_species=False):
    """
    Extract confidence values for target species from segments.

    Args:
        df: DataFrame with segments
        target_species: List of species to extract
        per_species: If True, return one record per species per segment.
                     If False, return max confidence across target species.

    Returns:
        List of dicts with segment_idx and confidence info.
    """
    records = []

    for idx, row in df.iterrows():
        species_list, confidence_list = _parse_arrays(
            row["scientific name"], row["confidence"]
        )

        for i, species in enumerate(species_list):
            if species in target_species and i < len(confidence_list):
                if per_species:
                    records.append(
                        {
                            "segment_idx": idx,
                            "species": species,
                            "confidence": float(confidence_list[i]),
                        }
                    )
                else:
                    # Find existing record for this segment or create new
                    existing = next(
                        (r for r in records if r["segment_idx"] == idx), None
                    )
                    conf = float(confidence_list[i])
                    if existing:
                        existing["target_max_confidence"] = max(
                            existing["target_max_confidence"], conf
                        )
                    else:
                        records.append(
                            {
                                "segment_idx": idx,
                                "target_max_confidence": conf,
                            }
                        )

    return records


def assign_user_ids(df, user_ids):
    """Distribute clips evenly among user IDs in round-robin fashion."""
    if not user_ids:
        df["userID"] = "default_user"
        return df

    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df["userID"] = [user_ids[i % len(user_ids)] for i in range(len(df))]
    return df


def count_unique_species(df, target_species=None):
    """Count unique species across all segments in the dataframe."""
    all_species = set()

    for species_array in df["scientific name"]:
        if isinstance(species_array, list | np.ndarray):
            all_species.update(species_array)
        elif isinstance(species_array, str):
            all_species.update(ast.literal_eval(species_array))

    return (
        len(all_species & set(target_species)) if target_species else len(all_species)
    )
