import os
from pathlib import Path

# ============================================================================
# S3 Configuration
# ============================================================================

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_BASE_URL = f"s3://{S3_BUCKET}"

# ============================================================================
# Expert Mode Configuration
# ============================================================================

# Expert mode datasets folder
EXPERT_DATASETS_FOLDER = f"{S3_BASE_URL}/validation_dataset"

# Site info CSV for mapping device IDs to site names
SITE_INFO_S3_PATH = f"{S3_BASE_URL}/site_info.csv"

# Expert mode validations stored in: validations_expert/session_{session_id}.csv
EXPERT_VALIDATIONS_PREFIX = "validations_expert"

# Expert Mode Settings
EXPERT_TOP_SPECIES_COUNT = int(os.getenv("EXPERT_TOP_SPECIES_COUNT", "10"))

# ============================================================================
# Language Configuration
# ============================================================================

# Language mapping for species names
LANGUAGE_MAPPING = {
    "English": "en_uk",
    "Spanish": "es",
    "Dutch": "nl",
    "Norwegian": "no",
    "French": "fr",
}

# Path to multilingual species names CSV
BIRDNET_MULTILINGUAL_PATH = (
    Path(__file__).parent.parent / "assets" / "birdnet_multilingual.csv"
)
