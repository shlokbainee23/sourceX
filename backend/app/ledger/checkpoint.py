"""
Signed ledger checkpoints and independent witness cosignatures.

A checkpoint commits to (origin, block_index, block_hash), where origin is the hash of
block #1 (identifies this ledger instance). It is signed by the authority
(context "sih26237/ledger-checkpoint/v1") and exported together with the full block
history, every signed trust manifest and the attested public keys (a "bundle").

An independent witness (scripts/witness.py, separate machine/custodian, its own ML-DSA
key pinned in trust_anchor/witnesses.json) replicates the history, verifies it end to
end, checks it extends everything it has cosigned before, and cosigns the checkpoint
(context "sih26237/witness-cosignature/v1"). The cosignature is imported back here.

Once block N is cosigned by `threshold` pinned witnesses, rewriting any block <= N is
detectable even by an attacker who controls this machine's data directory and signing
keys: the rewritten chain cannot match the cosigned block hash, and the witness refuses
to cosign a non-extending history. Blocks after the last witnessed checkpoint are only
locally tamper-evident; this is reported as unwitnessed coverage.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.crypto.pqc_dsa import CTX_CHECKPOINT, CTX_WITNESS_COSIGNATURE, dsa_sign, dsa_verify_hex
from app.database.connection import get_connection
from app.ledger.canonical import canonicalize_json

CHECKPOINT_FORMAT = "sih26237-ledger-checkpoint"
COSIGNATURE_FORMAT = "sih26237-witness-cosignature"
BUNDLE_FORMAT = "sih26237-ledger-bundle"


class CheckpointError(Exception):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checkpoint_bytes(body: Dict[str, Any]) -> bytes:
    return canonicalize_json(body)


def validate_checkpoint_body(body: Any) -> None:
    keys = {"format", "version", "origin", "block_index", "block_hash", "issued_at", "authority_id", "authority_key_id"}
    if not isinstance(body, dict) or set(body) != keys or body["format"] != CHECKPOINT_FORMAT or body["version"] != 1:
        raise CheckpointError("Checkpoint structure is invalid")
    if not isinstance(body["block_index"], int) or isinstance(body["block_index"], bool) or body["block_index"] < 1:
        raise CheckpointError("Checkpoint block_index is invalid")
    for f in ("origin", "block_hash"):
        if not isinstance(body[f], str) or len(body[f]) != 64:
            raise CheckpointError(f"Checkpoint {f} is invalid")


def _blocks(conn) -> list:
    return conn.execute("SELECT * FROM ledger_blocks ORDER BY block_index").fetchall()


def block_to_dict(r) -> Dict[str, Any]:
    return {k: r[k] for k in ("block_index", "timestamp", "event_type", "previous_hash", "record_hash",
                              "canonical_record", "signature", "signer_id", "block_hash")}


def create_checkpoint(authority_id: str, authority_key_id: str, authority_sk: bytes) -> Dict[str, Any]:
    """Signs a checkpoint over the current verified ledger head and records it."""
    from app.ledger.verify import verify_ledger
    result = verify_ledger()
    if not result["chain_valid"] or result["total_blocks"] == 0:
        raise CheckpointError("Refusing to checkpoint a ledger that is empty or fails verification")
    conn = get_connection()
    try:
        blocks = _blocks(conn)
        head = blocks[-1]
        body = {
            "format": CHECKPOINT_FORMAT,
            "version": 1,
            "origin": blocks[0]["block_hash"],
            "block_index": head["block_index"],
            "block_hash": head["block_hash"],
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "authority_id": authority_id,
            "authority_key_id": authority_key_id,
        }
        raw = checkpoint_bytes(body)
        sig = dsa_sign(authority_sk, raw, context=CTX_CHECKPOINT).hex()
        conn.execute(
            "INSERT INTO ledger_checkpoints (origin, block_index, block_hash, checkpoint, checkpoint_sha256, signature, "
            "created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (body["origin"], body["block_index"], body["block_hash"], raw.decode("utf-8"), _sha256(raw), sig,
             authority_id, body["issued_at"]))
    finally:
        conn.close()
    return {"checkpoint": body, "signature": sig, "checkpoint_sha256": _sha256(raw)}


def export_bundle(checkpoint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Everything an offline verifier / witness needs: blocks, all signed manifests, attested public keys."""
    from app.crypto.identity import get_registered_key
    from app.trust import all_packages, current_manifest
    view = current_manifest()
    public_keys = {}
    for entry in view["principals"].values():
        for k in entry["keys"]:
            reg = get_registered_key(k["key_id"])
            if reg and reg["mldsa_pk"] is not None:
                public_keys[k["key_id"]] = {"mldsa_public_key": reg["mldsa_pk"].hex(),
                                            "mlkem_public_key": reg["mlkem_ek"].hex() if reg["mlkem_ek"] else None}
    conn = get_connection()
    try:
        blocks = [block_to_dict(r) for r in _blocks(conn)]
    finally:
        conn.close()
    return {"format": BUNDLE_FORMAT, "version": 1, "exported_at": datetime.now(timezone.utc).isoformat(),
            "blocks": blocks, "manifests": all_packages(), "public_keys": public_keys, "checkpoint": checkpoint}


