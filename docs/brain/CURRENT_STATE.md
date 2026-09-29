# Current Project State

## Modified-copy attribution — 2026-09-29

- **FIXED:** `CORRELATED` remains an evidence-status label when every check except
  the exact delivered-file hash passes, but the API now returns no attribution or
  identity/session/document/block fields for that result. The raw watermark token
  and signer key ID are also withheld; report attribution is null.
- **FIXED:** Hash/signature audit events carrying a session or recipient are now
  recorded only after all ten checks pass. Failed/modified investigations carry
  no recipient-linked token or session reference in their audit events.
- **VERIFIED:** Focused adversarial regression coverage asserts the response,
  report and audit do not disclose attribution for edited, appended or resaved copies.

## Button styling — 2026-09-29

- Shared enabled-button colour-changing hover styles now cover landing/login and
  all workspace native buttons. Danger/warning remain distinct, disabled shared
  buttons do not gain hover feedback, keyboard focus is visible, and reduced
  motion disables colour transitions. Rebuilt local workstation assets.
- Build and seven API tests pass. Latest backend before/after checks both yield
  173 passed, 16 failed, 7 errors (including filesystem permissions), with no
  backend modifications. E2E 18 steps pass; BOM drift remains 385 items.

## Integration verification — 2026-09-29

This section supersedes historical counts and working-tree descriptions below for
the frontend integration branch based on GitHub `171db49`.

- **VERIFIED:** Uploaded source matches GitHub HEAD after line-ending normalization.
  Deployed JavaScript matches a locked baseline build exactly. Vercel's `/api/health`
  returns SPA HTML, confirming the missing backend connection on the public host.
- **VERIFIED:** Built landing page and four role workspaces run with FastAPI at
  `/workstation/` when `SIH_SERVE_FRONTEND=1`. Existing API routes and JSON root remain.
  Added private-file/traversal and API-separation checks. Browser tests exercised
  all four role logins and station switching, with no JavaScript page errors.
- **VERIFIED:** Real frontend API client completed PDF registration, broadcast
  encryption, step-up decryption, delivery download, VERIFIED investigation,
  report listing, ledger verification and audit listing against isolated test data.
- **VERIFIED:** Hosted HTML fallback cannot establish authentication. The login
  screen explains missing backend access and disables submission; mobile layout
  was inspected at 390px with no horizontal overflow. Browser demo passphrases
  were removed; station switching logs out and asks for the next credentials.
- **VERIFIED:** Seven new frontend API tests pass. Production build passes.
  The repository's standalone 18-step end-to-end demonstration also passes on
  Python 3.12; it accepts the existing CORRELATED behavior noted below.
  Lint exits successfully with zero errors and 37 existing warnings (same baseline
  warning count); the repository's zero-warning quality target is not yet met.
- **VERIFIED:** Python 3.12.14 with all `requirements.txt` packages installed:
  untouched baseline **176 passed / 18 failed** (194 total); integration
  **179 passed / 17 failed** (196 total). Every remaining failing test also fails
  in the baseline. The two new hosting tests pass. BOM newline preservation fixes
  the pre-existing `test_modified_bom_detected` failure on this Windows checkout.
- **CONFLICT:** The committed BOM predates the current frontend lockfile (including
  its Vercel CLI tree) and records different installed Python component metadata.
  After resolving CRLF checksum conversion, BOM validation reports 385 drift items.
  The BOM has not been regenerated to conceal this baseline mismatch. Added
  `.gitattributes` preserves checksum-covered file bytes in future Windows checkouts.
- **CONFLICT / RELEASE LIMITATION:** The 16 other failing tests cover existing
  verdict naming, ledger signing-key fixtures, trust-manifest schema/drift behavior,
  missing-pin behavior, and recipient-enrollment contracts. Some failures concern
  security semantics, not only stale test expectations; this task does not certify
  or repair the cryptographic engine. Existing `CORRELATED` results can carry a
  recipient identity without an exact hash match, conflicting with DEC-007/008
  and the stated no-attribution invariant. No attribution rules were changed here.
- **VERIFIED:** Dependency installation reported 29 existing npm audit findings
  (1 low, 12 moderate, 15 high, 1 critical). No automatic dependency upgrades were
  applied as part of the frontend integration.
- **Deployment:** Local changes only. No push, merge, Vercel deployment, or
  operational identity provisioning. Vercel remains a public interface; full
  operation uses the offline backend. See [deployment handoff](../FRONTEND_INTEGRATION.md).

The remaining sections describe the earlier snapshot and are retained as history.

> **Last Updated:** 2026-09-28  
> **Source of Truth:** Working repository tree and git baseline `7542c92`  
> **Evaluation Standard:** VERIFIED / DOCUMENTED / INFERRED / UNKNOWN / CONFLICT (No synthetic progress metrics)

---

## 1. Project Phase

