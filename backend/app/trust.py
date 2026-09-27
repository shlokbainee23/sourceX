"""
Signed trust-anchor manifest: the local trusted identity store for SIH26237.

The only authoritative external data this system needs is the issuing authority's
statement of WHO its principals are and WHICH public keys belong to them. That
statement enters the air-gapped system as a signed data package and passes through:

  package bytes -> size/JSON checks -> strict schema -> pinned authority fingerprint
  -> ML-DSA-44 signature -> version monotonicity / revocation monotonicity
  -> append-only trust_manifests table (+ authority-signed TRUST_MANIFEST_IMPORTED ledger block)

Source authority (the manifest is signed by the pinned authority key) is separate from
local data integrity (every stored package is re-verified on every read, and the
ledger records each accepted version so deleting a newer version is detectable).

The pin (SHA-256 of the authority ML-DSA public key) is read from a file outside the
data directory. Without a valid pin, nothing is trusted: attribution fails closed.
Encryption, decryption and ledger verification do not depend on this module.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import config
from app.crypto.pqc_dsa import PUBLIC_KEY_SIZE, SIGNATURE_SIZE, dsa_sign, dsa_verify
from app.database.connection import get_connection
from app.ledger.blockchain import commit_event, ledger_transaction, sign_record
from app.ledger.canonical import CanonicalizationError, canonicalize_json
from app.validation import is_hex64, is_valid_id

MANIFEST_TYPE = "SIH26237_TRUST_MANIFEST"
MANIFEST_SCHEMA_VERSION = 1
MAX_PACKAGE_BYTES = 1024 * 1024
MAX_PRINCIPALS = 5000
ROLES = ("AUTHORITY", "RECIPIENT", "INVESTIGATOR", "AUDITOR")
KEYED_ROLES = ("AUTHORITY", "RECIPIENT")

MALFORMED = "MALFORMED"
SCHEMA_INVALID = "SCHEMA_INVALID"
UNPINNED = "UNPINNED"
PIN_MISMATCH = "PIN_MISMATCH"
SIGNATURE_INVALID = "SIGNATURE_INVALID"
STALE = "STALE"
CONFLICT = "CONFLICT"
CORRUPTED = "CORRUPTED"
NOT_AVAILABLE = "NOT_AVAILABLE"
REGISTRY_DRIFT = "REGISTRY_DRIFT"

IMPORTED = "IMPORTED"
ALREADY_IMPORTED = "ALREADY_IMPORTED"

_TOP_KEYS = {"manifest_type", "schema_version", "version", "issued_at", "issuer", "source", "principals"}
_ISSUER_KEYS = {"principal_id", "organization", "mldsa_public_key"}
_SOURCE_KEYS = {"publisher", "description"}
_ENTRY_KEYS = {"principal_id", "role", "name", "mldsa_pk_sha256", "mlkem_pk_sha256", "status", "revoked_at"}


class TrustError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------- pin

def authority_pin() -> str:
    path = config.authority_pin_path()
    if not path.is_file():
        raise TrustError(UNPINNED, "No authority trust anchor is pinned")
    pin = path.read_text(encoding="utf-8").strip()
    if not is_hex64(pin):
        raise TrustError(UNPINNED, "Pinned authority trust anchor is malformed")
    return pin


def write_authority_pin(fingerprint: str) -> bool:
    """Writes the pin if absent. Returns True if written. Never replaces a different pin."""
    if not is_hex64(fingerprint):
        raise TrustError(SCHEMA_INVALID, "Fingerprint must be 64 lowercase hex characters")
    path = config.authority_pin_path()
    if path.exists():
        existing = path.read_text(encoding="utf-8").strip()
        if existing != fingerprint:
            raise TrustError(PIN_MISMATCH, "A different authority trust anchor is already pinned")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fingerprint + "\n", encoding="utf-8")
    return True


# -------------------------------------------------------------------------- schema

def _is_text(value: Any, max_len: int = 256) -> bool:
    return isinstance(value, str) and 0 < len(value) <= max_len


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_ts(value: Any) -> Optional[datetime]:
    if not _is_text(value, 64):
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    return ts if ts.tzinfo is not None else None


def _schema(cond: bool, message: str) -> None:
    if not cond:
        raise TrustError(SCHEMA_INVALID, message)


def validate_manifest_schema(m: Any) -> None:
    _schema(isinstance(m, dict) and set(m) == _TOP_KEYS, "Manifest fields do not match the schema")
    _schema(m["manifest_type"] == MANIFEST_TYPE, "Unknown manifest type")
    _schema(_is_int(m["schema_version"]) and m["schema_version"] == MANIFEST_SCHEMA_VERSION, "Unsupported schema version")
    _schema(_is_int(m["version"]) and m["version"] >= 1, "Manifest version must be a positive integer")
    _schema(_parse_ts(m["issued_at"]) is not None, "issued_at must be an ISO-8601 timestamp with timezone")

    issuer = m["issuer"]
    _schema(isinstance(issuer, dict) and set(issuer) == _ISSUER_KEYS, "Issuer fields do not match the schema")
    _schema(is_valid_id(issuer["principal_id"]), "Invalid issuer principal_id")
    _schema(_is_text(issuer["organization"]), "Invalid issuer organization")
    pk = issuer["mldsa_public_key"]
    _schema(isinstance(pk, str) and len(pk) == 2 * PUBLIC_KEY_SIZE and all(c in "0123456789abcdef" for c in pk),
            "Issuer ML-DSA-44 public key must be lowercase hex of the correct length")

    source = m["source"]
    _schema(isinstance(source, dict) and set(source) == _SOURCE_KEYS, "Source fields do not match the schema")
    _schema(_is_text(source["publisher"]) and _is_text(source["description"], 1024), "Invalid source provenance")

    entries = m["principals"]
    _schema(isinstance(entries, list) and 0 < len(entries) <= MAX_PRINCIPALS, "principals must be a non-empty list")
    seen = set()
    for e in entries:
        _schema(isinstance(e, dict) and set(e) == _ENTRY_KEYS, "Principal entry fields do not match the schema")
        pid = e["principal_id"]
        _schema(is_valid_id(pid) and pid not in seen, f"Invalid or duplicate principal_id {pid!r}")
        seen.add(pid)
        _schema(e["role"] in ROLES, f"Invalid role for {pid}")
        _schema(_is_text(e["name"]), f"Invalid name for {pid}")
        if e["role"] in KEYED_ROLES:
            _schema(is_hex64(e["mldsa_pk_sha256"]), f"{pid} requires an ML-DSA key fingerprint")
        else:
            _schema(e["mldsa_pk_sha256"] is None, f"{pid} must not carry an ML-DSA key fingerprint")
        if e["role"] == "RECIPIENT":
            _schema(is_hex64(e["mlkem_pk_sha256"]), f"{pid} requires an ML-KEM key fingerprint")
        else:
            _schema(e["mlkem_pk_sha256"] is None, f"{pid} must not carry an ML-KEM key fingerprint")
        _schema(e["status"] in ("ACTIVE", "REVOKED"), f"Invalid status for {pid}")
        if e["status"] == "ACTIVE":
            _schema(e["revoked_at"] is None, f"Active principal {pid} must not have revoked_at")
        else:
            _schema(_parse_ts(e["revoked_at"]) is not None, f"Revoked principal {pid} requires revoked_at")

    issuer_entry = next((e for e in entries if e["principal_id"] == issuer["principal_id"]), None)
    _schema(issuer_entry is not None and issuer_entry["role"] == "AUTHORITY" and issuer_entry["status"] == "ACTIVE",
            "Issuer must be listed as an ACTIVE AUTHORITY")
    _schema(issuer_entry["mldsa_pk_sha256"] == sha256_hex(bytes.fromhex(pk)),
            "Issuer entry fingerprint does not match the issuer public key")


def _no_duplicate_keys(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError(f"duplicate key {k!r}")
        obj[k] = v
    return obj


def _reject_float(_value):
    raise ValueError("floats are not permitted")


def verify_package(raw: bytes) -> Dict[str, Any]:
    """Full validation pipeline for one package. Raises TrustError; never returns partial trust."""
    if not isinstance(raw, (bytes, bytearray)) or len(raw) == 0 or len(raw) > MAX_PACKAGE_BYTES:
        raise TrustError(MALFORMED, "Package is empty or exceeds the size limit")
    try:
        pkg = json.loads(bytes(raw).decode("utf-8"), object_pairs_hook=_no_duplicate_keys, parse_float=_reject_float)
    except (UnicodeDecodeError, ValueError):
        raise TrustError(MALFORMED, "Package is not valid UTF-8 JSON")
    if not isinstance(pkg, dict) or set(pkg) != {"manifest", "signature"}:
        raise TrustError(MALFORMED, "Package must contain exactly 'manifest' and 'signature'")
    sig_hex = pkg["signature"]
    if not (isinstance(sig_hex, str) and len(sig_hex) == 2 * SIGNATURE_SIZE
            and all(c in "0123456789abcdef" for c in sig_hex)):
        raise TrustError(MALFORMED, "Signature must be lowercase hex of the ML-DSA-44 signature length")

    manifest = pkg["manifest"]
    validate_manifest_schema(manifest)
    try:
        manifest_bytes = canonicalize_json(manifest)
    except CanonicalizationError:
        raise TrustError(SCHEMA_INVALID, "Manifest is not canonicalizable")

    pin = authority_pin()
    issuer_pk = bytes.fromhex(manifest["issuer"]["mldsa_public_key"])
    fingerprint = sha256_hex(issuer_pk)
    if not hmac.compare_digest(fingerprint, pin):
        raise TrustError(PIN_MISMATCH, "Manifest issuer key does not match the pinned authority trust anchor")
    if not dsa_verify(issuer_pk, manifest_bytes, bytes.fromhex(sig_hex)):
        raise TrustError(SIGNATURE_INVALID, "Manifest ML-DSA-44 signature is invalid")

    return {
        "manifest": manifest,
        "signature": sig_hex,
        "manifest_sha256": sha256_hex(manifest_bytes),
        "issuer_fingerprint": fingerprint,
        "package": canonicalize_json({"manifest": manifest, "signature": sig_hex}).decode("utf-8"),
    }


# ------------------------------------------------------------------ local store

def _verify_stored(row) -> Dict[str, Any]:
    try:
        verified = verify_package(row["package"].encode("utf-8"))
    except TrustError as exc:
        if exc.code in (UNPINNED, PIN_MISMATCH):
            raise
        raise TrustError(CORRUPTED, f"Stored trust manifest v{row['version']} failed re-verification ({exc.code})")
    if verified["manifest_sha256"] != row["manifest_sha256"] or verified["manifest"]["version"] != row["version"] \
            or verified["issuer_fingerprint"] != row["issuer_fingerprint"]:
        raise TrustError(CORRUPTED, f"Stored trust manifest v{row['version']} does not match its recorded provenance")
    verified.update({"source_label": row["source_label"], "imported_by": row["imported_by"],
                     "imported_at": row["imported_at"], "version": row["version"]})
    return verified


def _ledger_manifest_records(conn) -> List[dict]:
    rows = conn.execute(
        "SELECT canonical_record FROM ledger_blocks WHERE event_type = 'TRUST_MANIFEST_IMPORTED' ORDER BY block_index"
    ).fetchall()
    return [json.loads(r["canonical_record"]) for r in rows]


def current_manifest() -> Dict[str, Any]:
    """Latest manifest, re-verified from storage and cross-checked against the ledger."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM trust_manifests ORDER BY version DESC LIMIT 1").fetchone()
        ledger_records = _ledger_manifest_records(conn)
        stored = {r["version"]: r["manifest_sha256"] for r in
                  conn.execute("SELECT version, manifest_sha256 FROM trust_manifests").fetchall()}
    finally:
        conn.close()
    if row is None:
        raise TrustError(NOT_AVAILABLE, "No trust manifest has been imported")
    verified = _verify_stored(row)
    for rec in ledger_records:
        if stored.get(rec.get("manifest_version")) != rec.get("manifest_sha256"):
            raise TrustError(CORRUPTED, f"Ledger records trust manifest v{rec.get('manifest_version')} "
                                        "which is missing or different in the local store (rollback detected)")
    return verified


