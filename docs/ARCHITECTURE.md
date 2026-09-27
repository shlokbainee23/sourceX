# Architecture

This is an offline, single-process prototype: a FastAPI backend (`backend/app`), SQLite storage, and a React/Vite UI (`frontend/`). It uses no network services. All principals share one server; each principal's private keys live in that principal's own encrypted keystore on the server's disk.

## Components

| Path | Responsibility |
|---|---|
| `app/config.py` | Environment-driven settings (`SIH_DATA_DIR`, `SIH_DEMO_MODE`, limits) |
| `app/auth.py` | Login (= keystore unlock), bearer sessions, `require_roles` |
| `app/audit.py` | Operational audit trail (`audit_events`), secret redaction |
| `app/crypto/pqc_kem.py` | ML-KEM-768 (`mlkem`) |
| `app/crypto/pqc_dsa.py` | ML-DSA-44 (`dilithium_py`), fail-closed verify |
| `app/crypto/kdf.py` | HKDF-SHA256, info bound to `document_id|recipient_id` |
| `app/crypto/symmetric.py` | AES-256-GCM, random 96-bit nonces, context AAD |
| `app/crypto/keystore.py` | Encrypted local software keystore (scrypt + AES-256-GCM) |
| `app/crypto/identity.py` | Principal provisioning, legacy plaintext-key migration |
| `app/watermark/*` | Forensic marker embed / strict extract / render comparison |
| `app/ledger/*` | Canonical JSON, record builders, hash chain, verification |
| `app/forensics.py` | Strict attribution engine |
| `app/trust.py` | Signed trust-anchor manifest: local trusted identity store, controlled import, revocation |
| `app/api/*` | HTTP routes (see `API.md`) |
| `scripts/generate_bom.py` | Offline SBOM + CBOM (CycloneDX 1.6) and drift check, written to `bom/` |

## Security pipeline

```text
AUTHORITY (logged in; ML-DSA key unlocked)
  register PDF ── SHA-256(original) ── signed DOCUMENT_REGISTERED block
  encrypt (one-shot):
    CEK = random 256-bit
    C_doc = AES-256-GCM(CEK, nonce, AAD="sih26237-document-v3|doc")      (document encrypted once)
    per recipient r:
      (ss, ct_kem) = ML-KEM-768.Encaps(ek_r)                              (ML-KEM never touches the document)
      KEK = HKDF-SHA256(ss, info="sih26237-cek-wrapping-v3|doc|r")
      W_r = AES-256-GCM(KEK, nonce_r, CEK, AAD="sih26237-cek-v3|doc|r")
    signed DOCUMENT_ENCRYPTED block; plaintext original destroyed

RECIPIENT r (logged in; identity from token; keys from own keystore)
  ss = Decaps(dk_r, ct_kem) → KEK → CEK (GCM tag check) → plaintext (GCM tag check)
  require SHA-256(plaintext) == registered original_hash
  session_id, token = "WM-" + 256 random bits
  delivered = embed(plaintext, token)          (render-mode-3 text on every page + metadata)
  record = {document_id, recipient_id, session_id, watermark_token,
            source_document_hash, delivered_document_hash, decryption_timestamp, ...}
  sig = ML-DSA-44.Sign(sk_r, canonical(record))
  ONE transaction: ledger block + session row; then head anchor updated

INVESTIGATOR
  upload → forensics.investigate_document() → VERIFIED | UNVERIFIED | VERIFICATION_ERROR
```

## Attribution rule

`VERIFIED` requires **all** of these checks to pass:
- `watermark_found`: a marker is present.
- `watermark_valid`: exactly one well-formed token, with no conflicting markers.
- `session_found`: a session row exists for that token.
- `document_hash_match`: SHA-256 of the upload equals the recorded `delivered_document_hash`.
- `record_consistent`: the record rebuilt from the session matches the ledger's stored record byte-for-byte, and the signer, signature and block index agree.
- `ledger_record_found`: exactly one decryption block carries the token.
- `signature_valid`: the ML-DSA-44 signature verifies against the named recipient's registered public key. Revoked keys are still used here, because revocation does not invalidate earlier signatures.
- `ledger_chain_valid`: the full chain and the head anchor verify.
- `document_provenance_valid`: exactly one authority-signed registration block and one broadcast-encryption block exist for the document. Both precede the decryption block, carry the same source hash as the decryption record, and the encryption block authorized this recipient.
- `identity_trusted`: the recipient's registered ML-DSA key matches the fingerprint attested in the latest signed trust manifest. That manifest must verify under the pinned authority key, and the key must not have been revoked before the decryption timestamp.

Any exception produces `VERIFICATION_ERROR` with no attribution. The result reports `trust_anchor` (the manifest version, its SHA-256, and the authority pin) so the exact trust data used can be identified.

## Trust anchor and controlled data ingestion

