"""Persistent, provenance-preserving store for official football pages."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from ..config import OFFICIAL_CORPUS_PATH

TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _tokens(value: str) -> set[str]:
    return set(TOKEN_RE.findall(value.casefold()))


class OfficialCorpus:
    """Small JSONL corpus that works before optional vector dependencies exist."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or OFFICIAL_CORPUS_PATH

    def documents(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        documents: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                document = json.loads(line)
            except json.JSONDecodeError:
                continue

            if document.get("url") and document.get("content"):
                documents.append(document)

        return documents

    def upsert(self, documents: Iterable[dict[str, Any]]) -> int:
        by_url = {document["url"]: document for document in self.documents()}
        timestamp = datetime.now(timezone.utc).isoformat()

        for document in documents:
            url = str(document.get("url") or "").strip()
            content = str(document.get("content") or "").strip()
            if not url or not content:
                continue

            by_url[url] = {
                "title": document.get("title") or urlparse(url).netloc,
                "url": url,
                "source": document.get("source") or urlparse(url).netloc,
                "date": document.get("date"),
                "content": content,
                "official": True,
                "ingested_at": timestamp,
            }

        if not by_url:
            return 0

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(
            "".join(json.dumps(document, ensure_ascii=False) + "\n" for document in by_url.values()),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
        return len(by_url)

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        ranked: list[tuple[float, dict[str, Any]]] = []
        for document in self.documents():
            haystack = f"{document.get('title', '')} {document.get('content', '')}"
            document_tokens = _tokens(haystack)
            overlap = len(query_tokens & document_tokens)
            if overlap == 0:
                continue

            score = overlap / max(len(query_tokens), 1)
            ranked.append(
                (
                    score,
                    {
                        "title": document.get("title"),
                        "url": document.get("url"),
                        "snippet": str(document.get("content", ""))[:500],
                        "excerpt": str(document.get("content", ""))[:520],
                        "scraped": True,
                        "cache_hit": True,
                        "official": True,
                        "score": score,
                    },
                )
            )

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [result for _, result in ranked[:top_k]]
