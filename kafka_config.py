# kafka_config.py
"""
Kafka Configuration for HealthBot AI
"""

import os
from dotenv import load_dotenv

load_dotenv()

class KafkaConfig:
    # Kafka broker settings (for local development)
    BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    # For cloud Kafka (Confluent Cloud, MSK, etc.)
    KAFKA_CLOUD_ENABLED = os.getenv('KAFKA_CLOUD_ENABLED', 'false').lower() == 'true'
    
    # Confluent Cloud settings (optional)
    CONFLUENT_BOOTSTRAP_SERVERS = os.getenv('CONFLUENT_BOOTSTRAP_SERVERS', '')
    CONFLUENT_API_KEY = os.getenv('CONFLUENT_API_KEY', '')
    CONFLUENT_API_SECRET = os.getenv('CONFLUENT_API_SECRET', '')
    
    # Topic names
    TOPICS = {
        'CHAT_REQUESTS': 'healthbot.chat.requests',
        'CHAT_RESPONSES': 'healthbot.chat.responses',
        'USER_FEEDBACK': 'healthbot.user.feedback',
        'MEDICAL_QUERIES': 'healthbot.medical.queries',
        'ANALYTICS_EVENTS': 'healthbot.analytics.events',
        'RAG_UPDATES': 'healthbot.rag.updates',
        'USER_ACTIVITY': 'healthbot.user.activity'
    }
    
    # Consumer group
    CONSUMER_GROUP = 'healthbot-consumer-group'
    
    # Settings
    AUTO_OFFSET_RESET = 'earliest'
    ENABLE_AUTO_COMMIT = True
    SESSION_TIMEOUT_MS = 30000
    MAX_POLL_RECORDS = 500

config = KafkaConfig()
