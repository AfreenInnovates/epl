"""The tool-calling agent loop.

``FootballAgent.stream`` yields :class:`AgentEvent` objects as the run
progresses and finishes with an ``answer`` event carrying a response that
conforms to :data:`FINAL_RESPONSE_SCHEMA`.
"""

from __future__ import annotations

import json
import time
import ast
from typing import Any, Iterator

from ..config import settings
from . import events
from .events import AgentEvent
from .prompts import FINAL_ANSWER_PROMPT, SYSTEM_PROMPT
from .schemas import (
    FINAL_RESPONSE_SCHEMA,
    TOOL_DESCRIPTIONS,
    TOOL_LABELS,
    TOOL_SPECS,
    empty_answer,
)
from .tools import execute_tool, result_highlights, summarise_result


# Hosted models meter tokens per minute, and the whole conversation is resent
# on every turn -- so evidence gathered early is paid for again on every later
# call. These caps keep a run inside a small budget without changing what the
# agent is able to conclude.
#
# The free Groq tier allows 8,000 tokens a minute on this model. A run that
# made two web searches over eight iterations cost roughly 22,000, so every
# question ended in a 429 partway through and the interface sat on "Writing
# answer" while the SDK backed off. One search is enough for the tactical half
# of an answer; the second was, in every trace we looked at, a rephrasing of
# the first.
WEB_SEARCH_BUDGET = 1
MAX_TOOL_RESULT_CHARS = 2200

# While gathering evidence the model only has to emit a tool call, so it does
# not need the budget the written answer needs. This is a completion cap, and
# completions are metered too.
GATHERING_COMPLETION_TOKENS = 700

# Once each of these has contributed, there is nothing further to gather.
GATHERING_TOOLS = frozenset(
    {"ml_player_search", "player_stats_tool", "search_football_web"}
)


def _trim_tool_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shorten oversized tool results before resending the conversation."""
    trimmed: list[dict[str, Any]] = []

    for message in messages:
        content = message.get("content")

        if (
            message.get("role") == "tool"
            and isinstance(content, str)
            and len(content) > MAX_TOOL_RESULT_CHARS
        ):
            message = {
                **message,
                "content": content[:MAX_TOOL_RESULT_CHARS] + " …[truncated]",
            }

        trimmed.append(message)

    return trimmed


def _synthesis_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rebuild the conversation with the tool-call machinery flattened out.

    The synthesis call sends no ``tools``, because the model is being asked to
    write rather than to gather. But the history still contains assistant
    messages carrying ``tool_calls``, and gpt-oss reads those as a cue to emit
    another one -- which the provider then rejects, because a request without
    tools implies ``tool_choice: none``::

        400 tool_use_failed: Tool choice is none, but model called a tool

    That killed every run at the last step. Turning each tool result into an
    ordinary message keeps all of the evidence and removes the cue.
    """
    flattened: list[dict[str, Any]] = []

    for message in messages:
        role = message.get("role")
        content = str(message.get("content") or "")

        if role == "tool":
            name = message.get("name") or "a tool"
            flattened.append(
                {"role": "user", "content": f"Result from {name}:\n{content}"}
            )
        elif role == "assistant" and not content.strip():
            # A bare tool call: the result it produced is kept above.
            continue
        else:
            flattened.append({"role": role, "content": content})

    return flattened


