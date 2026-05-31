@echo off
title Kafka Broker - Medical Chatbot
cd /d C:\kafka
echo ========================================
echo Starting Kafka Broker for Medical Chatbot
echo ========================================
echo.
echo Waiting for Zookeeper...
timeout /t 5 /nobreak >nul
bin\windows\kafka-server-start.bat config\server.properties
