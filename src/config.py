import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Data directories (set in .env)
AUDIO_DIR = os.getenv("AUDIO_DIR", "")
RESULTS_DIR = os.getenv("RESULTS_DIR", "")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "")

# Path to multilingual species names CSV
BIRDNET_MULTILINGUAL_PATH = (
    Path(__file__).parent.parent / "assets" / "birdnet_multilingual.csv"
)
