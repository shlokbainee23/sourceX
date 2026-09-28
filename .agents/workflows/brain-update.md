# Workflow: Project Brain Maintenance

> **Goal:** Keep the persistent Project Brain synchronized with repository reality.

---

## When to Update Each Brain File

| File | Trigger for Update | What to Change |
|---|---|---|
| [docs/brain/CURRENT_STATE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CURRENT_STATE.md) | Significant code changes, test suite results, or new blocker discovered | Update phase, functional status table, test status, and known bugs |
| [docs/brain/TASKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/TASKS.md) | Picking up work (`IN_PROGRESS`), completing work (`DONE`), or discovering a new requirement (`BACKLOG`) | Update status, verification status, and relevant notes |
| [docs/brain/DECISIONS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/DECISIONS.md) | ONLY when a genuine architectural decision is approved | Add a new `DEC-xxx` entry with evidence and rationale |
| [docs/brain/RISKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/RISKS.md) | When an audit reveals a vulnerability or when a risk is mitigated | Update mitigation status or add new risk entry |
| [docs/brain/CHANGELOG.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CHANGELOG.md) | Every completed task or meaningful modification | Add a dated entry detailing what changed |

## Maintenance Rules
1. Never fabricate dates or historical entries.
2. Never invent completion percentages; use `VERIFIED COMPLETE`, `PARTIAL`, `NOT VERIFIED`, `UNKNOWN`.
3. Keep brain files token-efficient: use links to source code rather than copy-pasting code blocks.
