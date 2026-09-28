@echo off
REM Starts the Knowledge Assistant backend (FastAPI + uvicorn) using the isolated venv.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [run] .venv not found. Create it first:
  echo   python -m venv .venv
  echo   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
echo [run] Starting backend on http://localhost:8000 ...
".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000
pause
