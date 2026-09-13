"""Standalone regression tests for the Anakin web client adapter."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eplai.rag.web import AnakinClient, search_results  # noqa: E402


def test_search_adapter_is_exposed_on_anakin_client() -> None:
    assert callable(getattr(AnakinClient, "search", None))
    assert callable(getattr(AnakinClient, "scrape", None))


def test_search_results_uses_client_search() -> None:
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {
        "results": [
            {
                "title": "Official team news",
                "url": "https://club.example/news",
                "date": "2026-09-13",
                "snippet": "A football update.",
            }
        ]
    }

    with patch("eplai.rag.web.requests.post", return_value=response):
        results = search_results(
            "football tactical update unique regression query",
            client=AnakinClient(api_key="test-key"),
        )

    assert results[0]["url"] == "https://club.example/news"
    assert results[0]["cache_hit"] is False


if __name__ == "__main__":
    test_search_adapter_is_exposed_on_anakin_client()
    test_search_results_uses_client_search()
    print("ok  test_anakin_web_client")
