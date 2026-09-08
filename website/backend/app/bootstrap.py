"""Make the ``eplai`` package importable when running from a source checkout.

Installing the project (``pip install -e .``) makes this a no-op, but running
``uvicorn`` straight from the repo should work too.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "src"

if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
