import json
import os
from datetime import datetime

class KafkaService:
    def __init__(self):
        self.available = False
        self.producer = None
        # Only initialize if Kafka is enabled
        if os.getenv("KAFKA_ENABLED", "false").lower() == "true":
            self.initialize()
        else:
            print("💡 Kafka is disabled in environment variables")
    
    def initialize(self):
        """Initialize Kafka producer if available"""
        try:
            from kafka import KafkaProducer
            KAFKA_BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
            
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda v: str(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            self.available = True
            print("✅ Kafka producer initialized successfully!")
        except ImportError:
            print("❌ Kafka not installed. Continuing without Kafka messaging.")
        except Exception as e:
            print(f"❌ Kafka connection failed: {e}")
            print("💡 Continuing without Kafka messaging.")

    def send_chat_message(self, user_id, user_message, bot_response, alert_triggered=False):
        """Send chat data to Kafka for processing"""
        if self.available and self.producer:
            try:
                message_data = {
                    "user_id": user_id,
                    "user_message": user_message,
                    "bot_response": bot_response,
                    "timestamp": datetime.now().isoformat(),
                    "alert_triggered": alert_triggered
                }
                
                future = self.producer.send(
                    topic="healthq-chats",
                    key=user_id,
                    value=message_data
                )
                future.get(timeout=10)
                print(f"✅ Message sent to Kafka topic: healthq-chats")
                return True
            except Exception as e:
                print(f"❌ Failed to send message to Kafka: {e}")
                return False
        return False

    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()

# Create a global instance - THIS LINE IS IMPORTANT
kafka_service = KafkaService()