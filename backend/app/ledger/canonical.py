"""
Deterministic JSON canonicalization for SIH26237.

Records are restricted to strings, integers, booleans, null, lists and objects with
string keys. Floats are rejected because their serialization is where JSON
canonicalization schemes (e.g. RFC 8785) diverge between runtimes. Within this
subset, sorted keys + compact separators + UTF-8 gives a stable byte sequence.
Keys are sorted by Python code point order, which equals RFC 8785's UTF-16 order
for the ASCII keys used by this project.
"""

import json
from typing import Any, Dict


class CanonicalizationError(ValueError):
    pass


def _check(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise CanonicalizationError(f"Float values are not permitted in canonical records ({path})")
    if isinstance(value, list):
        for i, item in enumerate(value):
            _check(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalizationError(f"Non-string key at {path}")
            _check(v, f"{path}.{k}")
        return
    raise CanonicalizationError(f"Unsupported type {type(value).__name__} at {path}")


def canonicalize_json(record: Dict[str, Any]) -> bytes:
    """Serialize a record into its canonical UTF-8 byte string."""
    if not isinstance(record, dict):
        raise CanonicalizationError("Canonical record must be a JSON object")
    _check(record)
    return json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
