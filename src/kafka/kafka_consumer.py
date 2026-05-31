# kafka_consumer.py
"""
Kafka Consumer for HealthBot AI
Processes events from Kafka topics
"""

import json
import threading
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging

from kafka_config import config
from database.healthbot_db import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthBotKafkaConsumer:
    def __init__(self):
        self.consumers = {}
        self.running = False
        self.enabled = False
        self._connect()
    
    def _connect(self):
        """Connect to Kafka broker"""
        try:
            self.consumer = KafkaConsumer(
                *config.TOPICS.values(),
                bootstrap_servers=config.BOOTSTRAP_SERVERS,
                group_id=config.CONSUMER_GROUP,
                auto_offset_reset=config.AUTO_OFFSET_RESET,
                enable_auto_commit=config.ENABLE_AUTO_COMMIT,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                max_poll_records=config.MAX_POLL_RECORDS
            )
            self.enabled = True
            logger.info("✅ Kafka consumer connected successfully")
        except Exception as e:
            logger.warning(f"⚠️ Kafka consumer not available: {e}")
            self.enabled = False
    
    def process_chat_requests(self, event_data):
        """Process chat request events"""
        data = event_data.get('data', {})
        user_id = data.get('user_id')
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        
        logger.info(f"📨 Processing chat request from {user_id}: {message[:50]}...")
        
        # Store analytics
        if db.available:
            db.db.analytics_events.insert_one({
                'event_type': 'chat_request',
                'user_id': user_id,
                'conversation_id': conversation_id,
                'message_preview': message[:100],
                'timestamp': event_data.get('timestamp')
            })
    
    def process_user_feedback(self, event_data):
        """Process user feedback events"""
        data = event_data.get('data', {})
        user_id = data.get('user_id')
        rating = data.get('rating')
        feedback = data.get('feedback')
        
        logger.info(f"⭐ Feedback received from {user_id}: Rating {rating}/5")
        
        # Store feedback in MongoDB
        if db.available:
            db.save_feedback(user_id, None, rating, feedback)
    
    def process_medical_queries(self, event_data):
        """Process medical queries for analytics"""
        data = event_data.get('data', {})
        query = data.get('query')
        
        logger.info(f"🔍 Medical query: {query[:50]}...")
        
        # Track popular queries
        if db.available:
            db.db.medical_queries_stats.update_one(
                {'query': query},
                {'': {'count': 1}, '': {'last_queried': event_data.get('timestamp')}},
                upsert=True
            )
    
    def start_consuming(self):
        """Start consuming messages"""
        if not self.enabled:
            logger.warning("Kafka not available, skipping consumer")
            return
        
        self.running = True
        logger.info("🚀 Starting Kafka consumer...")
        
        for message in self.consumer:
            if not self.running:
                break
            
            topic = message.topic
            event_data = message.value
            event_type = event_data.get('event_type')
            
            try:
                if topic == config.TOPICS['CHAT_REQUESTS']:
                    self.process_chat_requests(event_data)
                elif topic == config.TOPICS['USER_FEEDBACK']:
                    self.process_user_feedback(event_data)
                elif topic == config.TOPICS['MEDICAL_QUERIES']:
                    self.process_medical_queries(event_data)
                else:
                    logger.debug(f"Received event from {topic}: {event_type}")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        logger.info("Kafka consumer stopped")

# Global consumer instance
kafka_consumer = HealthBotKafkaConsumer()
