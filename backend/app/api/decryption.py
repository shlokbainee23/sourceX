"""
Recipient decryption, forensic marking and signed provenance API for SIH26237.

The recipient identity comes exclusively from the authenticated session. Private keys
come from that session's unlocked encrypted keystore. Every cryptographic failure
denies access; nothing is recorded as a successful decryption unless the session row
and the signed ledger block are committed together in one transaction.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.documents import get_docs_dir
from app.audit import record_audit
from app.auth import AuthSession, require_roles
from app.crypto.kdf import derive_cek_wrapping_key
from app.crypto.pqc_kem import kem_decapsulate
from app.crypto.symmetric import NONCE_SIZE, cek_aad, compute_sha256, decrypt_document, document_aad, unwrap_cek
from app.database.connection import get_connection
from app.ledger.blockchain import commit_event, ledger_transaction, sign_record
from app.ledger.records import build_decryption_record
from app.models.schemas import DecryptionResponse, DecryptRequest
from app.validation import is_valid_id
from app.watermark.embed import embed_watermark, generate_watermark_token

router = APIRouter(prefix="/api", tags=["decryption"])


def _deny(principal_id: str, document_id: str, status: int, detail: str, reason: str):
    record_audit("DECRYPTION_DENIED", principal_id, "DENIED", document_id=document_id, reason=reason)
    raise HTTPException(status_code=status, detail=detail)


@router.post("/decrypt", response_model=DecryptionResponse)
def decrypt_document_for_recipient(payload: DecryptRequest, session: AuthSession = Depends(require_roles("RECIPIENT"))):
    recipient_id = session.principal_id
    document_id = payload.document_id
    if payload.recipient_id is not None and payload.recipient_id != recipient_id:
        _deny(recipient_id, document_id, 403, "Recipients may only decrypt as themselves.", "recipient_id_mismatch")

    record_audit("DECRYPTION_STARTED", recipient_id, document_id=document_id)

    conn = get_connection()
    pkg = conn.execute("SELECT * FROM encrypted_packages WHERE document_id = ? AND recipient_id = ?",
                       (document_id, recipient_id)).fetchone()
    doc = conn.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,)).fetchone()
    conn.close()
    if not pkg or not doc:
        _deny(recipient_id, document_id, 403, "You are not authorized to decrypt this document.", "no_package")

    if "mlkem_dk" not in session.keys or "mldsa_sk" not in session.keys:
        _deny(recipient_id, document_id, 403, "Keystore is not unlocked for this session.", "keystore_locked")

    enc_file = get_docs_dir() / f"{document_id}_encrypted.bin"
    if not enc_file.exists():
        _deny(recipient_id, document_id, 404, "Encrypted document payload not found.", "ciphertext_missing")
    enc_data = enc_file.read_bytes()
    doc_nonce, doc_ciphertext = enc_data[:NONCE_SIZE], enc_data[NONCE_SIZE:]

    try:
        ss = kem_decapsulate(session.keys["mlkem_dk"], bytes.fromhex(pkg["kem_ciphertext"]))
        wrapping_key = derive_cek_wrapping_key(ss, document_id, recipient_id)
        cek = unwrap_cek(bytes.fromhex(pkg["wrapped_cek"]), bytes.fromhex(pkg["wrap_nonce"]), wrapping_key,
                         cek_aad(document_id, recipient_id))
    except (InvalidTag, ValueError):
        _deny(recipient_id, document_id, 403, "Decryption denied: key package could not be opened.", "cek_unwrap_failed")

    try:
        plaintext = decrypt_document(doc_ciphertext, doc_nonce, cek, document_aad(document_id))
    except (InvalidTag, ValueError):
        _deny(recipient_id, document_id, 409, "Decryption denied: document ciphertext failed authentication.",
              "ciphertext_auth_failed")

    source_hash = compute_sha256(plaintext)
    if source_hash != doc["original_hash"]:
        _deny(recipient_id, document_id, 409, "Decryption denied: plaintext does not match the registered document hash.",
              "source_hash_mismatch")

    now_ts = datetime.now(timezone.utc).isoformat()
    session_id = f"SES-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(8).upper()}"
    wm_token = generate_watermark_token()
    delivered_pdf = embed_watermark(plaintext, wm_token)
    delivered_hash = compute_sha256(delivered_pdf)
    record_audit("WATERMARK_CREATED", recipient_id, session_id=session_id,
                 token_ref=hashlib.sha256(wm_token.encode()).hexdigest()[:16])

    record = build_decryption_record(
        document_id=document_id,
        recipient_id=recipient_id,
        session_id=session_id,
        watermark_token=wm_token,
        source_document_hash=source_hash,
        delivered_document_hash=delivered_hash,
        decryption_timestamp=now_ts,
    )
    sig_hex = sign_record(session.keys["mldsa_sk"], record)

    out_filename = f"{document_id}_{recipient_id}_{session_id}.pdf"
    out_path = get_docs_dir() / out_filename
    out_path.write_bytes(delivered_pdf)

    conn = get_connection()
    try:
        with ledger_transaction(conn) as tx:
            block = commit_event("DOCUMENT_DECRYPTED", record, sig_hex, recipient_id, conn=conn)
            tx["block"] = block
            conn.execute("""
                INSERT INTO sessions (session_id, document_id, recipient_id, watermark_token, watermark_token_hash,
                                      source_document_hash, delivered_document_hash, delivered_filename, signature,
                                      block_index, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED')
            """, (session_id, document_id, recipient_id, wm_token, hashlib.sha256(wm_token.encode()).hexdigest(),
                  source_hash, delivered_hash, out_filename, sig_hex, block["block_index"], now_ts))
    except Exception:
        out_path.unlink(missing_ok=True)
        record_audit("DECRYPTION_FAILED", recipient_id, "FAILED", document_id=document_id, reason="ledger_commit_failed")
        raise HTTPException(status_code=500, detail="Decryption record could not be committed; no copy was released.")
    finally:
        conn.close()

    record_audit("LEDGER_COMMITTED", recipient_id, event_type="DOCUMENT_DECRYPTED", block_index=block["block_index"])
    record_audit("DECRYPTION_COMPLETED", recipient_id, document_id=document_id, session_id=session_id)

    return DecryptionResponse(
        session_id=session_id,
        document_id=document_id,
        recipient_id=recipient_id,
        watermark_token=wm_token,
        decryption_timestamp=now_ts,
        delivered_document_hash=delivered_hash,
        signature=sig_hex[:64] + "...",
        block_index=block["block_index"],
        block_hash=block["block_hash"],
        decrypted_file_path=f"/api/sessions/{session_id}/download",
        message="Decryption complete. Forensic marker embedded and recipient-signed record committed to the ledger.",
    )


@router.get("/sessions/{session_id}/download")
def download_session_copy(session_id: str, session: AuthSession = Depends(require_roles("RECIPIENT"))):
    """A recipient may download only the copy produced by one of their own sessions."""
    if not is_valid_id(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    conn = get_connection()
    row = conn.execute("SELECT recipient_id, delivered_filename FROM sessions WHERE session_id = ?",
                       (session_id,)).fetchone()
    conn.close()
    if not row or row["recipient_id"] != session.principal_id:
        record_audit("DOWNLOAD_DENIED", session.principal_id, "DENIED", session_id=session_id)
        raise HTTPException(status_code=404, detail="Session not found.")

    docs_dir = get_docs_dir().resolve()
    file_path = (docs_dir / row["delivered_filename"]).resolve()
    if file_path.parent != docs_dir or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Delivered copy not found.")
    record_audit("DOCUMENT_DOWNLOADED", session.principal_id, session_id=session_id)
    return FileResponse(file_path, media_type="application/pdf", filename=row["delivered_filename"])
