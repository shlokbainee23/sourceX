# Workflow: Feature Implementation

> **Goal:** Guide an AI agent through a safe, verified implementation of a task from TASKS.md.

```text
DISCOVER ──> PLAN ──> IMPLEMENT ──> TEST ──> VERIFY ──> UPDATE BRAIN
```

### Step 1: Discover
1. Read the assigned task in [docs/brain/TASKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/TASKS.md).
2. Check [docs/brain/CURRENT_STATE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CURRENT_STATE.md) for related blockers or known conflicts.
3. Review relevant architectural records in [docs/brain/DECISIONS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/DECISIONS.md).
4. Inspect the target source files and their corresponding unit tests.

### Step 2: Plan
1. Detail the exact file edits needed.
2. Ensure backward compatibility with existing API consumers and test fixtures.
3. Identify potential failure modes and fail-closed requirements.

### Step 3: Implement
1. Modify only the necessary files.
2. Do not refactor unrelated files.
3. Preserve all existing docstrings, type annotations, and error handling.

### Step 4: Test
1. Run target unit tests for the modified component.
2. Run the full test suite: `pytest tests -q`.
3. If frontend files were modified, run `npm run lint` and `npm run build`.

### Step 5: Verify
1. Inspect `git diff` to verify only intended lines changed.
2. Validate that no private keys, passphrases, or secrets were exposed.

### Step 6: Update Brain
1. Update task status in [docs/brain/TASKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/TASKS.md).
2. Record changes in [docs/brain/CHANGELOG.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CHANGELOG.md).
3. If project state changed, update [docs/brain/CURRENT_STATE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CURRENT_STATE.md).
