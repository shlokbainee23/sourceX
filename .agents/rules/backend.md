# Backend Engineering Rules

> **Scope:** Applied when modifying Python backend code, FastAPI routers, database operations, or cryptography.

## 1. Schema Design & API Contracts

- All request models inherit from `StrictModel` (`extra="forbid"`). Unexpected fields will trigger HTTP 422.
- Before modifying or adding fields to schemas in `backend/app/models/schemas.py`:
  - Verify that changes do NOT break test fixtures in `tests/testenv.py` or existing UI in `frontend/src/App.jsx`.
  - Maintain backward compatibility (e.g. use `Optional[...] = None` for newly introduced fields).
- Endpoints must follow the established error contract in [docs/API.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/API.md):
  - 400: Semantically invalid input (bad classification, invalid PDF).
  - 401: Invalid/missing token or failed login.
  - 403: Role unauthorized, document access denied, or demo endpoint called without demo mode.
  - 404: Resource not found (including another recipient's session).
  - 409: Conflict (duplicate doc ID, registry drift, already encrypted).
  - 422: Pydantic schema validation failure.
  - 500: Generic internal error (no internal stack traces exposed to client).

## 2. Database & Ledger Operations

- Database connection: Always obtain connections via `get_connection()` from `app.database.connection`.
- Write operations that alter ledger blocks or session records must use `ledger_transaction()` to enforce the in-process concurrency lock and ensure the head anchor (`ledger_head.json`) is updated atomically after COMMIT.
- Never drop database triggers in production application code.

## 3. Audit Logging

- Record operational events via `record_audit(event, principal_id, outcome, ...)` from `app.audit`.
- Never include raw byte buffers, CEKs, passphrases, or private keys in the `details` dictionary.