- **Current Status:** Advanced Functional Prototype / Diverged Working Copy
- **Baseline Git Commit:** `7542c92` ("Baseline: SIH26237 prototype as received (194 tests, 1 intermittent failure observed)")
- **Working Tree State:** 32 modified files, 4 untracked components (`lifecycle.py`, `checkpoint.py`, `pdf/`, `common.py`).
- **Operational Reality:**
  - Frontend builds and passes linter with 0 errors (`oxlint`, `vite build`).
  - SBOM/CBOM inventory drift check passes (`scripts/generate_bom.py --check`).
  - Test suite currently experiences **17 failures out of 194 tests** due to in-flight API schema breaking changes in the working tree.

---

## 2. Functional Status Matrix

| Subsystem / Feature | Status | Repository Evidence | Notes / Discrepancies |
|---|---|---|---|
| **PQC Key Encapsulation (ML-KEM-768)** | `VERIFIED COMPLETE` | [backend/app/crypto/pqc_kem.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/crypto/pqc_kem.py), [tests/test_crypto.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_crypto.py) | Key establishment only; never encrypts document directly. |
| **PQC Signatures (ML-DSA-44)** | `VERIFIED COMPLETE` | [backend/app/crypto/pqc_dsa.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/crypto/pqc_dsa.py), [tests/test_crypto.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_crypto.py) | Pure Python `dilithium-py`; signs canonical records and blocks. |
| **Encrypted Local Keystore** | `VERIFIED COMPLETE` | [backend/app/crypto/keystore.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/crypto/keystore.py), [tests/test_security_keystore.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_security_keystore.py) | scrypt + AES-256-GCM. Unlocked in memory for session. |
| **Document Registration & Storage** | `VERIFIED COMPLETE` | [backend/app/api/documents.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/documents.py) | Computes SHA-256; creates signed `DOCUMENT_REGISTERED` block. |
| **Broadcast Encryption Pipeline** | `VERIFIED COMPLETE` | [backend/app/api/encryption.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/encryption.py) | 1 CEK per doc; wrapped per recipient using HKDF-derived KEK. Plaintext original deleted after encryption. |
| **Forensic Watermark Embedding** | `VERIFIED COMPLETE` | [backend/app/watermark/embed.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/watermark/embed.py), [tests/test_watermark.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_watermark.py) | PDF render mode 3 (non-rendering text) + metadata. 0 differing pixels verified at 150 DPI in PyMuPDF. |
| **Recipient Decryption Execution** | `VERIFIED COMPLETE` | [backend/app/api/decryption.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/decryption.py), [frontend/src/features/recipient/DecryptionTerminal.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/features/recipient/DecryptionTerminal.jsx) | Mandatory step-up passphrase integrated with `StepUpModal` and `test_e2e_workflow.py`. Real-time truthful status. |
| **Tamper-Evident Hash Chain** | `VERIFIED COMPLETE` | [backend/app/ledger/blockchain.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/ledger/blockchain.py), [backend/app/database/connection.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/database/connection.py) | SHA-256 hash chaining, signed blocks, SQLite append-only triggers, `ledger_head.json` anchor. |
| **10-Check Attribution Engine** | `VERIFIED COMPLETE` | [backend/app/forensics.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/forensics.py), [frontend/src/features/investigation/VerdictDisplay.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/features/investigation/VerdictDisplay.jsx) | Level 1 Operational Verdict + Level 2 10-Point Checklist. Fail-closed attribution enforced with zero suspects on failure. |
| **Trust Anchor & Manifest System** | `VERIFIED COMPLETE` | [backend/app/trust.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/trust.py), [trust_anchor/authority.pin](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/trust_anchor/authority.pin) | Pinned SHA-256 authority key, monotonic manifest versions, revocation without invalidating past signatures. |
| **BOM / Supply-Chain Auditing** | `VERIFIED COMPLETE` | [scripts/generate_bom.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/scripts/generate_bom.py), [bom/](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/bom) | CycloneDX 1.6 SBOM + CBOM with SHA-256 checksums and automated drift check. |
| **Key Lifecycle Management** | `PARTIAL` / `UNTRACKED` | [backend/app/api/lifecycle.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/lifecycle.py) | Backend has `/api/enroll`, `/api/keys/me`, `/api/keys/rotate`, `/api/keys/change-passphrase`. Integrated in frontend key status & trust desk. |
| **Ledger Checkpoints & Cosignatures**| `PARTIAL` / `UNTRACKED` | [backend/app/ledger/checkpoint.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/ledger/checkpoint.py) | Checkpoint verification and bundle export drafted in backend. |
| **Isolated PDF Process Worker** | `PARTIAL` / `UNTRACKED` | [backend/app/pdf/worker.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/pdf/worker.py), [backend/app/pdf/ops.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/pdf/ops.py) | ProcessPoolExecutor for MuPDF operations; untracked in git. |
| **Frontend Workstation UI** | `VERIFIED COMPLETE` | [frontend/src/App.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx), [frontend/src/](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/) | Role-aware naval defense workstation (Authority, Recipient, Investigator, Auditor). Real client routing, Step-Up auth, zero native browser dialogs, real audit trail, dossier archive, visual invariance. |

---

## 3. Test Failure Analysis (17 Failing Tests)

A full execution of `pytest tests -q` on the working copy yielded **177 passed, 17 failed**:

