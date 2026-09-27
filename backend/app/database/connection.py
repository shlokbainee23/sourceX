"""
Database connection and schema initialization for SIH26237.
Uses SQLite for offline local storage. Evidence tables (ledger_blocks, sessions)
are protected by triggers that reject UPDATE/DELETE during normal operation.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app import config

SCHEMA_VERSION = 3

# Evidence tables are append-only; these triggers make the database itself reject
# mutation from application code. They do not stop an attacker with raw file access,
# which is why the ledger is also hash-chained, signed and anchored.
APPEND_ONLY_TRIGGERS = {
    "ledger_no_update": "CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger_blocks "
                        "BEGIN SELECT RAISE(ABORT, 'ledger_blocks is append-only'); END;",
    "ledger_no_delete": "CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger_blocks "
                        "BEGIN SELECT RAISE(ABORT, 'ledger_blocks is append-only'); END;",
    "sessions_no_update": "CREATE TRIGGER IF NOT EXISTS sessions_no_update BEFORE UPDATE ON sessions "
                          "BEGIN SELECT RAISE(ABORT, 'sessions is append-only'); END;",
    "sessions_no_delete": "CREATE TRIGGER IF NOT EXISTS sessions_no_delete BEFORE DELETE ON sessions "
                          "BEGIN SELECT RAISE(ABORT, 'sessions is append-only'); END;",
}

# The audit trail and imported trust manifests are never cleared, including by demo
# reset and tamper simulation, so these triggers are not dropped by any code path.
PERMANENT_TRIGGERS = {
    "audit_no_update": "CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events "
                       "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;",
    "audit_no_delete": "CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events "
                       "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;",
    "trust_no_update": "CREATE TRIGGER IF NOT EXISTS trust_no_update BEFORE UPDATE ON trust_manifests "
                       "BEGIN SELECT RAISE(ABORT, 'trust_manifests is append-only'); END;",
    "trust_no_delete": "CREATE TRIGGER IF NOT EXISTS trust_no_delete BEFORE DELETE ON trust_manifests "
                       "BEGIN SELECT RAISE(ABORT, 'trust_manifests is append-only'); END;",
}


def get_db_path() -> Path:
    return config.db_path()


def get_connection() -> sqlite3.Connection:
    # isolation_level=None: transactions are managed explicitly via transaction().
    conn = sqlite3.connect(get_db_path(), isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """BEGIN IMMEDIATE serializes writers so ledger block indices cannot race."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def _drop_legacy_evidence(cursor: sqlite3.Cursor):
    """Schema v1 evidence (unsigned authority blocks, pre-watermark hashes) cannot be
    verified under v2 rules, so it is discarded. Recipient public keys are preserved."""
    for trig in APPEND_ONLY_TRIGGERS:
        cursor.execute(f"DROP TRIGGER IF EXISTS {trig}")
    for table in ("sessions", "encrypted_packages", "documents", "ledger_blocks"):
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    head = config.ledger_head_path()
    if head.exists():
        head.unlink()
    _clear_document_vault()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    version = cursor.execute("PRAGMA user_version").fetchone()[0]
    if version < 2:
        _drop_legacy_evidence(cursor)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS principals (
        principal_id TEXT PRIMARY KEY,
        role TEXT NOT NULL CHECK (role IN ('AUTHORITY','RECIPIENT','INVESTIGATOR','AUDITOR')),
        name TEXT NOT NULL,
        mldsa_public_key TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        mlkem_public_key TEXT NOT NULL,
        mldsa_public_key TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        original_hash TEXT NOT NULL,
        classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL',
        owner TEXT NOT NULL,
        encrypted_path TEXT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'REGISTERED' CHECK (status IN ('REGISTERED','ENCRYPTED'))
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS encrypted_packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id TEXT NOT NULL,
        recipient_id TEXT NOT NULL,
        kem_ciphertext TEXT NOT NULL,
        wrapped_cek TEXT NOT NULL,
        wrap_nonce TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(document_id),
        FOREIGN KEY(recipient_id) REFERENCES recipients(recipient_id),
        UNIQUE(document_id, recipient_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        document_id TEXT NOT NULL,
        recipient_id TEXT NOT NULL,
        watermark_token TEXT UNIQUE NOT NULL,
        watermark_token_hash TEXT NOT NULL,
        source_document_hash TEXT NOT NULL,
        delivered_document_hash TEXT NOT NULL,
        delivered_filename TEXT NOT NULL,
        signature TEXT NOT NULL,
        block_index INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'COMPLETED',
        FOREIGN KEY(document_id) REFERENCES documents(document_id),
        FOREIGN KEY(recipient_id) REFERENCES recipients(recipient_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledger_blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        block_index INTEGER UNIQUE NOT NULL,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        previous_hash TEXT NOT NULL,
        record_hash TEXT NOT NULL,
        canonical_record TEXT NOT NULL,
        signature TEXT NOT NULL,
        signer_id TEXT NOT NULL,
        block_hash TEXT UNIQUE NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event TEXT NOT NULL,
        principal_id TEXT,
        outcome TEXT NOT NULL,
        details TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trust_manifests (
        version INTEGER PRIMARY KEY,
        manifest_sha256 TEXT UNIQUE NOT NULL,
        package TEXT NOT NULL,
        issuer_fingerprint TEXT NOT NULL,
        issued_at TEXT NOT NULL,
        source_label TEXT NOT NULL,
        imported_by TEXT,
        imported_at TEXT NOT NULL
    );
    """)

    for ddl in list(APPEND_ONLY_TRIGGERS.values()) + list(PERMANENT_TRIGGERS.values()):
        cursor.execute(ddl)

    cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.close()


def _clear_document_vault():
    docs_dir = config.documents_dir()
    for f in docs_dir.iterdir():
        if f.is_file() and f.name != ".gitkeep":
            try:
                f.unlink()
            except OSError:
                pass


def drop_append_only_triggers(conn: sqlite3.Connection):
    """Only for demo reset and tamper simulation; init_db() restores the triggers."""
    for trig in APPEND_ONLY_TRIGGERS:
        conn.execute(f"DROP TRIGGER IF EXISTS {trig}")


def reset_test_database():
    """
    Resets the local test/demo environment:
    - Clears documents, encrypted_packages, sessions, ledger_blocks and the ledger head anchor.
    - Preserves principals, recipient public keys and encrypted keystores.
    - Preserves the operational audit trail.
    """
    init_db()
    conn = get_connection()
    drop_append_only_triggers(conn)
    with transaction(conn):
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM encrypted_packages")
        conn.execute("DELETE FROM documents")
        conn.execute("DELETE FROM ledger_blocks")
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('sessions', 'encrypted_packages', 'documents', 'ledger_blocks')"
        )
    conn.execute("VACUUM")
    conn.close()

    head = config.ledger_head_path()
    if head.exists():
        head.unlink()
    _clear_document_vault()
    init_db()
    return True


if __name__ == "__main__":
    init_db()
    print("Database initialized at", get_db_path())
