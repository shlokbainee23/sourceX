# Risk Register & Hallucination Assessment

> **Repository Risk & Vulnerability Catalog**  
> Distinguishes between VERIFIED risks (directly confirmed by code, configuration, or test results) and SUSPECTED risks (inferred from design patterns or operational context).  
> *Rules:* Severity is derived strictly from real architectural evidence, not perceived importance.

---

## 1. Verified Risks

### RISK-SEC-01: Working Copy Schema Divergence Breaks Security Test Suite
- **ID:** `RISK-SEC-01`
- **Category:** `TESTING` / `SECURITY`
- **Risk:** Uncommitted modifications to `backend/app/models/schemas.py` and `backend/app/api/decryption.py` broke 17 security and workflow tests, preventing verification of regression freedom and breaking frontend decryption.
- **Evidence:** `pytest tests -q` results in 17 failures out of 194 tests. `test_e2e_workflow.py` fails on step [2] with 422 Unprocessable Entity due to required `passphrase` in `DecryptRequest`.
- **Severity:** `CRITICAL`
- **Current Mitigation:** None in active working tree. Baseline commit `7542c92` had passing tests.
- **Status:** `ACTIVE / UNRESOLVED`
- **Recommended Action:** Execute `TASK-001` and `TASK-003` to make step-up `passphrase` optional or backward-compatible, restoring full test suite pass rate.

---

