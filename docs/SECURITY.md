# Security Model

This document describes what the prototype actually enforces. Where a guarantee is absent, it says so.

## Roles and authorization boundaries

Identity and role come **only** from the server-side session behind the bearer token. Request bodies never establish identity. The permissions below are enforced in `app/auth.py` (`require_roles`) and in the route handlers.

| Operation | AUTHORITY | RECIPIENT | INVESTIGATOR | AUDITOR |
|---|---|---|---|---|
| Register / encrypt document, enrol recipient | yes | – | – | – |
| Decrypt (only documents packaged for *self*) | – | yes | – | – |
| Download delivered copy (own sessions only) | – | yes | – | – |
| Investigate leaked document | – | – | yes | – |
| Read ledger / verify chain | yes | – | yes | yes |
| Invariance comparison | yes | – | yes | yes |
| Read audit trail | – | – | – | yes |
| Tamper simulation (demo mode only) | – | – | – | yes |
| Demo reset (demo mode only) | yes | – | – | yes |
| View trust manifest | yes | – | yes | yes |
| Export trust manifest package | yes | – | – | yes |
| Import / issue trust manifest, revoke a principal | yes | – | – | – |

A client-supplied `recipient_id` on `/api/decrypt` is rejected (403) if it differs from the authenticated recipient. Another recipient's session copy returns 404, so the server doesn't reveal whether that session exists.

## Secrets and private keys

- Private keys exist on disk **only** inside `data/keystore/<id>.keystore.json`. The format is:
  - scrypt (N=2^15, r=8, p=1, random 16-byte salt) derives the key;
  - AES-256-GCM (random 12-byte nonce) encrypts the key material;
  - the full header (principal, role, KDF parameters, salt, nonce) is authenticated as AAD.
- A wrong passphrase and a modified file both fail the GCM tag, and unlock is denied. Weakened KDF parameters, a relabelled principal, and malformed files are rejected as corrupted.
- Login unlocks the keystore and then proves the keys match the registered public keys (KEM round-trip plus signature probe). Unlocked keys are held in process memory for the session: 30 minutes by default, cleared on logout or expiry. Python cannot guarantee memory zeroization.
- This is an **encrypted local software keystore, not an HSM**. The server process can use a recipient's key while that recipient is logged in.
- Legacy v1 plaintext `*.key.json` files are migrated by `scripts/provision_identities.py`, overwritten with random bytes, then deleted. On SSDs or journaling filesystems, old blocks may survive, so treat any earlier plaintext keys as exposed.
- No credentials are hardcoded. Passphrases are chosen at provisioning, or generated and printed once. Test passphrases are random per run.
- Passphrases are at least 12 characters. After 5 failed logins, the principal is locked out for 60 seconds. Login errors don't reveal whether a principal exists.

## Input validation

- Identifiers must match `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$` and contain no `..`. They are used in file names, HKDF info and AAD.
- JSON request models set `extra="forbid"`, so unexpected fields return 422.
- Uploads are capped at 25 MB by default (`SIH_MAX_UPLOAD_BYTES`). Registration requires a parseable PDF with at least one page.
- File paths are always built server-side from validated IDs, resolved, and checked to stay inside the documents directory.

## API security

- CORS is limited to the local UI origins (`SIH_ALLOWED_ORIGINS`), with no credentials mode. Only bearer tokens are used, never cookies.
- Unhandled errors return a generic 500 with no exception text or traceback.
- Demo endpoints (`/api/ledger/tamper-test`, `/api/ledger/reset`) return 403 unless `SIH_DEMO_MODE=1`.

## Sensitive logging rules

`app/audit.py` redacts any key containing `password`, `passphrase`, `private`, `secret`, `cek`, `mlkem_dk`, `mldsa_sk` or `session_token`, and omits raw bytes. Watermark tokens are logged only as a 16-hex-char SHA-256 reference. Document contents are never logged. Audit events record the acting principal, including the investigator for every forensic step. `audit_events` is append-only (SQLite triggers that no code path drops, including demo reset), so records are retained indefinitely, which exceeds the CERT-In 180-day minimum. It is **not** hash-chained or signed: someone with raw file access could alter it. The ledger is the evidence store.

## Fail-closed verification

- `pqc_dsa.dsa_verify` returns `False` for any malformed input or exception.
- `ledger.verify.verify_ledger` returns `chain_valid=False` for any anomaly or internal error.
- `forensics.investigate_document` returns `VERIFIED` only if all ten checks pass, including `document_provenance_valid` and `identity_trusted`.
- A `CORRELATED` modified-copy result means the marker and record checks may match but the exact delivered-file hash does not. It includes no recipient, document, session, block, raw marker, or signer-key identifier; the report also carries no attribution. Identity-linked hash/signature audit events are written only after all ten checks pass; non-verified audit events do not contain recipient-linked marker or session references.
- `trust.verify_principal_key` never raises. A missing pin, an empty or corrupted trust store, a fingerprint mismatch, or a revocation all return `trusted=False` with a reason. Any exception produces `VERIFICATION_ERROR`, with `attribution=null` and every flat attribution field null.
- Decryption is denied on:
  - a locked keystore;
  - a failed KEM or unwrap (403);
  - a ciphertext authentication failure (409);
  - a mismatch between the plaintext hash and the registered hash (409).

  The session row and ledger block are committed in one transaction. If that fails, no copy is released.
- Ledger appends are refused if the chain tail disagrees with the head anchor, so a truncation can't be silently re-anchored.

## Security-sensitive operations (read this file before changing them)

