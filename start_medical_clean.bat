# start_clean.bat
@echo off
title Medical Chatbot
cd /d C:\Users\KIIT\Desktop\Chatbot
echo ========================================
echo MEDICAL CHATBOT
echo ========================================
echo.
echo Killing any existing processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul
echo.
echo Starting Medical Chatbot Server...
echo.
python medical_bot_final.py
pause
