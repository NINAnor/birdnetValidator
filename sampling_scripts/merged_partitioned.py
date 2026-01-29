"""
This script:
- Merges multilabel predictions and confidence scores to a single row 
- Updates full audio path for prediction
- Adjusts output format required for Listening Lab 
- Works with S3 storage using boto3

Usage:
    python merged_partitioned.py \
        --s3-bucket your-bucket-name \
        --s3-endpoint https://your-s3-endpoint.com

"""

import argparse
import io
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import boto3
import duckdb
import numpy as np
import pandas as pd

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


# S3 defaults
DEFAULT_S3_BUCKET = "bencretois-ns8129k-proj-tabmon"
DEFAULT_DATASET_PATH = "tabmon_data"  # S3 prefix for audio
DEFAULT_INPUT_PATH = "merged_predictions_light"  # S3 prefix for input parquets
DEFAULT_OUTPUT_PATH = "Listening_Lab"  # S3 prefix for output parquets


COUNTRY_TO_FOLDER = {
    "France": "proj_tabmon_NINA_FR",
    "Norway": "proj_tabmon_NINA",
    "Netherlands": "proj_tabmon_NINA_NL",
    "Spain": "proj_tabmon_NINA_ES",
}


def bugg_id_to_folder(id_str):
    """Convert a device_id string to the bugg directory name."""
    padded_id = id_str.rjust(15, "0")
    return f"bugg_RPiID-1{padded_id}"


def get_duckdb_s3_connection():
    """Create a DuckDB connection configured for S3 access."""
    con = duckdb.connect(database=":memory:")
    
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    
    # Get S3 credentials and endpoint from environment
    s3_access_key = os.getenv("S3_ACCESS_KEY_ID")
    s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    s3_endpoint = os.getenv("S3_ENDPOINT")
    
    # Remove protocol if present - DuckDB adds it automatically
    s3_endpoint = s3_endpoint.replace("https://", "").replace("http://", "")
    
    con.execute("SET s3_region='us-east-1';")
    con.execute(f"SET s3_access_key_id='{s3_access_key}';")
    con.execute(f"SET s3_secret_access_key='{s3_secret_key}';")
    con.execute(f"SET s3_endpoint='{s3_endpoint}';")
    con.execute("SET s3_use_ssl=true;")
    con.execute("SET s3_url_style='path';")
    
    return con


def aggregate_parquet(bucket, s3_key):
    """Load a single parquet file from S3 and aggregate to one row per segment."""
    con = get_duckdb_s3_connection()
    
    # Build full S3 path
    s3_path = f"s3://{bucket}/{s3_key}"
    
    # Check if file has any data
    count = con.execute(f"SELECT COUNT(*) FROM '{s3_path}'").fetchone()[0]
    if count == 0:
        con.close()
        return None, 0

    # Aggregate query
    query = f"""
        SELECT
            filename,
            deployment_id,
            "start time",
            ARRAY_AGG("scientific name") AS "scientific name",
            ARRAY_AGG(confidence) AS confidence,
            MAX("max uncertainty") AS "max uncertainty"
        FROM '{s3_path}'
        GROUP BY filename, deployment_id, "start time"
        ORDER BY filename, "start time"
    """
    df = con.execute(query).fetchdf()
    con.close()

    return df, count


def resolve_conf_folder(s3_client, bucket, dataset_prefix, country, device_id):
    """Resolve the conf_folder for a given country/device_id pair from S3.
    
    Returns the conf_folder name if found, None otherwise.
    """
    country_folder = COUNTRY_TO_FOLDER.get(country)
    if country_folder is None:
        return None

    bugg_folder = bugg_id_to_folder(device_id)
    
    # Try different possible paths - audio data may be stored without dataset_prefix
    possible_prefixes = [
        f"{country_folder}/{bugg_folder}/",  # Direct path: proj_tabmon_NINA_FR/bugg_RPiID-...
        f"{dataset_prefix}/{country_folder}/{bugg_folder}/",  # With prefix: tabmon_data/proj_tabmon_NINA_FR/bugg_RPiID-...
    ]
    
    for bugg_prefix in possible_prefixes:
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket, Prefix=bugg_prefix, Delimiter="/"
            )
            
            if "CommonPrefixes" in response and len(response["CommonPrefixes"]) > 0:
                conf_folders = [
                    prefix["Prefix"].rstrip("/").split("/")[-1]
                    for prefix in response["CommonPrefixes"]
                ]

                if len(conf_folders) == 1:
                    return conf_folders[0]
                else:
                    tabmon_folders = [f for f in conf_folders if "TABMON" in f.upper()]
                    if tabmon_folders:
                        return sorted(tabmon_folders)[0]
                    return sorted(conf_folders)[0]

        except Exception:
            continue
    
    return None


def add_full_paths(df, country_folder, bugg_folder, conf_folder):
    prefix = f"{country_folder}/{bugg_folder}/{conf_folder}/"
    df["fullPath"] = prefix + df["filename"]
    return df


