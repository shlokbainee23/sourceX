"""
Recipient decryption, forensic marking and signed provenance API for SIH26237.

The recipient identity comes exclusively from the authenticated session. Decryption is
a step-up operation: the recipient re-enters the keystore passphrase, the private keys
are unlocked for this one request and dropped afterwards. The key that signs the
provenance record must be the recipient's current key as attested in the verified
trust manifest. Every cryptographic failure denies access; nothing is recorded as a
successful decryption unless the session row and the signed ledger block are committed
together in one transaction.

Plaintext retention: the marked copy is written to the data directory (protect it with
full-disk encryption) only until it is downloaded ONCE (then destroyed) or
DELIVERY_TTL expires (then purged). The ledger keeps only hashes.
"""

import hashlib
import secrets
import time
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app import config
from app.api.common import attested_signing_key
from app.api.documents import get_docs_dir
from app.audit import record_audit
from app.auth import AuthSession, StepUpError, require_roles, step_up_unlock
from app.crypto import keystore
from app.crypto.identity import destroy_file
from app.crypto.kdf import derive_cek_wrapping_key
from app.crypto.pqc_kem import kem_decapsulate
from app.crypto.symmetric import NONCE_SIZE, cek_aad, compute_sha256, decrypt_document, document_aad, unwrap_cek
from app.database.connection import get_connection
from app.ledger.blockchain import commit_event, ledger_transaction, sign_record
from app.ledger.records import DECRYPTION_RECORD_VERSION, build_decryption_record, package_digest
from app.models.schemas import DecryptionResponse, DecryptRequest
from app.pdf import worker
from app.validation import is_valid_id
from app.watermark.embed import generate_watermark_token

router = APIRouter(prefix="/api", tags=["decryption"])

DELIVERY_PREFIX = "delivery_"


def _deny(principal_id: str, document_id: str, status: int, detail: str, reason: str):
    record_audit("DECRYPTION_DENIED", principal_id, "DENIED", document_id=document_id, reason=reason)
    raise HTTPException(status_code=status, detail=detail)


def _delivery_path(session_id: str):
    return get_docs_dir() / f"{DELIVERY_PREFIX}{session_id}.pdf"


def purge_expired_deliveries() -> int:
    """Destroys undownloaded marked copies older than DELIVERY_TTL_SECONDS."""
    cutoff = time.time() - config.DELIVERY_TTL_SECONDS
    purged = 0
    for f in get_docs_dir().glob(f"{DELIVERY_PREFIX}*.pdf"):
        try:
            if f.stat().st_mtime < cutoff:
                destroy_file(f)
                purged += 1
        except OSError:
            continue
    if purged:
        record_audit("DELIVERY_PURGED", None, count=purged)
    return purged


def _encryption_block(conn, document_id: str):
    return conn.execute(
        "SELECT block_index, record_hash FROM ledger_blocks WHERE event_type = 'DOCUMENT_ENCRYPTED' "
        "AND json_extract(canonical_record, '$.document_id') = ?", (document_id,)).fetchall()


