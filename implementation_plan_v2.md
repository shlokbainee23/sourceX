# SIH26237 — Implementation Plan

> **Historical planning document.** It describes intentions, some of which differ from the
> implementation. The authoritative, code-verified descriptions are in `docs/ARCHITECTURE.md`,
> `docs/SECURITY.md`, `docs/API.md` and `docs/DATABASE.md`.
## Sovereign Offline Forensic Attribution System for Broadcast-Encrypted Documents

---

## 1. Problem Statement

**Organization:** Ministry of Defence  
**Department:** Indian Navy — WESEE  
**Category:** Software  
**Theme:** Blockchain & Cybersecurity  
**Problem Statement:** SIH26237

### Core Problem

A sensitive document may be broadcast-encrypted and distributed to multiple authorized recipients. Although each recipient can independently decrypt the same plaintext, the resulting copies are visually identical.

If one copy is later leaked, there is no reliable way to determine which authorized recipient produced the leaked copy.

### Required Outcome

The proposed system creates a unique, recipient- and session-specific forensic watermark at decryption time and records the decryption event in an offline tamper-evident ledger.

The investigation workflow is:

```text
Encrypted Document
       |
       v
Recipient Decryption Session
       |
       +--> Unique opaque watermark token
       |
       +--> Signed decryption record
       |
       v
Offline Append-Only Ledger
       |
       v
Leaked Document
       |
       v
Watermark Extraction
       |
       v
Ledger Lookup
       |
       v
Signature Verification
       |
       v
Ledger Integrity Verification
       |
       v
Verifiable Recipient + Session Attribution
```

---

# 2. Solution Summary

The prototype implements an **offline, air-gapped forensic attribution system** for confidential documents.

For every authorized decryption:

1. The recipient establishes a local post-quantum cryptographic identity.
2. The recipient decrypts the document through a controlled decryption session.
3. The system generates a cryptographically random watermark token.
4. The token is embedded into the decrypted document using a controlled non-rendering PDF watermark mechanism.
5. A canonical decryption record is generated.
6. The recipient signs the record using ML-DSA.
7. The signed record is committed to an append-only hash-chained local ledger.
8. If a document is leaked, an investigator extracts the watermark token.
9. The token is matched against the ledger.
10. The signature, record hash, document hash, and ledger chain are independently verified.
11. The system produces an attribution result showing the registered recipient and decryption session associated with the watermark.

### Important Security Principle

The watermark should contain an **opaque random cryptographic token**, not the recipient's name or recipient ID directly.

Example:

```text
Watermark Token:
WM-9f83...<256-bit random token>

Ledger:
WM token
   -> Document ID
   -> Recipient ID
   -> Session ID
   -> Timestamp
   -> Document hash
   -> Signature
```

This prevents the watermark itself from exposing recipient identity.

---

# 3. Design Goals

### Primary Goals

- Offline operation
- Air-gapped deployment
- No cloud KMS
- No external AI/API dependency at runtime
- Post-quantum key establishment
- Post-quantum digital signatures
- Recipient-specific decryption records
- Session-specific forensic watermarking
- Tamper-evident audit trail
- Leak investigation workflow
- Cryptographic verification
- Demonstrable end-to-end prototype within 48 hours

### Secondary Goals

- Clean tactical/cybersecurity interface
- Multiple recipient simulation
- Visual proof that recipient copies look identical
- Automated verification tests
- Clear SIH jury demonstration

### Non-Goals for the 48-Hour MVP

- Production-grade watermark robustness against every transformation
- Real naval deployment
- Hardware security modules
- Hardware-backed smartcards
- Full distributed Byzantine consensus
- Cloud deployment
- Internet-connected AI services
- Legal determination of guilt

---

# 4. Important Cryptographic Correction

## ML-KEM does not directly encrypt an AES key

The implementation must **not** describe ML-KEM as directly encapsulating or encrypting an arbitrary AES CEK.

ML-KEM establishes a shared secret between the sender and recipient.

Correct hybrid encryption flow:

```text
                    RANDOM AES-256-GCM KEY
                              |
                              v
                     Encrypt Document
                              |
                              v
                     Ciphertext + Tag
                              |
        ------------------------------------------
        |                    |                   |
        v                    v                   v
   Recipient R001       Recipient R002      Recipient R003
        |                    |                   |
        v                    v                   v
 ML-KEM Encapsulation  ML-KEM Encapsulation ML-KEM Encapsulation
        |                    |                   |
        v                    v                   v
   Shared Secret        Shared Secret        Shared Secret
        |                    |                   |
        v                    v                   v
       KDF                  KDF                 KDF
        |                    |                   |
        v                    v                   v
 CEK-wrapping key      CEK-wrapping key     CEK-wrapping key
        |                    |                   |
        +-----------> Wrapped CEK per recipient
```

