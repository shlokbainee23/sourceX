# SIH26237: Final Presentation Package

Every claim here is backed by code and a test, or is listed as a limitation. Details are in the linked docs.

## A. Final architecture

```text
             ┌──────────── air-gapped host (127.0.0.1) ─────────────┐
 Browser UI ─┤ FastAPI ── auth (keystore unlock, sessions, roles)   │
 (Vite/React)│   ├─ register  → authority-signed block             │
             │   ├─ encrypt   → ML-KEM-768 → HKDF → AES-256-GCM    │
             │   ├─ decrypt   → marker + signed record → ledger    │
             │   ├─ investigate → 10-check fail-closed engine     │
             │   └─ trust     → pinned, signed identity manifest   │
             │ SQLite (append-only triggers) · keystores · vault   │
             └── trust_anchor/authority.pin (outside the data dir)─┘
   removable media ⇄ signed manifest packages, wheelhouse + bom/ (verified with --check)
```

Details: [ARCHITECTURE.md](ARCHITECTURE.md).

## B. Security model

- **Identity:** a passphrase unlocks a scrypt + AES-256-GCM encrypted local software keystore. The role comes from the server-side session only.
- **Confidentiality:** ML-KEM-768 is used only for key establishment. Documents are encrypted with AES-256-GCM, with context-bound AAD.
- **Evidence:** per-decryption 256-bit marker, a canonical record bound to the delivered file's SHA-256, an ML-DSA-44 recipient signature, and a tamper-evident hash-chained provenance ledger (every block signed, with an external head anchor).
- **Identity attestation:** the recipient's key must match a signed trust manifest verified under a pinned authority fingerprint. Revocation is monotonic, and earlier evidence stays valid.
- **Attribution:** VERIFIED only if all 10 checks pass. Otherwise UNVERIFIED or VERIFICATION_ERROR, and no name is given.

Details: [SECURITY.md](SECURITY.md).

## C. Government ecosystem map

| Source | Role for SIH26237 | Decision |
|---|---|---|
| Issuing authority (WESEE HQ) identity data | Who holds which key | **INTEGRATE**: signed trust manifest |
| CERT-In SBOM/QBOM/CBOM Guidelines v2.0, TEC 910018:2025 | Cryptographic inventory | **LOCALIZE**: `bom/` + `--check` |
| MHA NISPG, CERT-In Directions 2022 and Govt Entities Guidelines 2023 | Control requirements | REFERENCE ONLY (alignment table in SECURITY.md) |
| NIC / NPL time (UTC(NPLI)) | Timestamp traceability | REFERENCE ONLY (host-level local time source) |
| CCA / India PKI | Legal digital signatures | REFERENCE ONLY (classical X.509, online CRL/OCSP) |
| API Setu, DigiLocker, data.gov.in | Citizen and open data | REJECT (online, irrelevant to attribution) |
| DPDP Act 2023 | Personal-data handling | REFERENCE ONLY |

## D. Data/API sources

No runtime government API. The register (owner, URL, access, offline fit, security implication, licensing, decision) is in [GOVERNMENT_ECOSYSTEM.md](GOVERNMENT_ECOSYSTEM.md). API Setu and data.gov.in were **evaluated but intentionally not integrated**, because they require online access and API keys and provide no data that strengthens cryptographic attribution.

## E. Offline deployment model

A single host with no outbound network. Software arrives as a wheelhouse and a built UI, verified with `generate_bom.py --check`. Identity updates arrive as signed packages on removable media. The pin is distributed out-of-band on read-only media, and time is synced to a local source traceable to UTC(NPLI). The full workflow is tested with sockets disabled.

## F. Trust boundaries

SOURCE DATA → VALIDATION (size, JSON strictness, schema) → INTEGRITY (pin + ML-DSA signature) → MONOTONICITY (no stale, conflicting or rolled-back versions) → LOCAL TRUST STORE (append-only, re-verified on every read, ledger-recorded) → APPLICATION (the `identity_trusted` check). **Source authority** is the pinned signature; **local integrity** is re-verification plus append-only storage plus the ledger cross-check.

## G. End-to-end demonstration flow

