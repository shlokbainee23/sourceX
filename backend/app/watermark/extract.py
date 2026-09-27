"""
Forensic attribution marker extractor for SIH26237.

Collects every marker occurrence from the invisible text layer of every page and
from the metadata layer, validates each against the strict token format, and
returns a single token only when all occurrences agree. Malformed or conflicting
markers are reported, never "best-effort" accepted.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

import pymupdf

from app.watermark.embed import WATERMARK_PREFIX, WATERMARK_SUFFIX, METADATA_KEY, is_valid_token

_TEXT_MARKER_RE = re.compile(re.escape(WATERMARK_PREFIX) + r"(\S*?)" + re.escape(WATERMARK_SUFFIX))
_META_MARKER_RE = re.compile(re.escape(METADATA_KEY) + r":([^;\s]*)")

FOUND = "FOUND"
NOT_FOUND = "NOT_FOUND"
MALFORMED = "MALFORMED"
CONFLICT = "CONFLICT"
UNREADABLE = "UNREADABLE"


@dataclass
class ExtractionResult:
    status: str
    token: Optional[str] = None
    candidates: List[str] = field(default_factory=list)
    reason: str = ""


def extract_watermark_detailed(pdf_bytes: bytes) -> ExtractionResult:
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return ExtractionResult(UNREADABLE, reason="File is not a readable PDF document")

    try:
        candidates: List[str] = []
        for page in doc:
            candidates.extend(_TEXT_MARKER_RE.findall(page.get_text()))
        keywords = (doc.metadata or {}).get("keywords") or ""
        candidates.extend(_META_MARKER_RE.findall(keywords))
    except Exception:
        return ExtractionResult(UNREADABLE, reason="PDF content could not be parsed")
    finally:
        doc.close()

    if not candidates:
        return ExtractionResult(NOT_FOUND, reason="No forensic attribution marker present in the document")

    malformed = [c for c in candidates if not is_valid_token(c)]
    if malformed:
        return ExtractionResult(MALFORMED, candidates=candidates,
                                reason="Forensic marker present but does not match the required token format")

    distinct = set(candidates)
    if len(distinct) > 1:
        return ExtractionResult(CONFLICT, candidates=sorted(distinct),
                                reason="Multiple different forensic markers found; attribution is ambiguous")

    return ExtractionResult(FOUND, token=candidates[0], candidates=candidates)


def extract_watermark(pdf_bytes: bytes) -> Optional[str]:
    """Returns the token only when exactly one valid, consistent marker is present."""
    result = extract_watermark_detailed(pdf_bytes)
    return result.token if result.status == FOUND else None
