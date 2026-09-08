"""Loading of the trained artifacts and the cosine-similarity matrices.

Cosine similarity is computed with numpy rather than scikit-learn so the
serving path stays dependency-light; the matrices are tiny (397 x 397).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import ARTIFACT_DIR, PLAYER_CLUSTERS_CSV

EMBEDDING_FILES = {
    "standard": "standard_embeddings.npy",
    "siamese": "siamese_embeddings.npy",
    "triplet": "triplet_embeddings.npy",
}


def cosine_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Full pairwise cosine similarity for a set of row vectors."""
    matrix = np.asarray(embeddings, dtype=np.float64)

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0

    normalised = matrix / norms

    return normalised @ normalised.T


@dataclass
class EmbeddingStore:
    """Player metadata plus one similarity matrix per representation."""

    metadata: pd.DataFrame
    embeddings: dict[str, np.ndarray]
    similarity: dict[str, np.ndarray]

    @property
    def player_names(self) -> np.ndarray:
        return self.metadata["Player Name"].to_numpy()

    def index_of(self, player_name: str) -> int:
        matches = np.where(self.player_names == player_name)[0]

        if matches.size == 0:
            raise KeyError(f"{player_name} not found in player embeddings.")

        return int(matches[0])

    def resolve(self, player_name: str) -> str | None:
        """Case-insensitive / partial name resolution.

        Returns the canonical name, or ``None`` when nothing matches. Exact
        matches win, then case-insensitive, then a unique substring match.
        """
        names = self.player_names

        if player_name in names:
            return player_name

        query = player_name.strip().casefold()

        lowered = {name.casefold(): name for name in names}
        if query in lowered:
            return lowered[query]

        partial = [name for name in names if query in name.casefold()]
        if len(partial) == 1:
            return partial[0]

        # Fall back to matching on surname when the query is a single token.
        surname = [name for name in names if name.casefold().split()[-1] == query]
        if len(surname) == 1:
            return surname[0]

        return None

    def profile(self, player_name: str) -> dict[str, object]:
        row = self.metadata.iloc[self.index_of(player_name)]
        return {key: row[key] for key in self.metadata.columns}


@lru_cache(maxsize=1)
def load_store(artifact_dir: Path | None = None) -> EmbeddingStore:
    """Load artifacts once per process."""
    artifact_dir = artifact_dir or ARTIFACT_DIR

    metadata_path = artifact_dir / "player_metadata.csv"
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"player_metadata.csv missing from {artifact_dir}. "
            "Unzip premier_league_artifacts.zip into artifacts/."
        )

    metadata = pd.read_csv(metadata_path)

    # Cluster labels are optional enrichment produced by notebook 03.
    if PLAYER_CLUSTERS_CSV.exists():
        clusters = pd.read_csv(PLAYER_CLUSTERS_CSV)[["Player Name", "Cluster"]]
        metadata = metadata.merge(clusters, on="Player Name", how="left")

    embeddings = {
        name: np.load(artifact_dir / filename)
        for name, filename in EMBEDDING_FILES.items()
        if (artifact_dir / filename).exists()
    }

    if not embeddings:
        raise FileNotFoundError(f"No embedding files found in {artifact_dir}.")

    similarity = {name: cosine_similarity_matrix(matrix) for name, matrix in embeddings.items()}

    return EmbeddingStore(metadata=metadata, embeddings=embeddings, similarity=similarity)
