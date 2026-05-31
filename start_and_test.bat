@echo off
echo Starting Chat Server and Test...
echo.

echo Opening Terminal 1 for Server...
start cmd /k "cd /d C:\Users\KIIT\Desktop\Chatbot && echo Starting Server... && python standalone_chat_fixed.py"

timeout /t 3 /nobreak > nul

echo Opening Terminal 2 for Testing...
start cmd /k "cd /d C:\Users\KIIT\Desktop\Chatbot && echo Running Tests... && timeout /t 2 /nobreak > nul && python smart_test.py"

echo.
echo Both terminals opened!
echo Terminal 1: Running the server
echo Terminal 2: Will test the server
echo.
echo Press any key to close this window...
pause > nul