### Sender

1. Generate random AES-256-GCM content-encryption key (CEK).
2. Encrypt the document using AES-256-GCM.
3. For each authorized recipient:
   - obtain recipient ML-KEM public key;
   - perform ML-KEM encapsulation;
   - derive a wrapping key from the ML-KEM shared secret using a suitable KDF;
   - use the derived key to protect/wrap the AES CEK.
4. Store the recipient-specific encapsulation/ciphertext metadata.

### Recipient

1. Use recipient ML-KEM private key to decapsulate.
2. Recreate the same shared secret.
3. Derive the same CEK-wrapping key.
4. Unwrap/recover the AES CEK.
5. Decrypt the document using AES-256-GCM.
6. Enter the controlled watermarking session.

---

# 5. Post-Quantum Cryptography

## 5.1 ML-KEM

Use:

**ML-KEM-768 — FIPS 203**

Purpose:

- Post-quantum key establishment
- Establish a shared secret between sender and recipient
- Protect the AES CEK through a derived wrapping key

The implementation must use a mature, locally installed cryptographic library with actual ML-KEM support.

Do not implement ML-KEM manually.

---

## 5.2 ML-DSA

Use:

**ML-DSA-44 — FIPS 204**

Purpose:

- Sign the canonical decryption record
- Bind the record to the recipient's private signing key
- Allow an investigator to verify that the record was signed by the registered recipient key

The system must keep the private signing key local to the recipient identity.

Private keys must never be sent to the backend as plaintext.

---

## 5.3 Symmetric Encryption

Use:

**AES-256-GCM**

Purpose:

- Encrypt the actual document content
- Provide confidentiality and authenticated encryption

Generate a fresh random nonce/IV for each encryption operation according to the selected cryptographic library's requirements.

---

## 5.4 Hashing

Use:

**SHA-256**

Purpose:

- Document integrity hash
- Ledger block hashing
- Previous-block references
- Record integrity
- Investigation verification

---

# 6. Key Management for MVP

The prototype should use a local encrypted keystore.

### Recipient Identity Contains

```text
Recipient ID
ML-KEM public key
ML-KEM private key
ML-DSA public key
ML-DSA private key
Key metadata
Creation timestamp
Status
```

### MVP Protection

- Store private keys locally.
- Never expose private keys through normal API responses.
- Protect local keystore using an encryption mechanism supported by the selected library.
- Apply appropriate file permissions.
- Keep the implementation simple enough to complete within 48 hours.

### Production Direction

A production system should consider:

- hardware-backed key storage;
- secure smartcards;
- HSM-backed keys;
- secure enclave mechanisms;
- institutional key lifecycle management.

These are future architecture items, not required for the 48-hour prototype.

---

# 7. Document Encryption Architecture

## 7.1 Registration

Sender registers:

```text
Document ID
Document Name
Document Type
Original SHA-256
Classification / metadata
Creation Timestamp
```

Example:

```text
DOC-001
operation_brief.pdf
SHA256: abc123...
```

---

## 7.2 Encryption

Generate:

```text
AES-256 CEK
AES-GCM nonce
```

Encrypt:

```text
Plain Document
      |
      v
AES-256-GCM
      |
      v
Ciphertext + Authentication Tag
```

Then create a recipient-specific key-protection package:

```text
Recipient ID
ML-KEM ciphertext
Derived CEK-wrapping metadata
Wrapped CEK
```

The same document ciphertext can therefore be authorized for multiple recipients while each recipient has a separate ML-KEM-based key-establishment path.

---

# 8. Recipient Decryption Workflow

For each recipient:

```text
Login / Identity Selection
          |
          v
Load Local PQC Identity
          |
          v
Receive Encrypted Document
          |
          v
ML-KEM Decapsulation
          |
          v
KDF
          |
          v
Recover AES CEK
          |
          v
AES-256-GCM Decryption
          |
          v
Create Decryption Session
          |
          v
Generate Watermark Token
          |
          v
Embed Watermark
          |
          v
Generate Canonical Record
          |
          v
ML-DSA Signature
          |
          v
Commit to Offline Ledger
          |
          v
Return Watermarked Document
```

---

# 9. Decryption Session

Every successful decryption receives a unique session.

Example:

```text
Session ID:
SES-20260926-0001

Recipient:
R001

Document:
DOC-001

Timestamp:
2026-09-26T18:30:15Z

Watermark Token:
random 256-bit token
```

