"""
Tamper-evident hash-chained provenance ledger for SIH26237.

Each block commits to:
    block_hash = SHA-256(canonical_json({v, block_index, timestamp, event_type,
                                         previous_hash, record_hash, signer_id, signature}))
    record_hash = SHA-256(canonical_json(record))

Every record is signed with ML-DSA-44 by its signer (AUTHORITY for registration,
encryption and manifest events, the RECIPIENT for decryption events, the INVESTIGATOR
for investigation reports). Record v3 signatures use the context string
"sih26237/ledger-record/v3" and name the signer's key_id; v2 records (empty context,
implicit key '<signer>#1') remain verifiable.

Crash consistency with the external head anchor (ledger_head.json):
    1. BEGIN IMMEDIATE; append block N+1
    2. write anchor {head: N, pending: N+1 (hash)} + fsync        (write-ahead intent)
    3. COMMIT
    4. write anchor {head: N+1, pending: null} + fsync
A crash between 3 and 4 leaves DB tail = pending intent; the next writer (or startup)
rolls the anchor forward only if the tail block equals the fsynced intent and passes
full verification. A crash between 2 and 3 leaves a stale intent that is discarded
because the DB tail still equals the anchored head. Any other disagreement is a
truncation/rollback signal and all writes stop.

Concurrency: an in-process lock plus an OS file lock (ledger.writer.lock) serialize
writers across processes that share the data directory; SQLite BEGIN IMMEDIATE
serializes the database itself.

Tamper evidence, not immutability: an attacker who controls the whole data directory
AND the signing keys could rebuild the chain. External witness cosignatures
(app.ledger.checkpoint) are what make a rewrite of already-witnessed history detectable.
"""

import hashlib
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app import config
from app.crypto.pqc_dsa import CTX_LEDGER_RECORD, CTX_LEGACY, dsa_sign
from app.database.connection import get_connection
from app.ledger.canonical import canonicalize_json

GENESIS_HASH = "0" * 64
BLOCK_FORMAT_VERSION = 2
RECORD_VERSION = "3.0"
ANCHOR_FORMAT = "sih26237-local-head-anchor"
ANCHOR_VERSION = 2

EVENT_SIGNER_ROLE = {
    "DOCUMENT_REGISTERED": "AUTHORITY",
    "DOCUMENT_ENCRYPTED": "AUTHORITY",
    "DOCUMENT_DECRYPTED": "RECIPIENT",
    "TRUST_MANIFEST_IMPORTED": "AUTHORITY",
    "INVESTIGATION_RECORDED": "INVESTIGATOR",
}

EVENT_RECORD_TYPE = {
    "DOCUMENT_REGISTERED": "DOCUMENT_REGISTRATION",
    "DOCUMENT_ENCRYPTED": "BROADCAST_ENCRYPTION",
    "DOCUMENT_DECRYPTED": "DECRYPTION_RECORD",
    "TRUST_MANIFEST_IMPORTED": "TRUST_MANIFEST",
    "INVESTIGATION_RECORDED": "INVESTIGATION_REPORT",
}

SIGNER_FIELD = {"AUTHORITY": "authority_id", "RECIPIENT": "recipient_id", "INVESTIGATOR": "investigator_id"}


class LedgerError(Exception):
    pass


def record_context(record: Dict[str, Any]) -> bytes:
    return CTX_LEDGER_RECORD if record.get("record_version") == RECORD_VERSION else CTX_LEGACY


def record_signer_key_id(record: Dict[str, Any], signer_id: str) -> str:
    if record.get("record_version") == RECORD_VERSION:
        return record.get("signer_key_id") or ""
    return f"{signer_id}#1"


# ----------------------------------------------------------------- locking

_LEDGER_LOCK = threading.RLock()
_depth = 0
_lock_handle = None
LOCK_TIMEOUT_SECONDS = 30


def _lock_path():
    return config.data_dir() / "ledger.writer.lock"


def _acquire_file_lock():
    fh = open(_lock_path(), "a+b")
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    try:
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    return fh
                except OSError:
                    if time.monotonic() > deadline:
                        raise LedgerError("Timed out waiting for the ledger writer lock")
                    time.sleep(0.01)
        import fcntl
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fh
            except OSError:
                if time.monotonic() > deadline:
                    raise LedgerError("Timed out waiting for the ledger writer lock")
                time.sleep(0.01)
    except BaseException:
        fh.close()
        raise


def _release_file_lock(fh) -> None:
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        fh.close()


@contextmanager
def writer_lock():
    """Re-entrant within a thread; exclusive across threads and processes."""
    global _depth, _lock_handle
    with _LEDGER_LOCK:
        if _depth == 0:
            _lock_handle = _acquire_file_lock()
        _depth += 1
        try:
            yield
        finally:
            _depth -= 1
            if _depth == 0:
                handle, _lock_handle = _lock_handle, None
                _release_file_lock(handle)


# ------------------------------------------------------------------ anchor

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
    """Normalized anchor {block_index, block_hash, pending} or None. Raises LedgerError if malformed."""
    path = config.ledger_head_path()
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        idx, bh = doc["block_index"], doc["block_hash"]
        if not isinstance(idx, int) or isinstance(idx, bool) or idx < 0 or not isinstance(bh, str) or len(bh) != 64:
            raise ValueError
        pending = doc.get("pending")
        if pending is not None:
            if set(pending) != {"block_index", "block_hash", "previous_hash"} or pending["block_index"] != idx + 1 \
                    or pending["previous_hash"] != bh:
                raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise LedgerError("Ledger head anchor is unreadable or malformed")
    return {"block_index": idx, "block_hash": bh, "pending": pending, "updated_at": doc.get("updated_at")}


