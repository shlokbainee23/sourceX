"""
Ledger integrity verification for SIH26237.

verify_ledger() recomputes everything from stored data and fails closed: any
anomaly or internal error yields chain_valid = False.

Checks per block:
  1. block_index continuity starting at 1 (detects deletion / insertion / reordering)
  2. previous_hash == block_hash of the previous block
  3. event_type is a known type
  4. stored canonical_record is exactly its canonical form, and record_hash matches
  5. block_hash recomputes over all header fields (incl. timestamp and signer_id)
  6. ML-DSA-44 signature by the signer whose role matches the event type;
     for decryption records, signer_id must equal the record's recipient_id
  7. session_id / watermark_token uniqueness across decryption records
Then: the chain tail must match the external head anchor (detects truncation).
"""

import hashlib
import json
from typing import Any, Dict

from app.crypto.identity import get_authority_public_key, get_recipient_public_keys
from app.crypto.pqc_dsa import dsa_verify_hex
from app.database.connection import get_connection, drop_append_only_triggers, init_db
from app.ledger.blockchain import (
    EVENT_SIGNER_ROLE,
    GENESIS_HASH,
    compute_block_hash,
    read_head_anchor,
)
from app.ledger.canonical import canonicalize_json


def _fail(total: int, verified: int, index, message: str, details: list) -> Dict[str, Any]:
    return {
        "chain_valid": False,
        "total_blocks": total,
        "verified_blocks": verified,
        "broken_block_index": index,
        "error_message": message,
        "verification_details": details,
    }


def _signer_public_key(event_type: str, signer_id: str, record: dict):
    role = EVENT_SIGNER_ROLE[event_type]
    if role == "RECIPIENT":
        if record.get("recipient_id") != signer_id:
            return None, "signer_id does not match record recipient_id"
        keys = get_recipient_public_keys(signer_id, include_revoked=True)
        return (keys["mldsa_pk"] if keys else None), f"Recipient {signer_id} public key not found"
    if record.get("authority_id") != signer_id:
        return None, "signer_id does not match record authority_id"
    pk = get_authority_public_key(signer_id)
    return pk, f"Authority {signer_id} public key not found"


def verify_ledger() -> Dict[str, Any]:
    try:
        return _verify_ledger()
    except Exception as exc:
        return _fail(0, 0, None, f"VERIFICATION_ERROR: ledger could not be verified ({type(exc).__name__})", [])


def _verify_ledger() -> Dict[str, Any]:
    conn = get_connection()
    blocks = conn.execute("SELECT * FROM ledger_blocks ORDER BY block_index ASC").fetchall()
    conn.close()
    total = len(blocks)
    anchor = read_head_anchor()

    if not blocks:
        if anchor is not None:
            return _fail(0, 0, None, "Ledger is empty but head anchor records blocks: truncation detected", [])
        return {"chain_valid": True, "total_blocks": 0, "verified_blocks": 0,
                "broken_block_index": None, "error_message": None, "verification_details": []}

    expected_previous_hash = GENESIS_HASH
    details = []
    seen_sessions, seen_tokens = set(), set()

    for i, b in enumerate(blocks):
        idx = b["block_index"]

        if idx != i + 1:
            return _fail(total, i, idx, f"Block sequence anomaly: expected index {i + 1}, found {idx}", details)

        if b["previous_hash"] != expected_previous_hash:
            return _fail(total, i, idx, f"Hash chain broken at Block #{idx}: previous_hash mismatch", details)

        if b["event_type"] not in EVENT_SIGNER_ROLE:
            return _fail(total, i, idx, f"Unknown event type in Block #{idx}", details)

        try:
            record = json.loads(b["canonical_record"])
            canonical_bytes = canonicalize_json(record)
        except Exception:
            return _fail(total, i, idx, f"Record payload unparseable in Block #{idx}", details)

        if canonical_bytes.decode("utf-8") != b["canonical_record"] or \
                hashlib.sha256(canonical_bytes).hexdigest() != b["record_hash"]:
            return _fail(total, i, idx, f"Record payload tampered in Block #{idx}: record_hash mismatch", details)

        recalculated = compute_block_hash(idx, b["timestamp"], b["event_type"], b["previous_hash"],
                                          b["record_hash"], b["signature"], b["signer_id"])
        if recalculated != b["block_hash"]:
            return _fail(total, i, idx, f"Block hash invalid in Block #{idx}: header fields modified", details)

        pk, missing_reason = _signer_public_key(b["event_type"], b["signer_id"], record)
        if pk is None:
            return _fail(total, i, idx, f"Block #{idx}: {missing_reason}", details)
        if not dsa_verify_hex(pk, canonical_bytes, b["signature"]):
            return _fail(total, i, idx, f"ML-DSA-44 signature verification failed for Block #{idx}", details)

        if b["event_type"] == "DOCUMENT_DECRYPTED":
            sid, tok = record.get("session_id"), record.get("watermark_token")
            if sid in seen_sessions or tok in seen_tokens:
                return _fail(total, i, idx, f"Duplicate session or watermark token in Block #{idx}", details)
            seen_sessions.add(sid)
            seen_tokens.add(tok)

        details.append({
            "block_index": idx,
            "event_type": b["event_type"],
            "signer_id": b["signer_id"],
            "signature_status": "VALID_ML_DSA_44",
            "hash_chain_status": "VALID",
            "block_hash": b["block_hash"],
        })
        expected_previous_hash = b["block_hash"]

    last = blocks[-1]
    if anchor is None:
        return _fail(total, total, None, "Ledger head anchor missing: cannot rule out truncation", details)
    if anchor.get("block_index") != last["block_index"] or anchor.get("block_hash") != last["block_hash"]:
        return _fail(total, total, last["block_index"],
                     f"Ledger tail (Block #{last['block_index']}) does not match head anchor "
                     f"(Block #{anchor.get('block_index')}): truncation or rollback detected", details)

    return {"chain_valid": True, "total_blocks": total, "verified_blocks": total,
            "broken_block_index": None, "error_message": None, "verification_details": details}


