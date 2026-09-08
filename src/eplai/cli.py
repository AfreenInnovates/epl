"""Terminal front-end for the agent.

Renders the same event stream the website consumes, so the CLI and the web UI
never disagree about what the agent is doing.

    python -m eplai.cli "Who plays like Bukayo Saka, and why?"
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .agent import FootballAgent

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"

def _widen_stdout() -> None:
    """Switch the console to UTF-8 where possible.

    Player names carry accents and the model writes em dashes; a Windows
    cp1252 console raises UnicodeEncodeError on both. Replacing unencodable
    characters is far better than losing the answer to a traceback.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, OSError, ValueError):
            pass


_widen_stdout()


UNICODE_ICONS = {
    "start": "»",
    "thinking": "*",
    "tool_call": "→",
    "tool_result": "✓",
    "tool_skipped": "↩",
    "writing": "✎",
    "error": "!",
    "done": "•",
}

ASCII_ICONS = {
    "start": ">",
    "thinking": "*",
    "tool_call": "->",
    "tool_result": "OK",
    "tool_skipped": "--",
    "writing": "~",
    "error": "!",
    "done": "*",
}


def _pick_icons() -> dict[str, str]:
    """Prefer the nicer glyphs, but never crash a cp1252 console over them."""
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"

    try:
        "".join(UNICODE_ICONS.values()).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return ASCII_ICONS

    return UNICODE_ICONS


ICONS = _pick_icons()

COLOURS = {
    "thinking": CYAN,
    "tool_call": YELLOW,
    "tool_result": GREEN,
    "tool_skipped": DIM,
    "writing": CYAN,
    "error": RED,
}


def _supports_colour() -> bool:
    return sys.stdout.isatty()


def _paint(text: str, colour: str) -> str:
    return f"{colour}{text}{RESET}" if _supports_colour() else text


def render_event(event: Any) -> None:
    """Print one progress line."""
    if event.type in ("start", "done", "answer"):
        return

    icon = ICONS.get(event.type, "-")
    colour = COLOURS.get(event.type, "")

    line = f"{icon} {event.label}"

    if event.tool and event.type == "tool_call":
        line = f"{icon} {event.label} {_paint('[' + event.tool + ']', DIM)}"

    print(_paint(line, colour))

    if event.detail:
        suffix = ""
        if event.duration_ms is not None:
            suffix = f" ({event.duration_ms} ms)"
        print(_paint(f"   {event.detail}{suffix}", DIM))


def _bullet_section(title: str, items: list[str]) -> None:
    if not items:
        return

    print(f"\n{_paint(title, BOLD)}")
    for item in items:
        print(f"  • {item}")


def display_answer(answer: dict[str, Any]) -> None:
    """Pretty-print the structured response."""
    rule = "=" * 70

    print(f"\n{rule}")
    print(_paint(answer.get("title", "Answer").upper(), BOLD))
    print(rule)

    print(f"\n{answer.get('summary', '')}")

    similar = answer.get("similar_players") or []
    if similar:
        print(f"\n{_paint('SIMILAR PLAYERS', BOLD)}")
        for item in similar:
            print(f"  • {_paint(item['player'], CYAN)}: {item['reason']}")

    _bullet_section("STATISTICAL EVIDENCE", answer.get("statistical_evidence") or [])
    _bullet_section("TACTICAL EVIDENCE", answer.get("tactical_evidence") or [])
    _bullet_section("LIMITATIONS", answer.get("limitations") or [])

    sources = answer.get("sources") or []
    if sources:
        print(f"\n{_paint('SOURCES', BOLD)}")
        for source in sources:
            print(f"  • {source['title']}")
            print(_paint(f"    {source['url']}", DIM))

    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the Premier League agent a question.")
    parser.add_argument("question", nargs="+", help="The question to ask.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead.")
    parser.add_argument("--max-iterations", type=int, default=None)

    args = parser.parse_args(argv)
    question = " ".join(args.question)

    agent = FootballAgent(max_iterations=args.max_iterations)
    answer: dict[str, Any] = {}

    for event in agent.stream(question):
        if event.type == "answer" and event.answer is not None:
            answer = event.answer
        elif not args.json:
            render_event(event)

    if args.json:
        print(json.dumps(answer, indent=2, ensure_ascii=False))
    else:
        display_answer(answer)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
