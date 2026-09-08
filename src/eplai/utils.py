"""Small shared helpers."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def jsonable(value: Any, ndigits: int = 4) -> Any:
    """Coerce a pandas/numpy scalar into something JSON and pydantic accept.

    Values read out of a DataFrame are numpy scalars, which serialise nowhere:
    not to JSON for tool results, not through pydantic for API responses. NaN
    becomes ``None`` rather than the invalid JSON literal ``NaN``.
    """
    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, np.floating):
        value = float(value)

    if isinstance(value, float):
        return None if math.isnan(value) else round(value, ndigits)

    if isinstance(value, np.ndarray):
        return [jsonable(item, ndigits) for item in value.tolist()]

    if value is None or isinstance(value, (str, int, bool)):
        return value

    return str(value)
