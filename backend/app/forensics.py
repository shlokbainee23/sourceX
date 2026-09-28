"""
Forensic attribution engine for SIH26237.

Pipeline (every step is evaluated and recorded):
  1. extract forensic marker (isolated PDF worker)            -> watermark_found / watermark_valid
  2. locate decryption session                                -> session_found
  3. SHA-256(uploaded) == recorded delivered_document_hash    -> document_hash_match
  4. reconstruct canonical record from the session and compare byte-for-byte with
     the ledger's stored record (and record_hash, signer)     -> record_consistent
  5. locate exactly one ledger decryption block for the token -> ledger_record_found
  6. verify the recipient ML-DSA-44 signature under the key named in the record,
     resolved through the signed trust manifest               -> signature_valid
  7. verify the complete ledger chain + head anchor + witness consistency -> ledger_chain_valid
  8. the decryption links to exactly one authority-signed registration and one
     broadcast encryption earlier in the chain that authorized this recipient; for v3
     records also the exact encryption record hash and this recipient's key package
                                                              -> document_provenance_valid
  9. the signing key was attested by the pinned authority and trusted at the block's
     ledger sequence (not revoked / retired / compromised before it) -> identity_trusted

Verdicts:
  VERIFIED          all ten checks pass: the exact delivered file, cryptographically
                    attributed to the recipient's attested key.
  CORRELATED        every check passes except the exact file hash: the marker is bound to
                    a verified, recipient-signed decryption, but the file was modified
                    after delivery. content_match says whether it still renders identically.
  NOT_ATTRIBUTABLE  any other check fails.
  VERIFICATION_ERROR the pipeline could not complete (fail closed, no attribution).
A marker match alone never produces attribution.
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.audit import record_audit
from app.crypto.pqc_dsa import CTX_INVESTIGATION_REPORT, dsa_sign, dsa_verify_hex
from app.crypto.symmetric import compute_sha256
from app.database.connection import get_connection
from app.ledger.blockchain import (RECORD_VERSION, commit_event, ledger_transaction, record_context,
                                   record_signer_key_id, sign_record)
from app.ledger.canonical import canonicalize_json
from app.ledger.records import build_decryption_record_from_session
from app.ledger.verify import verify_ledger
from app.pdf import worker
from app.trust import TrustError, authority_pin, current_manifest, key_valid_at, resolve_key
from app.watermark.extract import FOUND, NOT_FOUND, UNREADABLE

VERIFIED = "VERIFIED"
CORRELATED = "CORRELATED"
NOT_ATTRIBUTABLE = "NOT_ATTRIBUTABLE"
VERIFICATION_ERROR = "VERIFICATION_ERROR"

REPORT_FORMAT = "sih26237-investigation-report"

CHECKS = (
    "watermark_found",
    "watermark_valid",
    "session_found",
    "document_hash_match",
    "record_consistent",
    "ledger_record_found",
    "signature_valid",
    "ledger_chain_valid",
    "document_provenance_valid",
    "identity_trusted",
)

LIMITATIONS = [
    "The marker is a forensic attribution marker, not an unremovable watermark: rasterizing, "
    "printing/scanning, retyping or regenerating the PDF removes it (result: NOT_ATTRIBUTABLE).",
    "Attribution proves that the recipient's attested private key signed the decryption record for this "
    "copy. It does not by itself prove who disclosed the file (shared credentials, a compromised endpoint "
    "or coercion are outside what cryptography can show).",
    "Ledger blocks after the last witness-cosigned checkpoint are only locally tamper-evident.",
    "Timestamps come from the recording host's clock; ordering is established by ledger sequence numbers.",
]


def _token_ref(token: Optional[str]) -> Optional[str]:
    return hashlib.sha256(token.encode()).hexdigest()[:16] if token else None


def investigate_document(content: bytes, investigator_id: Optional[str] = None,
                         signer: Optional[Tuple[bytes, str]] = None) -> Dict[str, Any]:
    evidence = {name: False for name in CHECKS}
    failures: List[Dict[str, str]] = []
    context: Dict[str, Any] = {"investigator_id": investigator_id, "content_match": "UNKNOWN"}
    uploaded_hash = compute_sha256(content)
    record_audit("INVESTIGATION_STARTED", investigator_id, uploaded_document_hash=uploaded_hash)

    try:
        _run_pipeline(content, uploaded_hash, evidence, failures, context)
        if all(evidence.values()) and not failures:
            status = VERIFIED
        elif all(v for k, v in evidence.items() if k != "document_hash_match") and \
                all(f["check"] == "document_hash_match" for f in failures):
            status = CORRELATED
        else:
            status = NOT_ATTRIBUTABLE
    except Exception as exc:
        status = VERIFICATION_ERROR
        failures.append({"check": "pipeline", "reason": f"Verification could not be completed ({type(exc).__name__})"})

    for name in CHECKS:
        if not evidence[name] and not any(f["check"] == name for f in failures):
            failures.append({"check": name, "reason": "Not established"})

    attribution = None
    if status in (VERIFIED, CORRELATED):
        attribution = {k: context.get(k) for k in (
            "recipient_id", "recipient_name", "recipient_role", "document_id", "session_id", "decryption_timestamp",
            "block_index", "block_hash", "signer_public_key_sha256", "signer_key_id", "classification")}
    if status == VERIFIED:
        verdict = f"CRYPTOGRAPHICALLY VERIFIED ATTRIBUTION: {attribution['recipient_id']} ({attribution['recipient_name']})"
        reason = ("All ten evidence checks passed: exact delivered file, marker, session, signed record, ledger "
                  "record, full chain, document provenance and authority-attested signer key.")
        record_audit("ATTRIBUTION_VERIFIED", investigator_id, recipient_id=attribution["recipient_id"],
                     session_id=attribution["session_id"], block_index=attribution["block_index"])
    elif status == CORRELATED:
        verdict = (f"CORRELATED (MODIFIED COPY): marker bound to a verified decryption by {attribution['recipient_id']}; "
                   f"file changed after delivery (content: {context['content_match']})")
        reason = ("Every check passed except the exact file hash. The marker belongs to a verified, recipient-signed "
                  "decryption record, but this file is not byte-identical to the delivered copy.")
        record_audit("ATTRIBUTION_CORRELATED", investigator_id, recipient_id=attribution["recipient_id"],
                     session_id=attribution["session_id"], content_match=context["content_match"])
    else:
        verdict = "VERIFICATION ERROR - NO ATTRIBUTION" if status == VERIFICATION_ERROR else "NOT ATTRIBUTABLE"
        reason = "; ".join(f["reason"] for f in failures if f["reason"] != "Not established") or "Evidence incomplete"
        record_audit("ATTRIBUTION_REJECTED", investigator_id, "REJECTED", status=status,
                     failed_checks=[f["check"] for f in failures], token_ref=_token_ref(context.get("token")))

    result = {
        "status": status,
        "attribution_verdict": verdict,
        "reason": reason,
        "attribution": attribution,
        "verification": evidence,
        "failures": failures,
        "uploaded_document_hash": uploaded_hash,
        "content_match": context["content_match"],
        "uploaded_render_hash": context.get("uploaded_render_hash"),
        "dangerous_features": context.get("dangerous_features", []),
        "watermark_token": context.get("token"),
        "watermark_status": context.get("watermark_status"),
        "ledger_error": context.get("ledger_error"),
        "trust_anchor": context.get("trust_anchor"),
        "witness": context.get("witness"),
        "limitations": LIMITATIONS,
    }
    for key in ("recipient_id", "recipient_name", "recipient_role", "document_id", "session_id",
                "decryption_timestamp", "block_index", "block_hash"):
        result[key] = attribution[key] if status == VERIFIED else None
    result["document_hash_match"] = evidence["document_hash_match"]
    result["signature_valid"] = evidence["signature_valid"]
    result["ledger_chain_valid"] = evidence["ledger_chain_valid"]

    try:
        result["report"] = record_report(result, investigator_id, signer)
    except Exception as exc:
        result["report"] = {"status": "NOT_RECORDED", "reason": f"{type(exc).__name__}: {exc}"[:300]}
    return result


def _run_pipeline(content: bytes, uploaded_hash: str, evidence: dict, failures: list, context: dict) -> None:
    actor = context.get("investigator_id")
    # 1. Marker extraction in the isolated worker
    try:
        wm = worker.extract(content)
    except worker.PdfWorkerError as exc:
        wm = {"status": UNREADABLE, "token": None, "reason": f"PDF could not be processed safely ({exc})",
              "render_hash": None, "dangerous_features": []}
    context["watermark_status"] = wm["status"]
    context["uploaded_render_hash"] = wm.get("render_hash")
    context["dangerous_features"] = wm.get("dangerous_features") or []
    evidence["watermark_found"] = wm["status"] not in (NOT_FOUND, UNREADABLE)
    if wm["status"] == FOUND:
        evidence["watermark_valid"] = True
        context["token"] = wm["token"]
        record_audit("WATERMARK_FOUND", actor, token_ref=_token_ref(wm["token"]))
    else:
        failures.append({"check": "watermark_found" if not evidence["watermark_found"] else "watermark_valid",
                         "reason": wm["reason"]})

    # 7. The chain is always audited (independent of the token).
    chain = verify_ledger()
    context["witness"] = chain.get("witness")
    evidence["ledger_chain_valid"] = chain["chain_valid"] is True
    if evidence["ledger_chain_valid"]:
        record_audit("LEDGER_VERIFIED", actor, total_blocks=chain["total_blocks"])
    else:
        context["ledger_error"] = chain["error_message"]
        failures.append({"check": "ledger_chain_valid", "reason": f"Ledger integrity failure: {chain['error_message']}"})
        record_audit("LEDGER_AUDIT_FAILED", actor, "FAILED", error=chain["error_message"])

    token = context.get("token")
    if not token:
        return

    conn = get_connection()
    try:
        session = conn.execute("SELECT * FROM sessions WHERE watermark_token = ?", (token,)).fetchone()
        all_blocks = conn.execute("SELECT * FROM ledger_blocks ORDER BY block_index ASC").fetchall()
    finally:
        conn.close()

    # 2/3. Session lookup and exact / rendered content comparison
    if not session:
        failures.append({"check": "session_found",
                         "reason": "Marker is well-formed but no decryption session exists for it (unknown token)"})
    else:
        evidence["session_found"] = True
        if hmac.compare_digest(uploaded_hash, session["delivered_document_hash"]):
            evidence["document_hash_match"] = True
            context["content_match"] = "EXACT"
            record_audit("DOCUMENT_HASH_VERIFIED", actor, session_id=session["session_id"])
        else:
            recorded_render = session["delivered_render_hash"] if "delivered_render_hash" in session.keys() else None
            uploaded_render = context.get("uploaded_render_hash")
            if recorded_render and uploaded_render:
                context["content_match"] = "RENDER_IDENTICAL" if hmac.compare_digest(recorded_render, uploaded_render) \
                    else "DIFFERENT"
            failures.append({"check": "document_hash_match",
                             "reason": "Uploaded document SHA-256 does not match the delivered copy recorded for this "
                                       f"session (file modified after delivery; rendered content: {context['content_match']})"})

    # 5. Exactly one ledger decryption block for this token
    matches = []
    for b in all_blocks:
        if b["event_type"] != "DOCUMENT_DECRYPTED":
            continue
        try:
            if json.loads(b["canonical_record"]).get("watermark_token") == token:
                matches.append(b)
        except ValueError:
            continue
    if len(matches) == 1:
        evidence["ledger_record_found"] = True
    elif not matches:
        failures.append({"check": "ledger_record_found", "reason": "No ledger decryption record contains this marker"})
    else:
        failures.append({"check": "ledger_record_found", "reason": "Multiple ledger records claim this marker"})
    block = matches[0] if len(matches) == 1 else None
    if not block:
        return
    ledger_record = json.loads(block["canonical_record"])
    ledger_bytes = canonicalize_json(ledger_record)
    recipient_id = ledger_record.get("recipient_id")
    key_id = record_signer_key_id(ledger_record, block["signer_id"])

    # 4. Session record vs ledger record
    if session:
        reconstructed = canonicalize_json(build_decryption_record_from_session(session))
        consistent = (
            reconstructed == ledger_bytes
            and block["canonical_record"] == ledger_bytes.decode("utf-8")
            and hashlib.sha256(reconstructed).hexdigest() == block["record_hash"]
            and block["signer_id"] == session["recipient_id"] == recipient_id
            and session["signature"] == block["signature"]
            and session["block_index"] == block["block_index"]
        )
        if consistent:
            evidence["record_consistent"] = True
        else:
            failures.append({"check": "record_consistent",
                             "reason": "Session record and ledger record disagree (evidence altered)"})

    # 6 + 9. Signature under the manifest-attested key, trusted at this ledger sequence
    resolved = None
    trust_anchor = {"manifest_version": None, "manifest_sha256": None, "authority_pin": None, "signer_key_id": key_id}
    try:
        trust_anchor["authority_pin"] = authority_pin()
        view = current_manifest()
        trust_anchor["manifest_version"], trust_anchor["manifest_sha256"] = view["version"], view["manifest_sha256"]
        if isinstance(recipient_id, str) and block["signer_id"] == recipient_id:
            resolved = resolve_key(recipient_id, "RECIPIENT", key_id, view)
    except TrustError as exc:
        failures.append({"check": "identity_trusted", "reason": f"Signer key not attested ({exc.code}): {exc}"})
    context["trust_anchor"] = trust_anchor

    if resolved and dsa_verify_hex(resolved["mldsa_pk"], ledger_bytes, block["signature"],
                                   context=record_context(ledger_record)):
        evidence["signature_valid"] = True
        record_audit("SIGNATURE_VERIFIED", actor, recipient_id=recipient_id, block_index=block["block_index"])
    else:
        failures.append({"check": "signature_valid",
                         "reason": "Recipient ML-DSA-44 signature over the canonical record did not verify under the "
                                   "attested key"})
    if resolved:
        ok, why = key_valid_at(resolved, block["block_index"])
        if ok:
            evidence["identity_trusted"] = True
        else:
            failures.append({"check": "identity_trusted", "reason": why})

    # 8. Document provenance: registration -> broadcast encryption -> this decryption
    doc_id = ledger_record.get("document_id")
    reg, enc = [], []
    for b in all_blocks:
        if b["event_type"] not in ("DOCUMENT_REGISTERED", "DOCUMENT_ENCRYPTED"):
            continue
        rec = json.loads(b["canonical_record"])
        if rec.get("document_id") == doc_id:
            (reg if b["event_type"] == "DOCUMENT_REGISTERED" else enc).append((b, rec))
    if len(reg) == 1 and len(enc) == 1:
        (reg_b, reg_rec), (enc_b, enc_rec) = reg[0], enc[0]
        context["classification"] = reg_rec.get("classification")
        authorized = enc_rec.get("authorized_recipients")
        ok = (reg_b["block_index"] < enc_b["block_index"] < block["block_index"]
              and reg_rec.get("original_hash") == enc_rec.get("original_hash") == ledger_record.get("source_document_hash")
              and isinstance(authorized, list) and recipient_id in authorized)
        if ok and ledger_record.get("record_version") == RECORD_VERSION:
            ok = (ledger_record.get("encryption_record_hash") == enc_b["record_hash"]
                  and isinstance(enc_rec.get("package_hashes"), dict)
                  and enc_rec["package_hashes"].get(recipient_id) == ledger_record.get("package_sha256"))
        if ok:
            evidence["document_provenance_valid"] = True
        else:
            failures.append({"check": "document_provenance_valid",
                             "reason": "Decryption record does not follow a matching registration and a broadcast "
                                       "encryption (and key package) that authorized this recipient"})
    else:
        failures.append({"check": "document_provenance_valid",
                         "reason": "Expected exactly one registration and one broadcast-encryption block for this document"})

    conn = get_connection()
    try:
        recip = conn.execute("SELECT name, role FROM recipients WHERE recipient_id = ?", (recipient_id,)).fetchone()
    finally:
        conn.close()
    context.update({
        "recipient_id": recipient_id,
        "recipient_name": recip["name"] if recip else None,
        "recipient_role": recip["role"] if recip else None,
        "document_id": ledger_record.get("document_id"),
        "session_id": ledger_record.get("session_id"),
        "decryption_timestamp": ledger_record.get("decryption_timestamp"),
        "block_index": block["block_index"],
        "block_hash": block["block_hash"],
        "signer_key_id": key_id,
        "signer_public_key_sha256": hashlib.sha256(resolved["mldsa_pk"]).hexdigest() if resolved else None,
    })


# ------------------------------------------------------------------- reports

def build_report(result: Dict[str, Any], investigator_id: Optional[str], signer_key_id: Optional[str]) -> Dict[str, Any]:
    return {
        "format": REPORT_FORMAT,
        "version": 1,
        "report_id": f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(6).upper()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "investigator_id": investigator_id,
        "signer_key_id": signer_key_id,
        "status": result["status"],
        "verdict": result["attribution_verdict"],
        "uploaded_document_hash": result["uploaded_document_hash"],
        "uploaded_render_hash": result.get("uploaded_render_hash"),
        "content_match": result["content_match"],
        "watermark_status": result.get("watermark_status"),
        "watermark_token_sha256": hashlib.sha256(result["watermark_token"].encode()).hexdigest()
        if result.get("watermark_token") else None,
        "checks": result["verification"],
        "failures": result["failures"],
        "attribution": result.get("attribution"),
        "trust_anchor": result.get("trust_anchor"),
        "ledger_chain_valid": result["ledger_chain_valid"],
        "ledger_error": result.get("ledger_error"),
        "witness": {k: (result.get("witness") or {}).get(k) for k in
                    ("status", "witnessed_index", "total_blocks", "unwitnessed_blocks", "threshold")},
        "dangerous_features": result.get("dangerous_features", []),
        "limitations": result["limitations"],
    }


def record_report(result: Dict[str, Any], investigator_id: Optional[str],
                  signer: Optional[Tuple[bytes, str]]) -> Dict[str, Any]:
    """
    Stores the evidence report. With an attested investigator key the report is signed
    (context "sih26237/investigation-report/v1") and its hash is committed to the ledger
    in an investigator-signed INVESTIGATION_RECORDED block.
    """
    sk, key_id = signer if signer else (None, None)
    report = build_report(result, investigator_id, key_id)
    report_bytes = canonicalize_json(report)
    report_sha = hashlib.sha256(report_bytes).hexdigest()
    signature = dsa_sign(sk, report_bytes, context=CTX_INVESTIGATION_REPORT).hex() if sk else None
    block_index = None
    conn = get_connection()
    try:
        if sk and investigator_id:
            record = {
                "record_type": "INVESTIGATION_REPORT",
                "record_version": RECORD_VERSION,
                "investigator_id": investigator_id,
                "signer_key_id": key_id,
                "report_id": report["report_id"],
                "report_sha256": report_sha,
                "status": report["status"],
                "uploaded_document_hash": report["uploaded_document_hash"],
                "subject_block_index": (report["attribution"] or {}).get("block_index"),
                "timestamp": report["created_at"],
            }
            with ledger_transaction(conn) as tx:
                tx["block"] = commit_event("INVESTIGATION_RECORDED", record, sign_record(sk, record), investigator_id,
                                           conn=conn)
                block_index = tx["block"]["block_index"]
                conn.execute(
                    "INSERT INTO investigation_reports (report_id, report, report_sha256, signature, signer_key_id, "
                    "investigator_id, block_index, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (report["report_id"], report_bytes.decode("utf-8"), report_sha, signature, key_id,
                     investigator_id, block_index, report["created_at"]))
        else:
            conn.execute(
                "INSERT INTO investigation_reports (report_id, report, report_sha256, signature, signer_key_id, "
                "investigator_id, block_index, created_at) VALUES (?, ?, ?, ?, ?, ?, NULL, ?)",
                (report["report_id"], report_bytes.decode("utf-8"), report_sha, None, None,
                 investigator_id or "anonymous", report["created_at"]))
    finally:
        conn.close()
    record_audit("INVESTIGATION_REPORT_RECORDED", investigator_id, report_id=report["report_id"],
                 signed=bool(signature), block_index=block_index)
    return {"status": "SIGNED_AND_LEDGERED" if signature else "UNSIGNED", "report_id": report["report_id"],
            "report_sha256": report_sha, "signature": signature, "signer_key_id": key_id, "block_index": block_index}


def verify_report(report_id: str) -> Dict[str, Any]:
    """Re-verifies a stored report: hash, investigator signature (attested key) and ledger commitment."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM investigation_reports WHERE report_id = ?", (report_id,)).fetchone()
        block = conn.execute("SELECT * FROM ledger_blocks WHERE block_index = ?",
                             (row["block_index"],)).fetchone() if row and row["block_index"] else None
    finally:
        conn.close()
    if row is None:
        return {"found": False}
    report = json.loads(row["report"])
    out = {"found": True, "report": report, "report_sha256": row["report_sha256"], "hash_valid": False,
           "signature_valid": False, "ledger_committed": False, "signer_key_id": row["signer_key_id"]}
    raw = canonicalize_json(report)
    out["hash_valid"] = raw.decode("utf-8") == row["report"] and hashlib.sha256(raw).hexdigest() == row["report_sha256"]
    if row["signature"] and row["signer_key_id"]:
        try:
            resolved = resolve_key(row["investigator_id"], "INVESTIGATOR", row["signer_key_id"])
            out["signature_valid"] = dsa_verify_hex(resolved["mldsa_pk"], raw, row["signature"],
                                                    context=CTX_INVESTIGATION_REPORT)
        except TrustError as exc:
            out["signature_error"] = exc.code
    if block is not None:
        rec = json.loads(block["canonical_record"])
        out["ledger_committed"] = (block["event_type"] == "INVESTIGATION_RECORDED"
                                   and rec.get("report_id") == report_id
                                   and rec.get("report_sha256") == row["report_sha256"])
        out["block_index"] = block["block_index"]
    out["valid"] = out["hash_valid"] and out["signature_valid"] and out["ledger_committed"]
    return out
