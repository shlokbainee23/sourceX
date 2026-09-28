# Engineering Standards & Workflow Protocol

> **Scope:** Applied when planning, executing, and validating code changes.

## 1. Feature Implementation Protocol

Every engineering change must follow this sequence:

```text
DISCOVER
   │  Inspect CURRENT_STATE.md, TASKS.md, relevant code & tests
   ▼
 PLAN
   │  Identify exact files, schema impacts, and backward compatibility
   ▼
IMPLEMENT
   │  Make minimal, surgical modifications; preserve existing behavior
   ▼
 TEST
   │  Execute pytest, test_e2e_workflow.py, npm run lint/build, bom check
   ▼
VERIFY
   │  Separate verification from implementation; check diff & edge cases
   ▼
UPDATE BRAIN
      Update TASKS.md status, CURRENT_STATE.md, and CHANGELOG.md
```

## 2. Anti-Hallucination & Evidence Rules

- Do NOT invent or claim external integrations (e.g. DigiLocker, API Setu, live NTP, Ethereum).
- Do NOT generate fake completion percentages. Use:
  - `VERIFIED COMPLETE`
  - `PARTIAL`
  - `NOT VERIFIED`
  - `UNKNOWN`
  - `CONFLICT`
- Never silently fix a conflict by rewriting code or docs without documenting the reason.
- If an API or schema parameter is needed, verify against [docs/API.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/API.md) and [backend/app/models/schemas.py](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/backend/app/models/schemas.py).

## 3. Post-Task State Update

After finishing code changes:
1. Review `git diff --stat` to ensure no unintended files were touched.
2. Run the test commands.
3. Update [docs/brain/TASKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/TASKS.md) with task outcome and status.
4. Record meaningful changes in [docs/brain/CHANGELOG.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CHANGELOG.md).
