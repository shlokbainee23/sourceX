# Project Context Rules

> **Scope:** Always active for understanding repository context and documents.

## Context Discovery Standards
1. **Never read the entire repository at once:** This wastes token context and degrades reasoning. Load only the specific brain documents and source files required for the task.
2. **Navigation Hierarchy:**
   - To understand system components and authoritative links: read [docs/brain/PROJECT_BRAIN.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/PROJECT_BRAIN.md).
   - To check what actually works vs what is broken: read [docs/brain/CURRENT_STATE.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/CURRENT_STATE.md).
   - To find or update assigned tasks: read [docs/brain/TASKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/TASKS.md).
   - To check why an architectural pattern exists: read [docs/brain/DECISIONS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/DECISIONS.md).
   - To check known risks before proposing modifications: read [docs/brain/RISKS.md](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/docs/brain/RISKS.md).
3. **Source of Truth vs Historical Plans:**
   - Treat `implementation_plan_v2.md` strictly as a historical document that predated implementation.
   - Authoritative technical docs are `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/API.md`, and `docs/DATABASE.md`.
