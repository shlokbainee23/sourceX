"""
Forensic attribution engine for SIH26237.

Pipeline (every step is evaluated and recorded; attribution requires ALL to pass):
  1. extract forensic marker            -> watermark_found / watermark_valid
  2. locate decryption session          -> session_found
  3. SHA-256(uploaded) == recorded delivered_document_hash   -> document_hash_match
  4. reconstruct canonical record from the session and compare byte-for-byte with
     the ledger's stored record (and record_hash, signer)   -> record_consistent
  5. locate exactly one ledger decryption block for the token -> ledger_record_found
  6. verify recipient ML-DSA-44 signature over the canonical record -> signature_valid
  7. verify the complete ledger chain + head anchor           -> ledger_chain_valid
  8. the decryption record links to exactly one authority-signed registration and one
     broadcast-encryption block for the same source hash, both earlier in the chain,
     and the encryption block authorized this recipient      -> document_provenance_valid
  9. the recipient's signing key is the one attested by the pinned authority in the
     local signed trust manifest and was not revoked before the decryption -> identity_trusted

Fail closed: an exception at any point yields VERIFICATION_ERROR with no attribution.
A watermark match alone never produces attribution.
"""

import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional

from app.audit import record_audit
from app.crypto.identity import get_recipient_public_keys
from app.crypto.pqc_dsa import dsa_verify_hex
from app.crypto.symmetric import compute_sha256
from app.database.connection import get_connection
from app.ledger.canonical import canonicalize_json
from app.ledger.records import build_decryption_record_from_session
from app.ledger.verify import verify_ledger
from app.trust import verify_principal_key
from app.watermark.extract import FOUND, NOT_FOUND, UNREADABLE, extract_watermark_detailed

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
VERIFICATION_ERROR = "VERIFICATION_ERROR"

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


def _token_ref(token: Optional[str]) -> Optional[str]:
    return hashlib.sha256(token.encode()).hexdigest()[:16] if token else None


def investigate_document(content: bytes, investigator_id: Optional[str] = None) -> Dict[str, Any]:
    evidence = {name: False for name in CHECKS}
    failures: List[Dict[str, str]] = []
    context: Dict[str, Any] = {}
    uploaded_hash = compute_sha256(content)
    record_audit("INVESTIGATION_STARTED", investigator_id, uploaded_document_hash=uploaded_hash)

    context["investigator_id"] = investigator_id
    try:
        _run_pipeline(content, uploaded_hash, evidence, failures, context)
        status = VERIFIED if all(evidence.values()) and not failures else UNVERIFIED
    except Exception as exc:
        status = VERIFICATION_ERROR
        failures.append({"check": "pipeline", "reason": f"Verification could not be completed ({type(exc).__name__})"})

    for name in CHECKS:
        if not evidence[name] and not any(f["check"] == name for f in failures):
            failures.append({"check": name, "reason": "Not established"})

    attribution = None
    if status == VERIFIED:
        attribution = {
            "recipient_id": context["recipient_id"],
            "recipient_name": context.get("recipient_name"),
            "recipient_role": context.get("recipient_role"),
            "document_id": context["document_id"],
            "session_id": context["session_id"],
            "decryption_timestamp": context["decryption_timestamp"],
            "block_index": context["block_index"],
            "block_hash": context["block_hash"],
            "signer_public_key_sha256": context["signer_public_key_sha256"],
            "classification": context.get("classification"),
        }
        verdict = f"CRYPTOGRAPHICALLY VERIFIED ATTRIBUTION: {attribution['recipient_id']} ({attribution['recipient_name']})"
        reason = ("All evidence checks passed: marker, session, exact document hash, signed record, ledger record, "
                  "full chain, document provenance and authority-attested signer identity.")
        record_audit("ATTRIBUTION_VERIFIED", investigator_id, recipient_id=attribution["recipient_id"],
                     session_id=attribution["session_id"], block_index=attribution["block_index"])
    else:
        verdict = "VERIFICATION ERROR - NO ATTRIBUTION" if status == VERIFICATION_ERROR else "NO VERIFIED ATTRIBUTION"
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
        "watermark_token": context.get("token"),
        "watermark_status": context.get("watermark_status"),
        "ledger_error": context.get("ledger_error"),
        "trust_anchor": context.get("trust_anchor"),
    }
    # Flat fields kept for the existing UI; populated only for VERIFIED results.
    for key in ("recipient_id", "recipient_name", "recipient_role", "document_id", "session_id",
                "decryption_timestamp", "block_index", "block_hash"):
        result[key] = attribution[key] if attribution else None
    result["document_hash_match"] = evidence["document_hash_match"]
    result["signature_valid"] = evidence["signature_valid"]
    result["ledger_chain_valid"] = evidence["ledger_chain_valid"]
    return result


