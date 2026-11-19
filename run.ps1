Set-Location $PSScriptRoot
Write-Host "Starting ScamShield server on http://localhost:8000 ..." -ForegroundColor Cyan
& ".\.python311\python.exe" -m uvicorn app.main:app --reload --port 8000
