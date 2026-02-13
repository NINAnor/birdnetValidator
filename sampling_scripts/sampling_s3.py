"""S3 operations for annotation sampling."""

import io
import json
import os

import boto3


def format_dataframe_for_app(df):
    """
    Format DataFrame to match the expected structure for the annotation app.

    Expected format:
    - scientific name: string representation of list (e.g., '["species1", "species2"]')
    - confidence: string representation of list (e.g., '[0.5, 0.9]')
    - max uncertainty: string representation of list (e.g., '[0.2, 0.5]')
    - userID: string
    """
    df = df.copy()

    # Convert arrays to JSON string representations
    df["scientific name"] = df["scientific name"].apply(
        lambda x: json.dumps(x.tolist() if hasattr(x, "tolist") else x)
    )
    df["confidence"] = df["confidence"].apply(
        lambda x: json.dumps(x.tolist() if hasattr(x, "tolist") else x)
    )
    df["max uncertainty"] = df["max uncertainty"].apply(
        lambda x: json.dumps(x.tolist() if hasattr(x, "tolist") else x)
    )

    # Ensure userID is string
    if "userID" in df.columns:
        df["userID"] = df["userID"].astype(str)

    return df


def upload_to_s3(df, s3_bucket, output_key):
    """Upload DataFrame as parquet to S3."""
    # Format data for app compatibility
    df = format_dataframe_for_app(df)

    # Configure S3 client
    s3_config = {}
    s3_endpoint = os.getenv("S3_ENDPOINT")
    if s3_endpoint:
        if not s3_endpoint.startswith(("http://", "https://")):
            s3_endpoint = f"https://{s3_endpoint}"
        s3_config["endpoint_url"] = s3_endpoint

    aws_access_key = os.getenv("S3_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")

    if aws_access_key and aws_secret_key:
        s3_config["aws_access_key_id"] = aws_access_key
        s3_config["aws_secret_access_key"] = aws_secret_key

    s3_client = boto3.client("s3", **s3_config)

    # Convert to parquet and upload
    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    parquet_buffer.seek(0)

    s3_client.put_object(
        Bucket=s3_bucket, Key=output_key, Body=parquet_buffer.getvalue()
    )

    return f"s3://{s3_bucket}/{output_key}"