def _run_pipeline(content: bytes, uploaded_hash: str, evidence: dict, failures: list, context: dict) -> None:
    actor = context.get("investigator_id")
    # 1. Marker extraction and validation
    wm = extract_watermark_detailed(content)
    context["watermark_status"] = wm.status
    evidence["watermark_found"] = wm.status not in (NOT_FOUND, UNREADABLE)
    if wm.status == FOUND:
        evidence["watermark_valid"] = True
        context["token"] = wm.token
        record_audit("WATERMARK_FOUND", actor, token_ref=_token_ref(wm.token))
    else:
        failures.append({"check": "watermark_found" if not evidence["watermark_found"] else "watermark_valid",
                         "reason": wm.reason})

    # 7 is independent of the token, so the chain is always audited.
    chain = verify_ledger()
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
    blocks = [b for b in all_blocks if b["event_type"] == "DOCUMENT_DECRYPTED"]

    # 2. Session lookup
    if not session:
        failures.append({"check": "session_found",
                         "reason": "Marker is well-formed but no decryption session exists for it (unknown token)"})
    else:
        evidence["session_found"] = True

        # 3. Exact document hash comparison
        recorded = session["delivered_document_hash"]
        if hmac.compare_digest(uploaded_hash, recorded):
            evidence["document_hash_match"] = True
            record_audit("DOCUMENT_HASH_VERIFIED", actor, session_id=session["session_id"])
        else:
            failures.append({"check": "document_hash_match",
                             "reason": "Uploaded document SHA-256 does not match the delivered copy recorded for this session "
                                       "(document modified or marker transplanted)"})

    # 5. Ledger record lookup: exactly one decryption block for this token
    matches = []
    for b in blocks:
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

    # 4. Reconstruct the canonical record from the session and compare with the ledger
    if session:
        reconstructed = canonicalize_json(build_decryption_record_from_session(session))
        consistent = (
            reconstructed == ledger_bytes
            and block["canonical_record"] == ledger_bytes.decode("utf-8")
            and hashlib.sha256(reconstructed).hexdigest() == block["record_hash"]
            and block["signer_id"] == session["recipient_id"] == ledger_record.get("recipient_id")
            and session["signature"] == block["signature"]
            and session["block_index"] == block["block_index"]
        )
        if consistent:
            evidence["record_consistent"] = True
        else:
            failures.append({"check": "record_consistent",
                             "reason": "Session record and ledger record disagree (evidence altered)"})

    # 6. Signature by the recipient named in the signed record
    recipient_id = ledger_record.get("recipient_id")
    keys = get_recipient_public_keys(recipient_id, include_revoked=True) if isinstance(recipient_id, str) else None
    if keys and block["signer_id"] == recipient_id and dsa_verify_hex(keys["mldsa_pk"], ledger_bytes, block["signature"]):
        evidence["signature_valid"] = True
        record_audit("SIGNATURE_VERIFIED", actor, recipient_id=recipient_id, block_index=block["block_index"])
    else:
        failures.append({"check": "signature_valid",
                         "reason": "Recipient ML-DSA-44 signature over the canonical record did not verify"})

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
        if (reg_b["block_index"] < enc_b["block_index"] < block["block_index"]
                and reg_rec.get("original_hash") == enc_rec.get("original_hash") == ledger_record.get("source_document_hash")
                and isinstance(authorized, list) and recipient_id in authorized):
            evidence["document_provenance_valid"] = True
        else:
            failures.append({"check": "document_provenance_valid",
                             "reason": "Decryption record does not follow a matching registration and a broadcast "
                                       "encryption that authorized this recipient"})
    else:
        failures.append({"check": "document_provenance_valid",
                         "reason": "Expected exactly one registration and one broadcast-encryption block for this document"})

    # 9. Signer identity attested by the pinned authority in the local trust manifest
    if keys:
        trust = verify_principal_key(recipient_id, "RECIPIENT", keys["mldsa_pk"],
                                     ledger_record.get("decryption_timestamp"))
        context["trust_anchor"] = {k: trust[k] for k in ("manifest_version", "manifest_sha256", "authority_pin")}
        if trust["trusted"]:
            evidence["identity_trusted"] = True
        else:
            failures.append({"check": "identity_trusted", "reason": trust["reason"]})

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
        "signer_public_key_sha256": hashlib.sha256(keys["mldsa_pk"]).hexdigest() if keys else None,
    })
