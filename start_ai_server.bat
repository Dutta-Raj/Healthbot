@echo off
title Cohere AI Chatbot Server
cd /d C:\Users\KIIT\Desktop\Chatbot
echo ========================================
echo COHERE AI CHATBOT SERVER
echo ========================================
echo.
echo Using Cohere 'command' model (current)
echo Server: http://localhost:8000
echo Chat: POST /chat
echo.
echo Press CTRL+C to stop the server
echo ========================================
echo.
python standalone_chat_fixed_ai.py
pause