### Session Properties

The session must be unique even if:

- the same recipient decrypts the same document twice;
- multiple recipients decrypt the same document;
- the same recipient downloads multiple copies.

---

# 10. Forensic Watermark Design

## 10.1 Prototype Approach

For the 48-hour prototype, use a controlled PDF watermark mechanism that does not intentionally alter visible document content.

Possible implementation:

### Layer 1 — Non-rendering PDF content

Use PDF content structures that do not render visibly.

### Layer 2 — Embedded forensic metadata/object

Store the opaque watermark token in a dedicated forensic object/metadata structure.

### Important Limitation

The metadata/object layer alone is **not** a robust forensic watermark because PDF rewriting tools can remove or reconstruct document objects.

Therefore:

> The prototype watermark is designed to demonstrate controlled decryption-time attribution, not universal resistance to arbitrary document transformations.

---

## 10.2 Watermark Payload

Do not store:

```text
Recipient = R001
```

Instead store:

```text
WM_TOKEN = 256-bit random value
```

Optional metadata:

```text
WM_VERSION
DOCUMENT_HASH_PREFIX
```

The ledger maps:

```text
WM_TOKEN
   |
   +--> Document ID
   +--> Recipient ID
   +--> Session ID
   +--> Timestamp
   +--> Record hash
   +--> Signature
```

---

# 11. Visual Invariance Requirement

The user must not be able to visually distinguish the copies under the controlled test conditions.

The prototype should demonstrate:

```text
Original decrypted rendering
             VS
Recipient R001 rendering
             VS
Recipient R002 rendering
             VS
Recipient R003 rendering
```

Use automated rendering and image comparison where practical.

### Correct Claim

Use:

> "Non-rendering watermark with controlled visual-equivalence testing."

Do not claim:

> "100% identical under every possible print, scan, screenshot, OCR, compression, or editing operation."

---

# 12. Watermark Robustness Testing

### MVP Tests

Test at minimum:

- Open PDF
- Save PDF
- Copy file
- Rename file
- Transfer file
- Normal PDF rendering
- Watermark extraction

### Optional Tests

If time permits:

- PDF re-save using another library
- Metadata modification
- Text extraction
- Controlled compression

### Future Work

Production-grade robustness may require research and testing against:

- print/scan;
- screenshots;
- rasterization;
- OCR;
- cropping;
- recompression;
- page insertion/deletion;
- content editing.

Do not claim resistance unless actually tested.

---

# 13. Canonical Decryption Record

Every decryption produces a canonical record.

Example:

```json
{
  "record_version": "1.0",
  "document_id": "DOC-001",
  "document_hash": "SHA256...",
  "recipient_id": "R001",
  "session_id": "SES-001",
  "watermark_token": "256-bit-token",
  "decryption_timestamp": "2026-09-26T18:30:15Z"
}
```

The exact field order and serialization must be deterministic.

Use:

**JSON Canonicalization Scheme (RFC 8785)**

for deterministic serialization if supported by the implementation.

---

# 14. ML-DSA Signature

The recipient signs the canonical decryption record.

```text
Canonical Record
       |
       v
Hash / Canonical Bytes
       |
       v
ML-DSA-44 Sign
       |
       v
Digital Signature
```

Ledger stores:

```text
Canonical Record
Signature
Recipient Public Key Reference
```

The investigator can then perform:

```text
Record
  |
  v
ML-DSA Verification
  |
  +---- valid
  |
  +---- invalid
```

### Important Limitation

A valid cryptographic signature proves that the corresponding private signing key produced the signed record.

It should not automatically be described as a legal finding of guilt or absolute proof of human intent.

---

# 15. Offline Tamper-Evident Ledger

## MVP Architecture

Use a local append-only hash-chained ledger.

Example:

```text
BLOCK 001
previous_hash = GENESIS
record_hash = H(record)
block_hash = H(previous_hash + record_hash)

        |
        v

BLOCK 002
previous_hash = BLOCK001.hash
record_hash = H(record)
block_hash = H(previous_hash + record_hash)

        |
        v

BLOCK 003
...
```

---

# 16. Ledger Properties

Each block contains:

```text
block_index
timestamp
previous_hash
record_hash
record
signature
block_hash
```

### Verification

For every block:

```text
1. Recompute record hash.
2. Verify block hash.
3. Compare previous_hash with previous block hash.
4. Verify ML-DSA signature.
5. Confirm chain continuity.
```

If any block changes:

```text
Ledger Verification = FAILED
```

---

