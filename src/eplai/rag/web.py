"""Web search and scraping through the Anakin API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests

from ..config import settings

SEARCH_ENDPOINT = "https://api.anakin.io/v1/search"
SCRAPE_ENDPOINT = "https://api.anakin.io/v1/url-scraper/scrape"

BOILERPLATE_TAGS = ["script", "style", "noscript", "nav", "footer"]


class WebSearchError(RuntimeError):
    """Raised when the search provider cannot be reached or is unconfigured."""


class AnakinClient:
    """Thin wrapper over the two Anakin endpoints this project uses."""

    def __init__(self, api_key: str | None = None, timeout: int = 60) -> None:
        self.api_key = api_key or settings.anakin_api_key
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise WebSearchError(
                "ANAKIN_API_KEY is not set, so web search is unavailable."
            )

        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        response = requests.post(
            SEARCH_ENDPOINT,
            headers=self._headers(),
            json={"prompt": query, "limit": limit},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def scrape(self, url: str, use_browser: bool = False) -> dict[str, Any]:
        response = requests.post(
            SCRAPE_ENDPOINT,
            headers=self._headers(),
            json={"url": url, "useBrowser": use_browser, "generateJson": False},
            timeout=max(self.timeout, 90),
        )
        response.raise_for_status()
        return response.json()


def html_to_text(html: str) -> str:
    """Strip boilerplate tags and collapse the remaining text."""
    from bs4 import BeautifulSoup  # imported lazily: only needed when scraping

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(BOILERPLATE_TAGS):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def search_results(query: str, limit: int = 5, client: AnakinClient | None = None) -> list[dict[str, Any]]:
    """Flatten a search response into title/url/date/snippet records."""
    client = client or AnakinClient()

    payload = client.search(query, limit=limit)

    return [
        {
            "title": result.get("title"),
            "url": result.get("url"),
            "date": result.get("date"),
            "snippet": result.get("snippet"),
        }
        for result in payload.get("results", [])
    ]


def scrape_documents(
    results: list[dict[str, Any]],
    client: AnakinClient | None = None,
    min_words: int = 100,
) -> list[dict[str, Any]]:
    """Scrape each result, falling back to its snippet when scraping fails.

    Pages that yield fewer than ``min_words`` are kept only as snippets, since
    short scrapes are usually cookie walls rather than real content.
    """
    client = client or AnakinClient()

    documents: list[dict[str, Any]] = []

    for result in results:
        url = result.get("url")

        if not url:
            continue

        source = urlparse(url).netloc
        content = ""

        try:
            page = client.scrape(url)
            html = page.get("html", "")

            if html:
                content = html_to_text(html)
        except Exception as exc:  # network, parse or provider failure
            print(f"Scrape failed for {url}: {exc}")

        if len(content.split()) < min_words:
            content = str(result.get("snippet") or "")

        if len(content.split()) < 10:
            continue

        documents.append(
            {
                "title": result.get("title"),
                "url": url,
                "date": result.get("date"),
                "source": source,
                "content": content,
            }
        )

    return documents
