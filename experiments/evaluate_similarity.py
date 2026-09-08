"""Compare the three learned representations against each other.

Position consistency @ k is the share of a player's k nearest neighbours that
share their listed position. It is a proxy, not ground truth -- a good style
model *should* occasionally cross position lines, because an inverted winger
and an attacking midfielder can play the same role. Read a very high score as
"this model mostly memorised position", not as "this model is best".

    python experiments/evaluate_similarity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from eplai.similarity import load_store

BENCHMARK_PLAYERS = [
    "Bukayo Saka",
    "Erling Haaland",
    "Declan Rice",
    "David Raya",
    "Virgil van Dijk",
    "Cole Palmer",
]


def position_consistency(similarity: np.ndarray, positions: np.ndarray, idx: int, k: int = 10) -> float:
    scores = similarity[idx].copy()
    scores[idx] = -1

    top_indices = np.argsort(scores)[::-1][:k]

    return float((positions[top_indices] == positions[idx]).mean())


def neighbour_spread(similarity: np.ndarray, idx: int, k: int = 10) -> float:
    """Gap between the closest and the k-th closest neighbour.

    A model whose top-10 are all ~0.999 similar is not discriminating.
    """
    scores = similarity[idx].copy()
    scores[idx] = -1

    top = np.sort(scores)[::-1][:k]

    return float(top[0] - top[-1])


def main() -> int:
    store = load_store()

    names = store.player_names
    positions = store.metadata["Position"].to_numpy()

    rows = []

    for model_name, similarity in store.similarity.items():
        consistencies = []
        spreads = []

        for idx in range(len(names)):
            consistencies.append(position_consistency(similarity, positions, idx))
            spreads.append(neighbour_spread(similarity, idx))

        rows.append(
            {
                "Model": model_name,
                "Dimensions": store.embeddings[model_name].shape[1],
                "Position consistency @10": round(float(np.mean(consistencies)), 3),
                "Neighbour spread @10": round(float(np.mean(spreads)), 4),
            }
        )

    print("\nModel comparison across all players")
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n\nPosition consistency @10 for benchmark players")

    per_player = []

    for player in BENCHMARK_PLAYERS:
        resolved = store.resolve(player)

        if resolved is None:
            print(f"  (skipping {player}: not in dataset)")
            continue

        idx = store.index_of(resolved)

        row = {"Player": resolved, "Position": positions[idx]}

        for model_name, similarity in store.similarity.items():
            row[model_name] = round(position_consistency(similarity, positions, idx), 2)

        per_player.append(row)

    print(pd.DataFrame(per_player).to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
