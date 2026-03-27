"""S3 utilities for reading/writing files from S3 storage."""

import io
from urllib.parse import urlparse

import boto3

from config import S3_ACCESS_KEY, S3_ENDPOINT_URL, S3_SECRET_KEY


def is_s3_path(path):
    """Check if a path is an S3 URI."""
    return path.startswith("s3://")


def parse_s3_uri(uri):
    """Parse s3://bucket/key into (bucket, key)."""
    parsed = urlparse(uri)
    return parsed.netloc, parsed.path.lstrip("/")


def _get_s3_client():
    """Create a boto3 S3 client using credentials from config."""
    kwargs = {}
    if S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = S3_ENDPOINT_URL
    if S3_ACCESS_KEY and S3_SECRET_KEY:
        kwargs["aws_access_key_id"] = S3_ACCESS_KEY
        kwargs["aws_secret_access_key"] = S3_SECRET_KEY
    return boto3.client("s3", **kwargs)


def list_s3_files(s3_uri, extension=None):
    """List all files under an S3 prefix, optionally filtered by extension.

    Returns list of full S3 URIs.
    """
    client = _get_s3_client()
    bucket, prefix = parse_s3_uri(s3_uri)

    # Ensure prefix ends with /
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    files = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if extension is None or key.lower().endswith(extension):
                files.append(f"s3://{bucket}/{key}")
            elif isinstance(extension, (set, list, tuple)):
                if any(key.lower().endswith(ext) for ext in extension):
                    files.append(f"s3://{bucket}/{key}")
    return files


def read_s3_bytes(s3_uri):
    """Read a file from S3 and return its contents as bytes."""
    client = _get_s3_client()
    bucket, key = parse_s3_uri(s3_uri)
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def read_s3_text(s3_uri):
    """Read a text file from S3 and return its contents as a string."""
    return read_s3_bytes(s3_uri).decode("utf-8")


def write_s3_bytes(s3_uri, data):
    """Write bytes to an S3 object."""
    client = _get_s3_client()
    bucket, key = parse_s3_uri(s3_uri)
    client.put_object(Bucket=bucket, Key=key, Body=data)


def write_s3_text(s3_uri, text):
    """Write a text string to an S3 object."""
    write_s3_bytes(s3_uri, text.encode("utf-8"))
