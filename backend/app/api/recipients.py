"""
Recipients and Cryptographic Identity API Endpoints for SIH26237.
Only public keys are ever returned.

Recipients are enrolled without the authority ever learning their passphrase or
private key: the authority creates the identity and receives a one-time enrollment
code; the recipient redeems it (POST /api/enroll), chooses a passphrase and gets fresh
keys; the authority then attests the key fingerprint confirmed out of band.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.audit import record_audit
from app.auth import AuthSession, current_session, require_roles
from app.crypto.identity import IdentityError, create_pending_principal
from app.database.connection import get_connection
from app.models.schemas import InvestigatorCreate, RecipientCreate, RecipientResponse

router = APIRouter(prefix="/api/recipients", tags=["recipients"])


def _row_to_response(r) -> RecipientResponse:
    return RecipientResponse(
        recipient_id=r["recipient_id"],
        name=r["name"],
        role=r["role"],
        mlkem_public_key=r["mlkem_public_key"],
        mldsa_public_key=r["mldsa_public_key"],
        status=r["status"],
        created_at=r["created_at"],
    )


@router.get("", response_model=List[RecipientResponse])
def list_recipients(_: AuthSession = Depends(current_session)):
    """Public-key directory of registered recipients (display only; encryption uses attested keys)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM recipients ORDER BY recipient_id ASC").fetchall()
    finally:
        conn.close()
    return [_row_to_response(r) for r in rows]


@router.post("/create")
def create_recipient(payload: RecipientCreate, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """Creates a recipient identity awaiting enrollment and returns the one-time enrollment code."""
    try:
        result = create_pending_principal(payload.recipient_id, "RECIPIENT", payload.name, payload.role,
                                          session.principal_id)
    except IdentityError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit("ENROLLMENT_CODE_ISSUED", session.principal_id, principal=payload.recipient_id, role="RECIPIENT")
    return {**result, "next_step": "Deliver the enrollment code to the recipient out of band. After they enrol, "
                                   "confirm their key fingerprint and attest it (POST /api/trust/attest)."}


@router.post("/create-investigator")
def create_investigator(payload: InvestigatorCreate, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    try:
        result = create_pending_principal(payload.principal_id, "INVESTIGATOR", payload.name, "Investigator",
                                          session.principal_id)
    except IdentityError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit("ENROLLMENT_CODE_ISSUED", session.principal_id, principal=payload.principal_id, role="INVESTIGATOR")
    return result
