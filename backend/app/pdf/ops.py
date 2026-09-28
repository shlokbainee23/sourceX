"""
PDF operations executed inside the isolated worker process (app.pdf.worker).

These functions receive only PDF bytes and opaque marker tokens; no key material,
database handles or file paths ever reach this module. Every function returns plain
data (dicts of str/int/bytes) so results cross the process boundary safely.
"""

import hashlib
import re
from typing import Any, Dict, List

import pymupdf

from app.watermark.embed import embed_watermark
from app.watermark.extract import extract_watermark_detailed

RENDER_DPI = 150

# Active content and external references are rejected at registration and reported
# during investigation. Matching is on PDF name tokens in every object dictionary.
_DANGEROUS_NAMES = {
    "JavaScript": "javascript", "JS": "javascript",
    "Launch": "launch_action",
    "EmbeddedFile": "embedded_file", "EmbeddedFiles": "embedded_file",
    "XFA": "xfa_form",
    "GoToR": "external_reference", "GoToE": "external_reference", "URI": "external_reference",
    "SubmitForm": "external_reference", "ImportData": "external_reference",
    "RichMedia": "rich_media",
}
_NAME_RE = re.compile(r"/(" + "|".join(sorted(_DANGEROUS_NAMES, key=len, reverse=True)) + r")(?![A-Za-z0-9])")


def _open(pdf_bytes: bytes):
    if not isinstance(pdf_bytes, (bytes, bytearray)) or not bytes(pdf_bytes).startswith(b"%PDF-"):
        raise ValueError("not a PDF document")
    doc = pymupdf.open(stream=bytes(pdf_bytes), filetype="pdf")
    if doc.needs_pass or doc.is_encrypted:
        doc.close()
        raise ValueError("password-protected PDFs are not accepted")
    return doc


def _features(doc) -> List[str]:
    found = set()
    for xref in range(1, doc.xref_length()):
        try:
            obj = doc.xref_object(xref, compressed=False)
        except Exception:
            continue
        for m in _NAME_RE.finditer(obj):
            found.add(_DANGEROUS_NAMES[m.group(1)])
    try:
        if doc.embfile_count() > 0:
            found.add("embedded_file")
    except Exception:
        pass
    return sorted(found)


def _render_hash(doc, max_pages: int) -> str:
    h = hashlib.sha256()
    h.update(b"sih26237-render-v1|%d|" % RENDER_DPI)
    for i, page in enumerate(doc):
        if i >= max_pages:
            raise ValueError("page limit exceeded")
        pix = page.get_pixmap(dpi=RENDER_DPI, alpha=False)
        h.update(b"%d:%d:%d:%d|" % (i, pix.width, pix.height, pix.n))
        h.update(pix.samples)
    return h.hexdigest()


def inspect(pdf_bytes: bytes, max_pages: int) -> Dict[str, Any]:
    try:
        doc = _open(pdf_bytes)
    except Exception as exc:
        return {"ok": False, "error": f"unreadable PDF ({exc})"[:200]}
    try:
        pages = doc.page_count
        return {"ok": pages >= 1 and pages <= max_pages, "pages": pages, "dangerous_features": _features(doc),
                "error": None if 1 <= pages <= max_pages else f"page count {pages} outside 1..{max_pages}"}
    finally:
        doc.close()


def render_hash(pdf_bytes: bytes, max_pages: int) -> Dict[str, Any]:
    doc = _open(pdf_bytes)
    try:
        return {"render_hash": _render_hash(doc, max_pages), "pages": doc.page_count}
    finally:
        doc.close()


def mark(pdf_bytes: bytes, token: str, max_pages: int) -> Dict[str, Any]:
    """Embeds the marker and measures visual invariance via render hashes."""
    doc = _open(pdf_bytes)
    try:
        source_render = _render_hash(doc, max_pages)
    finally:
        doc.close()
    marked = embed_watermark(bytes(pdf_bytes), token)
    doc = _open(marked)
    try:
        delivered_render = _render_hash(doc, max_pages)
    finally:
        doc.close()
    return {"pdf": marked, "source_render_hash": source_render, "delivered_render_hash": delivered_render}


def extract(pdf_bytes: bytes, max_pages: int) -> Dict[str, Any]:
    result = extract_watermark_detailed(bytes(pdf_bytes))
    out = {"status": result.status, "token": result.token, "candidates": list(result.candidates),
           "reason": result.reason, "render_hash": None, "dangerous_features": [], "render_error": None}
    try:
        doc = _open(pdf_bytes)
        try:
            out["dangerous_features"] = _features(doc)
            out["render_hash"] = _render_hash(doc, max_pages)
        finally:
            doc.close()
    except Exception as exc:
        out["render_error"] = type(exc).__name__
    return out
