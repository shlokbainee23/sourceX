"""
Forensic leak investigation API for SIH26237.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.common import attested_signing_key
from app.api.uploads import read_upload
from app.audit import record_audit
from app.auth import AuthSession, require_roles
from app.database.connection import get_connection
from app.forensics import investigate_document, verify_report
from app.models.schemas import InvarianceRequest, InvestigationResult
from app.validation import is_valid_id

router = APIRouter(prefix="/api", tags=["investigation"])


@router.post("/investigate", response_model=InvestigationResult)
async def investigate_leaked_document(file: UploadFile = File(...),
                                      session: AuthSession = Depends(require_roles("INVESTIGATOR"))):
    """
    Strict, fail-closed attribution: VERIFIED, CORRELATED (modified copy), NOT_ATTRIBUTABLE or
    VERIFICATION_ERROR, with every check listed. The evidence report is signed with the
    investigator's attested key and committed to the ledger when that key is available.
    """
    content = await read_upload(file)
    try:
        signer = attested_signing_key(session)
    except HTTPException:
        signer = None
    return investigate_document(content, investigator_id=session.principal_id, signer=signer)


@router.get("/reports/{report_id}")
def get_report(report_id: str, session: AuthSession = Depends(require_roles("INVESTIGATOR", "AUDITOR", "AUTHORITY"))):
    """Returns a stored evidence report with an independent re-verification of hash, signature and ledger entry."""
    if not is_valid_id(report_id):
        raise HTTPException(status_code=404, detail="Report not found.")
    result = verify_report(report_id)
    if not result["found"]:
        raise HTTPException(status_code=404, detail="Report not found.")
    record_audit("REPORT_VERIFIED", session.principal_id, report_id=report_id, valid=result["valid"])
    return result


@router.get("/reports")
def list_reports(session: AuthSession = Depends(require_roles("INVESTIGATOR", "AUDITOR", "AUTHORITY"))):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT report_id, report_sha256, investigator_id, signer_key_id, block_index, created_at "
                            "FROM investigation_reports ORDER BY created_at DESC LIMIT 200").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.post("/forensics/invariance")
def compare_session_copies(payload: InvarianceRequest,
                           session: AuthSession = Depends(require_roles("INVESTIGATOR", "AUDITOR", "AUTHORITY"))):
    """
    Compares two delivered copies using the render hashes recorded (and recipient-signed)
    at decryption time: SHA-256 of the 150-DPI rasterization of every page. Delivered
    plaintext copies are not retained, so no copy is re-opened here.
    """
    if payload.session_a == payload.session_b:
        raise HTTPException(status_code=400, detail="Choose two different sessions.")
    conn = get_connection()
    try:
        rows = {r["session_id"]: r for r in conn.execute(
            "SELECT session_id, document_id, recipient_id, delivered_document_hash, source_render_hash, "
            "delivered_render_hash FROM sessions WHERE session_id IN (?, ?)",
            (payload.session_a, payload.session_b)).fetchall()}
    finally:
        conn.close()
    if payload.session_a not in rows or payload.session_b not in rows:
        raise HTTPException(status_code=404, detail="Session not found.")
    a, b = rows[payload.session_a], rows[payload.session_b]
    if not (a["delivered_render_hash"] and b["delivered_render_hash"]):
        raise HTTPException(status_code=409, detail="Render hashes were not recorded for these (legacy) sessions.")
    same_document = a["document_id"] == b["document_id"]
    visually_identical = (same_document and a["delivered_render_hash"] == b["delivered_render_hash"]
                          and a["source_render_hash"] == a["delivered_render_hash"]
                          and b["source_render_hash"] == b["delivered_render_hash"])
    forensically_distinct = a["delivered_document_hash"] != b["delivered_document_hash"]
    record_audit("INVARIANCE_AUDIT", session.principal_id, session_a=payload.session_a,
                 session_b=payload.session_b, visually_identical=visually_identical)
    return {
        "session_a": payload.session_a,
        "session_b": payload.session_b,
        "same_document": same_document,
        "is_visually_identical": visually_identical,
        "forensically_distinct": forensically_distinct,
        "render_hash_a": a["delivered_render_hash"],
        "render_hash_b": b["delivered_render_hash"],
        "delivered_document_hash_a": a["delivered_document_hash"],
        "delivered_document_hash_b": b["delivered_document_hash"],
        "method": "SHA-256 over 150-DPI RGB rasterization of every page, recorded in the recipient-signed record",
    }
