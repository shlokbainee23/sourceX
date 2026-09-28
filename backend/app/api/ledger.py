"""
Ledger explorer, verification, checkpoint/witness and (demo-only) tamper simulation
endpoints for SIH26237.
"""

import json
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app import config
from app.api.common import attested_signing_key
from app.api.uploads import read_upload
from app.audit import list_audit_events, record_audit
from app.auth import AuthSession, require_roles
from app.database.connection import reset_test_database
from app.ledger import checkpoint
from app.ledger.blockchain import get_all_blocks
from app.ledger.canonical import canonicalize_json
from app.ledger.verify import simulate_tampering, verify_ledger
from app.models.schemas import LedgerBlockResponse, LedgerVerificationResult, TamperRequest
from app.trust import TrustError

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


@router.get("/witness")
def get_witness_status(_: AuthSession = Depends(require_roles(*LEDGER_READERS))):
    status = checkpoint.witness_status()
    status["latest_checkpoint"] = checkpoint.latest_checkpoint()
    return status


@router.post("/checkpoint")
def create_checkpoint(session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """Signs a checkpoint over the verified head and returns the bundle for the witness (public data only)."""
    sk, key_id = attested_signing_key(session)
    try:
        cp = checkpoint.create_checkpoint(session.principal_id, key_id, sk)
        bundle = checkpoint.export_bundle(cp)
    except (checkpoint.CheckpointError, TrustError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit("LEDGER_CHECKPOINT_CREATED", session.principal_id, block_index=cp["checkpoint"]["block_index"],
                 checkpoint_sha256=cp["checkpoint_sha256"])
    return Response(content=canonicalize_json(bundle), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="ledger_bundle_'
                                                    f'{cp["checkpoint"]["block_index"]}.json"'})


@router.get("/bundle")
def export_bundle(session: AuthSession = Depends(require_roles(*LEDGER_READERS))):
    """Full ledger bundle (blocks, signed manifests, attested public keys) for offline verification."""
    try:
        bundle = checkpoint.export_bundle(checkpoint.latest_checkpoint())
    except TrustError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit("LEDGER_BUNDLE_EXPORTED", session.principal_id, blocks=len(bundle["blocks"]))
    return Response(content=canonicalize_json(bundle), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="ledger_bundle.json"'})


@router.post("/cosignature")
async def import_cosignature(file: UploadFile = File(...),
                             session: AuthSession = Depends(require_roles("AUTHORITY", "AUDITOR"))):
    """Imports a witness cosignature (verified against the pinned witness keys and the local chain)."""
    raw = await read_upload(file)
    try:
        doc = json.loads(raw.decode("utf-8"))
        result = checkpoint.import_cosignature(doc, session.principal_id)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Cosignature file is not valid JSON")
    except (checkpoint.CheckpointError, TrustError) as exc:
        record_audit("WITNESS_COSIGNATURE_REJECTED", session.principal_id, "REJECTED", reason=str(exc)[:200])
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit("WITNESS_COSIGNATURE_IMPORTED", session.principal_id, witness=result["witness_id"],
                 block_index=result["block_index"], status=result["status"])
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
    """DEMO ONLY: clears documents, sessions and ledger. Principals, keystores, trust manifests,
    witness cosignatures and the audit trail are preserved."""
    _require_demo_mode()
    reset_test_database()
    record_audit("DEMO_ENVIRONMENT_RESET", session.principal_id, "DEMO")
    return {
        "status": "SUCCESS",
        "message": "Demo documents, sessions and ledger reset (new ledger instance). Principals, encrypted "
                   "keystores, trust manifests and audit trail preserved.",
        "blocks_count": 0,
    }


@audit_router.get("")
def get_audit_trail(limit: int = 200, _: AuthSession = Depends(require_roles("AUDITOR"))):
    return list_audit_events(max(1, min(limit, 1000)))
