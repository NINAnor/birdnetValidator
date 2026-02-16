"""Core sampling logic for annotation dataset creation."""

import pandas as pd
from sampling_utils import (
    create_confidence_bins,
    extract_species_confidence,
    get_duckdb_s3_connection,
)


def load_segments_from_s3(s3_bucket, input_prefix, target_species, target_sites=None):
    """
    Load segments containing target species from S3 parquet files.

    Uses DuckDB for efficient querying with partition pruning when sites specified.
    """
    con = get_duckdb_s3_connection()
    species_array = "['" + "', '".join(target_species) + "']"

    # Build query based on whether sites are filtered
    if target_sites:
        # Read only specific partitions for better performance
        partition_patterns = [
            f"s3://{s3_bucket}/{input_prefix}/**/device_id={site}/*.parquet"
            for site in target_sites
        ]

        all_dfs = []
        for i, (pattern, site) in enumerate(
            zip(partition_patterns, target_sites, strict=False), 1
        ):
            try:
                print(f"    [{i}/{len(target_sites)}] Reading {site}...")
                query = f"""
                    SELECT filename, deployment_id, fullPath, "start time",
                           "scientific name", confidence, "max uncertainty", userID
                    FROM read_parquet('{pattern}', hive_partitioning=true)
                    WHERE list_has_any("scientific name", {species_array})
                """
                df = con.execute(query).fetchdf()

                if not df.empty:
                    df["device_id"] = site  # Add device_id from partition
                    all_dfs.append(df)
                    print(f"       ✓ Found {len(df):,} matching segments")
                else:
                    print("       - No matching segments")
            except Exception as e:
                print(f"       ⚠ Could not read {site}: {e}")
                continue

        con.close()
        return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    else:
        # Scan all files (slower but comprehensive)
        s3_pattern = f"s3://{s3_bucket}/{input_prefix}/**/*.parquet"
        print(f"  → Reading: {s3_pattern}")
        print("  ⚠ No site filter - scanning ALL files")

        try:
            query = f"""
                SELECT filename, deployment_id, fullPath, "start time",
                       "scientific name", confidence, "max uncertainty", userID
                FROM read_parquet('{s3_pattern}', hive_partitioning=true)
                WHERE list_has_any("scientific name", {species_array})
            """
            df = con.execute(query).fetchdf()
            con.close()
            return df
        except Exception as e:
            con.close()
            print(f"  ✗ Error loading data: {e}")
            return pd.DataFrame()


def subsample_by_confidence_bins(
    df,
    target_species,
    samples_per_bin=50,
    bin_size=0.1,
    random_seed=42,
    stratify_by_device=False,
    stratify_by_species=False,
):
    """
    Subsample segments by confidence bins of target species.

    Args:
        stratify_by_device: If True, sample per bin per device.
        stratify_by_species: If True, sample per bin per species (independently).

    Returns:
        Tuple of (sampled_df, sampling_metadata) where sampling_metadata is a DataFrame
        with columns: species, confidence, device_id, confidence_bin for each sample.
    """
    print("  → Extracting species confidence...")
    records = extract_species_confidence(
        df, target_species, per_species=stratify_by_species
    )
    conf_df = pd.DataFrame(records)

    if conf_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    conf_key = "confidence" if stratify_by_species else "target_max_confidence"
    print(f"  → Found {len(conf_df):,} records")

    conf_df["device_id"] = df.iloc[conf_df["segment_idx"]]["device_id"].values
    conf_df["confidence_bin"] = create_confidence_bins(conf_df[conf_key], bin_size)

    if stratify_by_species:
        return _subsample_by_species(
            df,
            conf_df,
            target_species,
            samples_per_bin,
            random_seed,
            stratify_by_device,
        )

    print("\n  Confidence distribution:")
    for bin_label, count in (
        conf_df["confidence_bin"].value_counts().sort_index().items()
    ):
        print(f"    {bin_label}: {count:,} segments")

    indices, metadata = _sample_from_bins(
        conf_df, samples_per_bin, random_seed, stratify_by_device, species=None
    )
    metadata_df = pd.DataFrame(metadata) if metadata else pd.DataFrame()
    return df.iloc[indices].copy().reset_index(drop=True), metadata_df


def _subsample_by_species(
    df, conf_df, target_species, samples_per_bin, random_seed, stratify_by_device
):
    """Sample independently for each target species."""
    all_indices = set()
    all_metadata = []

    for species in target_species:
        species_df = conf_df[conf_df["species"] == species]
        if species_df.empty:
            print(f"\n  🐦 {species}: No detections found")
            continue

        print(f"\n  🐦 {species}: {len(species_df):,} detections")
        indices, metadata = _sample_from_bins(
            species_df,
            samples_per_bin,
            random_seed,
            stratify_by_device,
            species=species,
        )
        all_indices.update(indices)
        all_metadata.extend(metadata)
        print(f"     → Sampled {len(indices)} segments")

    metadata_df = pd.DataFrame(all_metadata) if all_metadata else pd.DataFrame()
    return df.iloc[list(all_indices)].copy().reset_index(drop=True), metadata_df


def _sample_from_bins(
    conf_df, samples_per_bin, random_seed, stratify_by_device, species=None
):
    """Sample from confidence bins, optionally stratified by device.

    Returns:
        Tuple of (indices, metadata) where metadata tracks what was sampled.
    """
    subsampled_indices = []
    metadata = []

    if stratify_by_device:
        devices = conf_df["device_id"].unique()
        for device in devices:
            device_data = conf_df[conf_df["device_id"] == device]
            print(f"    📍 {device}:")

            for bin_label in conf_df["confidence_bin"].cat.categories:
                bin_data = device_data[device_data["confidence_bin"] == bin_label]
                if len(bin_data) == 0:
                    continue

                n = min(samples_per_bin, len(bin_data))
                sampled = bin_data.sample(n=n, random_state=random_seed)
                subsampled_indices.extend(sampled["segment_idx"].tolist())

                # Track metadata for each sampled segment
                for _, row in sampled.iterrows():
                    metadata.append(
                        {
                            "species": species or row.get("species", "unknown"),
                            "confidence": row.get(
                                "confidence", row.get("target_max_confidence")
                            ),
                            "device_id": device,
                            "confidence_bin": str(bin_label),
                        }
                    )
                print(f"       {bin_label}: {n}/{len(bin_data)}")
    else:
        for bin_label in conf_df["confidence_bin"].cat.categories:
            bin_data = conf_df[conf_df["confidence_bin"] == bin_label]
            if len(bin_data) == 0:
                continue

            n = min(samples_per_bin, len(bin_data))
            sampled = bin_data.sample(n=n, random_state=random_seed)
            subsampled_indices.extend(sampled["segment_idx"].tolist())

            for _, row in sampled.iterrows():
                metadata.append(
                    {
                        "species": species or row.get("species", "unknown"),
                        "confidence": row.get(
                            "confidence", row.get("target_max_confidence")
                        ),
                        "device_id": row.get("device_id", "unknown"),
                        "confidence_bin": str(bin_label),
                    }
                )
            print(f"    {bin_label}: {n}/{len(bin_data)}")

    return subsampled_indices, metadata