@router.post("/decrypt", response_model=DecryptionResponse)
def decrypt_document_for_recipient(payload: DecryptRequest, session: AuthSession = Depends(require_roles("RECIPIENT"))):
    recipient_id = session.principal_id
    document_id = payload.document_id
    if payload.recipient_id is not None and payload.recipient_id != recipient_id:
        _deny(recipient_id, document_id, 403, "Recipients may only decrypt as themselves.", "recipient_id_mismatch")

    purge_expired_deliveries()
    record_audit("DECRYPTION_STARTED", recipient_id, document_id=document_id)

    conn = get_connection()
    try:
        pkg = conn.execute("SELECT * FROM encrypted_packages WHERE document_id = ? AND recipient_id = ?",
                           (document_id, recipient_id)).fetchone()
        doc = conn.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,)).fetchone()
        enc_blocks = _encryption_block(conn, document_id)
    finally:
        conn.close()
    if not pkg or not doc:
        _deny(recipient_id, document_id, 403, "You are not authorized to decrypt this document.", "no_package")
    if len(enc_blocks) != 1:
        _deny(recipient_id, document_id, 409, "Document provenance is inconsistent; refusing to decrypt.",
              "encryption_block_count")

    try:
        keys = step_up_unlock(session, payload.passphrase)
    except StepUpError as exc:
        _deny(recipient_id, document_id, 401, str(exc), "step_up_failed")
    try:
        session.key_id = keystore.keystore_info(recipient_id)["key_id"]
        signing_key, signer_key_id = attested_signing_key(session, keys)
        package_key_id = pkg["recipient_key_id"] or f"{recipient_id}#1"
        if package_key_id == signer_key_id:
            dk = keys.get("mlkem_dk")
        else:
            dk = keystore.retired_kem_keys(keys).get(package_key_id)
        if dk is None:
            _deny(recipient_id, document_id, 403, "The key this package was encrypted to is not in your keystore.",
                  "package_key_unavailable")

        enc_file = get_docs_dir() / f"{document_id}_encrypted.bin"
        if not enc_file.exists():
            _deny(recipient_id, document_id, 404, "Encrypted document payload not found.", "ciphertext_missing")
        enc_data = enc_file.read_bytes()
        doc_nonce, doc_ciphertext = enc_data[:NONCE_SIZE], enc_data[NONCE_SIZE:]

        try:
            ss = kem_decapsulate(dk, bytes.fromhex(pkg["kem_ciphertext"]))
            wrapping_key = derive_cek_wrapping_key(ss, document_id, recipient_id)
            cek = unwrap_cek(bytes.fromhex(pkg["wrapped_cek"]), bytes.fromhex(pkg["wrap_nonce"]), wrapping_key,
                             cek_aad(document_id, recipient_id))
        except (InvalidTag, ValueError):
            _deny(recipient_id, document_id, 403, "Decryption denied: key package could not be opened.",
                  "cek_unwrap_failed")

        try:
            plaintext = decrypt_document(doc_ciphertext, doc_nonce, cek, document_aad(document_id))
        except (InvalidTag, ValueError):
            _deny(recipient_id, document_id, 409, "Decryption denied: document ciphertext failed authentication.",
                  "ciphertext_auth_failed")
        del cek

        source_hash = compute_sha256(plaintext)
        if source_hash != doc["original_hash"]:
            _deny(recipient_id, document_id, 409,
                  "Decryption denied: plaintext does not match the registered document hash.", "source_hash_mismatch")

        now_ts = datetime.now(timezone.utc).isoformat()
        session_id = f"SES-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(8).upper()}"
        wm_token = generate_watermark_token()
        try:
            marked = worker.mark(plaintext, wm_token)
        except worker.PdfWorkerError as exc:
            _deny(recipient_id, document_id, 500, f"Forensic marking failed: {exc}", "marking_failed")
        del plaintext
        if marked["source_render_hash"] != marked["delivered_render_hash"]:
            _deny(recipient_id, document_id, 500, "Forensic marking changed the rendered output; copy not released.",
                  "visual_invariance_failed")
        delivered_pdf = marked["pdf"]
        delivered_hash = compute_sha256(delivered_pdf)
        record_audit("WATERMARK_CREATED", recipient_id, session_id=session_id,
                     token_ref=hashlib.sha256(wm_token.encode()).hexdigest()[:16])

        pkg_sha = package_digest(document_id, recipient_id, package_key_id, pkg["kem_ciphertext"],
                                 pkg["wrapped_cek"], pkg["wrap_nonce"])
        record = build_decryption_record(
            document_id=document_id,
            recipient_id=recipient_id,
            session_id=session_id,
            watermark_token=wm_token,
            source_document_hash=source_hash,
            delivered_document_hash=delivered_hash,
            decryption_timestamp=now_ts,
            signer_key_id=signer_key_id,
            encryption_record_hash=enc_blocks[0]["record_hash"],
            package_sha256=pkg_sha,
            source_render_hash=marked["source_render_hash"],
            delivered_render_hash=marked["delivered_render_hash"],
        )
        sig_hex = sign_record(signing_key, record)
    finally:
        keys.clear()

    out_path = _delivery_path(session_id)
    out_path.write_bytes(delivered_pdf)
    conn = get_connection()
    try:
        with ledger_transaction(conn) as tx:
            block = commit_event("DOCUMENT_DECRYPTED", record, sig_hex, recipient_id, conn=conn)
            tx["block"] = block
            conn.execute("""
                INSERT INTO sessions (session_id, document_id, recipient_id, watermark_token, watermark_token_hash,
                                      source_document_hash, delivered_document_hash, delivered_filename, signature,
                                      block_index, timestamp, status, record_version, signer_key_id,
                                      encryption_record_hash, package_sha256, source_render_hash, delivered_render_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?, ?, ?, ?)
            """, (session_id, document_id, recipient_id, wm_token, hashlib.sha256(wm_token.encode()).hexdigest(),
                  source_hash, delivered_hash, out_path.name, sig_hex, block["block_index"], now_ts,
                  DECRYPTION_RECORD_VERSION, signer_key_id, record["encryption_record_hash"], pkg_sha,
                  record["source_render_hash"], record["delivered_render_hash"]))
    except Exception:
        destroy_file(out_path)
        record_audit("DECRYPTION_FAILED", recipient_id, "FAILED", document_id=document_id, reason="ledger_commit_failed")
        raise HTTPException(status_code=500, detail="Decryption record could not be committed; no copy was released.")
    finally:
        conn.close()

    record_audit("LEDGER_COMMITTED", recipient_id, event_type="DOCUMENT_DECRYPTED", block_index=block["block_index"])
    record_audit("DECRYPTION_COMPLETED", recipient_id, document_id=document_id, session_id=session_id,
                 signer_key_id=signer_key_id)

    return DecryptionResponse(
        session_id=session_id,
        document_id=document_id,
        recipient_id=recipient_id,
        signer_key_id=signer_key_id,
        watermark_token=wm_token,
        decryption_timestamp=now_ts,
        delivered_document_hash=delivered_hash,
        source_render_hash=record["source_render_hash"],
        delivered_render_hash=record["delivered_render_hash"],
        signature=sig_hex[:64] + "...",
        block_index=block["block_index"],
        block_hash=block["block_hash"],
        decrypted_file_path=f"/api/sessions/{session_id}/download",
        delivery_expires_in_seconds=config.DELIVERY_TTL_SECONDS,
        message="Decryption complete. Forensic marker embedded and recipient-signed record committed to the ledger. "
                "The copy can be downloaded once.",
    )


