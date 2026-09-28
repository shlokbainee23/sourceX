"""
Runtime configuration for SIH26237.
Data locations come from environment variables so tests and demos can run against
isolated data directories without touching the operational store. The installation
trust anchor (authority pin, witness pins) can be redirected only in explicit
development/test mode (SIH_DEV_MODE=1).
"""

import os
from pathlib import Path

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_TRUST_ANCHOR_DIR = _DEFAULT_DATA_DIR.parent.parent / "trust_anchor"


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


def dev_mode_enabled() -> bool:
    """Development/test mode: permits redirecting the installation trust anchor."""
    return os.environ.get("SIH_DEV_MODE", "0") == "1"


def _anchor_file(env_name: str, default_name: str) -> tuple:
    override = os.environ.get(env_name)
    if override:
        return Path(override).resolve(), True
    return (_DEFAULT_TRUST_ANCHOR_DIR / default_name).resolve(), False


def authority_pin_location() -> tuple:
    """(path, overridden). The pinned authority ML-DSA fingerprint lives OUTSIDE the data
    directory so that whoever controls the data store cannot replace the trust anchor.
    Deployments should place trust_anchor/ on read-only media."""
    return _anchor_file("SIH_AUTHORITY_PIN_FILE", "authority.pin")


def authority_pin_path() -> Path:
    return authority_pin_location()[0]


def witness_pin_location() -> tuple:
    """(path, overridden) of the pinned independent witness keys and threshold."""
    return _anchor_file("SIH_WITNESS_PIN_FILE", "witnesses.json")


def demo_mode_enabled() -> bool:
    """Tamper simulation and environment reset are only reachable in demo mode."""
    return os.environ.get("SIH_DEMO_MODE", "0") == "1"


SESSION_TTL_SECONDS = int(os.environ.get("SIH_SESSION_TTL_SECONDS", "1800"))
MAX_UPLOAD_BYTES = int(os.environ.get("SIH_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.environ.get("SIH_MAX_PDF_PAGES", "200"))
PDF_WORKER_TIMEOUT_SECONDS = int(os.environ.get("SIH_PDF_WORKER_TIMEOUT", "120"))
PDF_WORKER_MEMORY_MB = int(os.environ.get("SIH_PDF_WORKER_MEMORY_MB", "1024"))
DELIVERY_TTL_SECONDS = int(os.environ.get("SIH_DELIVERY_TTL_SECONDS", "900"))
MIN_PASSPHRASE_LENGTH = 12
LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 60
LOGIN_LOCKOUT_MAX_SECONDS = 900

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "SIH_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