def verify_checkpoint_signature(body: Dict[str, Any], signature: str, authority_pk: bytes) -> bool:
    return dsa_verify_hex(authority_pk, checkpoint_bytes(body), signature, context=CTX_CHECKPOINT)


def cosignature_message(body: Dict[str, Any]) -> bytes:
    return checkpoint_bytes(body)


def verify_cosignature_doc(doc: Any, pins: Dict[str, Any]) -> Dict[str, Any]:
    """Validates a cosignature document against the pinned witnesses. Returns parsed facts."""
    if not isinstance(doc, dict) or set(doc) != {"format", "version", "witness_id", "witness_public_key",
                                                 "checkpoint", "checkpoint_signature", "cosignature", "cosigned_at"} \
            or doc["format"] != COSIGNATURE_FORMAT or doc["version"] != 1:
        raise CheckpointError("Cosignature document structure is invalid")
    validate_checkpoint_body(doc["checkpoint"])
    try:
        wpk = bytes.fromhex(doc["witness_public_key"])
    except (TypeError, ValueError):
        raise CheckpointError("Witness public key is not hex")
    fp = _sha256(wpk)
    pinned = pins["witnesses"].get(fp)
    if pinned is None or pinned["witness_id"] != doc["witness_id"]:
        raise CheckpointError("Cosignature is not from a pinned witness")
    if not dsa_verify_hex(pinned["public_key"], cosignature_message(doc["checkpoint"]), doc["cosignature"],
                          context=CTX_WITNESS_COSIGNATURE):
        raise CheckpointError("Witness cosignature is invalid")
    return {"witness_id": doc["witness_id"], "witness_fingerprint": fp,
            "checkpoint_sha256": _sha256(checkpoint_bytes(doc["checkpoint"]))}


def import_cosignature(doc: Any, imported_by: str) -> Dict[str, Any]:
    """Verifies and stores a witness cosignature for a checkpoint of THIS ledger."""
    from app.trust import resolve_key, witness_pins
    pins = witness_pins()
    if not pins["configured"]:
        raise CheckpointError("No witnesses are pinned in the installation trust anchor")
    facts = verify_cosignature_doc(doc, pins)
    body = doc["checkpoint"]
    authority = resolve_key(body["authority_id"], "AUTHORITY", body["authority_key_id"])
    if not verify_checkpoint_signature(body, doc["checkpoint_signature"], authority["mldsa_pk"]):
        raise CheckpointError("Checkpoint authority signature is invalid")
    conn = get_connection()
    try:
        blocks = _blocks(conn)
        if not blocks or blocks[0]["block_hash"] != body["origin"]:
            raise CheckpointError("Checkpoint belongs to a different ledger instance (origin mismatch)")
        if body["block_index"] > len(blocks) or blocks[body["block_index"] - 1]["block_hash"] != body["block_hash"]:
            raise CheckpointError("CONFLICT: the witnessed block hash does not match the local ledger; "
                                  "local history differs from what the witness cosigned")
        existing = conn.execute("SELECT 1 FROM witness_cosignatures WHERE witness_fingerprint = ? AND checkpoint_sha256 = ?",
                                (facts["witness_fingerprint"], facts["checkpoint_sha256"])).fetchone()
        if existing:
            return {"status": "ALREADY_IMPORTED", **facts, "block_index": body["block_index"]}
        conn.execute(
            "INSERT INTO witness_cosignatures (witness_id, witness_fingerprint, origin, block_index, block_hash, "
            "checkpoint_sha256, cosignature, imported_by, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (facts["witness_id"], facts["witness_fingerprint"], body["origin"], body["block_index"], body["block_hash"],
             facts["checkpoint_sha256"], canonicalize_json(doc).decode("utf-8"), imported_by,
             datetime.now(timezone.utc).isoformat()))
    finally:
        conn.close()
    return {"status": "IMPORTED", **facts, "block_index": body["block_index"]}


