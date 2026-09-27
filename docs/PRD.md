# Product Requirements: SIH26237

## Problem

MoD / Indian Navy (WESEE) distributes sensitive documents by **broadcast encryption**: encrypt once, and each authorized recipient decrypts individually. After decryption, every recipient traditionally holds an identical copy, so a leaked copy cannot be tied to its source. A watermark applied before encryption is the same for everyone and does not help.

## Goal

When a leaked copy is recovered, identify **with cryptographic evidence** the recipient whose decryption session produced that exact file. Name nobody when the evidence is incomplete.

## Users

| Role | Needs |
|---|---|
| Issuing authority (WESEE HQ) | Register classified documents, encrypt once for a chosen set of recipients, enrol and revoke personnel |
| Recipient | Decrypt only what was issued to them and receive a readable copy |
| Investigator | Upload a recovered file and get a yes/no attribution with the evidence behind it |
| Auditor | Verify the ledger and review the audit trail |

## Functional requirements

1. Authenticated, role-enforced access. Identity comes from unlocking an encrypted local keystore.
2. Document registration with classification, signed by the authority.
3. Broadcast encryption: ML-KEM-768 key establishment per recipient, and one AES-256-GCM ciphertext.
4. Per-decryption forensic attribution marker, with no visible change to the rendered document.
5. Recipient-signed (ML-DSA-44) decryption record bound to the exact delivered file hash.
6. Tamper-evident hash-chained provenance ledger with verification and a head anchor.
7. Investigation that returns VERIFIED only when all ten evidence checks pass.
8. Signed identity attestation (trust-anchor manifest) with revocation that does not invalidate earlier evidence.
9. Audit trail of every security-relevant action, append-only.

## Non-functional requirements

- **Offline / air-gapped:** no runtime network, cloud KMS or public blockchain. The full workflow is tested with sockets disabled.
- **Fail closed:** any error, missing evidence or unavailable trust data means no attribution.
- **Honest claims:** every claim in the README or UI is implemented, enforced and tested. The approved wording is in `SECURITY.md`.
- **Supply-chain transparency:** SBOM and CBOM (CycloneDX 1.6), with an offline drift check.

## Government data and API integration

**Decision:** no government API or dataset is used at runtime. The problem is cryptographic and provenance-centric rather than data-dependent. The integrations that are adopted are local and offline:

| Integration | Mode | Requirement it meets |
|---|---|---|
| Signed trust-anchor manifest (issuing-authority identity data) | Signed data package, periodic import | Recipient keys must be attested by the authority, not just present in a local table |
| SBOM + CBOM aligned with CERT-In SBOM/QBOM/CBOM Guidelines v2.0 and TEC 910018:2025 | Local snapshot generated from the installed environment | Cryptographic inventory and component verification for air-gapped transfer |

Evaluated but intentionally not integrated: API Setu, data.gov.in, DigiLocker, CCA/India PKI online services, and live NIC/NPL time. The reasons and the full source register are in `GOVERNMENT_ECOSYSTEM.md`.

## Operational story

1. The authority provisions principals into encrypted keystores.
2. The authority's public-key fingerprint is pinned outside the data directory.
3. A signed trust manifest attesting every principal's keys is imported and recorded in the ledger.
4. The authority logs in and registers a classified PDF (a signed registration block).
5. The authority encrypts it once for R001–R003 (a signed broadcast-encryption block).
6. Each recipient logs in and decrypts.
7. At decryption, a fresh 256-bit marker is embedded invisibly.
8. The delivered file's SHA-256 is bound into a canonical decryption record.
9. The recipient's ML-DSA-44 key signs the record, and it is appended to the ledger.
10. Each recipient receives a visually identical but byte-unique copy.
11. A copy leaks.
12. The investigator uploads the recovered file.
13. The marker is extracted strictly and matched to exactly one session.
14. The file hash, record, signature and full chain are verified.
15. Document provenance and the recipient's key are verified against the local trusted manifest, which is itself verified under the pinned authority key.
16. All ten checks pass, giving VERIFIED attribution with the evidence and the trust-anchor version used. Any failure gives UNVERIFIED with no name.
17. The auditor verifies the ledger. Any modification, deletion or reordering is detected, and the tamper sandbox demonstrates this.

## Out of scope (prototype)

Print-and-scan robustness, hardware key storage, multi-node ledger replication, authority key rotation, SAG/JCB certification, and classified deployment.

## Success criteria

- The E2E proof and the full test suite pass.
- A modified document, modified record, modified ledger, unknown document, or unattested or revoked-before-decryption key never produces VERIFIED.
- An unauthorized recipient is denied.
- The core works with no network and no government source.
