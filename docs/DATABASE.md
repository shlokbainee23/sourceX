# Database

The database is SQLite at `$SIH_DATA_DIR/sih26237.sqlite` (default `backend/data/`), created by `app/database/connection.py::init_db()`. The schema version is kept in `PRAGMA user_version` and is currently 3. When a v1 database is opened, its evidence tables are dropped, because they can't be verified under v2 rules; recipient public keys are kept. Moving from v2 to v3 only adds `trust_manifests` and the permanent triggers, and no data is dropped.

Connections use `isolation_level=None`, and writers use `transaction()` (`BEGIN IMMEDIATE`). Anything that appends ledger blocks uses `ledger.blockchain.ledger_transaction()`, which adds an in-process lock and writes the head anchor after COMMIT.

## Tables

**principals**: the authentication registry.
- Columns: `principal_id` (PK), `role` (CHECK: AUTHORITY, RECIPIENT, INVESTIGATOR or AUDITOR), `name`, `mldsa_public_key` (nullable; set for AUTHORITY and RECIPIENT), `status`, `created_at`.

**recipients**: the recipient public-key directory, used for encryption and signature verification.
- Columns: `recipient_id` (UNIQUE), `name`, `role` (job title), `mlkem_public_key`, `mldsa_public_key`, `status` (`ACTIVE` or `REVOKED`; only ACTIVE keys receive new encryptions, while revoked keys are still used to verify earlier signatures), `created_at`.

**documents**
- Columns: `document_id` (UNIQUE), `filename`, `original_hash` (SHA-256 of the registered PDF), `classification`, `owner` (the authenticated authority), `encrypted_path`, `created_at`, `status` (CHECK: `REGISTERED` or `ENCRYPTED`).

**encrypted_packages**: one row per (document, recipient).
- Columns: `kem_ciphertext`, `wrapped_cek`, `wrap_nonce` (all hex), `created_at`.
- Constraints: `UNIQUE(document_id, recipient_id)`, with foreign keys to `documents` and `recipients`.

**sessions**: one row per successful decryption. Append-only (triggers).
- Columns: `session_id` (UNIQUE), `document_id`, `recipient_id`, `watermark_token` (UNIQUE), `watermark_token_hash`, `source_document_hash`, `delivered_document_hash`, `delivered_filename`, `signature`, `block_index`, `timestamp`, `status`.

**ledger_blocks**: the tamper-evident hash chain. Append-only (triggers).
- Columns: `block_index` (UNIQUE), `timestamp`, `event_type`, `previous_hash`, `record_hash`, `canonical_record` (the exact canonical JSON text), `signature` (ML-DSA-44 hex), `signer_id`, `block_hash` (UNIQUE).

**audit_events**: the operational audit trail. Append-only (permanent triggers), but not hash-chained or signed.
- Columns: `timestamp`, `event`, `principal_id`, `outcome`, `details` (redacted JSON).

**trust_manifests**: the local trusted store of signed identity manifests. Append-only (permanent triggers).
- Columns: `version` (PK), `manifest_sha256` (UNIQUE), `package` (the canonical signed package, re-verified on every read), `issuer_fingerprint`, `issued_at`, and the provenance fields `source_label`, `imported_by` and `imported_at`.

## Append-only triggers

- **Resettable:** `ledger_no_update`, `ledger_no_delete`, `sessions_no_update` and `sessions_no_delete` raise `ABORT`. Only `reset_test_database()` (demo reset) and `ledger.verify.simulate_tampering()` drop them, and both restore them through `init_db()`.
- **Permanent:** `audit_no_update`, `audit_no_delete`, `trust_no_update` and `trust_no_delete` are never dropped by application code, including demo reset.

Demo reset clears the ledger, which also removes the `TRUST_MANIFEST_IMPORTED` blocks used to detect a rollback of manifests imported before the reset. Stored manifests still verify against the pin.

## Ledger records (canonical JSON)

| event_type | signer | record_type | key fields |
|---|---|---|---|
| DOCUMENT_REGISTERED | AUTHORITY | DOCUMENT_REGISTRATION | authority_id, document_id, filename, original_hash, classification, timestamp |
| DOCUMENT_ENCRYPTED | AUTHORITY | BROADCAST_ENCRYPTION | authority_id, document_id, original_hash, ciphertext_hash, authorized_recipients, timestamp |
| DOCUMENT_DECRYPTED | RECIPIENT | DECRYPTION_RECORD (v2.0) | document_id, recipient_id, session_id, watermark_token, source_document_hash, delivered_document_hash, decryption_timestamp |
| TRUST_MANIFEST_IMPORTED | AUTHORITY | TRUST_MANIFEST | authority_id, manifest_version, manifest_sha256, issuer_fingerprint, source_label, timestamp |

Canonical form: keys sorted, compact separators, UTF-8, and floats rejected (`ledger/canonical.py`).

## Files outside SQLite (`$SIH_DATA_DIR`)

- `keystore/<id>.keystore.json`: the encrypted keystores.
- `documents/<doc>_original.pdf`: exists only between registration and encryption.
- `documents/<doc>_encrypted.bin`: the 12-byte nonce followed by the AES-GCM ciphertext and tag.
- `documents/<doc>_<recipient>_<session>.pdf`: delivered watermarked copies.
- `ledger_head.json`: the head anchor, `{block_index, block_hash, updated_at}`.

## Files outside the data directory

- `trust_anchor/authority.pin` (or `$SIH_AUTHORITY_PIN_FILE`): 64 hex characters, the SHA-256 of the authority's ML-DSA-44 public key. Written once by `scripts/provision_identities.py`, and never overwritten with a different value.
- `bom/sbom.cdx.json`, `bom/cbom.cdx.json`, `bom/SHA256SUMS`: the software and cryptographic bills of materials (`scripts/generate_bom.py`).
