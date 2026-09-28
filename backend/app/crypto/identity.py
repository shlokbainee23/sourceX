"""
Principal identities, key registry and key lifecycle for SIH26237.

Registry (SQLite, operational data, NOT a trust source):
    principals       one row per principal, lifecycle status
    principal_keys   every public key ever registered, identified as '<principal>#<n>';
                     key material is immutable (trigger), only the local status changes
    recipients       public directory view of each recipient's current key

Trust comes only from the signed manifest (app.trust): a key is used for encryption or
accepted as evidence only if its fingerprint is attested there.

Lifecycle:
    provision_principal     operator-side bootstrap (authority, investigator, auditor, tests)
    create_pending_principal + enroll_principal
                            the authority creates the identity and a one-time enrollment code;
                            the recipient chooses their own passphrase and keys are generated
                            then (the authority never learns the passphrase)
    rotate_keys             new key pair, old signing key destroyed, old ML-KEM key kept as
                            'retired' so earlier documents stay readable
    change_passphrase       re-encrypts the same key material

Private keys exist on disk only inside the encrypted keystore and are never returned
by any API.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app import config
from app.crypto import keystore
from app.crypto.pqc_dsa import CTX_KEY_POSSESSION, dsa_keygen, dsa_sign, dsa_verify
from app.crypto.pqc_dsa import public_key_from_secret as dsa_public_key
from app.crypto.pqc_kem import kem_decapsulate, kem_encapsulate, kem_keygen
from app.crypto.pqc_kem import public_key_from_secret as kem_public_key
from app.database.connection import get_connection, transaction
from app.validation import is_valid_id

ROLES = ("AUTHORITY", "RECIPIENT", "INVESTIGATOR", "AUDITOR")
SIGNING_ROLES = ("AUTHORITY", "RECIPIENT", "INVESTIGATOR")

PENDING_ENROLLMENT = "PENDING_ENROLLMENT"
PENDING_ATTESTATION = "PENDING_ATTESTATION"
ACTIVE = "ACTIVE"
REVOKED = "REVOKED"

ENROLLMENT_CODE_TTL_SECONDS = 72 * 3600

DEFAULT_PRINCIPALS = [
    {"principal_id": "WESEE_HQ", "role": "AUTHORITY", "name": "WESEE Headquarters (Sender Authority)"},
    {"principal_id": "R001", "role": "RECIPIENT", "name": "Commander Alpha", "title": "Navigation Officer (Naval Command)"},
    {"principal_id": "R002", "role": "RECIPIENT", "name": "Officer Bravo", "title": "Communications Director (Fleet Signals)"},
    {"principal_id": "R003", "role": "RECIPIENT", "name": "Officer Charlie", "title": "Weapons Specialist (Tactical Systems)"},
    {"principal_id": "INVESTIGATOR_01", "role": "INVESTIGATOR", "name": "Naval Forensics Investigator"},
    {"principal_id": "AUDITOR_01", "role": "AUDITOR", "name": "Ledger Auditor"},
]


class IdentityError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _legacy_key_file(principal_id: str) -> Path:
    return config.keystore_dir() / f"{principal_id}.key.json"


def legacy_plaintext_key_files() -> List[Path]:
    """Plaintext key files written by the v1 prototype."""
    return sorted(config.keystore_dir().glob("*.key.json"))


def destroy_file(path: Path) -> None:
    """Overwrite with random bytes before unlinking. Best effort: SSDs and journaling
    filesystems may retain old blocks, which is documented in SECURITY.md."""
    try:
        size = path.stat().st_size
        with open(path, "r+b") as f:
            f.write(os.urandom(max(size, 1)))
            f.flush()
            os.fsync(f.fileno())
    except FileNotFoundError:
        return
    finally:
        path.unlink(missing_ok=True)


def _load_legacy_recipient_keys(principal_id: str) -> Optional[Dict[str, bytes]]:
    path = _legacy_key_file(principal_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return {
        "mlkem_dk": bytes.fromhex(data["mlkem_private_key_hex"]),
        "mldsa_sk": bytes.fromhex(data["mldsa_private_key_hex"]),
    }


def _generate_keys(role: str) -> tuple:
    """Returns (secrets_map, mldsa_pk_hex, mlkem_ek_hex) for a role."""
    if role == "RECIPIENT":
        ek, dk = kem_keygen()
        pk, sk = dsa_keygen()
        return {"mlkem_dk": dk, "mldsa_sk": sk}, pk.hex(), ek.hex()
    if role in ("AUTHORITY", "INVESTIGATOR"):
        pk, sk = dsa_keygen()
        return {"mldsa_sk": sk}, pk.hex(), None
    return {}, None, None


# ----------------------------------------------------------------- registry reads

def principal_exists(principal_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM principals WHERE principal_id = ?", (principal_id,)).fetchone()
    conn.close()
    return row is not None and keystore.keystore_path(principal_id).exists()


def get_principal(principal_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM principals WHERE principal_id = ?", (principal_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_registered_key(key_id: str) -> Optional[dict]:
    """Registry row for one key ID (public keys as bytes). Unverified: callers must check
    the fingerprint against the signed manifest before trusting it."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM principal_keys WHERE key_id = ?", (key_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "principal_id": row["principal_id"],
        "key_id": row["key_id"],
        "seq": row["seq"],
        "status": row["status"],
        "mldsa_pk": bytes.fromhex(row["mldsa_public_key"]) if row["mldsa_public_key"] else None,
        "mlkem_ek": bytes.fromhex(row["mlkem_public_key"]) if row["mlkem_public_key"] else None,
        "created_at": row["created_at"],
    }


