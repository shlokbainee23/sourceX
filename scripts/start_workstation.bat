@echo off
setlocal
cd /d "%~dp0.."
if not exist "frontend\dist\index.html" (
  echo Build the frontend first: cd frontend ^&^& npm ci ^&^& npm run build
  exit /b 1
)
set SIH_SERVE_FRONTEND=1
echo Open http://127.0.0.1:8000/workstation/
echo Use the passphrases from scripts\provision_identities.py.
echo Demo reset and tamper endpoints stay disabled unless SIH_DEMO_MODE=1 is set.
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
