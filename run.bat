@echo off
REM Starts backend + frontend, each in its own window. Double-click to demo.
cd /d "%~dp0"
echo [run] Launching backend and frontend...
start "knowledge-backend" cmd /k "backend\run.bat"
timeout /t 3 /nobreak >nul
start "knowledge-frontend" cmd /k "frontend\run.bat"
echo [run] Both windows launched.
echo   Backend:  http://localhost:8000  (docs: /docs)
echo   Frontend: http://localhost:5173
echo NOTE: Ollama must be running (ollama serve) with a pulled model, e.g. llama3.1
pause
