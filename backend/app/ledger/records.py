"""
Canonical provenance record builders for SIH26237.
The same builder is used when signing at decryption time and when reconstructing
the record during investigation, so both sides produce identical canonical bytes.
"""

from typing import Any, Dict

DECRYPTION_RECORD_VERSION = "2.0"


def build_decryption_record(*, document_id: str, recipient_id: str, session_id: str, watermark_token: str,
                            source_document_hash: str, delivered_document_hash: str,
                            decryption_timestamp: str) -> Dict[str, Any]:
    return {
        "record_type": "DECRYPTION_RECORD",
        "record_version": DECRYPTION_RECORD_VERSION,
        "document_id": document_id,
        "recipient_id": recipient_id,
        "session_id": session_id,
        "watermark_token": watermark_token,
        "source_document_hash": source_document_hash,
        "delivered_document_hash": delivered_document_hash,
        "decryption_timestamp": decryption_timestamp,
    }


def build_decryption_record_from_session(row) -> Dict[str, Any]:
    return build_decryption_record(
        document_id=row["document_id"],
        recipient_id=row["recipient_id"],
        session_id=row["session_id"],
        watermark_token=row["watermark_token"],
        source_document_hash=row["source_document_hash"],
        delivered_document_hash=row["delivered_document_hash"],
        decryption_timestamp=row["timestamp"],
    )
