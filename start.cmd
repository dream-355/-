@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   Zhi Heng Care
echo   Web:  http://127.0.0.1:8000/?demo=1
echo   API:  http://127.0.0.1:8000/docs
echo   Close this window to stop the server.
echo.

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause
