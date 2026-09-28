# Frontend Engineering Rules

> **Scope:** Applied when modifying the React UI dashboard under `frontend/`.

## 1. Frontend Architecture

- **Stack:** React 19, Vite 8, Tailwind CSS 4, Lucide React icons.
- **Main Dashboard:** Monolithic component at [frontend/src/App.jsx](file:///c:/Users/thimm/Downloads/SIH26237-main/SIH26237-main/frontend/src/App.jsx).
- **Styling:** Tailwind CSS utility classes and `frontend/src/App.css`.

## 2. API Communication & Authentication

- All API calls must route through `apiFetch()` helper, ensuring `Authorization: Bearer <token>` is attached.
- Keystore unlocking occurs via `handleLogin(principalId)` calling `/api/auth/login`.
- The frontend must never enforce or assume authorization locally; it reflects backend HTTP status responses.
- If backend schemas change, update corresponding request payloads in `App.jsx` immediately.

## 3. Verification & Quality Gates

Before concluding frontend edits, always verify:
```powershell
cd frontend
npm run lint    # Must report 0 warnings and 0 errors (oxlint)
npm run build   # Must build dist/ successfully with Vite
cd ..
```
