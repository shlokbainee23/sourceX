"""
Upload handling helpers: size limits and PDF validation.
"""

from pathlib import PurePath

import pymupdf
from fastapi import HTTPException, UploadFile

from app import config


async def read_upload(file: UploadFile) -> bytes:
    content = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the maximum permitted size")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return content


def require_pdf(content: bytes) -> None:
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a PDF document")
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
        pages = doc.page_count
        doc.close()
    except Exception:
        raise HTTPException(status_code=400, detail="Uploaded PDF could not be parsed")
    if pages < 1:
        raise HTTPException(status_code=400, detail="Uploaded PDF has no pages")


def safe_filename(name: str) -> str:
    base = PurePath((name or "document.pdf").replace("\\", "/")).name
    cleaned = "".join(ch for ch in base if ch.isprintable())[:255]
    return cleaned or "document.pdf"
