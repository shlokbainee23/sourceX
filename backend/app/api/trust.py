"""
Trust-anchor manifest endpoints: view, export, import, attest, revoke, key compromise.
All operations are local; there is no network fetch anywhere in this module.
"""

import hmac

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app import trust
from app.api.uploads import read_upload
from app.audit import record_audit
from app.auth import AuthSession, require_roles, revoke_sessions_for
from app.crypto.identity import get_registered_key, list_principal_keys
from app.database.connection import get_connection
from app.models.schemas import AttestRequest, KeyCompromiseRequest, RevokeRequest

router = APIRouter(prefix="/api/trust", tags=["Trust Anchor"])

_STATUS = {
    trust.MALFORMED: 400,
    trust.SCHEMA_INVALID: 400,
    trust.PIN_MISMATCH: 400,
    trust.SIGNATURE_INVALID: 400,
    trust.STALE: 409,
    trust.CONFLICT: 409,
    trust.REGISTRY_DRIFT: 409,
    trust.UNATTESTED: 409,
    trust.UNPINNED: 503,
    trust.CORRUPTED: 503,
    trust.NOT_AVAILABLE: 503,
}


def _raise(exc: trust.TrustError, event: str, principal_id: str):
    record_audit(event, principal_id, "REJECTED", code=exc.code)
    raise HTTPException(status_code=_STATUS.get(exc.code, 400), detail=f"{exc.code}: {exc}")


def _authority_signer(session: AuthSession) -> tuple:
    """(pk, sk, key_id) for manifest signing: the session key must be the pinned authority key."""
    sk = session.keys.get("mldsa_sk")
    reg = get_registered_key(session.key_id) if session.key_id else None
    if sk is None or reg is None or reg["mldsa_pk"] is None:
        raise HTTPException(status_code=403, detail="Authority signing key not available")
    try:
        pin = trust.authority_pin()
    except trust.TrustError as exc:
        _raise(exc, "TRUST_MANIFEST_REJECTED", session.principal_id)
    if not hmac.compare_digest(trust.sha256_hex(reg["mldsa_pk"]), pin):
        record_audit("TRUST_MANIFEST_REJECTED", session.principal_id, "REJECTED", code=trust.PIN_MISMATCH)
        raise HTTPException(status_code=403, detail="Your key is not the pinned installation authority key")
    return reg["mldsa_pk"], sk, session.key_id


def _issue(session: AuthSession, label: str, description: str, event: str, **ops):
    pk, sk, key_id = _authority_signer(session)
    try:
        return trust.issue_and_import(session.principal_id, pk, sk, label, description, authority_key_id=key_id, **ops)
    except trust.TrustError as exc:
        _raise(exc, event, session.principal_id)


