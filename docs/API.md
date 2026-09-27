# API

The base URL is `http://127.0.0.1:8000`. The UI proxies `/api` through Vite, and interactive docs are at `/docs`.

Every endpoint except `/`, `/api/health` and `/api/auth/login` requires `Authorization: Bearer <token>`.

## Error contract

Errors return JSON `{"detail": "<message>"}` (for 422 the detail is a validation array).

| Code | Meaning |
|---|---|
| 400 | Semantically invalid input: bad classification, non-PDF, empty file, unknown recipient |
| 401 | Missing, invalid or expired token; failed login |
| 403 | Role not permitted; not authorized for this document; decryption denied; demo mode off |
| 404 | Resource not found, including another recipient's session |
| 409 | Conflict: duplicate document, already encrypted, ciphertext or hash integrity failure |
| 413 | Upload too large |
| 422 | Schema violation: missing or unexpected field, invalid identifier format |
| 500 | Generic internal error; no internals are disclosed |

## Auth

| Method | Path | Role | Body → Response |
|---|---|---|---|
| POST | `/api/auth/login` | – | `{principal_id, passphrase}` → `{token, principal_id, role, name, expires_in_seconds}` |
| POST | `/api/auth/logout` | any | → `{status}` |
| GET | `/api/auth/me` | any | → `{principal_id, role, name}` |

## Recipients and documents

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/api/recipients` | any | Public keys only |
| POST | `/api/recipients/create` | AUTHORITY | `{recipient_id, name, role, initial_passphrase}`; 409 if the recipient exists |
| GET | `/api/documents` | any | Recipients see only the documents they're authorized for |
| POST | `/api/documents/register` | AUTHORITY | multipart `document_id`, `classification` (RESTRICTED, CONFIDENTIAL, SECRET or TOP SECRET), `file` (PDF) |
| POST | `/api/documents/encrypt` | AUTHORITY | `{document_id, authorized_recipient_ids[]}`. One-shot (409 on repeat); unknown recipient → 400 |

## Decryption

| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/api/decrypt` | RECIPIENT | `{document_id}`. An optional `recipient_id` must equal self, otherwise 403 |
| GET | `/api/sessions/{session_id}/download` | RECIPIENT | Own sessions only; others get 404 |

The decrypt response is `{session_id, document_id, recipient_id, watermark_token, decryption_timestamp, delivered_document_hash, signature (truncated), block_index, block_hash, decrypted_file_path, message}`.

## Investigation

| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/api/investigate` | INVESTIGATOR | multipart `file` |
| POST | `/api/forensics/invariance` | AUTHORITY, INVESTIGATOR, AUDITOR | `{session_a, session_b}` → measured render comparison |

Investigation response (always 200 once the upload is accepted):

```json
{
  "status": "VERIFIED | UNVERIFIED | VERIFICATION_ERROR",
  "attribution_verdict": "CRYPTOGRAPHICALLY VERIFIED ATTRIBUTION: R002 (Officer Bravo) | NO VERIFIED ATTRIBUTION | VERIFICATION ERROR - NO ATTRIBUTION",
  "reason": "...",
  "attribution": {"recipient_id", "recipient_name", "recipient_role", "document_id", "classification", "session_id",
                  "decryption_timestamp", "block_index", "block_hash", "signer_public_key_sha256"} ,
  "verification": {"watermark_found", "watermark_valid", "session_found", "document_hash_match",
                   "record_consistent", "ledger_record_found", "signature_valid", "ledger_chain_valid",
                   "document_provenance_valid", "identity_trusted"},
  "trust_anchor": {"manifest_version", "manifest_sha256", "authority_pin"},
  "failures": [{"check": "...", "reason": "..."}],
  "uploaded_document_hash": "...", "watermark_token": "...", "watermark_status": "FOUND|NOT_FOUND|MALFORMED|CONFLICT|UNREADABLE",
  "ledger_error": null
}
```

`attribution` and the flat compatibility fields (`recipient_id`, `session_id`, …) are non-null **only** when `status == "VERIFIED"`.

## Ledger and audit

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/api/ledger` | AUTHORITY, INVESTIGATOR, AUDITOR | All blocks |
| GET | `/api/ledger/verify` | AUTHORITY, INVESTIGATOR, AUDITOR | `{chain_valid, total_blocks, verified_blocks, broken_block_index, error_message, verification_details[]}` |
| POST | `/api/ledger/tamper-test` | AUDITOR + demo mode | `{block_index, field, new_value}`. Fields: canonical_record, signer_id, previous_hash, timestamp, event_type, signature, record_hash, block_hash, delete, swap_with_next |
| POST | `/api/ledger/reset` | AUTHORITY or AUDITOR + demo mode | Clears evidence; keeps principals and keystores |
| GET | `/api/audit?limit=N` | AUDITOR | Most recent audit events (max 1000) |

## Trust anchor (signed identity manifest)

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/api/trust/manifest` | AUTHORITY, INVESTIGATOR, AUDITOR | `{available, authority_pin, current, history[]}` plus `error_code`/`reason` when unavailable. `current` is re-verified on every call |
| GET | `/api/trust/manifest/export` | AUTHORITY, AUDITOR | The signed package `{manifest, signature}` for transfer on removable media |
| POST | `/api/trust/import` | AUTHORITY | multipart `source_label` (provenance note), `file` (package JSON). Result `IMPORTED` or `ALREADY_IMPORTED` |
| POST | `/api/trust/issue` | AUTHORITY | Signs and imports the next version from the current registry |
| POST | `/api/trust/revoke` | AUTHORITY | `{principal_id, reason}`. New version with the principal REVOKED; ends its sessions |

Trust errors return `{"detail": "<CODE>: <message>"}`:

| Code | HTTP | Meaning |
|---|---|---|
| MALFORMED | 400 | Not a UTF-8 JSON object, duplicate keys, floats, over 1 MB, extra or missing top-level keys |
| SCHEMA_INVALID | 400 | Manifest fields or types wrong |
| PIN_MISMATCH | 400 | Issuer key is not the pinned authority |
| SIGNATURE_INVALID | 400 | ML-DSA signature does not verify (the content was modified) |
| STALE | 409 | Version lower than the current one |
| CONFLICT | 409 | Same version with different content, or removal, key change, role change or un-revocation |
| REGISTRY_DRIFT | 409 | The registry disagrees with an attested key, so issuing is refused |
| UNPINNED | 503 | No valid pin file |
| CORRUPTED | 503 | The stored manifest fails re-verification, or rollback was detected |
| NOT_AVAILABLE | 503 | No manifest imported yet |

The trust API never makes an outbound request, and none of its failures block encryption, decryption or ledger verification.