def list_principal_keys(principal_id: str) -> List[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT key_id, seq, status, mldsa_public_key, mlkem_public_key, created_at "
                        "FROM principal_keys WHERE principal_id = ? ORDER BY seq", (principal_id,)).fetchall()
    conn.close()
    return [{
        "key_id": r["key_id"], "seq": r["seq"], "status": r["status"], "created_at": r["created_at"],
        "mldsa_pk_sha256": sha256_hex(bytes.fromhex(r["mldsa_public_key"])) if r["mldsa_public_key"] else None,
        "mlkem_pk_sha256": sha256_hex(bytes.fromhex(r["mlkem_public_key"])) if r["mlkem_public_key"] else None,
    } for r in rows]


def get_recipient_public_keys(recipient_id: str, include_revoked: bool = False) -> Optional[Dict[str, bytes]]:
    """Registry view of a recipient's current keys (display and diagnostics only; not a trust source)."""
    conn = get_connection()
    query = "SELECT mlkem_public_key, mldsa_public_key FROM recipients WHERE recipient_id = ?"
    if not include_revoked:
        query += " AND status = 'ACTIVE'"
    row = conn.execute(query, (recipient_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {"mlkem_ek": bytes.fromhex(row["mlkem_public_key"]), "mldsa_pk": bytes.fromhex(row["mldsa_public_key"])}


def get_authority_public_key(principal_id: str) -> Optional[bytes]:
    """Registry view of an authority's current signing key (not a trust source)."""
    principal = get_principal(principal_id)
    if not principal or principal["role"] != "AUTHORITY" or not principal["mldsa_public_key"]:
        return None
    return bytes.fromhex(principal["mldsa_public_key"])


# ------------------------------------------------------- key/secret consistency

def keys_match_public(keys: Dict[str, bytes], mldsa_pk: Optional[bytes], mlkem_ek: Optional[bytes],
                      principal_id: str) -> bool:
    """Proves unlocked private keys correspond to the given public keys (seed derivation, or a
    sign/verify and encaps/decaps probe for legacy expanded keys)."""
    probe = b"sih26237-keystore-consistency-probe|" + principal_id.encode()
    if mldsa_pk is not None:
        sk = keys.get("mldsa_sk")
        if sk is None:
            return False
        if len(sk) == 32:
            if not hmac.compare_digest(dsa_public_key(sk), mldsa_pk):
                return False
        elif not dsa_verify(mldsa_pk, probe, dsa_sign(sk, probe, context=CTX_KEY_POSSESSION),
                            context=CTX_KEY_POSSESSION):
            return False
    elif "mldsa_sk" in keys:
        return False
    if mlkem_ek is not None:
        dk = keys.get("mlkem_dk")
        if dk is None:
            return False
        if len(dk) == 64:
            if not hmac.compare_digest(kem_public_key(dk), mlkem_ek):
                return False
        else:
            ss, ct = kem_encapsulate(mlkem_ek)
            if not hmac.compare_digest(kem_decapsulate(dk, ct), ss):
                return False
    elif "mlkem_dk" in keys:
        return False
    return True


def verify_keys_match_registry(principal_id: str, role: str, keys: Dict[str, bytes], key_id: Optional[str] = None) -> bool:
    """Authentication-time check: the unlocked keystore holds the private half of the key
    registered under its key ID. (Operations additionally require manifest attestation.)"""
    if role == "AUDITOR":
        return not any(k in keys for k in ("mldsa_sk", "mlkem_dk"))
    if role == "INVESTIGATOR" and "mldsa_sk" not in keys:
        return True  # legacy investigator without a signing key: reports are hash-only
    reg = get_registered_key(key_id or f"{principal_id}#1")
    if not reg or reg["principal_id"] != principal_id:
        return False
    return keys_match_public(keys, reg["mldsa_pk"], reg["mlkem_ek"] if role == "RECIPIENT" else None, principal_id)


# --------------------------------------------------------------- provisioning

def provision_principal(principal_id: str, role: str, name: str, passphrase: str, title: Optional[str] = None) -> dict:
    """
    Operator-side bootstrap: creates keys + encrypted keystore + registry rows for one
    principal. For recipients this is custodial (the operator chose the passphrase) and is
    used only for the synthetic demo bootstrap and tests; the API enrols recipients
    through create_pending_principal + enroll_principal instead.
    For recipients with a v1 plaintext key file, the existing keys are migrated into
    the encrypted keystore (public keys stay stable) and the plaintext file is destroyed.
    """
    if not is_valid_id(principal_id):
        raise IdentityError("Invalid principal identifier")
    if role not in ROLES:
        raise IdentityError("Invalid role")
    if principal_exists(principal_id):
        raise IdentityError(f"Principal {principal_id} is already provisioned")

    created_at = _now()
    key_id = f"{principal_id}#1" if role in SIGNING_ROLES else None
    migrated = False

    conn = get_connection()
    existing_recipient = conn.execute(
        "SELECT mlkem_public_key, mldsa_public_key FROM recipients WHERE recipient_id = ?", (principal_id,)
    ).fetchone()
    conn.close()

    legacy = _load_legacy_recipient_keys(principal_id) if role == "RECIPIENT" else None
    if legacy and existing_recipient:
        secrets_map = legacy
        mlkem_ek_hex = existing_recipient["mlkem_public_key"]
        mldsa_pk_hex = existing_recipient["mldsa_public_key"]
        migrated = True
    else:
        secrets_map, mldsa_pk_hex, mlkem_ek_hex = _generate_keys(role)

    ks_path = keystore.create_keystore(principal_id, role, passphrase, secrets_map, key_id=key_id)
    try:
        conn = get_connection()
        with transaction(conn):
            conn.execute(
                "INSERT INTO principals (principal_id, role, name, mldsa_public_key, status, created_at) "
                "VALUES (?, ?, ?, ?, 'ACTIVE', ?)",
                (principal_id, role, name, mldsa_pk_hex, created_at),
            )
            if key_id:
                conn.execute(
                    "INSERT INTO principal_keys (principal_id, key_id, seq, mldsa_public_key, mlkem_public_key, status, "
                    "created_at) VALUES (?, ?, 1, ?, ?, 'ACTIVE', ?)",
                    (principal_id, key_id, mldsa_pk_hex, mlkem_ek_hex, created_at))
            if role == "RECIPIENT":
                if existing_recipient:
                    conn.execute(
                        "UPDATE recipients SET name = ?, role = ?, mlkem_public_key = ?, mldsa_public_key = ?, status = 'ACTIVE' "
                        "WHERE recipient_id = ?",
                        (name, title or "Recipient", mlkem_ek_hex, mldsa_pk_hex, principal_id),
                    )
                else:
                    conn.execute(
                        "INSERT INTO recipients (recipient_id, name, role, mlkem_public_key, mldsa_public_key, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (principal_id, name, title or "Recipient", mlkem_ek_hex, mldsa_pk_hex, created_at),
                    )
        conn.close()
    except Exception:
        ks_path.unlink(missing_ok=True)
        raise

    if migrated:
        destroy_file(_legacy_key_file(principal_id))

    return {"principal_id": principal_id, "role": role, "name": name, "key_id": key_id,
            "migrated_legacy_keys": migrated}


# -------------------------------------------------------------- enrollment

def _hash_code(code: str, salt: bytes) -> str:
    return Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1).derive(code.encode("utf-8")).hex()


def create_pending_principal(principal_id: str, role: str, name: str, title: Optional[str], created_by: str) -> dict:
    """Creates an identity with no keys and returns a one-time enrollment code (shown once,
    stored only as a salted scrypt hash). The code must reach the person out of band."""
    if not is_valid_id(principal_id):
        raise IdentityError("Invalid principal identifier")
    if role not in ("RECIPIENT", "INVESTIGATOR"):
        raise IdentityError("Only recipients and investigators enrol themselves")
    code = "-".join(secrets.token_hex(3).upper() for _ in range(4))
    salt = os.urandom(16)
    now = _now()
    conn = get_connection()
    try:
        with transaction(conn):
            if conn.execute("SELECT 1 FROM principals WHERE principal_id = ?", (principal_id,)).fetchone() or \
                    conn.execute("SELECT 1 FROM recipients WHERE recipient_id = ?", (principal_id,)).fetchone():
                raise IdentityError(f"Principal {principal_id} already exists")
            conn.execute("INSERT INTO principals (principal_id, role, name, title, mldsa_public_key, status, created_at) "
                         "VALUES (?, ?, ?, ?, NULL, ?, ?)",
                         (principal_id, role, name, title or "Recipient", PENDING_ENROLLMENT, now))
            conn.execute("INSERT INTO enrollment_codes (principal_id, code_hash, salt, created_by, created_at, expires_at) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (principal_id, _hash_code(code, salt), salt.hex(), created_by, now,
                          time.time() + ENROLLMENT_CODE_TTL_SECONDS))
    finally:
        conn.close()
    return {"principal_id": principal_id, "role": role, "status": PENDING_ENROLLMENT, "enrollment_code": code,
            "expires_in_seconds": ENROLLMENT_CODE_TTL_SECONDS}


