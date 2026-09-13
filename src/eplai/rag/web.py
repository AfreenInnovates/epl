"""Web search and scraping through the Anakin API."""

from __future__ import annotations

from math import ceil
from typing import Any
from urllib.parse import urlparse

import requests

from ..config import settings
from .cache import SlidingWindowRateLimiter, TtlCache

SEARCH_ENDPOINT = "https://api.anakin.io/v1/search"
SCRAPE_ENDPOINT = "https://api.anakin.io/v1/url-scraper/scrape"
ANAKIN_API_BASE = "https://api.anakin.io/v1"

BOILERPLATE_TAGS = ["script", "style", "noscript", "nav", "footer"]
ANAKIN_CACHE = TtlCache(
    max_entries=settings.anakin_cache_max_entries,
    ttl_seconds=settings.anakin_cache_ttl_seconds,
)
ANAKIN_RATE_LIMITER = SlidingWindowRateLimiter(
    max_requests=settings.anakin_rate_limit_requests,
    window_seconds=settings.anakin_rate_limit_window_seconds,
)


class WebSearchError(RuntimeError):
    """Raised when the search provider cannot be reached or is unconfigured."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


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

    def _check_rate_limit(self) -> None:
        retry_after = ANAKIN_RATE_LIMITER.retry_after()

        if retry_after is not None:
            seconds = ceil(retry_after)
            raise WebSearchError(
                f"Anakin request limit reached. Retry in {seconds} seconds.",
                retry_after=seconds,
            )

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.status_code == 429:
            raw_retry_after = response.headers.get("Retry-After", "60")
            try:
                retry_after = max(1, int(float(raw_retry_after)))
            except ValueError:
                retry_after = 60

            raise WebSearchError(
                f"Anakin is rate limiting requests. Retry in {retry_after} seconds.",
                retry_after=retry_after,
            )

        response.raise_for_status()

    def _json_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        rate_limited: bool = True,
    ) -> dict[str, Any]:
        """Call a non-cached Anakin endpoint used by async jobs."""
        headers = self._headers()

        if rate_limited:
            self._check_rate_limit()

        response = requests.request(
            method,
            f"{ANAKIN_API_BASE}{path}",
            headers=headers,
            json=payload,
            timeout=max(self.timeout, 90),
        )
        self._raise_for_status(response)
        return response.json()

    def submit_agentic_search(self, prompt: str) -> dict[str, Any]:
        return self._json_request("POST", "/agentic-search", {"prompt": prompt})

    def get_agentic_search(self, job_id: str) -> dict[str, Any]:
        return self._json_request("GET", f"/agentic-search/{job_id}", rate_limited=False)

    def submit_map(
        self,
        url: str,
        limit: int = 100,
        depth: int = 2,
        search: str = "",
    ) -> dict[str, Any]:
        return self._json_request(
            "POST",
            "/map",
            {
                "url": url,
                "limit": min(max(limit, 1), 5000),
                "depth": min(max(depth, 1), 5),
                "search": search,
            },
        )

    def get_map(self, job_id: str) -> dict[str, Any]:
        return self._json_request("GET", f"/map/{job_id}", rate_limited=False)

    def submit_crawl(
        self,
        url: str,
        max_pages: int = 10,
        include_patterns: list[str] | None = None,
        country: str = "gb",
    ) -> dict[str, Any]:
        return self._json_request(
            "POST",
            "/crawl",
            {
                "url": url,
                "maxPages": min(max(max_pages, 1), 100),
                "includePatterns": include_patterns or [],
                "country": country,
            },
        )

    def get_crawl(self, job_id: str) -> dict[str, Any]:
        return self._json_request("GET", f"/crawl/{job_id}", rate_limited=False)

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        headers = self._headers()
        cache_key = f"search:{query.strip().casefold()}:{limit}"
        cached = ANAKIN_CACHE.get(cache_key)

        if cached is not None:
            return {**cached, "_cache_hit": True}

        self._check_rate_limit()
        response = requests.post(
            SEARCH_ENDPOINT,
            headers=headers,
            json={"prompt": query, "limit": limit},
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        payload = response.json()
        ANAKIN_CACHE.set(cache_key, payload)
        return {**payload, "_cache_hit": False}

    def scrape(self, url: str, use_browser: bool = False) -> dict[str, Any]:
        headers = self._headers()
        cache_key = f"scrape:{url.strip()}:{int(use_browser)}"
        cached = ANAKIN_CACHE.get(cache_key)

        if cached is not None:
            return {**cached, "_cache_hit": True}

        self._check_rate_limit()
        response = requests.post(
            SCRAPE_ENDPOINT,
            headers=headers,
            json={"url": url, "useBrowser": use_browser, "generateJson": False},
            timeout=max(self.timeout, 90),
        )
        self._raise_for_status(response)
        payload = response.json()
        ANAKIN_CACHE.set(cache_key, payload)
        return {**payload, "_cache_hit": False}


def _agentic_citations(value: Any, found: list[dict[str, str]]) -> None:
    if isinstance(value, dict):
        url = value.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            title = value.get("title") or value.get("name") or url
            citation = {"title": str(title), "url": url}
            if citation not in found:
                found.append(citation)

        for child in value.values():
            _agentic_citations(child, found)
    elif isinstance(value, list):
        for child in value:
            _agentic_citations(child, found)


def normalise_agentic_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose a stable report shape despite Agentic Search's dynamic schema."""
    generated = payload.get("generatedJson") or payload.get("generated_json") or {}
    citations: list[dict[str, str]] = []
    _agentic_citations(generated, citations)

    return {
        "summary": generated.get("summary") if isinstance(generated, dict) else None,
        "structured_data": (
            generated.get("structured_data", {}) if isinstance(generated, dict) else {}
        ),
        "citations": citations,
    }

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
            "cache_hit": bool(payload.get("_cache_hit")),
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
        scraped = False
        page_cache_hit = False

        try:
            page = client.scrape(url)
            page_cache_hit = bool(page.get("_cache_hit"))
            markdown = str(page.get("markdown") or "").strip()
            html = str(page.get("html") or "")

            if markdown:
                content = markdown
                scraped = True
            elif html:
                content = html_to_text(html)
                scraped = bool(content)
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
                "scraped": scraped,
                "cache_hit": bool(result.get("cache_hit")) or page_cache_hit,
            }
        )

    return documents
