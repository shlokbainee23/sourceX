"""
Forensic leak investigation API for SIH26237.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.documents import get_docs_dir
from app.api.uploads import read_upload
from app.audit import record_audit
from app.auth import AuthSession, require_roles
from app.database.connection import get_connection
from app.forensics import investigate_document
from app.models.schemas import InvarianceRequest, InvestigationResult
from app.watermark.validate import validate_visual_invariance

router = APIRouter(prefix="/api", tags=["investigation"])


@router.post("/investigate", response_model=InvestigationResult)
async def investigate_leaked_document(file: UploadFile = File(...),
                                      session: AuthSession = Depends(require_roles("INVESTIGATOR"))):
    """
    Strict, fail-closed attribution. Returns VERIFIED only when every evidence check
    passes; otherwise UNVERIFIED or VERIFICATION_ERROR with the failed checks listed.
    """
    content = await read_upload(file)
    return investigate_document(content, investigator_id=session.principal_id)


@router.post("/forensics/invariance")
def compare_session_copies(payload: InvarianceRequest,
                           session: AuthSession = Depends(require_roles("INVESTIGATOR", "AUDITOR", "AUTHORITY"))):
    """Renders two delivered copies at 150 DPI and counts differing pixel channel values."""
    conn = get_connection()
    rows = {
        r["session_id"]: r
        for r in conn.execute(
            "SELECT session_id, document_id, delivered_filename FROM sessions WHERE session_id IN (?, ?)",
            (payload.session_a, payload.session_b),
        ).fetchall()
    }
    conn.close()
    if payload.session_a not in rows or payload.session_b not in rows:
        raise HTTPException(status_code=404, detail="Session not found.")
    if payload.session_a == payload.session_b:
        raise HTTPException(status_code=400, detail="Choose two different sessions.")

    docs_dir = get_docs_dir().resolve()
    paths = []
    for sid in (payload.session_a, payload.session_b):
        path = (docs_dir / rows[sid]["delivered_filename"]).resolve()
        if path.parent != docs_dir or not path.is_file():
            raise HTTPException(status_code=404, detail="Delivered copy not found.")
        paths.append(path)

    result = validate_visual_invariance(paths[0].read_bytes(), paths[1].read_bytes())
    record_audit("INVARIANCE_AUDIT", session.principal_id, session_a=payload.session_a,
                 session_b=payload.session_b, differing=result["differing_pixels"])
    return {"session_a": payload.session_a, "session_b": payload.session_b, **result}