def list_manifests() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT version, manifest_sha256, issuer_fingerprint, issued_at, source_label, imported_by, "
                            "imported_at FROM trust_manifests ORDER BY version").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _check_monotonic(previous: Optional[dict], manifest: dict) -> None:
    if previous is None:
        return
    new_entries = {e["principal_id"]: e for e in manifest["principals"]}
    for old in previous["manifest"]["principals"]:
        new = new_entries.get(old["principal_id"])
        if new is None:
            raise TrustError(CONFLICT, f"Principal {old['principal_id']} was removed; manifests may only add or revoke")
        if (new["mldsa_pk_sha256"], new["mlkem_pk_sha256"], new["role"]) != \
                (old["mldsa_pk_sha256"], old["mlkem_pk_sha256"], old["role"]):
            raise TrustError(CONFLICT, f"Key or role change for {old['principal_id']} is not permitted")
        if old["status"] == "REVOKED" and (new["status"] != "REVOKED" or new["revoked_at"] != old["revoked_at"]):
            raise TrustError(CONFLICT, f"Revocation of {old['principal_id']} cannot be undone")


def import_package(raw: bytes, source_label: str, authority_id: str, authority_sk: bytes) -> Dict[str, Any]:
    """
    Imports a signed manifest package into the local trust store. The importing
    authority countersigns a TRUST_MANIFEST_IMPORTED ledger block in the same transaction.
    """
    if not _is_text(source_label, 256):
        raise TrustError(SCHEMA_INVALID, "source_label is required")
    verified = verify_package(raw)
    manifest = verified["manifest"]
    version = manifest["version"]

    conn = get_connection()
    try:
        with ledger_transaction(conn) as tx:
            same = conn.execute("SELECT manifest_sha256 FROM trust_manifests WHERE version = ?", (version,)).fetchone()
            if same is not None:
                if same["manifest_sha256"] == verified["manifest_sha256"]:
                    return {"status": ALREADY_IMPORTED, "version": version, "manifest_sha256": verified["manifest_sha256"]}
                raise TrustError(CONFLICT, f"A different trust manifest v{version} is already imported")
            latest = conn.execute("SELECT * FROM trust_manifests ORDER BY version DESC LIMIT 1").fetchone()
            previous = _verify_stored(latest) if latest is not None else None
            if previous is not None and version < previous["version"]:
                raise TrustError(STALE, f"Manifest v{version} is older than the imported v{previous['version']}")
            _check_monotonic(previous, manifest)

            imported_at = _now()
            conn.execute(
                "INSERT INTO trust_manifests (version, manifest_sha256, package, issuer_fingerprint, issued_at, "
                "source_label, imported_by, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (version, verified["manifest_sha256"], verified["package"], verified["issuer_fingerprint"],
                 manifest["issued_at"], source_label, authority_id, imported_at),
            )
            revoked = [e["principal_id"] for e in manifest["principals"] if e["status"] == "REVOKED"]
            for pid in revoked:
                conn.execute("UPDATE principals SET status = 'REVOKED' WHERE principal_id = ?", (pid,))
                conn.execute("UPDATE recipients SET status = 'REVOKED' WHERE recipient_id = ?", (pid,))
            record = {
                "record_type": "TRUST_MANIFEST",
                "record_version": "2.0",
                "authority_id": authority_id,
                "manifest_version": version,
                "manifest_sha256": verified["manifest_sha256"],
                "issuer_fingerprint": verified["issuer_fingerprint"],
                "source_label": source_label,
                "timestamp": imported_at,
            }
            tx["block"] = commit_event("TRUST_MANIFEST_IMPORTED", record, sign_record(authority_sk, record),
                                       authority_id, conn=conn)
    finally:
        conn.close()
    return {"status": IMPORTED, "version": version, "manifest_sha256": verified["manifest_sha256"],
            "revoked_principals": revoked, "block_index": tx["block"]["block_index"]}


