# kafka_medical_integration.py
"""Kafka Integration for Medical Chatbot"""

import json
import threading
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
import os
from dotenv import load_dotenv

load_dotenv()

class MedicalKafkaManager:
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.enabled = os.getenv('KAFKA_ENABLED', 'false').lower() == 'true'
        self.producer = None
        self.consumer = None
        
        if self.enabled:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    compression_type='gzip'
                )
                print("✅ Kafka Producer connected")
                
                self.consumer = KafkaConsumer(
                    'medical_chat_responses',
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id='medical_chatbot_group'
                )
                print("✅ Kafka Consumer connected")
            except Exception as e:
                print(f"⚠️ Kafka connection error: {e}")
                self.enabled = False
    
    def send_chat_request(self, user_id, message, session_id):
        """Send chat request to Kafka"""
        if not self.enabled or not self.producer:
            return None
        
        try:
            message_data = {
                "user_id": user_id,
                "message": message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "type": "chat_request"
            }
            future = self.producer.send('medical_chat_requests', value=message_data)
            result = future.get(timeout=10)
            print(f"📤 Chat request sent to Kafka - Offset: {result.offset}")
            return result
        except Exception as e:
            print(f"❌ Kafka send error: {e}")
            return None
    
    def send_analytics(self, user_id, query, response_length, processing_time):
        """Send analytics data to Kafka"""
        if not self.enabled or not self.producer:
            return None
        
        try:
            analytics_data = {
                "user_id": user_id,
                "query": query,
                "response_length": response_length,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat(),
                "type": "analytics"
            }
            self.producer.send('medical_analytics', value=analytics_data)
            print(f"📊 Analytics sent to Kafka")
        except Exception as e:
            print(f"❌ Analytics error: {e}")

# Singleton instance
kafka_manager = MedicalKafkaManager()
