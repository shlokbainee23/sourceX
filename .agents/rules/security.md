# Security & Compliance Rules

> **Scope:** Applied when touching security-sensitive code, keystores, cryptography, APIs, or ledger.

## 1. Security-Sensitive Files List

Before modifying any of these files, review [docs/SECURITY.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/SECURITY.md):
- `backend/app/crypto/*` (`keystore.py`, `identity.py`, `pqc_kem.py`, `pqc_dsa.py`, `symmetric.py`, `kdf.py`)
- `backend/app/auth.py`, `backend/app/audit.py`
- `backend/app/api/decryption.py`, `backend/app/api/encryption.py`
- `backend/app/ledger/*` (`blockchain.py`, `records.py`, `verify.py`, `canonical.py`)
- `backend/app/forensics.py`, `backend/app/watermark/*`
- `backend/app/trust.py`, `backend/app/api/trust.py`
- `trust_anchor/authority.pin`, `scripts/provision_identities.py`

## 2. Mandatory Agent Prohibitions

Agents must NEVER:
1. Write private keys, passphrases, or unlocked key dictionaries to disk, logs, HTTP responses, or test fixtures.
2. Accept identity or role from request body or query parameter; trust only the server-side bearer session.
3. Allow any verification function to return success on an exception, missing record, or partial evidence set.
4. Allow a watermark token match alone to attribute a document without the exact delivered file hash match.
5. Mutate `ledger_blocks` or `sessions` tables outside demo-mode tamper simulation or test database reset.
6. Drop or bypass the append-only triggers (`audit_no_update`, `trust_no_update`, `ledger_no_update`, etc.).
7. Weaken scrypt parameters (N=32768, r=8, p=1), reuse AES nonces, or replace PQC algorithms with classical ones.
8. Add any runtime network call or make any external API a dependency of core encryption, decryption, or verification.
9. Claim compliance with or certification against SAG, JCB, MHA NISPG, or IT-Act legal signatures. Use honest vocabulary:
   - "tamper-evident" (NOT "immutable")
   - "encrypted local software keystore" (NOT "HSM")
   - "forensic attribution marker" (NOT "unremovable watermark" or "leak prevention")

## 3. Fail-Closed Design Rule

All verification paths must fail closed:
- An exception in `investigate_document()` returns `VERIFICATION_ERROR`.
- A missing record, signature mismatch, or chain break returns `UNVERIFIED`.
- When attribution is not `VERIFIED`, the returned `recipient_id`, `recipient_name`, `session_id`, and `attribution` object must be strictly `null`.