# 17. Important Ledger Terminology

For the 48-hour prototype, use:

> **Offline tamper-evident append-only hash-chained provenance ledger**

Do not describe a single local SQLite/hash-chain instance as a fully decentralized blockchain.

### Production Evolution

A production system can evolve into:

```text
Node A
   |
Node B ---- Permissioned DLT ---- Node C
   |
Node D
```

with an appropriate permissioned Byzantine-fault-tolerant consensus mechanism.

The production goal is that no single administrator can silently rewrite the complete audit history.

---

# 18. Investigation Workflow

The investigator uploads a suspected leaked document.

```text
Leaked Document
      |
      v
File Validation
      |
      v
Watermark Extraction
      |
      v
Extract WM_TOKEN
      |
      v
Ledger Search
      |
      v
Matching Record
      |
      v
ML-DSA Signature Verification
      |
      v
Document Hash Verification
      |
      v
Ledger Chain Verification
      |
      v
Attribution Report
```

---

# 19. Investigation Result

Example:

```text
FORENSIC ATTRIBUTION RESULT

Status:
VERIFIED

Document:
DOC-001

Watermark:
WM-9f83...

Recipient:
R001

Session:
SES-001

Decryption Time:
2026-09-26 18:30:15

Signature:
VALID

Ledger Chain:
VALID

Document Integrity:
VALID

Attribution Record:
VERIFIED AGAINST OFFLINE LEDGER
```

If verification fails:

```text
STATUS:
UNVERIFIED

Possible reasons:
- watermark not found
- ledger record missing
- signature invalid
- document hash mismatch
- ledger chain tampered
```

---

# 20. Database Design

Use SQLite for the MVP.

## documents

```text
id
document_id
filename
original_hash
encrypted_path
created_at
status
```

## recipients

```text
id
recipient_id
name / display_name
role
mlkem_public_key
mldsa_public_key
status
created_at
```

## encrypted_packages

```text
id
document_id
recipient_id
kem_ciphertext
wrapped_cek
metadata
```

## sessions

```text
id
session_id
document_id
recipient_id
watermark_token_hash
document_hash
timestamp
status
```

## ledger_blocks

```text
id
block_index
previous_hash
record_hash
canonical_record
signature
block_hash
timestamp
```

---

# 21. Backend Architecture

Recommended:

**FastAPI + Python**

Suggested modules:

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── documents.py
│   │   ├── recipients.py
│   │   ├── encryption.py
│   │   ├── decryption.py
│   │   ├── investigation.py
│   │   └── ledger.py
│   │
│   ├── crypto/
│   │   ├── pqc_kem.py
│   │   ├── pqc_dsa.py
│   │   ├── symmetric.py
│   │   ├── kdf.py
│   │   └── identity.py
│   │
│   ├── watermark/
│   │   ├── embed.py
│   │   ├── extract.py
│   │   └── validate.py
│   │
│   ├── ledger/
│   │   ├── blockchain.py
│   │   ├── canonical.py
│   │   └── verify.py
│   │
│   ├── models/
│   └── database/
│
└── tests/
```

---

# 22. Cryptographic Library Requirement

Do not implement cryptographic primitives manually.

Before coding, verify that the selected local library actually supports:

```text
ML-KEM-768
ML-DSA-44
AES-256-GCM
SHA-256
```

If the preferred library does not support the required algorithm/version, select another mature local implementation.

Do not force Python 3.13 compatibility if the selected PQC library does not support it. Use a supported Python version for the actual cryptographic dependency.

---

# 23. Frontend Architecture

Recommended:

```text
React
Vite
Tailwind CSS
```

### Pages

```text
1. Dashboard
2. Sender / Document Registration
3. Recipient Identity Management
4. Encryption
5. Recipient Decryption
6. Session History
7. Ledger Explorer
8. Leak Investigation
9. Verification Result
10. Tamper Demonstration
```

---

# 24. UI Requirements

The interface should communicate:

```text
CONFIDENTIAL
OFFLINE
PQC PROTECTED
AUDIT VERIFIED
```

Recommended visual style:

- dark navy/cybersecurity theme;
- clear status indicators;
- minimal animations;
- readable typography;
- strong evidence panels;
- technical but understandable presentation.

Do not spend excessive development time on visual effects before the cryptographic workflow works.

---

# 25. Recipient Identity Switcher

For demonstration:

```text
Recipient R001
Recipient R002
Recipient R003
```

Each recipient has:

- separate PQC key pair;
- separate identity;
- separate decryption history.

The demo must clearly show that the same encrypted document can be decrypted by different authorized recipients.

---

# 26. Core API Design

### POST

```text
/api/documents/register
```

Register document.

### POST

```text
/api/documents/encrypt
```

Encrypt document for selected recipients.

### POST

```text
/api/recipients/create
```

Create local recipient identity.

### POST

```text
/api/decrypt
```

Perform recipient decryption and watermark generation.

### POST

```text
/api/investigate
```

Upload suspected leaked document.

### GET

```text
/api/ledger
```

View ledger.

### GET

```text
/api/ledger/verify
```

Verify complete chain.

### POST

```text
/api/ledger/tamper-test
```

Controlled demonstration of tamper detection.

---

# 27. Air-Gapped Requirement

The complete runtime prototype must work without:

- internet;
- cloud APIs;
- Gemini API;
- OpenAI API;
- external AI inference;
- cloud KMS;
- public blockchain;
- online watermark service.

All required dependencies must be installed locally.

### Runtime Rule

```text
Internet = OFF