- `crypto/keystore.py`, `crypto/identity.py`, `auth.py`
- `api/decryption.py`, `api/encryption.py`
- `ledger/blockchain.py`, `ledger/verify.py`, `ledger/records.py`, `ledger/canonical.py`
- `forensics.py`, `watermark/extract.py`
- `trust.py`, `api/trust.py`, `config.authority_pin_path`, `scripts/provision_identities.py`

## Trust anchor, revocation and key compromise

- **Pin:** `trust_anchor/authority.pin` (override with `SIH_AUTHORITY_PIN_FILE`) holds SHA-256 of the WESEE_HQ ML-DSA-44 public key. It lives outside the data directory and is written once; a different pin is never overwritten. Deploy it on read-only media and verify it out-of-band against the fingerprint printed at provisioning.
- **Manifest:** a signed statement of each principal's role and key fingerprints. Imports are validated as described in `ARCHITECTURE.md`. Stored packages are re-verified on every read, and the ledger records every accepted version.
- **If a recipient's private key or passphrase is stolen:** an AUTHORITY calls `POST /api/trust/revoke`. That:
  1. issues a new signed manifest version marking the key REVOKED with a timestamp;
  2. sets the registry status to REVOKED, which blocks login and blocks new encryption to that recipient;
  3. terminates the recipient's live sessions.

  Decryptions recorded **before** `revoked_at` remain attributable, and later ones fail `identity_trusted`. Revocation can't be undone by a later manifest.
- **If the authority key is stolen:** the attacker can sign manifests that pass the pin. Recovery requires a new authority key, a new pin distributed out-of-band, and re-provisioning. The prototype has no in-band authority rotation.

## Government-aligned controls (alignment, not certification)

| Guidance | What this prototype does | What it does **not** do |
|---|---|---|
| CERT-In Govt Entities Guidelines 6.2.3 (no unencrypted secret keys) | Private keys only inside encrypted keystores | No hardware protection |
| CERT-In Directions 2022 (logs ≥180 days, NIC/NPL time) | Append-only audit trail; UTC timestamps with offset | No NTP client; the host must be synced to a local source traceable to UTC(NPLI) |
| MHA NISPG classification | RESTRICTED/CONFIDENTIAL/SECRET/TOP SECRET bound into the signed registration record | No per-classification handling policy enforcement |
| MHA NISPG key management (documented process, logging, custodians) | Key operations are audited; revocation procedure documented | **Not SAG-approved algorithms; keys not from JCB; no cryptographic hardware.** These are mandatory gates before any SECRET/TOP SECRET use. |
| CERT-In SBOM/CBOM Guidelines v2.0 | CycloneDX SBOM + CBOM with checksums; drift check | No VEX/CSAF vulnerability feed (offline) |
| TEC 910018:2025 PQC migration | PQC key establishment and signatures; cryptographic inventory | Not hybrid (no classical+PQC combination) |
| DPDP Act 2023 | Marker holds no personal data; names stay local | No legal determination of applicability or exemption |
## Known limitations (honest scope)

- **Exact-hash attribution is brittle by design.** Any modification to the delivered file, including a re-save, yields `UNVERIFIED`. The marker may still be found, but it is never enough on its own.
- **The marker is removable.** It is ordinary invisible text plus metadata. Text extraction reveals it, and rasterizing, printing and scanning, retyping, or regenerating the PDF removes it. It is a forensic attribution marker, not an unremovable watermark, and it does not prevent leaks.
- **The 0-pixel invariance** is measured with PyMuPDF at 150 DPI only. Other renderers were not tested.
- **Signatures are made server-side**, using the recipient's keystore unlocked by the recipient's passphrase. They prove the record was created in a session authenticated as that recipient, not on a recipient-controlled device.
- **Trust anchors are local.** An attacker with write access to the data directory who substitutes a recipient's registry key now fails `identity_trusted`: the pinned, signed manifest attests the original fingerprint, and re-issuing is refused with `REGISTRY_DRIFT`. An attacker who controls **both** the data directory and the pin file, or who holds the authority private key, can still forge a consistent world. Production needs the pin on read-only media or in hardware, and externally witnessed ledger checkpoints.
- **Post-quantum only, not hybrid.** A flaw in ML-KEM or ML-DSA, or in the pure-Python `dilithium_py` implementation, has no classical fallback. The libraries are not FIPS-validated modules.
- **Single process only.** The ledger lock is in-process, and sessions and lockouts live in memory and reset on restart.
- **A crash** between the ledger COMMIT and the head-anchor write makes the next verification report a mismatch. This fails closed, and a manual review is needed to recover.

## Agent prohibitions

Agents must never:
- write private keys, passphrases or unlocked key maps to disk, logs, responses or test fixtures;
- accept identity or role from request data;
- make a verification path return success on an exception, a missing record or a partial evidence set;
- let a watermark match alone produce attribution;
- mutate `ledger_blocks` or `sessions` outside `simulate_tampering` or `reset_test_database`, or remove the append-only triggers;
- expose tamper or reset endpoints outside demo mode;
- weaken scrypt parameters, reuse nonces, or replace ML-KEM, ML-DSA, HKDF or AES-GCM without a documented concrete reason;
- describe the system as immutable, unremovable, HSM-backed or leak-proof;
- add a runtime network call, or make any external data source a dependency of encryption, decryption, signing or ledger verification;
- accept external data except through a signed, pinned, schema-validated, provenance-recording path like `app/trust.py`;
- overwrite or delete trust manifests or audit events, or drop their triggers;
- claim compliance with, or certification against, any government standard (NISPG, CERT-In, IT Act, DPDP), or claim the ML-DSA records are IT-Act digital signatures.
