"""Data processing — directory scanning and BirdNET result parsing.

Supports both local directories and S3 URIs (s3://bucket/prefix).
"""

import io
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from s3_utils import is_s3_path, list_s3_files, read_s3_text

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".ogg"}
BIRDNET_REQUIRED_COLUMNS = {
    "Begin Time (s)",
    "Common Name",
    "Confidence",
    "Begin Path",
}

# Regex to find YYYYMMDD_HHMMSS (or YYYYMMDDTHHMMSS) in a filename
_DATETIME_PATTERN = re.compile(r"(\d{8})[_T](\d{6})")


@st.cache_data(show_spinner=False)
def process_local_directories(audio_dir, results_dir):
    """Scan directories for audio files and BirdNET results.

    Works with both local paths and S3 URIs.
    Returns dict with audio_files mapping, clips list, and total count.
    """
    audio_files = _find_audio_files(audio_dir)
    result_files = _find_result_files(results_dir)
    clips = _parse_birdnet_results(result_files, audio_files)

    return {
        "audio_files": audio_files,
        "clips": clips,
        "total_clips": len(clips),
    }


def _find_audio_files(root_dir):
    """Find all audio files and return dict mapping basename -> path/URI."""
    if is_s3_path(root_dir):
        audio_map = {}
        uris = list_s3_files(root_dir, extension=tuple(SUPPORTED_AUDIO_EXTENSIONS))
        for uri in uris:
            basename = uri.split("/")[-1]
            audio_map[basename] = uri
        return audio_map

    audio_map = {}
    for root, _, files in os.walk(root_dir):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_AUDIO_EXTENSIONS:
                audio_map[filename] = os.path.join(root, filename)
    return audio_map


def _find_result_files(root_dir):
    """Find all potential BirdNET result .txt files."""
    if is_s3_path(root_dir):
        return list_s3_files(root_dir, extension=".txt")

    result_files = []
    for root, _, files in os.walk(root_dir):
        for filename in files:
            if filename.endswith(".txt"):
                result_files.append(str(Path(root) / filename))
    return result_files


def _read_result_file(result_file):
    """Read a BirdNET result file from local or S3."""
    if is_s3_path(result_file):
        text = read_s3_text(result_file)
        return pd.read_csv(io.StringIO(text), sep="\t")
    return pd.read_csv(result_file, sep="\t")


def _parse_birdnet_results(result_files, audio_files):
    """Parse BirdNET result files and create grouped clip list.

    Groups detections by (audio file, begin time) so each clip contains
    all species detected at that time point.
    """
    all_dfs = []
    for result_file in result_files:
        try:
            df = _read_result_file(result_file)
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
    combined["audio_basename"] = combined["Begin Path"].apply(os.path.basename)
    combined["local_audio_path"] = combined["audio_basename"].map(audio_files)
    combined = combined.dropna(subset=["local_audio_path"])

    if combined.empty:
        return []

    # Group by (audio file, begin time) to aggregate species per detection window
    grouped = combined.groupby(["local_audio_path", "Begin Time (s)"])

    clips = []
    for (audio_path, begin_time), group in grouped:
        basename = group["audio_basename"].iloc[0]
        clips.append(
            {
                "filename": audio_path,
                "audio_basename": basename,
                "start_time": float(begin_time),
                "end_time": float(group["End Time (s)"].iloc[0]),
                "species_array": group["Common Name"].tolist(),
                "confidence_array": [
                    float(c) for c in group["Confidence"].tolist()
                ],
                "species_codes": group["Species Code"].tolist(),
                "recording_datetime": parse_datetime_from_filename(basename),
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


def parse_datetime_from_filename(filename):
    """Extract a datetime from a filename containing YYYYMMDD_HHMMSS.

    Returns a datetime object, or None if no pattern is found.
    Examples:
        SMA13789_20250927_182102.wav  -> 2025-09-27 18:21:02
        recorder_20231015T060000.flac -> 2023-10-15 06:00:00
    """
    match = _DATETIME_PATTERN.search(filename)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None
