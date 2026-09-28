"""
Authentication and server-side authorization for SIH26237.

Login = unlocking the principal's encrypted keystore with its passphrase. On success
the server issues a random bearer token. Identity and role are ALWAYS derived from
that token on the server; request bodies are never trusted for identity.

Private-key custody:
  - RECIPIENT keys are never held in the session. Every decryption is a step-up
    operation: the recipient re-enters the passphrase, the keystore is unlocked for that
    one operation, and the key is dropped immediately afterwards. The provenance
    signature therefore always follows a fresh proof of passphrase knowledge.
  - AUTHORITY and INVESTIGATOR signing keys are held in process memory for the session
    lifetime only (like ssh-agent) and dropped on logout, expiry, rotation or revocation.
Python cannot guarantee memory zeroization; this is documented in SECURITY.md.

Failed logins are counted persistently (login_failures table) with exponential lockout,
so restarting the server does not reset brute-force protection.
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
from app.crypto.identity import get_principal, get_registered_key, verify_keys_match_registry
from app.database.connection import get_connection, transaction

SESSION_HELD_KEY_ROLES = ("AUTHORITY", "INVESTIGATOR")


@dataclass
class AuthSession:
    principal_id: str
    role: str
    name: str
    expires_at: float
    key_id: Optional[str] = None
    keys: Dict[str, bytes] = field(default_factory=dict, repr=False)


_sessions: Dict[str, AuthSession] = {}
_lock = threading.Lock()


class LoginError(Exception):
    pass


class StepUpError(Exception):
    pass


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------------------------------------------------------------- lockout

def _locked_until(principal_id: str) -> float:
    conn = get_connection()
    try:
        row = conn.execute("SELECT locked_until FROM login_failures WHERE principal_id = ?", (principal_id,)).fetchone()
    finally:
        conn.close()
    return row["locked_until"] if row else 0.0


def _register_failure(principal_id: str) -> None:
    now = time.time()
    conn = get_connection()
    try:
        with transaction(conn):
            row = conn.execute("SELECT failures FROM login_failures WHERE principal_id = ?", (principal_id,)).fetchone()
            failures = (row["failures"] if row else 0) + 1
            locked_until = 0.0
            if failures >= config.LOGIN_MAX_FAILURES:
                steps = failures - config.LOGIN_MAX_FAILURES
                locked_until = now + min(config.LOGIN_LOCKOUT_SECONDS * (2 ** min(steps, 16)),
                                         config.LOGIN_LOCKOUT_MAX_SECONDS)
            conn.execute("INSERT INTO login_failures (principal_id, failures, locked_until) VALUES (?, ?, ?) "
                         "ON CONFLICT(principal_id) DO UPDATE SET failures = excluded.failures, "
                         "locked_until = excluded.locked_until", (principal_id, failures, locked_until))
    finally:
        conn.close()


def _clear_failures(principal_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM login_failures WHERE principal_id = ?", (principal_id,))
    finally:
        conn.close()


def _check_not_locked(principal_id: str) -> None:
    if _locked_until(principal_id) > time.time():
        record_audit("LOGIN_FAILED", principal_id, "DENIED", reason="locked_out")
        raise LoginError("Too many failed attempts. Try again later.")


# ------------------------------------------------------------------ login

def _unlock_verified(principal_id: str, passphrase: str) -> tuple:
    """(principal, key_id, keys) after keystore unlock and registry consistency checks."""
    principal = get_principal(principal_id)
    generic_failure = "Invalid principal or passphrase"
    if not principal or principal["status"] != "ACTIVE":
        raise LoginError(generic_failure)
    if keystore.keystore_role(principal_id) != principal["role"]:
        raise LoginError(generic_failure)
    keys = keystore.unlock_keystore(principal_id, passphrase)
    key_id = keystore.keystore_info(principal_id)["key_id"] if keys.get("mldsa_sk") else None
    if key_id is not None:
        reg = get_registered_key(key_id)
        if reg is None or reg["status"] in ("REJECTED",):
            keys.clear()
            record_audit("KEYSTORE_REGISTRY_MISMATCH", principal_id, "DENIED", key_id=key_id)
            raise LoginError("Keystore does not match the registered public keys")
    if not verify_keys_match_registry(principal_id, principal["role"], keys, key_id):
        keys.clear()
        record_audit("KEYSTORE_REGISTRY_MISMATCH", principal_id, "DENIED")
        raise LoginError("Keystore does not match the registered public keys")
    return principal, key_id, keys


def login(principal_id: str, passphrase: str) -> tuple:
    _check_not_locked(principal_id)
    try:
        principal, key_id, keys = _unlock_verified(principal_id, passphrase)
    except (LoginError, keystore.KeystoreError) as exc:
        _register_failure(principal_id)
        record_audit("LOGIN_FAILED", principal_id, "DENIED", reason=type(exc).__name__)
        if isinstance(exc, keystore.KeystoreCorrupted):
            raise LoginError("Keystore integrity failure. Access denied.")
        raise LoginError("Invalid principal or passphrase") if not isinstance(exc, LoginError) else exc

    if principal["role"] not in SESSION_HELD_KEY_ROLES:
        keys.clear()
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        principal_id=principal_id,
        role=principal["role"],
        name=principal["name"],
        expires_at=time.time() + config.SESSION_TTL_SECONDS,
        key_id=key_id,
        keys=keys,
    )
    _clear_failures(principal_id)
    with _lock:
        _sessions[_token_key(token)] = session
    record_audit("LOGIN_SUCCEEDED", principal_id, role=principal["role"], key_id=key_id)
    return token, session


def step_up_unlock(session: AuthSession, passphrase: str) -> Dict[str, bytes]:
    """
    Re-authenticates the session's principal for one sensitive operation and returns the
    unlocked keys. The caller must clear() the returned dict when done. Failures count
    toward the persistent lockout.
    """
    if not isinstance(passphrase, str) or not passphrase:
        raise StepUpError("Passphrase confirmation is required for this operation")
    try:
        _check_not_locked(session.principal_id)
    except LoginError as exc:
        raise StepUpError(str(exc))
    try:
        principal, key_id, keys = _unlock_verified(session.principal_id, passphrase)
    except (LoginError, keystore.KeystoreError) as exc:
        _register_failure(session.principal_id)
        record_audit("STEP_UP_FAILED", session.principal_id, "DENIED", reason=type(exc).__name__)
        raise StepUpError("Passphrase confirmation failed")
    if principal["role"] != session.role:
        keys.clear()
        raise StepUpError("Passphrase confirmation failed")
    _clear_failures(session.principal_id)
    return keys


def logout(token: str) -> None:
    with _lock:
        session = _sessions.pop(_token_key(token), None)
    if session:
        session.keys.clear()
        record_audit("LOGOUT", session.principal_id)


def revoke_sessions_for(principal_id: str) -> int:
    """Terminates every live session of a principal (revocation, rotation, passphrase change)."""
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


def clear_lockouts() -> None:
    """Test/demo helper: clears persistent lockout counters."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM login_failures")
    finally:
        conn.close()


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
