"""
Key lifecycle endpoints: self-enrollment, key rotation, passphrase change, own key view.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.audit import record_audit
from app.auth import (AuthSession, LoginError, _check_not_locked, _clear_failures, _register_failure, current_session,
                      require_roles, revoke_sessions_for)
from app.crypto import keystore
from app.crypto.identity import IdentityError, change_passphrase, enroll_principal, list_principal_keys, rotate_keys
from app.models.schemas import ChangePassphraseRequest, EnrollRequest, RotateKeysRequest

router = APIRouter(prefix="/api", tags=["key lifecycle"])


@router.post("/enroll")
def enroll(payload: EnrollRequest):
    """
    Unauthenticated: redeems a one-time enrollment code. Keys are generated for the
    principal and stored in a keystore encrypted under the passphrase THEY chose. Returns
    the key fingerprints the principal must confirm with the authority out of band.
    """
    lock_key = f"enroll:{payload.principal_id}"
    try:
        _check_not_locked(lock_key)
    except LoginError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    try:
        result = enroll_principal(payload.principal_id, payload.enrollment_code, payload.passphrase)
    except (IdentityError, keystore.KeystoreError) as exc:
        _register_failure(lock_key)
        record_audit("ENROLLMENT_FAILED", payload.principal_id, "DENIED", reason=type(exc).__name__)
        raise HTTPException(status_code=400, detail=str(exc))
    _clear_failures(lock_key)
    record_audit("ENROLLMENT_COMPLETED", payload.principal_id, key_id=result["key_id"])
    return {**result, "next_step": "Read the ML-DSA fingerprint to the issuing authority. You can sign and decrypt "
                                   "once they have attested it."}


@router.get("/keys/me")
def my_keys(session: AuthSession = Depends(current_session)):
    return {"principal_id": session.principal_id, "role": session.role, "session_key_id": session.key_id,
            "keys": list_principal_keys(session.principal_id)}


@router.post("/keys/rotate")
def rotate(payload: RotateKeysRequest, session: AuthSession = Depends(require_roles("RECIPIENT", "INVESTIGATOR"))):
    """Generates a new key (PENDING until attested). All live sessions of the principal end."""
    try:
        result = rotate_keys(session.principal_id, payload.current_passphrase, payload.new_passphrase)
    except keystore.KeystoreUnlockFailed:
        _register_failure(session.principal_id)
        record_audit("KEY_ROTATION_FAILED", session.principal_id, "DENIED", reason="unlock_failed")
        raise HTTPException(status_code=401, detail="Current passphrase is incorrect")
    except (IdentityError, keystore.KeystoreError) as exc:
        record_audit("KEY_ROTATION_FAILED", session.principal_id, "DENIED", reason=type(exc).__name__)
        raise HTTPException(status_code=409, detail=str(exc))
    ended = revoke_sessions_for(session.principal_id)
    record_audit("KEY_ROTATED", session.principal_id, new_key_id=result["key_id"],
                 previous_key_id=result["previous_key_id"], sessions_terminated=ended)
    return {**result, "sessions_terminated": ended,
            "next_step": "Confirm the new fingerprint with the authority; it must be attested before use."}


@router.post("/auth/change-passphrase")
def change_my_passphrase(payload: ChangePassphraseRequest, session: AuthSession = Depends(current_session)):
    """Re-encrypts the keystore under a new passphrase. All live sessions of the principal end."""
    try:
        change_passphrase(session.principal_id, payload.current_passphrase, payload.new_passphrase)
    except keystore.KeystoreUnlockFailed:
        _register_failure(session.principal_id)
        record_audit("PASSPHRASE_CHANGE_FAILED", session.principal_id, "DENIED", reason="unlock_failed")
        raise HTTPException(status_code=401, detail="Current passphrase is incorrect")
    except keystore.KeystoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    ended = revoke_sessions_for(session.principal_id)
    record_audit("PASSPHRASE_CHANGED", session.principal_id, sessions_terminated=ended)
    return {"status": "PASSPHRASE_CHANGED", "sessions_terminated": ended}