1. **`test_e2e_workflow.py::test_end_to_end`**
   - *Failure:* `AssertionError: {"detail":[{"type":"missing","loc":["body","passphrase"],"msg":"Field required"}]}`
   - *Root Cause:* Working tree modified `DecryptRequest` in `backend/app/models/schemas.py` to make `passphrase` mandatory for decryption ("step-up" auth), whereas the E2E script and API spec only send `{"document_id": "..."}` using session bearer tokens.
2. **13 Fixture-Cascading Failures via `run_basic_flow`**
   - *Tests:*
     - `test_security_ledger.py`: `test_inserted_validly_signed_block_detected`, `test_inserted_block_forged_signature_detected`, `test_duplicate_token_in_ledger_detected`, `test_verification_fails_closed_on_internal_error`, `test_substituted_signer_key_fails`
     - `test_security_watermark.py`: `test_altered_marker_unknown_token`, `test_correct_marker_on_wrong_document`, `test_malformed_marker_in_investigation`, `test_conflicting_marker_in_investigation`
     - `test_trust_integration.py`: `test_modified_source_data_fails_signature`, `test_package_from_unpinned_authority_rejected`, `test_revocation_and_keys_cannot_be_rolled_back`, `test_missing_trust_anchor_fails_attribution_but_core_keeps_working`
   - *Root Cause:* All these tests initialize state via `testenv.run_basic_flow()`, which calls `POST /api/decrypt` without `passphrase`, crashing before test assertions execute.
3. **`test_trust_integration.py::test_corrupted_local_snapshot_detected`**
   - *Failure:* `AssertionError: assert ('NOT_ATTRIBUTABLE' == 'UNVERIFIED')`
   - *Root Cause:* Working tree code replaced the standard verdict `UNVERIFIED` with `NOT_ATTRIBUTABLE` in `app/forensics.py` and `app/models/schemas.py`.
4. **`test_trust_integration.py::test_registry_key_substitution_is_not_trusted_and_not_relaunderable`**
   - *Failure:* `Failed: DID NOT RAISE TrustError`
   - *Root Cause:* Working tree refactor in `backend/app/trust.py` changed drift-detection logic, bypassing the expected exception.
5. **`test_trust_integration.py::test_enrolment_revocation_lifecycle`**
   - *Failure:* `AssertionError: {"detail":[{"type":"extra_forbidden","loc":["body","initial_passphrase"],"msg":"Extra inputs are not permitted"}]}`
   - *Root Cause:* Working tree removed `initial_passphrase` from `RecipientCreate` schema in `app/models/schemas.py` in favor of new enrollment flow, breaking the existing endpoint contract.

---

## 4. Documentation Conflicts & Discrepancies

- **Verdict Naming Conflict:**
  - `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/PRD.md`, `docs/SECURITY.md`, `frontend/src/App.jsx`, `tests/test_trust_integration.py` specify:
    `status: "VERIFIED" | "UNVERIFIED" | "VERIFICATION_ERROR"`.
  - Modified working tree (`app/models/schemas.py`, `app/forensics.py`, `tests/test_security_investigation.py`) introduced:
    `status: "VERIFIED" | "CORRELATED" | "NOT_ATTRIBUTABLE" | "VERIFICATION_ERROR"`.
- **Decryption Auth Contract Conflict:**
  - `docs/API.md` states: `POST /api/decrypt` body is `{document_id}`. Keystore is unlocked during `/api/auth/login` and held in session memory.
  - Modified working tree states: `passphrase` is required on every decrypt ("step-up" authentication).
- **Recipient Enrolment Contract Conflict:**
  - `docs/API.md` states: `POST /api/recipients/create` takes `{recipient_id, name, role, initial_passphrase}`.
  - Modified working tree removed `initial_passphrase` and introduced separate `/api/enroll` endpoint.
- **Undocumented Subsystems in Working Copy:**
  - `backend/app/ledger/checkpoint.py` (witness checkpoints and bundles) is completely absent from all documentation files.
  - `backend/app/api/lifecycle.py` (key rotation and passphrase change) is completely absent from `docs/API.md`.
  - `backend/app/pdf/worker.py` (process pool isolation) is absent from `docs/ARCHITECTURE.md`.

---

## 5. Security & Verification Status

- **Cryptographic Algorithms:** ML-KEM-768, ML-DSA-44, AES-256-GCM, HKDF-SHA256, scrypt are strictly enforced without fallback.
- **Fail-Closed Verification:** Active across all modules. Any error or anomaly yields zero attribution.
- **Supply-Chain Assurance:** Verified. Committed CBOM and SBOM pass drift check against installed virtualenv.
- **Air-Gap Integrity:** No runtime network calls.

---

## 6. Deployment Status

- **Host:** Windows local machine, offline / air-gapped configuration.
- **Backend:** Accessible at `http://127.0.0.1:8000`.
- **Frontend:** Accessible at `http://127.0.0.1:5173`.
- **Data Persistence:** Local filesystem directory `backend/data/` (SQLite DB, Keystores, Documents vault).