### RISK-SEC-02: Watermark Token Removal via Text Stripping or Print-and-Scan
- **ID:** `RISK-SEC-02`
- **Category:** `SECURITY`
- **Risk:** An adversary can extract or remove the invisible text watermark (render mode 3) using standard PDF tools, OCR, rasterization (converting PDF pages to images), or printing and scanning.
- **Evidence:** Stated honestly in [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L105) and [README.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/README.md#L118).
- **Severity:** `HIGH`
- **Current Mitigation:** System does not claim to be a digital rights management (DRM) or leak-prevention system; it is a forensic attribution marker. Any file alteration triggers the exact-hash failure, failing closed (`UNVERIFIED`).
- **Status:** `ACCEPTED SCOPE BOUNDARY`
- **Recommended Action:** Document as explicit boundary; future production roadmap requires layered steganography and fuzzy perceptual hashing.

---

### RISK-SEC-03: Server-Side Keystores vs Hardware Security Modules (HSM)
- **ID:** `RISK-SEC-03`
- **Category:** `SECURITY` / `ARCHITECTURE`
- **Risk:** Private keys reside on the server's disk (encrypted with scrypt + AES-GCM) and are held in process memory while sessions are active. The server signs decryption records on behalf of the recipient. A root compromise of the server could compromise keys in memory.
- **Evidence:** [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L34-L35). Python cannot guarantee memory zeroization.
- **Severity:** `HIGH`
- **Current Mitigation:** Keys are never stored unencrypted on disk; scrypt derivation with random salt; session memory cleared on logout/expiry (30-min TTL); server restricts access by bearer token.
- **Status:** `ACCEPTED FOR PROTOTYPE`
- **Recommended Action:** Production deployment must transition to client-side signing on smartcards/tokens (PKCS#11 / HSM) as required by MHA NISPG.

---

### RISK-SEC-04: Single Authority Key Compromise
- **ID:** `RISK-SEC-04`
- **Category:** `SECURITY`
- **Risk:** If the WESEE_HQ private key is compromised, an attacker can sign fraudulent trust manifests that match the pinned fingerprint in `trust_anchor/authority.pin`.
- **Evidence:** [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L89-L90). The prototype has no in-band authority rotation mechanism.
- **Severity:** `HIGH`
- **Current Mitigation:** Authority pin lives outside the database and data directory; manifests are append-only and monotonic; cannot remove or relaunder existing attested principals.
- **Status:** `DOCUMENTED`
- **Recommended Action:** Store the pin file on read-only hardware media; establish out-of-band authority re-keying protocol.

---

### RISK-AI-01: AI Agent Context Hallucination & Fictional Capability Invention
- **ID:** `RISK-AI-01`
- **Category:** `AI / HALLUCINATION`
- **Risk:** Future AI agents working on the codebase may hallucinate that government APIs (DigiLocker, API Setu) or blockchain networks (Ethereum, Hyperledger) exist, or invent fictional completion percentages.
- **Evidence:** Previous AI edits modified schemas and created untracked subsystems (`lifecycle.py`, `checkpoint.py`) that diverged from authoritative docs and broke test fixtures.
- **Severity:** `HIGH`
- **Current Mitigation:** Strict project brain system established in `docs/brain/` with explicit evidence states (`VERIFIED`, `DOCUMENTED`, `INFERRED`, `UNKNOWN`, `CONFLICT`).
- **Status:** `MITIGATED BY BRAIN SYSTEM`
- **Recommended Action:** Enforce [AGENTS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/AGENTS.md) rules prohibiting unverified claims and silent schema modifications.

---

### RISK-DATA-01: Head Anchor File Crash Desynchronization
- **ID:** `RISK-DATA-01`
- **Category:** `RELIABILITY` / `DATA`
- **Risk:** If the server process crashes between the SQLite transaction COMMIT of a ledger block and the writing of `backend/data/ledger_head.json`, the ledger verification will detect a mismatch between the database tail and head anchor.
- **Evidence:** [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L111-L112), [backend/app/ledger/blockchain.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/ledger/blockchain.py).
- **Severity:** `MEDIUM`
- **Current Mitigation:** Verification fails closed; startup reconciliation logic (`reconcile_head_anchor()`) was drafted in working tree to detect and log recovery events.
- **Status:** `PARTIALLY MITIGATED`
- **Recommended Action:** Formalize atomic commit-and-anchor pattern or embed head anchor state directly into SQLite WAL checkpoint.

---

### RISK-UX-01: Frontend Lacks Trust Manifest & Key Lifecycle Management
- **ID:** `RISK-UX-01`
- **Category:** `UX`
- **Risk:** The React frontend dashboard (`frontend/src/App.jsx`) contains tabs for broadcast, decryption, invariance, investigation, ledger, and tamper testing, but zero UI elements for trust manifest export/import, revocation, or key lifecycle.
- **Evidence:** Frontend route audit of [frontend/src/App.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L433-L463).
- **Severity:** `MEDIUM`
- **Current Mitigation:** Trust manifest provisioning is executed via CLI script (`scripts/provision_identities.py`).
- **Status:** `ACTIVE / BACKLOG`
- **Recommended Action:** Implement `TASK-007` to add trust management interface to the UI.

---

## 2. Suspected Risks

### RISK-PERF-01: Pure-Python Dilithium Performance on Bulk Operations
- **ID:** `RISK-PERF-01`
- **Category:** `PERFORMANCE`
- **Risk:** The ML-DSA-44 signature implementation uses `dilithium-py` (pure Python). In high-throughput decryption scenarios, signing operations may introduce latency.
- **Evidence:** Full pytest suite with 194 tests takes ~132 seconds, primarily spent in Python lattice arithmetic.
- **Severity:** `LOW`
- **Current Mitigation:** Decryption is an interactive, per-recipient operational event; not high-frequency streaming.
- **Status:** `SUSPECTED / MONITORED`
- **Recommended Action:** Evaluate C-extension or Rust bindings for ML-DSA if throughput requirements increase.

---

### RISK-DEP-01: Windows File Path and Subprocess Limitations in PDF Worker
- **ID:** `RISK-DEP-01`
- **Category:** `DEPLOYMENT`
- **Risk:** Untracked PDF worker (`backend/app/pdf/worker.py`) uses `multiprocessing.ProcessPoolExecutor`. On Windows, process spawning overhead is significant, and memory limits (`resource.setrlimit`) cannot be enforced.
- **Evidence:** Explicitly documented in [backend/app/pdf/worker.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/pdf/worker.py#L11-L15).
- **Severity:** `LOW`
- **Current Mitigation:** Worker sets timeouts and process recycling on failure.
- **Status:** `DOCUMENTED LIMITATION`
- **Recommended Action:** Maintain documented limitation for Windows environments; leverage Linux cgroups/systemd for production naval appliance.
