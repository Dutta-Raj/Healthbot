# kafka_producer.py
"""
Kafka Producer for HealthBot AI
Sends events to Kafka topics
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

from kafka_config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthBotKafkaProducer:
    def __init__(self):
        self.producer = None
        self.enabled = False
        self._connect()
    
    def _connect(self):
        """Connect to Kafka broker"""
        try:
            if config.KAFKA_CLOUD_ENABLED:
                # For Confluent Cloud
                from confluent_kafka import Producer
                self.producer = Producer({
                    'bootstrap.servers': config.CONFLUENT_BOOTSTRAP_SERVERS,
                    'sasl.mechanisms': 'PLAIN',
                    'security.protocol': 'SASL_SSL',
                    'sasl.username': config.CONFLUENT_API_KEY,
                    'sasl.password': config.CONFLUENT_API_SECRET
                })
            else:
                # For local Kafka
                self.producer = KafkaProducer(
                    bootstrap_servers=config.BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3,
                    max_in_flight_requests_per_connection=5
                )
            self.enabled = True
            logger.info("✅ Kafka producer connected successfully")
        except Exception as e:
            logger.warning(f"⚠️ Kafka producer not available: {e}")
            self.enabled = False
    
    def send_event(self, topic: str, event_type: str, data: Dict[str, Any]):
        """Send event to Kafka topic"""
        if not self.enabled:
            return None
        
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        try:
            future = self.producer.send(topic, value=event)
            result = future.get(timeout=10)
            logger.info(f"✅ Event sent to {topic}: {event_type}")
            return result
        except KafkaError as e:
            logger.error(f"❌ Failed to send event: {e}")
            return None
    
    def send_chat_request(self, user_id: str, message: str, conversation_id: str):
        """Send chat request event"""
        return self.send_event(
            config.TOPICS['CHAT_REQUESTS'],
            'chat_request',
            {
                'user_id': user_id,
                'message': message,
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def send_chat_response(self, user_id: str, response: str, conversation_id: str):
        """Send chat response event"""
        return self.send_event(
            config.TOPICS['CHAT_RESPONSES'],
            'chat_response',
            {
                'user_id': user_id,
                'response': response,
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def send_user_feedback(self, user_id: str, rating: int, feedback_text: str):
        """Send user feedback event"""
        return self.send_event(
            config.TOPICS['USER_FEEDBACK'],
            'user_feedback',
            {
                'user_id': user_id,
                'rating': rating,
                'feedback': feedback_text,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def send_medical_query(self, user_id: str, query: str, context: Dict):
        """Send medical query for analytics"""
        return self.send_event(
            config.TOPICS['MEDICAL_QUERIES'],
            'medical_query',
            {
                'user_id': user_id,
                'query': query,
                'context': context,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def send_analytics_event(self, event_name: str, properties: Dict):
        """Send analytics event"""
        return self.send_event(
            config.TOPICS['ANALYTICS_EVENTS'],
            event_name,
            properties
        )

# Global producer instance
kafka_producer = HealthBotKafkaProducer()