1. Provision identities (writes the pin and manifest v1).
2. `WESEE_HQ` registers a SECRET PDF and encrypts it for R001 and R002.
3. R001 and R002 decrypt. R003 is denied with 403.
4. R002's copy is uploaded by `INVESTIGATOR_01`: VERIFIED, with manifest v1, its SHA-256 and the pin shown.
5. The same copy with one byte edited: UNVERIFIED (`document_hash_match`).
6. An unrelated PDF: UNVERIFIED.
7. `AUDITOR_01` tampers a block in the sandbox: the chain breaks at that block, and the same leak becomes UNVERIFIED.
8. (Optional) `POST /api/trust/revoke` for a recipient: sessions end, login fails, and earlier evidence is still VERIFIED.

This was run live against the running backend on 27 Sep 2026: steps 2–6 produced the expected results, and the ledger verified with 7 blocks.

## H. Security test results

`pytest tests`: **194 passed**. `tests/test_e2e_workflow.py`: **all 18 steps passed**. `generate_bom.py --check`: OK. `npm run lint` (oxlint): 0 errors. `npm run build`: OK.

| Suite | Tests |
|---|---|
| test_security_api | 47 |
| test_trust_integration | 35 |
| test_security_ledger | 24 |
| test_security_keystore | 22 |
| test_security_watermark | 18 |
| test_security_investigation | 16 |
| test_security_crypto | 14 |
| test_crypto / test_bom / test_watermark / test_ledger / test_e2e | 6 / 5 / 4 / 2 / 1 |

| Required outcome | Evidence |
|---|---|
| No internet → core works | `test_full_workflow_with_network_disabled` (sockets patched to raise) → VERIFIED |
| No government API → core works | No such dependency exists; a missing or corrupted trust store fails only `identity_trusted` (`test_missing_trust_anchor_fails_attribution_but_core_keeps_working`, `test_empty_trust_store_is_not_available`) |
| Corrupted data → fails safely | `test_corrupted_local_snapshot_detected`: CORRUPTED, attribution UNVERIFIED, VERIFIED again after restore; malformed, oversize, schema and signature failures rejected |
| Modified document → NOT VERIFIED | E2E step 15; live smoke test |
| Modified signed record → NOT VERIFIED | `test_security_investigation`, `test_security_crypto` |
| Modified ledger → DETECTED | E2E step 17; 24 ledger tests (every header field, delete, insert, reorder, truncate) |
| Unknown document → NOT VERIFIED | E2E step 14; live smoke test |
| Unauthorized recipient → DENIED | E2E step 16; live smoke test (403) |

## I. Known limitations

- Exact-hash attribution: any re-save or modification means UNVERIFIED.
- The marker is removable (text extraction, rasterization, print and scan).
- Keystores are software-only, private keys sit in server memory while a principal is logged in, and signing happens server-side.
- An attacker controlling both the data directory and the pin file, or holding the authority key, can forge a consistent state. There is no in-band authority key rotation.
- The audit trail is append-only but not hash-chained. Demo reset clears the ledger, including the manifest import records.
- PQC-only (not hybrid), and the libraries are not FIPS-validated (`dilithium_py` is pure Python).
- Not SAG-approved, keys are not from JCB, and there is no hardware key storage.
- Single process; sessions are lost on restart.

## J. Claims the team can safely make

- "Every decryption produces a unique, signed, ledger-recorded copy; the rendered page is pixel-identical at 150 DPI in our tests."
- "Attribution is reported only when ten independent checks pass; otherwise no one is named."
- "The ledger is tamper-evident: modification, deletion, insertion, reordering or truncation is detected."
- "Recipient keys are attested by a signed manifest under a pinned authority key; revocation stops future use without invalidating earlier evidence."
- "Post-quantum algorithms (FIPS 203 ML-KEM-768, FIPS 204 ML-DSA-44) with an encrypted local software keystore."
- "The full workflow runs with no network; no government API or cloud service is required."
- "The SBOM/CBOM follows the structure of the CERT-In v2.0 guidelines and is verifiable offline."

## K. Claims the team must not make

