from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "CONFIG.yaml"

_config = {}
if _CONFIG_PATH.exists():
    with open(_CONFIG_PATH) as f:
        _config = yaml.safe_load(f) or {}

# Data directories — local paths or s3:// URIs
AUDIO_DIR = _config.get("audio_dir", "")
RESULTS_DIR = _config.get("results_dir", "")
OUTPUT_DIR = _config.get("output_dir", "")

# S3 credentials (only needed when using s3:// paths)
S3_ENDPOINT_URL = _config.get("s3_endpoint_url", "")
S3_ACCESS_KEY = _config.get("s3_access_key", "")
S3_SECRET_KEY = _config.get("s3_secret_key", "")

# Assets directory
ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Path to multilingual species names CSV
BIRDNET_MULTILINGUAL_PATH = ASSETS_DIR / "birdnet_multilingual.csv"
