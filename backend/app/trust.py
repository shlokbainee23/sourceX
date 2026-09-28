"""
Trust hierarchy for SIH26237.

    installation trust anchor (read-only media, outside the data directory)
        authority.pin    SHA-256 of the authority ML-DSA-44 public key
        witnesses.json   independent witness public keys + cosignature threshold
            |
    signed trust manifest (ML-DSA-44 by the pinned authority, context-separated)
        principals, roles, and each principal's key history:
        key_id, ML-DSA / ML-KEM fingerprints, valid_after_block, retired_after_block,
        revoked_after_block
            |
    key resolver: a public key from the (untrusted) SQLite registry is used for
    encryption, or accepted for evidence verification, ONLY if its fingerprint equals
    the one attested in the verified manifest

Revocation and compromise are expressed as ledger sequence numbers, never wall-clock
time: a signature in block N by key K is trusted iff N <= K.retired_after_block and
N <= principal.revoked_after_block (when set). Timestamps are informational.

Manifest schema v1 (single key per principal, timestamp revocation) remains readable;
it is normalized into the v2 view, with revocation mapped to the ledger block that
imported it. New manifests are always schema v2.
"""

import copy
import hashlib
import hmac
import json
import os
import stat
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import config
from app.crypto.pqc_dsa import (CTX_LEGACY, CTX_TRUST_MANIFEST, PUBLIC_KEY_SIZE, SIGNATURE_SIZE, dsa_sign,
                                dsa_verify)
from app.database.connection import get_connection
from app.ledger.blockchain import commit_event, ledger_transaction, sign_record
from app.ledger.canonical import CanonicalizationError, canonicalize_json
from app.validation import is_hex64, is_valid_id

MANIFEST_TYPE = "SIH26237_TRUST_MANIFEST"
MANIFEST_SCHEMA_VERSION = 2
MAX_PACKAGE_BYTES = 1024 * 1024
MAX_PRINCIPALS = 5000
MAX_KEYS_PER_PRINCIPAL = 64
ROLES = ("AUTHORITY", "RECIPIENT", "INVESTIGATOR", "AUDITOR")
KEYED_ROLES = ("AUTHORITY", "RECIPIENT")
SIGNING_ROLES = ("AUTHORITY", "RECIPIENT", "INVESTIGATOR")

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
UNATTESTED = "UNATTESTED"

IMPORTED = "IMPORTED"
ALREADY_IMPORTED = "ALREADY_IMPORTED"

_TOP_KEYS = {"manifest_type", "schema_version", "version", "issued_at", "issuer", "source", "principals"}
_ISSUER_KEYS = {"principal_id", "organization", "mldsa_public_key"}
_SOURCE_KEYS = {"publisher", "description"}
_ENTRY_KEYS_V1 = {"principal_id", "role", "name", "mldsa_pk_sha256", "mlkem_pk_sha256", "status", "revoked_at"}
_ENTRY_KEYS_V2 = {"principal_id", "role", "name", "status", "revoked_after_block", "reason", "keys"}
_KEY_KEYS = {"key_id", "mldsa_pk_sha256", "mlkem_pk_sha256", "valid_after_block", "retired_after_block"}


class TrustError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# -------------------------------------------------------------- trust anchor

def authority_pin() -> str:
    path, overridden = config.authority_pin_location()
    if overridden and not config.dev_mode_enabled():
        raise TrustError(UNPINNED, "SIH_AUTHORITY_PIN_FILE override is only honoured in development mode "
                                   "(SIH_DEV_MODE=1); refusing to trust a redirected anchor")
    if not path.is_file():
        raise TrustError(UNPINNED, "No authority trust anchor is pinned")
    pin = path.read_text(encoding="utf-8").strip()
    if not is_hex64(pin):
        raise TrustError(UNPINNED, "Pinned authority trust anchor is malformed")
    return pin


def write_authority_pin(fingerprint: str) -> bool:
    """Writes the pin if absent (then marks it read-only). Never replaces a different pin."""
    if not is_hex64(fingerprint):
        raise TrustError(SCHEMA_INVALID, "Fingerprint must be 64 lowercase hex characters")
    path, overridden = config.authority_pin_location()
    if overridden and not config.dev_mode_enabled():
        raise TrustError(UNPINNED, "Refusing to write a redirected trust anchor outside development mode")
    if path.exists():
        existing = path.read_text(encoding="utf-8").strip()
        if existing != fingerprint:
            raise TrustError(PIN_MISMATCH, "A different authority trust anchor is already pinned")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fingerprint + "\n", encoding="utf-8")
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass
    return True


WITNESS_PIN_FORMAT = "sih26237-witness-pins"