TAMPERABLE_FIELDS = ("canonical_record", "signer_id", "previous_hash", "timestamp", "event_type",
                     "signature", "record_hash", "block_hash", "delete", "swap_with_next")


def simulate_tampering(block_index: int, field: str, new_value: Any = None) -> Dict[str, Any]:
    """
    DEMO / TEST ONLY. Simulates an adversary with raw write access to the SQLite file:
    drops the append-only triggers, modifies a block, then restores the triggers.
    Never called by normal operational code paths; the API exposes it only in demo mode.
    """
    if field not in TAMPERABLE_FIELDS:
        return {"success": False, "message": f"Unsupported tamper field: {field}"}

    init_db()
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ledger_blocks WHERE block_index = ?", (block_index,)).fetchone()
        if not row:
            return {"success": False, "message": f"Block #{block_index} does not exist"}
        drop_append_only_triggers(conn)

        if field == "canonical_record":
            data = json.loads(row["canonical_record"])
            if isinstance(new_value, dict):
                data.update(new_value)
            elif isinstance(new_value, str):
                try:
                    parsed = json.loads(new_value)
                    data.update(parsed) if isinstance(parsed, dict) else data.__setitem__("tampered_flag", new_value)
                except ValueError:
                    data["tampered_flag"] = new_value
            else:
                data["tampered_flag"] = True
            conn.execute("UPDATE ledger_blocks SET canonical_record = ? WHERE block_index = ?",
                         (json.dumps(data), block_index))
        elif field == "delete":
            conn.execute("DELETE FROM ledger_blocks WHERE block_index = ?", (block_index,))
        elif field == "swap_with_next":
            nxt = conn.execute("SELECT id FROM ledger_blocks WHERE block_index = ?", (block_index + 1,)).fetchone()
            if not nxt:
                return {"success": False, "message": f"Block #{block_index + 1} does not exist"}
            conn.execute("UPDATE ledger_blocks SET block_index = -1 WHERE block_index = ?", (block_index,))
            conn.execute("UPDATE ledger_blocks SET block_index = ? WHERE block_index = ?", (block_index, block_index + 1))
            conn.execute("UPDATE ledger_blocks SET block_index = ? WHERE block_index = -1", (block_index + 1,))
        else:
            conn.execute(f"UPDATE ledger_blocks SET {field} = ? WHERE block_index = ?", (str(new_value), block_index))
    finally:
        conn.close()
        init_db()

    return {
        "success": True,
        "message": f"Deliberate tamper applied to Block #{block_index} ({field} modified)",
        "tampered_block": block_index,
    }
