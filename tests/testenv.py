"""
Shared isolated test environment for SIH26237 tests.

Importing this module points SIH_DATA_DIR at a fresh temporary directory BEFORE any
application module is imported, so tests never touch the operational data store.
Test passphrases are generated randomly per run.
"""

import os
import secrets
import sys
import tempfile
from pathlib import Path

if "SIH_TEST_DATA_DIR" not in os.environ:
    os.environ["SIH_TEST_DATA_DIR"] = tempfile.mkdtemp(prefix="sih26237-test-")
os.environ["SIH_DATA_DIR"] = os.environ["SIH_TEST_DATA_DIR"]
os.environ["SIH_AUTHORITY_PIN_FILE"] = str(Path(os.environ["SIH_TEST_DATA_DIR"]) / "pin" / "authority.pin")
os.environ["SIH_DEMO_MODE"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.crypto.identity import DEFAULT_PRINCIPALS, principal_exists, provision_principal  # noqa: E402
from app.database.connection import init_db  # noqa: E402

_CREDENTIALS = {}


def provision_test_principals() -> dict:
    """Provision default principals once per process; returns {principal_id: passphrase}."""
    init_db()
    if not _CREDENTIALS:
        for p in DEFAULT_PRINCIPALS:
            pid = p["principal_id"]
            if principal_exists(pid):
                raise RuntimeError("Test data dir already provisioned by another process")
            passphrase = "test-" + secrets.token_urlsafe(16)
            provision_principal(pid, p["role"], p["name"], passphrase, title=p.get("title"))
            _CREDENTIALS[pid] = passphrase
        establish_test_trust()
    return dict(_CREDENTIALS)


def authority_material():
    """(public key, secret key) of WESEE_HQ for tests that sign manifests directly."""
    from app.crypto.identity import get_authority_public_key
    return get_authority_public_key("WESEE_HQ"), unlocked_keys("WESEE_HQ")["mldsa_sk"]


def establish_test_trust():
    import hashlib
    from app import trust
    pk, sk = authority_material()
    trust.write_authority_pin(hashlib.sha256(pk).hexdigest())
    trust.issue_and_import("WESEE_HQ", pk, sk, "test-provisioning", "Test provisioning")


def unlocked_keys(principal_id: str) -> dict:
    from app.crypto.keystore import unlock_keystore
    return unlock_keystore(principal_id, _CREDENTIALS[principal_id])


def login_headers(client, principal_id: str) -> dict:
    res = client.post("/api/auth/login", json={"principal_id": principal_id, "passphrase": _CREDENTIALS[principal_id]})
    assert res.status_code == 200, f"login failed for {principal_id}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['token']}"}


def upload(pdf: bytes, name: str = "doc.pdf") -> dict:
    import io
    return {"file": (name, io.BytesIO(pdf), "application/pdf")}


def run_basic_flow(client, doc_id: str = "DOC-T1", recipients=("R001", "R002", "R003")) -> dict:
    """Register + encrypt + decrypt for each recipient. Returns headers, decryptions and copies."""
    hq = login_headers(client, "WESEE_HQ")
    heads = {rid: login_headers(client, rid) for rid in recipients}
    raw = sample_pdf(f"BRIEF {doc_id}")
    r = client.post("/api/documents/register", data={"document_id": doc_id}, files=upload(raw), headers=hq)
    assert r.status_code == 200, r.text
    r = client.post("/api/documents/encrypt", json={"document_id": doc_id, "authorized_recipient_ids": list(recipients)},
                    headers=hq)
    assert r.status_code == 200, r.text
    dec, copies = {}, {}
    for rid in recipients:
        r = client.post("/api/decrypt", json={"document_id": doc_id}, headers=heads[rid])
        assert r.status_code == 200, r.text
        dec[rid] = r.json()
        copies[rid] = client.get(dec[rid]["decrypted_file_path"], headers=heads[rid]).content
    return {"hq": hq, "recipients": heads, "raw": raw, "dec": dec, "copies": copies,
            "inv": login_headers(client, "INVESTIGATOR_01"), "aud": login_headers(client, "AUDITOR_01")}


def sample_pdf(text: str = "CONFIDENTIAL NAVAL DIRECTIVE") -> bytes:
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "MINISTRY OF DEFENCE - INDIAN NAVY (WESEE)", fontsize=16, color=(0, 0, 0.5))
    page.insert_text((50, 120), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data
