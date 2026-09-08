"""FastAPI application for the Premier League intelligence website.

    uvicorn app.main:app --reload --port 8000     (from website/backend)
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import bootstrap  # noqa: F401  -- puts src/ on sys.path

from eplai.config import PLAYER_KNOWLEDGE_CSV, RAW_STATS_CSV, settings
from eplai.similarity import load_store

from .routes_agent import router as agent_router
from .routes_players import router as players_router
from .schemas import HealthResponse

# Deliberately scoped to what the embeddings and the per-90 table can actually
# answer. Questions about wages, transfer fees or age push the assistant into
# scraping the web for the decisive half of the answer, which is not what this
# project is for.
SUGGESTED_QUESTIONS = [
    "Who plays like Bukayo Saka, and why?",
    "Which defenders are most similar to Virgil van Dijk?",
    "Do all three models agree on who resembles Cole Palmer?",
    "Compare Bukayo Saka and Mohamed Salah on the ball",
    "What are Bukayo Saka's goals, assists, shots and carries per 90?",
    "Which players have the closest statistical profile to Declan Rice?",
]

app = FastAPI(
    title="Premier League Intelligence API",
    description=(
        "Player similarity from three learned embeddings, 2024/25 season "
        "statistics, and a tool-calling agent that combines them with web evidence."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(players_router)
app.include_router(agent_router)


@app.on_event("startup")
def warm_caches() -> None:
    """Load embeddings once at boot so the first question is not slow."""
    try:
        store = load_store()
        print(f"Loaded {len(store.metadata)} players, models: {list(store.similarity)}")
    except Exception as exc:
        print(f"Warning: could not load embeddings at startup: {exc}")


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """What is configured and what is missing."""
    try:
        store = load_store()
        players = len(store.metadata)
        models = list(store.similarity)
    except Exception:
        players = 0
        models = []

    return HealthResponse(
        status="ok" if players else "degraded",
        players=players,
        models=models,
        groq_configured=bool(settings.groq_api_key),
        web_search_configured=bool(settings.anakin_api_key),
        stats_available=PLAYER_KNOWLEDGE_CSV.exists() or RAW_STATS_CSV.exists(),
    )


@app.get("/api/suggestions", tags=["meta"])
def suggestions() -> dict[str, list[str]]:
    """Starter questions shown on the landing page."""
    return {"questions": SUGGESTED_QUESTIONS}