Application = STILL WORKS
```

This should be explicitly demonstrated during the final presentation if practical.

---

# 28. AI Usage Clarification

Gemini / Antigravity may be used during development as a coding assistant.

However:

```text
Gemini
Antigravity
ChatGPT
External AI APIs
```

must not be runtime dependencies of the submitted system.

The final architecture must remain:

```text
Local React
      +
Local FastAPI
      +
Local Crypto Libraries
      +
Local SQLite
      +
Local Ledger
```

---

# 29. Threat Model

The system should address:

### Threat 1 — Recipient leaks decrypted document

Mitigation:

```text
Unique session watermark
+
Ledger record
+
Cryptographic signature
```

### Threat 2 — Ledger record modified

Mitigation:

```text
Hash chaining
+
Signature verification
```

### Threat 3 — Watermark record modified

Mitigation:

```text
Ledger record hash
+
ML-DSA signature
```

### Threat 4 — Document content modified

Mitigation:

```text
Document hash comparison
```

### Threat 5 — Recipient identity spoofing

Mitigation:

```text
Recipient-specific PQC key pair
+
ML-DSA signature
```

### Threat 6 — Network/cloud compromise

Mitigation:

```text
Offline / air-gapped operation
```

---

# 30. Security Boundaries

The prototype must clearly distinguish:

### Confidentiality

Provided by:

```text
AES-256-GCM
+
ML-KEM-based key establishment
```

### Authenticity / Integrity

Provided by:

```text
AES-GCM authentication
+
SHA-256 hashes
+
ML-DSA signatures
```

### Forensic Attribution

Provided by:

```text
Unique watermark token
+
Recipient/session mapping
+
Signed decryption record
+
Tamper-evident ledger
```

---

# 31. Test Plan

## TC-01 — ML-KEM

```text
Generate recipient keys
        |
Encapsulate
        |
Decapsulate
        |
Compare shared secrets
```

Expected:

```text
PASS
```

---

## TC-02 — ML-DSA

```text
Generate signing keys
        |
Sign record
        |
Verify signature
```

Expected:

```text
PASS
```

---

## TC-03 — Visual Invariance

Generate:

```text
R001 copy
R002 copy
R003 copy
```

Render them under the same controlled environment.

Expected:

```text
No intentional visible watermark difference
```

---

## TC-04 — Watermark Uniqueness

Decrypt the same document:

```text
R001 session 1
R001 session 2
R002 session 1
R003 session 1
```

Expected:

```text
Different watermark token for every session
```

---

## TC-05 — Watermark Extraction

```text
Watermarked PDF
       |
       v
Extractor
       |
       v
