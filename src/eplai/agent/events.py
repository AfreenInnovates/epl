"""The event vocabulary the agent emits while it works.

The loop is a generator of these events so that the CLI, the notebook and the
web backend can all render the same progress feed without re-implementing it.
Private model reasoning is never emitted -- only the high-level execution state.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EventType = Literal[
    "start",
    "thinking",
    "tool_call",
    "tool_result",
    "tool_skipped",
    "writing",
    "answer",
    "error",
    "done",
]


@dataclass
class AgentEvent:
    """One step of the agent's visible execution state."""

    type: EventType
    label: str = ""
    detail: str = ""
    tool: str | None = None
    call_id: str | None = None
    iteration: int | None = None
    ok: bool | None = None
    duration_ms: int | None = None
    arguments: dict[str, Any] | None = None
    # A compact, display-ready slice of a tool result. It lets the interface
    # show what the models actually returned, rather than only the subset the
    # language model chose to mention in its prose.
    data: dict[str, Any] | None = None
    answer: dict[str, Any] | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Drop empty fields so the SSE payload stays small."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v not in (None, "")}


def start(query: str) -> AgentEvent:
    return AgentEvent(type="start", label="Received your question", detail=query)


def thinking(iteration: int) -> AgentEvent:
    return AgentEvent(
        type="thinking",
        label="Thinking",
        detail="Deciding what evidence is needed"
        if iteration == 1
        else "Reviewing the evidence so far",
        iteration=iteration,
    )


def writing() -> AgentEvent:
    return AgentEvent(
        type="writing",
        label="Writing answer",
        detail="Synthesising the retrieved evidence",
    )


def done() -> AgentEvent:
    return AgentEvent(type="done", label="Done")


def error(message: str) -> AgentEvent:
    return AgentEvent(type="error", label="Something went wrong", detail=message, ok=False)