def witness_pins() -> Dict[str, Any]:
    """
    Pinned independent witnesses: {"configured", "threshold", "witnesses": {fingerprint: {...}}}.
    Missing file -> not configured (history is then only locally verified). A malformed or
    redirected-outside-dev-mode file raises TrustError.
    """
    path, overridden = config.witness_pin_location()
    if overridden and not config.dev_mode_enabled():
        raise TrustError(UNPINNED, "SIH_WITNESS_PIN_FILE override is only honoured in development mode")
    if not path.is_file():
        return {"configured": False, "threshold": 0, "witnesses": {}}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys,
                         parse_float=_reject_float)
        if not isinstance(doc, dict) or set(doc) != {"format", "version", "threshold", "witnesses"} or \
                doc["format"] != WITNESS_PIN_FORMAT or doc["version"] != 1:
            raise ValueError
        witnesses = {}
        for w in doc["witnesses"]:
            if set(w) != {"witness_id", "mldsa_public_key"} or not is_valid_id(w["witness_id"]):
                raise ValueError
            pk = bytes.fromhex(w["mldsa_public_key"])
            if len(pk) != PUBLIC_KEY_SIZE:
                raise ValueError
            witnesses[sha256_hex(pk)] = {"witness_id": w["witness_id"], "public_key": pk}
        threshold = doc["threshold"]
        if not _is_int(threshold) or not 1 <= threshold <= len(witnesses):
            raise ValueError
    except (ValueError, TypeError, KeyError):
        raise TrustError(UNPINNED, "Pinned witness configuration is malformed")
    return {"configured": True, "threshold": threshold, "witnesses": witnesses}


# -------------------------------------------------------------------- schema

def _is_text(value: Any, max_len: int = 256) -> bool:
    return isinstance(value, str) and 0 < len(value) <= max_len


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_seq(value: Any) -> bool:
    return _is_int(value) and 0 <= value < 2 ** 53


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


def _is_hex_key(pk: Any) -> bool:
    return isinstance(pk, str) and len(pk) == 2 * PUBLIC_KEY_SIZE and all(c in "0123456789abcdef" for c in pk)


def _validate_common(m: Any) -> None:
    _schema(isinstance(m, dict) and set(m) == _TOP_KEYS, "Manifest fields do not match the schema")
    _schema(m["manifest_type"] == MANIFEST_TYPE, "Unknown manifest type")
    _schema(_is_int(m["schema_version"]) and m["schema_version"] in (1, 2), "Unsupported schema version")
    _schema(_is_int(m["version"]) and m["version"] >= 1, "Manifest version must be a positive integer")
    _schema(_parse_ts(m["issued_at"]) is not None, "issued_at must be an ISO-8601 timestamp with timezone")
    issuer = m["issuer"]
    _schema(isinstance(issuer, dict) and set(issuer) == _ISSUER_KEYS, "Issuer fields do not match the schema")
    _schema(is_valid_id(issuer["principal_id"]), "Invalid issuer principal_id")
    _schema(_is_text(issuer["organization"]), "Invalid issuer organization")
    _schema(_is_hex_key(issuer["mldsa_public_key"]),
            "Issuer ML-DSA-44 public key must be lowercase hex of the correct length")
    source = m["source"]
    _schema(isinstance(source, dict) and set(source) == _SOURCE_KEYS, "Source fields do not match the schema")
    _schema(_is_text(source["publisher"]) and _is_text(source["description"], 1024), "Invalid source provenance")
    entries = m["principals"]
    _schema(isinstance(entries, list) and 0 < len(entries) <= MAX_PRINCIPALS, "principals must be a non-empty list")


def _validate_v1_entries(m: dict) -> None:
    seen = set()
    for e in m["principals"]:
        _schema(isinstance(e, dict) and set(e) == _ENTRY_KEYS_V1, "Principal entry fields do not match the schema")
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