# ------------------------------------------------------------------ issuing

def _registry_entries(conn) -> Dict[str, dict]:
    rows = conn.execute(
        "SELECT p.principal_id, p.role, p.name, p.mldsa_public_key, r.mlkem_public_key "
        "FROM principals p LEFT JOIN recipients r ON r.recipient_id = p.principal_id ORDER BY p.principal_id"
    ).fetchall()
    out = {}
    for r in rows:
        out[r["principal_id"]] = {
            "principal_id": r["principal_id"],
            "role": r["role"],
            "name": r["name"],
            "mldsa_pk_sha256": sha256_hex(bytes.fromhex(r["mldsa_public_key"])) if r["role"] in KEYED_ROLES else None,
            "mlkem_pk_sha256": sha256_hex(bytes.fromhex(r["mlkem_public_key"])) if r["role"] == "RECIPIENT" else None,
            "status": "ACTIVE",
            "revoked_at": None,
        }
    return out


def build_next_manifest(authority_id: str, authority_pk: bytes, organization: str, publisher: str,
                        description: str, revoke: Optional[List[str]] = None) -> dict:
    """
    Builds the next manifest version from the local registry. Refuses if a registry key
    differs from the one already attested (registry substitution must not be laundered
    into a newly signed manifest).
    """
    try:
        previous = current_manifest()
    except TrustError as exc:
        if exc.code != NOT_AVAILABLE:
            raise
        previous = None
    conn = get_connection()
    try:
        entries = _registry_entries(conn)
    finally:
        conn.close()

    if previous is not None:
        for old in previous["manifest"]["principals"]:
            cur = entries.get(old["principal_id"])
            if cur is None or (cur["mldsa_pk_sha256"], cur["mlkem_pk_sha256"], cur["role"]) != \
                    (old["mldsa_pk_sha256"], old["mlkem_pk_sha256"], old["role"]):
                raise TrustError(REGISTRY_DRIFT, f"Registry keys for {old['principal_id']} differ from the attested manifest")
            if old["status"] == "REVOKED":
                cur["status"], cur["revoked_at"] = "REVOKED", old["revoked_at"]

    now = _now()
    for pid in revoke or []:
        entry = entries.get(pid)
        if entry is None:
            raise TrustError(SCHEMA_INVALID, f"Unknown principal {pid}")
        if pid == authority_id:
            raise TrustError(SCHEMA_INVALID, "The issuing authority cannot revoke itself")
        if entry["status"] != "REVOKED":
            entry["status"], entry["revoked_at"] = "REVOKED", now

    return {
        "manifest_type": MANIFEST_TYPE,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "version": (previous["version"] + 1) if previous else 1,
        "issued_at": now,
        "issuer": {"principal_id": authority_id, "organization": organization, "mldsa_public_key": authority_pk.hex()},
        "source": {"publisher": publisher, "description": description},
        "principals": [entries[k] for k in sorted(entries)],
    }


