# SIH26237 — Project Brain Index

> **Primary Navigation Layer for AI Agents & Engineers**  
> This file is the top-level index for the repository. It does not repeat full technical specifications; it points directly to the authoritative sources of truth.

---

## 1. Project Identity

| Attribute | Verified Value | Evidence |
|---|---|---|
| **Project Code** | `SIH26237` | [README.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/README.md) |
| **Organization** | Ministry of Defence (MoD) | [docs/PRD.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/PRD.md) |
| **Department** | Indian Navy — WESEE (Weapons and Electronics Systems Engineering Establishment) | [docs/PRD.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/PRD.md) |
| **Theme** | Blockchain & Cybersecurity | [docs/PRD.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/PRD.md) |
| **Core Mission** | Sovereign offline forensic attribution system for broadcast-encrypted documents | [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md) |
| **Operational Environment** | Air-gapped / offline local infrastructure (zero network dependencies at runtime) | [tests/test_trust_integration.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_trust_integration.py) |

---

## 2. Core Problem & Solution Principle

- **Problem:** Sensitive PDFs are broadcast-encrypted (encrypted once, decrypted by multiple authorized recipients). Traditionally, every decrypted copy is visually and digitally identical. If a copy leaks, all authorized recipients are equally plausible suspects, and pre-encryption watermarking is useless.
- **Solution:** At the exact moment of decryption, generate a unique random 256-bit opaque forensic marker (`WM-<64hex>`), embed it into the PDF invisibly (PDF text render mode 3 + metadata), bind the exact delivered file SHA-256 into a canonical record signed by the recipient's post-quantum key (ML-DSA-44), and append it to an offline tamper-evident hash-chained ledger.
- **Attribution Rule:** On upload of a leaked file, attribute **only** if all 10 independent checks pass (marker found & valid, session match, exact document hash, record consistency, ledger record, ML-DSA signature, full hash-chain integrity, document registration & encryption provenance, and identity trust under pinned authority manifest). Verification **fails closed**: any anomaly returns `UNVERIFIED` or `VERIFICATION_ERROR` with zero named suspects.

---

## 3. Evidence Classification Standard

When recording or evaluating any system claim, agents must use these exact states:

- `VERIFIED`: Directly confirmed from repository code, configuration, or passing tests.
- `DOCUMENTED`: Stated in documentation but not independently verified in active code.
- `INFERRED`: Reasonable engineering interpretation based on evidence, but not explicitly confirmed.
- `UNKNOWN`: Cannot be established from the repository.
- `CONFLICT`: Two or more repository sources (e.g. code vs docs or tests vs schemas) disagree.

---

## 4. Authoritative Document Map

| Domain | Authoritative Document | Role & Scope |
|---|---|---|
| **System Navigation** | [PROJECT_BRAIN.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/PROJECT_BRAIN.md) | Top-level map and index (this document) |
| **Current Reality** | [CURRENT_STATE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CURRENT_STATE.md) | Verified vs partial vs broken state snapshot |
| **Engineering Tasks** | [TASKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/TASKS.md) | Atomic, actionable tasks for future work |
| **Architecture Decisions** | [DECISIONS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/DECISIONS.md) | Recorded architectural decisions and justifications |
| **Risk Register** | [RISKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/RISKS.md) | Verified and suspected risks with severity and mitigations |
| **Change History** | [CHANGELOG.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CHANGELOG.md) | Log of brain modifications and engineering updates |
| **System Architecture** | [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md) | Cryptographic pipeline, trust boundaries, offline deployment |
| **Security & Permissions** | [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md) | Role matrix, keystore specification, fail-closed rules, agent prohibitions |
| **HTTP API Surface** | [docs/API.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/API.md) | Request/response contracts, status codes, error models |
| **Database & Schema** | [docs/DATABASE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/DATABASE.md) | SQLite schema v3, append-only triggers, canonical records |
| **Government Context** | [docs/GOVERNMENT_ECOSYSTEM.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/GOVERNMENT_ECOSYSTEM.md) | Evaluation of Indian government frameworks (CERT-In, NISPG, TEC) |
| **Requirements & Scope** | [docs/PRD.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/PRD.md) | Functional/non-functional requirements, honest scope limits |
| **Agent Invariants** | [AGENTS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/AGENTS.md) | Mandatory coding rules, security prohibitions, verification steps |

---

## 5. Technology Stack Quick Reference

- **Backend:** Python 3.12+, FastAPI, Uvicorn (`backend/app/main.py`)
- **Crypto:** ML-KEM-768 (`mlkem`), ML-DSA-44 (`dilithium-py`), AES-256-GCM / HKDF / scrypt (`cryptography`)
- **Document Engine:** PyMuPDF (`pymupdf`)
- **Database:** SQLite 3 with WAL and custom append-only triggers (`backend/data/sih26237.sqlite`)
- **Frontend:** React 19, Vite 8, Tailwind CSS 4, Lucide React (`frontend/src/App.jsx`)
- **Bills of Material:** CycloneDX 1.6 SBOM + CBOM (`bom/cbom.cdx.json`, `bom/sbom.cdx.json`, `scripts/generate_bom.py`)
