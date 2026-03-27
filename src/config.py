from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "CONFIG.yaml"

_config = {}
if _CONFIG_PATH.exists():
    with open(_CONFIG_PATH) as f:
        _config = yaml.safe_load(f) or {}


def _get(key, env_key, default=""):
    """Read from environment variable first, then CONFIG.yaml, then default."""
    import os
    return os.environ.get(env_key, _config.get(key, default))


# Data directories — local paths or s3:// URIs
AUDIO_DIR = _get("audio_dir", "BIRDNET_AUDIO_DIR")
RESULTS_DIR = _get("results_dir", "BIRDNET_RESULTS_DIR")
OUTPUT_DIR = _get("output_dir", "BIRDNET_OUTPUT_DIR")

# S3 credentials (only needed when using s3:// paths)
S3_ENDPOINT_URL = _get("s3_endpoint_url", "BIRDNET_S3_ENDPOINT_URL")
S3_ACCESS_KEY = _get("s3_access_key", "BIRDNET_S3_ACCESS_KEY")
S3_SECRET_KEY = _get("s3_secret_key", "BIRDNET_S3_SECRET_KEY")

# Assets directory
ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Path to multilingual species names CSV
BIRDNET_MULTILINGUAL_PATH = ASSETS_DIR / "birdnet_multilingual.csv"
