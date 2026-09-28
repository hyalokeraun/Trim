@echo off
REM Starts the Knowledge Assistant frontend (Vite dev server).
cd /d "%~dp0"
where npm >nul 2>nul
if errorlevel 1 (
  echo [run] Node.js/npm not found. Install Node 18+ first.
  pause
  exit /b 1
)
if not exist "node_modules" (
  echo [run] Installing dependencies first...
  call npm install
)
echo [run] Starting frontend on http://localhost:5173 ...
call npm run dev
pause
