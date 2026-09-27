# Code Style

## Backend (Python 3.12+, FastAPI, Pydantic v2)

- Each module opens with a docstring stating its responsibility and any security property it enforces. Keep that docstring accurate when behaviour changes.
- Put route handlers in `app/api/<area>.py`, with an `APIRouter(prefix="/api/...")`. Keep reusable logic out of routes: crypto goes in `app/crypto`, ledger code in `app/ledger`, and attribution in `app/forensics.py`.
- Authorization is declared in the handler signature with `Depends(require_roles(...))` or `Depends(current_session)`. Never check roles against request data.
- Request models extend `StrictModel` (`extra="forbid"`) and validate identifiers with `ID_PATTERN`.
- Raise `HTTPException` with a short, non-sensitive `detail`. Never interpolate exception text (`str(e)`) into responses.
- Database access uses `get_connection()` with plain SQL and `?` parameters. Multi-statement writes use `transaction(conn)`; anything that appends to the ledger uses `ledger_transaction(conn)`. Close connections in `finally`.
- Hashes are lowercase hex SHA-256 strings. Keys and signatures are stored as hex.
- Randomness comes only from `os.urandom` or `secrets`.
- Record security-relevant outcomes with `record_audit(EVENT, principal_id, outcome, **safe_details)`.
- Style: 4-space indentation, snake_case, type hints on public functions, and lines up to about 120 characters.

## Frontend (React 19 + Vite + Tailwind v4)

- `frontend/src/App.jsx` is a single component with `useState` hooks. Every backend call goes through `apiFetch`, which attaches the bearer token.
- Tailwind utility classes only; keep the existing dark "tactical" visual language.
- Linting uses `oxlint` (`npm run lint`), and the build must pass `npm run build`.

## Tests (pytest)

- Tests live in `tests/`. `tests/testenv.py` must be imported before any `app` module, because it isolates `SIH_DATA_DIR` to a temporary directory and turns on demo mode.
- Use the fixtures in `conftest.py`: `creds` (provision once per session), `clean_ledger` and `client`.
- Security tests assert the **failure** outcome explicitly (status code, `status != "VERIFIED"`, `chain_valid is False`).
- Legacy suites can also be run directly: `python tests/test_e2e_workflow.py`.
