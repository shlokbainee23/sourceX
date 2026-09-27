# SIH26237: How the Prototype Works
## Offline Forensic Attribution System for Broadcast-Encrypted Documents

**Department:** Ministry of Defence // Indian Navy — WESEE  
**Theme:** Blockchain & Cybersecurity  
**Problem Statement:** SIH26237  
**Environment:** Offline / air-gapped local infrastructure

> This is a plain-language walkthrough. The authoritative technical references are
> [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), [API.md](API.md) and [DATABASE.md](DATABASE.md).

---

## 1. The Problem in Plain English

WESEE HQ encrypts a secret document once and broadcasts it to three officers:
- **R001 — Commander Alpha** (Navigation)
- **R002 — Officer Bravo** (Communications)
- **R003 — Officer Charlie** (Weapons)

Each officer decrypts it independently. Traditionally, all decrypted copies are identical. If one leaks, every officer is an equally plausible suspect, and a watermark applied before encryption is the same for everyone.

### What the prototype does instead
1. When Officer Bravo decrypts, the server creates a **decryption session** and a random 256-bit **forensic attribution marker** (`WM-<64 hex>`). The marker contains no name.
2. The marker is embedded invisibly, as PDF text render mode 3 (neither fill nor stroke) plus a metadata entry.
3. A canonical decryption record binds the marker, session, recipient, document and the **SHA-256 of the exact file Bravo receives**. It is signed with Bravo's **ML-DSA-44** key, which is unlocked from Bravo's encrypted keystore when he logs in.
4. The signed record is appended to a **tamper-evident hash-chained provenance ledger**.
5. When a leaked PDF is found, the investigator uploads it. Attribution is **VERIFIED** only if the marker, the session, the exact file hash, the record, the signature and the full ledger all check out. Anything else is reported as **UNVERIFIED** or **VERIFICATION_ERROR**, with no suspect named.

---

## 2. Repository Layout

```text
backend/app/
  main.py            FastAPI app, CORS, generic error handler
  config.py          Environment configuration (data dir, demo mode, limits)
  auth.py            Login (keystore unlock) + bearer sessions + role checks
  audit.py           Security audit trail (no secrets)
  forensics.py       Strict fail-closed attribution engine
  api/               auth, documents, encryption, decryption, investigation, ledger, recipients
  crypto/            pqc_kem (ML-KEM-768), pqc_dsa (ML-DSA-44), kdf (HKDF), symmetric (AES-GCM),
                     keystore (scrypt + AES-GCM encrypted local software keystore), identity
  watermark/         embed, extract (strict), validate (render comparison)
  ledger/            canonical JSON, blockchain (append + head anchor), verify, records
  database/          SQLite schema, append-only triggers, migrations
backend/data/        documents/, keystore/*.keystore.json, sih26237.sqlite, ledger_head.json
frontend/src/App.jsx React dashboard
scripts/             provision_identities.py, reset_test_environment.py, start_*.bat
tests/               unit, adversarial security suites, 18-step E2E
```

---

## 3. Data Flow

```text
[AUTHORITY WESEE_HQ, logged in]
  Register PDF → SHA-256 → record signed by authority (ML-DSA) → Block: DOCUMENT_REGISTERED
  Encrypt      → random CEK → AES-256-GCM(document, AAD=doc id)
               → per recipient: ML-KEM-768 encaps → shared secret → HKDF(info=doc|recipient)
                 → AES-256-GCM(CEK, AAD=doc|recipient)
               → record signed by authority (incl. ciphertext hash) → Block: DOCUMENT_ENCRYPTED
               → plaintext original destroyed

[RECIPIENT R002, logged in]
  Decrypt      → ML-KEM decaps → HKDF → unwrap CEK → AES-GCM decrypt → check source hash
               → session SES-… + marker WM-… → embed marker → SHA-256(delivered file)
               → canonical record signed with R002's ML-DSA key → Block: DOCUMENT_DECRYPTED
  Download     → only R002's own session file

[INVESTIGATOR_01, logged in]
  Upload leak  → extract marker (must be exactly one valid marker)
               → session lookup → uploaded hash == recorded delivered hash?
               → rebuild record from session == ledger record?
               → ML-DSA signature valid under R002's registered key?
               → full ledger verification (chain, signatures, head anchor)
               → all pass: VERIFIED attribution to R002; otherwise no attribution
```

---

## 4. Components

### 4.1 Cryptography
- **ML-KEM-768 (FIPS 203):** key establishment only. It produces a 32-byte shared secret and a 1088-byte ciphertext. It does **not** encrypt the document.
- **HKDF-SHA256:** derives the 256-bit wrapping key from the shared secret. The info string binds the document ID and recipient ID, so a wrapped key cannot be moved to another document or recipient.
- **AES-256-GCM:** encrypts the document with the CEK, and the CEK with the wrapping key. Nonces are random, and the AAD binds the context.
- **ML-DSA-44 (FIPS 204):** signs every provenance record. Keys are 1312 bytes (public) and 2560 bytes (private); signatures are 2420 bytes.

### 4.2 Keystore
Private keys live in `backend/data/keystore/<ID>.keystore.json`, encrypted with AES-256-GCM under a key derived by scrypt from the principal's passphrase (random salt and nonce). A wrong passphrase or any modification fails cleanly. This is an **encrypted local software keystore, not an HSM**.

### 4.3 Forensic attribution marker
The marker is an opaque random token. Only the ledger links it to a session and recipient. Rendering the original and the marked PDF with PyMuPDF at 150 DPI shows 0 differing pixel samples. **Limitations:** text extraction reveals the marker, and rasterizing, printing and scanning, or regenerating the PDF removes it. Any modification changes the file hash, so attribution becomes UNVERIFIED.

### 4.4 Tamper-evident ledger
```text
block_hash = SHA-256(canonical_json({v:2, block_index, timestamp, event_type,
                                     previous_hash, record_hash, signer_id, signature}))
record_hash = SHA-256(canonical record bytes)
```
`verify_ledger()` checks index continuity, previous-hash links, the record hash, the block hash, each signature under the correct role's key, duplicate sessions and markers, and the external head anchor. It detects modified, deleted, inserted, reordered and truncated blocks. SQLite triggers block UPDATE and DELETE in normal operation. The ledger is tamper-**evident**, not immutable.

---

## 5. UI Tabs

| Tab | What happens |
|---|---|
| Operational Overview | Stats, algorithms, registered principals |
| 1. Sender Broadcast | AUTHORITY registers and encrypts for the selected recipients |
| 2. Recipient Decryption | The logged-in RECIPIENT decrypts; session, marker, signature and ledger block are created |
| 3. Visual Invariance | Backend renders two recipients' delivered copies and reports the measured pixel difference |
| 4. Leak Forensics | INVESTIGATOR uploads a file; evidence checklist and verdict |
| 5. Tamper-Evident Ledger | Block history with hashes, signers and records |
| 6. Tamper Sandbox | AUDITOR (demo mode only) modifies a block and sees verification fail |

---

## 6. Running the Tests

```powershell
.\.venv\Scripts\python -m pytest tests -q          # full suite
.\.venv\Scripts\python tests\test_e2e_workflow.py   # 18-step end-to-end proof
```
