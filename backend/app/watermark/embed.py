"""
Forensic attribution marker embedding for SIH26237.

Embeds an opaque 256-bit random token into a PDF using two non-rendering layers:
  Layer 1: text drawn with PDF text render mode 3 (neither fill nor stroke) on every page.
  Layer 2: the document metadata keywords field.

The token carries no recipient information. Its meaning comes only from the
recipient-signed decryption record in the ledger. This is a forensic attribution
marker, not an unremovable watermark: rasterizing, retyping, printing/scanning or
re-generating the PDF removes it.
"""

import re
import secrets

import pymupdf

WATERMARK_PREFIX = "::SIH26237_OPAQUE::"
WATERMARK_SUFFIX = "::"
METADATA_KEY = "WESEE_FORENSIC_TOKEN"
TOKEN_RE = re.compile(r"^WM-[0-9a-f]{64}$")


def generate_watermark_token() -> str:
    """Opaque 256-bit token from the OS CSPRNG."""
    return "WM-" + secrets.token_hex(32)


def is_valid_token(token: str) -> bool:
    return isinstance(token, str) and bool(TOKEN_RE.fullmatch(token))


def embed_watermark(pdf_bytes: bytes, wm_token: str) -> bytes:
    """Returns the watermarked PDF bytes."""
    if not is_valid_token(wm_token):
        raise ValueError("Refusing to embed a malformed watermark token")

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        marker_text = f"{WATERMARK_PREFIX}{wm_token}{WATERMARK_SUFFIX}"
        for page in doc:
            rect = page.rect
            point = pymupdf.Point(rect.x0 + 10, rect.y1 - 10)
            page.insert_text(point, marker_text, fontsize=4, render_mode=3)

        existing_meta = doc.metadata or {}
        existing_keywords = existing_meta.get("keywords") or ""
        # Strip any pre-existing marker so a re-processed file never carries two tokens.
        existing_keywords = re.sub(rf"{METADATA_KEY}:[^;\s]*;?\s*", "", existing_keywords).strip("; ")
        new_keywords = f"{METADATA_KEY}:{wm_token}"
        if existing_keywords:
            new_keywords = f"{existing_keywords}; {new_keywords}"

        doc.set_metadata({
            "keywords": new_keywords,
            "producer": "WESEE Offline Provenance Engine",
        })
        return doc.tobytes(garbage=3, deflate=True)
    finally:
        doc.close()
