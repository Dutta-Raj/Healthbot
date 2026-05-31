# test_kafka.py
"""Test Kafka connection for Medical Chatbot"""

import sys
import time

print("\n" + "="*50)
print("Testing Kafka Connection for Medical Chatbot")
print("="*50)

try:
    from kafka_medical_producer import kafka_medical
    
    print("\n📊 Kafka Status:")
    print(f"   Enabled: {kafka_medical.enabled}")
    print(f"   Bootstrap Servers: {kafka_medical.bootstrap_servers}")
    
    if kafka_medical.enabled:
        print("\n✅ Kafka is WORKING!")
        print("   Event-Driven Architecture is active")
        
        # Send test event
        kafka_medical.send_analytics({
            "event_type": "test_event",
            "message": "Kafka integration test successful"
        })
        print("\n📤 Test event sent to Kafka")
    else:
        print("\n⚠️ Kafka is not running")
        print("\nTo start Kafka:")
        print("1. Open terminal: .\\start_zookeeper.bat")
        print("2. Open another terminal: .\\start_kafka_broker.bat")
        print("3. Then restart this script")
        
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("Make sure kafka-python is installed: pip install kafka-python")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*50)
