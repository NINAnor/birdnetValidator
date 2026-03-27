import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Data directories (set in .env) — local paths or s3:// URIs
AUDIO_DIR = os.getenv("AUDIO_DIR", "")
RESULTS_DIR = os.getenv("RESULTS_DIR", "")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "")

# S3 credentials (only needed when using s3:// paths)
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")

# Assets directory
ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Path to multilingual species names CSV
BIRDNET_MULTILINGUAL_PATH = ASSETS_DIR / "birdnet_multilingual.csv"
