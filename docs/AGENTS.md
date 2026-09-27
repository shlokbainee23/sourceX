# Instructions for Coding Agents

This is an offline forensic document-attribution prototype. Its value depends entirely on its security claims being **true, enforced and tested**. The code is the source of truth. Update the docs whenever behaviour changes.

## Before you change anything

1. Read `docs/ARCHITECTURE.md` for the pipeline and the attribution rule.
2. Before touching any file in the "security-sensitive operations" list, read `docs/SECURITY.md`, including the **Agent prohibitions** at the end.
3. Read `docs/DATABASE.md` before changing the schema, and `docs/API.md` before changing endpoints or response shapes.
4. Follow `docs/CODE_STYLE.md`.
5. Before adding any external data source, API or dependency, read `docs/GOVERNMENT_ECOSYSTEM.md` and the **External dependency policy** in `docs/ARCHITECTURE.md`. `docs/PRD.md` defines scope.

## Invariants you must preserve

- No invalid evidence may produce `VERIFIED` attribution. A watermark match alone never attributes.
- Verification fails closed: an error, a missing record or partial evidence means not verified.
- Identity and role come only from the server-side session.
- No plaintext private keys on disk; no keys or passphrases in responses, logs or audit details.
- Ledger blocks and sessions are append-only in normal operation. Tamper simulation and reset exist only behind demo mode.
- ML-KEM is used only for key establishment. The document is encrypted with AES-256-GCM.
- No runtime network access. External data enters only as a pinned, signed, schema-validated package with recorded provenance, and its failure may only make attribution fail closed.
- Trust manifests and audit events are never updated or deleted. Revocation is monotonic and does not invalidate earlier signatures.
- After changing dependencies or crypto parameters, regenerate `bom/` (`scripts/generate_bom.py`) so that `--check` passes.

## Running things

```powershell
.\.venv\Scripts\python -m pytest tests -q         # full suite (isolated temp data dir)
.\.venv\Scripts\python tests\test_e2e_workflow.py  # 18-step end-to-end proof, verbose
cd frontend; npm run lint; npm run build
.\.venv\Scripts\python scripts\provision_identities.py [--generate] [--issue-manifest]
.\.venv\Scripts\python scripts\generate_bom.py [--check]
```

## When you add a feature

- Add a test for every new security-relevant path, including its failure cases.
- If you add a claim to the README or UI, it must be implemented, enforced and tested first. Use precise terms: "tamper-evident" (not "immutable"), "encrypted local software keystore" (not "HSM"), and "forensic attribution marker" (not "unremovable watermark").