```text
trust_anchor/authority.pin   SHA-256(WESEE_HQ ML-DSA pk), outside the data dir (SIH_AUTHORITY_PIN_FILE)
        │
signed package {manifest, signature} ──> app/trust.verify_package:
        size ≤ 1 MB → UTF-8 JSON (no duplicate keys, no floats) → strict schema
        → issuer fingerprint == pin → ML-DSA-44 signature
        ──> import_package (one ledger_transaction):
            same version + same hash → ALREADY_IMPORTED; different → CONFLICT; lower → STALE
            no removal, key change, role change or un-revocation of attested principals → else CONFLICT
            INSERT trust_manifests (append-only) + provenance (source_label, imported_by, imported_at)
            apply revocations to the registry (principals/recipients status = REVOKED)
            authority-signed TRUST_MANIFEST_IMPORTED ledger block (version + manifest hash)
```

Every read (`current_manifest`) re-verifies the stored package against the pin and its recorded hash. It also checks that every manifest version recorded in the ledger is still present and unchanged, so deleting the newest version (a rollback) is detected.

Manifests are produced by `scripts/provision_identities.py` (initial pin and v1), on enrolment (`/api/recipients/create`), by re-issue (`/api/trust/issue`) and by revocation (`/api/trust/revoke`). A new manifest is never issued if the registry disagrees with an already-attested key (`REGISTRY_DRIFT`), so a substituted registry key can't be laundered into a freshly signed manifest.

## Trust boundaries

| Boundary | What crosses it | Control |
|---|---|---|
| Browser → API | Passphrase (login only), bearer token, uploads | Local origin CORS, role checks, size limits, strict schemas |
| API → keystore files | Passphrase-derived key | scrypt + AES-256-GCM with header AAD, registry consistency probe |
| Removable media → trust store | Signed manifest package | Pin, signature, schema, monotonicity, append-only storage |
| Data directory → verifier | Registry, ledger, sessions | Hash chain, signatures, head anchor, manifest attestation, pin outside the data dir |
| Operator → pin file | Authority fingerprint | Out-of-band; deploy on read-only media. This is **not** protected by the software. |

**Source authority** (who vouches for the data) is established by the pinned ML-DSA signature. **Local integrity** (whether the stored data is unchanged) is established by re-verification, append-only triggers and ledger cross-references. Government origin alone is never treated as trust.

## Offline deployment model

- **Runtime:** a single air-gapped host runs uvicorn (127.0.0.1) and the built UI. There are no outbound connections: `tests/test_trust_integration.py::test_full_workflow_with_network_disabled` runs the full workflow with sockets disabled.
- **Software transfer:** a wheelhouse plus the built frontend, verified with `python scripts/generate_bom.py --check`. That check compares installed packages and crypto parameters against `bom/` and its `SHA256SUMS`.
- **Identity transfer:** signed trust-manifest packages (`GET /api/trust/manifest/export` → removable media → `POST /api/trust/import`). The pin file is distributed separately.
- **Time:** host clock synchronised to a local time source traceable to UTC(NPLI), as the CERT-In 2022 Directions require. Timestamps are UTC with an offset.
- **Data at rest:** `backend/data/` holds the keystores, database, vault and head anchor; the pin lives outside it. The only data that ever leaves the system are delivered copies downloaded by their recipient and packages an operator exports deliberately.

## External dependency policy

1. No runtime network calls. Any new integration must work with the network disconnected.
2. External data enters only as a **signed package** through `app/trust.py`, or a future equivalent with the same pipeline, and always keeps its provenance.
3. External failure (missing, stale, corrupted or unsigned data) may only make attribution **fail closed**. It must never block or weaken encryption, decryption, signing or ledger verification.
4. Government sources are integrated only when they meet a concrete requirement; see `GOVERNMENT_ECOSYSTEM.md` for the evaluations and rejections.

## Ledger

`block_hash = SHA-256(canonical({v, block_index, timestamp, event_type, previous_hash, record_hash, signer_id, signature}))`, with genesis `previous_hash = 0*64`. Every block is signed:
- Authority events are signed by the authority's ML-DSA key.
- Decryption events are signed by the recipient's key.
- `TRUST_MANIFEST_IMPORTED` events are signed by the importing authority.

The head anchor file `data/ledger_head.json` records the latest `(block_index, block_hash)`, which makes deletion of the newest blocks detectable. SQLite triggers reject UPDATE/DELETE on `ledger_blocks` and `sessions`. The only code that bypasses them is demo reset and tamper simulation.

The ledger is **tamper-evident, not immutable**. See `SECURITY.md` for the limits.

## Frontend

`frontend/src/App.jsx` is a single component. Choosing a station prompts for that principal's keystore passphrase and calls `/api/auth/login`. The returned bearer token is sent with every request. The UI never decides authorization; the backend enforces it.
