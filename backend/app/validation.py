"""
Shared input validation rules for SIH26237.
Identifiers are used in file names, HKDF info strings and AAD, so they are
restricted to a strict character set with no path separators or delimiters.
"""

import re

ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
_ID_RE = re.compile(ID_PATTERN)
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

CLASSIFICATIONS = ("RESTRICTED", "CONFIDENTIAL", "SECRET", "TOP SECRET")


def is_valid_id(value: str) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value)) and ".." not in value


def is_hex64(value: str) -> bool:
    return isinstance(value, str) and bool(HEX64_RE.fullmatch(value))
