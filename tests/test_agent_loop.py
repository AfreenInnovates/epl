"""Agent-loop tests that run without an API key.

A stub client stands in for Groq so the loop's control flow -- tool dispatch,
duplicate suppression, the iteration budget and the structured hand-off -- is
verified without network access.

    python -m pytest tests/ -q
    python tests/test_agent_loop.py        (runs without pytest too)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eplai.agent import FootballAgent  # noqa: E402
from eplai.agent.loop import WEB_SEARCH_BUDGET, _recover_synthesis  # noqa: E402


# ----------------------------------------------------------------------
# stub client
# ----------------------------------------------------------------------


@dataclass
class StubFunction:
    name: str
    arguments: str


@dataclass
class StubToolCall:
    id: str
    function: StubFunction


@dataclass
class StubMessage:
    content: str | None = None
    tool_calls: list[StubToolCall] | None = None


@dataclass
class StubChoice:
    message: StubMessage


@dataclass
class StubResponse:
    choices: list[StubChoice]


@dataclass
class StubClient:
    """Replays a scripted sequence of assistant messages."""

    script: list[StubMessage]
    final_answer: dict
    calls: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.chat = self  # mimic client.chat.completions.create
        self.completions = self

    def create(self, **kwargs):
        self.calls.append(kwargs)

        # The synthesis step is the one that asks for a JSON schema.
        if kwargs.get("response_format"):
            return StubResponse(
                [StubChoice(StubMessage(content=json.dumps(self.final_answer)))]
            )

        index = len([c for c in self.calls if not c.get("response_format")]) - 1

        if index < len(self.script):
            return StubResponse([StubChoice(self.script[index])])

        return StubResponse([StubChoice(StubMessage(content="done"))])


ANSWER = {
    "title": "Players comparable to Bukayo Saka",
    "summary": "Three representations broadly agree on a set of wide attackers.",
    "similar_players": [{"player": "Mohammed Kudus", "reason": "Similar carrying volume."}],
    "statistical_evidence": ["Saka: 0.31 goals per 90"],
    "tactical_evidence": [],
    "limitations": ["Statistical similarity is not tactical equivalence."],
    "sources": [],
}


def tool_call(call_id: str, name: str, arguments: dict) -> StubToolCall:
    return StubToolCall(id=call_id, function=StubFunction(name, json.dumps(arguments)))


# ----------------------------------------------------------------------
# tests
# ----------------------------------------------------------------------


def test_tool_call_then_answer() -> None:
    client = StubClient(
        script=[
            StubMessage(
                tool_calls=[tool_call("c1", "ml_player_search", {"player_name": "Bukayo Saka"})]
            ),
            StubMessage(content="I have what I need."),
        ],
        final_answer=ANSWER,
    )

    events = list(FootballAgent(client=client).stream("Who plays like Bukayo Saka?"))
    types = [event.type for event in events]

    assert types[0] == "start"
    assert "thinking" in types
    assert "tool_call" in types
    assert "tool_result" in types
    assert types[-1] == "done"

    call = next(e for e in events if e.type == "tool_call")
    assert call.tool == "ml_player_search"
    assert call.label == "Searching similar players"

    result = next(e for e in events if e.type == "tool_result")
    assert result.ok is True
    assert "comparable players" in result.detail

    answer = next(e for e in events if e.type == "answer")
    assert answer.answer is not None
    assert answer.answer["title"] == ANSWER["title"]


def test_duplicate_tool_calls_are_skipped() -> None:
    duplicate = {"player_name": "Bukayo Saka"}

    client = StubClient(
        script=[
            StubMessage(tool_calls=[tool_call("c1", "ml_player_search", duplicate)]),
            StubMessage(tool_calls=[tool_call("c2", "ml_player_search", duplicate)]),
            StubMessage(content="Done."),
        ],
        final_answer=ANSWER,
    )

    events = list(FootballAgent(client=client).stream("Who plays like Saka?"))

    assert sum(1 for e in events if e.type == "tool_call") == 1
    assert sum(1 for e in events if e.type == "tool_skipped") == 1


def test_iteration_budget_still_answers() -> None:
    """A model that never stops calling tools must still produce an answer."""
    client = StubClient(
        script=[
            StubMessage(
                tool_calls=[
                    tool_call(f"c{i}", "player_stats_tool", {"player_name": f"Player {i}"})
                ]
            )
            for i in range(10)
        ],
        final_answer=ANSWER,
    )

    events = list(FootballAgent(client=client, max_iterations=3).stream("Stats please"))

    answer = next(e for e in events if e.type == "answer")
    assert answer.answer is not None
    assert any("tool-call limit" in limit for limit in answer.answer["limitations"])


def test_web_search_budget_is_enforced() -> None:
    """A model that keeps searching must be cut off, not left to burn tokens."""
    client = StubClient(
        script=[
            StubMessage(
                tool_calls=[
                    tool_call(f"c{i}", "search_football_web", {"query": f"query {i}"})
                ]
            )
            for i in range(5)
        ],
        final_answer=ANSWER,
    )

    events = list(FootballAgent(client=client, max_iterations=6).stream("Tell me about Saka"))

    attempted = [e for e in events if e.type == "tool_call" and e.tool == "search_football_web"]
    refused = [e for e in events if e.type == "tool_skipped"]

    assert len(attempted) == WEB_SEARCH_BUDGET, (
        "web search should stop after the budget is spent"
    )
    assert refused, "the refusal should be visible in the trace"


def test_unknown_player_reports_error_not_crash() -> None:
    client = StubClient(
        script=[
            StubMessage(
                tool_calls=[tool_call("c1", "ml_player_search", {"player_name": "Zinedine Zidane"})]
            ),
            StubMessage(content="Not in the dataset."),
        ],
        final_answer=ANSWER,
    )

    events = list(FootballAgent(client=client).stream("Who plays like Zidane?"))

    result = next(e for e in events if e.type == "tool_result")
    assert result.ok is False
    assert "not in the 2024/25 modelling dataset" in result.detail


def test_model_failure_surfaces_as_event() -> None:
    class ExplodingClient(StubClient):
        def create(self, **kwargs):
            raise RuntimeError("model unavailable")

    events = list(
        FootballAgent(client=ExplodingClient([], ANSWER)).stream("Anything")
    )

    assert any(e.type == "error" for e in events)

    answer = next(e for e in events if e.type == "answer")
    assert answer.answer is not None
    assert "model unavailable" in answer.answer["limitations"][0]


def test_synthesis_carries_no_tool_calls() -> None:
    """The final call must not look like a conversation that is still gathering.

    It is sent without `tools`, which the provider reads as tool_choice=none.
    Leaving assistant `tool_calls` in the history prompts the model to emit one
    anyway, and the request comes back 400 tool_use_failed -- which used to
    kill every run at the last step.
    """
    client = StubClient(
        script=[
            StubMessage(
                tool_calls=[
                    tool_call("c1", "ml_player_search", {"player_name": "Bukayo Saka"})
                ]
            ),
            StubMessage(content="Here is what I found."),
        ],
        final_answer=ANSWER,
    )

    list(FootballAgent(client=client, max_iterations=3).stream("Who plays like Saka?"))

    synthesis = next(call for call in client.calls if call.get("response_format"))

    assert "tools" not in synthesis, "the synthesis call sends no tool definitions"
    assert all(
        "tool_calls" not in message for message in synthesis["messages"]
    ), "no assistant message may still carry tool_calls"
    assert all(
        message["role"] != "tool" for message in synthesis["messages"]
    ), "tool results must be flattened into ordinary messages"

    # The evidence itself has to survive the flattening.
    assert any(
        "ml_player_search" in message["content"] for message in synthesis["messages"]
    )


def test_partial_structured_response_is_recovered() -> None:
    partial = {
        "title": "Players comparable to Mohamed Salah",
        "summary": "Son Heung-Min has the closest profile among the players compared.",
        "similar_players": [
            {"player": "Son Heung-Min", "reason": "Similar wide-attacking profile."}
        ],
    }
    error = RuntimeError(
        "Error code: 400 - "
        + repr({"error": {"failed_generation": json.dumps(partial)}})
    )

    answer = _recover_synthesis(
        [
            {
                "role": "tool",
                "content": json.dumps(
                    {
                        "results": [
                            {
                                "title": "Official player profile",
                                "url": "https://example.com/player",
                            }
                        ]
                    }
                ),
            }
        ],
        error,
    )

    assert answer["title"] == partial["title"]
    assert answer["similar_players"] == partial["similar_players"]
    assert answer["sources"] == [
        {"title": "Official player profile", "url": "https://example.com/player"}
    ]
    assert answer["statistical_evidence"] == []
    assert answer["limitations"]


def test_gathering_stops_once_every_tool_has_answered() -> None:
    """Each extra turn resends the whole conversation, so do not take one for free."""
    client = StubClient(
        script=[
            StubMessage(
                tool_calls=[
                    tool_call("c1", "ml_player_search", {"player_name": "Bukayo Saka"})
                ]
            ),
            StubMessage(
                tool_calls=[
                    tool_call("c2", "player_stats_tool", {"player_name": "Bukayo Saka"})
                ]
            ),
            StubMessage(
                tool_calls=[tool_call("c3", "search_football_web", {"query": "Saka role"})]
            ),
            StubMessage(
                tool_calls=[
                    tool_call("c4", "ml_player_search", {"player_name": "Cole Palmer"})
                ]
            ),
        ],
        final_answer=ANSWER,
    )

    events = list(FootballAgent(client=client, max_iterations=6).stream("Who plays like Saka?"))

    gathering = [call for call in client.calls if not call.get("response_format")]

    assert len(gathering) == 3, "a fourth gathering turn buys nothing"
    assert [e.tool for e in events if e.type == "tool_call"] == [
        "ml_player_search",
        "player_stats_tool",
        "search_football_web",
    ]

    answer = next(e for e in events if e.type == "answer")
    assert answer.answer is not None
    assert not any(
        "tool-call limit" in limitation for limitation in answer.answer["limitations"]
    ), "stopping early is not the same as running out of iterations"


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]

    for test in tests:
        test()
        print(f"ok  {test.__name__}")

    print(f"\n{len(tests)} passed")
