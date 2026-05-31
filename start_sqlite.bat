@echo off
title HEALTHBOT AI - SQLITE VERSION
cd /d C:\Users\KIIT\Desktop\Chatbot
echo ========================================
echo HEALTHBOT AI - SQLITE VERSION
echo ========================================
echo.
echo Features:
echo   - User Authentication (JWT)
echo   - SQLite Database (no MongoDB needed)
echo   - Cohere AI Integration
echo   - Conversation History
echo.
echo Server: http://localhost:8000
echo Frontend: frontend_dashboard.html
echo.
echo Press CTRL+C to stop
echo ========================================
echo.
python production_chatbot_sqlite.py
pause
