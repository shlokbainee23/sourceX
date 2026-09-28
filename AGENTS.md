# AGENTS.md — SIH26237 Project Agent Rules

> **Operating Standard for AI Coding Agents**  
> This is an offline forensic document-attribution system for Indian Navy (WESEE) / MoD.  
> Its value depends entirely on its security and cryptographic claims being **true, enforced, and tested**.

---

## 1. Prime Directive: The Repository is the Source of Truth

1. **Verify Before Assuming:** Never treat documentation as ground truth when it contradicts active source code, schemas, or tests. Documentation is evidence, not truth.
2. **Never Hallucinate:** If an endpoint, library, schema field, government integration, or feature cannot be confirmed from the codebase, classify it as `UNKNOWN`. Never fabricate APIs, credentials, or completion percentages.
3. **Use Explicit Evidence States:** Classify claims as `VERIFIED`, `DOCUMENTED`, `INFERRED`, `UNKNOWN`, or `CONFLICT`.
4. **Never Silently Resolve Conflicts:** When code and documentation diverge, document the discrepancy in [docs/brain/CURRENT_STATE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CURRENT_STATE.md). Do not silently rewrite one version without an explicit task.

---

## 2. Mandatory Protocol Before Any Coding

Before implementing any task:
1. Read [docs/brain/CURRENT_STATE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CURRENT_STATE.md) to understand verified reality and known breakages.
2. Read [docs/brain/TASKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/TASKS.md) to verify task requirements and dependencies.
3. Consult [docs/brain/DECISIONS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/DECISIONS.md) before proposing architectural alterations.
4. Inspect the relevant implementation and tests directly.
5. Follow the cycle: **DISCOVER → PLAN → IMPLEMENT → TEST → VERIFY → UPDATE BRAIN**.

---

## 3. Invariants You Must Never Violate

- **Strict Offline Air-Gap:** Zero runtime network calls. Any new capability must work with network sockets disabled.
- **Fail-Closed Verification:** Attribution is reported as `VERIFIED` **only** if all 10 checks pass. Any anomaly, missing record, or internal error returns `UNVERIFIED` (or `VERIFICATION_ERROR`) with zero suspect names.
- **Watermark Alone Never Attributes:** A watermark match without an exact file hash match and valid cryptographic signatures never produces attribution.
- **Identity from Server Session Only:** Identity and role come strictly from unlocking the server-side keystore during login. Client-supplied IDs in request bodies must never override session authentication.
- **Secret Protection:** No plaintext private keys on disk. No passphrases, CEKs, or private keys in HTTP responses, logs, or audit details.
- **Append-Only Immutability:** Ledger blocks and session rows are append-only. Triggers must never be dropped in production code paths.
- **Cryptographic Algorithms:** ML-KEM-768 for key establishment only; ML-DSA-44 for signing; AES-256-GCM for document encryption. Never swap or weaken without documented justification.

---

## 4. Verification Commands

Always run these commands before and after making changes:

```powershell
# Run backend test suite (isolated temporary data directory)
.\.venv\Scripts\python -m pytest tests -q

# Run end-to-end 18-step verification proof
.\.venv\Scripts\python tests\test_e2e_workflow.py

# Lint and build frontend
cd frontend; npm run lint; npm run build; cd ..

# Verify installed packages and crypto inventory against committed BOM
.\.venv\Scripts\python scripts\generate_bom.py --check
```

---

## 5. Scoped Rule References

For domain-specific guidelines, refer to:
- `.agents/rules/project-context.md` (Context indexing)
- `.agents/rules/engineering.md` (Workflow & quality standards)
- `.agents/rules/security.md` (Security boundaries & agent prohibitions)
- `.agents/rules/backend.md` (FastAPI, SQLite, Cryptography)
- `.agents/rules/frontend.md` (React dashboard UI)
- `.agents/rules/testing.md` (Test strategies & adversarial fixtures)
