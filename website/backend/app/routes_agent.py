"""The agent endpoints.

``/api/ask/stream`` is the one the website uses: it emits the agent's execution
events over Server-Sent Events so the UI can show what is happening while it
happens, rather than a spinner and a wall of text at the end.
"""

from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from eplai.agent import FootballAgent

from .schemas import AskRequest, AskResponse

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


def _sse(event_name: str, payload: dict) -> str:
    """Format one Server-Sent Event frame."""
    data = json.dumps(payload, ensure_ascii=False)
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
