"""
API security tests: authentication, server-side role enforcement, cross-recipient access,
input validation, duplicate/nonexistent resources, secret non-disclosure, audit trail.
"""

import pytest

import testenv
from app import config
from app.auth import clear_all_sessions


@pytest.fixture
def heads(client, clean_ledger):
    return {pid: testenv.login_headers(client, pid)
            for pid in ("WESEE_HQ", "R001", "R002", "R003", "INVESTIGATOR_01", "AUDITOR_01")}


PROTECTED = [
    ("get", "/api/recipients", None),
    ("get", "/api/documents", None),
    ("post", "/api/documents/encrypt", {"document_id": "D", "authorized_recipient_ids": ["R001"]}),
    ("post", "/api/decrypt", {"document_id": "D"}),
    ("get", "/api/ledger", None),
    ("get", "/api/ledger/verify", None),
    ("post", "/api/ledger/tamper-test", {"block_index": 1, "field": "timestamp", "new_value": "x"}),
    ("post", "/api/ledger/reset", None),
    ("get", "/api/audit", None),
    ("get", "/api/auth/me", None),
]


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_unauthenticated_rejected(client, method, path, body):
    r = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
    assert r.status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/api/recipients", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
    assert client.get("/api/recipients", headers={"Authorization": "Basic abc"}).status_code == 401


def test_upload_endpoints_require_auth(client):
    assert client.post("/api/investigate", files=testenv.upload(testenv.sample_pdf())).status_code == 401
    assert client.post("/api/documents/register", data={"document_id": "X"},
                       files=testenv.upload(testenv.sample_pdf())).status_code == 401


@pytest.mark.parametrize("pid", ["R001", "INVESTIGATOR_01", "AUDITOR_01"])
def test_only_authority_registers_and_encrypts(client, heads, pid):
    r = client.post("/api/documents/register", data={"document_id": "DOC-X"}, files=testenv.upload(testenv.sample_pdf()),
                    headers=heads[pid])
    assert r.status_code == 403
    r = client.post("/api/documents/encrypt", json={"document_id": "DOC-X", "authorized_recipient_ids": ["R001"]},
                    headers=heads[pid])
    assert r.status_code == 403


@pytest.mark.parametrize("pid", ["WESEE_HQ", "INVESTIGATOR_01", "AUDITOR_01"])
def test_only_recipients_decrypt(client, heads, pid):
    assert client.post("/api/decrypt", json={"document_id": "DOC-X"}, headers=heads[pid]).status_code == 403


@pytest.mark.parametrize("pid", ["WESEE_HQ", "R002", "AUDITOR_01"])
def test_only_investigator_investigates(client, heads, pid):
    r = client.post("/api/investigate", files=testenv.upload(testenv.sample_pdf()), headers=heads[pid])
    assert r.status_code == 403


def test_recipients_cannot_read_ledger_or_audit(client, heads):
    for path in ("/api/ledger", "/api/ledger/verify", "/api/audit"):
        assert client.get(path, headers=heads["R001"]).status_code == 403


@pytest.mark.parametrize("pid", ["WESEE_HQ", "R001", "INVESTIGATOR_01"])
def test_unauthorized_ledger_mutation(client, heads, pid):
    r = client.post("/api/ledger/tamper-test", json={"block_index": 1, "field": "timestamp", "new_value": "x"},
                    headers=heads[pid])
    assert r.status_code == 403
    if pid != "WESEE_HQ":
        assert client.post("/api/ledger/reset", headers=heads[pid]).status_code == 403


def test_demo_operations_disabled_outside_demo_mode(client, heads, monkeypatch):
    monkeypatch.setenv("SIH_DEMO_MODE", "0")
    r = client.post("/api/ledger/tamper-test", json={"block_index": 1, "field": "timestamp", "new_value": "x"},
                    headers=heads["AUDITOR_01"])
    assert r.status_code == 403
    assert client.post("/api/ledger/reset", headers=heads["AUDITOR_01"]).status_code == 403


def test_recipient_cannot_access_other_recipient_data(client, clean_ledger):
    flow = testenv.run_basic_flow(client, "DOC-A1", ("R001", "R002"))
    r003 = testenv.login_headers(client, "R003")
    r001 = flow["recipients"]["R001"]
    assert client.get(flow["dec"]["R002"]["decrypted_file_path"], headers=r001).status_code == 404
    assert client.get(flow["dec"]["R002"]["decrypted_file_path"], headers=r003).status_code == 404
    assert client.post("/api/decrypt", json={"document_id": "DOC-A1", "passphrase": testenv.passphrase("R003")}, headers=r003).status_code == 403
    assert client.post("/api/decrypt", json={"document_id": "DOC-A1", "recipient_id": "R002", "passphrase": testenv.passphrase("R001")}, headers=r001).status_code == 403
    assert client.get("/api/documents", headers=r003).json() == []
    assert [d["document_id"] for d in client.get("/api/documents", headers=r001).json()] == ["DOC-A1"]