def _fsync_dir(path) -> None:
    if os.name == "nt":
        return
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_head_anchor(block_index: int, block_hash: str, pending: Optional[Dict[str, Any]] = None) -> None:
    path = config.ledger_head_path()
    tmp = path.with_name(path.name + ".tmp")
    data = json.dumps({
        "format": ANCHOR_FORMAT,
        "version": ANCHOR_VERSION,
        "block_index": block_index,
        "block_hash": block_hash,
        "pending": pending,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    for attempt in range(50):
        try:
            os.replace(tmp, path)
            break
        except PermissionError:
            if attempt == 49:
                raise
            time.sleep(0.02)
    _fsync_dir(path.parent)


def _tail(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT * FROM ledger_blocks ORDER BY block_index DESC LIMIT 1"
    ).fetchone()


def _anchor_head(anchor: Optional[Dict[str, Any]]):
    if anchor is None:
        return 0, GENESIS_HASH
    return anchor["block_index"], anchor["block_hash"]


def _matches(tail, index: int, block_hash: str) -> bool:
    if tail is None:
        return index == 0 and block_hash == GENESIS_HASH
    return tail["block_index"] == index and tail["block_hash"] == block_hash


def reconcile_head_anchor() -> Dict[str, Any]:
    """
    Brings the anchor in line with a committed-but-unanchored tail block, or refuses.
    Returns {"action": "none"|"cleared_stale_intent"|"rolled_forward", ...}.
    Raises LedgerError on any other disagreement (truncation / rollback / tampering).
    """
    with writer_lock():
        anchor = read_head_anchor()
        conn = get_connection()
        try:
            tail = _tail(conn)
        finally:
            conn.close()
        head_index, head_hash = _anchor_head(anchor)
        pending = anchor["pending"] if anchor else None

        if _matches(tail, head_index, head_hash):
            if pending is None:
                return {"action": "none"}
            _write_head_anchor(head_index, head_hash, None)
            return {"action": "cleared_stale_intent", "block_index": head_index}

        if pending is not None and tail is not None and tail["block_index"] == pending["block_index"] \
                and tail["block_hash"] == pending["block_hash"] and tail["previous_hash"] == head_hash:
            from app.ledger.verify import verify_single_block
            problem = verify_single_block(tail)
            if problem:
                raise LedgerError(f"Committed tail block #{tail['block_index']} matches the write-ahead intent "
                                  f"but fails verification ({problem}); refusing to roll forward")
            _write_head_anchor(tail["block_index"], tail["block_hash"], None)
            return {"action": "rolled_forward", "block_index": tail["block_index"]}

        found = tail["block_index"] if tail is not None else 0
        raise LedgerError(f"Ledger tail (Block #{found}) does not match head anchor (Block #{head_index}): "
                          "truncation, rollback or unanchored writes; refusing to append")


# ------------------------------------------------------------- transactions

@contextmanager
def ledger_transaction(conn: sqlite3.Connection):
    """
    Database transaction that may append exactly one ledger block. Callers assign the
    appended block to state["block"]. The write-ahead intent is fsynced before COMMIT
    and the head anchor is advanced after COMMIT.
    """
    with writer_lock():
        reconcile_head_anchor()
        state: Dict[str, Any] = {"block": None}
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield state
            block = state["block"]
            if block is not None:
                head_index, head_hash = _anchor_head(read_head_anchor())
                if block["block_index"] != head_index + 1 or block["previous_hash"] != head_hash:
                    raise LedgerError("Appended block does not extend the anchored head")
                _write_head_anchor(head_index, head_hash, {"block_index": block["block_index"],
                                                           "block_hash": block["block_hash"],
                                                           "previous_hash": block["previous_hash"]})
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        if state["block"] is not None:
            try:
                _write_head_anchor(state["block"]["block_index"], state["block"]["block_hash"], None)
            except OSError:
                # The fsynced intent lets the next writer roll the anchor forward safely.
                pass


def commit_event(event_type: str, record: Dict[str, Any], signature: str, signer_id: str,
                 conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Appends a signed record as a new block. When `conn` is supplied the caller must be
    inside ledger_transaction(conn) and store the returned block in state["block"].
    """
    if event_type not in EVENT_SIGNER_ROLE:
        raise LedgerError(f"Unknown ledger event type {event_type}")
    if record.get("record_type") != EVENT_RECORD_TYPE[event_type]:
        raise LedgerError(f"Record type does not match event {event_type}")
    if record.get(SIGNER_FIELD[EVENT_SIGNER_ROLE[event_type]]) != signer_id:
        raise LedgerError("Record signer field does not match signer_id")

    canonical_bytes = canonicalize_json(record)
    record_hash = hashlib.sha256(canonical_bytes).hexdigest()
    canonical_str = canonical_bytes.decode("utf-8")

    def _append(c: sqlite3.Connection) -> Dict[str, Any]:
        last = _tail(c)
        head_index, head_hash = _anchor_head(read_head_anchor())
        if not _matches(last, head_index, head_hash):
            raise LedgerError("Ledger tail does not match head anchor: refusing to append")
        block_index = head_index + 1
        previous_hash = head_hash
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
    return dsa_sign(sk, canonicalize_json(record), context=record_context(record)).hex()


def get_all_blocks():
    """Retrieve all ledger blocks ordered by index."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM ledger_blocks ORDER BY block_index ASC").fetchall()
    finally:
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
