@echo off
title HEALTHBOT AI - PRODUCTION SERVER
cd /d C:\Users\KIIT\Desktop\Chatbot
echo ========================================
echo HEALTHBOT AI - PRODUCTION READY
echo ========================================
echo.
echo Features:
echo   - User Authentication (JWT)
echo   - MongoDB Database
echo   - Cohere AI Integration
echo   - Conversation History
echo   - Feedback System
echo.
echo Server: http://localhost:8000
echo Frontend: frontend_dashboard.html
echo.
echo Press CTRL+C to stop
echo ========================================
echo.
python production_chatbot.py
pause