def test_download_path_traversal_blocked(client, clean_ledger):
    flow = testenv.run_basic_flow(client, "DOC-A2", ("R001",))
    h = flow["recipients"]["R001"]
    for evil in ("..%5C..%5Csih26237.sqlite", "..%2F..%2Fsih26237.sqlite", "DOC-A2_original.pdf", "..", "%2e%2e"):
        r = client.get(f"/api/sessions/{evil}/download", headers=h)
        assert r.status_code == 404, evil


@pytest.mark.parametrize("doc_id", ["../../evil", "..\\evil", "a/b", "", "x" * 65, "DOC|1", "..", ".hidden"])
def test_register_rejects_bad_document_ids(client, heads, doc_id):
    r = client.post("/api/documents/register", data={"document_id": doc_id}, files=testenv.upload(testenv.sample_pdf()),
                    headers=heads["WESEE_HQ"])
    assert r.status_code in (400, 422)


def test_register_input_validation(client, heads, monkeypatch):
    hq = heads["WESEE_HQ"]
    assert client.post("/api/documents/register", data={"document_id": "D1"}, headers=hq).status_code == 422
    assert client.post("/api/documents/register", files=testenv.upload(testenv.sample_pdf()), headers=hq).status_code == 422
    assert client.post("/api/documents/register", data={"document_id": "D1", "classification": "ULTRA"},
                       files=testenv.upload(testenv.sample_pdf()), headers=hq).status_code == 400
    assert client.post("/api/documents/register", data={"document_id": "D1"},
                       files=testenv.upload(b"not a pdf"), headers=hq).status_code == 400
    assert client.post("/api/documents/register", data={"document_id": "D1"},
                       files=testenv.upload(b""), headers=hq).status_code == 400
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 100)
    assert client.post("/api/documents/register", data={"document_id": "D1"},
                       files=testenv.upload(testenv.sample_pdf()), headers=hq).status_code == 413


def test_json_bodies_reject_unexpected_and_missing_fields(client, heads):
    hq, r1 = heads["WESEE_HQ"], heads["R001"]
    assert client.post("/api/documents/encrypt", json={"document_id": "D"}, headers=hq).status_code == 422
    assert client.post("/api/documents/encrypt", json={"document_id": "D", "authorized_recipient_ids": []},
                       headers=hq).status_code == 422
    assert client.post("/api/documents/encrypt", json={"document_id": "D", "authorized_recipient_ids": ["R001"],
                                                       "role": "AUTHORITY"}, headers=hq).status_code == 422
    assert client.post("/api/decrypt", json={"document_id": "D", "is_admin": True}, headers=r1).status_code == 422
    assert client.post("/api/decrypt", json={"document_id": "../x"}, headers=r1).status_code == 422
    assert client.post("/api/auth/login", json={"principal_id": "R001"}).status_code == 422
    assert client.post("/api/auth/login", json={"principal_id": "R001", "passphrase": "x", "role": "AUTHORITY"}).status_code == 422


def test_duplicate_and_nonexistent_resources(client, heads):
    hq = heads["WESEE_HQ"]
    pdf = testenv.upload(testenv.sample_pdf())
    assert client.post("/api/documents/register", data={"document_id": "DUP"}, files=pdf, headers=hq).status_code == 200
    assert client.post("/api/documents/register", data={"document_id": "DUP"},
                       files=testenv.upload(testenv.sample_pdf()), headers=hq).status_code == 409
    assert client.post("/api/documents/encrypt", json={"document_id": "DUP", "authorized_recipient_ids": ["R999"]},
                       headers=hq).status_code == 400
    assert client.post("/api/documents/encrypt", json={"document_id": "NOPE", "authorized_recipient_ids": ["R001"]},
                       headers=hq).status_code == 404
    assert client.post("/api/documents/encrypt", json={"document_id": "DUP", "authorized_recipient_ids": ["R001"]},
                       headers=hq).status_code == 200
    assert client.post("/api/documents/encrypt", json={"document_id": "DUP", "authorized_recipient_ids": ["R002"]},
                       headers=hq).status_code == 409
    assert client.post("/api/decrypt", json={"document_id": "NOPE", "passphrase": testenv.passphrase("R001")}, headers=heads["R001"]).status_code in (403, 404)
    assert client.post("/api/forensics/invariance", json={"session_a": "SES-A", "session_b": "SES-B"},
                       headers=heads["AUDITOR_01"]).status_code == 404


