"""
Tamper-evident ledger adversarial tests: modified, deleted, inserted, reordered blocks,
modified header fields, truncation, append-only enforcement, fail-closed verification.
"""

import sqlite3

import pytest

import testenv
from app.database.connection import drop_append_only_triggers, get_connection, init_db
from app.ledger import verify as verify_mod
from app.ledger.blockchain import LedgerError, commit_event, compute_block_hash, compute_record_hash, sign_record
from app.ledger.records import build_decryption_record
from app.ledger.verify import simulate_tampering, verify_ledger


@pytest.fixture
def chain(client, clean_ledger):
    flow = testenv.run_basic_flow(client, "DOC-L1", ("R001", "R002", "R003"))
    assert verify_ledger()["chain_valid"] is True
    return flow  # blocks: 1 REGISTERED, 2 ENCRYPTED, 3-5 DECRYPTED


def _assert_broken(expected_index=None):
    res = verify_ledger()
    assert res["chain_valid"] is False, res
    if expected_index is not None:
        assert res["broken_block_index"] == expected_index, res
    return res


def test_valid_chain(chain):
    res = verify_ledger()
    assert res["total_blocks"] == 5 and res["verified_blocks"] == 5
    assert all(d["signature_status"] == "VALID_ML_DSA_44" for d in res["verification_details"])


@pytest.mark.parametrize("field,value", [
    ("canonical_record", '{"recipient_id": "R001"}'),
    ("timestamp", "2020-01-01T00:00:00+00:00"),
    ("signer_id", "R001"),
    ("previous_hash", "f" * 64),
    ("signature", "00" * 2420),
    ("event_type", "DOCUMENT_REGISTERED"),
    ("record_hash", "a" * 64),
    ("block_hash", "b" * 64),
])
def test_modified_block_detected(chain, field, value):
    simulate_tampering(4, field, value)
    res = _assert_broken()
    assert res["broken_block_index"] in (4, 5)


def test_modified_authority_block_detected(chain):
    simulate_tampering(2, "canonical_record", '{"authorized_recipients": ["R001","R002","R003","R999"]}')
    _assert_broken(2)


def test_deleted_middle_block_detected(chain):
    simulate_tampering(3, "delete")
    _assert_broken(4)


def test_deleted_last_block_detected_by_anchor(chain):
    simulate_tampering(5, "delete")
    res = _assert_broken()
    assert "anchor" in res["error_message"]


def test_reordered_blocks_detected(chain):
    simulate_tampering(3, "swap_with_next")
    _assert_broken(3)


def test_inserted_validly_signed_block_detected(chain):
    """Even a correctly chained, genuinely signed block appended outside the app is detected."""
    conn = get_connection()
    tail = conn.execute("SELECT block_index, block_hash FROM ledger_blocks ORDER BY block_index DESC LIMIT 1").fetchone()
    rec = build_decryption_record(document_id="DOC-L1", recipient_id="R001", session_id="SES-FORGED",
                                  watermark_token="WM-" + "e" * 64, source_document_hash="0" * 64,
                                  delivered_document_hash="1" * 64, decryption_timestamp="2026-01-01T00:00:00+00:00")
    sig = sign_record(testenv.unlocked_keys("R001")["mldsa_sk"], rec)
    from app.ledger.canonical import canonicalize_json
    idx, ts = tail["block_index"] + 1, "2026-01-01T00:00:00+00:00"
    rh = compute_record_hash(rec)
    bh = compute_block_hash(idx, ts, "DOCUMENT_DECRYPTED", tail["block_hash"], rh, sig, "R001")
    conn.execute("INSERT INTO ledger_blocks (block_index, timestamp, event_type, previous_hash, record_hash, "
                 "canonical_record, signature, signer_id, block_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                 (idx, ts, "DOCUMENT_DECRYPTED", tail["block_hash"], rh, canonicalize_json(rec).decode(), sig, "R001", bh))
    conn.close()
    res = _assert_broken()
    assert "anchor" in res["error_message"]


def test_inserted_block_forged_signature_detected(chain):
    """Attacker re-chains a block claiming R002 but signed with R003's key."""
    conn = get_connection()
    tail = conn.execute("SELECT block_index, block_hash FROM ledger_blocks ORDER BY block_index DESC LIMIT 1").fetchone()
    rec = build_decryption_record(document_id="DOC-L1", recipient_id="R002", session_id="SES-FRAME",
                                  watermark_token="WM-" + "d" * 64, source_document_hash="0" * 64,
                                  delivered_document_hash="1" * 64, decryption_timestamp="2026-01-01T00:00:00+00:00")
    sig = sign_record(testenv.unlocked_keys("R003")["mldsa_sk"], rec)
    from app.ledger.canonical import canonicalize_json
    idx, ts = tail["block_index"] + 1, "2026-01-01T00:00:00+00:00"
    rh = compute_record_hash(rec)
    bh = compute_block_hash(idx, ts, "DOCUMENT_DECRYPTED", tail["block_hash"], rh, sig, "R002")
    conn.execute("INSERT INTO ledger_blocks (block_index, timestamp, event_type, previous_hash, record_hash, "
                 "canonical_record, signature, signer_id, block_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                 (idx, ts, "DOCUMENT_DECRYPTED", tail["block_hash"], rh, canonicalize_json(rec).decode(), sig, "R002", bh))
    conn.close()
    res = _assert_broken(idx)
    assert "signature" in res["error_message"]


def test_duplicate_token_in_ledger_detected(client, clean_ledger):
    rec = build_decryption_record(document_id="D", recipient_id="R001", session_id="S1", watermark_token="WM-" + "c" * 64,
                                  source_document_hash="0" * 64, delivered_document_hash="1" * 64,
                                  decryption_timestamp="2026-01-01T00:00:00+00:00")
    keys = testenv.unlocked_keys("R001")
    commit_event("DOCUMENT_DECRYPTED", rec, sign_record(keys["mldsa_sk"], rec), "R001")
    rec2 = dict(rec, session_id="S2")
    commit_event("DOCUMENT_DECRYPTED", rec2, sign_record(keys["mldsa_sk"], rec2), "R001")
    res = _assert_broken(2)
    assert "Duplicate" in res["error_message"]


def test_append_only_triggers_block_mutation(chain):
    conn = get_connection()
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE ledger_blocks SET signer_id = 'R003' WHERE block_index = 3")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM ledger_blocks WHERE block_index = 5")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE sessions SET recipient_id = 'R003'")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM sessions")
    conn.close()
    assert verify_ledger()["chain_valid"] is True


