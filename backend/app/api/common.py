"""
Shared API helpers: resolving the attested signing key for a session.
"""

from typing import Dict, Tuple

from fastapi import HTTPException

from app.audit import record_audit
from app.auth import AuthSession
from app.trust import TrustError, resolve_operational_key


def attested_signing_key(session: AuthSession, keys: Dict[str, bytes] = None) -> Tuple[bytes, str]:
    """
    (secret key, key_id) for a NEW signed operation. The session's key must be the
    principal's current key as attested in the verified trust manifest; a key that is
    pending attestation, retired, revoked or substituted in the registry cannot sign.
    """
    keys = session.keys if keys is None else keys
    try:
        resolved = resolve_operational_key(session.principal_id, session.role)
    except TrustError as exc:
        record_audit("SIGNING_KEY_REJECTED", session.principal_id, "DENIED", reason=exc.code)
        raise HTTPException(status_code=409, detail=f"Signing key is not usable ({exc.code}): {exc}")
    if session.key_id != resolved["key_id"] or "mldsa_sk" not in keys:
        record_audit("SIGNING_KEY_REJECTED", session.principal_id, "DENIED", reason="key_not_current",
                     session_key_id=session.key_id, attested_key_id=resolved["key_id"])
        raise HTTPException(status_code=409, detail="Your unlocked key is not the currently attested key "
                                                    "(rotation awaiting attestation?)")
    return keys["mldsa_sk"], resolved["key_id"]