def sign_manifest(manifest: dict, authority_sk: bytes) -> bytes:
    validate_manifest_schema(manifest)
    sig = dsa_sign(authority_sk, canonicalize_json(manifest))
    return canonicalize_json({"manifest": manifest, "signature": sig.hex()})


DEFAULT_ORGANIZATION = "WESEE, Indian Navy (issuing authority)"
DEFAULT_PUBLISHER = "WESEE HQ identity provisioning (synthetic demo identities)"


def issue_and_import(authority_id: str, authority_pk: bytes, authority_sk: bytes, source_label: str,
                     description: str, revoke: Optional[List[str]] = None) -> Dict[str, Any]:
    manifest = build_next_manifest(authority_id, authority_pk, DEFAULT_ORGANIZATION, DEFAULT_PUBLISHER,
                                   description, revoke)
    return import_package(sign_manifest(manifest, authority_sk), source_label, authority_id, authority_sk)


# ------------------------------------------------------------ verification

def verify_principal_key(principal_id: str, role: str, mldsa_pk: bytes, event_timestamp: str) -> Dict[str, Any]:
    """
    Is `mldsa_pk` the key the pinned authority attested for `principal_id` in `role`,
    and was it not revoked at `event_timestamp`? Never raises; returns trusted=False
    with a reason on any failure.
    """
    result = {"trusted": False, "reason": None, "manifest_version": None, "manifest_sha256": None,
              "authority_pin": None}
    try:
        result["authority_pin"] = authority_pin()
        m = current_manifest()
        result["manifest_version"], result["manifest_sha256"] = m["version"], m["manifest_sha256"]
        entry = next((e for e in m["manifest"]["principals"] if e["principal_id"] == principal_id), None)
        if entry is None:
            result["reason"] = f"{principal_id} is not listed in trust manifest v{m['version']}"
        elif entry["role"] != role:
            result["reason"] = f"{principal_id} is attested as {entry['role']}, not {role}"
        elif not hmac.compare_digest(entry["mldsa_pk_sha256"] or "", sha256_hex(mldsa_pk)):
            result["reason"] = f"Registered key for {principal_id} does not match the key attested by the authority"
        elif entry["status"] == "REVOKED" and (
                (_parse_ts(event_timestamp) is None) or _parse_ts(event_timestamp) >= _parse_ts(entry["revoked_at"])):
            result["reason"] = f"{principal_id}'s key was revoked at {entry['revoked_at']}, before this event"
        else:
            result["trusted"] = True
    except TrustError as exc:
        result["reason"] = f"Trust store unavailable ({exc.code}): {exc}"
    except Exception as exc:
        result["reason"] = f"Trust verification error ({type(exc).__name__})"
    return result