def walk_parquet_files(s3_client, bucket, input_prefix):
    """
    Yield (country, device_id, s3_key, filename) for each parquet file in S3.
    Expects structure: input_prefix/country={country}/device_id={device_id}/*.parquet
    """
    # List country folders
    country_response = s3_client.list_objects_v2(
        Bucket=bucket, Prefix=input_prefix + "/", Delimiter="/"
    )

    if "CommonPrefixes" not in country_response:
        print(f"No country folders found at s3://{bucket}/{input_prefix}/")
        return

    for country_prefix in sorted(
        country_response["CommonPrefixes"], key=lambda x: x["Prefix"]
    ):
        country_folder = country_prefix["Prefix"].rstrip("/").split("/")[-1]
        if not country_folder.startswith("country="):
            continue
        country = country_folder.split("=", 1)[1]

        # List device folders
        device_response = s3_client.list_objects_v2(
            Bucket=bucket, Prefix=country_prefix["Prefix"], Delimiter="/"
        )

        if "CommonPrefixes" not in device_response:
            continue

        for device_prefix in sorted(
            device_response["CommonPrefixes"], key=lambda x: x["Prefix"]
        ):
            device_folder = device_prefix["Prefix"].rstrip("/").split("/")[-1]
            if not device_folder.startswith("device_id="):
                continue
            device_id = device_folder.split("=", 1)[1]

            # List parquet files
            files_response = s3_client.list_objects_v2(
                Bucket=bucket, Prefix=device_prefix["Prefix"]
            )

            if "Contents" not in files_response:
                continue

            for obj in sorted(files_response["Contents"], key=lambda x: x["Key"]):
                s3_key = obj["Key"]
                filename = s3_key.split("/")[-1]
                if filename.endswith(".parquet"):
                    yield country, device_id, s3_key, filename


def main():
    parser = argparse.ArgumentParser(
        description="Export annotation database from merged predictions (S3 version)."
    )
    parser.add_argument(
        "--s3-bucket",
        default=DEFAULT_S3_BUCKET,
        help="S3 bucket name",
    )
    parser.add_argument(
        "--dataset-prefix",
        default=DEFAULT_DATASET_PATH,
        help="S3 prefix for the audio dataset (default: tabmon_data)",
    )
    parser.add_argument(
        "--input-prefix",
        default=DEFAULT_INPUT_PATH,
        help="S3 prefix for input parquet files (default: merged_predictions_light)",
    )
    parser.add_argument(
        "--output-prefix",
        default=DEFAULT_OUTPUT_PATH,
        help="S3 prefix for output parquet files (default: Listening_Lab)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing output files (default: False)",
    )
    parser.add_argument(
        "--s3-endpoint",
        default=None,
        help="Custom S3 endpoint URL (for non-AWS S3)",
    )
    args = parser.parse_args()

    # Initialize S3 client with credentials from environment
    s3_config = {}
    
    # Check for custom endpoint (prioritize command line, then environment)
    s3_endpoint = args.s3_endpoint or os.getenv("S3_ENDPOINT")
    if s3_endpoint:
        # Ensure endpoint has protocol
        if not s3_endpoint.startswith(("http://", "https://")):
            s3_endpoint = f"https://{s3_endpoint}"
        s3_config["endpoint_url"] = s3_endpoint
    
    # Explicitly pass credentials from environment if available
    aws_access_key = os.getenv("S3_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    
    if aws_access_key and aws_secret_key:
        s3_config["aws_access_key_id"] = aws_access_key
        s3_config["aws_secret_access_key"] = aws_secret_key
        print(f"Using S3 credentials from environment variables")
    else:
        print("Warning: No S3 credentials found in environment variables")
    
    if s3_endpoint:
        print(f"Using S3 endpoint: {s3_endpoint}")
    
    s3_client = boto3.client("s3", **s3_config)

    total_start = time.time()
    total_rows_in = 0
    total_segments_out = 0
    files_processed = 0
    files_skipped = 0

    # Cache conf_folder lookups per (country, device_id)
    conf_cache = {}

    for country, device_id, s3_key, parquet_name in walk_parquet_files(
        s3_client, args.s3_bucket, args.input_prefix
    ):
        # Check if output already exists in S3
        output_key = f"{args.output_prefix}/country={country}/device_id={device_id}/{parquet_name}"

        if not args.overwrite:
            try:
                s3_client.head_object(Bucket=args.s3_bucket, Key=output_key)
                files_skipped += 1
                continue
            except s3_client.exceptions.ClientError:
                pass  # File doesn't exist, proceed

        file_start = time.time()

        # Aggregate this single file
        df, rows_in = aggregate_parquet(args.s3_bucket, s3_key)
        if df is None or df.empty:
            print(f"  [{country}/{device_id}/{parquet_name}] empty, skipping")
            continue

        # Resolve conf_folder (cached per device)
        cache_key = (country, device_id)
        if cache_key not in conf_cache:
            conf_cache[cache_key] = resolve_conf_folder(
                s3_client, args.s3_bucket, args.dataset_prefix, country, device_id
            )
        conf_folder = conf_cache[cache_key]

        # Build fullPath column
        country_folder = COUNTRY_TO_FOLDER.get(country, country)
        bugg_folder = bugg_id_to_folder(device_id)
        df = add_full_paths(df, country_folder, bugg_folder, conf_folder)

        # Add placeholder userID
        df["userID"] = np.nan

        # Reorder columns
        df = df[
            [
                "filename",
                "deployment_id",
                "fullPath",
                "start time",
                "confidence",
                "scientific name",
                "max uncertainty",
                "userID",
            ]
        ]

        # Write to S3
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
        parquet_buffer.seek(0)

        s3_client.put_object(
            Bucket=args.s3_bucket, Key=output_key, Body=parquet_buffer.getvalue()
        )

        elapsed = time.time() - file_start
        total_rows_in += rows_in
        total_segments_out += len(df)
        files_processed += 1

        print(
            f"  [{country}/{device_id}/{parquet_name}] "
            f"{rows_in:,} rows -> {len(df):,} segments [{elapsed:.2f}s]"
        )

    total_elapsed = time.time() - total_start
    print(
        f"\nDone. Processed {files_processed} files, skipped {files_skipped} in {total_elapsed:.1f}s"
    )
    print(f"  Total rows in:     {total_rows_in:,}")
    print(f"  Total segments out: {total_segments_out:,}")
    print(f"  Output S3 path:    s3://{args.s3_bucket}/{args.output_prefix}/")



if __name__ == "__main__":
    main()