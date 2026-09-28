# Testing & Verification Rules

> **Scope:** Applied when running, writing, or debugging tests.

## 1. Test Execution Commands

```powershell
# Run full Pytest suite (194 tests)
.\.venv\Scripts\python -m pytest tests -q

# Run end-to-end 18-step demonstration workflow
.\.venv\Scripts\python tests\test_e2e_workflow.py

# Verify software & cryptographic bill of materials
.\.venv\Scripts\python scripts\generate_bom.py --check
```

## 2. Test Isolation Standard

- All tests import `testenv`, which sets `SIH_DATA_DIR` to a fresh temporary directory (`SIH_TEST_DATA_DIR = tempfile.mkdtemp(...)`).
- Tests must NEVER read from or write to the live operational database `backend/data/sih26237.sqlite`.
- Passphrases in tests are generated randomly per run via `secrets.token_urlsafe()`.

## 3. When Writing New Tests

- Every new security path, API endpoint, or ledger event must include test coverage for:
  1. The happy path (authorized execution).
  2. Unauthorized role attempt (403).
  3. Malformed / unexpected input (422).
  4. Adversarial tampering / corruption (fails closed).
- Use `simulate_tampering` from `app.ledger.verify` to validate ledger tamper detection.
