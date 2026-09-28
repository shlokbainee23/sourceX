"""
Encrypted local software keystore tests: unlock, wrong passphrase, corruption,
header tampering, principal swapping, registry mismatch, and API-level denial.
"""

import json
from contextlib import contextmanager

import pytest

import testenv
from app.auth import clear_all_sessions
from app.config import keystore_dir
from app.crypto import keystore
from app.crypto.identity import get_recipient_public_keys


@contextmanager
def preserved(principal_id):
    path = keystore.keystore_path(principal_id)
    original = path.read_bytes()
    try:
        yield path
    finally:
        path.write_bytes(original)
        clear_all_sessions()


def test_unlock_with_correct_passphrase(creds):
    keys = keystore.unlock_keystore("R001", creds["R001"])
    assert set(keys) == {"mlkem_dk", "mldsa_sk"}
    assert set(keystore.unlock_keystore("INVESTIGATOR_01", creds["INVESTIGATOR_01"])) == {"mldsa_sk"}


def test_wrong_passphrase_rejected(creds):
    with pytest.raises(keystore.KeystoreUnlockFailed):
        keystore.unlock_keystore("R001", creds["R001"] + "x")
    with pytest.raises(keystore.KeystoreUnlockFailed):
        keystore.unlock_keystore("R001", creds["R002"])


def test_no_plaintext_private_keys_on_disk(creds):
    assert not list(keystore_dir().glob("*.key.json"))
    for pid in ("WESEE_HQ", "R001", "R002", "R003"):
        raw = keystore.keystore_path(pid).read_bytes()
        doc = json.loads(raw)
        assert {"format", "version", "principal_id", "role", "kdf", "cipher", "ciphertext"}.issubset(set(doc))
        for key in keystore.unlock_keystore(pid, creds[pid]).values():
            assert key not in raw and key.hex().encode() not in raw


def test_salts_and_nonces_unique(creds):
    salts, nonces = set(), set()
    for path in keystore_dir().glob("*.keystore.json"):
        doc = json.loads(path.read_text())
        salts.add(doc["kdf"]["salt"])
        nonces.add(doc["cipher"]["nonce"])
    count = len(list(keystore_dir().glob("*.keystore.json")))
    assert len(salts) == count and len(nonces) == count


def test_ciphertext_corruption_detected(creds):
    with preserved("R002") as path:
        doc = json.loads(path.read_text())
        ct = bytearray.fromhex(doc["ciphertext"])
        ct[20] ^= 0x01
        doc["ciphertext"] = ct.hex()
        path.write_text(json.dumps(doc))
        with pytest.raises(keystore.KeystoreUnlockFailed):
            keystore.unlock_keystore("R002", creds["R002"])


@pytest.mark.parametrize("mutate", [
    lambda d: d["kdf"].__setitem__("n", 2 ** 10),                     # KDF downgrade
    lambda d: d.__setitem__("role", "AUTHORITY"),                      # role relabel
    lambda d: d["cipher"].__setitem__("nonce", "00" * 12),             # nonce swap
    lambda d: d["kdf"].__setitem__("salt", "00" * 16),                 # salt swap
    lambda d: d.__setitem__("version", 99),
])
def test_header_tampering_detected(creds, mutate):
    with preserved("R003") as path:
        doc = json.loads(path.read_text())
        mutate(doc)
        path.write_text(json.dumps(doc))
        with pytest.raises(keystore.KeystoreError):
            keystore.unlock_keystore("R003", creds["R003"])


@pytest.mark.parametrize("content", [b"", b"not json", b"{}", b'{"ciphertext": "zz"}'])
def test_malformed_keystore_detected(creds, content):
    with preserved("R001") as path:
        path.write_bytes(content)
        with pytest.raises(keystore.KeystoreCorrupted):
            keystore.unlock_keystore("R001", creds["R001"])


def test_keystore_swapped_between_principals_rejected(creds):
    with preserved("R002") as path:
        path.write_bytes(keystore.keystore_path("R001").read_bytes())
        with pytest.raises(keystore.KeystoreCorrupted):
            keystore.unlock_keystore("R002", creds["R001"])


def test_missing_keystore(creds):
    with pytest.raises(keystore.KeystoreNotFound):
        keystore.unlock_keystore("NOBODY", "whatever-passphrase")


