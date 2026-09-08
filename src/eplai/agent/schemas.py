"""Tool definitions and the structured-output schema for the final answer."""

from __future__ import annotations

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "ml_player_search",
            "description": (
                "Find Premier League players statistically similar to a "
                "specified player using multiple machine-learning "
                "representations (autoencoder, Siamese and triplet embeddings)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "Player to find similar players for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of similar players to return.",
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["player_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "player_stats_tool",
            "description": (
                "Get structured 2024/25 Premier League statistics for a player, "
                "including per-90 rates. Accepts several players at once."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "A single player name.",
                    },
                    "player_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Several player names to look up in one call. "
                            "Prefer this over repeated single-player calls."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_football_web",
            "description": (
                "Search the web for football news, tactical analysis, player "
                "role information and other relevant football context. Write "
                "one broad query covering everything you need; you may call "
                "this at most twice per question."
            ),
            "parameters": {
                "type": "object",
                # Bounds are deliberately loose. The provider validates tool
                # arguments server-side and rejects the entire request when the
                # model strays outside them, so the result count is clamped
                # inside the tool rather than constrained here.
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["query"],
            },
        },
    },
]

# Human-friendly captions shown while each tool runs.
TOOL_LABELS: dict[str, str] = {
    "ml_player_search": "Searching similar players",
    "player_stats_tool": "Looking up player statistics",
    "search_football_web": "Searching football sources",
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "ml_player_search": "Comparing embedding neighbourhoods across three models",
    "player_stats_tool": "Reading per-90 numbers from the 2024/25 dataset",
    "search_football_web": "Gathering tactical and contextual evidence",
}


FINAL_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "similar_players": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "player": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["player", "reason"],
                "additionalProperties": False,
            },
        },
        "statistical_evidence": {"type": "array", "items": {"type": "string"}},
        "tactical_evidence": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["title", "url"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "title",
        "summary",
        "similar_players",
        "statistical_evidence",
        "tactical_evidence",
        "limitations",
        "sources",
    ],
    "additionalProperties": False,
}


def empty_answer(title: str, summary: str, limitations: list[str] | None = None) -> dict:
    """A schema-shaped answer for failure and fallback paths."""
    return {
        "title": title,
        "summary": summary,
        "similar_players": [],
        "statistical_evidence": [],
        "tactical_evidence": [],
        "limitations": limitations or [],
        "sources": [],
    }
