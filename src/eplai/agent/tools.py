"""Executable implementations behind the agent's tool specifications.

Every tool returns a JSON-serialisable object and never raises: a failed tool
should give the model something to reason about, not abort the run.
"""

from __future__ import annotations

from typing import Any

from ..rag.context import get_player_stats
from ..rag.corpus import OfficialCorpus
from ..rag.web import AnakinClient, WebSearchError, scrape_documents, search_results
from ..similarity import load_store, similar_players_records
from ..utils import jsonable


def _resolve(player_name: str) -> tuple[str | None, list[str]]:
    """Resolve a name to its canonical form, with suggestions on failure."""
    store = load_store()

    resolved = store.resolve(player_name)

    if resolved is not None:
        return resolved, []

    query = player_name.strip().casefold()
    suggestions = [name for name in store.player_names if query in name.casefold()][:5]

    if not suggestions:
        # Offer players sharing any token with the query.
        tokens = set(query.split())
        suggestions = [
            name
            for name in store.player_names
            if tokens & set(name.casefold().split())
        ][:5]

    return None, suggestions


def ml_player_search(player_name: str, top_k: int = 5) -> dict[str, Any]:
    """Consensus similarity search across the three embedding models."""
    top_k = max(1, min(int(top_k or 5), 10))

    resolved, suggestions = _resolve(player_name)

    if resolved is None:
        return {
            "error": f"'{player_name}' is not in the 2024/25 modelling dataset.",
            "note": "The dataset only covers players with at least 450 minutes.",
            "suggestions": suggestions,
        }

    # Each model contributes top_k names, so the consensus table can hold up to
    # 3 * top_k rows. Return only the requested number: the tail is by
    # definition the names the models agreed on least, and it is pure context
    # cost for the model reading this.
    records = similar_players_records(resolved, top_k=top_k)[:top_k]

    return {
        "query_player": resolved,
        "method": "consensus across autoencoder, Siamese and triplet embeddings",
        "results": records,
    }


def player_stats_tool(
    player_name: str | None = None,
    player_names: list[str] | None = None,
) -> dict[str, Any]:
    """Structured statistics for one or several players."""
    names = list(player_names or [])

    if player_name:
        names.insert(0, player_name)

    if not names:
        return {"error": "Provide player_name or player_names."}

    players: list[dict[str, Any]] = []
    not_found: list[dict[str, Any]] = []

    seen: set[str] = set()

    for name in names:
        resolved, suggestions = _resolve(name)

        if resolved is None:
            not_found.append({"requested": name, "suggestions": suggestions})
            continue

        if resolved in seen:
            continue

        seen.add(resolved)

        stats = get_player_stats(resolved)

        if stats is None:
            not_found.append(
                {
                    "requested": name,
                    "suggestions": [],
                    "reason": "Player is in the embedding set but has no statistics row.",
                }
            )
            continue

        players.append({key: jsonable(value) for key, value in stats.items()})

    result: dict[str, Any] = {"players": players}

    if not_found:
        result["not_found"] = not_found

    if not players:
        result["error"] = "No requested player was found in the dataset."

    return result


# Search snippets are the largest thing that enters the conversation. Left
# whole, three searches were enough to exceed an 8k tokens-per-minute budget
# before the answer could be written.
MAX_SNIPPET_CHARS = 320
MAX_EXCERPT_CHARS = 520


def _truncate(text: Any, limit: int = MAX_SNIPPET_CHARS) -> str:
    text = str(text or "").strip()

    if len(text) <= limit:
        return text

    return text[:limit].rsplit(" ", 1)[0] + "…"


MAX_WEB_RESULTS = 3


