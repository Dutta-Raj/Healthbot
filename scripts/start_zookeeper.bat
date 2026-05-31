@echo off
title Zookeeper - Medical Chatbot
cd /d C:\kafka
echo ========================================
echo Starting Zookeeper for Medical Chatbot
echo ========================================
echo.
bin\windows\zookeeper-server-start.bat config\zookeeper.properties
