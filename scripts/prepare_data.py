"""Turn the raw season CSV into the processed tables the app serves.

Writes ``data/processed/player_knowledge.csv``, which is what the stats tool
and the website read at request time.

    python scripts/prepare_data.py
"""

from __future__ import annotations

import sys

import _bootstrap  # noqa: F401

from eplai.config import MIN_MINUTES
from eplai.data import load_raw, build_model_frame, write_player_knowledge


def main() -> int:
    df = load_raw()
    print(f"Loaded {len(df)} player rows from the raw dataset.")

    df_model = build_model_frame(df)
    print(f"{len(df_model)} players remain after the {MIN_MINUTES}-minute filter.")

    path = write_player_knowledge(df_model)
    print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
