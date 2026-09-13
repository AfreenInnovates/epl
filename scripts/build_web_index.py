"""Build the FAISS index over scraped football coverage.

Searches the web for each seed player, scrapes the results, chunks them and
embeds the chunks. The index is optional -- the agent works without it, using
live search instead -- but it makes the offline RAG path in notebook 04
reproducible.

    python scripts/build_web_index.py --players "Bukayo Saka" "Cole Palmer"
"""

from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401

from eplai.config import WEB_INDEX_DIR
from eplai.rag import OfficialCorpus, WebIndex, chunk_documents, scrape_documents, search_results
from eplai.rag.web import AnakinClient

DEFAULT_PLAYERS = [
    "Bukayo Saka",
    "Mohamed Salah",
    "Cole Palmer",
    "Erling Haaland",
    "Bruno Fernandes",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", nargs="*", default=DEFAULT_PLAYERS)
    parser.add_argument("--limit", type=int, default=5, help="Search results per player.")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args()

    client = AnakinClient()

    if not client.configured:
        raise SystemExit("ANAKIN_API_KEY is not set. Add it to your .env file.")

    documents = []

    official_documents = OfficialCorpus().documents()
    if official_documents:
        print(f"Including {len(official_documents)} official corpus pages")
        documents.extend(official_documents)

    for player in args.players:
        query = f"{player} playing style tactical analysis Premier League"
        print(f"\nSearching: {query}")

        results = search_results(query, limit=args.limit, client=client)
        print(f"  {len(results)} results")

        documents.extend(scrape_documents(results, client=client))

    print(f"\nCollected {len(documents)} documents")

    if not documents:
        raise SystemExit("Nothing to index.")

    chunks = chunk_documents(documents, args.chunk_size, args.overlap)
    print(f"Split into {len(chunks)} chunks")

    index = WebIndex.build(chunks)
    index.save(WEB_INDEX_DIR)

    print(f"Index saved to {WEB_INDEX_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