def enroll_principal(principal_id: str, enrollment_code: str, passphrase: str) -> dict:
    """The principal redeems the one-time code, chooses a passphrase and receives fresh keys.
    The new key is PENDING until the authority attests its fingerprint in a signed manifest."""
    principal = get_principal(principal_id)
    generic = IdentityError("Invalid or expired enrollment code")
    if not principal or principal["status"] != PENDING_ENROLLMENT:
        raise generic
    conn = get_connection()
    row = conn.execute("SELECT * FROM enrollment_codes WHERE principal_id = ?", (principal_id,)).fetchone()
    conn.close()
    if not row or row["used_at"] is not None or row["expires_at"] < time.time():
        raise generic
    if not hmac.compare_digest(_hash_code(enrollment_code or "", bytes.fromhex(row["salt"])), row["code_hash"]):
        raise generic

    role = principal["role"]
    secrets_map, mldsa_pk_hex, mlkem_ek_hex = _generate_keys(role)
    key_id = f"{principal_id}#1"
    ks_path = keystore.create_keystore(principal_id, role, passphrase, secrets_map, key_id=key_id)
    now = _now()
    try:
        conn = get_connection()
        with transaction(conn):
            used = conn.execute("UPDATE enrollment_codes SET used_at = ? WHERE principal_id = ? AND used_at IS NULL",
                                (now, principal_id)).rowcount
            if used != 1:
                raise generic
            conn.execute("UPDATE principals SET status = ?, mldsa_public_key = ? WHERE principal_id = ?",
                         (PENDING_ATTESTATION, mldsa_pk_hex, principal_id))
            conn.execute("INSERT INTO principal_keys (principal_id, key_id, seq, mldsa_public_key, mlkem_public_key, status, "
                         "created_at) VALUES (?, ?, 1, ?, ?, 'PENDING', ?)",
                         (principal_id, key_id, mldsa_pk_hex, mlkem_ek_hex, now))
            if role == "RECIPIENT":
                conn.execute("INSERT INTO recipients (recipient_id, name, role, mlkem_public_key, mldsa_public_key, status, "
                             "created_at) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                             (principal_id, principal["name"], principal.get("title") or "Recipient",
                              mlkem_ek_hex, mldsa_pk_hex, now))
        conn.close()
    except Exception:
        ks_path.unlink(missing_ok=True)
        raise
    return {"principal_id": principal_id, "key_id": key_id, "status": PENDING_ATTESTATION,
            "mldsa_pk_sha256": sha256_hex(bytes.fromhex(mldsa_pk_hex)),
            "mlkem_pk_sha256": sha256_hex(bytes.fromhex(mlkem_ek_hex)) if mlkem_ek_hex else None}


