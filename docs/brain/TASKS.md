# Engineering Task System

> **Executable Task Registry for AI Agents & Engineers**  
> Every task is scoped to be atomic and executable without reconstructing the whole project context.  
> Statuses: `BACKLOG` | `READY` | `IN_PROGRESS` | `BLOCKED` | `VERIFYING` | `DONE`

---

## Task Summary Table

| Task ID | Title | Status | Priority | Relevant Subsystem |
|---|---|---|---|---|
| **TASK-001** | Resolve DecryptRequest Schema & Test Breakage | `READY` | CRITICAL | Backend API / Schemas / Tests |
| **TASK-002** | Align Investigation Verdict States (UNVERIFIED vs NOT_ATTRIBUTABLE) | `READY` | HIGH | Attribution Engine / API / Schemas |
| **TASK-003** | Reconcile Recipient Enrolment & Creation Schema | `READY` | HIGH | Identity / API / Schemas |
| **TASK-004** | Fix Trust Manifest Registry Drift Check in Tests | `READY` | HIGH | Trust Anchor / Tests |
| **TASK-005** | Verify Full End-to-End Workflow & 194-Test Suite | `BLOCKED` (by 001-004) | CRITICAL | Full Test Suite / Quality Gate |
| **TASK-006** | Formalize & Track Key Lifecycle & Checkpoint Subsystems | `BACKLOG` | MEDIUM | Architecture / Ledger / Docs |
| **TASK-007** | Extend Frontend UI for Trust Anchor & Manifest Management | `BACKLOG` | MEDIUM | Frontend UI / Trust Subsystem |

---

## Detailed Task Specifications

### TASK-001: Resolve DecryptRequest Schema & Test Breakage
- **TASK ID:** `TASK-001`
- **TITLE:** Resolve DecryptRequest Schema & Test Breakage (Passphrase Step-up vs Session Unlock)
- **STATUS:** `COMPLETED`
- **PRIORITY:** `CRITICAL`
- **PURPOSE:** Eliminate the blocking HTTP 422 error on `/api/decrypt` that causes test failures in `test_e2e_workflow.py` and breaks the frontend UI.
- **DEPENDENCIES:** None
- **RELEVANT FILES:**
  - [backend/app/models/schemas.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/models/schemas.py)
  - [backend/app/api/decryption.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/decryption.py)
  - [tests/test_e2e_workflow.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_e2e_workflow.py)
  - [frontend/src/features/recipient/DecryptionTerminal.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/features/recipient/DecryptionTerminal.jsx)
- **REQUIREMENTS:**
  1. Update `test_e2e_workflow.py` to transmit recipient keystore passphrases.
  2. Implement `StepUpModal` in the frontend UI to prompt for the keystore passphrase without `window.prompt`.
  3. Ensure that an authenticated recipient with an active session can decrypt and verify provenance.
- **ACCEPTANCE CRITERIA:**
  - `POST /api/decrypt` succeeds when called with `{"document_id": "...", "passphrase": "..."}`.
  - `test_e2e_workflow.py` runs through all 18 steps with exit code 0.
- **TEST REQUIREMENTS:** `python tests/test_e2e_workflow.py` passes 100%.
- **SECURITY CONSIDERATIONS:** Keys decrypted in memory strictly for the request duration and immediately scrubbed.
- **VERIFICATION STATUS:** `VERIFIED COMPLETE`

---

### TASK-002: Align Investigation Verdict States (UNVERIFIED vs NOT_ATTRIBUTABLE)
- **TASK ID:** `TASK-002`
- **TITLE:** Reconcile Investigation Verdict Nomenclature across Code, Tests, and Docs
- **STATUS:** `READY`
- **PRIORITY:** `HIGH`
- **PURPOSE:** Resolve conflict between `UNVERIFIED` (asserted in `docs/*`, `frontend/src/App.jsx`, `test_trust_integration.py`) and `NOT_ATTRIBUTABLE` / `CORRELATED` (introduced in modified `schemas.py` and `forensics.py`).
- **DEPENDENCIES:** None
- **RELEVANT FILES:**
  - [backend/app/models/schemas.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/models/schemas.py)
  - [backend/app/forensics.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/forensics.py)
  - [backend/app/api/investigation.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/investigation.py)
  - [tests/test_trust_integration.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_trust_integration.py)
  - [tests/test_security_investigation.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_security_investigation.py)
