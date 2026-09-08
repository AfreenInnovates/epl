"""Loading and feature engineering for the raw season CSV.

The transformations here mirror notebooks 03 and 04 exactly, so embeddings
trained in the notebook stay aligned with statistics served by the website.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import (
    MIN_MINUTES,
    PLAYER_KNOWLEDGE_CSV,
    PROCESSED_DATA_DIR,
    RAW_STATS_CSV,
)
from .schema import (
    IDENTITY_COLS,
    IMPORTANT_STATS,
    PER90_COLS,
    PERCENTAGE_COLS,
    model_feature_columns,
)


class RawDataMissingError(FileNotFoundError):
    """Raised when the season CSV has not been downloaded yet."""


def load_raw(path: Path | None = None) -> pd.DataFrame:
    """Read the raw Kaggle CSV and coerce percentage columns to floats."""
    path = path or RAW_STATS_CSV

    if not path.exists():
        raise RawDataMissingError(
            f"Raw dataset not found at {path}.\n"
            "Run `python scripts/download_data.py` (needs Kaggle credentials), "
            "or drop epl_player_stats_24_25.csv into data/raw/ manually."
        )

    df = pd.read_csv(path)

    # Stored as "87%" strings. Depending on the pandas version these arrive as
    # object or as StringDtype, so test for "not numeric" rather than for a
    # specific dtype -- the narrower check silently skipped the conversion and
    # left percentages as strings.
    for col in PERCENTAGE_COLS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = (
                df[col].astype(str).str.replace("%", "", regex=False).astype(float)
            )

    return df


def add_per90_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Append a ``<stat>_per90`` column for every counting stat."""
    df = df.copy()

    for col in PER90_COLS:
        df[f"{col}_per90"] = (df[col] / df["Minutes"]) * 90

    return df


def build_model_frame(df: pd.DataFrame, min_minutes: int = MIN_MINUTES) -> pd.DataFrame:
    """Per-90 enrich the frame and drop low-minute players."""
    enriched = add_per90_columns(df)
    return enriched[enriched["Minutes"] >= min_minutes].copy().reset_index(drop=True)


def build_player_knowledge(df_model: pd.DataFrame) -> pd.DataFrame:
    """The identity + headline-stat table used by the stats tool and the UI."""
    return df_model[IDENTITY_COLS + IMPORTANT_STATS].copy()


def build_feature_matrix(df_model: pd.DataFrame) -> pd.DataFrame:
    """The numeric matrix fed to the scaler and the embedding models."""
    return df_model[model_feature_columns()].copy()


def drop_correlated_features(X: pd.DataFrame, threshold: float = 0.90) -> tuple[pd.DataFrame, list[str]]:
    """Remove one side of every feature pair correlated above ``threshold``.

    Returns the reduced frame and the list of dropped column names, so the same
    columns can be dropped at inference time.
    """
    corr = X.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))

    to_drop = [column for column in upper.columns if any(upper[column] > threshold)]

    return X.drop(columns=to_drop), to_drop


def prepare(path: Path | None = None) -> pd.DataFrame:
    """Raw CSV to modelling population, in one call."""
    return build_model_frame(load_raw(path))


@lru_cache(maxsize=1)
def player_knowledge() -> pd.DataFrame:
    """Cached player-knowledge table.

    Prefers the pre-computed CSV in ``data/processed`` so the web backend can
    start without the raw Kaggle download; falls back to computing it.
    """
    if PLAYER_KNOWLEDGE_CSV.exists():
        return pd.read_csv(PLAYER_KNOWLEDGE_CSV)

    return build_player_knowledge(prepare())


def write_player_knowledge(df_model: pd.DataFrame) -> Path:
    """Persist the player-knowledge table for the serving layer."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    knowledge = build_player_knowledge(df_model)
    knowledge.to_csv(PLAYER_KNOWLEDGE_CSV, index=False)

    return PLAYER_KNOWLEDGE_CSV