def test_short_passphrase_refused():
    with pytest.raises(keystore.KeystoreError):
        keystore.create_keystore("SHORTPW", "INVESTIGATOR", "short", {})


def test_create_refuses_overwrite(creds):
    with pytest.raises(keystore.KeystoreError):
        keystore.create_keystore("R001", "RECIPIENT", "another-long-passphrase", {})


def test_api_login_denied_on_wrong_passphrase_and_corruption(client, creds):
    from app.database.connection import reset_test_database
    clear_all_sessions()
    r = client.post("/api/auth/login", json={"principal_id": "R001", "passphrase": "wrong-passphrase-123"})
    assert r.status_code == 401
    with preserved("R001") as path:
        path.write_bytes(b"garbage")
        r = client.post("/api/auth/login", json={"principal_id": "R001", "passphrase": creds["R001"]})
        assert r.status_code == 401
        assert "passphrase" not in r.text.lower() or "invalid" in r.text.lower()
    reset_test_database()
    assert "token" in client.post("/api/auth/login", json={"principal_id": "R001", "passphrase": creds["R001"]}).json()


def test_registry_mismatch_denies_login(client, creds):
    """If the public-key registry is swapped, the unlocked keys no longer match and login fails."""
    from app.database.connection import PERMANENT_TRIGGERS, get_connection
    clear_all_sessions()
    original = get_recipient_public_keys("R002")
    other = get_recipient_public_keys("R003")
    conn = get_connection()
    conn.execute("DROP TRIGGER IF EXISTS keys_no_rekey")
    conn.execute("UPDATE principal_keys SET mldsa_public_key = ? WHERE key_id='R002#1'", (other["mldsa_pk"].hex(),))
    try:
        r = client.post("/api/auth/login", json={"principal_id": "R002", "passphrase": creds["R002"]})
        assert r.status_code == 401
    finally:
        conn.execute("DROP TRIGGER IF EXISTS keys_no_rekey")
        conn.execute("UPDATE principal_keys SET mldsa_public_key = ? WHERE key_id='R002#1'", (original["mldsa_pk"].hex(),))
        conn.execute(PERMANENT_TRIGGERS["keys_no_rekey"])
        conn.close()
        clear_all_sessions()


def test_login_lockout(client, creds):
    clear_all_sessions()
    for _ in range(5):
        client.post("/api/auth/login", json={"principal_id": "R003", "passphrase": "definitely-wrong-pw"})
    r = client.post("/api/auth/login", json={"principal_id": "R003", "passphrase": creds["R003"]})
    assert r.status_code == 401 and "Too many" in r.json()["detail"]
    clear_all_sessions()


def test_legacy_plaintext_migration(tmp_path, monkeypatch):
    """A v1 plaintext key file is migrated into an encrypted keystore and destroyed."""
    import os
    from app.crypto.identity import provision_principal
    from app.crypto.pqc_dsa import dsa_keygen
    from app.crypto.pqc_kem import kem_keygen
    from app.database.connection import get_connection, init_db

    monkeypatch.setenv("SIH_DATA_DIR", str(tmp_path))
    init_db()
    ek, dk = kem_keygen()
    pk, sk = dsa_keygen()
    conn = get_connection()
    conn.execute("INSERT INTO recipients (recipient_id, name, role, mlkem_public_key, mldsa_public_key, created_at) "
                 "VALUES ('R009','Legacy','Legacy',?,?,'2026-01-01')", (ek.hex(), pk.hex()))
    conn.close()
    legacy = keystore_dir() / "R009.key.json"
    legacy.write_text(json.dumps({"mlkem_private_key_hex": dk.hex(), "mldsa_private_key_hex": sk.hex()}))

    result = provision_principal("R009", "RECIPIENT", "Legacy", "legacy-migration-pass")
    assert result["migrated_legacy_keys"] is True
    assert not legacy.exists()
    keys = keystore.unlock_keystore("R009", "legacy-migration-pass")
    assert keys["mlkem_dk"] == dk and keys["mldsa_sk"] == sk
    assert dk.hex().encode() not in keystore.keystore_path("R009").read_bytes()
    assert os.environ["SIH_DATA_DIR"] == str(tmp_path)
