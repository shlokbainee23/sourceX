# SIH26237: Offline Forensic Attribution System for Broadcast-Encrypted Documents

**Organization:** Ministry of Defence  
**Department:** Indian Navy — WESEE  
**Category:** Software  
**Theme:** Blockchain & Cybersecurity  
**Problem Statement:** SIH26237  
**Operational Environment:** Offline / air-gapped local infrastructure (no network or cloud dependencies at runtime)

---

## 1. Problem and Approach

Sensitive documents are distributed **broadcast-encrypt, individually-decrypt**: an authority encrypts once, and each authorized recipient decrypts independently. Once decrypted, every copy is traditionally identical. If one leaks, every recipient is an equally plausible suspect, and a pre-encryption watermark is the same for everyone.

This prototype acts **at the moment of decryption**:

1. A decryption session is created with an opaque 256-bit random **forensic attribution marker** (`WM-<64 hex>`).
2. The marker is embedded in the PDF as non-rendering text (PDF text render mode 3) and as metadata. Rendering with PyMuPDF at 150 DPI shows **0 differing pixel samples** (measured in tests).
3. A canonical decryption record binds the marker, session, recipient, document and **SHA-256 of the exact delivered file**. The recipient signs it with **ML-DSA-44 (FIPS 204)**.
4. The signed record is appended to a **tamper-evident hash-chained provenance ledger**.
5. An investigator uploads a leaked file. Attribution is reported as **VERIFIED** only if all ten checks pass: marker found, marker well-formed, session, exact document hash, record consistency, ledger record, signature, full chain, document provenance (authority-signed registration and encryption to this recipient), and the recipient's key being attested by the **signed trust-anchor manifest** under the pinned authority key. Otherwise the result is **UNVERIFIED** or **VERIFICATION_ERROR**, and no suspect is named.

No government API or dataset is used at runtime. The problem is cryptographic and provenance-centric, not data-dependent. Official sources were evaluated, and the two with a concrete requirement were localized: signed identity attestation and CERT-In-aligned SBOM/CBOM. See [docs/GOVERNMENT_ECOSYSTEM.md](docs/GOVERNMENT_ECOSYSTEM.md).

