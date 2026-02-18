"""Database queries for Expert mode."""

import duckdb
import streamlit as st

from config import (
    EXPERT_DATASETS_FOLDER,
    EXPERT_TOP_SPECIES_COUNT,
    S3_ACCESS_KEY_ID,
    S3_BUCKET,
    S3_ENDPOINT,
    S3_SECRET_ACCESS_KEY,
)


@st.cache_resource
def get_duckdb_connection():
    """Create and configure DuckDB connection."""
    conn = duckdb.connect()
    conn.execute("INSTALL httpfs;")
    conn.execute("LOAD httpfs;")
    conn.execute("SET s3_region='us-east-1';")
    conn.execute(f"SET s3_access_key_id='{S3_ACCESS_KEY_ID}';")
    conn.execute(f"SET s3_secret_access_key='{S3_SECRET_ACCESS_KEY}';")
    conn.execute(f"SET s3_endpoint='{S3_ENDPOINT}';")
    conn.execute("SET s3_use_ssl=true;")
    conn.execute("SET s3_url_style='path';")
    return conn


def list_available_datasets():
    """List all available parquet datasets in the validation_dataset folder."""
    import boto3
    from botocore.client import Config

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{S3_ENDPOINT}",
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )

        # Remove s3:// prefix and get folder path
        folder_path = EXPERT_DATASETS_FOLDER.replace(f"s3://{S3_BUCKET}/", "")

        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=folder_path,
        )

        if "Contents" not in response:
            return []

        datasets = []
        for obj in response["Contents"]:
            key = obj["Key"]
            if key.endswith(".parquet"):
                filename = key.split("/")[-1]
                datasets.append(
                    {
                        "name": filename.replace(".parquet", ""),
                        "path": f"s3://{S3_BUCKET}/{key}",
                        "size": obj["Size"],
                    }
                )

        return sorted(datasets, key=lambda x: x["name"])
    except Exception as e:
        st.error(f"Error listing datasets: {e}")
        return []


def check_user_has_annotations(user_id, dataset_path=None):
    """Check if user has any assigned annotations in the selected dataset."""
    if dataset_path is None:
        dataset_path = st.session_state.get("expert_selected_dataset")
        if not dataset_path:
            return False

    try:
        conn = get_duckdb_connection()
        query = (
            f"SELECT COUNT(*) FROM '{dataset_path}' "
            "WHERE CAST(userID AS VARCHAR) = CAST(? AS VARCHAR)"
        )
        result = conn.execute(query, [user_id]).fetchone()
        return result[0] > 0 if result else False
    except Exception:
        return False


@st.cache_data
def get_top_species_for_database(dataset_path):
    """Get top N species by detection count for checklist."""
    conn = get_duckdb_connection()
    query = (
        f'SELECT "scientific name", COUNT(*) as count '
        f"FROM '{dataset_path}' "
        f'GROUP BY "scientific name" ORDER BY count DESC '
        f"LIMIT {EXPERT_TOP_SPECIES_COUNT}"
    )
    return [row[0] for row in conn.execute(query).fetchall()]


@st.cache_data(ttl=300)
def get_species_for_user(user_id, dataset_path):
    """Get unique species available for a user in the dataset.

    Returns list of species names sorted alphabetically.
    """
    conn = get_duckdb_connection()
    query = f"""
    SELECT DISTINCT unnest("scientific name") as species
    FROM '{dataset_path}'
    WHERE CAST(userID AS VARCHAR) = CAST(? AS VARCHAR)
    ORDER BY species
    """
    try:
        results = conn.execute(query, [user_id]).fetchall()
        return [row[0] for row in results]
    except Exception:
        return []


@st.cache_data(
    ttl=1800, show_spinner="Loading assigned clips..."
)  # Cache for 10 minutes
def get_assigned_clips_for_user(user_id, dataset_path):
    """
    Get all assigned clips for a specific userID from the selected dataset.
    Returns list of dicts for efficient processing.
    CACHED to avoid repeated parquet queries.

    Args:
        user_id: The user's ID (can be string or int)
        dataset_path: S3 path to the parquet dataset

    Returns:
        List of dicts with clip information
    """
    conn = get_duckdb_connection()
    query = f"""
    SELECT
        fullPath as filename,
        deployment_id,
        "start time" as start_time,
        "scientific name" as species_array,
        confidence as confidence_array,
        userID
    FROM '{dataset_path}'
    WHERE CAST(userID AS VARCHAR) = CAST(? AS VARCHAR)
    ORDER BY filename, start_time
    """
    results = conn.execute(query, [user_id]).fetchall()

    clips = [
        {
            "filename": row[0],
            "deployment_id": row[1],
            "start_time": row[2],
            "species_array": row[3],
            "confidence_array": row[4],
            "userID": row[5],
        }
        for row in results
    ]

    return clips


