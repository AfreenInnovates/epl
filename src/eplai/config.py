"""Central configuration and filesystem paths for the EPL intelligence project."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional, only needed for local development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"

RAW_STATS_CSV = RAW_DATA_DIR / "epl_player_stats_24_25.csv"
PLAYER_KNOWLEDGE_CSV = PROCESSED_DATA_DIR / "player_knowledge.csv"
PLAYER_CLUSTERS_CSV = PROCESSED_DATA_DIR / "player_clusters.csv"
WEB_INDEX_DIR = PROCESSED_DATA_DIR / "web_index"
OFFICIAL_CORPUS_PATH = PROCESSED_DATA_DIR / "official_corpus.jsonl"

KAGGLE_DATASET = "aesika/english-premier-league-player-stats-2425"

# Players below this many minutes are excluded from the modelling population,
# because per-90 rates computed from tiny samples are unstable.
MIN_MINUTES = 450


@dataclass(frozen=True)
class Settings:
    """Runtime settings resolved from the environment."""

    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    anakin_api_key: str | None = os.getenv("ANAKIN_API_KEY")
    anakin_cache_ttl_seconds: int = int(os.getenv("ANAKIN_CACHE_TTL_SECONDS", "300"))
    anakin_cache_max_entries: int = int(os.getenv("ANAKIN_CACHE_MAX_ENTRIES", "128"))
    anakin_rate_limit_requests: int = int(os.getenv("ANAKIN_RATE_LIMIT_REQUESTS", "8"))
    anakin_rate_limit_window_seconds: int = int(
        os.getenv("ANAKIN_RATE_LIMIT_WINDOW_SECONDS", "60")
    )

    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Every iteration resends the whole conversation, so the last ones are the
    # most expensive and the least informative. Five is enough for similarity,
    # statistics, one web search and a spare turn.
    max_agent_iterations: int = int(os.getenv("MAX_AGENT_ITERATIONS", "5"))
    temperature: float = float(os.getenv("AGENT_TEMPERATURE", "0.2"))
    max_completion_tokens: int = int(os.getenv("MAX_COMPLETION_TOKENS", "1600"))

    # The SDK's own default is minutes long. A run that stalls there shows the
    # visitor a "Thinking" line and nothing else, so fail fast and say so.
    groq_timeout: float = float(os.getenv("GROQ_TIMEOUT", "45"))
    groq_max_retries: int = int(os.getenv("GROQ_MAX_RETRIES", "1"))

    cors_origins: str = os.getenv(
        "CORS_ORIGINS",
        ",".join(
            [
                "http://localhost:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
            ]
        ),
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def require_groq_key(self) -> str:
        if not self.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        return self.groq_api_key


settings = Settings()
