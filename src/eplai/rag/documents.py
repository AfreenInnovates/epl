"""Turning player rows and scraped pages into retrievable text."""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def player_to_document(row: pd.Series) -> str:
    """A compact natural-language profile of a single player."""
    return f"""
Player: {row['Player Name']}
Club: {row['Club']}
Position: {row['Position']}

Key Statistics:
Goals: {row['Goals']}
Assists: {row['Assists']}
Shots: {row['Shots']}
Shots On Target: {row['Shots On Target']}

Goals per 90: {row['Goals_per90']:.3f}
Assists per 90: {row['Assists_per90']:.3f}
Shots per 90: {row['Shots_per90']:.3f}
Touches per 90: {row['Touches_per90']:.3f}
Passes per 90: {row['Passes_per90']:.3f}
Carries per 90: {row['Carries_per90']:.3f}
Progressive Carries per 90: {row['Progressive Carries_per90']:.3f}
Through Balls per 90: {row['Through Balls_per90']:.3f}
Crosses per 90: {row['Crosses_per90']:.3f}

Pass Completion: {row['Passes%']}%
Conversion: {row['Conversion %']}%
Tackles per 90: {row['Tackles_per90']:.3f}
Interceptions per 90: {row['Interceptions_per90']:.3f}
Ground Duels per 90: {row['Ground Duels_per90']:.3f}
Aerial Duels per 90: {row['Aerial Duels_per90']:.3f}
""".strip()


def build_player_documents(player_knowledge: pd.DataFrame) -> dict[str, str]:
    """Map every player name to its profile document."""
    return {
        row["Player Name"]: player_to_document(row)
        for _, row in player_knowledge.iterrows()
    }


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping word windows.

    Overlap keeps a sentence that straddles a boundary retrievable from both
    sides of the split.
    """
    words = text.split()

    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")

    chunks: list[str] = []
    start = 0

    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def chunk_documents(
    documents: Iterable[dict[str, object]],
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[dict[str, object]]:
    """Flatten a list of documents into retrievable chunks with provenance."""
    chunks: list[dict[str, object]] = []

    for doc_id, doc in enumerate(documents):
        for chunk_id, chunk in enumerate(
            chunk_text(str(doc.get("content", "")), chunk_size, overlap)
        ):
            chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "title": doc.get("title"),
                    "url": doc.get("url"),
                    "source": doc.get("source"),
                    "date": doc.get("date"),
                    "text": chunk,
                }
            )

    return chunks
