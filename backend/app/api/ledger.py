"""
Ledger explorer, verification and (demo-only) tamper simulation endpoints for SIH26237.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app import config
from app.audit import list_audit_events, record_audit
from app.auth import AuthSession, require_roles
from app.database.connection import reset_test_database
from app.ledger.blockchain import get_all_blocks
from app.ledger.verify import simulate_tampering, verify_ledger
from app.models.schemas import LedgerBlockResponse, LedgerVerificationResult, TamperRequest

router = APIRouter(prefix="/api/ledger", tags=["ledger"])
audit_router = APIRouter(prefix="/api/audit", tags=["audit"])

LEDGER_READERS = ("AUTHORITY", "INVESTIGATOR", "AUDITOR")


def _require_demo_mode():
    if not config.demo_mode_enabled():
        raise HTTPException(status_code=403, detail="Demo operations are disabled (set SIH_DEMO_MODE=1).")


@router.get("", response_model=List[LedgerBlockResponse])
def get_ledger_blocks(_: AuthSession = Depends(require_roles(*LEDGER_READERS))):
    return [LedgerBlockResponse(**b) for b in get_all_blocks()]


@router.get("/verify", response_model=LedgerVerificationResult)
def run_ledger_verification(session: AuthSession = Depends(require_roles(*LEDGER_READERS))):
    result = verify_ledger()
    if result["chain_valid"]:
        record_audit("LEDGER_VERIFIED", session.principal_id, total_blocks=result["total_blocks"])
    else:
        record_audit("LEDGER_AUDIT_FAILED", session.principal_id, "FAILED", error=result["error_message"])
    return result


@router.post("/tamper-test")
def trigger_tamper_test(payload: TamperRequest, session: AuthSession = Depends(require_roles("AUDITOR"))):
    """DEMO ONLY: simulates an attacker editing the SQLite file directly."""
    _require_demo_mode()
    res = simulate_tampering(payload.block_index, payload.field, payload.new_value)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    record_audit("TAMPER_SIMULATION", session.principal_id, "DEMO", block_index=payload.block_index, field=payload.field)
    return res


@router.post("/reset")
def reset_ledger_environment(session: AuthSession = Depends(require_roles("AUDITOR", "AUTHORITY"))):
    """DEMO ONLY: clears documents, sessions and ledger. Principals and keystores are preserved."""
    _require_demo_mode()
    reset_test_database()
    record_audit("DEMO_ENVIRONMENT_RESET", session.principal_id, "DEMO")
    return {
        "status": "SUCCESS",
        "message": "Demo documents, sessions and ledger reset. Principals and encrypted keystores preserved.",
        "blocks_count": 0,
    }


@audit_router.get("")
def get_audit_trail(limit: int = 200, _: AuthSession = Depends(require_roles("AUDITOR"))):
    return list_audit_events(max(1, min(limit, 1000)))
