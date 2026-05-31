# cloud_kafka_setup.py
"""
Setup guide for Confluent Cloud Kafka (Free Tier)
"""

print("""
🌩️ Setting up Free Kafka on Confluent Cloud:

1. Go to https://confluent.cloud
2. Sign up for free account (no credit card required)
3. Create a new cluster (Basic tier - free)
4. Create API keys
5. Add to your .env file:

KAFKA_CLOUD_ENABLED=true
CONFLUENT_BOOTSTRAP_SERVERS=pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
CONFLUENT_API_KEY=your_api_key
CONFLUENT_API_SECRET=your_api_secret

6. Install confluent-kafka:
   pip install confluent-kafka

Then run: python main_api_with_kafka.py
""")
