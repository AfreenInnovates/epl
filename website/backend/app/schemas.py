"""Response models for the public API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    players: int
    models: list[str]
    groq_configured: bool
    web_search_configured: bool
    stats_available: bool


class PlayerSummary(BaseModel):
    name: str
    club: str | None = None
    position: str | None = None
    position_label: str | None = None


class SimilarPlayer(BaseModel):
    player: str
    club: str | None = None
    position: str | None = None
    models_retrieved: int
    mean_rank: float
    best_rank: int
    mean_similarity: float


class SimilarPlayersResponse(BaseModel):
    query_player: str
    results: list[SimilarPlayer]


class PlayerStatsResponse(BaseModel):
    player: str
    club: str | None = None
    position: str | None = None
    position_label: str | None = None
    stats: dict[str, Any]


class AnswerSource(BaseModel):
    title: str
    url: str


class AnswerSimilarPlayer(BaseModel):
    player: str
    reason: str


class Answer(BaseModel):
    title: str
    summary: str
    similar_players: list[AnswerSimilarPlayer] = Field(default_factory=list)
    statistical_evidence: list[str] = Field(default_factory=list)
    tactical_evidence: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    sources: list[AnswerSource] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str
    max_iterations: int | None = None


class AskResponse(BaseModel):
    question: str
    answer: Answer
    trace: list[dict[str, Any]]


class WebRefreshRequest(BaseModel):
    question: str


class WebRefreshResponse(BaseModel):
    query: str
    results: list[dict[str, Any]] = Field(default_factory=list)


class ResearchRequest(BaseModel):
    question: str