def test_plaintext_destroyed_after_encryption(client, clean_ledger):
    from app.config import documents_dir
    testenv.run_basic_flow(client, "DOC-P1", ("R001",))
    assert not (documents_dir() / "DOC-P1_original.pdf").exists()
    assert (documents_dir() / "DOC-P1_encrypted.bin").exists()


def test_repeat_decryption_creates_new_signed_session(client, clean_ledger):
    flow = testenv.run_basic_flow(client, "DOC-R1", ("R001",))
    again = client.post("/api/decrypt", json={"document_id": "DOC-R1", "passphrase": testenv.passphrase("R001")}, headers=flow["recipients"]["R001"]).json()
    assert again["session_id"] != flow["dec"]["R001"]["session_id"]
    assert again["watermark_token"] != flow["dec"]["R001"]["watermark_token"]


def test_login_does_not_reveal_principal_existence(client, creds):
    clear_all_sessions()
    a = client.post("/api/auth/login", json={"principal_id": "NOBODY", "passphrase": "x" * 12})
    b = client.post("/api/auth/login", json={"principal_id": "R001", "passphrase": "x" * 12})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    clear_all_sessions()


def test_logout_invalidates_token(client, creds):
    h = testenv.login_headers(client, "R001")
    assert client.get("/api/auth/me", headers=h).status_code == 200
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_session_expiry(client, creds, monkeypatch):
    import app.auth as auth_mod
    h = testenv.login_headers(client, "R001")
    real = auth_mod.time.time
    monkeypatch.setattr(auth_mod.time, "time", lambda: real() + config.SESSION_TTL_SECONDS + 5)
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_no_secrets_in_responses_or_audit(client, creds, heads):
    import json
    from app.audit import list_audit_events
    from app.crypto.keystore import unlock_keystore
    flow = testenv.run_basic_flow(client, "DOC-S1", ("R002",))
    bodies = [
        client.get("/api/recipients", headers=heads["WESEE_HQ"]).text,
        client.post("/api/auth/login", json={"principal_id": "R002", "passphrase": creds["R002"]}).text,
        json.dumps(flow["dec"]["R002"]),
        client.get("/api/ledger", headers=heads["AUDITOR_01"]).text,
    ]
    audit_dump = json.dumps(list_audit_events(1000))
    keys = unlock_keystore("R002", creds["R002"])
    for blob in bodies + [audit_dump]:
        for k in keys.values():
            assert k.hex() not in blob
        assert creds["R002"] not in blob
    assert "private" not in bodies[0].lower()


def test_audit_trail_records_security_events(client, clean_ledger):
    flow = testenv.run_basic_flow(client, "DOC-AU", ("R001",))
    client.post("/api/investigate", files=testenv.upload(flow["copies"]["R001"]), headers=flow["inv"])
    client.post("/api/investigate", files=testenv.upload(testenv.sample_pdf()), headers=flow["inv"])
    events = {e["event"] for e in client.get("/api/audit?limit=1000", headers=flow["aud"]).json()}
    for expected in ("DOCUMENT_REGISTERED", "DOCUMENT_ENCRYPTED", "DECRYPTION_STARTED", "DECRYPTION_COMPLETED",
                     "WATERMARK_CREATED", "LEDGER_COMMITTED", "INVESTIGATION_STARTED", "WATERMARK_FOUND",
                     "DOCUMENT_HASH_VERIFIED", "SIGNATURE_VERIFIED", "LEDGER_VERIFIED",
                     "ATTRIBUTION_VERIFIED", "ATTRIBUTION_REJECTED", "LOGIN_SUCCEEDED"):
        assert expected in events, expected


def test_errors_do_not_leak_internals(client, heads, monkeypatch):
    import app.api.investigation as inv_mod

    def explode(*a, **k):
        raise RuntimeError("SECRET-INTERNAL-DETAIL")
    monkeypatch.setattr(inv_mod, "get_connection", explode)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        flow = testenv.run_basic_flow(c, "DOC-E1", ("R001", "R002"))
        r = c.post("/api/forensics/invariance", json={"session_a": flow["dec"]["R001"]["session_id"],
                                                      "session_b": flow["dec"]["R002"]["session_id"]},
                   headers=flow["aud"])
    assert r.status_code == 500 and "SECRET-INTERNAL-DETAIL" not in r.text