What this system does **not** claim is listed in [Known limitations](#6-known-limitations).

---

## 2. Cryptographic Suite

| Purpose | Algorithm | Standard | Implementation |
|---|---|---|---|
| Key establishment (not document encryption) | ML-KEM-768 | FIPS 203 | `mlkem` |
| Signatures on provenance records | ML-DSA-44 | FIPS 204 | `dilithium_py` (pure Python) |
| Document and CEK encryption | AES-256-GCM, random 96-bit nonces, context AAD | SP 800-38D | `cryptography` |
| Wrapping-key derivation | HKDF-SHA256, info bound to document and recipient | RFC 5869 | `cryptography` |
| Private-key protection | scrypt + AES-256-GCM encrypted local software keystore | RFC 7914 | `cryptography` |
| Record canonicalization | Sorted-key compact UTF-8 JSON, floats rejected | Deterministic JSON (not full RFC 8785) | `ledger/canonical.py` |
| Provenance ledger | SHA-256 hash chain, every block ML-DSA-signed, external head anchor | — | SQLite + append-only triggers |

The pipeline is: `ML-KEM-768 → shared secret → HKDF-SHA256 → wrapping key → AES-256-GCM(CEK)`, with `AES-256-GCM(CEK) → document`. Details are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 3. Roles (enforced server-side)

| Role | Principal(s) | Can |
|---|---|---|
| AUTHORITY | `WESEE_HQ` | Register and broadcast-encrypt documents; enrol and revoke principals; import signed trust manifests |
| RECIPIENT | `R001`, `R002`, `R003` | Decrypt documents packaged for themselves; download only their own copies |
| INVESTIGATOR | `INVESTIGATOR_01` | Investigate leaked files |
| AUDITOR | `AUDITOR_01` | Verify the ledger, read the audit trail, run tamper simulation (demo mode) |

Logging in means unlocking that principal's encrypted keystore with its passphrase. The full permission matrix is in [docs/SECURITY.md](docs/SECURITY.md).

---

## 4. How to Run

Prerequisites: Python 3.12+ and Node.js 20+.

```powershell
# One-time setup (project root)
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
cd frontend; npm install; cd ..

# Provision principals into encrypted keystores (prompts for passphrases,
# or --generate prints random ones ONCE). Also migrates and destroys v1 plaintext keys,
# writes the authority pin (trust_anchor/authority.pin) and issues the signed trust manifest.
# Existing deployments: add --issue-manifest to pin and attest already-provisioned keys.
.\.venv\Scripts\python scripts\provision_identities.py

# Optional: verify installed software and crypto parameters against the committed SBOM/CBOM
.\.venv\Scripts\python scripts\generate_bom.py --check

# Backend (demo mode enables tamper simulation and reset)
$env:SIH_DEMO_MODE="1"; .\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd frontend; npm run dev      # http://localhost:5173
```

In the UI, choose a station in the top-right selector and enter that principal's passphrase. Demo flow:
1. `WESEE_HQ`: register and encrypt a document.
2. `R001`, `R002`, `R003`: each decrypts, and `R002` downloads their copy.
3. `INVESTIGATOR_01`: upload R002's copy.
4. `AUDITOR_01`: run the tamper sandbox.

---

## 5. Verification Evidence

```powershell
.\.venv\Scripts\python -m pytest tests -q          # 194 tests, isolated temp data directory
.\.venv\Scripts\python tests\test_e2e_workflow.py   # verbose 18-step end-to-end proof
```

| Suite | Covers |
|---|---|
| `test_e2e_workflow.py` | The full 18-step proof: register → encrypt → 3 decryptions → unique markers → measured invariance → VERIFIED attribution of the leaked copy → clean, modified and tampered-ledger cases UNVERIFIED → unauthorized decryption denied → no plaintext keys on disk |
| `test_security_crypto.py` | Wrong recipient, corrupted ciphertext, tag, wrapped key and KEM ciphertext, context swapping, altered records, invalid signatures |
| `test_security_keystore.py` | Unlock, wrong passphrase, ciphertext and header tampering, KDF downgrade, principal swap, registry mismatch, lockout, legacy migration |
| `test_security_watermark.py` | Missing, malformed, altered, conflicting, unknown, duplicate and transplanted markers |
| `test_security_investigation.py` | Exact match, modified or re-saved document, marker on wrong document, invalid signature, broken ledger, forged session rows, fail-closed errors |
| `test_security_ledger.py` | Modified, deleted, inserted, reordered and truncated blocks; every header field; append-only triggers; concurrent appends |
| `test_security_api.py` | Authentication, role matrix, cross-recipient access, path traversal, malformed and unexpected input, duplicates, secret non-disclosure, audit trail |
| `test_trust_integration.py` | Signed manifest import: valid, malformed, oversize, modified, foreign authority, stale, conflicting, duplicate, rollback, corrupted store, missing pin, registry substitution, revocation lifecycle, full workflow with the network disabled |
| `test_bom.py` | CBOM matches code constants, no quantum-vulnerable algorithms, SBOM matches the installed environment, tampered BOM detected |
| `test_crypto.py`, `test_watermark.py`, `test_ledger.py` | Primitive and component behaviour |

---

## 6. Known Limitations

- **Exact-hash attribution:** any modification or re-save of the delivered file makes the result UNVERIFIED. This is deliberate; a marker alone never attributes.
- **The marker is removable:** it is invisible text plus metadata. Text extraction reveals it, and rasterizing, printing and scanning, or regenerating the PDF removes it. It supports attribution; it does not prevent leaks.
- **Encrypted local software keystore, not an HSM:** keys are in server memory while a principal is logged in, and signing happens server-side.
- **Tamper-evident, not immutable:** substituting a registry key now fails the trust-manifest check. An attacker who controls both the data directory and the pin file, or who holds the authority private key, can still forge consistent evidence.
- **Not cleared for classified use:** the algorithms are NIST PQC, not SAG-approved; keys are not from JCB; there is no hardware key storage; and it is PQC-only, not hybrid. See the government-aligned controls in [docs/SECURITY.md](docs/SECURITY.md).
- **Single-process prototype:** sessions live in memory and are cleared on restart.

The full list is in [docs/SECURITY.md](docs/SECURITY.md).

---

## 7. Prototype vs Production

| Capability | This prototype | Production direction |
|---|---|---|
| Ledger | Single-node SQLite hash chain, signed blocks, local head anchor | Replicated ledger across command nodes with externally witnessed checkpoints |
| Key storage | scrypt + AES-256-GCM encrypted local software keystore | HSM / smartcard (PKCS#11), recipient-side signing |
| Trust anchors | Pinned authority key, signed monotonic identity manifest, revocation | Pin on read-only or hardware media, authority key rotation, recipient certificates |
| Marker robustness | Survives copy, rename and transfer of the unmodified file | Layered marking with print-and-scan resilience, and fuzzy attribution evidence |
| Cloud / AI dependencies | None | None |

Documentation: [PRD](docs/PRD.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · [SECURITY](docs/SECURITY.md) · [GOVERNMENT_ECOSYSTEM](docs/GOVERNMENT_ECOSYSTEM.md) · [API](docs/API.md) · [DATABASE](docs/DATABASE.md) · [CODE_STYLE](docs/CODE_STYLE.md) · [AGENTS](docs/AGENTS.md) · [PRESENTATION](docs/PRESENTATION.md)
