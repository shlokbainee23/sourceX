"""
Authentication and server-side authorization for SIH26237.

Login = unlocking the principal's encrypted keystore with its passphrase. On success
the server issues a random bearer token. Identity and role are ALWAYS derived from
that token on the server; request bodies are never trusted for identity.

Unlocked private keys are held in process memory for the session lifetime only
(like ssh-agent), and dropped on logout or expiry. Python cannot guarantee memory
zeroization; this is documented in SECURITY.md.
"""

import hashlib
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from fastapi import Depends, Header, HTTPException

from app import config
from app.audit import record_audit
from app.crypto import keystore
from app.crypto.identity import get_principal, verify_keys_match_registry


@dataclass
class AuthSession:
    principal_id: str
    role: str
    name: str
    expires_at: float
    keys: Dict[str, bytes] = field(default_factory=dict, repr=False)


_sessions: Dict[str, AuthSession] = {}
_failures: Dict[str, tuple] = {}
_lock = threading.Lock()


class LoginError(Exception):
    pass


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def login(principal_id: str, passphrase: str) -> tuple:
    now = time.time()
    with _lock:
        count, locked_until = _failures.get(principal_id, (0, 0.0))
        if locked_until > now:
            record_audit("LOGIN_FAILED", principal_id, "DENIED", reason="locked_out")
            raise LoginError("Too many failed attempts. Try again later.")

    principal = get_principal(principal_id)
    generic_failure = "Invalid principal or passphrase"
    try:
        if not principal or principal["status"] != "ACTIVE":
            raise LoginError(generic_failure)
        if keystore.keystore_role(principal_id) != principal["role"]:
            raise LoginError(generic_failure)
        keys = keystore.unlock_keystore(principal_id, passphrase)
        if not verify_keys_match_registry(principal_id, principal["role"], keys):
            record_audit("KEYSTORE_REGISTRY_MISMATCH", principal_id, "DENIED")
            raise LoginError("Keystore does not match the registered public keys")
    except (LoginError, keystore.KeystoreError) as exc:
        with _lock:
            count, _ = _failures.get(principal_id, (0, 0.0))
            count += 1
            lock_until = now + config.LOGIN_LOCKOUT_SECONDS if count >= config.LOGIN_MAX_FAILURES else 0.0
            _failures[principal_id] = (0 if lock_until else count, lock_until)
        reason = type(exc).__name__
        record_audit("LOGIN_FAILED", principal_id, "DENIED", reason=reason)
        if isinstance(exc, keystore.KeystoreCorrupted):
            raise LoginError("Keystore integrity failure. Access denied.")
        raise LoginError(generic_failure) if not isinstance(exc, LoginError) else exc

    token = secrets.token_urlsafe(32)
    session = AuthSession(
        principal_id=principal_id,
        role=principal["role"],
        name=principal["name"],
        expires_at=now + config.SESSION_TTL_SECONDS,
        keys=keys,
    )
    with _lock:
        _failures.pop(principal_id, None)
        _sessions[_token_key(token)] = session
    record_audit("LOGIN_SUCCEEDED", principal_id, role=principal["role"])
    return token, session


def logout(token: str) -> None:
    with _lock:
        session = _sessions.pop(_token_key(token), None)
    if session:
        session.keys.clear()
        record_audit("LOGOUT", session.principal_id)


def revoke_sessions_for(principal_id: str) -> int:
    """Terminates every live session of a principal (used on key revocation)."""
    with _lock:
        keys = [k for k, s in _sessions.items() if s.principal_id == principal_id]
        for k in keys:
            _sessions[k].keys.clear()
            del _sessions[k]
    return len(keys)


def clear_all_sessions() -> None:
    with _lock:
        for s in _sessions.values():
            s.keys.clear()
        _sessions.clear()
        _failures.clear()


def _resolve(token: str) -> Optional[AuthSession]:
    with _lock:
        key = _token_key(token)
        session = _sessions.get(key)
        if session and session.expires_at < time.time():
            session.keys.clear()
            _sessions.pop(key, None)
            return None
        return session


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return authorization[len("Bearer "):].strip()


def current_session(authorization: Optional[str] = Header(default=None)) -> AuthSession:
    session = _resolve(_extract_bearer(authorization))
    if not session:
        raise HTTPException(status_code=401, detail="Session invalid or expired", headers={"WWW-Authenticate": "Bearer"})
    return session


def current_token(authorization: Optional[str] = Header(default=None)) -> str:
    return _extract_bearer(authorization)


def require_roles(*roles: str):
    def dependency(session: AuthSession = Depends(current_session)) -> AuthSession:
        if session.role not in roles:
            record_audit("AUTHORIZATION_DENIED", session.principal_id, "DENIED", role=session.role, required=list(roles))
            raise HTTPException(status_code=403, detail="Your role is not permitted to perform this operation")
        return session
    return dependency