def _failed_generation(exc: Exception) -> dict[str, Any] | None:
    """Recover a provider's partial JSON when strict validation rejects it."""
    body = getattr(exc, "body", None)
    generation: Any = None

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            generation = error.get("failed_generation")

    if generation is None:
        text = str(exc)
        try:
            raw_body = text.split(" - ", 1)[1]
            parsed_body = ast.literal_eval(raw_body)
            error = parsed_body.get("error", {})
            if isinstance(error, dict):
                generation = error.get("failed_generation")
        except (IndexError, SyntaxError, ValueError, TypeError):
            return None

    if not isinstance(generation, str):
        return None

    try:
        parsed = json.loads(generation)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def _tool_sources(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract source records already returned by the web tool."""
    sources: list[dict[str, str]] = []
    seen: set[str] = set()

    for message in messages:
        if message.get("role") != "tool":
            continue

        try:
            payload = json.loads(str(message.get("content") or "{}"))
        except json.JSONDecodeError:
            continue

        for result in payload.get("results", []):
            if not isinstance(result, dict):
                continue

            url = result.get("url")
            if not isinstance(url, str) or not url or url in seen:
                continue

            seen.add(url)
            sources.append({"title": str(result.get("title") or url), "url": url})

    return sources


def _recover_synthesis(
    messages: list[dict[str, Any]], exc: Exception
) -> dict[str, Any]:
    """Return a transparent answer instead of dropping a partial dossier."""
    partial = _failed_generation(exc)

    if partial is None:
        return empty_answer(
            "Answer could not be formatted",
            str(exc)[:800] or "The model returned an unreadable response.",
            ["The structured-output step failed to produce valid JSON."],
        )

    answer = empty_answer(
        str(partial.get("title") or "Answer from available evidence"),
        str(partial.get("summary") or "The model returned a partial answer."),
    )

    for key in (
        "similar_players",
        "statistical_evidence",
        "tactical_evidence",
        "limitations",
    ):
        value = partial.get(key)
        if isinstance(value, list):
            answer[key] = value

    answer["sources"] = (
        partial.get("sources")
        if isinstance(partial.get("sources"), list)
        else _tool_sources(messages)
    )

    missing = [
        key
        for key in (
            "statistical_evidence",
            "tactical_evidence",
            "limitations",
            "sources",
        )
        if key not in partial
    ]
    if missing:
        answer["limitations"].append(
            "The provider returned a partial structured response; omitted sections "
            f"were retained as empty or recovered from tool results: {', '.join(missing)}."
        )

    return answer


def _explain(exc: Exception) -> str:
    """Turn a provider exception into something a reader can act on."""
    text = str(exc)

    if "rate_limit" in text or "429" in text or "413" in text:
        return (
            "The language model provider rejected the request for exceeding its "
            "rate limit. Wait a minute and ask again, or raise the limit on your "
            "provider account."
        )

    if "authentication" in text.lower() or "401" in text or "invalid_api_key" in text:
        return "The model provider rejected the API key. Check GROQ_API_KEY in your .env file."

    if "timeout" in text.lower() or "timed out" in text.lower():
        return (
            "The language model did not respond within "
            f"{settings.groq_timeout:.0f} seconds. Ask again, or raise "
            "GROQ_TIMEOUT in your .env file."
        )

    return text


def _message_to_dict(message: Any) -> dict[str, Any]:
    """Normalise a Groq/OpenAI message object into a plain dict."""
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or "",
    }

    if getattr(message, "tool_calls", None):
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]

    return payload


class FootballAgent:
    """Runs the evidence-gathering loop and the structured synthesis step."""

    def __init__(
        self,
        client: Any | None = None,
        model: str | None = None,
        max_iterations: int | None = None,
    ) -> None:
        self._client = client
        self.model = model or settings.groq_model
        self.max_iterations = max_iterations or settings.max_agent_iterations

    @property
    def client(self) -> Any:
        if self._client is None:
            from groq import Groq

            self._client = Groq(
                api_key=settings.require_groq_key(),
                timeout=settings.groq_timeout,
                max_retries=settings.groq_max_retries,
            )

        return self._client

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def stream(self, user_query: str) -> Iterator[AgentEvent]:
        """Run the agent, yielding progress events as they happen."""
        try:
            yield from self._stream(user_query)
        except Exception as exc:  # surface failures as events, never as tracebacks
            message = _explain(exc)

            yield events.error(message)
            yield AgentEvent(
                type="answer",
                answer=empty_answer(
                    "The assistant could not complete this question",
                    message,
                    [str(exc)],
                ),
            )
            yield events.done()

    def run(self, user_query: str) -> dict[str, Any]:
        """Run to completion and return only the final structured answer."""
        answer = empty_answer(
            "No answer produced",
            "The agent finished without returning an answer.",
        )

        for event in self.stream(user_query):
            if event.type == "answer" and event.answer is not None:
                answer = event.answer

        return answer

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _stream(self, user_query: str) -> Iterator[AgentEvent]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ]

        yield events.start(user_query)

        executed_calls: set[tuple[str, str]] = set()
        used_tools: set[str] = set()
        budget = {"search_football_web": WEB_SEARCH_BUDGET}

        exhausted_iterations = True

        for iteration in range(1, self.max_iterations + 1):
            yield events.thinking(iteration)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=_trim_tool_messages(messages),
                tools=TOOL_SPECS,
                temperature=settings.temperature,
                max_completion_tokens=min(
                    GATHERING_COMPLETION_TOKENS, settings.max_completion_tokens
                ),
            )

            message = response.choices[0].message
            messages.append(_message_to_dict(message))

            if not message.tool_calls:
                yield events.writing()
                yield AgentEvent(type="answer", answer=self._synthesise(messages))
                yield events.done()
                return

            for tool_call in message.tool_calls:
                yield from self._run_tool_call(
                    tool_call, messages, executed_calls, used_tools, budget, iteration
                )

            # Every tool has now contributed what it can, and the next turn
            # would resend the whole conversation only to be told to stop. Go
            # straight to the answer instead: it is a round trip cheaper, and
            # on a metered account that round trip is the one that tips a run
            # over the per-minute limit.
            if GATHERING_TOOLS <= used_tools:
                exhausted_iterations = False
                break

        yield events.writing()

        answer = self._synthesise(messages)

        if exhausted_iterations:
            answer.setdefault("limitations", []).append(
                "The assistant reached its tool-call limit, so the evidence may be "
                "incomplete."
            )

        yield AgentEvent(type="answer", answer=answer)
        yield events.done()

    def _run_tool_call(
        self,
        tool_call: Any,
        messages: list[dict[str, Any]],
        executed_calls: set[tuple[str, str]],
        used_tools: set[str],
        budget: dict[str, int],
        iteration: int,
    ) -> Iterator[AgentEvent]:
        tool_name = tool_call.function.name

        try:
            arguments = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            arguments = {}

        if budget.get(tool_name, 1) <= 0:
            yield AgentEvent(
                type="tool_skipped",
                label="Search budget reached",
                detail="Answering from the evidence already gathered",
                tool=tool_name,
                call_id=tool_call.id,
                iteration=iteration,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(
                        {
                            "note": "Search budget for this question is spent. "
                            "Write the final answer from the evidence you have."
                        }
                    ),
                }
            )
            return

        call_key = (tool_name, json.dumps(arguments, sort_keys=True))

        if call_key in executed_calls:
            yield AgentEvent(
                type="tool_skipped",
                label="Skipped repeat call to " + tool_name,
                detail="This exact query was already answered",
                tool=tool_name,
                call_id=tool_call.id,
                iteration=iteration,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(
                        {
                            "note": "Duplicate call skipped. Reuse the earlier "
                            "result for these arguments."
                        }
                    ),
                }
            )
            return

        executed_calls.add(call_key)
        used_tools.add(tool_name)

        if tool_name in budget:
            budget[tool_name] -= 1

        yield AgentEvent(
            type="tool_call",
            label=TOOL_LABELS.get(tool_name, "Calling " + tool_name),
            detail=TOOL_DESCRIPTIONS.get(tool_name, ""),
            tool=tool_name,
            call_id=tool_call.id,
            iteration=iteration,
            arguments=arguments,
        )

        started = time.perf_counter()
        result = execute_tool(tool_name, arguments)
        duration_ms = int((time.perf_counter() - started) * 1000)

        failed = isinstance(result, dict) and bool(result.get("error"))

        yield AgentEvent(
            type="tool_result",
            label=TOOL_LABELS.get(tool_name, tool_name),
            detail=summarise_result(tool_name, result),
            tool=tool_name,
            call_id=tool_call.id,
            iteration=iteration,
            ok=not failed,
            duration_ms=duration_ms,
            data=result_highlights(tool_name, result),
        )

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )

    def _synthesise(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Ask the model for the final answer in the structured schema."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=_synthesis_messages(_trim_tool_messages(messages))
                + [{"role": "system", "content": FINAL_ANSWER_PROMPT}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "football_intelligence_response",
                        "strict": True,
                        "schema": FINAL_RESPONSE_SCHEMA,
                    },
                },
                temperature=settings.temperature,
                max_completion_tokens=settings.max_completion_tokens,
            )
        except Exception as exc:
            return _recover_synthesis(messages, exc)

        content = response.choices[0].message.content or "{}"

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return empty_answer(
                "Answer could not be formatted",
                content[:800] or "The model returned an unreadable response.",
                ["The structured-output step failed to produce valid JSON."],
            )


def run_agent(user_query: str, max_iterations: int | None = None) -> dict[str, Any]:
    """Convenience wrapper mirroring the notebook's ``run_agent``."""
    return FootballAgent(max_iterations=max_iterations).run(user_query)


def stream_agent(
    user_query: str, max_iterations: int | None = None
) -> Iterator[AgentEvent]:
    """Convenience wrapper for the streaming form."""
    return FootballAgent(max_iterations=max_iterations).stream(user_query)