Immutable or blockchain-grade ledger; unremovable or robust watermark; leak prevention; HSM or hardware-protected keys; approved for SECRET or TOP SECRET; NISPG, CERT-In, IT Act or DPDP compliant or certified; legally valid digital signatures; "Government API connected"; attribution of modified, printed or scanned copies; FIPS-validated cryptography; quantum-proof.

## L. Files changed (government-integration cycle)

- **New:**
  - `backend/app/trust.py` and `backend/app/api/trust.py`;
  - `scripts/generate_bom.py`, and its output `bom/sbom.cdx.json`, `bom/cbom.cdx.json` and `bom/SHA256SUMS`;
  - `tests/test_trust_integration.py` and `tests/test_bom.py`;
  - `docs/GOVERNMENT_ECOSYSTEM.md`, `docs/PRD.md` and `docs/PRESENTATION.md`.
- **Modified:**
  - backend: `backend/app/config.py`, `database/connection.py` (schema v3), `ledger/blockchain.py`, `ledger/verify.py`, `crypto/identity.py`, `forensics.py`, `models/schemas.py`, `auth.py`, `main.py` and `api/recipients.py`;
  - scripts: `scripts/provision_identities.py`;
  - tests: `tests/testenv.py` and `tests/test_security_ledger.py`;
  - frontend: `frontend/src/App.jsx`;
  - docs: `README.md`, `docs/ARCHITECTURE.md`, `SECURITY.md`, `API.md`, `DATABASE.md` and `AGENTS.md`;
  - `.gitignore`.
- `docs/DESIGN_SYSTEM.md` was requested for review but does not exist in the repository.

## M. Remaining risks

1. Authority key compromise has no in-band recovery.
2. The pin file's protection depends on how it is deployed.
3. Server-side signing means a compromised host can sign as any logged-in user.
4. The pure-Python ML-DSA implementation has not been audited for side channels.
5. The marker is trivially strippable by a knowledgeable insider. Attribution then fails closed and does not misattribute, but the leak goes unattributed.
6. The SBOM has no offline vulnerability feed, so CVE review is manual.

## Adversarial review (MoD panel)

- **Why offline?** Operational networks are air-gapped, and every online dependency is an exfiltration path and an availability risk. The system needs nothing external.
- **Why PQC?** Harvest-now-decrypt-later against long-lived classified material. FIPS 203 and 204 are standardized, and TEC 910018:2025 calls for PQC migration. We are not hybrid, and we say so.
- **Why watermark at decryption?** Before encryption every copy is identical, so only decryption-time marking distinguishes recipients.
- **Why isn't a static watermark enough?** It identifies the document, not the recipient, and it can be forged. Ours is random, per-session, and bound by signature to the exact delivered file.
- **How is modification proven?** The SHA-256 of the uploaded file must equal the signed `delivered_document_hash`. Any change gives UNVERIFIED.
- **How is actual decryption proven?** A ledger block signed with the recipient's ML-DSA key, created only on the server-side decrypt path after that recipient's keystore was unlocked. Because signing is server-side, this proves the recipient's session performed the decryption, not physical possession by the person.
- **False attribution?** It requires forging an ML-DSA signature, a chain-consistent ledger and a manifest under the pinned authority key. A marker transplanted onto another file fails the hash check.
- **Ledger modified?** Hash chain, per-block signatures and the head anchor detect it, and attribution then fails.
- **Ledger corrupted?** Verification fails, which means VERIFICATION_ERROR or UNVERIFIED. It never falls back to a best guess.
- **Stolen private key?** Revoke it: new manifest, sessions ended, login and new encryption blocked. Decryptions before `revoked_at` stay attributable, and later ones fail `identity_trusted`. A stolen authority key requires re-provisioning.
- **Network disconnected?** No effect; this is tested with sockets disabled.
- **Why each government API?** None is used at runtime. Each was evaluated, and see section C for why each was rejected or kept as reference.
- **Service unavailable?** There is no runtime external service. An unavailable or corrupted trust store fails only the identity check, closed.
- **Stored locally?** Encrypted keystores, public keys, the SQLite database (documents metadata, packages, sessions, ledger, audit, manifests), ciphertext, delivered copies, the head anchor, and the pin.
- **What leaves the system?** Only delivered copies a recipient downloads and manifest packages an operator exports deliberately. There are no telemetry or network calls.