def _validate_v2_entries(m: dict) -> None:
    seen, key_ids = set(), set()
    for e in m["principals"]:
        _schema(isinstance(e, dict) and set(e) == _ENTRY_KEYS_V2, "Principal entry fields do not match the schema")
        pid = e["principal_id"]
        _schema(is_valid_id(pid) and pid not in seen, f"Invalid or duplicate principal_id {pid!r}")
        seen.add(pid)
        role = e["role"]
        _schema(role in ROLES, f"Invalid role for {pid}")
        _schema(_is_text(e["name"]), f"Invalid name for {pid}")
        _schema(e["status"] in ("ACTIVE", "REVOKED"), f"Invalid status for {pid}")
        if e["status"] == "ACTIVE":
            _schema(e["revoked_after_block"] is None and e["reason"] is None,
                    f"Active principal {pid} must not carry revocation data")
        else:
            _schema(_is_seq(e["revoked_after_block"]) and _is_text(e["reason"]),
                    f"Revoked principal {pid} requires revoked_after_block and reason")
        keys = e["keys"]
        _schema(isinstance(keys, list) and len(keys) <= MAX_KEYS_PER_PRINCIPAL, f"Invalid key list for {pid}")
        if role == "AUDITOR":
            _schema(not keys, f"{pid} (AUDITOR) must not carry keys")
        if role in KEYED_ROLES and e["status"] == "ACTIVE":
            _schema(len(keys) > 0, f"{pid} requires at least one attested key")
        current = 0
        for k in keys:
            _schema(isinstance(k, dict) and set(k) == _KEY_KEYS, f"Key entry fields for {pid} do not match the schema")
            kid = k["key_id"]
            _schema(isinstance(kid, str) and kid.startswith(pid + "#") and kid[len(pid) + 1:].isdigit()
                    and kid not in key_ids, f"Invalid or duplicate key_id {kid!r}")
            key_ids.add(kid)
            _schema(is_hex64(k["mldsa_pk_sha256"]), f"{kid} requires an ML-DSA key fingerprint")
            if role == "RECIPIENT":
                _schema(is_hex64(k["mlkem_pk_sha256"]), f"{kid} requires an ML-KEM key fingerprint")
            else:
                _schema(k["mlkem_pk_sha256"] is None, f"{kid} must not carry an ML-KEM key fingerprint")
            _schema(_is_seq(k["valid_after_block"]), f"{kid} valid_after_block must be a non-negative integer")
            ra = k["retired_after_block"]
            _schema(ra is None or (_is_seq(ra) and ra >= 0), f"{kid} retired_after_block is invalid")
            current += ra is None
        _schema(current <= 1, f"{pid} has more than one current key")


def validate_manifest_schema(m: Any) -> None:
    _validate_common(m)
    if m["schema_version"] == 1:
        _validate_v1_entries(m)
        issuer_entry = next((e for e in m["principals"] if e["principal_id"] == m["issuer"]["principal_id"]), None)
        _schema(issuer_entry is not None and issuer_entry["role"] == "AUTHORITY" and issuer_entry["status"] == "ACTIVE",
                "Issuer must be listed as an ACTIVE AUTHORITY")
        _schema(issuer_entry["mldsa_pk_sha256"] == sha256_hex(bytes.fromhex(m["issuer"]["mldsa_public_key"])),
                "Issuer entry fingerprint does not match the issuer public key")
        return
    _validate_v2_entries(m)
    issuer_entry = next((e for e in m["principals"] if e["principal_id"] == m["issuer"]["principal_id"]), None)
    _schema(issuer_entry is not None and issuer_entry["role"] == "AUTHORITY" and issuer_entry["status"] == "ACTIVE",
            "Issuer must be listed as an ACTIVE AUTHORITY")
    current = next((k for k in issuer_entry["keys"] if k["retired_after_block"] is None), None)
    _schema(current is not None and current["mldsa_pk_sha256"] == sha256_hex(bytes.fromhex(m["issuer"]["mldsa_public_key"])),
            "Issuer's current key fingerprint does not match the issuer public key")


