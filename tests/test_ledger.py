"""
Ledger unit tests for SIH26237: canonicalization, signed hash chaining, verification.
Run with pytest or directly: python tests/test_ledger.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testenv  # noqa: E402,F401

import pytest  # noqa: E402

from app.database.connection import reset_test_database  # noqa: E402
from app.ledger.blockchain import commit_event, sign_record  # noqa: E402
from app.ledger.canonical import CanonicalizationError, canonicalize_json  # noqa: E402
from app.ledger.records import build_decryption_record  # noqa: E402
from app.ledger.verify import simulate_tampering, verify_ledger  # noqa: E402


def test_canonical_json():
    c1 = canonicalize_json({"b": 2, "a": 1, "c": [1, 2, 3]})
    c2 = canonicalize_json({"c": [1, 2, 3], "a": 1, "b": 2})
    assert c1 == c2 == b'{"a":1,"b":2,"c":[1,2,3]}'
    with pytest.raises(CanonicalizationError):
        canonicalize_json({"x": 1.5})
    print("[OK] Deterministic canonical JSON (floats rejected).")


def build_sample_chain():
    """Registration (authority) + two recipient decryption blocks."""
    authority = testenv.unlocked_keys("WESEE_HQ")
    reg = {"record_type": "DOCUMENT_REGISTRATION", "record_version": "2.0", "authority_id": "WESEE_HQ",
           "document_id": "DOC-001", "original_hash": "e3" * 32, "timestamp": "2026-09-26T22:00:00Z"}
    blocks = [commit_event("DOCUMENT_REGISTERED", reg, sign_record(authority["mldsa_sk"], reg), "WESEE_HQ")]
    for rid, n in (("R001", "a"), ("R002", "b")):
        rec = build_decryption_record(document_id="DOC-001", recipient_id=rid, session_id=f"SES-{rid}",
                                      watermark_token="WM-" + n * 64, source_document_hash="e3" * 32,
                                      delivered_document_hash=n * 64, decryption_timestamp="2026-09-26T22:05:00Z",
                                      signer_key_id=f"{rid}#1")
        keys = testenv.unlocked_keys(rid)
        blocks.append(commit_event("DOCUMENT_DECRYPTED", rec, sign_record(keys["mldsa_sk"], rec), rid))
    return blocks


def test_ledger_append_and_verify(creds):
    reset_test_database()
    b = build_sample_chain()
    assert [x["block_index"] for x in b] == [1, 2, 3]
    assert b[1]["previous_hash"] == b[0]["block_hash"] and b[2]["previous_hash"] == b[1]["block_hash"]
    result = verify_ledger()
    assert result["chain_valid"] is True and result["verified_blocks"] == 3, result
    print("[OK] Signed hash chain verifies (3 blocks).")

    simulate_tampering(2, "canonical_record", {"recipient_id": "R003"})
    tampered = verify_ledger()
    assert tampered["chain_valid"] is False and tampered["broken_block_index"] == 2
    print(f"[OK] Tamper detected: {tampered['error_message']}")


if __name__ == "__main__":
    testenv.provision_test_principals()
    test_canonical_json()
    test_ledger_append_and_verify(None)
    print("\nALL LEDGER TESTS PASSED.")