@router.get("/sessions/{session_id}/download")
def download_session_copy(session_id: str, session: AuthSession = Depends(require_roles("RECIPIENT"))):
    """One-time download of the copy produced by one of the recipient's own sessions."""
    if not is_valid_id(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    conn = get_connection()
    try:
        row = conn.execute("SELECT recipient_id, document_id, delivered_filename FROM sessions WHERE session_id = ?",
                           (session_id,)).fetchone()
    finally:
        conn.close()
    if not row or row["recipient_id"] != session.principal_id:
        record_audit("DOWNLOAD_DENIED", session.principal_id, "DENIED", session_id=session_id)
        raise HTTPException(status_code=404, detail="Session not found.")

    purge_expired_deliveries()
    docs_dir = get_docs_dir().resolve()
    file_path = (docs_dir / row["delivered_filename"]).resolve()
    if file_path.parent != docs_dir or not file_path.is_file():
        raise HTTPException(status_code=410, detail="Delivered copy is no longer available (already downloaded or expired).")
    claimed = file_path.with_name(file_path.name + f".{secrets.token_hex(4)}.claimed")
    try:
        file_path.rename(claimed)
    except OSError:
        raise HTTPException(status_code=410, detail="Delivered copy is no longer available (already downloaded or expired).")
    try:
        data = claimed.read_bytes()
    finally:
        destroy_file(claimed)
    record_audit("DOCUMENT_DOWNLOADED", session.principal_id, session_id=session_id)
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{row["document_id"]}_{session_id}.pdf"',
                             "Cache-Control": "no-store"})
