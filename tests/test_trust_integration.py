"""
Signed trust-anchor manifest (controlled data ingestion) tests.

Covers valid / invalid / modified / stale / conflicting / duplicate / malformed packages,
missing or malformed trust anchor, empty and corrupted local store, rollback,
registry substitution, revocation, credential failures and network-disconnected operation.
External trust failures must never break encryption, decryption or ledger integrity,
and must always make attribution fail closed.
"""

import hashlib
import json
import socket

import pytest

from testenv import authority_material, login_headers, run_basic_flow, sample_pdf, upload
from app import trust
from app.crypto.identity import provision_principal
from app.crypto.pqc_dsa import dsa_keygen
from app.database.connection import get_connection, init_db


def _next(revoke=None, **overrides):
    pk, sk = authority_material()
    m = trust.build_next_manifest("WESEE_HQ", pk, trust.DEFAULT_ORGANIZATION, trust.DEFAULT_PUBLISHER,
                                  "test", revoke)
    m.update(overrides)
    return m, sk


def _import(raw: bytes):
    _, sk = authority_material()
    return trust.import_package(raw, "test-import", "WESEE_HQ", sk)


def _code(raw: bytes) -> str:
    with pytest.raises(trust.TrustError) as exc:
        _import(raw)
    return exc.value.code


def _valid_pkg() -> dict:
    m, sk = _next()
    return json.loads(trust.sign_manifest(m, sk))


def _investigate(client, flow, rid="R002"):
    r = client.post("/api/investigate", files=upload(flow["copies"][rid], "leak.pdf"), headers=flow["inv"])
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ valid data

