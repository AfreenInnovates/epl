"""Consensus similarity search across the three learned representations.

A player that three independent representations all rank highly is a stronger
signal than a player that only one of them likes, so results are ranked by how
many models retrieved them before their average rank is considered.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .store import EmbeddingStore, load_store


def per_model_neighbours(
    store: EmbeddingStore,
    player_name: str,
    top_k: int = 5,
) -> pd.DataFrame:
    """Top-k neighbours from each representation, as a long-format frame."""
    query_idx = store.index_of(player_name)

    records = []

    for model_name, sim_matrix in store.similarity.items():
        scores = sim_matrix[query_idx].copy()
        scores[query_idx] = -1  # never return the query player

        top_indices = np.argsort(scores)[::-1][:top_k]

        for rank, idx in enumerate(top_indices, start=1):
            records.append(
                {
                    "Model": model_name,
                    "Player": store.player_names[idx],
                    "Rank": rank,
                    "Similarity": float(scores[idx]),
                }
            )

    return pd.DataFrame(records)


def retrieve_similar_players(
    player_name: str,
    top_k: int = 5,
    store: EmbeddingStore | None = None,
) -> pd.DataFrame:
    """Consensus neighbour table, ranked by agreement then by mean rank."""
    store = store or load_store()

    results = per_model_neighbours(store, player_name, top_k=top_k)

    consensus = (
        results.groupby("Player")
        .agg(
            Models_Retrieved=("Model", "count"),
            Mean_Rank=("Rank", "mean"),
            Best_Rank=("Rank", "min"),
            Mean_Similarity=("Similarity", "mean"),
        )
        .reset_index()
    )

    consensus = consensus.sort_values(
        ["Models_Retrieved", "Mean_Rank"],
        ascending=[False, True],
    ).reset_index(drop=True)

    metadata_cols = [c for c in ("Club", "Position") if c in store.metadata.columns]

    if metadata_cols:
        consensus = consensus.merge(
            store.metadata[["Player Name", *metadata_cols]],
            left_on="Player",
            right_on="Player Name",
            how="left",
        ).drop(columns=["Player Name"])

    return consensus


def similar_players_records(
    player_name: str,
    top_k: int = 5,
    store: EmbeddingStore | None = None,
) -> list[dict[str, object]]:
    """JSON-serialisable version of :func:`retrieve_similar_players`."""
    frame = retrieve_similar_players(player_name, top_k=top_k, store=store)

    records: list[dict[str, object]] = []

    for row in frame.to_dict(orient="records"):
        records.append(
            {
                "player": row["Player"],
                "club": row.get("Club"),
                "position": row.get("Position"),
                "models_retrieved": int(row["Models_Retrieved"]),
                "mean_rank": round(float(row["Mean_Rank"]), 2),
                "best_rank": int(row["Best_Rank"]),
                "mean_similarity": round(float(row["Mean_Similarity"]), 4),
            }
        )

    return records
