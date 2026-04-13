"""BirdNET Validator — validate bird species detections from BirdNET."""

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

__version__ = "0.1.0"

_PACKAGE_DIR = Path(__file__).parent
_DASHBOARD = _PACKAGE_DIR.parent / "src" / "dashboard.py"


def _open_browser_when_ready(port, timeout=30):
    """Wait for Streamlit to start, then open the browser."""
    import urllib.request
    url = f"http://localhost:{port}"
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)


def run(
    audio_dir,
    results_dir,
    output_dir,
    *,
    s3_endpoint_url="",
    s3_access_key="",
    s3_secret_key="",
    port=8501,
    open_browser=True,
):
    """Launch the BirdNET Validator app.

    Parameters
    ----------
    audio_dir : str
        Path to audio files (local path or s3:// URI).
    results_dir : str
        Path to BirdNET result files (local path or s3:// URI).
    output_dir : str
        Path where validation CSVs will be saved (local path or s3:// URI).
    s3_endpoint_url : str, optional
        S3 endpoint URL (only needed for s3:// paths).
    s3_access_key : str, optional
        S3 access key.
    s3_secret_key : str, optional
        S3 secret key.
    port : int, optional
        Port to run the app on (default: 8501).
    open_browser : bool, optional
        Whether to open the browser automatically (default: True).
    """
    # Pass config via environment variables
    env = os.environ.copy()
    env["AUDIO_DIR"] = str(audio_dir)
    env["RESULTS_DIR"] = str(results_dir)
    env["OUTPUT_DIR"] = str(output_dir)
    if s3_endpoint_url:
        env["S3_ENDPOINT_URL"] = s3_endpoint_url
    if s3_access_key:
        env["S3_ACCESS_KEY"] = s3_access_key
    if s3_secret_key:
        env["S3_SECRET_KEY"] = s3_secret_key

    if open_browser:
        threading.Thread(
            target=_open_browser_when_ready,
            args=(port,),
            daemon=True,
        ).start()

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(_DASHBOARD),
        "--server.port", str(port),
        "--server.headless", "true",
    ]

    # DEVNULL avoids "invalid handle" errors in environments where
    # standard handles may not exist (e.g. pythonw.exe, embedded interpreters).
    subprocess.run(
        cmd,
        env=env,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