def test_valid_package_imports_with_provenance_and_duplicate_is_idempotent(clean_ledger):
    m, sk = _next()
    raw = trust.sign_manifest(m, sk)
    res = _import(raw)
    assert res["status"] == trust.IMPORTED and res["version"] == m["version"]
    cur = trust.current_manifest()
    assert cur["version"] == m["version"]
    assert cur["manifest_sha256"] == hashlib.sha256(json.dumps(
        m, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert cur["source_label"] == "test-import" and cur["imported_by"] == "WESEE_HQ" and cur["imported_at"]
    assert cur["manifest"]["source"]["publisher"] == trust.DEFAULT_PUBLISHER
    assert _import(raw)["status"] == trust.ALREADY_IMPORTED


# ------------------------------------------------------------------ invalid data

@pytest.mark.parametrize("raw", [
    b"",
    b"\xff\xfe\x00",
    b"not json",
    b"[]",
    b'{"manifest": {}, "manifest": {}, "signature": "00"}',
    b'{"manifest": 1.5, "signature": "00"}',
    b'{"manifest": {}}',
    b'{"manifest": {}, "signature": "zz"}',
])
def test_malformed_packages_rejected(creds, raw):
    assert _code(raw) == trust.MALFORMED


def test_oversized_package_rejected(creds):
    assert _code(b"{" + b" " * (trust.MAX_PACKAGE_BYTES + 1) + b"}") == trust.MALFORMED


@pytest.mark.parametrize("mutate", [
    lambda m: m.update(extra="x"),
    lambda m: m.update(manifest_type="OTHER"),
    lambda m: m.update(version=0),
    lambda m: m.update(version=True),
    lambda m: m.update(issued_at="yesterday"),
    lambda m: m["principals"][0].update(principal_id="../etc"),
    lambda m: next(e for e in m["principals"] if e["role"] == "RECIPIENT").update(mlkem_pk_sha256=None),
    lambda m: next(e for e in m["principals"] if e["role"] == "RECIPIENT").update(status="REVOKED"),
    lambda m: m["issuer"].update(mldsa_public_key="ab" * 10),
    lambda m: m.update(principals=[]),
])
def test_schema_violations_rejected(creds, mutate):
    pkg = _valid_pkg()
    mutate(pkg["manifest"])
    assert _code(json.dumps(pkg).encode()) == trust.SCHEMA_INVALID


def test_modified_source_data_fails_signature(creds):
    pkg = _valid_pkg()
    entry = next(e for e in pkg["manifest"]["principals"] if e["principal_id"] == "R002")
    entry["mldsa_pk_sha256"] = hashlib.sha256(dsa_keygen()[0]).hexdigest()
    assert _code(json.dumps(pkg).encode()) == trust.SIGNATURE_INVALID

    pkg = _valid_pkg()
    pkg["manifest"]["source"]["publisher"] = "Forged publisher"
    assert _code(json.dumps(pkg).encode()) == trust.SIGNATURE_INVALID


def test_package_from_unpinned_authority_rejected(creds):
    foreign_pk, foreign_sk = dsa_keygen()
    m, _ = _next()
    m["issuer"]["mldsa_public_key"] = foreign_pk.hex()
    next(e for e in m["principals"] if e["principal_id"] == "WESEE_HQ")["mldsa_pk_sha256"] = \
        hashlib.sha256(foreign_pk).hexdigest()
    assert _code(trust.sign_manifest(m, foreign_sk)) == trust.PIN_MISMATCH


# ------------------------------------------------------------ version control

def test_stale_version_rejected(creds):
    base = trust.current_manifest()["version"]
    m_future, sk = _next(version=base + 2)
    assert _import(trust.sign_manifest(m_future, sk))["status"] == trust.IMPORTED
    m_old, sk = _next(version=base + 1)
    assert _code(trust.sign_manifest(m_old, sk)) == trust.STALE


def test_conflicting_same_version_rejected(creds):
    cur = trust.current_manifest()
    m, sk = _next(version=cur["version"], issued_at="2020-01-01T00:00:00+00:00")
    assert _code(trust.sign_manifest(m, sk)) == trust.CONFLICT


def test_revocation_and_keys_cannot_be_rolled_back(creds):
    provision_principal("R900", "RECIPIENT", "Temp Officer", "temp-passphrase-900")
    pk, sk = authority_material()
    trust.issue_and_import("WESEE_HQ", pk, sk, "test", "enrol R900")
    trust.issue_and_import("WESEE_HQ", pk, sk, "test", "revoke R900", revoke=["R900"])

    m, sk = _next()
    entry = next(e for e in m["principals"] if e["principal_id"] == "R900")
    assert entry["status"] == "REVOKED"
    entry["status"], entry["revoked_at"] = "ACTIVE", None
    assert _code(trust.sign_manifest(m, sk)) == trust.CONFLICT

    m, sk = _next()
    next(e for e in m["principals"] if e["principal_id"] == "R001")["mldsa_pk_sha256"] = "1" * 64
    assert _code(trust.sign_manifest(m, sk)) == trust.CONFLICT

    m, sk = _next()
    m["principals"] = [e for e in m["principals"] if e["principal_id"] != "R001"]
    assert _code(trust.sign_manifest(m, sk)) == trust.CONFLICT


# -------------------------------------------------- unavailable / corrupted source

def test_missing_trust_anchor_fails_attribution_but_core_keeps_working(client, clean_ledger, monkeypatch, tmp_path):
    monkeypatch.setenv("SIH_AUTHORITY_PIN_FILE", str(tmp_path / "absent.pin"))
    flow = run_basic_flow(client, "DOC-NOPIN")
    res = _investigate(client, flow)
    assert res["status"] == "UNVERIFIED" and res["attribution"] is None
    assert res["verification"]["identity_trusted"] is False
    assert all(v for k, v in res["verification"].items() if k != "identity_trusted")
    assert any("UNPINNED" in f["reason"] for f in res["failures"])
    assert client.get("/api/ledger/verify", headers=flow["aud"]).json()["chain_valid"] is True


def test_malformed_pin_is_unpinned(creds, monkeypatch, tmp_path):
    bad = tmp_path / "bad.pin"
    bad.write_text("not-a-fingerprint")
    monkeypatch.setenv("SIH_AUTHORITY_PIN_FILE", str(bad))
    with pytest.raises(trust.TrustError) as exc:
        trust.authority_pin()
    assert exc.value.code == trust.UNPINNED
    with pytest.raises(trust.TrustError) as exc:
        trust.write_authority_pin("0" * 64)
    assert exc.value.code == trust.PIN_MISMATCH


def test_empty_trust_store_is_not_available(creds, monkeypatch, tmp_path):
    monkeypatch.setenv("SIH_DATA_DIR", str(tmp_path))
    init_db()
    res = trust.verify_principal_key("R002", "RECIPIENT", b"x" * 1312, "2026-01-01T00:00:00+00:00")
    assert res["trusted"] is False and "NOT_AVAILABLE" in res["reason"]


def test_corrupted_local_snapshot_detected(client, clean_ledger):
    flow = run_basic_flow(client, "DOC-CORRUPT")
    conn = get_connection()
    row = conn.execute("SELECT version, package FROM trust_manifests ORDER BY version DESC LIMIT 1").fetchone()
    conn.execute("DROP TRIGGER trust_no_update")
    conn.execute("UPDATE trust_manifests SET package = ? WHERE version = ?",
                 (row["package"].replace("Officer Bravo", "Officer Mallory"), row["version"]))
    conn.close()
    try:
        with pytest.raises(trust.TrustError) as exc:
            trust.current_manifest()
        assert exc.value.code == trust.CORRUPTED
        res = _investigate(client, flow)
        assert res["status"] == "UNVERIFIED" and res["verification"]["identity_trusted"] is False
    finally:
        conn = get_connection()
        conn.execute("DROP TRIGGER IF EXISTS trust_no_update")
        conn.execute("UPDATE trust_manifests SET package = ? WHERE version = ?", (row["package"], row["version"]))
        conn.close()
        init_db()
    assert _investigate(client, flow)["status"] == "VERIFIED"


def test_deleting_latest_manifest_is_detected_as_rollback(clean_ledger):
    pk, sk = authority_material()
    trust.issue_and_import("WESEE_HQ", pk, sk, "test", "version recorded in ledger")
    conn = get_connection()
    row = dict(conn.execute("SELECT * FROM trust_manifests ORDER BY version DESC LIMIT 1").fetchone())
    conn.execute("DROP TRIGGER trust_no_delete")
    conn.execute("DELETE FROM trust_manifests WHERE version = ?", (row["version"],))
    conn.close()
    try:
        with pytest.raises(trust.TrustError) as exc:
            trust.current_manifest()
        assert exc.value.code == trust.CORRUPTED and "rollback" in str(exc.value)
    finally:
        conn = get_connection()
        conn.execute("INSERT INTO trust_manifests VALUES (:version, :manifest_sha256, :package, :issuer_fingerprint, "
                     ":issued_at, :source_label, :imported_by, :imported_at)", row)
        conn.close()
        init_db()
    assert trust.current_manifest()["version"] == row["version"]


def test_trust_store_tables_are_append_only(creds):
    conn = get_connection()
    try:
        for sql in ("UPDATE trust_manifests SET source_label = 'x'", "DELETE FROM trust_manifests",
                    "UPDATE audit_events SET outcome = 'x'", "DELETE FROM audit_events"):
            with pytest.raises(Exception):
                conn.execute(sql)
    finally:
        conn.close()


def test_registry_key_substitution_is_not_trusted_and_not_relaunderable(creds):
    conn = get_connection()
    original = conn.execute("SELECT mldsa_public_key FROM recipients WHERE recipient_id = 'R002'").fetchone()[0]
    rogue_pk = dsa_keygen()[0]
    conn.execute("UPDATE recipients SET mldsa_public_key = ? WHERE recipient_id = 'R002'", (rogue_pk.hex(),))
    conn.execute("UPDATE principals SET mldsa_public_key = ? WHERE principal_id = 'R002'", (rogue_pk.hex(),))
    conn.close()
    try:
        res = trust.verify_principal_key("R002", "RECIPIENT", rogue_pk, "2026-01-01T00:00:00+00:00")
        assert res["trusted"] is False and "does not match" in res["reason"]
        with pytest.raises(trust.TrustError) as exc:
            _next()
        assert exc.value.code == trust.REGISTRY_DRIFT
    finally:
        conn = get_connection()
        conn.execute("UPDATE recipients SET mldsa_public_key = ? WHERE recipient_id = 'R002'", (original,))
        conn.execute("UPDATE principals SET mldsa_public_key = ? WHERE principal_id = 'R002'", (original,))
        conn.close()


# ------------------------------------------------------------------ API workflow

def test_enrolment_revocation_lifecycle(client, clean_ledger):
    hq = login_headers(client, "WESEE_HQ")
    before = trust.current_manifest()["version"]
    r = client.post("/api/recipients/create", headers=hq, json={
        "recipient_id": "R777", "name": "Officer Delta", "role": "Signals", "initial_passphrase": "delta-passphrase-777"})
    assert r.status_code == 200, r.text
    cur = trust.current_manifest()
    assert cur["version"] == before + 1
    assert any(e["principal_id"] == "R777" for e in cur["manifest"]["principals"])

    r777 = {"Authorization": "Bearer " + client.post("/api/auth/login", json={
        "principal_id": "R777", "passphrase": "delta-passphrase-777"}).json()["token"]}
    raw = sample_pdf("DELTA BRIEF")
    assert client.post("/api/documents/register", data={"document_id": "DOC-R777"}, files=upload(raw),
                       headers=hq).status_code == 200
    assert client.post("/api/documents/encrypt", json={"document_id": "DOC-R777", "authorized_recipient_ids": ["R777"]},
                       headers=hq).status_code == 200
    dec = client.post("/api/decrypt", json={"document_id": "DOC-R777"}, headers=r777).json()
    leaked = client.get(dec["decrypted_file_path"], headers=r777).content

    r = client.post("/api/trust/revoke", json={"principal_id": "R777", "reason": "key compromise"}, headers=hq)
    assert r.status_code == 200, r.text
    assert r.json()["sessions_terminated"] >= 1 and "R777" in r.json()["revoked_principals"]

    assert client.get("/api/auth/me", headers=r777).status_code == 401
    assert client.post("/api/auth/login", json={"principal_id": "R777", "passphrase": "delta-passphrase-777"}
                       ).status_code == 401
    assert client.post("/api/documents/register", data={"document_id": "DOC-R777B"}, files=upload(raw),
                       headers=hq).status_code == 200
    assert client.post("/api/documents/encrypt", json={"document_id": "DOC-R777B", "authorized_recipient_ids": ["R777"]},
                       headers=hq).status_code == 400

    inv = login_headers(client, "INVESTIGATOR_01")
    res = client.post("/api/investigate", files=upload(leaked, "leak.pdf"), headers=inv).json()
    assert res["status"] == "VERIFIED", res["failures"]
    assert res["attribution"]["recipient_id"] == "R777"
    assert res["trust_anchor"]["manifest_version"] == trust.current_manifest()["version"]
    assert client.get("/api/ledger/verify", headers=inv).json()["chain_valid"] is True


def test_trust_api_authorization_and_transfer(client, clean_ledger):
    hq = login_headers(client, "WESEE_HQ")
    inv = login_headers(client, "INVESTIGATOR_01")
    aud = login_headers(client, "AUDITOR_01")
    r001 = login_headers(client, "R001")
    pkg_file = {"file": ("m.json", b"{}", "application/json")}

    assert client.post("/api/trust/import", data={"source_label": "x-node"}, files=pkg_file).status_code == 401
    assert client.post("/api/trust/import", data={"source_label": "x-node"}, files=pkg_file, headers=inv).status_code == 403
    assert client.post("/api/trust/revoke", json={"principal_id": "R002", "reason": "nope"}, headers=r001).status_code == 403
    assert client.post("/api/trust/issue", headers=aud).status_code == 403
    assert client.get("/api/trust/manifest", headers=r001).status_code == 403

    view = client.get("/api/trust/manifest", headers=inv).json()
    assert view["available"] is True and view["authority_pin"] == trust.authority_pin()
    assert "mldsa_public_key" not in view["current"]["issuer"]

    exported = client.get("/api/trust/manifest/export", headers=aud)
    assert exported.status_code == 200
    r = client.post("/api/trust/import", data={"source_label": "transfer-media"},
                    files={"file": ("m.json", exported.content, "application/json")}, headers=hq)
    assert r.status_code == 200 and r.json()["status"] == trust.ALREADY_IMPORTED

    assert client.post("/api/trust/import", data={"source_label": "x-node"}, files=pkg_file,
                       headers=hq).status_code == 400
    assert client.post("/api/trust/revoke", json={"principal_id": "WESEE_HQ", "reason": "self"},
                       headers=hq).status_code == 400
    assert client.post("/api/trust/revoke", json={"principal_id": "NOBODY", "reason": "unknown"},
                       headers=hq).status_code == 400


# ------------------------------------------------------------------ offline

def test_full_workflow_with_network_disabled(client, clean_ledger, monkeypatch):
    def no_network(*_a, **_k):
        raise OSError("network disabled for this test")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)

    flow = run_basic_flow(client, "DOC-OFFLINE")
    res = _investigate(client, flow)
    assert res["status"] == "VERIFIED" and res["attribution"]["recipient_id"] == "R002"
    assert all(res["verification"].values())
