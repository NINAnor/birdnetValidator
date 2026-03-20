"""Local data processing - zip upload and BirdNET result parsing."""

import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".ogg"}
BIRDNET_REQUIRED_COLUMNS = {
    "Begin Time (s)",
    "Common Name",
    "Confidence",
    "Begin Path",
}


def process_uploaded_zip(uploaded_file):
    """Extract zip file and process BirdNET results + audio files.

    Returns dict with extract_dir, audio_files mapping, clips list, and total count.
    """
    extract_dir = Path(tempfile.mkdtemp(prefix="birdnet_validator_"))

    with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    audio_files = _find_audio_files(extract_dir)
    result_files = _find_result_files(extract_dir)
    clips = _parse_birdnet_results(result_files, audio_files)

    return {
        "extract_dir": str(extract_dir),
        "audio_files": audio_files,
        "clips": clips,
        "total_clips": len(clips),
    }


def _find_audio_files(root_dir):
    """Find all audio files and return dict mapping basename -> local path."""
    audio_map = {}
    for root, _, files in os.walk(root_dir):
        for filename in files:
            if Path(filename).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
                full_path = str(Path(root) / filename)
                audio_map[filename] = full_path
    return audio_map


def _find_result_files(root_dir):
    """Find all potential BirdNET result .txt files."""
    result_files = []
    for root, _, files in os.walk(root_dir):
        for filename in files:
            if filename.endswith(".txt"):
                result_files.append(str(Path(root) / filename))
    return result_files


def _parse_birdnet_results(result_files, audio_files):
    """Parse BirdNET result files and create grouped clip list.

    Groups detections by (audio file, begin time) so each clip contains
    all species detected at that time point.
    """
    all_dfs = []
    for result_file in result_files:
        try:
            df = pd.read_csv(result_file, sep="\t")
            if BIRDNET_REQUIRED_COLUMNS.issubset(set(df.columns)):
                all_dfs.append(df)
        except Exception:
            continue

    if not all_dfs:
        return []

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined[combined["Common Name"] != "nocall"]

    if combined.empty:
        return []

    # Match audio files by basename of the original path
    combined["audio_basename"] = combined["Begin Path"].apply(
        lambda p: Path(p).name
    )
    combined["local_audio_path"] = combined["audio_basename"].map(audio_files)
    combined = combined.dropna(subset=["local_audio_path"])

    if combined.empty:
        return []

    # Group by (audio file, begin time) to aggregate species per detection window
    grouped = combined.groupby(["local_audio_path", "Begin Time (s)"])

    clips = []
    for (audio_path, begin_time), group in grouped:
        clips.append(
            {
                "filename": audio_path,
                "audio_basename": group["audio_basename"].iloc[0],
                "start_time": float(begin_time),
                "end_time": float(group["End Time (s)"].iloc[0]),
                "species_array": group["Common Name"].tolist(),
                "confidence_array": [
                    float(c) for c in group["Confidence"].tolist()
                ],
                "species_codes": group["Species Code"].tolist(),
            }
        )

    clips.sort(key=lambda c: (c["filename"], c["start_time"]))
    return clips


def get_unique_species(clips):
    """Get sorted list of unique species across all clips."""
    species = set()
    for clip in clips:
        species.update(clip["species_array"])
    return sorted(species)
