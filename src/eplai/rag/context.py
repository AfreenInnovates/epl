"""Assembling ML, statistical and web evidence into one prompt-ready block."""

from __future__ import annotations

from typing import Any

from ..data import RawDataMissingError, player_knowledge
from ..similarity import retrieve_similar_players
from ..utils import jsonable
from .index import WebIndex


def get_player_stats(player_name: str) -> dict[str, Any] | None:
    """Headline statistics for one player.

    Returns ``None`` when the player is unknown *or* when the season data has
    not been downloaded yet -- callers surface that as a missing-data message
    rather than a crash.
    """
    try:
        knowledge = player_knowledge()
    except RawDataMissingError:
        return None

    match = knowledge[knowledge["Player Name"] == player_name]

    if match.empty:
        return None

    row = match.iloc[0]

    fields = {
        "Player": "Player Name",
        "Club": "Club",
        "Position": "Position",
        "Minutes": "Minutes",
        "Goals": "Goals",
        "Assists": "Assists",
        "Goals_per90": "Goals_per90",
        "Assists_per90": "Assists_per90",
        "Shots_per90": "Shots_per90",
        "Touches_per90": "Touches_per90",
        "Passes_per90": "Passes_per90",
        "Carries_per90": "Carries_per90",
        "Progressive_Carries_per90": "Progressive Carries_per90",
        "Through_Balls_per90": "Through Balls_per90",
        "Crosses_per90": "Crosses_per90",
        "Tackles_per90": "Tackles_per90",
        "Interceptions_per90": "Interceptions_per90",
        "Passes_pct": "Passes%",
        "Conversion_pct": "Conversion %",
    }

    # Coerced here rather than at each call site: numpy scalars serialise
    # neither to JSON for tool results nor through pydantic for API responses.
    return {name: jsonable(row[column]) for name, column in fields.items()}


def build_player_context(
    player_name: str,
    top_players: int = 5,
    top_web: int = 5,
    index: WebIndex | None = None,
) -> dict[str, Any]:
    """Gather every evidence source available for a single player."""
    similar = retrieve_similar_players(player_name, top_k=top_players)

    web_results: list[dict[str, Any]] = []

    if index is not None:
        web_results = index.search_diverse(
            f"{player_name} playing style tactical analysis Premier League",
            top_k=top_web,
        )

    return {
        "query_player": get_player_stats(player_name),
        "similar_players": similar,
        "web_results": web_results,
    }


def format_rag_context(context: dict[str, Any]) -> str:
    """Render the context dictionary as the evidence block sent to the model."""
    player = context.get("query_player")

    if player is None:
        stats_text = "QUERY PLAYER\nNo statistics available for this player.\n"
    else:
        stats_text = f"""
QUERY PLAYER
Player: {player['Player']}
Club: {player['Club']}
Position: {player['Position']}

Goals: {player['Goals']}
Assists: {player['Assists']}
Goals per 90: {player['Goals_per90']:.3f}
Assists per 90: {player['Assists_per90']:.3f}
Shots per 90: {player['Shots_per90']:.3f}
Touches per 90: {player['Touches_per90']:.3f}
Passes per 90: {player['Passes_per90']:.3f}
Carries per 90: {player['Carries_per90']:.3f}
Progressive Carries per 90: {player['Progressive_Carries_per90']:.3f}
Through Balls per 90: {player['Through_Balls_per90']:.3f}
Crosses per 90: {player['Crosses_per90']:.3f}
"""

    similar_text = "\nSIMILAR PLAYERS\n"

    for _, row in context["similar_players"].head(5).iterrows():
        similar_text += (
            f"- {row['Player']} "
            f"(Models retrieved: {row['Models_Retrieved']}, "
            f"Mean rank: {row['Mean_Rank']:.2f})\n"
        )

    web_text = "\nWEB EVIDENCE\n"

    for i, result in enumerate(context["web_results"], start=1):
        web_text += (
            f"\nSOURCE {i}\n"
            f"Title: {result['title']}\n"
            f"URL: {result['url']}\n"
            f"Evidence: {result['text']}\n"
        )

    return stats_text + similar_text + web_text
