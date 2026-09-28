"""
Broadcast Encryption API for SIH26237.

Hybrid model (ML-KEM does NOT encrypt the document):
    random CEK --AES-256-GCM(AAD=document_id)--> document ciphertext (once)
    per recipient: ML-KEM-768 encaps(ek) -> shared secret
                   HKDF-SHA256(ss, info=doc|recipient) -> wrapping key
                   AES-256-GCM(wrapping key, AAD=doc|recipient) -> wrapped CEK

Recipient encapsulation keys are resolved through the signed trust manifest: an
ML-KEM key substituted in the registry is refused, never used.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.common import attested_signing_key
from app.api.documents import get_docs_dir
from app.audit import record_audit
from app.auth import AuthSession, require_roles
from app.crypto.identity import destroy_file
from app.crypto.kdf import derive_cek_wrapping_key
from app.crypto.pqc_kem import kem_encapsulate
from app.crypto.symmetric import cek_aad, compute_sha256, document_aad, encrypt_document, generate_cek, wrap_cek
from app.database.connection import get_connection
from app.ledger.blockchain import RECORD_VERSION, commit_event, ledger_transaction, sign_record
from app.ledger.records import package_digest
from app.models.schemas import EncryptRequest
from app.trust import TrustError, current_manifest, resolve_operational_key
from app.validation import is_valid_id

router = APIRouter(prefix="/api/documents", tags=["encryption"])


@router.post("/encrypt")
def encrypt_document_for_recipients(payload: EncryptRequest, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """
    Encrypts a registered document once for a fixed set of recipients.
    Encryption is one-shot: re-encrypting would orphan existing recipient packages.
    After success the plaintext original is destroyed; only ciphertext remains in the vault.
    """
    recipient_ids = list(dict.fromkeys(payload.authorized_recipient_ids))
    invalid = [r for r in recipient_ids if not is_valid_id(r)]
    if invalid:
        raise HTTPException(status_code=400, detail="Invalid recipient identifier(s)")

    conn = get_connection()
    doc = conn.execute("SELECT * FROM documents WHERE document_id = ?", (payload.document_id,)).fetchone()
    conn.close()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc["status"] != "REGISTERED":
        raise HTTPException(status_code=409, detail="Document is already encrypted; broadcast encryption is one-shot.")

    signing_key, key_id = attested_signing_key(session)
    try:
        view = current_manifest()
    except TrustError as exc:
        raise HTTPException(status_code=409, detail=f"Trust store unavailable ({exc.code})")
    resolved = {}
    for rid in recipient_ids:
        try:
            resolved[rid] = resolve_operational_key(rid, "RECIPIENT", view)
        except TrustError as exc:
            record_audit("DOCUMENT_ENCRYPTED", session.principal_id, "FAILED", document_id=payload.document_id,
                         reason=exc.code, recipient_id=rid)
            raise HTTPException(status_code=400, detail=f"Recipient {rid} has no usable attested key ({exc.code})")

    doc_file = get_docs_dir() / f"{payload.document_id}_original.pdf"
    if not doc_file.exists():
        raise HTTPException(status_code=409, detail="Original document is not available in the vault.")
    plaintext = doc_file.read_bytes()
    if compute_sha256(plaintext) != doc["original_hash"]:
        record_audit("DOCUMENT_ENCRYPTED", session.principal_id, "FAILED", document_id=payload.document_id,
                     reason="vault_integrity_mismatch")
        raise HTTPException(status_code=409, detail="Vault copy does not match the registered hash; refusing to encrypt.")

    cek = generate_cek()
    doc_ciphertext, doc_nonce = encrypt_document(plaintext, cek, document_aad(payload.document_id))
    enc_doc_file = get_docs_dir() / f"{payload.document_id}_encrypted.bin"

    now_ts = datetime.now(timezone.utc).isoformat()
    packages, package_hashes, recipient_keys = [], {}, {}
    for rid, r in resolved.items():
        ss, kem_ct = kem_encapsulate(r["mlkem_ek"])
        wrapping_key = derive_cek_wrapping_key(ss, payload.document_id, rid)
        wrapped_cek, wrap_nonce = wrap_cek(cek, wrapping_key, cek_aad(payload.document_id, rid))
        row = (payload.document_id, rid, kem_ct.hex(), wrapped_cek.hex(), wrap_nonce.hex(), now_ts, r["key_id"])
        packages.append(row)
        recipient_keys[rid] = r["key_id"]
        package_hashes[rid] = package_digest(payload.document_id, rid, r["key_id"], row[2], row[3], row[4])
    del cek

    record = {
        "record_type": "BROADCAST_ENCRYPTION",
        "record_version": RECORD_VERSION,
        "authority_id": session.principal_id,
        "signer_key_id": key_id,
        "document_id": payload.document_id,
        "original_hash": doc["original_hash"],
        "ciphertext_hash": compute_sha256(doc_nonce + doc_ciphertext),
        "authorized_recipients": sorted(resolved),
        "recipient_keys": recipient_keys,
        "package_hashes": package_hashes,
        "manifest_version": view["version"],
        "encryption_algorithm": "AES-256-GCM + ML-KEM-768 + HKDF-SHA256",
        "timestamp": now_ts,
    }
    signature = sign_record(signing_key, record)

    enc_doc_file.write_bytes(doc_nonce + doc_ciphertext)
    conn = get_connection()
    try:
        with ledger_transaction(conn) as tx:
            conn.executemany("""
                INSERT INTO encrypted_packages (document_id, recipient_id, kem_ciphertext, wrapped_cek, wrap_nonce,
                                                created_at, recipient_key_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, packages)
            conn.execute("UPDATE documents SET status = 'ENCRYPTED', encrypted_path = ? WHERE document_id = ?",
                         (enc_doc_file.name, payload.document_id))
            tx["block"] = commit_event("DOCUMENT_ENCRYPTED", record, signature, session.principal_id, conn=conn)
    except Exception:
        enc_doc_file.unlink(missing_ok=True)
        raise
    finally:
        conn.close()
    block = tx["block"]
    destroy_file(doc_file)

    record_audit("DOCUMENT_ENCRYPTED", session.principal_id, document_id=payload.document_id,
                 recipients=sorted(resolved))
    record_audit("LEDGER_COMMITTED", session.principal_id, event_type="DOCUMENT_ENCRYPTED", block_index=block["block_index"])
    return {
        "document_id": payload.document_id,
        "status": "ENCRYPTED",
        "authorized_recipients": sorted(resolved),
        "recipient_keys": recipient_keys,
        "block_index": block["block_index"],
        "message": f"Broadcast-encrypted for {len(resolved)} recipient(s): AES-256-GCM content, ML-KEM-768 key "
                   "establishment to manifest-attested keys.",
    }
