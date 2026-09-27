"""
Operational audit trail for SIH26237.
Records security-relevant events (who did what, outcome) in the audit_events table
and the Python log. This trail is operational telemetry; it is NOT hash-chained.
Provenance evidence lives in the tamper-evident ledger.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("sih26237.audit")

# Keys whose values must never reach the audit trail or logs.
_FORBIDDEN_KEY_FRAGMENTS = ("password", "passphrase", "private", "secret", "cek", "mlkem_dk", "mldsa_sk", "session_token")


def _sanitize(details: dict) -> dict:
    clean = {}
    for key, value in details.items():
        lowered = key.lower()
        if any(fragment in lowered for fragment in _FORBIDDEN_KEY_FRAGMENTS):
            clean[key] = "[REDACTED]"
        elif isinstance(value, (bytes, bytearray)):
            clean[key] = f"[{len(value)} bytes omitted]"
        else:
            clean[key] = value
    return clean


def record_audit(event: str, principal_id: Optional[str], outcome: str = "SUCCESS", **details: Any) -> None:
    """Best-effort audit write. Failure to audit is logged but never turns a denial into success."""
    from app.database.connection import get_connection

    safe = _sanitize(details)
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info("%s principal=%s outcome=%s details=%s", event, principal_id, outcome, safe)
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO audit_events (timestamp, event, principal_id, outcome, details) VALUES (?, ?, ?, ?, ?)",
            (timestamp, event, principal_id, outcome, json.dumps(safe, sort_keys=True, default=str)),
        )
        conn.close()
    except Exception:
        logger.exception("Failed to persist audit event %s", event)


def list_audit_events(limit: int = 200) -> list:
    from app.database.connection import get_connection

    conn = get_connection()
    rows = conn.execute(
        "SELECT timestamp, event, principal_id, outcome, details FROM audit_events ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "timestamp": r["timestamp"],
            "event": r["event"],
            "principal_id": r["principal_id"],
            "outcome": r["outcome"],
            "details": json.loads(r["details"]),
        }
        for r in rows
    ]
