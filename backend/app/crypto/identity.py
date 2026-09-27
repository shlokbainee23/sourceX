"""
Principal identities and key provisioning for SIH26237.

Every principal (AUTHORITY, RECIPIENT, INVESTIGATOR, AUDITOR) has an encrypted local
software keystore protected by its own passphrase. Public keys live in SQLite;
private keys exist on disk only inside the encrypted keystore and are never
returned by any API.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app import config
from app.crypto import keystore
from app.crypto.pqc_dsa import dsa_keygen, dsa_sign, dsa_verify
from app.crypto.pqc_kem import kem_keygen, kem_encapsulate, kem_decapsulate
from app.database.connection import get_connection, transaction
from app.validation import is_valid_id

ROLES = ("AUTHORITY", "RECIPIENT", "INVESTIGATOR", "AUDITOR")

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


def principal_exists(principal_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM principals WHERE principal_id = ?", (principal_id,)).fetchone()
    conn.close()
    return row is not None and keystore.keystore_path(principal_id).exists()


def provision_principal(principal_id: str, role: str, name: str, passphrase: str, title: Optional[str] = None) -> dict:
    """
    Creates keys + encrypted keystore + registry rows for one principal.
    For recipients with a v1 plaintext key file, the existing keys are migrated into
    the encrypted keystore (public keys stay stable) and the plaintext file is destroyed.
    """
    if not is_valid_id(principal_id):
        raise IdentityError("Invalid principal identifier")
    if role not in ROLES:
        raise IdentityError("Invalid role")
    if principal_exists(principal_id):
        raise IdentityError(f"Principal {principal_id} is already provisioned")

    created_at = datetime.now(timezone.utc).isoformat()
    secrets_map: Dict[str, bytes] = {}
    mldsa_pk_hex = None
    mlkem_ek_hex = None
    migrated = False

    conn = get_connection()
    existing_recipient = conn.execute(
        "SELECT mlkem_public_key, mldsa_public_key FROM recipients WHERE recipient_id = ?", (principal_id,)
    ).fetchone()
    conn.close()

    if role == "RECIPIENT":
        legacy = _load_legacy_recipient_keys(principal_id)
        if legacy and existing_recipient:
            secrets_map = legacy
            mlkem_ek_hex = existing_recipient["mlkem_public_key"]
            mldsa_pk_hex = existing_recipient["mldsa_public_key"]
            migrated = True
        else:
            kem_ek, kem_dk = kem_keygen()
            dsa_pk, dsa_sk = dsa_keygen()
            secrets_map = {"mlkem_dk": kem_dk, "mldsa_sk": dsa_sk}
            mlkem_ek_hex, mldsa_pk_hex = kem_ek.hex(), dsa_pk.hex()
    elif role == "AUTHORITY":
        dsa_pk, dsa_sk = dsa_keygen()
        secrets_map = {"mldsa_sk": dsa_sk}
        mldsa_pk_hex = dsa_pk.hex()

    ks_path = keystore.create_keystore(principal_id, role, passphrase, secrets_map)
    try:
        conn = get_connection()
        with transaction(conn):
            conn.execute(
                "INSERT INTO principals (principal_id, role, name, mldsa_public_key, created_at) VALUES (?, ?, ?, ?, ?)",
                (principal_id, role, name, mldsa_pk_hex, created_at),
            )
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

    return {"principal_id": principal_id, "role": role, "name": name, "migrated_legacy_keys": migrated}


def get_principal(principal_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM principals WHERE principal_id = ?", (principal_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recipient_public_keys(recipient_id: str, include_revoked: bool = False) -> Optional[Dict[str, bytes]]:
    """Loads a recipient's public keys from SQLite. Operational paths (encryption, login)
    use ACTIVE keys only; verification of historical evidence must include revoked keys,
    because revocation does not invalidate signatures made before it."""
    conn = get_connection()
    query = "SELECT mlkem_public_key, mldsa_public_key FROM recipients WHERE recipient_id = ?"
    if not include_revoked:
        query += " AND status = 'ACTIVE'"
    row = conn.execute(query, (recipient_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "mlkem_ek": bytes.fromhex(row["mlkem_public_key"]),
        "mldsa_pk": bytes.fromhex(row["mldsa_public_key"]),
    }


def get_authority_public_key(principal_id: str) -> Optional[bytes]:
    principal = get_principal(principal_id)
    if not principal or principal["role"] != "AUTHORITY" or not principal["mldsa_public_key"]:
        return None
    return bytes.fromhex(principal["mldsa_public_key"])


def verify_keys_match_registry(principal_id: str, role: str, keys: Dict[str, bytes]) -> bool:
    """Proves the unlocked private keys correspond to the registered public keys."""
    probe = b"sih26237-keystore-consistency-probe|" + principal_id.encode()
    if role == "RECIPIENT":
        pub = get_recipient_public_keys(principal_id)
        if not pub or "mlkem_dk" not in keys or "mldsa_sk" not in keys:
            return False
        ss, ct = kem_encapsulate(pub["mlkem_ek"])
        if kem_decapsulate(keys["mlkem_dk"], ct) != ss:
            return False
        return dsa_verify(pub["mldsa_pk"], probe, dsa_sign(keys["mldsa_sk"], probe))
    if role == "AUTHORITY":
        pk = get_authority_public_key(principal_id)
        if not pk or "mldsa_sk" not in keys:
            return False
        return dsa_verify(pk, probe, dsa_sign(keys["mldsa_sk"], probe))
    return keys == {}
