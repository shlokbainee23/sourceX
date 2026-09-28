# Workflow: Verification & Quality Audit

> **Goal:** Independent verification of an implementation or state audit.  
> *Principle:* An implementing agent must not automatically declare its own work correct. Verification audits must inspect with adversarial rigor.

---

## Audit Workflow Sequence

1. **Requirements Compliance Check:**
   - Verify every requirement against active implementation.
   - Check if any requirement was omitted or substituted with synthetic logic.

2. **Architecture & Invariant Compliance Check:**
   - Check that zero runtime network calls were added.
   - Verify that all verification paths fail closed (`UNVERIFIED` / `VERIFICATION_ERROR`).
   - Confirm no plaintext keys or passphrases appear in logs, responses, or disk.

3. **API & Database Contract Audit:**
   - Verify that response models match [docs/API.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/API.md).
   - Check that SQLite triggers remain active.

4. **Test Suite & Build Execution:**
   - Run `pytest tests -q`.
   - Run `python tests/test_e2e_workflow.py`.
   - Run `cd frontend; npm run lint; npm run build; cd ..`.
   - Run `python scripts/generate_bom.py --check`.

5. **Classification of Findings:**
   The verification report must categorize all findings into these explicit states:
   - `CONFIRMED DEFECT`: Reproducible bug, failing test, or violated security invariant.
   - `POSSIBLE DEFECT`: Suspicious pattern or unhandled edge case without immediate reproduction.
   - `MISSING EVIDENCE`: Stated capability cannot be confirmed from code or tests.
   - `DOCUMENTATION CONFLICT`: Code and documentation disagree.
   - `RECOMMENDATION`: Suggested engineering improvement (never label a recommendation as a defect).
