# simple_kafka.py
"""
Simple In-Memory Kafka Alternative for HealthBot AI
No external dependencies required!
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from collections import deque
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMessageQueue:
    """In-memory message queue as Kafka alternative"""
    
    def __init__(self):
        self.topics = {}
        self.subscribers = {}
        self.lock = threading.Lock()
    
    def create_topic(self, topic_name: str):
        """Create a new topic"""
        with self.lock:
            if topic_name not in self.topics:
                self.topics[topic_name] = deque(maxlen=10000)  # Keep last 10000 messages
                self.subscribers[topic_name] = []
                logger.info(f"✅ Topic created: {topic_name}")
    
    def produce(self, topic_name: str, message: Dict[str, Any]):
        """Produce message to topic"""
        if topic_name not in self.topics:
            self.create_topic(topic_name)
        
        # Add message with metadata
        enriched_message = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'data': message
        }
        
        with self.lock:
            self.topics[topic_name].append(enriched_message)
            
            # Notify subscribers
            for callback in self.subscribers.get(topic_name, []):
                try:
                    callback(enriched_message)
                except Exception as e:
                    logger.error(f"Subscriber error: {e}")
        
        logger.info(f"📤 Message produced to {topic_name}")
        return enriched_message['id']
    
    def consume(self, topic_name: str, callback):
        """Subscribe to topic"""
        if topic_name not in self.subscribers:
            self.subscribers[topic_name] = []
        
        self.subscribers[topic_name].append(callback)
        logger.info(f"👤 Subscriber added to {topic_name}")
        
        # Send existing messages if needed
        with self.lock:
            for msg in self.topics.get(topic_name, []):
                callback(msg)
    
    def get_messages(self, topic_name: str, limit: int = 100) -> List[Dict]:
        """Get recent messages from topic"""
        if topic_name not in self.topics:
            return []
        
        messages = list(self.topics[topic_name])
        return messages[-limit:]

# Create global message queue
message_queue = SimpleMessageQueue()

# Define topics
TOPICS = {
    'CHAT_REQUESTS': 'healthbot.chat.requests',
    'CHAT_RESPONSES': 'healthbot.chat.responses',
    'USER_FEEDBACK': 'healthbot.user.feedback',
    'MEDICAL_QUERIES': 'healthbot.medical.queries',
    'ANALYTICS_EVENTS': 'healthbot.analytics.events',
    'USER_ACTIVITY': 'healthbot.user.activity'
}

# Initialize topics
for topic in TOPICS.values():
    message_queue.create_topic(topic)

class HealthBotMessageQueue:
    """HealthBot specific message queue wrapper"""
    
    def __init__(self):
        self.enabled = True
        self.queue = message_queue
    
    def send_chat_request(self, user_id: str, message: str, conversation_id: str):
        """Send chat request event"""
        return self.queue.produce(
            TOPICS['CHAT_REQUESTS'],
            {
                'type': 'chat_request',
                'user_id': user_id,
                'message': message,
                'conversation_id': conversation_id
            }
        )
    
    def send_chat_response(self, user_id: str, response: str, conversation_id: str):
        """Send chat response event"""
        return self.queue.produce(
            TOPICS['CHAT_RESPONSES'],
            {
                'type': 'chat_response',
                'user_id': user_id,
                'response': response[:500],  # Truncate for storage
                'conversation_id': conversation_id
            }
        )
    
    def send_feedback(self, user_id: str, rating: int, feedback_text: str):
        """Send user feedback event"""
        return self.queue.produce(
            TOPICS['USER_FEEDBACK'],
            {
                'type': 'feedback',
                'user_id': user_id,
                'rating': rating,
                'feedback': feedback_text
            }
        )
    
    def send_medical_query(self, user_id: str, query: str, metadata: Dict = None):
        """Send medical query for analytics"""
        return self.queue.produce(
            TOPICS['MEDICAL_QUERIES'],
            {
                'type': 'medical_query',
                'user_id': user_id,
                'query': query,
                'metadata': metadata or {}
            }
        )
    
    def send_analytics(self, event_name: str, properties: Dict):
        """Send analytics event"""
        return self.queue.produce(
            TOPICS['ANALYTICS_EVENTS'],
            {
                'type': event_name,
                'properties': properties
            }
        )
    
    def get_chat_requests(self, limit: int = 100):
        """Get recent chat requests"""
        return self.queue.get_messages(TOPICS['CHAT_REQUESTS'], limit)
    
    def get_feedback(self, limit: int = 100):
        """Get recent feedback"""
        return self.queue.get_messages(TOPICS['USER_FEEDBACK'], limit)
    
    def get_stats(self):
        """Get queue statistics"""
        stats = {}
        for name, topic in TOPICS.items():
            stats[name] = len(self.queue.get_messages(topic, 1000))
        return stats

# Global instance
message_bus = HealthBotMessageQueue()

print("✅ Simple Message Queue (Kafka alternative) initialized")
print(f"📊 Available topics: {', '.join(TOPICS.values())}")
