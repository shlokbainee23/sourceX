@echo off
echo ========================================================
echo Starting SIH26237 Backend (FastAPI) - DEMO MODE
echo Demo mode enables the tamper-simulation and reset endpoints.
echo First run? Provision identities: .venv\Scripts\python scripts\provision_identities.py
echo ========================================================
cd /d "%~dp0.."
set SIH_DEMO_MODE=1
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
