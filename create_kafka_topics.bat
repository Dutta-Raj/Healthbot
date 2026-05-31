@echo off
cd /d C:\kafka
echo Creating Kafka topics for Medical Chatbot...
echo.
bin\windows\kafka-topics.bat --create --topic medical_chat_requests --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
bin\windows\kafka-topics.bat --create --topic medical_chat_responses --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
bin\windows\kafka-topics.bat --create --topic medical_analytics --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
echo.
echo Topics created successfully!
bin\windows\kafka-topics.bat --list --bootstrap-server localhost:9092
pause
