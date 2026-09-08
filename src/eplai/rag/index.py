"""FAISS-backed vector index over scraped web chunks.

sentence-transformers and faiss are imported lazily so the agent and the web
backend can run without them installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ..config import WEB_INDEX_DIR, settings


class WebIndex:
    """Dense retrieval over web chunks, with per-source diversification."""

    def __init__(self, chunks: list[dict[str, Any]], embeddings: np.ndarray, model_name: str) -> None:
        self.chunks = chunks
        self.embeddings = embeddings.astype("float32")
        self.model_name = model_name

        self._model = None
        self._index = None

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    @classmethod
    def build(cls, chunks: list[dict[str, Any]], model_name: str | None = None) -> "WebIndex":
        from sentence_transformers import SentenceTransformer

        model_name = model_name or settings.embedding_model
        model = SentenceTransformer(model_name)

        embeddings = model.encode(
            [chunk["text"] for chunk in chunks],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        index = cls(chunks, embeddings, model_name)
        index._model = model

        return index

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def save(self, directory: Path | None = None) -> Path:
        directory = directory or WEB_INDEX_DIR
        directory.mkdir(parents=True, exist_ok=True)

        np.save(directory / "embeddings.npy", self.embeddings)

        (directory / "chunks.json").write_text(
            json.dumps(self.chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (directory / "meta.json").write_text(
            json.dumps({"model_name": self.model_name}), encoding="utf-8"
        )

        return directory

    @classmethod
    def load(cls, directory: Path | None = None) -> "WebIndex":
        directory = directory or WEB_INDEX_DIR

        if not (directory / "chunks.json").exists():
            raise FileNotFoundError(
                f"No web index at {directory}. Run `python scripts/build_web_index.py` first."
            )

        chunks = json.loads((directory / "chunks.json").read_text(encoding="utf-8"))
        embeddings = np.load(directory / "embeddings.npy")
        meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))

        return cls(chunks, embeddings, meta["model_name"])

    # ------------------------------------------------------------------
    # retrieval
    # ------------------------------------------------------------------

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

        return self._model

    @property
    def index(self):
        if self._index is None:
            import faiss

            self._index = faiss.IndexFlatIP(self.embeddings.shape[1])
            self._index.add(self.embeddings)

        return self._index

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_embedding = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).astype("float32")

        scores, indices = self.index.search(query_embedding, min(top_k, len(self.chunks)))

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            chunk = dict(self.chunks[idx])
            chunk["score"] = float(score)
            results.append(chunk)

        return results

    def search_diverse(
        self,
        query: str,
        top_k: int = 5,
        max_per_source: int = 2,
    ) -> list[dict[str, Any]]:
        """Cap how many chunks a single domain can contribute.

        Without this, one long scraped page floods every slot and the answer
        ends up resting on a single source.
        """
        candidates = self.search(query, top_k=max(top_k * 3, 15))

        selected: list[dict[str, Any]] = []
        source_counts: dict[str, int] = {}

        for result in candidates:
            source = str(result.get("source"))

            if source_counts.get(source, 0) >= max_per_source:
                continue

            selected.append(result)
            source_counts[source] = source_counts.get(source, 0) + 1

            if len(selected) >= top_k:
                break

        return selected
