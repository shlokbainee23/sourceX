"""
Recipients and Cryptographic Identity API Endpoints for SIH26237.
Only public keys are ever returned.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app import trust
from app.audit import record_audit
from app.auth import AuthSession, current_session, require_roles
from app.crypto.identity import IdentityError, get_authority_public_key, provision_principal
from app.crypto.keystore import KeystoreError
from app.database.connection import get_connection
from app.models.schemas import RecipientCreate, RecipientResponse

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
    """Public-key directory of registered recipients (any authenticated principal)."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM recipients ORDER BY recipient_id ASC").fetchall()
    conn.close()
    return [_row_to_response(r) for r in rows]


@router.post("/create", response_model=RecipientResponse)
def create_recipient(payload: RecipientCreate, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """AUTHORITY enrols a new recipient; keys are generated into an encrypted keystore."""
    try:
        provision_principal(payload.recipient_id, "RECIPIENT", payload.name, payload.initial_passphrase, title=payload.role)
    except (IdentityError, KeystoreError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit("RECIPIENT_ENROLLED", session.principal_id, recipient_id=payload.recipient_id)
    try:
        result = trust.issue_and_import(session.principal_id, get_authority_public_key(session.principal_id),
                                        session.keys["mldsa_sk"], "local-enrolment",
                                        f"Enrolment of {payload.recipient_id}")
        record_audit("TRUST_MANIFEST_ISSUED", session.principal_id, version=result["version"])
    except trust.TrustError as exc:
        # The recipient exists but is not attested; attribution for them fails closed
        # until POST /api/trust/issue succeeds.
        record_audit("TRUST_MANIFEST_ISSUE_FAILED", session.principal_id, "FAILED", code=exc.code)
    conn = get_connection()
    row = conn.execute("SELECT * FROM recipients WHERE recipient_id = ?", (payload.recipient_id,)).fetchone()
    conn.close()
    return _row_to_response(row)
