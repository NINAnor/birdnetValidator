import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if present (local dev); env vars from Docker/Portainer take precedence
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_PATH, override=False)

# Data directories — local paths or s3:// URIs
AUDIO_DIR = os.environ.get("AUDIO_DIR", "")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "")

# S3 credentials (only needed when using s3:// paths)
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")

# Assets directory
ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Path to multilingual species names CSV
BIRDNET_MULTILINGUAL_PATH = ASSETS_DIR / "birdnet_multilingual.csv"
