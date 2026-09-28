# MASTER PRODUCT UX ARCHITECTURE & INTEGRATION AUDIT
**Version:** Sanjay UI  
**Project:** SIH26237 — Offline Forensic Attribution System for Broadcast-Encrypted Documents  
**Sponsoring Organization:** Ministry of Defence // Indian Navy — WESEE  
**Audit Role:** Senior Product Engineer, UX Architect, UI/UX Lead & Frontend Systems Architect  
**Audit Phase:** Phase 1 — Reverse-Engineering, Integration Audit & UX Architecture *(No UI Redesign Implemented)*  

---

## 1. Executive Summary

### 1.1 Product Purpose & Value Proposition
The application is an air-gapped, sovereign cryptographic provenance and forensic attribution engine developed for the Indian Navy (WESEE). 
In high-security defence environments, classified directives are distributed via **broadcast encryption** (encrypted once for multiple officers, where each recipient independently decrypts their copy). Historically, all decrypted copies are bit-for-bit identical, meaning if an officer leaks a document, every recipient is equally suspect, and pre-encryption watermarks fail because every recipient receives the exact same watermark.

This system solves the attribution dilemma by acting **at the exact moment of decryption**:
1. It injects a unique, opaque 256-bit cryptographic attribution marker (`WM-<64 hex>`) into the PDF as invisible text (PDF text render mode 3) and document metadata. PyMuPDF pixel rasterization at 150 DPI produces **0 differing pixels** between decrypted copies.
2. The recipient cryptographically signs a canonical decryption record binding their identity, document hash, marker, and session ID using Post-Quantum Digital Signatures (**ML-DSA-44 / FIPS 204**).
3. The signed provenance record is committed to a local, append-only SQLite hash-chained ledger.
4. When a leaked document is recovered, an investigator uploads it. The system performs a strict 10-point fail-closed verification pipeline (marker extraction, exact hash matching, ledger lookup, signature verification, trust-anchor attestation, chain consistency). If all pass, the specific recipient is named with mathematical certainty; if any check fails, the result is fail-closed (`UNVERIFIED` or `VERIFICATION_ERROR`), naming no suspects.

