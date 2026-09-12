"""Strict JSON input for benchmark configuration and execution receipts."""

import json
import math
from pathlib import Path


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        _invalid_constant(value)
    return number


def decode_json(text, label="JSON"):
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
            parse_float=_finite_float,
        )
    except ValueError as exc:
        raise ValueError(f"Invalid {label}: {exc}") from exc


def read_json(path):
    path = Path(path)
    return decode_json(path.read_text(encoding="utf-8"), str(path))
