"""
Authentication API for SIH26237.
"""

from fastapi import APIRouter, Depends, HTTPException

from app import config
from app.auth import AuthSession, LoginError, current_session, current_token, login, logout
from app.models.schemas import LoginRequest, LoginResponse, PrincipalResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login_endpoint(payload: LoginRequest):
    """Unlocks the principal's encrypted keystore and issues a bearer token."""
    try:
        token, session = login(payload.principal_id, payload.passphrase)
    except LoginError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return LoginResponse(
        token=token,
        principal_id=session.principal_id,
        role=session.role,
        name=session.name,
        expires_in_seconds=config.SESSION_TTL_SECONDS,
    )


@router.post("/logout")
def logout_endpoint(token: str = Depends(current_token), _: AuthSession = Depends(current_session)):
    logout(token)
    return {"status": "LOGGED_OUT"}


@router.get("/me", response_model=PrincipalResponse)
def whoami(session: AuthSession = Depends(current_session)):
    return PrincipalResponse(principal_id=session.principal_id, role=session.role, name=session.name)
