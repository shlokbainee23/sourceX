"""
Trust-anchor manifest endpoints: view, export, import, re-issue and revoke.
All operations are local; there is no network fetch anywhere in this module.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app import trust
from app.api.uploads import read_upload
from app.audit import record_audit
from app.auth import AuthSession, require_roles, revoke_sessions_for
from app.crypto.identity import get_authority_public_key
from app.models.schemas import RevokeRequest

router = APIRouter(prefix="/api/trust", tags=["Trust Anchor"])

_STATUS = {
    trust.MALFORMED: 400,
    trust.SCHEMA_INVALID: 400,
    trust.PIN_MISMATCH: 400,
    trust.SIGNATURE_INVALID: 400,
    trust.STALE: 409,
    trust.CONFLICT: 409,
    trust.REGISTRY_DRIFT: 409,
    trust.UNPINNED: 503,
    trust.CORRUPTED: 503,
    trust.NOT_AVAILABLE: 503,
}


def _raise(exc: trust.TrustError, event: str, principal_id: str):
    record_audit(event, principal_id, "REJECTED", code=exc.code)
    raise HTTPException(status_code=_STATUS.get(exc.code, 400), detail=f"{exc.code}: {exc}")


def _authority_pk(session: AuthSession) -> bytes:
    pk = get_authority_public_key(session.principal_id)
    if pk is None:
        raise HTTPException(status_code=403, detail="Authority key not registered")
    return pk


@router.get("/manifest")
def get_manifest(_: AuthSession = Depends(require_roles("AUTHORITY", "INVESTIGATOR", "AUDITOR"))):
    """Current trust manifest with provenance, plus the import history."""
    try:
        pin = trust.authority_pin()
    except trust.TrustError as exc:
        return {"available": False, "error_code": exc.code, "reason": str(exc), "authority_pin": None,
                "current": None, "history": trust.list_manifests()}
    try:
        m = trust.current_manifest()
    except trust.TrustError as exc:
        return {"available": False, "error_code": exc.code, "reason": str(exc), "authority_pin": pin,
                "current": None, "history": trust.list_manifests()}
    manifest = m["manifest"]
    return {
        "available": True,
        "authority_pin": pin,
        "current": {
            "version": m["version"],
            "manifest_sha256": m["manifest_sha256"],
            "issued_at": manifest["issued_at"],
            "issuer": {k: v for k, v in manifest["issuer"].items() if k != "mldsa_public_key"},
            "issuer_fingerprint": m["issuer_fingerprint"],
            "source": manifest["source"],
            "source_label": m["source_label"],
            "imported_by": m["imported_by"],
            "imported_at": m["imported_at"],
            "principals": manifest["principals"],
        },
        "history": trust.list_manifests(),
    }


@router.get("/manifest/export")
def export_manifest(session: AuthSession = Depends(require_roles("AUTHORITY", "AUDITOR"))):
    """Signed package for transfer to another air-gapped node (contains public data only)."""
    try:
        m = trust.current_manifest()
    except trust.TrustError as exc:
        _raise(exc, "TRUST_MANIFEST_EXPORT_FAILED", session.principal_id)
    record_audit("TRUST_MANIFEST_EXPORTED", session.principal_id, version=m["version"])
    return Response(content=m["package"], media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="trust_manifest_v{m["version"]}.json"'})


@router.post("/import")
async def import_manifest(
    source_label: str = Form(..., min_length=3, max_length=256),
    file: UploadFile = File(...),
    session: AuthSession = Depends(require_roles("AUTHORITY")),
):
    raw = await read_upload(file)
    try:
        result = trust.import_package(raw, source_label, session.principal_id, session.keys["mldsa_sk"])
    except trust.TrustError as exc:
        _raise(exc, "TRUST_MANIFEST_REJECTED", session.principal_id)
    for pid in result.get("revoked_principals", []):
        revoke_sessions_for(pid)
    record_audit("TRUST_MANIFEST_IMPORT", session.principal_id, status=result["status"], version=result["version"],
                 manifest_sha256=result["manifest_sha256"])
    return result


@router.post("/issue")
def issue_manifest(session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """Re-issue the manifest from the registry (attests newly enrolled principals)."""
    try:
        result = trust.issue_and_import(session.principal_id, _authority_pk(session), session.keys["mldsa_sk"],
                                        "local-issue", "Re-issued from the local registry")
    except trust.TrustError as exc:
        _raise(exc, "TRUST_MANIFEST_REJECTED", session.principal_id)
    record_audit("TRUST_MANIFEST_ISSUED", session.principal_id, version=result["version"])
    return result


@router.post("/revoke")
def revoke_principal(payload: RevokeRequest, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """Revokes a principal's keys: new signed manifest version, registry status REVOKED,
    live sessions terminated. Evidence signed before revocation remains verifiable."""
    try:
        result = trust.issue_and_import(session.principal_id, _authority_pk(session), session.keys["mldsa_sk"],
                                        "local-revocation", f"Revocation: {payload.reason}",
                                        revoke=[payload.principal_id])
    except trust.TrustError as exc:
        _raise(exc, "KEY_REVOCATION_REJECTED", session.principal_id)
    ended = revoke_sessions_for(payload.principal_id)
    record_audit("KEY_REVOKED", session.principal_id, revoked_principal=payload.principal_id,
                 version=result["version"], sessions_terminated=ended)
    return {**result, "sessions_terminated": ended}
