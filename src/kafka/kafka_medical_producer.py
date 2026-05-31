# kafka_medical_producer.py
"""Kafka Producer for Medical Chatbot - Event-Driven Architecture"""

import json
import threading
import time
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable
import os
from dotenv import load_dotenv

load_dotenv()

class MedicalChatbotKafka:
    """
    Kafka implementation for Medical Chatbot
    Demonstrates event-driven architecture for healthcare applications
    """
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.enabled = False
        self.producer = None
        self.consumer_thread = None
        
        # Topics for medical chatbot
        self.topics = {
            'chat_requests': 'medical_chat_requests',
            'chat_responses': 'medical_chat_responses', 
            'analytics': 'medical_analytics',
            'notifications': 'medical_notifications'
        }
        
        self._initialize_kafka()
    
    def _initialize_kafka(self):
        """Initialize Kafka connection"""
        try:
            # Create producer
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip',
                retries=3
            )
            
            # Test connection
            self.producer.send(self.topics['analytics'], {'test': 'connection'})
            self.producer.flush()
            
            self.enabled = True
            print("✅ Kafka Connected - Event-Driven Architecture Active")
            print(f"   📤 Producer ready on {self.bootstrap_servers}")
            
            # Start consumer thread for responses
            self._start_response_consumer()
            
        except NoBrokersAvailable:
            print("⚠️ Kafka brokers not available - running in standalone mode")
            print("   Start Kafka with: start_zookeeper.bat and start_kafka_broker.bat")
            self.enabled = False
        except Exception as e:
            print(f"⚠️ Kafka initialization error: {e}")
            self.enabled = False
    
    def _start_response_consumer(self):
        """Start background consumer for responses"""
        def consume_responses():
            try:
                consumer = KafkaConsumer(
                    self.topics['chat_responses'],
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id='medical_chatbot_group'
                )
                
                print(f"   📥 Consumer listening on: {self.topics['chat_responses']}")
                
                for message in consumer:
                    data = message.value
                    print(f"   📨 Response received for: {data.get('user_id', 'unknown')}")
                    # Here you would trigger a callback to send response to user
                    
            except Exception as e:
                print(f"Consumer error: {e}")
            
        self.consumer_thread = threading.Thread(target=consume_responses, daemon=True)
        self.consumer_thread.start()
    
    def send_chat_request(self, user_id: str, message: str, session_id: str):
        """Send chat request to Kafka queue"""
        if not self.enabled or not self.producer:
            return None
        
        try:
            event_data = {
                "event_type": "chat_request",
                "user_id": user_id,
                "message": message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "source": "medical_chatbot"
            }
            
            future = self.producer.send(self.topics['chat_requests'], value=event_data)
            result = future.get(timeout=10)
            
            print(f"   📤 Chat request queued: {result.topic}[{result.partition}] @ offset {result.offset}")
            return result
            
        except Exception as e:
            print(f"   ❌ Failed to queue: {e}")
            return None
    
    def send_analytics(self, event_data: dict):
        """Send analytics events to Kafka"""
        if not self.enabled or not self.producer:
            return None
        
        try:
            event_data["timestamp"] = datetime.now().isoformat()
            event_data["source"] = "medical_chatbot"
            
            self.producer.send(self.topics['analytics'], value=event_data)
            print(f"   📊 Analytics event queued: {event_data.get('event_type', 'unknown')}")
            
        except Exception as e:
            print(f"   ❌ Analytics error: {e}")
    
    def get_status(self):
        """Get Kafka connection status"""
        return {
            "enabled": self.enabled,
            "bootstrap_servers": self.bootstrap_servers,
            "topics": self.topics,
            "producer_connected": self.producer is not None
        }

# Singleton instance
kafka_medical = MedicalChatbotKafka()
