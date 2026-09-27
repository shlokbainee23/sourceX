"""
Runtime configuration for SIH26237.
All values come from environment variables so tests and demos can run against
isolated data directories without touching the operational store.
"""

import os
from pathlib import Path

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def data_dir() -> Path:
    path = Path(os.environ.get("SIH_DATA_DIR", str(_DEFAULT_DATA_DIR))).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir() -> Path:
    path = data_dir() / "documents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def keystore_dir() -> Path:
    path = data_dir() / "keystore"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "sih26237.sqlite"


def ledger_head_path() -> Path:
    return data_dir() / "ledger_head.json"


def authority_pin_path() -> Path:
    """The pinned authority ML-DSA fingerprint lives OUTSIDE the data directory so that
    whoever controls the data store cannot silently replace the trust anchor. Deployments
    should place it on read-only media."""
    default = _DEFAULT_DATA_DIR.parent.parent / "trust_anchor" / "authority.pin"
    return Path(os.environ.get("SIH_AUTHORITY_PIN_FILE", str(default))).resolve()


def demo_mode_enabled() -> bool:
    """Tamper simulation and environment reset are only reachable in demo mode."""
    return os.environ.get("SIH_DEMO_MODE", "0") == "1"


SESSION_TTL_SECONDS = int(os.environ.get("SIH_SESSION_TTL_SECONDS", "1800"))
MAX_UPLOAD_BYTES = int(os.environ.get("SIH_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MIN_PASSPHRASE_LENGTH = 12
LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 60

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "SIH_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