def witness_coverage(blocks: List[Any], cosignatures: List[Dict[str, Any]], pins: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shared by the app and the offline verifier. `cosignatures` are cosignature documents.
    A cosignature whose block hash disagrees with `blocks` is a conflict (history rewrite).
    """
    out = {"configured": pins["configured"], "threshold": pins["threshold"], "witnessed_index": 0,
           "total_blocks": len(blocks), "unwitnessed_blocks": len(blocks), "conflicts": [], "warnings": [],
           "witnesses": sorted(w["witness_id"] for w in pins["witnesses"].values())}
    if not pins["configured"]:
        out["status"] = "NOT_CONFIGURED"
        return out
    origin = blocks[0]["block_hash"] if blocks else None
    by_index: Dict[int, set] = {}
    for doc in cosignatures:
        try:
            facts = verify_cosignature_doc(doc, pins)
        except CheckpointError as exc:
            out["warnings"].append(f"ignored cosignature: {exc}")
            continue
        body = doc["checkpoint"]
        if body["origin"] != origin:
            out["warnings"].append(f"cosignature by {facts['witness_id']} is for a different ledger instance")
            continue
        idx = body["block_index"]
        if idx > len(blocks) or not hmac.compare_digest(blocks[idx - 1]["block_hash"], body["block_hash"]):
            out["conflicts"].append({"block_index": idx, "witness_id": facts["witness_id"],
                                     "witnessed_block_hash": body["block_hash"]})
            continue
        by_index.setdefault(idx, set()).add(facts["witness_fingerprint"])
    covered = [idx for idx in by_index
               if len(set().union(*(by_index[j] for j in by_index if j >= idx))) >= pins["threshold"]]
    out["witnessed_index"] = max(covered, default=0)
    out["unwitnessed_blocks"] = len(blocks) - out["witnessed_index"]
    out["status"] = "CONFLICT" if out["conflicts"] else (
        "WITNESSED" if out["witnessed_index"] == len(blocks) and blocks else
        "PARTIALLY_WITNESSED" if out["witnessed_index"] else "UNWITNESSED")
    return out


def stored_cosignatures() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT cosignature FROM witness_cosignatures ORDER BY id").fetchall()
    finally:
        conn.close()
    return [json.loads(r["cosignature"]) for r in rows]


def witness_status(blocks: Optional[List[Any]] = None) -> Dict[str, Any]:
    from app.trust import TrustError, witness_pins
    try:
        pins = witness_pins()
    except TrustError as exc:
        return {"configured": False, "status": "PIN_ERROR", "error": str(exc), "conflicts": [], "witnessed_index": 0}
    if blocks is None:
        conn = get_connection()
        try:
            blocks = _blocks(conn)
        finally:
            conn.close()
    return witness_coverage(blocks, stored_cosignatures(), pins)


def latest_checkpoint() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ledger_checkpoints ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"checkpoint": json.loads(row["checkpoint"]), "signature": row["signature"],
            "checkpoint_sha256": row["checkpoint_sha256"]}
