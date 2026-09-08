"""Download the 2024/25 Premier League player-stats dataset from Kaggle.

Requires Kaggle credentials, supplied either as a ``~/.kaggle/kaggle.json``
file or as the ``KAGGLE_USERNAME`` / ``KAGGLE_KEY`` environment variables.

    python scripts/download_data.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from eplai.config import KAGGLE_DATASET, RAW_DATA_DIR, RAW_STATS_CSV


def ensure_credentials() -> None:
    """Materialise kaggle.json from environment variables when necessary."""
    config_dir = Path.home() / ".kaggle"
    config_file = config_dir / "kaggle.json"

    if config_file.exists():
        return

    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")

    if not (username and key):
        raise SystemExit(
            "No Kaggle credentials found.\n"
            "Either place kaggle.json in ~/.kaggle/, or set KAGGLE_USERNAME and "
            "KAGGLE_KEY in your .env file.\n"
            "Alternatively, download the dataset manually from\n"
            f"  https://www.kaggle.com/datasets/{KAGGLE_DATASET}\n"
            f"and save the CSV to {RAW_STATS_CSV}"
        )

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps({"username": username, "key": key}), encoding="utf-8")

    try:
        config_file.chmod(0o600)
    except OSError:
        pass  # Windows filesystems may not support the mode change

    print(f"Wrote Kaggle credentials to {config_file}")


def main() -> int:
    if RAW_STATS_CSV.exists():
        print(f"Dataset already present at {RAW_STATS_CSV}")
        return 0

    ensure_credentials()

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        raise SystemExit("kaggle is not installed. Run: pip install kaggle")

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    api = KaggleApi()
    api.authenticate()

    print(f"Downloading {KAGGLE_DATASET} to {RAW_DATA_DIR} ...")
    api.dataset_download_files(KAGGLE_DATASET, path=str(RAW_DATA_DIR), unzip=True)

    # The archive may nest the CSV; flatten it to the expected location.
    if not RAW_STATS_CSV.exists():
        candidates = list(RAW_DATA_DIR.rglob("*.csv"))

        if not candidates:
            raise SystemExit("Download finished but no CSV was found.")

        shutil.move(str(candidates[0]), RAW_STATS_CSV)

    print(f"Ready: {RAW_STATS_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
