import json
import os
from confluent_kafka import Producer, Consumer

class KafkaHealthService:
    def __init__(self):
        self.enabled = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
        self.producer = None
        
        if self.enabled:
            try:
                self.producer = Producer({
                    'bootstrap.servers': 'localhost:9092',
                    'client.id': 'healthbot-producer'
                })
                print("✅ Kafka Producer initialized")
            except Exception as e:
                print(f"❌ Kafka setup failed: {e}")
                self.enabled = False
        else:
            print("ℹ️ Kafka is disabled - running in local mode")

    def produce_message(self, topic, key, value):
        if not self.enabled:
            print(f"ℹ️ [KAFKA-LOG] Would send to {topic}: {value}")
            return True
            
        try:
            self.producer.produce(
                topic=topic,
                key=str(key),
                value=json.dumps(value)
            )
            self.producer.poll(0)
            return True
        except Exception as e:
            print(f"❌ Error producing message: {e}")
            return False

kafka_service = KafkaHealthService()
