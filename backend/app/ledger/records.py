"""
Canonical provenance record builders for SIH26237.
The same builder is used when signing at decryption time and when reconstructing
the record during investigation, so both sides produce identical canonical bytes.

Decryption record v3 additionally binds:
  signer_key_id            the recipient key that signed (manifest-attested)
  encryption_record_hash   record_hash of the authority-signed BROADCAST_ENCRYPTION block
  package_sha256           digest of this recipient's key package, which the encryption
                           record also lists (chain of custody package -> decryption)
  source/delivered_render_hash  SHA-256 of the 150-DPI rasterization before and after
                           marking (equal values = visually identical copy)
v2 records (without these fields) remain verifiable.
"""

import hashlib
from typing import Any, Dict, Optional

from app.ledger.canonical import canonicalize_json

DECRYPTION_RECORD_VERSION = "3.0"
LEGACY_DECRYPTION_RECORD_VERSION = "2.0"


def package_digest(document_id: str, recipient_id: str, recipient_key_id: str, kem_ciphertext_hex: str,
                   wrapped_cek_hex: str, wrap_nonce_hex: str) -> str:
    return hashlib.sha256(canonicalize_json({
        "document_id": document_id,
        "recipient_id": recipient_id,
        "recipient_key_id": recipient_key_id,
        "kem_ciphertext": kem_ciphertext_hex,
        "wrapped_cek": wrapped_cek_hex,
        "wrap_nonce": wrap_nonce_hex,
    })).hexdigest()


def build_decryption_record(*, document_id: str, recipient_id: str, session_id: str, watermark_token: str,
                            source_document_hash: str, delivered_document_hash: str,
                            decryption_timestamp: str, signer_key_id: Optional[str] = None,
                            encryption_record_hash: Optional[str] = None, package_sha256: Optional[str] = None,
                            source_render_hash: Optional[str] = None, delivered_render_hash: Optional[str] = None,
                            record_version: str = DECRYPTION_RECORD_VERSION) -> Dict[str, Any]:
    record = {
        "record_type": "DECRYPTION_RECORD",
        "record_version": record_version,
        "document_id": document_id,
        "recipient_id": recipient_id,
        "session_id": session_id,
        "watermark_token": watermark_token,
        "source_document_hash": source_document_hash,
        "delivered_document_hash": delivered_document_hash,
        "decryption_timestamp": decryption_timestamp,
    }
    if record_version == DECRYPTION_RECORD_VERSION:
        record.update({
            "signer_key_id": signer_key_id,
            "encryption_record_hash": encryption_record_hash,
            "package_sha256": package_sha256,
            "source_render_hash": source_render_hash,
            "delivered_render_hash": delivered_render_hash,
        })
    return record


def build_decryption_record_from_session(row) -> Dict[str, Any]:
    keys = row.keys() if hasattr(row, "keys") else []
    version = row["record_version"] if "record_version" in keys and row["record_version"] else \
        LEGACY_DECRYPTION_RECORD_VERSION
    return build_decryption_record(
        document_id=row["document_id"],
        recipient_id=row["recipient_id"],
        session_id=row["session_id"],
        watermark_token=row["watermark_token"],
        source_document_hash=row["source_document_hash"],
        delivered_document_hash=row["delivered_document_hash"],
        decryption_timestamp=row["timestamp"],
        signer_key_id=row["signer_key_id"] if "signer_key_id" in keys else None,
        encryption_record_hash=row["encryption_record_hash"] if "encryption_record_hash" in keys else None,
        package_sha256=row["package_sha256"] if "package_sha256" in keys else None,
        source_render_hash=row["source_render_hash"] if "source_render_hash" in keys else None,
        delivered_render_hash=row["delivered_render_hash"] if "delivered_render_hash" in keys else None,
        record_version=version,
    )
