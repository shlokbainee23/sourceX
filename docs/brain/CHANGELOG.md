# Project Brain Changelog

## [2026-09-29] — Withhold attribution for modified copies

- Corrected the `CORRELATED` verdict: a marker linked to a signed decryption
  record no longer identifies a recipient unless the uploaded file's exact hash
  matches the delivered copy.
- Withheld attribution and joinable recipient/session/document/block fields,
  raw marker token, and signer key ID from modified-copy responses and reports.
  Deferred identity-linked hash/signature audit events until all ten checks pass.
- Updated the investigation UI and security regression expectations.

## [2026-09-29] — Button hover feedback

- Added shared colour-changing hover styles for native buttons across landing,
  login and workspaces, including nested labels/icons; danger and warning keep
  semantic colours. Added keyboard focus and reduced-motion support.
- Shared Button hover/active utilities now exclude disabled controls.
- Added an optional local Playwright regression for rendered button styles.
- Production build and seven API tests pass; existing lint warnings remain.
  Before/after backend runs both report 173 passed, 16 failed and 7 errors
  (including filesystem permission errors); E2E passes all 18 steps and BOM
  still reports 385 pre-existing drift items. Backend code is unchanged.

## [2026-09-29] — SourceX frontend/backend integration

- Compared the provided archive, GitHub `171db49`, and deployed Vercel assets.
  Found matching frontend JavaScript but no functioning API on the public host.
- Added optional local build hosting at `/workstation/`, preserving the API root
  and existing endpoints; relative assets support both local and Vercel hosting.
- Added readable connection failures and authentication-response validation;
  login now checks backend availability, and engine status starts as unknown.
- Removed frontend demo passphrases. Station switching terminates the old session
  and prompts for the selected station's actual credentials.
- Added a workstation launcher, locked Vercel installation commands, regression
  tests, deployment instructions and checksum-preserving BOM line-ending rules.
- Verified frontend build, 7 API tests, 2 hosting tests, real client workflow, and
  browser login/navigation for all four roles. Full Python suite has no new
  failures: 179 passed / 17 failed versus baseline 176 passed / 18 failed.
- Recorded existing security-contract conflicts, BOM drift and npm audit findings
  in CURRENT_STATE.md. No cryptographic behavior, operational data or live deployment changed.

> **Engineering Change Log**  
> Tracks initialization, architectural reconciliation, and brain system updates.  
> *Rules:* No simulated historical entries. Only verified actions executed in the repository are recorded.

---

## [2026-09-28] — Project Brain System Initialization

### Initialized
- Brain system initialized on 2026-09-28.
- Created `docs/brain/` navigation, state, task, decision, risk, and change tracking system:
  - `docs/brain/PROJECT_BRAIN.md`: High-density index referencing authoritative documentation without duplicating content.
  - `docs/brain/CURRENT_STATE.md`: Comprehensive snapshot of actual repository state, verified features, working-copy divergences, and root-cause analysis of the 17 failing tests.
  - `docs/brain/TASKS.md`: Executable atomic task specifications (`TASK-001` through `TASK-007`) targeting test resolution, schema alignment, and subsystem tracking.
  - `docs/brain/DECISIONS.md`: Authoritative record of 12 established architectural decisions (`DEC-001` through `DEC-012`) with repository evidence links.
  - `docs/brain/RISKS.md`: Catalog of verified and suspected risks across security, testing, architecture, hallucination, reliability, and UX domains.
  - `docs/brain/CHANGELOG.md`: This file.

### Audited
- Full codebase audit across backend (`backend/app`), frontend (`frontend/src`), test suite (`tests/`), scripts (`scripts/`), documentation (`docs/`), bills of materials (`bom/`), and git history.
- Verified passing state of `frontend`: `npm run lint` (0 errors) and `npm run build` (success).
- Verified passing state of BOM inventory: `python scripts/generate_bom.py --check` (success).
- Executed full Pytest suite (194 tests) and identified root causes of 17 failures stemming from working-copy schema and verdict naming changes.
- Identified untracked draft subsystems (`backend/app/api/lifecycle.py`, `backend/app/ledger/checkpoint.py`, `backend/app/pdf/worker.py`).

## [2026-09-28] — Industrial Product Transformation & E2E Proof Resolution

### Completed
- **P0.1 & P0.2 Fixed:** Resolved decryption contract mismatch (`passphrase` step-up auth) and eliminated all native browser dialogs (`window.prompt`, `window.alert`, `window.confirm`). Implemented `StepUpModal` and `ConfirmModal`.
- **E2E 18-Step Proof:** All 18 steps of `tests/test_e2e_workflow.py` verified passing.
- **Frontend Modular Transformation:** Decomposed monolithic 1,219-line `App.jsx` into modular defense workstation architecture:
  - `src/app/`: `config.js`, `AuthContext.jsx` (sessionStorage token custody, `/api/auth/me` validation, server logout), `RouterContext.jsx` (hash router with deep linking and history).
  - `src/services/api.js`: Unified API client with automatic token injection and error mapping.
  - `src/components/common/`: `Badge.jsx`, `Button.jsx` (truthful loading spinners, zero fake timers), `Card.jsx`, `HashDisplay.jsx` (monospace, copy-to-clipboard), `Modal.jsx`, `StepUpModal.jsx`, `ConfirmModal.jsx`, `Alert.jsx`.
  - `src/components/layout/`: `DefenseHeader.jsx` (WESEE / MoD branding, air-gap status), `RoleNav.jsx` (role-gated navigation), `SystemFooter.jsx`, `AppShell.jsx`.
  - `src/features/auth/`: `LoginPage.jsx` (station selection, unmasked credential elimination).
  - `src/features/authority/`: `DirectivesManager.jsx`, `PersonnelManager.jsx`, `TrustDesk.jsx`, `AuthorityWorkspace.jsx`.
  - `src/features/recipient/`: `InboxView.jsx`, `DecryptionTerminal.jsx` (step-up auth, verified provenance, one-time download with HTTP 410 handling), `StationKeyStatus.jsx`, `RecipientWorkspace.jsx`.
  - `src/features/investigation/`: `IntakeVerification.jsx`, `VerdictDisplay.jsx` (10-point check checklist, strict fail-closed attribution), `VisualInvarianceTool.jsx` (150-DPI raster hash comparison), `DossierArchive.jsx` (`/api/reports` integration), `InvestigatorWorkspace.jsx`.
  - `src/features/auditor/`: `LedgerExplorer.jsx`, `AuditTrailViewer.jsx` (real `/api/audit` integration), `TamperSandbox.jsx` (adversarial simulation mode with chain breakage and restore), `AuditorWorkspace.jsx`.
- **Build & Quality Gates Verified:**
  - `npm run lint`: 0 errors.
  - `npm run build`: built in <700ms.
  - `python scripts/generate_bom.py --check`: PASSED.
  - `python tests/test_e2e_workflow.py`: ALL 18 PROOF STEPS PASSED.