- **REQUIREMENTS:**
  1. Standardize on the canonical verdict tri-state: `VERIFIED`, `UNVERIFIED`, `VERIFICATION_ERROR` as documented in `docs/ARCHITECTURE.md` and `docs/API.md`.
  2. If additional granular sub-statuses (e.g. `CORRELATED` where marker matches but hash differs) are retained, ensure the top-level `status` field remains backward compatible or properly mapped.
  3. Ensure `test_corrupted_local_snapshot_detected` assertion passes cleanly.
- **ACCEPTANCE CRITERIA:**
  - Investigation endpoints return consistent status codes recognized by both tests and frontend UI.
  - Zero test assertions fail due to status string mismatch.
- **TEST REQUIREMENTS:** `pytest tests/test_security_investigation.py tests/test_trust_integration.py -k "test_corrupted_local_snapshot_detected"` passes.
- **SECURITY CONSIDERATIONS:** Attribution must remain strictly fail-closed; no suspect name or flat attribution fields may ever be returned when status != `VERIFIED`.
- **VERIFICATION STATUS:** `NOT VERIFIED`

---

### TASK-003: Reconcile Recipient Enrolment & Creation Schema
- **TASK ID:** `TASK-003`
- **TITLE:** Fix Recipient Creation Schema & Support Enrolment Lifecycle
- **STATUS:** `READY`
- **PRIORITY:** `HIGH`
- **PURPOSE:** Fix `POST /api/recipients/create` 422 error caused by removing `initial_passphrase` from `RecipientCreate` while `test_enrolment_revocation_lifecycle` and `docs/API.md` require it.
- **DEPENDENCIES:** None
- **RELEVANT FILES:**
  - [backend/app/models/schemas.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/models/schemas.py)
  - [backend/app/api/recipients.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/recipients.py)
  - [tests/test_trust_integration.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_trust_integration.py)
- **REQUIREMENTS:**
  1. Support `initial_passphrase` in `RecipientCreate` schema (optional or required) so direct provisioning via authority remains functional.
  2. Maintain compatibility with `/api/enroll` if self-enrollment workflow is active.
- **ACCEPTANCE CRITERIA:**
  - `POST /api/recipients/create` accepts `initial_passphrase` without raising `extra_forbidden`.
  - `test_enrolment_revocation_lifecycle` completes successfully.
- **TEST REQUIREMENTS:** `pytest tests/test_trust_integration.py -k "test_enrolment_revocation_lifecycle"` passes.
- **SECURITY CONSIDERATIONS:** Initial passphrases must meet minimum length (12 characters) and never be logged or echoed in responses.
- **VERIFICATION STATUS:** `NOT VERIFIED`

---

### TASK-004: Fix Trust Manifest Registry Drift Check in Tests
- **TASK ID:** `TASK-004`
- **TITLE:** Restore Registry Drift Exception in Trust Module
- **STATUS:** `READY`
- **PRIORITY:** `HIGH`
- **PURPOSE:** Fix `test_registry_key_substitution_is_not_trusted_and_not_relaunderable` which failed because `TrustError` with `REGISTRY_DRIFT` was not raised during key substitution.
- **DEPENDENCIES:** None
- **RELEVANT FILES:**
  - [backend/app/trust.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/trust.py)
  - [tests/test_trust_integration.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_trust_integration.py)
- **REQUIREMENTS:**
  1. Verify why `_next()` in `app/trust.py` failed to raise `TrustError(REGISTRY_DRIFT)`.
  2. Ensure registry key substitutions cannot be laundered into newly issued manifests.
- **ACCEPTANCE CRITERIA:**
  - `test_registry_key_substitution_is_not_trusted_and_not_relaunderable` passes.
- **TEST REQUIREMENTS:** `pytest tests/test_trust_integration.py -k "test_registry_key_substitution"` passes.
- **SECURITY CONSIDERATIONS:** Substituting keys in the database registry must fail closed and block manifest re-issuance.
- **VERIFICATION STATUS:** `NOT VERIFIED`

---

