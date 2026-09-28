"""
Ledger integrity verification for SIH26237.

verify_blocks() is the shared verification core used by the application and by the
independent offline verifier (scripts/offline_verify.py). It recomputes everything
from the supplied blocks and fails closed. Signer public keys come from a key lookup
that only returns keys attested in a verified trust manifest.

Checks per block:
  1. block_index continuity starting at 1 (detects deletion / insertion / reordering)
  2. previous_hash == block_hash of the previous block
  3. event_type is known and record_type matches it
  4. stored canonical_record is exactly its canonical form, and record_hash matches
  5. block_hash recomputes over all header fields (incl. timestamp and signer_id)
  6. the signer field of the record equals signer_id and the role matches the event
  7. ML-DSA-44 signature (context-separated for v3 records) under the attested key
  8. session_id / watermark_token uniqueness across decryption records
Annotations (do not break integrity, but are reported and used by forensics):
  - key_trust: blocks signed after the signer's revocation / key retirement sequence
  - timestamp_warnings: timestamps that go backwards or are unparseable
Then: the chain tail must match the external head anchor (detects truncation), and
witness cosignatures (if configured) must not conflict with the local history.
"""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.crypto.pqc_dsa import dsa_verify_hex
from app.database.connection import drop_append_only_triggers, get_connection, init_db
from app.ledger.blockchain import (EVENT_RECORD_TYPE, EVENT_SIGNER_ROLE, GENESIS_HASH, SIGNER_FIELD, LedgerError,
                                   compute_block_hash, read_head_anchor, record_context, record_signer_key_id)
from app.ledger.canonical import canonicalize_json

# lookup(signer_id, role, key_id, block_index) -> (public_key | None, problem | None, trust_note | None)
KeyLookup = Callable[[str, str, str, int], tuple]


def _result(valid: bool, total: int, verified: int, index, message: Optional[str], details: list,
            **extra) -> Dict[str, Any]:
    out = {
        "chain_valid": valid,
        "total_blocks": total,
        "verified_blocks": verified,
        "broken_block_index": index,
        "error_message": message,
        "verification_details": details,
        "key_trust_warnings": [],
        "timestamp_warnings": [],
    }
    out.update(extra)
    return out


def manifest_key_lookup(principals: Dict[str, dict], public_keys: Dict[str, bytes]) -> KeyLookup:
    """Key lookup over a normalized manifest view and a {key_id: ML-DSA public key} map."""
    def lookup(signer_id: str, role: str, key_id: str, block_index: int):
        entry = principals.get(signer_id)
        if entry is None or entry["role"] != role:
            return None, f"signer {signer_id} is not attested as {role}", None
        key = next((k for k in entry["keys"] if k["key_id"] == key_id), None)
        if key is None:
            return None, f"signing key {key_id!r} is not attested for {signer_id}", None
        pk = public_keys.get(key_id)
        if pk is None:
            return None, f"public key {key_id} is not available", None
        if not hmac.compare_digest(hashlib.sha256(pk).hexdigest(), key["mldsa_pk_sha256"]):
            return None, f"public key {key_id} does not match the attested fingerprint", None
        note = None
        if entry["revoked_after_block"] is not None and block_index > entry["revoked_after_block"]:
            note = f"signed after {signer_id} was revoked (after block {entry['revoked_after_block']})"
        elif key["retired_after_block"] is not None and block_index > key["retired_after_block"]:
            note = f"signed after key {key_id} was retired/compromised (after block {key['retired_after_block']})"
        return pk, None, note
    return lookup


