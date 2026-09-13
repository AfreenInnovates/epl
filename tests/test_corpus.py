"""Standalone tests for the official-source corpus."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eplai.rag.corpus import OfficialCorpus  # noqa: E402


def test_corpus_upserts_and_searches_with_provenance() -> None:
    with TemporaryDirectory() as directory:
        corpus = OfficialCorpus(Path(directory) / "official.jsonl")
        corpus.upsert(
            [
                {
                    "title": "Official squad news",
                    "url": "https://club.example/squad",
                    "source": "club.example",
                    "content": "Bruno Fernandes returned to midfield training before the weekend fixture.",
                }
            ]
        )

        results = corpus.search("Bruno midfield training")

        assert len(results) == 1
        assert results[0]["url"] == "https://club.example/squad"
        assert results[0]["official"] is True
        assert results[0]["cache_hit"] is True


if __name__ == "__main__":
    test_corpus_upserts_and_searches_with_provenance()
    print("ok  test_corpus_upserts_and_searches_with_provenance")
