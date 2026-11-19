@echo off
cd /d "%~dp0"
echo Starting ScamShield server on http://localhost:8000 ...
.\.python311\python.exe -m uvicorn app.main:app --reload --port 8000
pause