### 1.2 Current State Assessment: Core Paradox
* **Backend Maturity:** The backend ([`backend/app/`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app)) is a robust, production-grade cryptographic service supporting ML-KEM-768 key encapsulation, ML-DSA-44 signatures, scrypt/AES-256-GCM local encrypted keystores, monotonic signed trust manifests with authority pinning, witness cosignatures, and an append-only hash chain.
* **Frontend State:** The frontend ([`frontend/src/App.jsx`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx)) is a **1,219-line single-file monolithic demonstration script** written in React 19 + Tailwind CSS v4. It lacks client-side routing, contains zero component modularity, stores all state in volatile memory, exposes non-functional and uncoordinated controls, numbers navigation tabs 1 through 6 as a single sequential demo script, and uses browser native dialogs (`window.prompt`, `window.alert`, `window.confirm`) for military officer authentication.
* **P0 Critical Integration Break:** During Schema v4 development, the backend added a mandatory step-up authentication requirement (`passphrase: str = Field(..., min_length=1)`) to `POST /api/decrypt` ([`schemas.py:L106`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/models/schemas.py#L106)). However, `App.jsx` ([`App.jsx:L208-L213`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L208-L213)) was never updated and sends only `{ document_id }`. As a result, **recipient decryption currently crashes with HTTP 422 Unprocessable Entity in the UI**.

---

## 2. Current Application Architecture

### 2.1 Technology Stack & Runtime Topology

```
                       AIR-GAPPED CLIENT BROWSER (Port 5173)
                                      |
         Vite Dev Server Proxy (/api/* -> http://localhost:8000)
                                      |
                         FASTAPI BACKEND (Port 8000)
    +-------------------------------------------------------------------+
    | Core Endpoints:                                                   |
    | - /api/auth/*        (Sessions, Keystore Unlock, Lockout Engine)  |
    | - /api/documents/*   (PDF Registration, Vault Storage)            |
    | - /api/encrypt/*     (ML-KEM-768 Encapsulation, AES-256-GCM CEK) |
    | - /api/decrypt/*     (Step-Up Unlock, Watermarking, ML-DSA-44)    |
    | - /api/investigate/* (Forensic Leak Attribution Pipeline)         |
    | - /api/trust/*       (Signed Manifests, Attestation, Revocation)  |
    | - /api/ledger/*      (Hash Chain, Checkpoints, Tamper Sandboxing) |
    | - /api/audit/*       (Append-Only Security Audit Trail)           |
    +-------------------------------------------------------------------+
           |                          |                         |
     SQLite Engine              Local Keystore           Document Vault
   (sih26237.sqlite)          (data/keystore/*.json)      (data/documents/)
   [Append-Only Triggers]     [scrypt + AES-256-GCM]      [Ephemeral Delivery]
```

#### Frontend Stack
* **Runtime & Framework:** React 19.2.8, React DOM 19.2.8, Vite 8.3.0.
* **Styling:** Tailwind CSS v4.3.3 (`@tailwindcss/vite`).
* **Icons:** `lucide-react` 1.48.0.
* **Routing:** **None.** Single-page conditional rendering via `useState('dashboard')`.
* **State Management:** Unsynchronized local `useState` hooks inside [`App.jsx`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx).

#### Backend Stack
* **Framework:** Python 3.12+ FastAPI 0.115+, Uvicorn.
* **Post-Quantum Cryptography:** 
  * `mlkem` (ML-KEM-768 / FIPS 203) for post-quantum key encapsulation.
  * `dilithium_py` (ML-DSA-44 / FIPS 204) for post-quantum digital signatures.
* **Symmetric Cryptography & KDF:** `cryptography` (AES-256-GCM, HKDF-SHA256, scrypt).
* **PDF Engine:** PyMuPDF (`pymupdf`) for non-rendering text injection (ISO 32000-1 Mode 3) and raster rendering verification.
* **Database & Persistence:** SQLite with custom SQL append-only database triggers (`ledger_no_update`, `ledger_no_delete`, `sessions_no_update`, `sessions_no_delete`, `audit_no_update`, `audit_no_delete`, `keys_no_rekey`).

### 2.2 Operational Personas & Roles

| Persona | Principal ID | Role | Responsibilities |
|---|---|---|---|
| **Issuing Authority** | `WESEE_HQ` | `AUTHORITY` | Registers classified directives, encrypts directives once for designated recipients, enrols/revokes officers, signs trust manifests. |
| **Recipients** | `R001` (Cmdr Alpha), `R002` (Offr Bravo), `R003` (Offr Charlie) | `RECIPIENT` | Decrypts packages encrypted for their station, signs decryption provenance record with station ML-DSA-44 key, downloads one-time delivered copy. |
| **Investigator** | `INVESTIGATOR_01` | `INVESTIGATOR` | Uploads recovered/leaked files, triggers strict 10-point forensic attribution check, generates signed forensic reports. |
| **Auditor** | `AUDITOR_01` | `AUDITOR` | Verifies hash-chain continuity and head anchor, inspects security audit trail, runs tamper sandboxing simulations. |

---

## 3. Complete Route Map

The application currently has **no client-side router** (URLs never change from `/`). Navigation is simulated using an internal tab state variable `activeTab` inside [`App.jsx`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx). Below is the comprehensive route map correlating the frontend tab views with the underlying backend endpoints:

| Virtual Route / Tab | Component / Section | Auth Required | Allowed Roles | Entry Point | Exit / Next Step | Data & API Dependencies | Implementation Status |
|---|---|---|---|---|---|---|---|
| `/` (`dashboard`) | Operational Overview ([`App.jsx:L490-633`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L490-L633)) | Optional (public read-only) | All | Initial Load | Tab Bar, "Switch to Officer" | `GET /api/recipients`<br>`GET /api/documents`<br>`GET /api/ledger`<br>`GET /api/ledger/verify` | **PARTIAL** (Static crypto matrix, non-interactive document cards) |
| `/sender` (`sender`) | Sender Broadcast ([`App.jsx:L635-734`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L635-L734)) | Yes (Bearer token) | `AUTHORITY` | Tab Bar | Tab 2 (`recipient`) | `POST /api/documents/register`<br>`POST /api/documents/encrypt` | **WORKING** (Authority only; ignores role gating in UI) |
| `/recipient` (`recipient`) | Recipient Decryption ([`App.jsx:L736-842`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L736-L842)) | Yes (Bearer token) | `RECIPIENT` | Tab Bar, Dashboard "Switch" | Download Button, Tab 4 | `POST /api/decrypt`<br>`GET /api/sessions/{id}/download` | **BROKEN** (`passphrase` omitted from payload → HTTP 422) |
| `/invariance` (`invariance`) | Visual Invariance ([`App.jsx:L844-903`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L844-L903)) | Yes (Bearer token) | `AUTHORITY`, `INVESTIGATOR`, `AUDITOR` | Tab Bar | Tab 5 (`investigation`) | `POST /api/forensics/invariance` | **PARTIALLY WORKING** (Selects 2 latest sessions from memory; crashes if `< 2` sessions exist) |
| `/investigation` (`investigation`) | Leak Forensics ([`App.jsx:L905-1025`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L905-L1025)) | Yes (Bearer token) | `INVESTIGATOR` | Tab Bar | View Verdict Details | `POST /api/investigate` | **WORKING** (Displays all 10 verification check badges) |
| `/ledger` (`ledger`) | Tamper-Evident Ledger ([`App.jsx:L1027-1096`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1027-L1096)) | Yes (Bearer token) | `AUTHORITY`, `INVESTIGATOR`, `AUDITOR` | Tab Bar | Audit Button, Reset Button | `GET /api/ledger`<br>`GET /api/ledger/verify`<br>`POST /api/ledger/reset` | **WORKING** (Dumps raw JSON blocks; reset button enabled for all) |
| `/tamper` (`tamper`) | Tamper Sandbox ([`App.jsx:L1098-1168`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1098-L1168)) | Yes (Bearer token) | `AUDITOR` | Tab Bar | Re-audit Button | `POST /api/ledger/tamper-test`<br>`GET /api/ledger/verify`<br>`POST /api/ledger/reset` | **WORKING** (Demo mode only; mutates block in SQLite directly) |
| *No UI Route* | Trust Anchor & Manifests | Yes | `AUTHORITY`, `AUDITOR` | None | None | `GET /api/trust/manifest`<br>`POST /api/trust/import`<br>`GET /api/trust/manifest/export` | **MISSING IN UI** (Backend endpoints exist, no UI controls) |
| *No UI Route* | Officer Enrolment & Key Lifecycle | Partial (Public / Auth) | `AUTHORITY`, `RECIPIENT` | None | None | `POST /api/enroll`<br>`POST /api/recipients/create`<br>`POST /api/keys/rotate`<br>`POST /api/auth/change-passphrase` | **MISSING IN UI** (Backend endpoints exist, no UI controls) |
| *No UI Route* | Security Audit Trail | Yes | `AUDITOR` | None | None | `GET /api/audit` | **MISSING IN UI** (UI uses fake client log array instead of real audit trail) |
| *No UI Route* | Forensic Reports Repository | Yes | `INVESTIGATOR`, `AUDITOR`, `AUTHORITY` | None | None | `GET /api/reports`<br>`GET /api/reports/{id}` | **MISSING IN UI** (Historical reports cannot be viewed or downloaded) |
| *No UI Route* | Ledger Checkpoints & Witnesses | Yes | `AUTHORITY`, `AUDITOR` | None | None | `GET /api/ledger/witness`<br>`POST /api/ledger/checkpoint`<br>`POST /api/ledger/cosignature` | **MISSING IN UI** (Cross-node witnessing has no UI) |

---

## 4. Current vs Proposed Information Architecture

### 4.1 Current Information Architecture (Flat & Monolithic)

```
Root (Single Page App)
├── Top Navigation (Horizontal Tabs)
│   ├── [Tab] Operational Overview (Dashboard)
│   ├── [Tab] 1. Sender Broadcast
│   ├── [Tab] 2. Recipient Decryption
│   ├── [Tab] 3. Visual Invariance
│   ├── [Tab] 4. Leak Forensics
│   ├── [Tab] 5. Tamper-Evident Ledger
│   └── [Tab] 6. Tamper Sandbox
├── Station Switcher Dropdown (Forces window.prompt on change)
├── Main Workspace (Conditional render of 1 active tab)
└── Right Sidebar (Ephemeral React State Logs)
```

**Architectural Deficiencies:**
1. **Sequential Script Illusion:** Numbering tabs 1 to 6 presents the application as a single wizard step flow rather than a multi-persona enterprise defense system.
2. **Missing Security Boundaries:** A Recipient sees the Sender and Tamper tabs; an Auditor sees Decryption and Broadcast controls.
3. **Hidden Core Subsystems:** Key management, identity attestation, trust anchor manifests, and real audit logs are buried without any representation in the IA.

### 4.2 Proposed Information Architecture (Role-Aware Product Architecture)

```
Sovereign Defense Attribution System (SIH26237)
│
├── Public / Unauthenticated Space
│   ├── Station Login Portal (Station selection, passphrase unlock, lockout feedback)
│   └── Officer Identity Enrolment (Redeem one-time code, generate local PQC keys)
│
├── Authenticated Core System (Role-Gated Shell with Persistent Session)
│   │
│   ├── Global Navigation Header
│   │   ├── Defense Header (Ministry of Defence / Indian Navy WESEE branding)
│   │   ├── Real-time Engine Health & PQC Status Badges
│   │   ├── Active Station Profile Card (Role, Principal ID, Attestation Status)
│   │   └── Session Controls (Lock Station, Change Passphrase, Logout)
│   │
│   ├── Issuing Authority Workspace (Role: AUTHORITY)
│   │   ├── Document Vault & Registration
│   │   │   ├── Registered Directives Library
│   │   │   ├── Directive Intake (Upload PDF, Set Classification)
│   │   │   └── Broadcast Encryption Console (ML-KEM-768 Recipient Selection)
│   │   ├── Officer & Key Directory
│   │   │   ├── Officer Registry (Active, Pending, Revoked)
│   │   │   ├── Enrolment Dispatch (Generate one-time onboarding codes)
│   │   │   └── Key Attestation Desk (Confirm ML-DSA fingerprints out-of-band)
│   │   └── Trust Anchor Administration
│   │       ├── Manifest Manager (Version, SHA-256, Pinned Key)
│   │       ├── Package Export/Import (Offline air-gapped node exchange)
│   │       └── Key Revocation & Compromise Declaration
│   │
│   ├── Officer Decryption Workspace (Role: RECIPIENT)
│   │   ├── Assigned Directives Inbox (Documents packaged for current officer)
│   │   ├── Secure Decryption Terminal
│   │   │   ├── Step-Up Passphrase Verification Dialog
│   │   │   ├── Cryptographic Pipeline Telemetry
│   │   │   └── Provenance Commitment Summary
│   │   ├── One-Time Document Dispatch (Single-download safeguard with destruction warning)
│   │   └── Key Lifecycle Management (View key history, initiate key rotation)
│   │
│   ├── Forensic Investigation Lab (Role: INVESTIGATOR, AUTHORITY)
│   │   ├── Leak Intake (Upload suspicious PDF)
│   │   ├── Attribution Verification Engine (10-point cryptographic breakdown)
│   │   ├── Visual Invariance Inspector (Comparative 150-DPI pixel delta audit)
│   │   └── Evidence Reports Archive (Historical signed investigation dossiers)
│   │
│   └── Ledger & Audit Console (Role: AUDITOR, AUTHORITY, INVESTIGATOR)
│       ├── Provenance Ledger Explorer (Block-by-block hash chain inspector)
│       ├── Chain Verification Diagnostic (Automated head-to-genesis validator)
│       ├── Cryptographic Audit Trail (Real-time immutable security event log from /api/audit)
│       ├── Witness & Checkpoint Console (Offline cosignature import/export)
│       └── Adversarial Tamper Sandbox (Demonstration mode integrity testing)
```

---

## 5. Navigation Architecture & Element Audit

### 5.1 Navigation Elements Audit

| Element | Location | Target Destination | Observed Behavior | Problem / Defect | Recommendation |
|---|---|---|---|---|---|
| **Tab Buttons (1–6)** | Top Sub-header ([`App.jsx:L449-462`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L449-L462)) | Changes `activeTab` state | Switches visible view in main column | No URL updates; browser Back button exits the app; tabs are visible regardless of user role. | Implement React Router or hash routing; filter tab visibility based on authenticated `session.role`. |
| **STATION Select Dropdown** | Header Right ([`App.jsx:L468-481`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L468-L481)) | Calls `handleLogin(station)` | Triggers native `window.prompt` for passphrase; stores token in memory | Hardcoded list (`WESEE_HQ`, `R001`, `R002`, `R003`, `INVESTIGATOR_01`, `AUDITOR_01`). Unmasked password entry. Any newly provisioned recipient is missing. | Replace with dedicated Login modal/screen, dynamic station listing, password-masked input, and logout action. |
| **"Switch to Officer" Button** | Dashboard Recipient Card ([`App.jsx:L618-626`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L618-L626)) | Logs in as recipient & switches to `recipient` tab | Prompts passphrase via `window.prompt`, then flips `activeTab` to `'recipient'` | Cross-contaminates authority dashboard with recipient session switching. Bypasses normal authentication flow. | Remove direct login shortcuts from public dashboards; enforce explicit session transition. |
| **"Download Officer's Decrypted PDF"** | Recipient Decryption Card ([`App.jsx:L829-835`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L829-L835)) | `/api/sessions/{session_id}/download` | Fetches blob and triggers browser download | Backend destroys the file on download. If user clicks again, backend returns 410 Gone, but UI only logs "Download denied or file unavailable." | Add prominent warning that download is single-use; disable button after first successful download. |
| **"Reset to Genesis" Button** | Ledger Tab ([`App.jsx:L1037-1043`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1037-L1043)) & Tamper Tab ([`App.jsx:L1134-1139`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1134-L1139)) | `POST /api/ledger/reset` | Resets SQLite database tables and local state | Duplicated in two different tabs; uses native `window.confirm`; available even when logged in as non-admin if demo mode is enabled. | Restrict to Auditor/Authority in Demo mode; place in a dedicated Administrative Maintenance section with modal confirmation. |
| **"Clear" Telemetry Log** | Telemetry Sidebar Header ([`App.jsx:L1178-1183`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1178-L1183)) | Resets `logs` array to `[]` | Wipes the React state array | Misleads users into thinking they cleared audit logs; actually only clears ephemeral UI strings. Real audit events remain in DB. | Rename to "Clear Console Screen" and provide a distinct link to the true Cryptographic Audit Trail (`/api/audit`). |

---

## 6. Primary User Journeys (Trace & Audit)

### Journey 1: Station Authentication & Keystore Unlock
* **START:** User opens application.
* **Intent:** Log in as an authorized officer (`WESEE_HQ` or `R002`) to perform operational tasks.
* **Current Action:** Clicks "STATION" dropdown in header, selects principal ID. Browser pops unmasked `window.prompt("Enter keystore passphrase for R002:")`. User types passphrase.
* **Backend Flow:** `POST /api/auth/login` → verifies lockout table (`login_failures`) → checks `keystore/<id>.keystore.json` exists → derives scrypt key → decrypts AES-256-GCM keystore → verifies public key matches SQLite registry → generates 32-byte bearer token → stores `AuthSession` in memory.
* **Observed Status:** **FRAGMENTED & INSECURE**.
  * Passphrase is typed in cleartext in standard browser dialog.
  * Token is held in volatile React state (`authToken`). Pressing browser Refresh (F5) immediately logs the user out.
  * If login fails 5 times, backend locks the user out with exponential backoff (`LOGIN_LOCKOUT_SECONDS`), but UI displays only a generic error in the telemetry sidebar without lockout timers.

### Journey 2: Authority Document Registration & Broadcast Encryption
* **START:** Logged in as `WESEE_HQ`. User navigates to "1. Sender Broadcast".
* **Intent:** Register a classified directive PDF and broadcast-encrypt it for `R001`, `R002`, and `R003`.
* **Current Action:** Types Document ID (`docId`), selects Classification (`CONFIDENTIAL`), selects file from disk, clicks "Register Document with Authority". After success, checks recipient checkboxes, clicks "Broadcast Encrypt".
* **Backend Flow:**
  1. `POST /api/documents/register`: Uploads PDF multipart → checks SHA-256 → signs `DOCUMENT_REGISTRATION` with authority ML-DSA-44 key → commits block #1 to SQLite ledger → saves `DOC-2026-001_original.pdf` in vault.
  2. `POST /api/documents/encrypt`: Resolves operational keys against signed trust manifest → generates 256-bit random CEK → encrypts document via AES-256-GCM → for each recipient: ML-KEM-768 encapsulate → HKDF-SHA256 wrap CEK → commits `DOCUMENT_ENCRYPTED` block #2 to ledger → **destroys original plaintext PDF from vault**.
* **Observed Status:** **WORKING BUT DISCONNECTED**.
  * The form uses a hardcoded default `DOC-2026-001` stored in a global state string.
  * Once registered, there is no visual indicator showing the registered document status or hash before encryption.
  * If user forgets to register and clicks "Broadcast Encrypt", it fails with an ambiguous error.

### Journey 3: Recipient Controlled Decryption & Provenance Signing
* **START:** Logged in as `R002`. User navigates to "2. Recipient Decryption".
* **Intent:** Decrypt the authorized directive, generate a unique forensic marker, sign provenance, and download copy.
* **Current Action:** Sees target document ID (read from global `docId`), clicks "DECRYPT & GENERATE PROVENANCE RECORD".
* **Backend Flow:** `POST /api/decrypt` with `{ document_id }`.
* **Observed Status:** **CRITICAL BREAKAGE (P0)**.
  * Backend model [`DecryptRequest`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/models/schemas.py#L103-L109) mandates:
    ```python
    class DecryptRequest(StrictModel):
        document_id: str = IdStr
        passphrase: str = Field(..., min_length=1, max_length=1024)
    ```
  * Frontend [`App.jsx:L208-L212`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L208-L212) sends:
    ```javascript
    body: JSON.stringify({ document_id: docId })
    ```
  * FastAPI immediately rejects with `HTTP 422 Unprocessable Entity: missing field 'passphrase'`.
  * The user is blocked from ever completing decryption in the UI!
  * **Secondary Mockery:** The UI uses `setTimeout(..., 400)` delays to advance a fake 6-step progress bar before the API request completes.

### Journey 4: Forensic Leak Investigation
* **START:** Logged in as `INVESTIGATOR_01`. User navigates to "4. Leak Forensics".
* **Intent:** Upload an intercepted/leaked PDF, extract marker, verify chain, and attribute to the source officer.
* **Current Action:** Drags/drops or selects leaked PDF file, clicks "RUN FORENSIC ANALYSIS & LEDGER LOOKUP".
* **Backend Flow:** `POST /api/investigate` (multipart file) → extracts invisible marker via PyMuPDF (strict mode 3) → queries `sessions` table for token hash → compares uploaded document SHA-256 with `delivered_document_hash` → validates ML-DSA-44 signature → verifies block in ledger hash chain → verifies signer identity in trusted manifest against pinned authority anchor → returns full evidence dictionary.
* **Observed Status:** **WORKING**.
  * Correctly displays green/red status badge and all 10 granular check statuses (`watermark_found`, `document_hash_match`, `signature_valid`, etc.).
  * **UX Flaw:** Investigation results are ephemeral. If the investigator switches tabs or refreshes, the verdict is wiped. No history of past investigations (`/api/reports`) is displayed.

### Journey 5: Ledger Tamper Sandboxing & Auditing
* **START:** Logged in as `AUDITOR_01`. User navigates to "6. Tamper Sandbox".
* **Intent:** Intentionally modify a historical ledger block in SQLite to demonstrate mathematical detection.
* **Current Action:** Selects a block, clicks "Tamper Block #N", then clicks "Re-Audit Ledger Integrity".
* **Backend Flow:** `POST /api/ledger/tamper-test` (replaces canonical JSON with modified string) → calls `GET /api/ledger/verify` (iterates blocks 0..N, recalculates SHA-256 chain and ML-DSA signatures) → returns `{ chain_valid: false, broken_block_index: N, error_message: "Hash mismatch" }`.
* **Observed Status:** **WORKING**.
  * Effectively demonstrates post-quantum and blockchain tamper detection for defense evaluations.
  * **UX Flaw:** Available blocks are rendered as an unorganized row of wrapped buttons. If the ledger has 50 blocks, the UI breaks into an overflowing grid of red buttons.

---

## 7. Comprehensive Button & Action Audit

| Action Element | Code Location | Observed Action | Expected User Intent | Backend Endpoint | Resulting State | Status | Problem & Impact |
|---|---|---|---|---|---|---|---|
| **STATION Selector** | [`App.jsx:L468`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L468) | Triggers `window.prompt` | Authenticate station securely | `POST /api/auth/login` | Updates `authToken`, `activeIdentity` | **PARTIALLY WORKING** | Unmasked plaintext input; hardcoded list misses dynamically created principals. |
| **"Register Document"** | [`App.jsx:L684`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L684) | Submits form with file | Register PDF with authority | `POST /api/documents/register` | Document saved, block committed | **WORKING** | Requires pre-filled `docId`; no validation on file format prior to submission. |
| **"Broadcast Encrypt"** | [`App.jsx:L724`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L724) | Sends doc ID & recipient list | Encrypt document once | `POST /api/documents/encrypt` | Ciphertext saved, original destroyed | **WORKING** | One-shot operation; repeating causes 409 Conflict with poor UI explanation. |
| **"Switch to Officer"** | [`App.jsx:L618`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L618) | Calls `handleLogin` & changes tab | Switch active identity | `POST /api/auth/login` | Switches station | **WORKING** | Clutters operational overview; bypasses realistic station boundaries. |
| **"DECRYPT & GENERATE"** | [`App.jsx:L764`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L764) | Sends `{ document_id }` | Decrypt and sign copy | `POST /api/decrypt` | **HTTP 422 Error** | **BROKEN** | **P0 Blocker:** Fails to provide mandatory step-up passphrase required by backend. |
| **"Download Officer's PDF"** | [`App.jsx:L830`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L830) | Downloads file blob | Save marked PDF | `GET /api/sessions/{id}/download` | File downloaded, server file destroyed | **PARTIALLY WORKING** | Single-use download destroys server copy; second click fails with generic error. |
| **"RUN INVARIANCE AUDIT"** | [`App.jsx:L860`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L860) | Sends last 2 session IDs | Compare 150-DPI renders | `POST /api/forensics/invariance` | Invariance stats displayed | **PARTIALLY WORKING** | Hardcoded to pick last 2 sessions in memory; crashes if fewer than 2 exist. |
| **"RUN FORENSIC ANALYSIS"** | [`App.jsx:L930`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L930) | Uploads leaked PDF | Identify source recipient | `POST /api/investigate` | Verification card displayed | **WORKING** | Result lost on tab switch; no persistence or export capability. |
| **"Reset to Genesis"** | [`App.jsx:L1038`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1038) | Calls reset API | Clean demo state | `POST /api/ledger/reset` | Database cleared | **WORKING** | Uses native browser alert; dangerous action lacks two-step confirmation. |
| **"Run Audit"** | [`App.jsx:L1045`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1045) | Calls verify API | Verify hash chain | `GET /api/ledger/verify` | Updates audit status | **WORKING** | Output only shows binary PASS/FAIL in telemetry, no block-by-block trace. |
| **"Tamper Block #N"** | [`App.jsx:L1119`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1119) | Modifies SQLite block | Simulate adversary | `POST /api/ledger/tamper-test` | Block mutated in DB | **WORKING** | Cluttered UI when many blocks exist; native `confirm` dialog used. |
| **"Clear" Logs** | [`App.jsx:L1178`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L1178) | Empties React `logs` array | Clear log display | *None (Local state)* | Sidebar cleared | **UNCLEAR** | Gives false impression that audit logs were deleted; does not touch `/api/audit`. |

---

## 8. Backend, API & Data Integration Map

### 8.1 API Surface & Frontend Coverage Audit

```
Backend API Coverage: 48% Integrated (12 of 25 endpoints consumed)
[########################------------------------]
```

| Domain | Backend Endpoint | HTTP Method | Consumed in UI? | Integration Gap / Impact |
|---|---|---|---|---|
| **Auth** | `/api/auth/login` | POST | **Yes** | Uses unmasked `window.prompt`. |
| | `/api/auth/logout` | POST | **No** | No logout button; token simply abandoned on switch. |
| | `/api/auth/me` | GET | **No** | UI never validates token validity on mount. |
| | `/api/auth/change-passphrase` | POST | **No** | Key re-encryption under new passphrase impossible from UI. |
| **Lifecycle** | `/api/enroll` | POST | **No** | Personnel cannot self-enrol or redeem one-time codes in UI. |
| | `/api/keys/me` | GET | **No** | Officers cannot inspect their own PQC key IDs or status. |
| | `/api/keys/rotate` | POST | **No** | Key rotation workflow completely absent in UI. |
| **Recipients** | `/api/recipients` | GET | **Yes** | Rendered in dashboard table. |
| | `/api/recipients/create` | POST | **No** | Authority cannot provision new recipients via UI. |
| | `/api/recipients/create-investigator`| POST | **No** | Authority cannot provision investigators via UI. |
| **Documents** | `/api/documents` | GET | **Yes** | Fetched into state but **never rendered as an interactive list**! |
| | `/api/documents/register` | POST | **Yes** | Form available in Tab 2. |
| | `/api/documents/encrypt` | POST | **Yes** | Checkbox list available in Tab 2. |
| **Decryption**| `/api/decrypt` | POST | **Yes (Broken)**| Missing `passphrase` payload causing HTTP 422. |
| | `/api/sessions/{id}/download` | GET | **Yes** | Single-use download. |
| **Forensics** | `/api/investigate` | POST | **Yes** | Form available in Tab 4. |
| | `/api/reports` | GET | **No** | Investigation reports archive cannot be browsed. |
| | `/api/reports/{id}` | GET | **No** | Stored report verification cannot be inspected. |
| | `/api/forensics/invariance` | POST | **Yes** | Hardcoded session picking. |
| **Ledger** | `/api/ledger` | GET | **Yes** | Block dump in Tab 5. |
| | `/api/ledger/verify` | GET | **Yes** | Verify button in Tab 5 & 6. |
| | `/api/ledger/witness` | GET | **No** | External witness cosignature status invisible. |
| | `/api/ledger/checkpoint` | POST | **No** | Cannot sign and export ledger checkpoints in UI. |
| | `/api/ledger/bundle` | GET | **No** | Cannot export offline ledger bundle for air-gapped audit. |
| | `/api/ledger/cosignature` | POST | **No** | Cannot import witness cosignatures in UI. |
| | `/api/ledger/tamper-test` | POST | **Yes** | Buttons in Tab 6. |
| | `/api/ledger/reset` | POST | **Yes** | Reset button in Tab 5 & 6. |
| **Audit** | `/api/audit` | GET | **No** | True security audit trail is never loaded into UI! |
| **Trust** | `/api/trust/manifest` | GET | **No** | Signed trust manifest view is completely missing from UI. |
| | `/api/trust/manifest/export` | GET | **No** | Cannot export signed manifest package for air-gapped nodes. |
| | `/api/trust/import` | POST | **No** | Cannot import new signed trust packages from UI. |
| | `/api/trust/issue` | POST | **No** | Cannot re-issue manifest from local registry in UI. |
| | `/api/trust/pending` | GET | **No** | Authority cannot view keys awaiting attestation. |
| | `/api/trust/attest` | POST | **No** | Authority cannot confirm out-of-band fingerprints in UI. |
| | `/api/trust/revoke` | POST | **No** | Authority cannot revoke compromised officers in UI. |
| | `/api/trust/key-compromise` | POST | **No** | Cannot mark key retroactively compromised in UI. |

---

## 9. Authentication, Roles & Security Boundaries

### 9.1 Authentication Implementation Analysis
1. **Keystore-Backed Auth:** Authentication in this system is fundamentally cryptographic. Logging in means providing a passphrase that unlocks an encrypted keystore (`backend/data/keystore/<principal_id>.keystore.json`). The private keys are decrypted into memory, and a high-entropy random bearer token (32 bytes url-safe) is generated.
2. **Current Frontend Defect:**
   * **OBSERVED:** [`App.jsx:L64`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L64) executes `window.prompt(...)`.
   * **PROBLEM:** Standard browser `prompt` displays characters unmasked, does not allow pasting securely, halts the JS thread, and looks unprofessional for a defense system.
   * **RECOMMENDATION:** Build a modal/page authentication form with an HTML5 `<input type="password">`, explicit validation, and clear error messaging.
3. **Session Volatility:**
   * **OBSERVED:** `authToken` is stored solely in React component state (`useState(null)`).
   * **PROBLEM:** Any browser reload, back-forward navigation, or tab crash immediately wipes the token and returns the user to an unauthenticated dashboard.
   * **RECOMMENDATION:** Store the session token in `sessionStorage` (air-gapped single-tab session security) and execute `GET /api/auth/me` on startup to validate the token.

### 9.2 Role-Based Access Control (RBAC) Mismatch

```
SERVER-SIDE ENFORCEMENT (Strict)              CLIENT-SIDE VISIBILITY (Broken)
+------------------------------------+       +------------------------------------+
| AUTHORITY: Register, Encrypt, Trust|       | ALL USERS SEE ALL 6 TABS:          |
| RECIPIENT: Decrypt, Download       |  <--  | [Dashboard] [Sender] [Recipient]   |
| INVESTIGATOR: Investigate, Invar.  |  !=   | [Invariance] [Forensics] [Ledger]  |
| AUDITOR: Ledger, Tamper, Audit     |       | [Tamper Sandbox]                   |
+------------------------------------+       +------------------------------------+
```

* **OBSERVED:** All 6 navigation tabs are rendered for every user at all times.
* **PROBLEM:** A recipient officer who clicks "Broadcast Encrypt" receives an unhandled 403 Forbidden error in the log window. An investigator who clicks "Tamper Block" receives a 403 error. The UI fails to communicate permissions to the user.
* **RECOMMENDATION:** Implement role-based navigation filtering:
  * When logged in as `RECIPIENT`: Show only Assigned Directives, Decryption Terminal, and Personal Keys.
  * When logged in as `AUTHORITY`: Show Document Vault, Recipient Management, and Trust Anchor.
  * When logged in as `INVESTIGATOR`: Show Forensic Intake, Investigation Dossiers, and Invariance.
  * When logged in as `AUDITOR`: Show Ledger Explorer, Audit Trail, and Tamper Sandbox (if Demo mode active).

---

## 10. Application State & Edge-Case Audit

| Operational State | Current Implementation | Missing Handlers & Problems | Impact & Severity |
|---|---|---|---|
| **Initial Loading** | `loading` boolean state disables some buttons | No page-level loading indicators or skeleton screens; initial fetch has no spinners. | Medium (P2) |
| **Empty States** | Minimal fallback text in logs | If `documents` or `ledgerBlocks` are empty, empty tables/cards render broken borders or zero-height elements. | Medium (P2) |
| **Network Failure** | Caught in generic `catch (err)` | Appends string to `logs`; does not offer retry buttons or alert banners. | High (P1) |
| **Step-Up Authentication** | Completely missing in decryption | Backend requires keystore passphrase to sign decryption record; UI never prompts for it. | **Critical (P0)** |
| **401 Unauthorized / Expired** | No interceptor | If session TTL expires (default 1 hour), requests fail silently or log red text. No redirect to login. | High (P1) |
| **403 Forbidden** | Logs error text | User is not informed why their role was refused or who to contact. | Medium (P2) |
| **409 Conflict (Repeat Encrypt)**| Logs error text | Broadcast encryption is one-shot. Re-encrypting throws 409; UI does not explain why. | Medium (P2) |
| **410 Gone (Expired Download)** | Logs generic "Download denied" | Single-use file download destroys file; subsequent clicks fail without informing user file was destroyed. | High (P1) |
| **429 Too Many Attempts** | Backend locks account | UI does not show countdown timer when principal is locked out. | Medium (P2) |
| **Partial Data** | None | If trust manifest is unavailable, attribution returns `VERIFICATION_ERROR`; UI displays raw JSON error. | High (P1) |

---

## 11. Responsive & Cross-Device UX Audit

* **Desktop Display (>= 1280px):** 
  * Layout divides into an 8-column main area and a 4-column telemetry log.
  * **Problem:** Telemetry log height is fixed at `h-[750px]`, which overflows or underflows depending on browser vertical resolution.
* **Tablet Display (768px - 1024px):**
  * Top navigation tabs wrap awkwardly or require horizontal scrolling.
  * Two-column tables (NIST crypto matrix) cause horizontal document overflow.
* **Mobile Display (< 768px):**
  * **Critical Breakage:** The header telemetry badges (`ML-KEM-768`, `ML-DSA-44`, `LEDGER`) stack vertically, pushing the station switcher down.
  * Tab navigation becomes an unscrollable horizontal ribbon that cuts off tabs 4, 5, and 6.
  * Modals and cards lack mobile padding, causing buttons to touch screen edges.
  * The file upload dropzone is unusable on mobile touchscreens without specific mobile file picker styling.

---

## 12. Accessibility (a11y) Audit

1. **Semantic Structure:**
   * Uses non-semantic `<div onClick>` and button elements without accessible names or aria attributes.
   * `index.html` has title `<title>frontend</title>`, which is unacceptable for a sovereign naval system.
2. **Form Controls:**
   * File upload `<input type="file">` lacks associated `<label for="...">` associations.
   * Station switcher `<select>` has no `<label>` element, relying on adjacent unassociated `<span>STATION:</span>`.
3. **Contrast & Color Dependence:**
   * Relies entirely on red/green color cues (e.g. text-rose-400 vs text-emerald-400) without distinct icon or text-based state indicators for color-blind officers.
   * Muted text classes (`text-slate-500`, `text-slate-600`) fail WCAG 2.1 AA minimum contrast ratios (4.5:1) against dark backgrounds (`#070d19` and `#0a1329`).
4. **Keyboard Navigation & Focus Trapping:**
   * No `:focus-visible` ring outlines on navigation tabs or interactive buttons.
   * Tab switches do not shift DOM focus, making screen readers disoriented upon view transitions.

---

## 13. Technical Debt & Codebase Cleanup Audit

### 13.1 Dead Code & Unused Assets
* **OBSERVED:** [`frontend/src/App.css`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.css) contains 185 lines of legacy boilerplate styles from the default Vite starter (`.counter`, `.hero`, `.framework`, `.vite`, `#next-steps`).
* **PROBLEM:** Neither [`main.jsx`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/main.jsx) nor [`App.jsx`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx) imports `App.css`. It is 100% dead code sitting in the repository.
* **OBSERVED:** [`frontend/src/assets/hero.png`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/assets/hero.png), `react.svg`, and `vite.svg` exist in the directory but are never referenced in `App.jsx`.

### 13.2 Anti-Patterns & Fragilities in `App.jsx`
1. **Monolithic God Component:** 1,219 lines in a single component holding 18 distinct pieces of state. Any state change triggers a full re-render of the entire view.
2. **Mock / Fake Delays:**
   * [`App.jsx:L192-205`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L192-L205): Uses fake `setTimeout(r, 400)` calls to animate steps 1 through 5 before the network call even finishes. If the network call fails, the UI has already lied to the user that steps 1 to 5 succeeded.
3. **Hardcoded Mock Constants:**
   * Hardcoded initial state `useState('DOC-2026-001')`. If an authority registers a different document ID, all other tabs remain stuck on `DOC-2026-001` unless manually typed.
   * Hardcoded station selector list ([`App.jsx:L473-480`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L473-L480)) ignores principals created dynamically via backend scripts or API.
4. **Missing Router:**
   * No URL synchronization means users cannot bookmark, reload, or share deep links to specific documents or blocks.

---

## 14. Product-Level UX & Design Problems

### 14.1 Top UX Breakages

1. **"The Illusion of a Single Flow":**
   * Tabs are labelled: `1. Sender Broadcast` → `2. Recipient Decryption` → `3. Visual Invariance` → `4. Leak Forensics` → `5. Tamper-Evident Ledger` → `6. Tamper Sandbox`.
   * This confuses users by treating distinct military command roles (HQ Authority, Sea-Command Officer, Naval Forensics Investigator, System Auditor) as sequential steps on a single dashboard.
2. **Missing Document Selection in Decryption:**
   * In Tab 2, a recipient cannot pick from a list of documents issued to them. They must blindly trust that `docId` in memory matches what was encrypted.
3. **Download Blind Spot:**
   * The backend destroys the decrypted file immediately after one download. The UI provides zero explanation or advance warning, leading users to believe the system crashed when subsequent downloads fail with HTTP 410.
4. **Audit Trail Disconnect:**
   * The application has a dedicated append-only audit database table (`audit_events`) and API (`/api/audit`). The UI ignores this and presents a fragile local array of strings that disappears on page reload.

---

## 15. The Primary Product Loop

The core product loop of the SIH26237 system represents the complete lifecycle of a sovereign classified directive from issuance to forensic leak attribution:

```
[1. AUTHORITY DIRECTIVE ENTRANCE]
   │  Authority registers PDF -> Original SHA-256 bound -> DOCUMENT_REGISTERED block signed
   ▼
[2. BROADCAST KEY ENCAPSULATION]
   │  Authority selects officers -> ML-KEM-768 encapsulation -> DOCUMENT_ENCRYPTED block
   │  Plaintext destroyed from vault -> Broadcast package stored
   ▼
[3. RECIPIENT AIR-GAPPED DECRYPTION]
   │  Officer authenticates -> Enters step-up passphrase -> KEM decapsulation -> CEK unwrapped
   │  256-bit opaque marker injected (Mode 3) -> Visual invariance verified (0 diff samples)
   │  Delivered SHA-256 bound -> ML-DSA-44 signature -> DOCUMENT_DECRYPTED block committed
   ▼
[4. SECURE DISPATCH & DISPOSAL]
   │  Officer downloads delivered PDF once -> Server delivery copy destroyed
   ▼
[5. LEAK DETECTION & FORENSIC INTAKE]
   │  Leaked document recovered -> Intercepted file uploaded to Forensic Portal
   ▼
[6. 10-POINT FORENSIC ATTRIBUTION ENGINE]
   │  Marker extracted -> Exact delivered hash matched -> Ledger session located
   │  Recipient signature verified -> Ledger hash chain verified -> Trust anchor validated
   ▼
[7. VERDICT & DOSSIER GENERATION]
   │  Attribution confirmed (Recipient named) OR Fail-closed refusal (No suspect named)
   │  Signed investigation report committed to ledger
   ▼
[8. AUDITOR CONTINUITY & WITNESSING]
   │  Auditor verifies ledger integrity -> Head anchor verified -> External witness cosigned
```

---

## 16. Recommended Product & Navigation Architecture

### 16.1 Proposed Navigation Model

* **Global Persistent Topbar:**
  * System Badge: `MINISTRY OF DEFENCE // INDIAN NAVY (WESEE)`
  * Security State: `OFFLINE AIR-GAPPED // PQC OPERATIONAL`
  * System Telemetry: KEM (FIPS 203), DSA (FIPS 204), Ledger Head Index
  * Station Status: Active Officer Name, Principal ID, Role Badge
  * Session Menu: Change Passphrase, Key Lifecycle, Logout
* **Role-Based Primary Navigation (Sidebar or Sub-header):**
  * **Authority Portal (`WESEE_HQ`):**
    * *Directives Vault:* Intake, Registration, Broadcast Encryption
    * *Personnel Registry:* Recipient Enrolment, Key Fingerprint Attestation
    * *Trust Anchors:* Monotonic Manifests, Pin Status, Revocation
  * **Recipient Terminal (`R001`, `R002`, `R003`):**
    * *Directive Inbox:* Authorized incoming packages
    * *Decryption Desk:* Step-up passphrase confirmation, Provenance signing
    * *Key Card:* Station public keys, rotation triggers
  * **Forensics Lab (`INVESTIGATOR_01`):**
    * *Leak Investigation:* Document intake, 10-point check suite
    * *Invariance Inspector:* Visual pixel comparison suite
    * *Evidence Dossiers:* Stored investigation reports (`/api/reports`)
  * **Audit & Continuity (`AUDITOR_01`):**
    * *Ledger Chain Explorer:* Block visualizer, head anchor verify
    * *Security Audit Trail:* Live stream from `/api/audit`
    * *Witness & Checkpoints:* Cosignature import/export
    * *Tamper Sandbox:* Adversarial simulation controls (Demo Mode)

---

## 17. Required Design System Components

To prepare for Phase 2 without writing premature visual code, we specify the required atomic component contracts:

1. **StationAuthModal:** Secure modal dialog with password-masked input, station selector, lockout countdown timer, and enter key submission.
2. **StepUpPromptDialog:** High-security confirmation modal that requests the officer's passphrase before executing signing/decryption operations.
3. **RoleGatedRoute:** Navigation wrapper that inspects `session.role` and renders an access-denied fallback or redirects unauthorized roles.
4. **VerificationBadgeGrid:** 10-item granular status component mapping to `VerificationEvidence` (`watermark_found`, `document_hash_match`, etc.) with distinct icons, tooltip descriptions, and color-independent badges.
5. **LedgerBlockViewer:** Expandable card component displaying block header, previous hash, current block hash, signer identity, and parsed canonical JSON payload.
6. **DirectiveCard / Table:** Interactive list displaying document ID, filename, classification badge, owner, encryption status, and contextual actions ("Encrypt", "Decrypt", "Inspect").
7. **SingleUseDownloadButton:** Action button with countdown warning, confirmation prompt, and automatic post-click disabled state with "File Destroyed on Server" notice.
8. **AuditLogTable:** Real-time paginated table consuming `/api/audit` with filterable columns for timestamp, event type, principal, outcome (`SUCCESS`, `DENIED`, `FAILED`), and metadata details.
9. **TrustManifestCard:** Inspector displaying monotonic version, manifest SHA-256, pinned authority key fingerprint, and principal attestation table.
10. **Toast / Banner Notification System:** Global alert system replacing browser `alert` and console logs for critical feedback (HTTP 409 Conflict, HTTP 422 Validation, Network Error).

---

## 18. Prioritized Implementation Roadmap

### Phase 2 Implementation Schedule

#### P0 — Critical Architectural Fixes (Day 1)
* **P0.1: Fix Decryption Step-Up Passphrase Payload:**
  * **Current:** [`App.jsx:L208-L212`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx#L208-L212) sends `{ document_id }`.
  * **Problem:** Crashes with HTTP 422 Unprocessable Entity.
  * **Proposed:** Implement `StepUpPromptDialog` to collect the recipient's passphrase and transmit `{ document_id, passphrase }` in accordance with [`schemas.py:L103`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/models/schemas.py#L103).
  * **Reason:** Restores primary functional capability of the product.
* **P0.2: Remove Native Browser Dialogs:**
  * **Current:** `window.prompt`, `window.alert`, `window.confirm`.
  * **Problem:** Unmasked passwords, thread blocking, terrible UX.
  * **Proposed:** Replace with React modal dialogs and inline error banners.
  * **Reason:** Baseline security and usability requirement for defense systems.
* **P0.3: Update E2E Test Suite:**
  * **Current:** [`tests/test_e2e_workflow.py:L71`](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_e2e_workflow.py#L71) calls `/api/decrypt` without `passphrase`.
  * **Problem:** E2E test fails with AssertionError.
  * **Proposed:** Update `test_e2e_workflow.py` to pass the recipient's passphrase via `testenv.passphrase(rid)`.
  * **Reason:** Ensures automated regression suite passes.

#### P1 — High Priority Product Restructuring (Day 2)
* **P1.1: Component Decomposition & Client Routing:**
  * Break monolithic `App.jsx` into modular components under `src/components/` and `src/views/`.
  * Introduce standard routing (`/login`, `/authority`, `/recipient`, `/investigator`, `/audit`).
* **P1.2: Role-Based Navigation & Session Persistence:**
  * Store auth token in `sessionStorage`; persist active session across page reloads.
  * Filter navigation menus dynamically based on authenticated role.
* **P1.3: Interactive Directive Inbox for Recipients:**
  * Replace static `docId` text input with an interactive table consuming `GET /api/documents` showing actual authorized directives.
* **P1.4: One-Time Download UX Safeguard:**
  * Add clear visual cues and modal confirmation explaining server-side file destruction upon download.

#### P2 — Medium Priority Feature Integrations (Day 3)
* **P2.1: Trust Anchor & Manifest Management View:**
  * Integrate `GET /api/trust/manifest`, `/api/trust/pending`, `/api/trust/attest`, and `/api/trust/revoke` into an Authority Trust Desk.
* **P2.2: Cryptographic Audit Trail View:**
  * Replace ephemeral React logs with a real audit log view consuming `GET /api/audit`.
  * **P2.3: Forensic Reports History:**
  * Add historical reports archive consuming `GET /api/reports` and `GET /api/reports/{id}`.
* **P2.4: Clean Dead Code & Assets:**
  * Delete unreferenced `App.css` and unreferenced boilerplate images.

#### P3 — Low Priority Polish & Enhancements (Day 4)
* **P3.1: Responsive Layout Polish:**
  * Optimize mobile and tablet breakpoints.
* **P3.2: Accessibility (WCAG 2.1 AA) Polish:**
  * Ensure high-contrast ratios, focus rings, and screen-reader tags.
* **P3.3: Ledger Bundle Export & Witness UI:**
  * Add buttons to export offline ledger packages and import external witness cosignatures.

---

## 19. Open Questions & Unknowns

1. **Air-Gapped Node Synchronization Method:**
   * *Status:* `UNKNOWN — requires confirmation`.
   * *Detail:* Backend supports exporting signed manifests and ledger bundles to removable media, but does the operational environment use USB drives, read-only optical discs, or an isolated local naval LAN?
2. **Hardware Security Module (HSM) Roadmap:**
   * *Status:* `UNKNOWN — requires confirmation`.
   * *Detail:* The documentation clearly states that software keystores are an air-gapped prototype implementation. Should Phase 2 UI account for future PKCS#11 / smartcard hardware token unlock prompts?
3. **Print-and-Scan Watermarking:**
   * *Status:* Documented in `SECURITY.md` as explicitly out of scope for the current prototype (exact-hash matching fails if printed and scanned). UI must explicitly communicate this limitation to avoid misleading military investigators during demonstrations.

---

### Audit Phase Conclusion
The architecture, data contracts, security mechanics, and user flows of SIH26237 have been fully audited, traced, and documented. **Phase 1 is complete. No UI code has been modified. Awaiting user instruction before initiating Phase 2.**
