"""
Upload handling helpers: size limits and PDF validation (parsing happens in the
isolated PDF worker process, never in the key-holding server process).
"""

from pathlib import PurePath

from fastapi import HTTPException, UploadFile

from app import config
from app.pdf import worker


async def read_upload(file: UploadFile) -> bytes:
    content = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the maximum permitted size")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return content


def require_pdf(content: bytes, *, reject_active_content: bool = True) -> dict:
    """Validates a PDF in the worker. Returns the inspection result."""
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a PDF document")
    try:
        info = worker.inspect(content)
    except worker.PdfWorkerError as exc:
        raise HTTPException(status_code=400, detail=f"Uploaded PDF could not be processed safely: {exc}")
    if not info.get("ok"):
        raise HTTPException(status_code=400, detail=f"Uploaded PDF rejected: {info.get('error') or 'could not be parsed'}")
    if reject_active_content and info.get("dangerous_features"):
        raise HTTPException(status_code=400,
                            detail="Uploaded PDF contains active content or external references which are not "
                                   f"permitted: {', '.join(info['dangerous_features'])}")
    return info


def safe_filename(name: str) -> str:
    base = PurePath((name or "document.pdf").replace("\\", "/")).name
    cleaned = "".join(ch for ch in base if ch.isprintable())[:255]
    return cleaned or "document.pdf"