def _parse_ts(value) -> Optional[datetime]:
    try:
        ts = datetime.fromisoformat(value)
        return ts if ts.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def check_block(b, record: dict, lookup: KeyLookup) -> tuple:
    """(problem | None, trust_note | None, canonical_bytes) for one block's content and signature."""
    if b["event_type"] not in EVENT_SIGNER_ROLE:
        return "Unknown event type", None, None
    canonical_bytes = canonicalize_json(record)
    if canonical_bytes.decode("utf-8") != b["canonical_record"] or \
            hashlib.sha256(canonical_bytes).hexdigest() != b["record_hash"]:
        return "Record payload tampered: record_hash mismatch", None, None
    if record.get("record_type") != EVENT_RECORD_TYPE[b["event_type"]]:
        return "record_type does not match event type", None, None
    recalculated = compute_block_hash(b["block_index"], b["timestamp"], b["event_type"], b["previous_hash"],
                                      b["record_hash"], b["signature"], b["signer_id"])
    if recalculated != b["block_hash"]:
        return "Block hash invalid: header fields modified", None, None
    role = EVENT_SIGNER_ROLE[b["event_type"]]
    if record.get(SIGNER_FIELD[role]) != b["signer_id"]:
        return f"signer_id does not match record {SIGNER_FIELD[role]}", None, None
    key_id = record_signer_key_id(record, b["signer_id"])
    pk, problem, note = lookup(b["signer_id"], role, key_id, b["block_index"])
    if pk is None:
        return problem, None, None
    if not dsa_verify_hex(pk, canonical_bytes, b["signature"], context=record_context(record)):
        return "ML-DSA-44 signature verification failed", None, None
    return None, note, canonical_bytes


def verify_blocks(blocks: List[Any], lookup: KeyLookup, anchor: Optional[Dict[str, Any]] = None,
                  require_anchor: bool = True) -> Dict[str, Any]:
    total = len(blocks)
    details, trust_warnings, ts_warnings = [], [], []
    extra = {}

    def fail(verified, index, message):
        r = _result(False, total, verified, index, message, details)
        r["key_trust_warnings"], r["timestamp_warnings"] = trust_warnings, ts_warnings
        return r

    if not blocks:
        if anchor is not None and anchor["block_index"] != 0:
            return fail(0, None, "Ledger is empty but head anchor records blocks: truncation detected")
        return _result(True, 0, 0, None, None, [], anchor_state="EMPTY")

    expected_previous_hash = GENESIS_HASH
    seen_sessions, seen_tokens = set(), set()
    last_ts = None
    for i, b in enumerate(blocks):
        idx = b["block_index"]
        if idx != i + 1:
            return fail(i, idx, f"Block sequence anomaly: expected index {i + 1}, found {idx}")
        if b["previous_hash"] != expected_previous_hash:
            return fail(i, idx, f"Hash chain broken at Block #{idx}: previous_hash mismatch")
        try:
            record = json.loads(b["canonical_record"])
            if not isinstance(record, dict):
                raise ValueError
        except Exception:
            return fail(i, idx, f"Record payload unparseable in Block #{idx}")
        try:
            problem, note, _ = check_block(b, record, lookup)
        except Exception as exc:
            problem, note = f"verification error ({type(exc).__name__})", None
        if problem:
            return fail(i, idx, f"Block #{idx}: {problem}")

        if b["event_type"] == "DOCUMENT_DECRYPTED":
            sid, tok = record.get("session_id"), record.get("watermark_token")
            if sid in seen_sessions or tok in seen_tokens:
                return fail(i, idx, f"Duplicate session or watermark token in Block #{idx}")
            seen_sessions.add(sid)
            seen_tokens.add(tok)

        ts = _parse_ts(b["timestamp"])
        if ts is None:
            ts_warnings.append({"block_index": idx, "warning": "timestamp unparseable"})
        elif last_ts is not None and ts < last_ts:
            ts_warnings.append({"block_index": idx, "warning": "timestamp earlier than previous block "
                                                               "(clock rollback or manipulation)"})
        if ts is not None:
            last_ts = ts if last_ts is None else max(last_ts, ts)
        if note:
            trust_warnings.append({"block_index": idx, "signer_id": b["signer_id"], "warning": note})

        details.append({
            "block_index": idx,
            "event_type": b["event_type"],
            "signer_id": b["signer_id"],
            "signer_key_id": record_signer_key_id(record, b["signer_id"]),
            "signature_status": "VALID_ML_DSA_44",
            "hash_chain_status": "VALID",
            "key_trust": "TRUSTED_AT_SEQUENCE" if note is None else "NOT_TRUSTED_AT_SEQUENCE",
            "block_hash": b["block_hash"],
        })
        expected_previous_hash = b["block_hash"]

    last = blocks[-1]
    if anchor is None:
        if require_anchor:
            return fail(total, None, "Ledger head anchor missing: cannot rule out truncation")
        extra["anchor_state"] = "NOT_CHECKED"
    elif anchor["block_index"] == last["block_index"] and anchor["block_hash"] == last["block_hash"]:
        extra["anchor_state"] = "MATCH"
    elif anchor.get("pending") and anchor["pending"]["block_index"] == last["block_index"] and \
            anchor["pending"]["block_hash"] == last["block_hash"]:
        extra["anchor_state"] = "PENDING_ROLL_FORWARD"
    else:
        return fail(total, last["block_index"],
                    f"Ledger tail (Block #{last['block_index']}) does not match head anchor "
                    f"(Block #{anchor['block_index']}): truncation or rollback detected")

    r = _result(True, total, total, None, None, details, **extra)
    r["key_trust_warnings"], r["timestamp_warnings"] = trust_warnings, ts_warnings
    return r


