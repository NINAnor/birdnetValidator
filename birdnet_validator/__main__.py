"""CLI entry point: python -m birdnet_validator or birdnet-validator command."""

import argparse
import sys

from birdnet_validator import run


def main():
    parser = argparse.ArgumentParser(
        prog="birdnet-validator",
        description="Launch the BirdNET Validator app.",
    )
    parser.add_argument(
        "--audio-dir", required=True,
        help="Path to audio files (local or s3:// URI)",
    )
    parser.add_argument(
        "--results-dir", required=True,
        help="Path to BirdNET result files (local or s3:// URI)",
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Path for validation output CSVs (local or s3:// URI)",
    )
    parser.add_argument(
        "--s3-endpoint-url", default="",
        help="S3 endpoint URL",
    )
    parser.add_argument(
        "--s3-access-key", default="",
        help="S3 access key",
    )
    parser.add_argument(
        "--s3-secret-key", default="",
        help="S3 secret key",
    )
    parser.add_argument(
        "--port", type=int, default=8501,
        help="Port to run the app on (default: 8501)",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't open the browser automatically",
    )

    args = parser.parse_args()

    run(
        audio_dir=args.audio_dir,
        results_dir=args.results_dir,
        output_dir=args.output_dir,
        s3_endpoint_url=args.s3_endpoint_url,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
        port=args.port,
        open_browser=not args.no_browser,
    )


if __name__ == "__main__":
    main()