def test_append_refused_after_truncation(chain):
    simulate_tampering(5, "delete")
    rec = {"record_type": "DOCUMENT_REGISTRATION", "record_version": "2.0", "authority_id": "WESEE_HQ",
           "document_id": "X", "original_hash": "0" * 64, "timestamp": "t"}
    with pytest.raises(LedgerError):
        commit_event("DOCUMENT_REGISTERED", rec, sign_record(testenv.unlocked_keys("WESEE_HQ")["mldsa_sk"], rec), "WESEE_HQ")


def test_unknown_event_type_refused(chain):
    with pytest.raises(LedgerError):
        commit_event("ARBITRARY_EVENT", {"a": 1}, "00", "R001")


def test_non_canonical_storage_detected(chain):
    """Same JSON content, different byte layout -> treated as tampering."""
    conn = get_connection()
    drop_append_only_triggers(conn)
    row = conn.execute("SELECT canonical_record FROM ledger_blocks WHERE block_index = 3").fetchone()
    conn.execute("UPDATE ledger_blocks SET canonical_record = ? WHERE block_index = 3", (row[0].replace(",", ", "),))
    conn.close()
    init_db()
    _assert_broken(3)


def test_verification_fails_closed_on_internal_error(chain, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("key registry unavailable")
    monkeypatch.setattr(verify_mod, "get_recipient_public_keys", boom)
    res = verify_ledger()
    assert res["chain_valid"] is False and "VERIFICATION_ERROR" in res["error_message"]


def test_concurrent_appends_keep_chain_valid(client, clean_ledger):
    from concurrent.futures import ThreadPoolExecutor
    authority = testenv.unlocked_keys("WESEE_HQ")

    def append(i):
        rec = {"record_type": "DOCUMENT_REGISTRATION", "record_version": "2.0", "authority_id": "WESEE_HQ",
               "document_id": f"C{i}", "original_hash": "0" * 64, "timestamp": str(i)}
        return commit_event("DOCUMENT_REGISTERED", rec, sign_record(authority["mldsa_sk"], rec), "WESEE_HQ")

    with ThreadPoolExecutor(max_workers=8) as pool:
        blocks = list(pool.map(append, range(16)))
    assert sorted(b["block_index"] for b in blocks) == list(range(1, 17))
    res = verify_ledger()
    assert res["chain_valid"] is True and res["total_blocks"] == 16


def test_substituted_signer_key_fails(chain):
    from app.crypto.pqc_dsa import dsa_keygen
    conn = get_connection()
    original = conn.execute("SELECT mldsa_public_key FROM recipients WHERE recipient_id = 'R003'").fetchone()[0]
    conn.execute("UPDATE recipients SET mldsa_public_key = ? WHERE recipient_id = 'R003'", (dsa_keygen()[0].hex(),))
    conn.close()
    try:
        _assert_broken()
    finally:
        conn = get_connection()
        conn.execute("UPDATE recipients SET mldsa_public_key = ? WHERE recipient_id = 'R003'", (original,))
        conn.close()


def test_revocation_does_not_invalidate_earlier_signatures(chain):
    conn = get_connection()
    conn.execute("UPDATE recipients SET status = 'REVOKED' WHERE recipient_id = 'R003'")
    conn.close()
    try:
        assert verify_ledger()["chain_valid"] is True
    finally:
        conn = get_connection()
        conn.execute("UPDATE recipients SET status = 'ACTIVE' WHERE recipient_id = 'R003'")
        conn.close()
