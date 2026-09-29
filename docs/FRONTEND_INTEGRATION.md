# SourceX frontend integration

Inspected 2026-09-29. GitHub baseline: `171db49c477bee91c7335d93064edf85b701ce2a`.

## What differed

| Evidence | Result |
| --- | --- |
| Extracted `sourceX-main` versus GitHub HEAD | VERIFIED: all supplied files match after normalizing CRLF/LF line endings. |
| Live JavaScript `/assets/index-DE_6svfZ.js` versus a locked local build | VERIFIED: identical JavaScript content. |
| Live stylesheet versus local build | Same length; observed differences in extremely small `oklab` floating-point values generated on different platforms. No separate frontend source was found. |
| Vercel `/api/health` | VERIFIED: HTTP 200 with `text/html` and the SPA index, not the API's `{"status":"HEALTHY"}` JSON. |
| Existing API client | Accepted that HTML as a successful response; login could construct an invalid user from it. |
| Existing backend | Python/FastAPI, persistent SQLite and keystores, in-memory bearer sessions; no static frontend mount. |

The landing page and role workspaces were already in one codebase. Integration
therefore focuses on hosting the built frontend with its API and handling the
static-only deployment accurately. No separate frontend was reconstructed.

## Integrated local operation

Use Python 3.12/3.13 on Windows and Node 24. Install dependencies, provision
identities with `scripts/provision_identities.py`, and build `frontend/` as in the
README. Then run `scripts/start_workstation.bat`.

Equivalent launch on any platform:

1. Set `SIH_SERVE_FRONTEND=1` in the backend process environment.
2. Run the project environment's `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`.
3. Open `http://127.0.0.1:8000/workstation/` or `http://127.0.0.1:8000/workstation/#/login`.

Only `frontend/dist/` is public. Existing `/api/*` routes, authorization, file
downloads, and the JSON root endpoint are preserved. Missing API paths remain
404s. Missing build output produces a clear startup error when the mount is enabled.
Relative asset URLs make the same build usable at Vercel's root or `/workstation/`.
Development (`npm run dev`) and preview (`npm run preview`) proxy `/api` to
`127.0.0.1:8000`.

Leave `VITE_API_URL` unset for the local deployment. It is a build-time optional
origin override, not a secret. A split frontend/backend setup would need the exact
frontend origin in `SIH_ALLOWED_ORIGINS`. The preferred offline deployment uses
one origin and needs no extra CORS configuration.

Passphrases are entered by the operator, never supplied by the browser bundle.
The old demo strings were publicly downloadable; provision fresh credentials for
anything beyond disposable demonstrations. No operational identities were
provisioned or changed during this integration; tests use temporary identities.

## Vercel and GitHub handoff

The changes are in the local `integration/frontend-backend` branch working tree.
They have not been pushed, merged, or deployed.

- With Vercel Root Directory set to the repository root, the root `vercel.json`
  installs using `npm ci --prefix frontend`, builds using `npm run build --prefix frontend`,
  and publishes `frontend/dist`.
- With Root Directory set to `frontend`, `frontend/vercel.json` uses `npm ci`,
  `npm run build`, and `dist`.
- Use the existing Vercel project to retain `source-x-ten.vercel.app`. A GitHub
  collaborator with write access can push the reviewed branch and open a PR.
  The Vercel project owner needs access to its Git integration and deployment settings.
  First validate a preview deployment, then promote or merge through the project's
  normal production workflow. No tokens need to be pasted into source files or chat.
- The public Vercel build remains a showcase. A working public login would require
  a separately authorized backend deployment with persistent storage and HTTPS;
  that changes the repository's offline operating model. Merely setting a Vercel
  variable or pointing a public site at localhost does not deploy the engine.

## Verification

`npm test` covers static-host HTML fallback, invalid authentication responses,
network errors, bearer tokens, multipart uploads, step-up passphrases, PDF blobs,
and authorization/validation errors. `tests/test_frontend_hosting.py` covers build
availability, asset serving, API separation, and traversal/private-file rejection.

The verification findings, including pre-existing failures, are recorded in
`docs/brain/CURRENT_STATE.md`. The historical project documents describe an older
backend state; their green-check claims are not a current release certification.

Final results: 7 frontend API tests and 2 new hosting tests pass; the production
build and four-role browser smoke pass. The full backend suite is 179 passed /
17 failed, compared with 176 passed / 18 failed in the untouched baseline under
the same environment. No new failing tests were introduced. Existing failures
include security-contract conflicts and stale BOM inventory; resolve those before
a production release. Lint reports zero errors but 37 pre-existing warnings.
