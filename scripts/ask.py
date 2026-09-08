"""Ask the agent a question from the terminal.

    python scripts/ask.py "Who plays like Bukayo Saka, and why?"
"""

from __future__ import annotations

import sys

import _bootstrap  # noqa: F401

from eplai.cli import main

if __name__ == "__main__":
    sys.exit(main())