WM_TOKEN
```

Expected:

```text
Token successfully recovered
```

---

## TC-06 — File Operations

Test:

```text
Copy
Rename
Transfer
Open
Save
```

Expected:

```text
Watermark remains extractable under tested operations
```

---

## TC-07 — Ledger Verification

Create several records.

Expected:

```text
Ledger = VALID
```

---

## TC-08 — Ledger Tamper Test

Modify one stored block.

Expected:

```text
Ledger = INVALID
```

Show the exact block where the chain breaks.

---

## TC-09 — Negative Investigation

Upload:

```text
Unwatermarked PDF
```

Expected:

```text
NO VERIFIED ATTRIBUTION
```

---

## TC-10 — Air-Gapped Test

Disable network connectivity.

Run:

```text
Registration
Encryption
Decryption
Watermarking
Signing
Ledger commit
Investigation
Verification
```

Expected:

```text
ALL CORE FEATURES WORK OFFLINE
```

---

# 32. 48-Hour Implementation Strategy

## Phase 1 — Hours 0–4

### Setup

- repository;
- backend;
- frontend;
- SQLite;
- dependency installation;
- cryptographic library validation.

### Critical checkpoint

Confirm actual working support for:

```text
ML-KEM-768
ML-DSA-44
AES-256-GCM
```

Do this before building the rest of the application.

---

# 33. Phase 2 — Hours 4–10

Implement:

```text
PQC identity generation
ML-KEM key generation
ML-DSA key generation
AES-GCM encryption
KEM shared-secret establishment
KDF
CEK wrapping/unwrapping
```

Write automated cryptographic tests.

---

# 34. Phase 3 — Hours 10–16

Implement:

```text
Document registration
Recipient management
Encryption
Recipient-specific encrypted package
Decryption
Session creation
```

At this point:

```text
Sender -> Encrypt -> Recipient -> Decrypt
```

must work completely offline.

---

# 35. Phase 4 — Hours 16–23

Implement:

```text
Watermark token generation
PDF watermark embedding
Watermark extraction
Visual equivalence testing
```

Do not spend excessive time trying to solve every possible transformation attack.

---

# 36. Phase 5 — Hours 23–30

Implement:

```text
Canonical decryption record
ML-DSA signature
Hash-chain ledger
Ledger verification
```

End-to-end:

```text
Decrypt
 -> Watermark
 -> Sign
 -> Ledger
```

must work.

---

# 37. Phase 6 — Hours 30–36

Implement investigation:

```text
Upload leak
 -> Extract token
 -> Lookup ledger
 -> Verify signature
 -> Verify document hash
 -> Verify ledger
 -> Display attribution
```

---

# 38. Phase 7 — Hours 36–42

Frontend integration:

```text
Dashboard
Encryption
Decryption
Ledger
Investigation
Verification
```

Prioritize usability over animation.

---

# 39. Phase 8 — Hours 42–46

Run all tests.

Fix:

- cryptographic bugs;
- PDF extraction bugs;
- ledger integrity issues;
- frontend/backend integration issues.

Prepare a clean demo dataset.

---

# 40. Phase 9 — Hours 46–48

Prepare:

- PPT;
- architecture diagram;
- threat model;
- test evidence;
- screenshots;
- demo sequence;
- backup video if required;
- offline demonstration.

---

# 41. Six-Person Team Division

## Member 1 — PQC / Cryptography

Responsible for:

- ML-KEM;
- ML-DSA;
- AES-GCM;
- KDF;
- key handling;
- crypto tests.

---

## Member 2 — Encryption / Decryption Backend

Responsible for:

- document registration;
- encryption package;
- recipient decryption;
- session management;
- APIs.

---

## Member 3 — Watermark Engine

Responsible for:

- token generation;
- PDF embedding;
- extraction;
- visual equivalence tests;
- watermark robustness experiments.

---

## Member 4 — Ledger / Forensics

Responsible for:

- canonical records;
- signatures;
- hash chain;
- ledger verification;
- investigation workflow.

---

## Member 5 — Frontend

Responsible for:

- React UI;
- dashboard;
- recipient workflow;
- ledger explorer;
- investigation interface.

---

## Member 6 — Integration / Testing / PPT

Responsible for:

- end-to-end integration;
- automated tests;
- attack/tamper demonstrations;
- screenshots;
- architecture diagrams;
- SIH PPT;
- final demo coordination.

---

# 42. Recommended Repository Structure

```text
sih26237/
│
├── backend/
├── frontend/
├── tests/
├── docs/
│   ├── architecture.md
│   ├── threat_model.md
│   └── demo.md
│
├── sample_data/
│   ├── original.pdf
│   └── leaked.pdf
│
├── scripts/
│
├── docker/
│
├── README.md
└── implementation_plan.md
```

---

# 43. Demo Scenario

Use three recipients:

```text
R001 — Commander Alpha
R002 — Officer Bravo
R003 — Officer Charlie
```

Register:

```text
operation_brief.pdf
```

Encrypt once for:

```text
R001
R002
R003
```

Then:

### Demo Step 1

Show:

```text
ONE encrypted document
THREE authorized recipients
```

### Demo Step 2

Decrypt as R001.

Show:

```text
Session ID
Watermark Token
Signature
Ledger Block
```

### Demo Step 3

Decrypt as R002.

Show a different:

```text
Session ID
Watermark Token
Signature
Ledger Block
```

### Demo Step 4

Show that the rendered documents appear visually equivalent.

### Demo Step 5

Pretend the R002 copy was leaked.

Upload it to the investigation portal.

### Demo Step 6

System extracts:

```text
WM_TOKEN
```

### Demo Step 7

System finds:

```text
Recipient R002
Session SES-002
```

### Demo Step 8

System verifies:

```text
ML-DSA Signature = VALID
Document Hash = VALID
Ledger Chain = VALID
```

### Demo Step 9

Tamper with a ledger block.

Run verification.

Show:

```text
LEDGER INTEGRITY = FAILED
```

This creates the main SIH demonstration story.

---

# 44. PPT Technical Architecture

Recommended architecture diagram:

```text
                 SENDER
                   |
                   v
          Document Registration
                   |
                   v
           AES-256-GCM Encryption
                   |
                   v
        +----------+----------+
        |          |          |
       R001       R002       R003
        |          |          |
     ML-KEM     ML-KEM     ML-KEM
        |          |          |
        +----------+----------+
                   |
                   v
          Local Decryption
                   |
                   v
       Session-Specific Token
                   |
                   v
          Invisible PDF Marker
                   |
                   v
            ML-DSA Signature
                   |
                   v
      Offline Hash-Chain Ledger
                   |
                   v
               LEAK
                   |
                   v
        Watermark Extraction
                   |
                   v
            Ledger Lookup
                   |
                   v
       Signature + Hash + Chain
             Verification
                   |
                   v
          FORENSIC ATTRIBUTION
