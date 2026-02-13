"""Core sampling logic for annotation dataset creation."""

import pandas as pd
from sampling_utils import (
    create_confidence_bins,
    extract_target_species_confidence,
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
    df, target_species, samples_per_bin=50, bin_size=0.1, random_seed=42
):
    """
    Subsample segments by confidence bins of target species.

    Preserves full segment data (all species arrays) but bins/samples
    based on maximum confidence of target species in each segment.
    """
    # Extract confidence values for target species
    print("  → Extracting target species confidence...")
    segments_with_conf = extract_target_species_confidence(df, target_species)
    conf_df = pd.DataFrame(segments_with_conf)
    print(f"  → Found {len(conf_df):,} segments with target species")

    # Create bins and show distribution
    conf_df["confidence_bin"] = create_confidence_bins(
        conf_df["target_max_confidence"], bin_size
    )

    print("\n  Confidence distribution:")
    bin_counts = conf_df["confidence_bin"].value_counts().sort_index()
    for bin_label, count in bin_counts.items():
        print(f"    {bin_label}: {count:,} segments")

    # Sample from each bin
    subsampled_indices = []
    print(f"\n  Sampling {samples_per_bin} per bin:")

    for bin_label in conf_df["confidence_bin"].cat.categories:
        bin_data = conf_df[conf_df["confidence_bin"] == bin_label]
        if len(bin_data) == 0:
            continue

        n_samples = min(samples_per_bin, len(bin_data))
        sampled = bin_data.sample(n=n_samples, random_state=random_seed)
        subsampled_indices.extend(sampled["segment_idx"].tolist())

        percentage = (n_samples / len(bin_data)) * 100
        print(
            f"    {bin_label}: {n_samples:,} from {len(bin_data):,} ({percentage:.1f}%)"
        )

    return df.iloc[subsampled_indices].copy().reset_index(drop=True)
