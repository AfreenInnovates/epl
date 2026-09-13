"""The agent endpoints.

``/api/ask/stream`` is the one the website uses: it emits the agent's execution
events over Server-Sent Events so the UI can show what is happening while it
happens, rather than a spinner and a wall of text at the end.
"""

from __future__ import annotations

import json
import math
from typing import Iterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from eplai.agent import FootballAgent
from eplai.agent.tools import search_football_web
from eplai.rag.web import AnakinClient, WebSearchError, normalise_agentic_result

from .schemas import (
    AskRequest,
    AskResponse,
    ResearchRequest,
    WebRefreshRequest,
    WebRefreshResponse,
)

router = APIRouter(prefix="/api", tags=["agent"])

MAX_QUESTION_LENGTH = 500


def _validate(question: str) -> str:
    question = question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="A question is required.")

    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Questions are limited to {MAX_QUESTION_LENGTH} characters.",
        )

    return question


def _sse_safe(value: object) -> object:
    """Convert non-finite numbers before serialising an SSE payload."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _sse_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sse_safe(item) for item in value]
    return value


def _sse(event_name: str, payload: dict) -> str:
    """Format one Server-Sent Event frame."""
    data = json.dumps(_sse_safe(payload), ensure_ascii=False, allow_nan=False)
    return f"event: {event_name}\ndata: {data}\n\n"


@router.get("/ask/stream")
def ask_stream(
    q: str = Query(..., description="The question to ask."),
    max_iterations: int | None = Query(default=None, ge=1, le=12),
) -> StreamingResponse:
    """Stream the agent's progress and its final structured answer."""
    question = _validate(q)

    def generate() -> Iterator[str]:
        agent = FootballAgent(max_iterations=max_iterations)

        try:
            for event in agent.stream(question):
                yield _sse(event.type, event.to_dict())
        except Exception as exc:  # a failure after headers are sent
            yield _sse("error", {"type": "error", "detail": str(exc)})
            yield _sse("done", {"type": "done"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Stops nginx from buffering the stream into a single response.
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Non-streaming variant: run to completion and return answer plus trace."""
    question = _validate(request.question)

    agent = FootballAgent(max_iterations=request.max_iterations)

    trace: list[dict] = []
    answer: dict | None = None

    for event in agent.stream(question):
        if event.type == "answer" and event.answer is not None:
            answer = event.answer
        else:
            trace.append(event.to_dict())

    if answer is None:
        raise HTTPException(status_code=500, detail="The agent produced no answer.")

    return AskResponse(question=question, answer=answer, trace=trace)


@router.post("/web/refresh", response_model=WebRefreshResponse)
def refresh_web(request: WebRefreshRequest) -> WebRefreshResponse:
    """Retry only missing Anakin evidence for a locally cached answer."""
    question = _validate(request.question)
    result = search_football_web(question)

    if result.get("error"):
        status_code = 429 if result.get("rate_limited") else 503
        headers = (
            {"Retry-After": str(result["retry_after"])}
            if result.get("retry_after")
            else None
        )
        raise HTTPException(status_code=status_code, detail=result["error"], headers=headers)

    return WebRefreshResponse(query=question, results=result.get("results", []))


@router.post("/anakin/research")
def submit_anakin_research(request: ResearchRequest) -> dict:
    """Queue Anakin's four-stage research pipeline."""
    question = _validate(request.question)

    try:
        result = AnakinClient().submit_agentic_search(
            f"Produce a football scouting research brief for this question: {question}. "
            "Focus on current tactical role, form, injuries, transfer context, and cite sources."
        )
    except WebSearchError as exc:
        raise HTTPException(
            status_code=429 if exc.retry_after is not None else 503,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else None,
        ) from exc

    return {
        "job_id": result.get("job_id") or result.get("id"),
        "status": result.get("status", "pending"),
        "created_at": result.get("created_at") or result.get("createdAt"),
    }


@router.get("/anakin/research/{job_id}")
def get_anakin_research(job_id: str) -> dict:
    """Poll an Anakin research job; GET polling is not rate limited by Anakin."""
    try:
        result = AnakinClient().get_agentic_search(job_id)
    except WebSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    response = {
        "job_id": result.get("job_id") or result.get("id") or job_id,
        "status": result.get("status", "pending"),
    }

    if result.get("status") == "completed":
        response["report"] = normalise_agentic_result(result)
    elif result.get("status") == "failed":
        response["error"] = result.get("error", "Anakin research failed.")

    return response