@st.cache_data(ttl=300)
def get_validated_pro_clips(user_id, dataset_path):
    """Get clips already validated by this user for the given dataset.
    Returns set of (filename, start_time) tuples.
    """
    import tempfile
    from pathlib import Path

    import boto3
    import pandas as pd
    from botocore.client import Config

    from config import (
        EXPERT_VALIDATIONS_PREFIX,
        S3_ACCESS_KEY_ID,
        S3_BUCKET,
        S3_ENDPOINT,
        S3_SECRET_ACCESS_KEY,
    )

    # Extract dataset name for filtering
    dataset_name = (
        dataset_path.split("/")[-1].replace(".parquet", "") if dataset_path else ""
    )

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{S3_ENDPOINT}",
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )

        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=EXPERT_VALIDATIONS_PREFIX
        )
        if "Contents" not in response:
            return set()

        all_validations = []
        for obj in response["Contents"]:
            # Only load files for this dataset
            filename = obj["Key"].split("/")[-1]
            if obj["Key"].endswith(".csv") and filename.startswith(f"{dataset_name}_"):
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w+", suffix=".csv", delete=False
                    ) as temp_file:
                        try:
                            s3_client.download_file(
                                S3_BUCKET, obj["Key"], temp_file.name
                            )
                            df = pd.read_csv(temp_file.name)
                            all_validations.append(df)
                        finally:
                            Path(temp_file.name).unlink()
                except Exception as e:
                    # Skip invalid CSV files during validation loading
                    st.warning(f"Skipping invalid file {obj['Key']}: {e}")
                    continue

        if not all_validations:
            return set()

        combined_df = pd.concat(all_validations, ignore_index=True)
        filtered = combined_df[combined_df["userID"].astype(str) == str(user_id)]
        return set(zip(filtered["filename"], filtered["start_time"], strict=False))

    except Exception:
        return set()


def _get_validated_clips_with_session(user_id, dataset_path):
    """Get all validated clips including session state."""
    validated_clips = get_validated_pro_clips(user_id, dataset_path)
    if hasattr(st.session_state, "expert_validated_clips_session"):
        validated_clips = validated_clips.union(
            st.session_state.expert_validated_clips_session
        )
    return validated_clips


def get_random_assigned_clip(user_id, dataset_path, species_filter=None):
    """Get next unvalidated clip for user from the selected dataset.

    Args:
        user_id: User ID to filter by
        dataset_path: S3 path to the parquet dataset
        species_filter: Optional list of species to filter by

    Uses deterministic ordering (filename, start_time).
    Returns dict with clip info, or 'all_validated': True if done.
    """
    conn = get_duckdb_connection()
    validated_clips = _get_validated_clips_with_session(user_id, dataset_path)

    if validated_clips:
        validated_tuples = [
            (filename, start_time) for filename, start_time in validated_clips
        ]
        placeholders = ",".join(["(?, ?)" for _ in validated_tuples])
        exclusion_clause = f'AND (fullPath, "start time") NOT IN ({placeholders})'
        exclusion_params = [
            item
            for filename, start_time in validated_tuples
            for item in [filename, start_time]
        ]
    else:
        exclusion_clause = ""
        exclusion_params = []

    # Build species filter clause
    if species_filter:
        species_placeholders = ",".join(["?" for _ in species_filter])
        species_clause = (
            f'AND len(list_filter("scientific name", '
            f"x -> x IN ({species_placeholders}))) > 0"
        )
        species_params = list(species_filter)
    else:
        species_clause = ""
        species_params = []

    query = f"""
    SELECT fullPath, deployment_id, "start time", "scientific name",
           confidence, userID
    FROM '{dataset_path}'
    WHERE CAST(userID AS VARCHAR) = CAST(? AS VARCHAR)
    {exclusion_clause}
    {species_clause}
    ORDER BY fullPath, "start time"
    LIMIT 1
    """

    try:
        result = conn.execute(
            query, [user_id] + exclusion_params + species_params
        ).fetchone()

        if result:
            return {
                "filename": result[0],
                "deployment_id": result[1],
                "start_time": result[2],
                "species_array": result[3],
                "confidence_array": result[4],
                "userID": result[5],
                "all_validated": False,
            }
        else:
            # Check if there are any clips at all for this user (with species filter)
            count_query = (
                f"SELECT COUNT(*) FROM '{dataset_path}' "
                f"WHERE CAST(userID AS VARCHAR) = CAST(? AS VARCHAR) "
                f"{species_clause}"
            )
            total = conn.execute(
                count_query, [user_id] + species_params
            ).fetchone()[0]

            if total > 0:
                return {"all_validated": True, "total_clips": total}
            else:
                return None
    except Exception as e:
        st.error(f"Error fetching random clip: {e}")
        return None


@st.cache_data
def get_remaining_pro_clips_count(user_id, dataset_path, species_filter=None):
    """Get count of remaining unvalidated clips for user in the selected dataset.

    Args:
        user_id: User ID to filter by
        dataset_path: S3 path to the parquet dataset
        species_filter: Optional list of species to filter by

    Uses DuckDB COUNT for performance.
    """
    conn = get_duckdb_connection()
    validated_clips = _get_validated_clips_with_session(user_id, dataset_path)

    if validated_clips:
        validated_tuples = [
            (filename, start_time) for filename, start_time in validated_clips
        ]
        placeholders = ",".join(["(?, ?)" for _ in validated_tuples])
        exclusion_clause = f'AND (fullPath, "start time") NOT IN ({placeholders})'
        exclusion_params = [
            item
            for filename, start_time in validated_tuples
            for item in [filename, start_time]
        ]
    else:
        exclusion_clause = ""
        exclusion_params = []

    # Build species filter clause
    if species_filter:
        species_placeholders = ",".join(["?" for _ in species_filter])
        species_clause = (
            f'AND len(list_filter("scientific name", '
            f"x -> x IN ({species_placeholders}))) > 0"
        )
        species_params = list(species_filter)
    else:
        species_clause = ""
        species_params = []

    query = (
        f"SELECT COUNT(*) FROM '{dataset_path}' "
        f"WHERE CAST(userID AS VARCHAR) = CAST(? AS VARCHAR) "
        f"{exclusion_clause} "
        f"{species_clause}"
    )

    try:
        result = conn.execute(
            query, [user_id] + exclusion_params + species_params
        ).fetchone()
        return result[0] if result else 0
    except Exception:
        return 0