# ---------------------------------------------------------------- rotation

def rotate_keys(principal_id: str, current_passphrase: str, new_passphrase: str) -> dict:
    """
    Generates a new key pair for a recipient or investigator. The previous signing key is
    destroyed (the keystore is rewritten without it); the previous ML-KEM key is kept as
    retired so documents already encrypted to it remain readable. The new key is PENDING
    until attested; until then the principal cannot sign new evidence.
    """
    principal = get_principal(principal_id)
    if not principal or principal["status"] != ACTIVE:
        raise IdentityError("Only active principals can rotate keys")
    role = principal["role"]
    if role not in ("RECIPIENT", "INVESTIGATOR"):
        raise IdentityError("Authority key rollover requires a new installation trust anchor (key ceremony)")
    conn = get_connection()
    pending = conn.execute("SELECT 1 FROM principal_keys WHERE principal_id = ? AND status = 'PENDING'",
                           (principal_id,)).fetchone()
    max_seq = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM principal_keys WHERE principal_id = ?",
                           (principal_id,)).fetchone()[0]
    conn.close()
    if pending:
        raise IdentityError("A key rotation is already awaiting attestation")

    old = keystore.unlock_keystore(principal_id, current_passphrase)
    old_key_id = keystore.keystore_info(principal_id)["key_id"]
    new_secrets, mldsa_pk_hex, mlkem_ek_hex = _generate_keys(role)
    retired = {name: v for name, v in old.items() if name.startswith(keystore.RETIRED_PREFIX)}
    if "mlkem_dk" in old:
        retired[keystore.RETIRED_PREFIX + old_key_id] = old["mlkem_dk"]
    new_secrets.update(retired)
    seq = max_seq + 1
    key_id = f"{principal_id}#{seq}"
    now = _now()

    keystore._check_passphrase(new_passphrase)
    conn = get_connection()
    try:
        conn.execute("INSERT INTO principal_keys (principal_id, key_id, seq, mldsa_public_key, mlkem_public_key, status, "
                     "created_at) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                     (principal_id, key_id, seq, mldsa_pk_hex, mlkem_ek_hex, now))
        try:
            keystore.write_keystore(principal_id, role, key_id, new_passphrase, new_secrets, replace=True)
        except Exception:
            conn.execute("UPDATE principal_keys SET status = 'REJECTED' WHERE key_id = ?", (key_id,))
            raise
    finally:
        conn.close()
        old.clear()
    return {"principal_id": principal_id, "key_id": key_id, "previous_key_id": old_key_id, "status": "PENDING",
            "mldsa_pk_sha256": sha256_hex(bytes.fromhex(mldsa_pk_hex)),
            "mlkem_pk_sha256": sha256_hex(bytes.fromhex(mlkem_ek_hex)) if mlkem_ek_hex else None}


def change_passphrase(principal_id: str, current_passphrase: str, new_passphrase: str) -> None:
    """Re-encrypts the same key material under a new passphrase (fresh salt and nonce)."""
    info = keystore.keystore_info(principal_id)
    keys = keystore.unlock_keystore(principal_id, current_passphrase)
    try:
        keystore.write_keystore(principal_id, info["role"], info["key_id"] if keys.get("mldsa_sk") else None,
                                new_passphrase, keys, replace=True)
    finally:
        keys.clear()
