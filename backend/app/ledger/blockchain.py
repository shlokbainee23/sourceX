"""
Tamper-evident hash-chained provenance ledger for SIH26237.

Each block commits to:
    block_hash = SHA-256(canonical_json({v, block_index, timestamp, event_type,
                                         previous_hash, record_hash, signer_id, signature}))
    record_hash = SHA-256(canonical_json(record))

Every record is signed with ML-DSA-44 by its signer (AUTHORITY for registration and
encryption events, the RECIPIENT for decryption events).

Tamper evidence, not immutability: SQLite triggers reject UPDATE/DELETE from
application code, the chain detects modified/inserted/deleted/reordered blocks, and
an external head anchor file detects truncation of the newest blocks. An attacker
who controls the whole data directory AND the signing keys could rebuild the chain.
"""

import hashlib
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app import config
from app.crypto.pqc_dsa import dsa_sign
from app.database.connection import get_connection, transaction
from app.ledger.canonical import canonicalize_json

GENESIS_HASH = "0" * 64
BLOCK_FORMAT_VERSION = 2

EVENT_SIGNER_ROLE = {
    "DOCUMENT_REGISTERED": "AUTHORITY",
    "DOCUMENT_ENCRYPTED": "AUTHORITY",
    "DOCUMENT_DECRYPTED": "RECIPIENT",
    "TRUST_MANIFEST_IMPORTED": "AUTHORITY",
}


class LedgerError(Exception):
    pass


# The head anchor is written after COMMIT; this lock keeps "append + anchor update"
# atomic with respect to other writers in this process. Single-process deployment only.
_LEDGER_LOCK = threading.RLock()


@contextmanager
def ledger_transaction(conn: sqlite3.Connection):
    """
    Wraps a database transaction that appends ledger blocks. Callers assign the
    appended block to state["block"]; the head anchor is updated only after COMMIT.
    """
    with _LEDGER_LOCK:
        state: Dict[str, Any] = {"block": None}
        with transaction(conn):
            yield state
        if state["block"] is not None:
            _write_head_anchor(state["block"]["block_index"], state["block"]["block_hash"])


def compute_record_hash(record: Dict[str, Any]) -> str:
    return hashlib.sha256(canonicalize_json(record)).hexdigest()


def compute_block_hash(block_index: int, timestamp: str, event_type: str, previous_hash: str,
                       record_hash: str, signature: str, signer_id: str) -> str:
    header = {
        "v": BLOCK_FORMAT_VERSION,
        "block_index": block_index,
        "timestamp": timestamp,
        "event_type": event_type,
        "previous_hash": previous_hash,
        "record_hash": record_hash,
        "signer_id": signer_id,
        "signature": signature,
    }
    return hashlib.sha256(canonicalize_json(header)).hexdigest()


def read_head_anchor() -> Optional[Dict[str, Any]]:
    path = config.ledger_head_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_head_anchor(block_index: int, block_hash: str) -> None:
    path = config.ledger_head_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "block_index": block_index,
        "block_hash": block_hash,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")
    os.replace(tmp, path)


def _tail(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT block_index, block_hash FROM ledger_blocks ORDER BY block_index DESC LIMIT 1"
    ).fetchone()


def _check_tail_matches_anchor(tail) -> None:
    """Refuse to append on top of a ledger whose tail disagrees with the head anchor;
    otherwise a truncation would be silently re-anchored by the next commit."""
    anchor = read_head_anchor()
    if tail is None:
        if anchor is not None:
            raise LedgerError("Ledger is empty but head anchor exists: possible truncation")
        return
    if anchor is None or anchor.get("block_index") != tail["block_index"] or anchor.get("block_hash") != tail["block_hash"]:
        raise LedgerError("Ledger tail does not match head anchor: refusing to append")


def commit_event(event_type: str, record: Dict[str, Any], signature: str, signer_id: str,
                 conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Appends a signed record as a new block. When `conn` is supplied the caller must be
    inside ledger_transaction(conn) and store the returned block in state["block"].
    """
    if event_type not in EVENT_SIGNER_ROLE:
        raise LedgerError(f"Unknown ledger event type {event_type}")

    canonical_bytes = canonicalize_json(record)
    record_hash = hashlib.sha256(canonical_bytes).hexdigest()
    canonical_str = canonical_bytes.decode("utf-8")

    def _append(c: sqlite3.Connection) -> Dict[str, Any]:
        last = _tail(c)
        _check_tail_matches_anchor(last)
        if last:
            block_index = last["block_index"] + 1
            previous_hash = last["block_hash"]
        else:
            block_index = 1
            previous_hash = GENESIS_HASH
        timestamp = datetime.now(timezone.utc).isoformat()
        block_hash = compute_block_hash(block_index, timestamp, event_type, previous_hash,
                                        record_hash, signature, signer_id)
        c.execute("""
            INSERT INTO ledger_blocks (
                block_index, timestamp, event_type, previous_hash,
                record_hash, canonical_record, signature, signer_id, block_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (block_index, timestamp, event_type, previous_hash,
              record_hash, canonical_str, signature, signer_id, block_hash))
        return {
            "block_index": block_index,
            "timestamp": timestamp,
            "event_type": event_type,
            "previous_hash": previous_hash,
            "record_hash": record_hash,
            "canonical_record": record,
            "signature": signature,
            "signer_id": signer_id,
            "block_hash": block_hash,
        }

    if conn is not None:
        return _append(conn)

    own = get_connection()
    try:
        with ledger_transaction(own) as state:
            state["block"] = _append(own)
    finally:
        own.close()
    return state["block"]


def sign_record(sk: bytes, record: Dict[str, Any]) -> str:
    return dsa_sign(sk, canonicalize_json(record)).hex()


def get_all_blocks():
    """Retrieve all ledger blocks ordered by index."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ledger_blocks ORDER BY block_index ASC").fetchall()
    conn.close()
    return [
        {
            "block_index": r["block_index"],
            "timestamp": r["timestamp"],
            "event_type": r["event_type"],
            "previous_hash": r["previous_hash"],
            "record_hash": r["record_hash"],
            "canonical_record": json.loads(r["canonical_record"]),
            "signature": r["signature"],
            "signer_id": r["signer_id"],
            "block_hash": r["block_hash"],
        }
        for r in rows
    ]