def search_football_web(query: str, limit: int = 3) -> dict[str, Any]:
    """Web search for tactical and contextual evidence."""
    limit = max(1, min(int(limit or 3), MAX_WEB_RESULTS))
    official_results = OfficialCorpus().search(query, top_k=min(2, limit))

    try:
        client = AnakinClient()
        results = search_results(query, limit=limit, client=client)
    except WebSearchError as exc:
        if official_results:
            return {
                "query": query,
                "results": official_results,
                "anakin_error": str(exc),
                "rate_limited": exc.retry_after is not None,
                "retry_after": exc.retry_after,
            }

        return {
            "error": str(exc),
            "results": [],
            "rate_limited": exc.retry_after is not None,
            "retry_after": exc.retry_after,
        }
    except Exception as exc:  # provider/network failure
        return {"error": f"Web search failed: {exc}", "results": []}

    try:
        documents = scrape_documents(results[:limit], client=client, min_words=40)
    except Exception:
        documents = []

    documents_by_url = {document.get("url"): document for document in documents}
    combined_results = official_results + results
    seen_urls: set[str] = set()
    trimmed: list[dict[str, Any]] = []

    for result in combined_results:
        url = result.get("url")
        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        document = documents_by_url.get(url, {})
        trimmed.append(
            {
                "title": result.get("title"),
                "url": url,
                "date": result.get("date"),
                "snippet": _truncate(result.get("snippet")),
                "excerpt": _truncate(
                    document.get("content") or result.get("excerpt"),
                    limit=MAX_EXCERPT_CHARS,
                ),
                "scraped": bool(result.get("scraped")) or bool(document.get("scraped")),
                "cache_hit": bool(result.get("cache_hit"))
                or bool(document.get("cache_hit")),
                "official": bool(result.get("official")),
            }
        )

    return {"query": query, "results": trimmed[:limit], "official_count": len(official_results)}


TOOL_FUNCTIONS = {
    "ml_player_search": ml_player_search,
    "player_stats_tool": player_stats_tool,
    "search_football_web": search_football_web,
}


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Dispatch a tool call, converting unexpected failures into error payloads."""
    func = TOOL_FUNCTIONS.get(tool_name)

    if func is None:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        if tool_name == "ml_player_search":
            return func(
                player_name=arguments["player_name"],
                top_k=int(arguments.get("top_k", 5)),
            )

        if tool_name == "player_stats_tool":
            return func(
                player_name=arguments.get("player_name"),
                player_names=arguments.get("player_names"),
            )

        return func(
            query=arguments["query"],
            limit=int(arguments.get("limit", 5)),
        )

    except KeyError as exc:
        return {"error": f"Missing required argument: {exc}"}
    except Exception as exc:
        return {"error": f"{tool_name} failed: {exc}"}


def result_highlights(tool_name: str, result: Any) -> dict[str, Any] | None:
    """A small display-ready slice of a tool result, for the interface.

    The language model decides what to write about; this is what the tools
    actually returned. Showing both means a reader can see that ten candidates
    were considered even when the answer discusses one.
    """
    if not isinstance(result, dict) or result.get("error"):
        return None

    if tool_name == "ml_player_search":
        return {
            "query_player": result.get("query_player"),
            "candidates": [
                {
                    "player": row.get("player"),
                    "club": row.get("club"),
                    "position": row.get("position"),
                    "models_retrieved": row.get("models_retrieved"),
                    "mean_similarity": row.get("mean_similarity"),
                }
                for row in result.get("results", [])
            ],
        }

    if tool_name == "player_stats_tool":
        return {
            "players": [player.get("Player") for player in result.get("players", [])]
        }

    if tool_name == "search_football_web":
        return {
            "sources": [
                {
                    "title": row.get("title"),
                    "url": row.get("url"),
                    "excerpt": row.get("excerpt"),
                    "scraped": row.get("scraped", False),
                    "cache_hit": row.get("cache_hit", False),
                    "official": row.get("official", False),
                }
                for row in result.get("results", [])
            ],
            "anakin_error": result.get("anakin_error"),
        }

    return None


def summarise_result(tool_name: str, result: Any) -> str:
    """A one-line description of a tool result, for the live progress feed."""
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"])

    if tool_name == "ml_player_search":
        count = len(result.get("results", [])) if isinstance(result, dict) else 0
        return f"Found {count} comparable players"

    if tool_name == "player_stats_tool":
        players = result.get("players", []) if isinstance(result, dict) else []
        if len(players) == 1:
            return f"Retrieved statistics for {players[0].get('Player')}"
        return f"Retrieved statistics for {len(players)} players"

    if tool_name == "search_football_web":
        count = len(result.get("results", [])) if isinstance(result, dict) else 0
        scraped = (
            sum(1 for row in result.get("results", []) if row.get("scraped"))
            if isinstance(result, dict)
            else 0
        )
        cached = (
            sum(1 for row in result.get("results", []) if row.get("cache_hit"))
            if isinstance(result, dict)
            else 0
        )
        official = (
            sum(1 for row in result.get("results", []) if row.get("official"))
            if isinstance(result, dict)
            else 0
        )
        suffix = f" ({cached} reused from cache)" if cached else ""
        official_suffix = f", including {official} official corpus" if official else ""
        return f"Retrieved {count} web sources and scraped {scraped} pages{official_suffix}{suffix}"

    return "Completed"
