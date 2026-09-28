# Architectural & Engineering Decisions

> **Authoritative Decision Record**  
> Tracks architectural choices, engineering standards, and scope boundaries established in the codebase.  
> *Rules:* Reasons must be backed by repository evidence; where evidence is absent, state `Reason: UNKNOWN`. Never fabricate historical rationale.

---

## Decision Register

### DEC-001: Offline / Air-Gapped Architecture (Zero Runtime Network Calls)
- **ID:** `DEC-001`
- **Decision:** The entire application must operate strictly offline on an air-gapped local host, with zero outbound network calls, cloud KMS, or external blockchain nodes at runtime.
- **Reason:** Naval tactical and defence documents operate in classified, air-gapped operational environments (WESEE / Indian Navy). Network access introduces severe operational risk and external attack surfaces.
- **Evidence:** [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md#L101-L108), [docs/GOVERNMENT_ECOSYSTEM.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/GOVERNMENT_ECOSYSTEM.md#L7-L14), [tests/test_trust_integration.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_trust_integration.py#L320-L358) (tests whole workflow with socket connections explicitly blocked).
- **Affected Components:** Entire backend, API handlers, trust subsystem, audit subsystem.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** No (core operational requirement).

---

### DEC-002: ML-KEM-768 Restricted to Key Establishment
- **ID:** `DEC-002`
- **Decision:** ML-KEM-768 (FIPS 203) is used solely to encapsulate/decapsulate a 32-byte shared secret per recipient. It never touches or encrypts the document plaintext directly.
- **Reason:** Asymmetric lattice-based algorithms (KEM) are computationally heavy, have substantial ciphertext overhead (1,088 bytes per encapsulation), and are designed for key exchange, not bulk data encryption. Bulk document encryption requires symmetric ciphers.
- **Evidence:** [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md#L27-L38), [backend/app/api/encryption.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/api/encryption.py#L40-L75), [implementation_plan_v2.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/implementation_plan_v2.md#L144-L182).
- **Affected Components:** `backend/app/crypto/pqc_kem.py`, `backend/app/api/encryption.py`, `backend/app/api/decryption.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** No.

---

### DEC-003: Hybrid Cryptographic Key Wrapping Pipeline
- **ID:** `DEC-003`
- **Decision:** The cryptographic hierarchy is:
  `CEK (AES-256)` -> `ML-KEM-768.Encaps(ek_r) -> ss` -> `HKDF-SHA256(ss, info="...|doc|recipient") -> KEK` -> `AES-256-GCM(KEK, CEK)` -> `AES-256-GCM(CEK, document)`.
- **Reason:** Guarantees cryptographic context separation: a wrapped CEK cannot be transplanted or decrypted for a different document ID or recipient ID. AES-256-GCM provides authenticated encryption with associated data (AAD).
- **Evidence:** [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md#L27-L48), [backend/app/crypto/symmetric.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/crypto/symmetric.py), [tests/test_crypto.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_crypto.py#L42-L57).
- **Affected Components:** `backend/app/crypto/kdf.py`, `backend/app/crypto/symmetric.py`, `backend/app/api/encryption.py`, `backend/app/api/decryption.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** No.

---

### DEC-004: Post-Quantum Digital Signatures (ML-DSA-44)
- **ID:** `DEC-004`
- **Decision:** Use ML-DSA-44 (FIPS 204) via pure-Python `dilithium-py` for signing canonical decryption records, registration events, broadcast encryption blocks, and trust manifests.
- **Reason:** Provides quantum-resistant authentication and non-repudiation in alignment with TEC 910018:2025 and future national quantum security standards.
- **Evidence:** [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L100), [backend/app/crypto/pqc_dsa.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/crypto/pqc_dsa.py), [bom/cbom.cdx.json](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/bom/cbom.cdx.json).
- **Affected Components:** `backend/app/crypto/pqc_dsa.py`, `backend/app/ledger/blockchain.py`, `backend/app/trust.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** Parameters could be upgraded to ML-DSA-65/87 or hybrid in production, but ML-DSA-44 is the standard prototype choice.

---

### DEC-005: Watermark Token Must Be Opaque CSPRNG Random
- **ID:** `DEC-005`
- **Decision:** The watermark embedded in a PDF must be an opaque 256-bit random hex token prefixed with `WM-` (`WM-[0-9a-f]{64}`). It must never contain the recipient's name, ID, rank, or department directly.
- **Reason:** Prevents leak-analysis attacks where an adversary inspects or removes specific text strings corresponding to suspect names. Attribution is achieved solely through the tamper-evident ledger lookup. Complies with DPDP Act 2023 data minimization.
- **Evidence:** [README.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/README.md#L83-L91), [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md#L42), [backend/app/watermark/embed.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/watermark/embed.py).
- **Affected Components:** `backend/app/watermark/embed.py`, `backend/app/watermark/extract.py`, `backend/app/api/decryption.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** No.

---

### DEC-006: Non-Rendering PDF Text (Render Mode 3) for Visual Invariance
- **ID:** `DEC-006`
- **Decision:** Watermarks are injected as text with PDF text rendering mode 3 (neither fill nor stroke) on every page, plus PDF document metadata.
- **Reason:** Guarantees 0-pixel visual deviation when rendered (measured at 150 DPI with PyMuPDF) so the reading experience and visual presentation are unchanged for authorized officers.
- **Evidence:** [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md#L43), [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L106), [backend/app/watermark/embed.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/watermark/embed.py), [tests/test_watermark.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_watermark.py).
- **Affected Components:** `backend/app/watermark/embed.py`, `backend/app/watermark/validate.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** Production direction notes layered marking (e.g. robust steganography or print-and-scan resilience) as future work.

---

### DEC-007: Exact-Hash Attribution Requirement
- **ID:** `DEC-007`
- **Decision:** A leaked document is verified ONLY if its SHA-256 hash matches the recorded `delivered_document_hash` in the signed decryption session. A watermark match alone NEVER attributes.
- **Reason:** A forensic attribution marker can be extracted, forged, or transplanted into a modified document. Only the cryptographic binding of marker + exact delivered file hash + recipient signature + full ledger chain constitutes undeniable forensic evidence.
- **Evidence:** [README.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/README.md#L116), [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L104), [backend/app/forensics.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/forensics.py).
- **Affected Components:** `backend/app/forensics.py`, `backend/app/api/investigation.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** No.

---

### DEC-008: Fail-Closed Attribution Rule
- **ID:** `DEC-008`
- **Decision:** If any of the 10 forensic checks fail, or if an internal exception occurs, the system must return `UNVERIFIED` (or `VERIFICATION_ERROR`) and populate zero suspect names (`recipient_id: null`).
- **Reason:** In a military/defence context, naming an innocent officer based on incomplete or tampered forensic evidence is unacceptable. Verification must fail safe/closed.
- **Evidence:** [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L56-L70), [backend/app/forensics.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/forensics.py), [tests/test_security_investigation.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_security_investigation.py).
- **Affected Components:** `backend/app/forensics.py`, `backend/app/api/investigation.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** No.

---

### DEC-009: SQLite Hash-Chained Ledger with Head Anchor
- **ID:** `DEC-009`
- **Decision:** Provenance ledger is stored in SQLite table `ledger_blocks` with SHA-256 hash chaining, SQLite append-only triggers, and an out-of-database external anchor file `backend/data/ledger_head.json`.
- **Reason:** Provides tamper-evidence against database modification, row insertion, deletion, reordering, and truncation without requiring complex distributed consensus for single-node air-gapped prototype.
- **Evidence:** [docs/DATABASE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/DATABASE.md#L25-L40), [backend/app/ledger/blockchain.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/ledger/blockchain.py), [tests/test_security_ledger.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_security_ledger.py).
- **Affected Components:** `backend/app/ledger/*`, `backend/app/database/connection.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** Production roadmap suggests multi-node replicated ledger with witness checkpoints.

---

### DEC-010: Pinned Authority Key & Monotonic Signed Trust Manifests
- **ID:** `DEC-010`
- **Decision:** The issuing authority's ML-DSA public key fingerprint is stored outside the database at `trust_anchor/authority.pin`. Identity rosters are ingested only as signed manifests with strictly monotonic version numbers. Revocation is permanent.
- **Reason:** Prevents database administrators or local attackers from substituting public keys in the `recipients` table to launder forged signatures.
- **Evidence:** [docs/ARCHITECTURE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/ARCHITECTURE.md#L71-L88), [backend/app/trust.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/trust.py), [tests/test_trust_integration.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_trust_integration.py).
- **Affected Components:** `backend/app/trust.py`, `backend/app/api/trust.py`, `scripts/provision_identities.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** Production direction recommends storing the pin in hardware/read-only media.

---

### DEC-011: Local Encrypted Software Keystore (scrypt + AES-256-GCM)
- **ID:** `DEC-011`
- **Decision:** Private keys are stored in encrypted JSON files (`backend/data/keystore/<id>.keystore.json`) using scrypt (N=32768, r=8, p=1) and AES-256-GCM with header AAD. No plaintext keys on disk.
- **Reason:** Replaces legacy plaintext `.key.json` files with secure at-rest protection meeting CERT-In government entity guideline 6.2.3 intent for offline prototype.
- **Evidence:** [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md#L27-L38), [backend/app/crypto/keystore.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/crypto/keystore.py), [tests/test_security_keystore.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/tests/test_security_keystore.py).
- **Affected Components:** `backend/app/crypto/keystore.py`, `backend/app/auth.py`.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** Hardware security modules (PKCS#11 / HSM) are the required production gate.

---

### DEC-012: Rejection of Online Government APIs
- **ID:** `DEC-012`
- **Decision:** Explicitly evaluated and rejected API Setu, data.gov.in, DigiLocker, online CCA/India PKI CRL/OCSP, and live NIC NTP. Adopted only offline-compatible standards: CycloneDX SBOM/CBOM (`bom/`), MHA NISPG classification vocabulary, and CERT-In logging requirements.
- **Reason:** The core attribution problem is cryptographic and provenance-based, not data-dependent. Online APIs require Internet access, legal onboarding, API keys, and introduce availability and data leakage risks incompatible with air-gapped naval operations.
- **Evidence:** [docs/GOVERNMENT_ECOSYSTEM.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/GOVERNMENT_ECOSYSTEM.md#L15-L31), [docs/PRD.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/PRD.md#L39-L49).
- **Affected Components:** Architecture policy, dependency manifest, operational procedures.
- **Status:** `ACTIVE / ENFORCED`
- **Can Be Revisited:** No.
