"""
Forensic attribution engine tests (Phase 5/6). The critical invariant:
NO INVALID EVIDENCE MAY PRODUCE VERIFIED ATTRIBUTION.
"""

import pymupdf
import pytest

import testenv
from app import forensics
from app.database.connection import drop_append_only_triggers, get_connection, init_db
from app.ledger.verify import simulate_tampering


def _investigate(client, headers, pdf):
    r = client.post("/api/investigate", files=testenv.upload(pdf), headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def flow(client, clean_ledger):
    return testenv.run_basic_flow(client, "DOC-I1", ("R001", "R002", "R003"))


def test_exact_matching_document_verified(client, flow):
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "VERIFIED"
    assert res["attribution"]["recipient_id"] == "R002"
    assert all(res["verification"].values())
    assert res["failures"] == []
    import hashlib
    from app.crypto.identity import get_recipient_public_keys
    expected_fp = hashlib.sha256(get_recipient_public_keys("R002")["mldsa_pk"]).hexdigest()
    assert res["attribution"]["signer_public_key_sha256"] == expected_fp


def test_each_recipient_attributed_to_self(client, flow):
    for rid in ("R001", "R002", "R003"):
        res = _investigate(client, flow["inv"], flow["copies"][rid])
        assert res["status"] == "VERIFIED" and res["attribution"]["recipient_id"] == rid


def test_modified_document_unverified(client, flow):
    doc = pymupdf.open(stream=flow["copies"]["R002"], filetype="pdf")
    doc[0].insert_text((50, 500), "edited", fontsize=8)
    edited = doc.tobytes()
    doc.close()
    conn = get_connection()
    try:
        first_event_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM audit_events").fetchone()[0]
    finally:
        conn.close()
    res = _investigate(client, flow["inv"], edited)
    assert res["status"] == "CORRELATED" and res["attribution"] is None
    assert res["verification"]["document_hash_match"] is False
    assert all(res[field] is None for field in (
        "recipient_id", "recipient_name", "recipient_role", "document_id", "session_id",
        "decryption_timestamp", "block_index", "block_hash", "watermark_token"))
    stored_report = client.get(f"/api/reports/{res['report']['report_id']}", headers=flow["inv"]).json()["report"]
    assert stored_report["attribution"] is None
    conn = get_connection()
    try:
        events = conn.execute("SELECT event, details FROM audit_events WHERE principal_id = ? AND id > ?",
                              ("INVESTIGATOR_01", first_event_id)).fetchall()
    finally:
        conn.close()
    assert not any(e["event"] == "SIGNATURE_VERIFIED" for e in events)
    assert not any(e["event"] in ("ATTRIBUTION_CORRELATED", "DOCUMENT_HASH_VERIFIED") for e in events)
    assert all("token_ref" not in e["details"] for e in events)


def test_appended_bytes_unverified(client, flow):
    res = _investigate(client, flow["inv"], flow["copies"]["R002"] + b"\n%trailing")
    assert res["status"] == "CORRELATED"
    assert res["attribution"] is None and res["recipient_id"] is None
    assert res["verification"]["document_hash_match"] is False


def test_resaved_document_unverified(client, flow):
    """Honest limitation: a re-saved copy keeps the marker but loses exact-hash evidence."""
    doc = pymupdf.open(stream=flow["copies"]["R002"], filetype="pdf")
    resaved = doc.tobytes(garbage=4)
    doc.close()
    res = _investigate(client, flow["inv"], resaved)
    assert res["status"] == "CORRELATED"
    assert res["attribution"] is None and res["recipient_id"] is None
    assert res["verification"]["watermark_valid"] is True


def test_clean_unknown_document(client, flow):
    res = _investigate(client, flow["inv"], testenv.sample_pdf("UNRELATED"))
    assert res["status"] == "NOT_ATTRIBUTABLE" and res["attribution_verdict"] == "NOT ATTRIBUTABLE"


def test_non_pdf_upload(client, flow):
    res = _investigate(client, flow["inv"], b"just some bytes")
    assert res["status"] == "NOT_ATTRIBUTABLE" and res["watermark_status"] == "UNREADABLE"


def test_invalid_signature_unverified(client, flow, monkeypatch):
    monkeypatch.setattr(forensics, "dsa_verify_hex", lambda *a, **k: False)
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "NOT_ATTRIBUTABLE" and res["verification"]["signature_valid"] is False
    assert res["verification"]["document_hash_match"] is True


def test_valid_signature_but_broken_ledger(client, flow):
    """Tampering an unrelated block leaves R002's signature valid but must withdraw attribution."""
    simulate_tampering(1, "timestamp", "2020-01-01T00:00:00+00:00")
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "NOT_ATTRIBUTABLE"
    assert res["verification"]["signature_valid"] is True
    assert res["verification"]["ledger_chain_valid"] is False


def test_forged_session_row_rejected(client, flow):
    """An attacker edits the session row so a forged document's hash 'matches'."""
    tok = flow["dec"]["R002"]["watermark_token"]
    from app.watermark.embed import embed_watermark
    from app.crypto.symmetric import compute_sha256
    forged = embed_watermark(testenv.sample_pdf("FORGED CONTENT"), tok)
    conn = get_connection()
    drop_append_only_triggers(conn)
    conn.execute("UPDATE sessions SET delivered_document_hash = ? WHERE watermark_token = ?", (compute_sha256(forged), tok))
    conn.close()
    init_db()
    res = _investigate(client, flow["inv"], forged)
    assert res["status"] == "NOT_ATTRIBUTABLE"
    assert res["verification"]["document_hash_match"] is True
    assert res["verification"]["record_consistent"] is False


def test_session_reassigned_to_other_recipient_rejected(client, flow):
    tok = flow["dec"]["R002"]["watermark_token"]
    conn = get_connection()
    drop_append_only_triggers(conn)
    conn.execute("UPDATE sessions SET recipient_id = 'R003' WHERE watermark_token = ?", (tok,))
    conn.close()
    init_db()
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "NOT_ATTRIBUTABLE" and res["verification"]["record_consistent"] is False


def test_ledger_record_reattributed_rejected(client, flow):
    simulate_tampering(flow["dec"]["R002"]["block_index"], "canonical_record", {"recipient_id": "R003"})
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "NOT_ATTRIBUTABLE" and res["attribution"] is None


def test_ledger_record_deleted(client, flow):
    simulate_tampering(flow["dec"]["R002"]["block_index"], "delete")
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "NOT_ATTRIBUTABLE"
    assert res["verification"]["ledger_record_found"] is False


def test_verification_error_fails_closed(client, flow, monkeypatch):
    def boom():
        raise RuntimeError("ledger unavailable")
    monkeypatch.setattr(forensics, "verify_ledger", boom)
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "VERIFICATION_ERROR" and res["attribution"] is None
    assert res["recipient_id"] is None


def test_database_unavailable_fails_closed(client, flow, monkeypatch):
    def broken():
        raise RuntimeError("db down")
    monkeypatch.setattr(forensics, "get_connection", broken)
    res = _investigate(client, flow["inv"], flow["copies"]["R002"])
    assert res["status"] == "VERIFICATION_ERROR" and res["attribution"] is None


def test_invariant_no_mutation_verifies(client, flow):
    base = flow["copies"]["R002"]
    mutations = [
        base[:-1],
        base + b" ",
        base.replace(b"%PDF-1.", b"%PDF-2.", 1),
        base[: len(base) // 2] + bytes([base[len(base) // 2] ^ 0x01]) + base[len(base) // 2 + 1:],
        flow["copies"]["R001"],  # a different recipient's valid copy must never attribute to R002
        testenv.sample_pdf(),
    ]
    for m in mutations:
        res = _investigate(client, flow["inv"], m)
        if m == flow["copies"]["R001"]:
            assert res["status"] == "VERIFIED" and res["attribution"]["recipient_id"] == "R001"
            continue
        assert m != base
        assert res["status"] != "VERIFIED"
        assert res["recipient_id"] is None