def _no_duplicate_keys(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError(f"duplicate key {k!r}")
        obj[k] = v
    return obj


def _reject_float(_value):
    raise ValueError("floats are not permitted")


def manifest_context(manifest: dict) -> bytes:
    return CTX_TRUST_MANIFEST if manifest.get("schema_version") == 2 else CTX_LEGACY


def verify_package(raw: bytes, pin: Optional[str] = None) -> Dict[str, Any]:
    """Full validation pipeline for one package. Raises TrustError; never returns partial trust.
    `pin` defaults to the installation trust anchor (offline verifiers pass their own)."""
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

    pin = authority_pin() if pin is None else pin
    issuer_pk = bytes.fromhex(manifest["issuer"]["mldsa_public_key"])
    fingerprint = sha256_hex(issuer_pk)
    if not hmac.compare_digest(fingerprint, pin):
        raise TrustError(PIN_MISMATCH, "Manifest issuer key does not match the pinned authority trust anchor")
    if not dsa_verify(issuer_pk, manifest_bytes, bytes.fromhex(sig_hex), context=manifest_context(manifest)):
        raise TrustError(SIGNATURE_INVALID, "Manifest ML-DSA-44 signature is invalid")

    return {
        "manifest": manifest,
        "signature": sig_hex,
        "manifest_sha256": sha256_hex(manifest_bytes),
        "issuer_fingerprint": fingerprint,
        "package": canonicalize_json({"manifest": manifest, "signature": sig_hex}).decode("utf-8"),
    }


# ------------------------------------------------------------- normalization

def normalize_entries(manifest: dict, import_blocks: Optional[Dict[int, int]] = None,
                      history: Optional[List[dict]] = None) -> Dict[str, dict]:
    """
    Returns {principal_id: v2 entry}. Schema v1 entries become a single key '<id>#1';
    a v1 revocation is mapped to the ledger block that imported the first manifest
    version listing it as revoked (revoked_after_block = that block - 1). If that block
    cannot be found, revoked_after_block = 0 (fail closed: no evidence by that key is
    trusted).
    """
    if manifest["schema_version"] == 2:
        return {e["principal_id"]: copy.deepcopy(e) for e in manifest["principals"]}
    out = {}
    for e in manifest["principals"]:
        keys = []
        if e["role"] in KEYED_ROLES:
            keys.append({"key_id": f"{e['principal_id']}#1", "mldsa_pk_sha256": e["mldsa_pk_sha256"],
                         "mlkem_pk_sha256": e["mlkem_pk_sha256"], "valid_after_block": 0, "retired_after_block": None})
        revoked_after = None
        if e["status"] == "REVOKED":
            revoked_after = 0
            for older in sorted(history or [], key=lambda h: h["version"]):
                ent = next((x for x in older["manifest"]["principals"] if x["principal_id"] == e["principal_id"]), None)
                if ent and ent["status"] == "REVOKED":
                    blk = (import_blocks or {}).get(older["version"])
                    revoked_after = max(blk - 1, 0) if blk else 0
                    break
        out[e["principal_id"]] = {
            "principal_id": e["principal_id"], "role": e["role"], "name": e["name"], "status": e["status"],
            "revoked_after_block": revoked_after, "reason": "legacy revocation" if e["status"] == "REVOKED" else None,
            "keys": keys,
        }
    return out


# ---------------------------------------------------------------- local store

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


def _ledger_manifest_blocks(conn) -> List[tuple]:
    rows = conn.execute(
        "SELECT block_index, canonical_record FROM ledger_blocks WHERE event_type = 'TRUST_MANIFEST_IMPORTED' "
        "ORDER BY block_index").fetchall()
    return [(r["block_index"], json.loads(r["canonical_record"])) for r in rows]


def current_manifest() -> Dict[str, Any]:
    """Latest manifest, re-verified from storage, cross-checked against the ledger, and
    normalized: result["principals"] is {principal_id: v2 entry}."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM trust_manifests ORDER BY version").fetchall()
        ledger_records = _ledger_manifest_blocks(conn)
    finally:
        conn.close()
    if not rows:
        raise TrustError(NOT_AVAILABLE, "No trust manifest has been imported")
    stored = {r["version"]: r["manifest_sha256"] for r in rows}
    for _, rec in ledger_records:
        if stored.get(rec.get("manifest_version")) != rec.get("manifest_sha256"):
            raise TrustError(CORRUPTED, f"Ledger records trust manifest v{rec.get('manifest_version')} "
                                        "which is missing or different in the local store (rollback detected)")
    verified = _verify_stored(rows[-1])
    history = None
    if verified["manifest"]["schema_version"] == 1:
        history = [_verify_stored(r) for r in rows if r["version"] <= verified["version"]]
    import_blocks = {rec.get("manifest_version"): idx for idx, rec in ledger_records}
    verified["principals"] = normalize_entries(verified["manifest"], import_blocks, history)
    verified["schema_version"] = verified["manifest"]["schema_version"]
    return verified


def list_manifests() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT version, manifest_sha256, issuer_fingerprint, issued_at, source_label, imported_by, "
                            "imported_at FROM trust_manifests ORDER BY version").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def all_packages() -> List[str]:
    """Every stored signed package in version order (for offline export)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT package FROM trust_manifests ORDER BY version").fetchall()
    finally:
        conn.close()
    return [r["package"] for r in rows]


# ------------------------------------------------------------ monotonic rules

def check_transition(previous: Optional[Dict[str, dict]], new: Dict[str, dict], tail: Optional[int]) -> None:
    """
    Manifests may only add principals, add keys, retire keys once, or revoke once.
    With `tail` (the ledger head at import), newly set sequence bounds must not lie in
    the future. Raises TrustError(CONFLICT).
    """
    def bound_ok(value):
        return tail is None or value <= tail

    for pid, e in new.items():
        for k in e["keys"]:
            if k["retired_after_block"] is not None and k["retired_after_block"] < k["valid_after_block"] \
                    and (previous is None or pid not in previous):
                raise TrustError(CONFLICT, f"{k['key_id']} retired before it became valid")
    if previous is None:
        return
    for pid, old in previous.items():
        cur = new.get(pid)
        if cur is None:
            raise TrustError(CONFLICT, f"Principal {pid} was removed; manifests may only add, retire or revoke")
        if cur["role"] != old["role"]:
            raise TrustError(CONFLICT, f"Role change for {pid} is not permitted")
        if old["status"] == "REVOKED":
            if cur["status"] != "REVOKED" or cur["revoked_after_block"] != old["revoked_after_block"]:
                raise TrustError(CONFLICT, f"Revocation of {pid} cannot be undone or moved")
        elif cur["status"] == "REVOKED" and not bound_ok(cur["revoked_after_block"]):
            raise TrustError(CONFLICT, f"Revocation of {pid} cannot take effect after the current ledger head")
        new_keys = {k["key_id"]: k for k in cur["keys"]}
        for ok in old["keys"]:
            nk = new_keys.get(ok["key_id"])
            if nk is None or (nk["mldsa_pk_sha256"], nk["mlkem_pk_sha256"], nk["valid_after_block"]) != \
                    (ok["mldsa_pk_sha256"], ok["mlkem_pk_sha256"], ok["valid_after_block"]):
                raise TrustError(CONFLICT, f"Key or role change for {pid} is not permitted ({ok['key_id']})")
            if ok["retired_after_block"] is not None:
                if nk["retired_after_block"] != ok["retired_after_block"]:
                    raise TrustError(CONFLICT, f"Retirement of {ok['key_id']} cannot be undone or moved")
            elif nk["retired_after_block"] is not None:
                if nk["retired_after_block"] < ok["valid_after_block"] or not bound_ok(nk["retired_after_block"]):
                    raise TrustError(CONFLICT, f"Retirement of {ok['key_id']} is outside its validity window")
        added = [k for k in cur["keys"] if k["key_id"] not in {o["key_id"] for o in old["keys"]}]
        if added and old["status"] == "REVOKED":
            raise TrustError(CONFLICT, f"Revoked principal {pid} cannot receive new keys")
        for k in added:
            if not bound_ok(k["valid_after_block"]):
                raise TrustError(CONFLICT, f"{k['key_id']} cannot become valid after the current ledger head")


def _tail_index(conn) -> int:
    return conn.execute("SELECT COALESCE(MAX(block_index), 0) FROM ledger_blocks").fetchone()[0]


def _apply_to_registry(conn, entries: Dict[str, dict]) -> None:
    """Mirrors attested state into the operational registry (status only; never key material)."""
    for pid, e in entries.items():
        for k in e["keys"]:
            row = conn.execute("SELECT mldsa_public_key, mlkem_public_key FROM principal_keys WHERE key_id = ?",
                               (k["key_id"],)).fetchone()
            if not row:
                continue
            if sha256_hex(bytes.fromhex(row["mldsa_public_key"])) != k["mldsa_pk_sha256"]:
                continue
            status = "ACTIVE" if k["retired_after_block"] is None else "RETIRED"
            conn.execute("UPDATE principal_keys SET status = ? WHERE key_id = ?", (status, k["key_id"]))
            if status == "ACTIVE":
                conn.execute("UPDATE principals SET mldsa_public_key = ? WHERE principal_id = ?",
                             (row["mldsa_public_key"], pid))
                if e["role"] == "RECIPIENT":
                    conn.execute("UPDATE recipients SET mldsa_public_key = ?, mlkem_public_key = ? WHERE recipient_id = ?",
                                 (row["mldsa_public_key"], row["mlkem_public_key"], pid))
        principal_status = "REVOKED" if e["status"] == "REVOKED" else "ACTIVE"
        conn.execute("UPDATE principals SET status = ? WHERE principal_id = ? AND status != 'PENDING_ENROLLMENT'",
                     (principal_status, pid))
        if e["role"] == "RECIPIENT":
            conn.execute("UPDATE recipients SET status = ? WHERE recipient_id = ?", (principal_status, pid))


def import_package(raw: bytes, source_label: str, authority_id: str, authority_sk: bytes,
                   authority_key_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Imports a signed schema-v2 manifest package into the local trust store. The importing
    authority countersigns a TRUST_MANIFEST_IMPORTED ledger block in the same transaction.
    """
    if not _is_text(source_label, 256):
        raise TrustError(SCHEMA_INVALID, "source_label is required")
    verified = verify_package(raw)
    manifest = verified["manifest"]
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise TrustError(SCHEMA_INVALID, "Only schema v2 manifests can be imported; v1 is read-only (legacy)")
    version = manifest["version"]
    authority_key_id = authority_key_id or f"{authority_id}#1"

    conn = get_connection()
    try:
        with ledger_transaction(conn) as tx:
            same = conn.execute("SELECT manifest_sha256 FROM trust_manifests WHERE version = ?", (version,)).fetchone()
            if same is not None:
                if same["manifest_sha256"] == verified["manifest_sha256"]:
                    return {"status": ALREADY_IMPORTED, "version": version, "manifest_sha256": verified["manifest_sha256"]}
                raise TrustError(CONFLICT, f"A different trust manifest v{version} is already imported")
            latest = conn.execute("SELECT * FROM trust_manifests ORDER BY version DESC LIMIT 1").fetchone()
            previous_entries = None
            if latest is not None:
                prev = _verify_stored(latest)
                if version < prev["version"]:
                    raise TrustError(STALE, f"Manifest v{version} is older than the imported v{prev['version']}")
                history = None
                if prev["manifest"]["schema_version"] == 1:
                    history = [_verify_stored(r) for r in conn.execute(
                        "SELECT * FROM trust_manifests ORDER BY version").fetchall()]
                blocks = {rec.get("manifest_version"): idx for idx, rec in _ledger_manifest_blocks(conn)}
                previous_entries = normalize_entries(prev["manifest"], blocks, history)
            new_entries = normalize_entries(manifest)
            check_transition(previous_entries, new_entries, _tail_index(conn))

            imported_at = _now()
            conn.execute(
                "INSERT INTO trust_manifests (version, manifest_sha256, package, issuer_fingerprint, issued_at, "
                "source_label, imported_by, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (version, verified["manifest_sha256"], verified["package"], verified["issuer_fingerprint"],
                 manifest["issued_at"], source_label, authority_id, imported_at),
            )
            _apply_to_registry(conn, new_entries)
            revoked = sorted(pid for pid, e in new_entries.items() if e["status"] == "REVOKED"
                             and (previous_entries is None or previous_entries.get(pid, {}).get("status") != "REVOKED"))
            record = {
                "record_type": "TRUST_MANIFEST",
                "record_version": "3.0",
                "authority_id": authority_id,
                "signer_key_id": authority_key_id,
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


# -------------------------------------------------------------------- issuing

def _registry_keys(conn, principal_id: str) -> List[Any]:
    return conn.execute("SELECT * FROM principal_keys WHERE principal_id = ? ORDER BY seq", (principal_id,)).fetchall()


def _key_entry(row, role: str, valid_after: int) -> dict:
    return {
        "key_id": row["key_id"],
        "mldsa_pk_sha256": sha256_hex(bytes.fromhex(row["mldsa_public_key"])),
        "mlkem_pk_sha256": sha256_hex(bytes.fromhex(row["mlkem_public_key"])) if role == "RECIPIENT" else None,
        "valid_after_block": valid_after,
        "retired_after_block": None,
    }


def build_next_manifest(authority_id: str, authority_pk: bytes, organization: str, publisher: str,
                        description: str, revoke: Optional[List[str]] = None, *,
                        attest: Optional[List[dict]] = None, compromise: Optional[List[dict]] = None,
                        reason: Optional[str] = None) -> dict:
    """
    Builds the next schema-v2 manifest from the attested state plus explicit operations:
      - principals provisioned ACTIVE in the registry but not yet attested are added
        (operator bootstrap path);
      - attest: [{"principal_id", "key_id", "mldsa_pk_sha256"}] attests a PENDING key whose
        fingerprint was confirmed out of band; an existing current key is retired at the
        current ledger head (rotation);
      - revoke: principal IDs, effective after the current ledger head;
      - compromise: [{"key_id", "compromised_after_block"}] retires a key retroactively,
        so evidence it signed after that block is no longer trusted.
    Refuses if a registry key differs from the one already attested (registry substitution
    must not be laundered into a newly signed manifest).
    """
    try:
        previous = current_manifest()
    except TrustError as exc:
        if exc.code != NOT_AVAILABLE:
            raise
        previous = None

    conn = get_connection()
    try:
        tail = _tail_index(conn)
        entries: Dict[str, dict] = copy.deepcopy(previous["principals"]) if previous else {}
        for pid, e in entries.items():
            reg = {r["key_id"]: r for r in _registry_keys(conn, pid)}
            for k in e["keys"]:
                row = reg.get(k["key_id"])
                if row is None or sha256_hex(bytes.fromhex(row["mldsa_public_key"])) != k["mldsa_pk_sha256"] or \
                        (k["mlkem_pk_sha256"] is not None and
                         sha256_hex(bytes.fromhex(row["mlkem_public_key"] or "")) != k["mlkem_pk_sha256"]):
                    raise TrustError(REGISTRY_DRIFT, f"Registry keys for {pid} differ from the attested manifest")

        principals = conn.execute("SELECT * FROM principals ORDER BY principal_id").fetchall()
        for p in principals:
            if p["status"] != "ACTIVE":
                continue
            existing = entries.get(p["principal_id"])
            if existing is not None:
                if p["role"] == "INVESTIGATOR" and not existing["keys"] and existing["status"] == "ACTIVE":
                    keys = [r for r in _registry_keys(conn, p["principal_id"]) if r["status"] == "ACTIVE"]
                    existing["keys"] = [_key_entry(r, p["role"], tail) for r in keys[-1:]]
                continue
            keys = [r for r in _registry_keys(conn, p["principal_id"]) if r["status"] == "ACTIVE"]
            if p["role"] == "AUDITOR":
                keys = []
            entries[p["principal_id"]] = {
                "principal_id": p["principal_id"], "role": p["role"], "name": p["name"], "status": "ACTIVE",
                "revoked_after_block": None, "reason": None,
                "keys": [_key_entry(r, p["role"], tail if previous else 0) for r in keys[-1:]],
            }

        for item in attest or []:
            pid, kid, confirmed = item.get("principal_id"), item.get("key_id"), item.get("mldsa_pk_sha256")
            row = conn.execute("SELECT * FROM principal_keys WHERE key_id = ? AND principal_id = ?", (kid, pid)).fetchone()
            principal = conn.execute("SELECT * FROM principals WHERE principal_id = ?", (pid,)).fetchone()
            if row is None or principal is None or row["status"] != "PENDING":
                raise TrustError(SCHEMA_INVALID, f"No pending key {kid!r} for {pid!r}")
            if not is_hex64(confirmed or "") or not hmac.compare_digest(
                    sha256_hex(bytes.fromhex(row["mldsa_public_key"])), confirmed):
                raise TrustError(SCHEMA_INVALID, f"Confirmed fingerprint does not match pending key {kid}")
            new_key = _key_entry(row, principal["role"], tail)
            if pid in entries:
                e = entries[pid]
                if e["status"] != "ACTIVE":
                    raise TrustError(CONFLICT, f"{pid} is revoked")
                for k in e["keys"]:
                    if k["retired_after_block"] is None:
                        k["retired_after_block"] = tail
                e["keys"].append(new_key)
            else:
                if principal["status"] != "PENDING_ATTESTATION":
                    raise TrustError(SCHEMA_INVALID, f"{pid} is not awaiting attestation")
                entries[pid] = {"principal_id": pid, "role": principal["role"], "name": principal["name"],
                                "status": "ACTIVE", "revoked_after_block": None, "reason": None, "keys": [new_key]}
    finally:
        conn.close()

    for item in compromise or []:
        kid, after = item.get("key_id"), item.get("compromised_after_block")
        entry = next((e for e in entries.values() for k in e["keys"] if k["key_id"] == kid), None)
        key = next((k for k in entry["keys"] if k["key_id"] == kid), None) if entry else None
        if key is None:
            raise TrustError(SCHEMA_INVALID, f"Unknown key {kid!r}")
        if entry["role"] == "AUTHORITY":
            raise TrustError(SCHEMA_INVALID, "Authority key compromise requires a new installation trust anchor")
        if not _is_seq(after) or after > tail or after < key["valid_after_block"]:
            raise TrustError(SCHEMA_INVALID, f"compromised_after_block must lie in [{key['valid_after_block']}, {tail}]")
        if key["retired_after_block"] is not None and key["retired_after_block"] <= after:
            raise TrustError(CONFLICT, f"{kid} is already retired at or before block {after}")
        if key["retired_after_block"] is not None:
            raise TrustError(CONFLICT, f"Retirement of {kid} cannot be moved")
        key["retired_after_block"] = after

    for pid in revoke or []:
        entry = entries.get(pid)
        if entry is None:
            raise TrustError(SCHEMA_INVALID, f"Unknown principal {pid}")
        if pid == authority_id:
            raise TrustError(SCHEMA_INVALID, "The issuing authority cannot revoke itself")
        if entry["status"] != "REVOKED":
            entry["status"], entry["revoked_after_block"] = "REVOKED", tail
            entry["reason"] = (reason or "revoked by authority")[:256]

    return {
        "manifest_type": MANIFEST_TYPE,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "version": (previous["version"] + 1) if previous else 1,
        "issued_at": _now(),
        "issuer": {"principal_id": authority_id, "organization": organization, "mldsa_public_key": authority_pk.hex()},
        "source": {"publisher": publisher, "description": description[:1024]},
        "principals": [entries[k] for k in sorted(entries)],
    }


def sign_manifest(manifest: dict, authority_sk: bytes) -> bytes:
    validate_manifest_schema(manifest)
    sig = dsa_sign(authority_sk, canonicalize_json(manifest), context=manifest_context(manifest))
    return canonicalize_json({"manifest": manifest, "signature": sig.hex()})


DEFAULT_ORGANIZATION = "WESEE, Indian Navy (issuing authority)"
DEFAULT_PUBLISHER = "WESEE HQ identity provisioning (synthetic demo identities)"


def issue_and_import(authority_id: str, authority_pk: bytes, authority_sk: bytes, source_label: str,
                     description: str, revoke: Optional[List[str]] = None, *, attest: Optional[List[dict]] = None,
                     compromise: Optional[List[dict]] = None, reason: Optional[str] = None,
                     authority_key_id: Optional[str] = None) -> Dict[str, Any]:
    manifest = build_next_manifest(authority_id, authority_pk, DEFAULT_ORGANIZATION, DEFAULT_PUBLISHER,
                                   description, revoke, attest=attest, compromise=compromise, reason=reason)
    return import_package(sign_manifest(manifest, authority_sk), source_label, authority_id, authority_sk,
                          authority_key_id)


# ---------------------------------------------------------------- key resolver

def _registry_key(key_id: str) -> Optional[dict]:
    from app.crypto.identity import get_registered_key
    return get_registered_key(key_id)


def resolve_key(principal_id: str, role: str, key_id: Optional[str] = None,
                view: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Resolves a principal's public key through the verified manifest. With key_id=None the
    principal's current (non-retired) key is returned. Raises TrustError when the
    principal, role or key is not attested, or when the registry key bytes do not match
    the attested fingerprint (registry substitution).
    """
    view = view or current_manifest()
    entry = view["principals"].get(principal_id)
    if entry is None:
        raise TrustError(UNATTESTED, f"{principal_id} is not listed in trust manifest v{view['version']}")
    if entry["role"] != role:
        raise TrustError(UNATTESTED, f"{principal_id} is attested as {entry['role']}, not {role}")
    if key_id is None:
        key = next((k for k in entry["keys"] if k["retired_after_block"] is None), None)
        if key is None:
            raise TrustError(UNATTESTED, f"{principal_id} has no current attested key")
    else:
        key = next((k for k in entry["keys"] if k["key_id"] == key_id), None)
        if key is None:
            raise TrustError(UNATTESTED, f"Key {key_id} is not attested for {principal_id}")
    reg = _registry_key(key["key_id"])
    if reg is None or reg["principal_id"] != principal_id or reg["mldsa_pk"] is None:
        raise TrustError(UNATTESTED, f"Public key {key['key_id']} is not available in the local registry")
    if not hmac.compare_digest(sha256_hex(reg["mldsa_pk"]), key["mldsa_pk_sha256"]):
        raise TrustError(REGISTRY_DRIFT, f"Registered key for {principal_id} does not match the key attested by the authority")
    if key["mlkem_pk_sha256"] is not None and (
            reg["mlkem_ek"] is None or not hmac.compare_digest(sha256_hex(reg["mlkem_ek"]), key["mlkem_pk_sha256"])):
        raise TrustError(REGISTRY_DRIFT, f"Registered ML-KEM key for {principal_id} does not match the attested key")
    return {"principal_id": principal_id, "role": role, "key_id": key["key_id"], "mldsa_pk": reg["mldsa_pk"],
            "mlkem_ek": reg["mlkem_ek"] if key["mlkem_pk_sha256"] else None, "key": key, "entry": entry,
            "manifest_version": view["version"], "manifest_sha256": view["manifest_sha256"]}


def key_valid_at(resolved: Dict[str, Any], block_index: int) -> tuple:
    """(trusted, reason) for a signature by `resolved` in ledger block `block_index`."""
    entry, key = resolved["entry"], resolved["key"]
    if entry["revoked_after_block"] is not None and block_index > entry["revoked_after_block"]:
        return False, (f"{resolved['principal_id']} was revoked after block {entry['revoked_after_block']}; "
                       f"this evidence is in block {block_index}")
    if key["retired_after_block"] is not None and block_index > key["retired_after_block"]:
        return False, (f"Key {key['key_id']} was retired/compromised after block {key['retired_after_block']}; "
                       f"this evidence is in block {block_index}")
    return True, None


def resolve_operational_key(principal_id: str, role: str, view: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Key usable for NEW operations: attested, current, principal ACTIVE."""
    resolved = resolve_key(principal_id, role, None, view)
    if resolved["entry"]["status"] != "ACTIVE":
        raise TrustError(UNATTESTED, f"{principal_id} is revoked")
    return resolved


def verify_principal_key(principal_id: str, role: str, mldsa_pk: bytes, block_index: int,
                         key_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Is `mldsa_pk` the key the pinned authority attested for `principal_id` (key_id or the
    legacy '#1'), and was it trusted at ledger sequence `block_index`? Never raises.
    """
    result = {"trusted": False, "reason": None, "manifest_version": None, "manifest_sha256": None,
              "authority_pin": None, "key_id": None}
    try:
        result["authority_pin"] = authority_pin()
        view = current_manifest()
        result["manifest_version"], result["manifest_sha256"] = view["version"], view["manifest_sha256"]
        resolved = resolve_key(principal_id, role, key_id or f"{principal_id}#1", view)
        result["key_id"] = resolved["key_id"]
        if not hmac.compare_digest(resolved["mldsa_pk"], mldsa_pk):
            result["reason"] = f"Signing key for {principal_id} does not match the key attested by the authority"
        else:
            ok, why = key_valid_at(resolved, block_index)
            result["trusted"], result["reason"] = ok, why
    except TrustError as exc:
        result["reason"] = f"Trust store unavailable or key not attested ({exc.code}): {exc}"
    except Exception as exc:
        result["reason"] = f"Trust verification error ({type(exc).__name__})"
    return result