```

---

# 45. Suggested PPT Slides

## Slide 1 — Title

**Sovereign Offline Forensic Attribution for Broadcast-Encrypted Documents**

---

## Slide 2 — Problem

Explain:

- same plaintext;
- visually identical copies;
- leak cannot be reliably attributed.

---

## Slide 3 — Proposed Solution

Show:

```text
Decrypt
 -> Watermark
 -> Sign
 -> Ledger
 -> Investigate
```

---

## Slide 4 — System Architecture

Show sender, recipients, crypto, watermark, ledger and investigator.

---

## Slide 5 — Post-Quantum Security

Explain:

```text
ML-KEM-768
ML-DSA-44
AES-256-GCM
SHA-256
```

---

## Slide 6 — Forensic Watermark

Explain:

```text
Unique random token
+
Decryption session
+
Non-rendering embedding
```

---

## Slide 7 — Immutable Audit Trail

Show:

```text
Block N-1
   |
Block N
   |
Block N+1
```

with previous hash relationships.

---

## Slide 8 — Leak Investigation

Show:

```text
Leak
 -> Extract
 -> Lookup
 -> Verify
 -> Attribute
```

---

## Slide 9 — Threat Model

Show:

```text
Leaked file
Tampered ledger
Modified document
Spoofed identity
Network compromise
```

and corresponding mitigations.

---

## Slide 10 — Offline / Air-Gapped Design

Show:

```text
NO CLOUD
NO PUBLIC BLOCKCHAIN
NO EXTERNAL AI
NO ONLINE KMS
```

---

## Slide 11 — Prototype Results

Show actual:

- ML-KEM test;
- ML-DSA test;
- visual equivalence;
- watermark extraction;
- ledger verification;
- tamper detection;
- offline test.

---

## Slide 12 — Future Scope

Possible production evolution:

- permissioned multi-node DLT;
- stronger watermark robustness;
- hardware-backed key protection;
- institutional key lifecycle;
- secure deployment in classified environments.

Clearly distinguish these from the working MVP.

---

# 46. MVP vs Production

| Capability | 48-Hour MVP | Production Direction |
|---|---|---|
| Key establishment | ML-KEM-768 | ML-KEM-based institutional PKI |
| Signatures | ML-DSA-44 | Institutional signing infrastructure |
| Symmetric encryption | AES-256-GCM | AES-GCM with managed key lifecycle |
| Watermark | Controlled PDF prototype | Robust forensic watermark research |
| Ledger | Local hash chain | Permissioned multi-node DLT |
| Database | SQLite | Hardened institutional database |
| Key storage | Encrypted local keystore | Hardware-backed protection |
| Deployment | Offline workstation | Hardened air-gapped environment |
| AI | None at runtime | None required for core workflow |
| Investigation | Token + cryptographic verification | Full forensic evidence pipeline |

---

# 47. Claims to Avoid

Do not claim:

- "ML-KEM encrypts the AES key directly."
- "The PDF watermark survives every possible transformation."
- "The metadata object is impossible to remove."
- "The single SQLite ledger is decentralized blockchain."
- "A valid signature proves criminal guilt."
- "The system is production-ready for classified deployment."
- "The system is legally non-repudiable."
- "The watermark is invisible under every conceivable rendering pipeline."

Use technically defensible wording instead.

---

# 48. Recommended Claims

Use:

> "The prototype establishes a cryptographically verifiable link between a controlled decryption session and a unique forensic watermark token."

> "ML-KEM is used for post-quantum key establishment, while AES-256-GCM protects document content."

> "ML-DSA signs the canonical decryption record."

> "The MVP uses an offline append-only hash-chained provenance ledger."

> "The architecture is designed to evolve into a permissioned multi-node DLT."

> "The prototype demonstrates watermark extraction and cryptographic attribution under the tested document transformations."

---

# 49. Final Acceptance Criteria

The prototype is considered successful if all of the following work offline:

```text
[ ] Recipient PQC identity generation
[ ] ML-KEM-768 key establishment
[ ] AES-256-GCM document encryption
[ ] Recipient-specific CEK protection
[ ] Recipient decryption
[ ] Unique session generation
[ ] Unique watermark token generation
[ ] Watermark embedding
[ ] Watermark extraction
[ ] Visual equivalence demonstration
[ ] Canonical decryption record
[ ] ML-DSA-44 signature
[ ] Hash-chained ledger commit
[ ] Ledger verification
[ ] Leak investigation
[ ] Recipient/session lookup
[ ] Signature verification
[ ] Document hash verification
[ ] Tamper detection
[ ] Air-gapped operation
```

---

# 50. Final Implementation Priority

If time becomes limited, implement in this exact order:

```text
1. PQC library validation
2. ML-KEM
3. AES-GCM
4. CEK wrapping flow
5. ML-DSA
6. Document encryption/decryption
7. Session generation
8. Watermark embedding/extraction
9. Signed decryption record
10. Hash-chain ledger
11. Investigation workflow
12. Verification
13. Frontend
14. UI polish
15. Advanced robustness
```

The working end-to-end security workflow is more important than visual polish.

---

# 51. Final Development Instruction for Antigravity

Before implementing anything:

1. Inspect the existing repository.
2. Inspect the current implementation plan.
3. Verify the actual cryptographic library/API available in the environment.
4. Confirm ML-KEM-768 and ML-DSA-44 support.
5. Confirm the supported Python version.
6. Identify any dependency incompatibilities.
7. Do not implement cryptographic primitives manually.
8. Do not introduce cloud APIs or runtime AI dependencies.
9. Preserve offline operation.
10. Keep the MVP implementation small enough to finish within 48 hours.

Before major implementation begins, produce a short technical readiness report containing:

```text
A. Confirmed capabilities
B. Library/API availability
C. Known compatibility risks
D. Watermark implementation risks
E. Ledger limitations
F. 48-hour MVP risks
G. Proposed mitigations
H. Exact first implementation steps
```

Then proceed with implementation only after the architecture is internally consistent.

---

# 52. Technical Readiness Checklist

Antigravity/Gemini should explicitly answer:

### Cryptography

- Can the environment run ML-KEM-768?
- Can the environment run ML-DSA-44?
- Is AES-256-GCM available?
- Is a suitable KDF available?
- Can private keys remain local?

### Watermark

- Can the chosen PDF library embed and extract the opaque token?
- Can the implementation demonstrate controlled visual equivalence?
- What transformations are actually supported?

### Ledger

- Can the local hash chain be created and verified?
- Can tampering be demonstrated?
- Is the MVP clearly distinguished from a distributed DLT?

### Offline

- Does the complete workflow work with network access disabled?
- Are all dependencies locally available?
- Are there any hidden API calls?

### Integration

- Can the full flow run:

```text
Register
 -> Encrypt
 -> Decrypt
 -> Watermark
 -> Sign
 -> Ledger
 -> Leak
 -> Extract
 -> Verify
 -> Attribute
```

without external services?

---

# 53. Final Success Demonstration

The strongest 2-minute demo should be:

```text
1. Encrypt one document for R001, R002 and R003.

2. Decrypt as R001.
   Show unique session + watermark.

3. Decrypt as R002.
   Show different session + watermark.

4. Show visually equivalent documents.

5. Upload the R002 copy as a "leak".

6. Extract watermark token.

7. Match ledger.

8. Verify ML-DSA signature.

9. Verify document hash.

10. Verify ledger chain.

11. Display:
       VERIFIED ATTRIBUTION
       Recipient: R002
       Session: SES-002

12. Tamper with one ledger block.

13. Run verification again.

14. Display:
       LEDGER INTEGRITY FAILED
```

This directly demonstrates the core problem, the proposed solution, cryptographic evidence, offline auditability, and tamper detection.
