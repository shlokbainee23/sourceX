"""
Database connection and schema initialization for SIH26237.
Uses SQLite for offline local storage. Evidence tables (ledger_blocks, sessions)
are protected by triggers that reject UPDATE/DELETE during normal operation.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app import config

SCHEMA_VERSION = 4

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
    # Public key material is immutable once registered; only the operational status may change.
    "keys_no_rekey": "CREATE TRIGGER IF NOT EXISTS keys_no_rekey BEFORE UPDATE OF principal_id, key_id, seq, "
                     "mldsa_public_key, mlkem_public_key, created_at ON principal_keys "
                     "BEGIN SELECT RAISE(ABORT, 'principal_keys key material is immutable'); END;",
    "keys_no_delete": "CREATE TRIGGER IF NOT EXISTS keys_no_delete BEFORE DELETE ON principal_keys "
                      "BEGIN SELECT RAISE(ABORT, 'principal_keys is append-only'); END;",
    "cosig_no_update": "CREATE TRIGGER IF NOT EXISTS cosig_no_update BEFORE UPDATE ON witness_cosignatures "
                       "BEGIN SELECT RAISE(ABORT, 'witness_cosignatures is append-only'); END;",
    "cosig_no_delete": "CREATE TRIGGER IF NOT EXISTS cosig_no_delete BEFORE DELETE ON witness_cosignatures "
                       "BEGIN SELECT RAISE(ABORT, 'witness_cosignatures is append-only'); END;",
    "ckpt_no_update": "CREATE TRIGGER IF NOT EXISTS ckpt_no_update BEFORE UPDATE ON ledger_checkpoints "
                      "BEGIN SELECT RAISE(ABORT, 'ledger_checkpoints is append-only'); END;",
    "ckpt_no_delete": "CREATE TRIGGER IF NOT EXISTS ckpt_no_delete BEFORE DELETE ON ledger_checkpoints "
                      "BEGIN SELECT RAISE(ABORT, 'ledger_checkpoints is append-only'); END;",
    "report_no_update": "CREATE TRIGGER IF NOT EXISTS report_no_update BEFORE UPDATE ON investigation_reports "
                        "BEGIN SELECT RAISE(ABORT, 'investigation_reports is append-only'); END;",
    "report_no_delete": "CREATE TRIGGER IF NOT EXISTS report_no_delete BEFORE DELETE ON investigation_reports "
                        "BEGIN SELECT RAISE(ABORT, 'investigation_reports is append-only'); END;",
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

    _create_v4_tables(cursor)
    for ddl in list(APPEND_ONLY_TRIGGERS.values()) + list(PERMANENT_TRIGGERS.values()):
        cursor.execute(ddl)
    _backfill_principal_keys(cursor)

    cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.close()


def _columns(cursor: sqlite3.Cursor, table: str) -> set:
    return {r[1] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall()}


def _create_v4_tables(cursor: sqlite3.Cursor) -> None:
    """Schema v4 additions. Additive only: no existing evidence is rewritten."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS principal_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        principal_id TEXT NOT NULL,
        key_id TEXT UNIQUE NOT NULL,
        seq INTEGER NOT NULL,
        mldsa_public_key TEXT,
        mlkem_public_key TEXT,
        status TEXT NOT NULL CHECK (status IN ('PENDING','ACTIVE','RETIRED','REJECTED')),
        created_at TEXT NOT NULL,
        UNIQUE(principal_id, seq)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enrollment_codes (
        principal_id TEXT PRIMARY KEY,
        code_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at REAL NOT NULL,
        used_at TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledger_checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin TEXT NOT NULL,
        block_index INTEGER NOT NULL,
        block_hash TEXT NOT NULL,
        checkpoint TEXT NOT NULL,
        checkpoint_sha256 TEXT UNIQUE NOT NULL,
        signature TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS witness_cosignatures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        witness_id TEXT NOT NULL,
        witness_fingerprint TEXT NOT NULL,
        origin TEXT NOT NULL,
        block_index INTEGER NOT NULL,
        block_hash TEXT NOT NULL,
        checkpoint_sha256 TEXT NOT NULL,
        cosignature TEXT NOT NULL,
        imported_by TEXT NOT NULL,
        imported_at TEXT NOT NULL,
        UNIQUE(witness_fingerprint, checkpoint_sha256)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS investigation_reports (
        report_id TEXT PRIMARY KEY,
        report TEXT NOT NULL,
        report_sha256 TEXT UNIQUE NOT NULL,
        signature TEXT,
        signer_key_id TEXT,
        investigator_id TEXT NOT NULL,
        block_index INTEGER,
        created_at TEXT NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS login_failures (
        principal_id TEXT PRIMARY KEY,
        failures INTEGER NOT NULL,
        locked_until REAL NOT NULL
    );
    """)
    session_cols = _columns(cursor, "sessions")
    for col in ("record_version", "signer_key_id", "encryption_record_hash", "package_sha256",
                "source_render_hash", "delivered_render_hash"):
        if col not in session_cols:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT")
    if "recipient_key_id" not in _columns(cursor, "encrypted_packages"):
        cursor.execute("ALTER TABLE encrypted_packages ADD COLUMN recipient_key_id TEXT")
    if "title" not in _columns(cursor, "principals"):
        cursor.execute("ALTER TABLE principals ADD COLUMN title TEXT")


def _backfill_principal_keys(cursor: sqlite3.Cursor) -> None:
    """Principals created before schema v4 get their single existing key registered as '<id>#1'."""
    rows = cursor.execute("""
        SELECT p.principal_id, p.mldsa_public_key, r.mlkem_public_key, p.created_at
        FROM principals p LEFT JOIN recipients r ON r.recipient_id = p.principal_id
        WHERE p.mldsa_public_key IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM principal_keys k WHERE k.principal_id = p.principal_id)
    """).fetchall()
    for pid, dsa_pk, kem_pk, created_at in rows:
        cursor.execute(
            "INSERT INTO principal_keys (principal_id, key_id, seq, mldsa_public_key, mlkem_public_key, status, created_at) "
            "VALUES (?, ?, 1, ?, ?, 'ACTIVE', ?)", (pid, f"{pid}#1", dsa_pk, kem_pk, created_at))


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
        conn.execute("DELETE FROM login_failures")
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('sessions', 'encrypted_packages', 'documents', 'ledger_blocks', 'login_failures')"
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
