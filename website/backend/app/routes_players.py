"""Player lookup endpoints, used by the landing page and the answer cards."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from eplai.data import POSITION_LABELS
from eplai.rag.context import get_player_stats
from eplai.similarity import load_store, similar_players_records

from .schemas import (
    PlayerStatsResponse,
    PlayerSummary,
    SimilarPlayersResponse,
)

router = APIRouter(prefix="/api/players", tags=["players"])


def _resolve_or_404(name: str) -> str:
    store = load_store()
    resolved = store.resolve(name)

    if resolved is None:
        raise HTTPException(status_code=404, detail=f"'{name}' is not in the dataset.")

    return resolved


@router.get("", response_model=list[PlayerSummary])
def list_players(
    q: str | None = Query(default=None, description="Case-insensitive name filter."),
    position: str | None = Query(default=None, description="GKP, DEF, MID or FWD."),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[PlayerSummary]:
    """Search the player population."""
    store = load_store()
    frame = store.metadata

    if position:
        frame = frame[frame["Position"].str.upper() == position.upper()]

    if q:
        needle = q.strip().casefold()
        frame = frame[frame["Player Name"].str.casefold().str.contains(needle, regex=False)]

    return [
        PlayerSummary(
            name=row["Player Name"],
            club=row.get("Club"),
            position=row.get("Position"),
            position_label=POSITION_LABELS.get(str(row.get("Position")), row.get("Position")),
        )
        for row in frame.head(limit).to_dict(orient="records")
    ]


@router.get("/{name}", response_model=PlayerStatsResponse)
def player_detail(name: str) -> PlayerStatsResponse:
    """Headline statistics for one player."""
    resolved = _resolve_or_404(name)

    stats = get_player_stats(resolved)

    if stats is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Player statistics are not available. Run scripts/download_data.py "
                "and scripts/prepare_data.py to populate them."
            ),
        )

    profile = load_store().profile(resolved)

    return PlayerStatsResponse(
        player=resolved,
        club=str(profile.get("Club")),
        position=str(profile.get("Position")),
        position_label=POSITION_LABELS.get(
            str(profile.get("Position")), str(profile.get("Position"))
        ),
        stats={k: v for k, v in stats.items() if k not in ("Player", "Club", "Position")},
    )


@router.get("/{name}/similar", response_model=SimilarPlayersResponse)
def similar_players(
    name: str,
    top_k: int = Query(default=5, ge=1, le=10),
) -> SimilarPlayersResponse:
    """Consensus similarity neighbours, straight from the embeddings."""
    resolved = _resolve_or_404(name)

    return SimilarPlayersResponse(
        query_player=resolved,
        results=similar_players_records(resolved, top_k=top_k),
    )