### TASK-005: Verify Full End-to-End Workflow & 194-Test Suite
- **TASK ID:** `TASK-005`
- **TITLE:** Full Test Suite Verification (194 Tests + E2E Workflow Proof)
- **STATUS:** `BLOCKED`
- **PRIORITY:** `CRITICAL`
- **PURPOSE:** Validate that all 194 tests pass cleanly in an isolated temporary environment.
- **DEPENDENCIES:** `TASK-001`, `TASK-002`, `TASK-003`, `TASK-004`
- **RELEVANT FILES:**
  - All test files under [tests/](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/)
- **REQUIREMENTS:**
  1. Execute `pytest tests -q`.
  2. Execute `python tests/test_e2e_workflow.py`.
  3. Ensure 0 failures and 0 errors.
- **ACCEPTANCE CRITERIA:**
  - 100% tests passing (194/194).
  - 18-step E2E demonstration script logs `ALL 18 END-TO-END DEMONSTRATION STEPS PASSED`.
- **TEST REQUIREMENTS:** Both full test commands exit with code 0.
- **SECURITY CONSIDERATIONS:** No test fixtures may bypass production security checks or leave sensitive artifacts on disk.
- **VERIFICATION STATUS:** `NOT VERIFIED`

---

### TASK-006: Formalize & Track Key Lifecycle & Checkpoint Subsystems
- **TASK ID:** `TASK-006`
- **TITLE:** Formalize, Document, and Test Untracked Working Subsystems
- **STATUS:** `BACKLOG`
- **PRIORITY:** `MEDIUM`
- **PURPOSE:** Integrate or cleanly isolate the untracked modules (`backend/app/api/lifecycle.py`, `backend/app/ledger/checkpoint.py`, `backend/app/pdf/worker.py`).
- **DEPENDENCIES:** `TASK-005`
- **RELEVANT FILES:**
  - [backend/app/api/lifecycle.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/lifecycle.py)
  - [backend/app/ledger/checkpoint.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/ledger/checkpoint.py)
  - [backend/app/pdf/worker.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/pdf/worker.py)
  - [docs/API.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/API.md)
  - [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md)
  - [docs/DATABASE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/DATABASE.md)
- **REQUIREMENTS:**
  1. Audit complete security and functional behavior of key lifecycle, checkpoints, and worker.
  2. Document endpoints in `docs/API.md` and schema tables in `docs/DATABASE.md`.
  3. Add comprehensive automated tests covering all new code paths.
- **ACCEPTANCE CRITERIA:**
  - No undocumented untracked files remain in the repository.
  - Documentation and implementation are in 100% agreement.
- **TEST REQUIREMENTS:** Dedicated unit and adversarial security tests.
- **SECURITY CONSIDERATIONS:** Witness keys and checkpoint cosignatures must follow pinned trust model.
- **VERIFICATION STATUS:** `NOT VERIFIED`

---

### TASK-007: Extend Frontend UI for Trust Anchor & Manifest Management
- **TASK ID:** `TASK-007`
- **TITLE:** Add UI Management for Trust Manifests & Principal Lifecycle
- **STATUS:** `COMPLETED`
- **PRIORITY:** `MEDIUM`
- **PURPOSE:** Allow Station Authority (WESEE_HQ) and Auditor (AUDITOR_01) to view, export, import, and revoke trust manifests via the web UI without requiring curl or scripts.
- **DEPENDENCIES:** `TASK-005`
- **RELEVANT FILES:**
  - [frontend/src/features/authority/TrustDesk.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/features/authority/TrustDesk.jsx)
  - [frontend/src/features/authority/PersonnelManager.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/features/authority/PersonnelManager.jsx)
  - [frontend/src/features/recipient/StationKeyStatus.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/features/recipient/StationKeyStatus.jsx)
- **REQUIREMENTS:**
  1. Add dedicated "Trust Desk" and "Personnel Registry" views in Authority workspace.
  2. Support displaying the current pinned authority fingerprint, manifest version, and attested roster.
  3. Support station enrollment code generation and attestation.
  4. Support principal revocation action for `AUTHORITY` with deliberate confirmation.
- **ACCEPTANCE CRITERIA:**
  - Authority can inspect trust manifest state, pin location, and pending attestations.
  - Frontend passes `npm run lint` and `npm run build`.
- **TEST REQUIREMENTS:** `npm run build` and `npm run lint` verified.
- **SECURITY CONSIDERATIONS:** Never expose passphrases or private keys in the UI; only export signed public manifest packages.
- **VERIFICATION STATUS:** `VERIFIED COMPLETE`