@router.get("/manifest")
def get_manifest(_: AuthSession = Depends(require_roles("AUTHORITY", "INVESTIGATOR", "AUDITOR"))):
    """Current trust manifest (normalized key history) with provenance, plus the import history."""
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
    try:
        witnesses = trust.witness_pins()
        witness_info = {"configured": witnesses["configured"], "threshold": witnesses["threshold"],
                        "witnesses": [{"witness_id": w["witness_id"], "fingerprint": fp}
                                      for fp, w in witnesses["witnesses"].items()]}
    except trust.TrustError as exc:
        witness_info = {"configured": False, "error": str(exc)}
    return {
        "available": True,
        "authority_pin": pin,
        "witness_pins": witness_info,
        "current": {
            "version": m["version"],
            "schema_version": m["schema_version"],
            "manifest_sha256": m["manifest_sha256"],
            "issued_at": manifest["issued_at"],
            "issuer": {k: v for k, v in manifest["issuer"].items() if k != "mldsa_public_key"},
            "issuer_fingerprint": m["issuer_fingerprint"],
            "source": manifest["source"],
            "source_label": m["source_label"],
            "imported_by": m["imported_by"],
            "imported_at": m["imported_at"],
            "principals": [m["principals"][k] for k in sorted(m["principals"])],
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
    _, sk, key_id = _authority_signer(session)
    try:
        result = trust.import_package(raw, source_label, session.principal_id, sk, key_id)
    except trust.TrustError as exc:
        _raise(exc, "TRUST_MANIFEST_REJECTED", session.principal_id)
    for pid in result.get("revoked_principals", []):
        revoke_sessions_for(pid)
    record_audit("TRUST_MANIFEST_IMPORT", session.principal_id, status=result["status"], version=result["version"],
                 manifest_sha256=result["manifest_sha256"])
    return result


@router.post("/issue")
def issue_manifest(session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """Re-issue the manifest (includes operator-provisioned principals not yet attested)."""
    result = _issue(session, "local-issue", "Re-issued from the local registry", "TRUST_MANIFEST_REJECTED")
    record_audit("TRUST_MANIFEST_ISSUED", session.principal_id, version=result["version"])
    return result


@router.get("/pending")
def pending_attestations(_: AuthSession = Depends(require_roles("AUTHORITY", "AUDITOR"))):
    """Keys generated by enrolment or rotation that await the authority's fingerprint confirmation."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT DISTINCT k.principal_id, p.role, p.name, p.status FROM principal_keys k "
                            "JOIN principals p ON p.principal_id = k.principal_id WHERE k.status = 'PENDING' "
                            "ORDER BY k.principal_id").fetchall()
    finally:
        conn.close()
    return [{"principal_id": r["principal_id"], "role": r["role"], "name": r["name"], "principal_status": r["status"],
             "keys": [k for k in list_principal_keys(r["principal_id"]) if k["status"] == "PENDING"]} for r in rows]


@router.post("/attest")
def attest_key(payload: AttestRequest, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """
    Attests a pending key. The authority must supply the ML-DSA fingerprint it confirmed
    with the key holder out of band (read aloud / compared on screen); a mismatch is refused.
    For a rotation, the previous key is retired at the current ledger head.
    """
    result = _issue(session, "local-attestation", f"Attestation of {payload.key_id}", "KEY_ATTESTATION_REJECTED",
                    attest=[{"principal_id": payload.principal_id, "key_id": payload.key_id,
                             "mldsa_pk_sha256": payload.confirmed_mldsa_pk_sha256}])
    ended = revoke_sessions_for(payload.principal_id)
    record_audit("KEY_ATTESTED", session.principal_id, principal=payload.principal_id, key_id=payload.key_id,
                 version=result["version"], sessions_terminated=ended)
    return {**result, "sessions_terminated": ended}


@router.post("/revoke")
def revoke_principal(payload: RevokeRequest, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """Revokes a principal after the current ledger head: new signed manifest version, registry
    status REVOKED, live sessions terminated. Evidence in earlier blocks remains verifiable."""
    result = _issue(session, "local-revocation", f"Revocation: {payload.reason}", "KEY_REVOCATION_REJECTED",
                    revoke=[payload.principal_id], reason=payload.reason)
    ended = revoke_sessions_for(payload.principal_id)
    record_audit("KEY_REVOKED", session.principal_id, revoked_principal=payload.principal_id,
                 version=result["version"], sessions_terminated=ended)
    return {**result, "sessions_terminated": ended}


@router.post("/key-compromise")
def mark_key_compromised(payload: KeyCompromiseRequest, session: AuthSession = Depends(require_roles("AUTHORITY"))):
    """
    Retires a key retroactively: evidence it signed after `compromised_after_block` is no
    longer trusted (investigations of it return NOT_ATTRIBUTABLE). The holder must rotate
    and have the new key attested before signing again.
    """
    result = _issue(session, "local-key-compromise", f"Key compromise of {payload.key_id}: {payload.reason}",
                    "KEY_COMPROMISE_REJECTED",
                    compromise=[{"key_id": payload.key_id, "compromised_after_block": payload.compromised_after_block}])
    holder = payload.key_id.rpartition("#")[0]
    ended = revoke_sessions_for(holder)
    record_audit("KEY_COMPROMISED", session.principal_id, key_id=payload.key_id,
                 after_block=payload.compromised_after_block, version=result["version"], sessions_terminated=ended)
    return {**result, "sessions_terminated": ended}
