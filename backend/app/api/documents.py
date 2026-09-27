"""
Document registration and listing API for SIH26237.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app import config
from app.api.uploads import read_upload, require_pdf, safe_filename
from app.audit import record_audit
from app.auth import AuthSession, current_session, require_roles
from app.crypto.symmetric import compute_sha256
from app.database.connection import get_connection
from app.ledger.blockchain import commit_event, ledger_transaction, sign_record
from app.models.schemas import DocumentResponse
from app.validation import CLASSIFICATIONS, ID_PATTERN

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_docs_dir() -> Path:
    return config.documents_dir()


def _to_response(r) -> DocumentResponse:
    return DocumentResponse(
        document_id=r["document_id"],
        filename=r["filename"],
        original_hash=r["original_hash"],
        classification=r["classification"],
        owner=r["owner"],
        created_at=r["created_at"],
        status=r["status"],
    )


@router.get("", response_model=List[DocumentResponse])
def list_documents(session: AuthSession = Depends(current_session)):
    """Recipients see only documents they are authorized for; other roles see all."""
    conn = get_connection()
    if session.role == "RECIPIENT":
        rows = conn.execute("""
            SELECT d.* FROM documents d
            JOIN encrypted_packages p ON p.document_id = d.document_id
            WHERE p.recipient_id = ? ORDER BY d.id DESC
        """, (session.principal_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    conn.close()
    return [_to_response(r) for r in rows]


@router.post("/register", response_model=DocumentResponse)
async def register_document(
    document_id: str = Form(..., pattern=ID_PATTERN, max_length=64),
    classification: str = Form("CONFIDENTIAL"),
    file: UploadFile = File(...),
    session: AuthSession = Depends(require_roles("AUTHORITY")),
):
    """
    AUTHORITY registers a confidential PDF. The SHA-256 of the original is recorded in an
    authority-signed DOCUMENT_REGISTERED ledger block. The owner is the authenticated authority.
    """
    if classification not in CLASSIFICATIONS:
        raise HTTPException(status_code=400, detail=f"classification must be one of {list(CLASSIFICATIONS)}")
    if ".." in document_id:
        raise HTTPException(status_code=400, detail="Invalid document identifier")

    content = await read_upload(file)
    require_pdf(content)
    filename = safe_filename(file.filename)
    doc_hash = compute_sha256(content)
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    exists = conn.execute("SELECT 1 FROM documents WHERE document_id = ?", (document_id,)).fetchone()
    conn.close()
    if exists:
        raise HTTPException(status_code=409, detail=f"Document ID {document_id} already registered.")

    record = {
        "record_type": "DOCUMENT_REGISTRATION",
        "record_version": "2.0",
        "authority_id": session.principal_id,
        "document_id": document_id,
        "filename": filename,
        "original_hash": doc_hash,
        "classification": classification,
        "timestamp": created_at,
    }
    signature = sign_record(session.keys["mldsa_sk"], record)

    save_path = get_docs_dir() / f"{document_id}_original.pdf"
    save_path.write_bytes(content)
    conn = get_connection()
    try:
        with ledger_transaction(conn) as tx:
            conn.execute("""
                INSERT INTO documents (document_id, filename, original_hash, classification, owner, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'REGISTERED')
            """, (document_id, filename, doc_hash, classification, session.principal_id, created_at))
            tx["block"] = commit_event("DOCUMENT_REGISTERED", record, signature, session.principal_id, conn=conn)
    except Exception:
        save_path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()
    block = tx["block"]

    record_audit("DOCUMENT_REGISTERED", session.principal_id, document_id=document_id, original_hash=doc_hash)
    record_audit("LEDGER_COMMITTED", session.principal_id, event_type="DOCUMENT_REGISTERED", block_index=block["block_index"])
    return DocumentResponse(
        document_id=document_id,
        filename=filename,
        original_hash=doc_hash,
        classification=classification,
        owner=session.principal_id,
        created_at=created_at,
        status="REGISTERED",
    )
