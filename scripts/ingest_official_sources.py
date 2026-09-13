"""Map and crawl official football sites into the local ScoutLab corpus.

Examples:
    python scripts/ingest_official_sources.py --url https://www.premierleague.com
    python scripts/ingest_official_sources.py --url https://www.arsenal.com --max-pages 25 --rebuild-index
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Callable
from urllib.parse import urlparse

import _bootstrap  # noqa: F401

from eplai.rag import OfficialCorpus, WebIndex, chunk_documents, html_to_text
from eplai.rag.web import AnakinClient


def poll(
    getter: Callable[[str], dict[str, Any]],
    job_id: str,
    label: str,
    interval: float = 2.0,
    timeout: float = 600.0,
) -> dict[str, Any]:
    started = time.monotonic()

    while time.monotonic() - started < timeout:
        result = getter(job_id)
        status = result.get("status")
        print(f"{label}: {status}")

        if status in {"completed", "failed"}:
            return result

        time.sleep(interval)

    raise TimeoutError(f"{label} did not finish within {timeout:.0f} seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", required=True, help="Official site root.")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--map-limit", type=int, default=100)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--search", default="", help="Map URL filter, such as /news/")
    parser.add_argument("--rebuild-index", action="store_true")
    args = parser.parse_args()

    client = AnakinClient()
    if not client.configured:
        raise SystemExit("ANAKIN_API_KEY is not set. Add it to your .env file.")

    documents: list[dict[str, Any]] = []

    for root in args.url:
        domain = urlparse(root).netloc
        print(f"\nMapping official source: {domain}")
        map_job = client.submit_map(
            root,
            limit=args.map_limit,
            depth=args.depth,
            search=args.search,
        )
        map_result = poll(client.get_map, map_job["jobId"], f"Map {domain}")

        if map_result.get("status") != "completed":
            raise RuntimeError(map_result.get("error") or f"Map failed for {root}")

        links = map_result.get("links", [])
        print(f"  discovered {len(links)} official URLs")

        crawl_job = client.submit_crawl(
            root,
            max_pages=args.max_pages,
            include_patterns=[args.search] if args.search else [],
            country="gb",
        )
        crawl_result = poll(client.get_crawl, crawl_job["jobId"], f"Crawl {domain}")

        if crawl_result.get("status") != "completed":
            raise RuntimeError(crawl_result.get("error") or f"Crawl failed for {root}")

        for page in crawl_result.get("results", []):
            if page.get("status") != "completed":
                continue

            markdown = str(page.get("markdown") or "").strip()
            html = str(page.get("html") or "")
            content = markdown or html_to_text(html)

            if content:
                documents.append(
                    {
                        "title": page.get("title") or page.get("url") or domain,
                        "url": page.get("url"),
                        "source": domain,
                        "content": content,
                    }
                )

    corpus = OfficialCorpus()
    count = corpus.upsert(documents)
    print(f"\nOfficial corpus now contains {count} pages at {corpus.path}")

    if args.rebuild_index:
        chunks = chunk_documents(corpus.documents())
        if chunks:
            index = WebIndex.build(chunks)
            index.save()
            print(f"Rebuilt vector index with {len(chunks)} official chunks")

    return 0


if __name__ == "__main__":
    sys.exit(main())