def local_key_lookup(view: Optional[Dict[str, Any]] = None) -> KeyLookup:
    """Lookup over the verified local manifest and the registry key bytes it attests."""
    from app.crypto.identity import get_registered_key
    from app.trust import current_manifest
    view = view or current_manifest()
    public_keys = {}
    for entry in view["principals"].values():
        for k in entry["keys"]:
            reg = get_registered_key(k["key_id"])
            if reg and reg["principal_id"] == entry["principal_id"] and reg["mldsa_pk"] is not None:
                public_keys[k["key_id"]] = reg["mldsa_pk"]
    return manifest_key_lookup(view["principals"], public_keys)


def _load_blocks() -> list:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM ledger_blocks ORDER BY block_index ASC").fetchall()
    finally:
        conn.close()


def verify_single_block(row) -> Optional[str]:
    """Problem string or None (used before rolling the head anchor forward)."""
    try:
        record = json.loads(row["canonical_record"])
        problem, _, _ = check_block(row, record, local_key_lookup())
        return problem
    except Exception as exc:
        return f"verification error ({type(exc).__name__}: {exc})"


def verify_ledger() -> Dict[str, Any]:
    try:
        return _verify_ledger()
    except Exception as exc:
        return _result(False, 0, 0, None, f"VERIFICATION_ERROR: ledger could not be verified ({type(exc).__name__})", [])


def _verify_ledger() -> Dict[str, Any]:
    from app.trust import TrustError
    blocks = _load_blocks()
    try:
        anchor = read_head_anchor()
    except LedgerError as exc:
        return _result(False, len(blocks), 0, None, str(exc), [])
    try:
        lookup = local_key_lookup() if blocks else (lambda *a: (None, "no trust manifest", None))
    except TrustError as exc:
        return _result(False, len(blocks), 0, None,
                       f"Trust store unavailable ({exc.code}): signer keys cannot be authenticated", [])
    result = verify_blocks(blocks, lookup, anchor)
    if not result["chain_valid"]:
        return result
    from app.ledger.checkpoint import witness_status
    witness = witness_status(blocks)
    result["witness"] = witness
    if witness.get("status") == "PIN_ERROR":
        result["chain_valid"] = False
        result["error_message"] = f"Witness trust anchor unusable: {witness.get('error')}"
    elif witness.get("conflicts"):
        result["chain_valid"] = False
        result["error_message"] = ("Local ledger history conflicts with a checkpoint cosigned by an independent "
                                   "witness: history was rewritten")
        result["broken_block_index"] = witness["conflicts"][0]["block_index"]
    return result


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
