"""
End-to-end proof for SIH26237 (runs against an isolated data directory).

 1. Authority registers a confidential document.
 2. Authority broadcast-encrypts it for R001, R002, R003.
 3. Each recipient decrypts independently (authenticated, own keystore).
 4. Each session receives a unique opaque forensic marker.
 5. Recipient copies are visually equivalent (0 differing pixel samples, measured).
 6. R002's copy is treated as leaked.
 7-13. Investigation: marker extracted, session located, document hash matches,
       record consistent, signature verifies, ledger record found, chain verifies
       -> VERIFIED attribution to R002.
14. Clean document -> UNVERIFIED.
15. Modified leaked document -> UNVERIFIED (hash mismatch).
16. Unauthorized recipient cannot decrypt / cannot impersonate.
17. Modified ledger is detected and attribution is withdrawn.
18. No plaintext private keys exist on disk.

Run with pytest or directly: python tests/test_e2e_workflow.py
"""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testenv  # noqa: E402

import pymupdf  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _upload(pdf: bytes, name="doc.pdf"):
    return {"file": (name, io.BytesIO(pdf), "application/pdf")}


def run_end_to_end_demonstration(verbose: bool = True):
    from app.auth import clear_all_sessions
    from app.config import keystore_dir
    from app.database.connection import reset_test_database
    from app.main import app

    log = print if verbose else (lambda *a, **k: None)
    testenv.provision_test_principals()
    reset_test_database()
    clear_all_sessions()

    with TestClient(app) as client:
        hq = testenv.login_headers(client, "WESEE_HQ")
        inv = testenv.login_headers(client, "INVESTIGATOR_01")
        aud = testenv.login_headers(client, "AUDITOR_01")
        rec = {rid: testenv.login_headers(client, rid) for rid in ("R001", "R002", "R003")}

        log("=" * 72)
        log("SIH26237 - END-TO-END FORENSIC ATTRIBUTION PROOF")
        log("=" * 72)

        raw_pdf = testenv.sample_pdf("TACTICAL DIRECTIVE: OPERATION SINDHURAKSHAK")
        r = client.post("/api/documents/register", data={"document_id": "DOC-2026-001", "classification": "CONFIDENTIAL"},
                        files=_upload(raw_pdf, "operation_brief.pdf"), headers=hq)
        assert r.status_code == 200, r.text
        log(f"[1]  Registered DOC-2026-001, SHA-256 {r.json()['original_hash'][:16]}... (authority-signed block)")

        r = client.post("/api/documents/encrypt", json={"document_id": "DOC-2026-001",
                                                        "authorized_recipient_ids": ["R001", "R002", "R003"]}, headers=hq)
        assert r.status_code == 200, r.text
        log(f"[2]  Broadcast-encrypted for {r.json()['authorized_recipients']}")

        dec = {}
        for rid in ("R001", "R002", "R003"):
            r = client.post("/api/decrypt", json={"document_id": "DOC-2026-001", "passphrase": testenv.passphrase(rid)}, headers=rec[rid])
            assert r.status_code == 200, r.text
            dec[rid] = r.json()
            assert dec[rid]["recipient_id"] == rid
        log("[3]  R001, R002, R003 decrypted independently (identity from session, keys from own keystore)")

        tokens = {d["watermark_token"] for d in dec.values()}
        sessions = {d["session_id"] for d in dec.values()}
        assert len(tokens) == 3 and len(sessions) == 3
        log("[4]  Three distinct sessions and three distinct opaque 256-bit markers")

        r = client.post("/api/forensics/invariance", json={"session_a": dec["R001"]["session_id"],
                                                           "session_b": dec["R002"]["session_id"]}, headers=aud)
        assert r.status_code == 200, r.text
        inv_res = r.json()
        assert inv_res["is_visually_identical"] is True and inv_res["render_hash_a"] == inv_res["render_hash_b"]
        log(f"[5]  Measured visual invariance R001 vs R002: identical 150-DPI render hash {inv_res['render_hash_a'][:16]}...")

        leaked = client.get(dec["R002"]["decrypted_file_path"], headers=rec["R002"]).content
        assert leaked.startswith(b"%PDF")
        log("[6]  R002's delivered copy treated as leaked")

        report = client.post("/api/investigate", files=_upload(leaked, "LEAKED.pdf"), headers=inv).json()
        v = report["verification"]
        assert report["status"] == "VERIFIED", report
        assert all(v.values()), v
        assert report["attribution"]["recipient_id"] == "R002"
        assert report["attribution"]["session_id"] == dec["R002"]["session_id"]
        log("[7]  Marker extracted            : " + str(v["watermark_found"] and v["watermark_valid"]))
        log("[8]  Session located             : " + str(v["session_found"]))
        log("[9]  Document hash matches       : " + str(v["document_hash_match"]))
        log("[10] Signature verifies          : " + str(v["signature_valid"]) + " (record consistent: "
            + str(v["record_consistent"]) + ")")
        log("[11] Ledger record exists        : " + str(v["ledger_record_found"]))
        log("[12] Ledger chain verifies       : " + str(v["ledger_chain_valid"]))
        log(f"[13] {report['attribution_verdict']}")

        clean = client.post("/api/investigate", files=_upload(raw_pdf), headers=inv).json()
        assert clean["status"] in ("UNVERIFIED", "NOT_ATTRIBUTABLE") and clean["attribution"] is None
        assert clean["verification"]["watermark_found"] is False
        log(f"[14] Clean document -> {clean['status']} ({clean['attribution_verdict']})")

        doc = pymupdf.open(stream=leaked, filetype="pdf")
        doc[0].insert_text((50, 400), "ALTERED", fontsize=10)
        modified = doc.tobytes()
        doc.close()
        mod = client.post("/api/investigate", files=_upload(modified), headers=inv).json()
        assert mod["status"] in ("UNVERIFIED", "CORRELATED", "NOT_ATTRIBUTABLE")
        assert mod["recipient_id"] is None
        assert mod["attribution"] is None
        assert mod["watermark_token"] is None
        stored_report = client.get(f"/api/reports/{mod['report']['report_id']}", headers=inv).json()["report"]
        assert stored_report["attribution"] is None
        assert mod["verification"]["watermark_valid"] is True
        assert mod["verification"]["document_hash_match"] is False
        log(f"[15] Modified leaked copy (marker intact) -> {mod['status']}: document_hash_match=False")

        r = client.post("/api/documents/register", data={"document_id": "DOC-2026-002"},
                        files=_upload(testenv.sample_pdf("SECOND BRIEF")), headers=hq)
        assert r.status_code == 200
        assert client.post("/api/documents/encrypt", json={"document_id": "DOC-2026-002",
                                                           "authorized_recipient_ids": ["R001"]}, headers=hq).status_code == 200
        denied = client.post("/api/decrypt", json={"document_id": "DOC-2026-002", "passphrase": testenv.passphrase("R003")}, headers=rec["R003"])
        spoof = client.post("/api/decrypt", json={"document_id": "DOC-2026-001", "recipient_id": "R002", "passphrase": testenv.passphrase("R003")}, headers=rec["R003"])
        stolen = client.get(dec["R002"]["decrypted_file_path"], headers=rec["R003"])
        assert denied.status_code == 403 and spoof.status_code == 403 and stolen.status_code == 404
        log("[16] Unauthorized R003: decrypt DOC-2026-002 -> 403, impersonate R002 -> 403, fetch R002 copy -> 404")

        t = client.post("/api/ledger/tamper-test", json={"block_index": dec["R002"]["block_index"],
                                                         "field": "canonical_record",
                                                         "new_value": '{"recipient_id": "R003"}'}, headers=aud)
        assert t.status_code == 200
        audit = client.get("/api/ledger/verify", headers=aud).json()
        assert audit["chain_valid"] is False and audit["broken_block_index"] == dec["R002"]["block_index"]
        after = client.post("/api/investigate", files=_upload(leaked), headers=inv).json()
        assert after["status"] in ("UNVERIFIED", "NOT_ATTRIBUTABLE") and after["verification"]["ledger_chain_valid"] is False
        log(f"[17] Ledger tamper detected at Block #{audit['broken_block_index']}; same leak now -> {after['status']}")

        leftovers = list(keystore_dir().glob("*.key.json"))
        assert not leftovers
        for pid in ("WESEE_HQ", "R001", "R002", "R003"):
            ks = (keystore_dir() / f"{pid}.keystore.json").read_bytes()
            for key in testenv.unlocked_keys(pid).values():
                assert key.hex().encode() not in ks and key not in ks
        log("[18] No plaintext private keys on disk: keystores contain no key bytes/hex")

        log("=" * 72)
        log("ALL 18 END-TO-END PROOF STEPS PASSED")
        log("=" * 72)


def test_end_to_end(creds):
    run_end_to_end_demonstration(verbose=False)


if __name__ == "__main__":
    run_end_to_end_demonstration()
